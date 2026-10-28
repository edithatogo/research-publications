# SPDX-License-Identifier: Apache-2.0
"""Read-only adapter for saved Publication Registry rows, with explicit skips.

Locale-shaped Text timestamps are retained as evidence, never assigned a zone.
This qualifies the saved registry projection, not complete upstream coverage.
"""
from collections import Counter
from copy import deepcopy
import re
from scripts.e09_first_discovery import (
    _utc_instant, _canonical_key, parse_registry_row, STATUS_TIERS,
    select_new_threads, select_catch_up_threads,
)
from scripts.e09_feed_contracts import publication_source_key


def qualify_rows(rows):
    if not isinstance(rows, list):
        raise ValueError('Complete native row list required')
    # Validate before ordering: mixed/missing identities must reject the whole
    # input through the same explicit boundary, never leak a partial packet.
    if any(not isinstance(row, dict) or type(row.get('Id')) is not int
           or row['Id'] < 1 for row in rows):
        raise ValueError('Native row object and positive item identity required')
    selected, accounting, seen, seen_ids = [], [], set(), set()
    for row in sorted(rows, key=lambda r: r['Id']):
        if row['Id'] in seen_ids:
            raise ValueError('Repeated native item identity; no partial selection')
        seen_ids.add(row['Id'])
        evidence = {'item_id': row['Id'], 'native_etag': row.get('odata.etag'),
                    'native_version': row.get('OData__UIVersionString'),
                    'raw_first_observed': row.get('field_19'),
                    'raw_last_observed': row.get('field_20'),
                    'raw_publication_month': row.get('field_6'),
                    'raw_publication_date': row.get('field_7'),
                    'publication_date_precision': row.get('field_8')}
        key = row.get('field_1')
        if key is None or key == '':
            accounting.append({**evidence, 'disposition': 'retained_placeholder'})
            continue
        key = publication_source_key(key)
        if key in seen:
            raise ValueError('Repeated native SourceKey; no partial selection')
        seen.add(key)
        canonical = _canonical_key(row.get('field_2'))
        status = row.get('field_17')
        if status not in STATUS_TIERS:
            raise ValueError('Unknown native review label')
        evidence.update(publication_key=key, canonical_key=canonical,
                        review_status=status, tier=STATUS_TIERS[status])
        if (not isinstance(evidence['native_etag'], str) or not evidence['native_etag']
                or evidence['native_etag'] == '*'
                or not isinstance(evidence['native_version'], str)
                or not re.fullmatch(r'[1-9][0-9]*\.[0-9]+', evidence['native_version'])):
            raise ValueError('Saved native revision evidence missing')
        first, last = row.get('field_19'), row.get('field_20')
        try:
            _utc_instant(first, 'FirstObservedUTC')
        except (ValueError, TypeError):
            accounting.append({**evidence, 'disposition': 'excluded' if status == 'Excluded'
                               else 'unknown_first_observation',
                               'first_observation_status': 'unqualified_instant'})
            continue
        try:
            if last is not None:
                _utc_instant(last, 'LastObservedUTC')
            evidence['last_observation_status'] = 'qualified' if last is not None else 'unknown'
        except (ValueError, TypeError):
            evidence['last_observation_status'] = 'unqualified_instant_retained'
            last = None
        month = row.get('field_6')
        if month == '' or row.get('field_8') not in {'day', 'month'}:
            month = None
        title = None if row.get('Title') == '' else row.get('Title')
        logical = dict(SourceKey=key, CanonicalKey=canonical, ReviewStatus=status,
                       FirstObservedUTC=first, LastObservedUTC=last,
                       PublicationMonth=month, Title=title)
        # No other malformed field or reversed qualified chronology is softened.
        parse_registry_row(logical)
        selected.append(logical)
        accounting.append({**evidence, 'disposition': 'qualified'})
    return {'qualified_rows': selected, 'accounting': accounting,
            'disposition_counts': dict(Counter(r['disposition'] for r in accounting)),
            'tier_counts': dict(Counter(r.get('tier', 'placeholder') for r in accounting))}


def selection_packet(rows, *, baseline_utc, through_utc, catch_up_from_utc):
    result = qualify_rows(deepcopy(rows))
    qualified = sorted(result['qualified_rows'], key=lambda r: r['SourceKey'])
    by_canonical = {}
    for row in result['accounting']:
        if 'canonical_key' in row:
            by_canonical.setdefault(row['canonical_key'], []).append(row)
    aliases = {key: [{'publication_key': r['publication_key'], 'tier': r['tier']}
                     for r in group] for key, group in by_canonical.items() if len(group) > 1}
    # Equal keys are evidence to reconcile against saved mappings, not authority
    # to pick a winner, merge human content or open multiple publication threads.
    ready = [r for r in qualified if r['CanonicalKey'] not in aliases]
    new = select_new_threads(ready, baseline_utc=baseline_utc, through_utc=through_utc)
    catch_up = select_catch_up_threads(ready, catch_up_from_utc=catch_up_from_utc,
                                       catch_up_to_utc=baseline_utc)
    by_key = {r['SourceKey']: r for r in qualified}
    for record in new['new_threads'] + catch_up:
        source = by_key[record['publication_key']]
        record.update(Title=source['Title'], PublicationMonth=source['PublicationMonth'])
    return {**result, 'new': new, 'catch_up': catch_up,
            'canonical_aliases_held_for_mapping_reconciliation': aliases,
            'window': {'baseline_exclusive_utc': baseline_utc, 'through_inclusive_utc': through_utc,
                       'catch_up_from_inclusive_utc': catch_up_from_utc},
            'delivery_state': 'no_send'}
