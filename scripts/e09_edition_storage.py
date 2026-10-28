# SPDX-License-Identifier: Apache-2.0
"""Immutable no-send edition snapshots; no provider, schedule or delivery ledger.

Store the exact preference and input projection so a saved edition can be rebuilt.
A prepared or saved no-send edition never counts as delivered.
"""
from copy import deepcopy
from hashlib import sha256
import json
from datetime import timezone, timedelta
from scripts.e09_subscription_editions import build_first_discovery_editions, enum_empty_windows
from scripts.e09_feed_contracts import validate_subscription_preference
from scripts.e09_feed_contracts import publication_source_key
from scripts.e09_feed_contracts import _parse_aware_instant


def brisbane_discovery_date(first_observed_utc):
    """Project a qualified aware observation instant; never guess a naive zone."""
    return _parse_aware_instant(first_observed_utc, 'first_observed_utc').astimezone(
        timezone(timedelta(hours=10))).date().isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def prepare_edition_snapshot(subscription, discovered, *, start_date, end_date,
                             already_delivered=()):
    preference = validate_subscription_preference(deepcopy(subscription))
    if preference['delivery_authority_active'] or preference['delivery_authority_reference'] is not None:
        raise ValueError('Only no-send qualification preferences permitted')
    if not isinstance(already_delivered, (list, tuple, set, frozenset)):
        raise ValueError('Delivered keys must be an explicit collection')
    for key in already_delivered:
        publication_source_key(key, 'already_delivered publication key')
    delivered = sorted(set(already_delivered))
    # Validate span even for an off/withdrawn preference.
    slots = enum_empty_windows('daily', start_date, end_date)
    result = build_first_discovery_editions(preference, discovered, already_delivered=delivered)
    for row in discovered:
        if not start_date <= row.get('discovered_on', '') <= end_date:
            raise ValueError('Input outside explicit Brisbane date span')
    if preference['cadence'] in {'daily', 'weekly'} and preference['status'] == 'active':
        slots = enum_empty_windows(preference['cadence'], start_date, end_date)
        existing = {(e['window_start'], e['window_end']): e for e in result['editions']}
        for slot in slots:
            key = (slot['start'], slot['end'])
            if key not in existing:
                existing[key] = dict(edition_kind='first_discovery_feed',
                    subscription_id=preference['subscription_id'], subscriber_urn=preference['subscriber_urn'],
                    cadence=preference['cadence'], window_start=key[0], window_end=key[1],
                    publications=[], publication_count=0, intended_outcome='no_send',
                    delivery_authority_reference=None)
        result['editions'] = [existing[k] for k in sorted(existing)]
    inputs = dict(subscription=preference,
                  discovered=sorted(deepcopy(discovered), key=lambda r: r['publication_key']),
                  already_delivered=delivered, start_date=start_date, end_date=end_date)
    digest = sha256(canonical(inputs).encode()).hexdigest()
    return dict(edition_snapshot_id='e09-edition:'+digest, revision=1,
                inputs=inputs, input_sha256=digest, result=result,
                timezone='Australia/Brisbane', authoritative=False,
                intended_outcome='no_send', delivered=False)


def validate_edition_snapshot(record):
    if not isinstance(record, dict) or set(record) != {
            'edition_snapshot_id','revision','inputs','input_sha256','result',
            'timezone','authoritative','intended_outcome','delivered'}:
        raise ValueError('Exact edition snapshot required')
    inputs = record['inputs']
    if not isinstance(inputs, dict) or set(inputs) != {
            'subscription','discovered','already_delivered','start_date','end_date'}:
        raise ValueError('Exact edition inputs required')
    expected = prepare_edition_snapshot(**inputs)
    if (record != expected or type(record['revision']) is not int
            or record['authoritative'] is not False or record['delivered'] is not False):
        raise ValueError('Edition fingerprint/output differs; retain immutable original')
    return deepcopy(record)
