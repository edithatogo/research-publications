"""Evidence-bound internal date planning over retained policy/anchor captures.

No source-date edits, approval decisions, native writes or message delivery.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from scripts.grants_planning import (validate_policy, institutional_policy_status,
    institutional_deadline, reconcile_institutional_override_history)
from scripts.grants_registry import parse_offset_instant

FORMAT = 'rims-approved-policy-v1'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def key(prefix, value):
    return prefix + hashlib.sha256(canonical(value).encode()).hexdigest()[:32]


def real_day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('An explicit real source day is required')
    return date.fromisoformat(value)


def approved_policy(record, *, organisation, evidence_files):
    """Validate an already-reviewed authority binding, never grant approval."""
    value = json.loads(record['PolicyJson'])
    if not isinstance(value, dict) or value.get('SchemaVersion') != FORMAT:
        return None  # Old raw/test policies are not upgraded implicitly.
    if set(value) != {'SchemaVersion', 'Policy', 'Authority', 'Scope'}:
        raise ValueError('Policy envelope fields differ from the accepted contract')
    p, authority, scope = value['Policy'], value['Authority'], value['Scope']
    if not validate_policy(p) or p['OrganisationKey'] != organisation:
        raise ValueError('Valid policy for the exact organisation required')
    if p['AnchorKind'] != 'final':
        raise ValueError('Only the confirmed external-final anchor is implemented')
    expected = key('POLICY:', [p['PolicyKey'], p['Version']])
    if record.get('PolicyVersionKey') != expected:
        raise ValueError('Immutable policy version key differs')
    required = {'Status', 'DocumentID', 'DocumentVersion', 'SourceURL', 'EvidenceSHA256',
                'PolicySHA256', 'ApprovedBy', 'ApprovedAtUTC'}
    if not isinstance(authority, dict) or set(authority) != required:
        raise ValueError('Complete authoritative policy evidence required')
    if authority['Status'] != 'Approved':
        return None
    for field in required - {'Status'}:
        if not isinstance(authority[field], str) or not authority[field].strip() or authority[field] != authority[field].strip():
            raise ValueError('Authority fields must be explicit unpadded text')
    u = urlsplit(authority['SourceURL'])
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.port == 0:
        raise ValueError('Authoritative HTTPS source required')
    if parse_offset_instant(authority['ApprovedAtUTC']).utcoffset() != timedelta(0):
        raise ValueError('Approval evidence must retain an explicit UTC timestamp')
    digest = authority['EvidenceSHA256']
    if not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('Exact original policy digest required')
    if digest not in evidence_files:
        raise ValueError('Original policy evidence is missing from the retained archive map')
    original = Path(evidence_files[digest]).read_bytes()
    if hashlib.sha256(original).hexdigest() != digest:
        raise ValueError('Original policy evidence differs; preserve and stop')
    if authority['PolicySHA256'] != hashlib.sha256(canonical(p).encode()).hexdigest():
        raise ValueError('Approved rule binding differs from policy content')
    if p['CalendarOrBusinessDays'] == 'business':
        holiday_hash = p['HolidayCoverage']['EvidenceSHA256']
        if holiday_hash not in evidence_files:
            raise ValueError('Original holiday evidence is missing from the retained archive map')
        holiday_original = Path(evidence_files[holiday_hash]).read_bytes()
        if hashlib.sha256(holiday_original).hexdigest() != holiday_hash:
            raise ValueError('Original holiday evidence differs')
    if (not isinstance(scope, dict) or set(scope) != {'Sources', 'OpportunityKeys'}
            or scope['Sources'] != ['GrantConnectRSS'] or not isinstance(scope['OpportunityKeys'], list)
            or any(not isinstance(k, str) or not k or k != k.strip() for k in scope['OpportunityKeys'])
            or len(scope['OpportunityKeys']) != len(set(scope['OpportunityKeys']))):
        raise ValueError('Explicit GrantConnect applicability scope required')
    return copy.deepcopy(value)


def plan(snapshot, *, organisation, as_of, evidence_files):
    """Produce proposed internal rows plus explicit held/stale dispositions.

    The caller must reconcile source/policy/history ETags before any future
    native application. This planner never authorises those writes.
    """
    real_day(as_of)
    if not isinstance(organisation, str) or not organisation or organisation != organisation.strip():
        raise ValueError('Exact organisation identity required')
    if not isinstance(evidence_files, dict):
        raise ValueError('Retained original evidence map required')
    required = {'policies', 'overrides', 'registry', 'calendar'}
    if not isinstance(snapshot, dict) or set(snapshot) != required:
        raise ValueError('Four complete retained row arrays required')
    if any(not isinstance(snapshot[k], list) for k in required):
        raise ValueError('Complete native arrays required')
    original = copy.deepcopy(snapshot)
    registry = {}
    for row in snapshot['registry']:
        identity = row['OpportunityKey']
        if identity in registry:
            raise ValueError('Duplicate registry identity')
        registry[identity] = row
    policies = []
    versions = set()
    for record in snapshot['policies']:
        if record['PolicyVersionKey'] in versions:
            raise ValueError('Duplicate policy version identity')
        versions.add(record['PolicyVersionKey'])
        envelope = approved_policy(record, organisation=organisation, evidence_files=evidence_files)
        if envelope is not None:
            policies.append((record, envelope))
    histories = [json.loads(r['OverrideJson']) for r in snapshot['overrides']]
    result = {'as_of': as_of, 'organisation': organisation, 'rows': [], 'held': [],
              'override_assessments': [], 'native_submission_allowed': False}
    seen = set()
    for anchor in snapshot['calendar']:
        deadline = anchor.get('DeadlineKey', '')
        if not isinstance(deadline, str) or not deadline.startswith('GC-CLOSE:'):
            continue
        if deadline in seen:
            raise ValueError('Duplicate source deadline identity')
        seen.add(deadline)
        source = registry.get(anchor.get('OpportunityKey'))
        if (not source or source.get('Source') != 'GrantConnectRSS' or anchor.get('RevisionApplied') is not True
                or anchor.get('ReviewStatus') not in ['Reviewed', 'Source confirmed']
                or not re.fullmatch(r'GC-CLOSE:[0-9a-f]{32}', deadline)):
            result['held'].append({'DeadlineKey': deadline, 'Reason': 'unqualified_source_anchor'})
            continue
        url = lambda value: value.get('Url') if isinstance(value, dict) else value
        official = url(anchor.get('SourceURL'))
        if (not isinstance(official, str) or not official.startswith('https://www.grants.gov.au/')
                or official != url(source.get('URL')) or not source.get('EvidenceHash')):
            raise ValueError('Source anchor provenance differs from retained registry')
        day = anchor.get('Calendar_x0020_day')
        exact = anchor.get('DeadlinePrecision') == 'day' and anchor.get('Cancelled') is not True
        if exact:
            real_day(day)
        matches = [(r, e) for r, e in policies if
            (not e['Scope']['OpportunityKeys'] or source['OpportunityKey'] in e['Scope']['OpportunityKeys'])
            and institutional_policy_status(e['Policy'], as_of) == 'current'
            and parse_offset_instant(e['Authority']['ApprovedAtUTC']).date().isoformat() <= as_of]
        if len(matches) > 1:
            raise ValueError('Overlapping authoritative policies; explicit reconciliation required')
        record, envelope = matches[0] if matches else (None, None)
        p = envelope['Policy'] if envelope else None
        current_anchor = {'DeadlineKey': deadline, 'LocalDate': day if exact else None,
                          'Precision': anchor.get('DeadlinePrecision', 'unknown'), 'Cancelled': anchor.get('Cancelled') is True}
        history = [r for r in histories if r.get('AnchorDeadlineKey') == deadline]
        assessed = reconcile_institutional_override_history(history, current_anchor=current_anchor,
            current_policy=p, as_of=as_of)
        result['override_assessments'].extend(assessed)
        reason = 'approved_policy_missing' if p is None else None
        if not exact:
            reason = 'source_cancelled_or_not_day_precision'
        calculated = None
        if not reason:
            calculated = institutional_deadline(day, p['LeadDays'],
                business_days=p['CalendarOrBusinessDays'] == 'business', holidays=p.get('HolidayDates'))
            if calculated is None:
                reason = 'date_outside_representable_range'
            elif (calculated < p['EffectiveFrom'] or day < p['EffectiveFrom']
                    or (p.get('EffectiveTo') and day > p['EffectiveTo'])):
                reason = 'date_outside_policy_effective_interval'
            elif p['CalendarOrBusinessDays'] == 'business' and (calculated < p['HolidayCoverage']['CoverageStart'] or day > p['HolidayCoverage']['CoverageEnd']):
                reason = 'holiday_coverage_incomplete'
        if reason:
            result['held'].append({'DeadlineKey': deadline, 'Reason': reason})
            continue
        latest = [r for r in assessed if r['SupersededByRevision'] is None]
        # A stale or unreviewed override is visible, never silently applied or overwritten.
        usable = [r for r in latest if r['MatchesCurrentInputs'] and r['ReviewStatusIsReviewed']]
        if len(usable) > 1:
            raise ValueError('Conflicting reviewed override histories')
        needs_review = bool(latest and not usable)
        internal = key('INTERNAL:', [source['OpportunityKey'], deadline, p['PolicyKey']])
        row = {'DeadlineKey': internal, 'OpportunityKey': source['OpportunityKey'],
               'AnchorDeadlineKey': deadline, 'AnchorDate': day, 'PolicyKey': p['PolicyKey'],
               'PolicyVersion': p['Version'], 'PolicyVersionKey': record['PolicyVersionKey'],
               'CalculatedDate': calculated, 'EffectiveDate': usable[0]['OverrideDate'] if usable else (None if needs_review else calculated),
               'OverrideKey': usable[0]['OverrideKey'] if usable else None,
               'NeedsOverrideReview': needs_review,
               'PolicyEvidenceSHA256': envelope['Authority']['EvidenceSHA256'],
               'AuthorityURL': envelope['Authority']['SourceURL'], 'SourceURL': official,
               'SourceRevision': anchor.get('Revision'), 'SourceVersion': anchor.get('odata.etag'),
               'PolicyRowID': record.get('Id'), 'PolicyRowVersion': record.get('odata.etag'),
               'ReviewStatus': 'Needs override review' if needs_review else 'Policy backed'}
        material = {k: v for k, v in row.items() if k not in ['SourceVersion', 'PolicyRowID', 'PolicyRowVersion']}
        row['Revision'] = hashlib.sha256(canonical(material).encode()).hexdigest()
        result['rows'].append(row)
    assert snapshot == original, 'Source/history mutation is forbidden'
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--organisation', required=True)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--evidence-map', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    paths = [Path(p).resolve() for p in [args.snapshot, args.evidence_map, args.output]]
    if any(not p.is_relative_to(root / 'private') for p in paths):
        parser.error('Retain source captures, evidence map and new output under private/')
    result = plan(json.loads(paths[0].read_text()), organisation=args.organisation,
                  as_of=args.as_of, evidence_files=json.loads(paths[1].read_text()))
    with paths[2].open('x') as handle:
        json.dump(result, handle, indent=2)


if __name__ == '__main__':
    main()
