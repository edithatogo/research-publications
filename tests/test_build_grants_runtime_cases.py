# SPDX-License-Identifier: Apache-2.0
import pytest

from scripts.build_grants_runtime_cases import build_cases
from scripts.grants_registry import stable_key


def cases():
    return {case['case']: case for case in build_cases('2026-10-05T00:00:00Z')['cases']}


def test_replay_and_update_keep_identity_but_source_changes():
    c = cases()
    original = c['create']['rows'][0]
    replay = c['same_key_replay']['rows'][0]
    updated = c['changed_source_update']['rows'][0]
    assert original == replay
    assert original['OpportunityKey'] == updated['OpportunityKey'] == stable_key(updated)
    assert original['EvidenceHash'] != updated['EvidenceHash']
    assert c['same_key_replay']['expected_write_count'] == 1


def test_conflict_is_a_valid_different_key_with_same_source_evidence():
    c = cases()
    updated = c['changed_source_update']['rows'][0]
    conflict = c['source_evidence_conflict']['rows'][0]
    assert conflict['OpportunityKey'] == stable_key(conflict) != updated['OpportunityKey']
    assert all(conflict[k] == updated[k] for k in ('Source', 'SourceID', 'EvidenceHash'))
    assert c['source_evidence_conflict']['expected_write_count'] == 0
    assert c['source_evidence_conflict']['expected_run_status'] == 'Failed'


def test_blank_failures_are_independent_and_preserve_all_rows_and_versions():
    c = cases()
    for field in ('OpportunityKey', 'Source', 'SourceID', 'EvidenceHash'):
        case = c['blank_' + field]
        assert case['rows'][0][field] == '   '
        assert case['expected_run_status'] == 'Failed'
        assert case['expected_write_count'] == 0
        assert case['unrelated_rows_and_versions_must_be_unchanged']
    assert c['changed_source_update']['rows'][0]['Source'] == 'SYNTHETIC_ACCEPTANCE'


def test_quoted_fixture_is_separate_and_all_outputs_are_unexecuted():
    packet = build_cases('2026-10-05T00:00:00Z')
    assert not packet['executed'] and not packet['native_acceptance']
    assert len(packet['cases']) == 13
    c = cases()
    quoted = c['quoted_source_identity_create']['rows'][0]
    assert "'" in quoted['SourceID']
    assert quoted['OpportunityKey'] != c['create']['rows'][0]['OpportunityKey']
    assert len(set(packet['rollback_fixture_keys'])) == 2


def test_fixture_choice_values_and_native_create_review_defaults():
    row = cases()['create']['rows'][0]
    assert row['RetrievedTimestampStatus'] == 'valid'
    assert row['DeadlineTemporalStatus'] == row['DeadlinePrecision'] == 'unknown'
    assert row['Status'] == row['CHHHSRelevance'] == 'Unknown'
    assert cases()['create']['expected_create_review'] == {'ReviewStatus': 'Needs Review', 'ReviewNotes': ''}


def test_older_uncertain_and_malformed_cases_preserve_rows_and_distinct_urls():
    c = cases()
    for name in ('older_observation', 'missing_timezone_observation', 'malformed_observation'):
        assert c[name]['expected_write_count'] == 0
        assert c[name]['expected_run_status'] == 'Failed'
    row = c['create']['rows'][0]
    assert row['URL'] != row['SourceRowURL']
    assert '#fixture-row' in row['SourceRowURL']


def test_populated_deadline_covers_midnight_conversion_without_new_identity():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    c = cases()
    row = c['populated_deadline_update']['rows'][0]
    source = datetime.fromisoformat('2026-10-06T00:30:00+11:00')
    brisbane = source.astimezone(ZoneInfo('Australia/Brisbane'))
    assert row['DeadlineTimezone'] == 'Australia/Sydney'
    assert row['DeadlineLocalTime'] == '00:30:00'
    assert row['DeadlineUTCInstant'] == source.astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z')
    assert row['DeadlineBrisbaneDate'] == brisbane.date().isoformat() == '2026-10-05'
    assert row['DeadlineBrisbaneTime'] == brisbane.time().isoformat() == '23:30:00'
    assert row['OpportunityKey'] == c['changed_source_update']['rows'][0]['OpportunityKey']
    assert c['populated_deadline_update']['requires_fixture'] is True


@pytest.mark.parametrize('time', ['2026-10-05T00:00:00', '2026-10-05T10:00:00+10:00'])
def test_requires_explicit_utc(time):
    with pytest.raises(ValueError):
        build_cases(time)


def test_changed_and_populated_fixture_observations_follow_initial_capture():
    c=cases()
    assert c['create']['rows'][0]['RetrievedUTC']=='2026-10-05T00:00:00Z'
    assert c['changed_source_update']['rows'][0]['RetrievedUTC']=='2026-10-05T00:00:01+00:00'
    assert c['populated_deadline_update']['rows'][0]['RetrievedUTC']=='2026-10-05T00:00:02+00:00'
    assert c['same_key_replay']['rows'][0]==c['create']['rows'][0]
