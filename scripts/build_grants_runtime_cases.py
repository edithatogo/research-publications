"""Prepare synthetic grants runtime cases; never invoke a flow or write list rows."""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

if __package__:
    from scripts.grants_registry import stable_key
else:
    from grants_registry import stable_key

ROOT = Path(__file__).resolve().parents[1]


def build_cases(observed_at_utc: str) -> dict:
    observed = datetime.fromisoformat(observed_at_utc.replace('Z', '+00:00'))
    if observed.tzinfo is None or observed.utcoffset().total_seconds() != 0:
        raise ValueError('Explicit UTC fixture observation time required')
    row = {'Title': 'SYNTHETIC ACCEPTANCE — grants guard', 'Source': 'SYNTHETIC_ACCEPTANCE',
           'SourceID': 'rims-guard-fixture', 'RoundID': 'round-a',
           'URL': 'https://example.invalid/opportunity',
           'SourceRowURL': 'https://example.invalid/source#fixture-row',
           'EvidenceHash': hashlib.sha256(b'SYNTHETIC ACCEPTANCE grants guard v1').hexdigest(),
           'RetrievedUTC': observed_at_utc, 'RetrievedTimestampStatus': 'valid',
           'DeadlinePrecision': 'unknown', 'Status': 'Unknown', 'CHHHSRelevance': 'Unknown',
           'ReviewStatus': 'Reviewed', 'ReviewNotes': 'SYNTHETIC ACCEPTANCE ONLY',
           'DeadlineTimezone': '', 'DeadlineLocalTime': '', 'DeadlineUTCInstant': '',
           'DeadlineBrisbaneDate': '', 'DeadlineBrisbaneTime': '', 'DeadlineTemporalStatus': 'unknown'}
    row['OpportunityKey'] = stable_key(row)
    cases = []
    def add(name, payload, *, prior, result, writes, diagnostic=None):
        cases.append({'case': name, 'requires_fixture': prior, 'rows': [copy.deepcopy(payload)],
                      'expected_run_status': result, 'expected_write_count': writes,
                      'expected_diagnostic': diagnostic,
                      'expected_create_review': {'ReviewStatus': 'Needs Review', 'ReviewNotes': ''},
                      'requires_full_before_after_snapshot': True,
                      'unrelated_rows_and_versions_must_be_unchanged': True})
    add('create', row, prior=False, result='Succeeded', writes=1)
    add('same_key_replay', row, prior=True, result='Succeeded', writes=1)
    updated = copy.deepcopy(row)
    updated['Title'] = 'SYNTHETIC ACCEPTANCE — updated grants guard'
    updated['EvidenceHash'] = hashlib.sha256(b'SYNTHETIC ACCEPTANCE grants guard v2').hexdigest()
    updated['RetrievedUTC'] = (observed + timedelta(seconds=1)).isoformat()
    add('changed_source_update', updated, prior=True, result='Succeeded', writes=1)
    collision = copy.deepcopy(updated)
    collision['RoundID'] = 'round-b'
    collision['OpportunityKey'] = stable_key(collision)
    add('source_evidence_conflict', collision, prior=True, result='Failed', writes=0,
        diagnostic='CONFLICTING_OPPORTUNITY_KEY_FOR_SOURCE_EVIDENCE')
    for field in ('OpportunityKey', 'Source', 'SourceID', 'EvidenceHash'):
        invalid = copy.deepcopy(updated)
        invalid[field] = '   '
        add('blank_' + field, invalid, prior=True, result='Failed', writes=0,
            diagnostic='INVALID_GRANTS_SOURCE_IDENTITY')
    older = copy.deepcopy(updated)
    older['RetrievedUTC'] = (observed - timedelta(seconds=1)).isoformat()
    add('older_observation', older, prior=True, result='Failed', writes=0,
        diagnostic='OLDER_GRANTS_OBSERVATION')
    uncertain = copy.deepcopy(updated)
    uncertain['RetrievedUTC'] = observed.replace(tzinfo=None).isoformat()
    add('missing_timezone_observation', uncertain, prior=True, result='Failed', writes=0,
        diagnostic='UNCERTAIN_GRANTS_OBSERVATION_TIME')
    malformed = copy.deepcopy(updated)
    malformed['RetrievedUTC'] = 'invalid-dateZ'
    add('malformed_observation', malformed, prior=True, result='Failed', writes=0)
    quoted = copy.deepcopy(row)
    quoted['SourceID'] = "rims-guard-fixture-o'brien"
    quoted['OpportunityKey'] = stable_key(quoted)
    add('quoted_source_identity_create', quoted, prior=False, result='Succeeded', writes=1)
    projected = copy.deepcopy(updated)
    projected['RetrievedUTC'] = (observed + timedelta(seconds=2)).isoformat()
    projected.update(DeadlinePrecision='day', DeadlineTimezone='Australia/Sydney',
                     DeadlineLocalTime='00:30:00', DeadlineUTCInstant='2026-10-05T13:30:00Z',
                     DeadlineBrisbaneDate='2026-10-05', DeadlineBrisbaneTime='23:30:00',
                     DeadlineTemporalStatus='zone_resolved')
    add('populated_deadline_update', projected, prior=True, result='Succeeded', writes=1)
    return {'kind': 'SYNTHETIC_GRANTS_RUNTIME_CASES', 'prepared_at_utc': observed_at_utc,
            'native_acceptance': False, 'executed': False,
            'cases': cases,
            'execution_prerequisites': ['parallel data-layer acceptance',
                'specific scoped activation/run authority', 'fresh exact native schema and full row snapshot',
                'fixture identities absent before create', 'preserved verified solution rollback'],
            'acceptance_requirements': ['correlate each request, submitted rows, terminal run and action results',
                'create produces one exact keyed row; replay never creates a second row',
                'update preserves existing ReviewStatus and ReviewNotes',
                'replay may create a new SharePoint version; do not claim a no-write replay',
                'zero-write cases preserve every row and version',
                'reconcile typed source fields and all six deadline fields without invented precision',
                'remove only scoped synthetic fixtures with restorable rollback and exact key-set readback',
                'restore original Off state'],
            'deferred_cases': ['multiple existing matches requires separate isolated target; preserve uniqueness',
                'cross-run concurrency requires separate native proof'],
            'rollback_fixture_keys': [row['OpportunityKey'], quoted['OpportunityKey']]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT / 'private' / 'ops').resolve()):
        parser.error('Output must remain under private/ops/')
    packet = build_cases(datetime.now(timezone.utc).isoformat())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(packet, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(f"Prepared {len(packet['cases'])} synthetic cases; executed=False native_acceptance=False")


if __name__ == '__main__':
    main()
