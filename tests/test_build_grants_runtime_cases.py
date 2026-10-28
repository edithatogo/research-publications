# SPDX-License-Identifier: Apache-2.0
import unittest
from scripts.build_grants_runtime_cases import build_cases
from scripts.grants_registry import stable_key

def cases():
    return {case['case']: case for case in build_cases('2026-10-05T00:00:00Z')['cases']}

class RuntimeCaseTests(unittest.TestCase):

    def test_replay_and_update_keep_identity_but_source_changes(self):
        c = cases()
        original = c['create']['rows'][0]
        replay = c['same_key_replay']['rows'][0]
        updated = c['changed_source_update']['rows'][0]
        self.assertEqual(original, replay)
        self.assertTrue(original['OpportunityKey'] == updated['OpportunityKey'] == stable_key(updated))
        self.assertNotEqual(original['EvidenceHash'], updated['EvidenceHash'])
        self.assertEqual(c['same_key_replay']['expected_write_count'], 1)

    def test_conflict_is_a_valid_different_key_with_same_source_evidence(self):
        c = cases()
        updated = c['changed_source_update']['rows'][0]
        conflict = c['source_evidence_conflict']['rows'][0]
        self.assertTrue(conflict['OpportunityKey'] == stable_key(conflict) != updated['OpportunityKey'])
        self.assertTrue(all((conflict[k] == updated[k] for k in ('Source', 'SourceID', 'EvidenceHash'))))
        self.assertEqual(c['source_evidence_conflict']['expected_write_count'], 0)
        self.assertEqual(c['source_evidence_conflict']['expected_run_status'], 'Failed')

    def test_blank_failures_are_independent_and_preserve_all_rows_and_versions(self):
        c = cases()
        for field in ('OpportunityKey', 'Source', 'SourceID', 'EvidenceHash'):
            case = c['blank_' + field]
            self.assertEqual(case['rows'][0][field], '   ')
            self.assertEqual(case['expected_run_status'], 'Failed')
            self.assertEqual(case['expected_write_count'], 0)
            self.assertTrue(case['unrelated_rows_and_versions_must_be_unchanged'])
        self.assertEqual(c['changed_source_update']['rows'][0]['Source'], 'SYNTHETIC_ACCEPTANCE')

    def test_quoted_fixture_is_separate_and_all_outputs_are_unexecuted(self):
        packet = build_cases('2026-10-05T00:00:00Z')
        self.assertTrue(not packet['executed'] and (not packet['native_acceptance']))
        self.assertEqual(len(packet['cases']), 13)
        c = cases()
        quoted = c['quoted_source_identity_create']['rows'][0]
        self.assertIn("'", quoted['SourceID'])
        self.assertNotEqual(quoted['OpportunityKey'], c['create']['rows'][0]['OpportunityKey'])
        self.assertEqual(len(set(packet['rollback_fixture_keys'])), 2)

    def test_fixture_choice_values_and_native_create_review_defaults(self):
        row = cases()['create']['rows'][0]
        self.assertEqual(row['RetrievedTimestampStatus'], 'valid')
        self.assertTrue(row['DeadlineTemporalStatus'] == row['DeadlinePrecision'] == 'unknown')
        self.assertTrue(row['Status'] == row['CHHHSRelevance'] == 'Unknown')
        self.assertEqual(cases()['create']['expected_create_review'], {'ReviewStatus': 'Needs Review', 'ReviewNotes': ''})

    def test_older_uncertain_and_malformed_cases_preserve_rows_and_distinct_urls(self):
        c = cases()
        for name in ('older_observation', 'missing_timezone_observation', 'malformed_observation'):
            self.assertEqual(c[name]['expected_write_count'], 0)
            self.assertEqual(c[name]['expected_run_status'], 'Failed')
        row = c['create']['rows'][0]
        self.assertNotEqual(row['URL'], row['SourceRowURL'])
        self.assertIn('#fixture-row', row['SourceRowURL'])

    def test_populated_deadline_covers_midnight_conversion_without_new_identity(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        c = cases()
        row = c['populated_deadline_update']['rows'][0]
        source = datetime.fromisoformat('2026-10-06T00:30:00+11:00')
        brisbane = source.astimezone(ZoneInfo('Australia/Brisbane'))
        self.assertEqual(row['DeadlineTimezone'], 'Australia/Sydney')
        self.assertEqual(row['DeadlineLocalTime'], '00:30:00')
        self.assertEqual(row['DeadlineUTCInstant'], source.astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z'))
        self.assertTrue(row['DeadlineBrisbaneDate'] == brisbane.date().isoformat() == '2026-10-05')
        self.assertTrue(row['DeadlineBrisbaneTime'] == brisbane.time().isoformat() == '23:30:00')
        self.assertEqual(row['OpportunityKey'], c['changed_source_update']['rows'][0]['OpportunityKey'])
        self.assertIs(c['populated_deadline_update']['requires_fixture'], True)

    def test_requires_explicit_utc_case_1(self):
        time = '2026-10-05T00:00:00'
        with self.assertRaises(ValueError):
            build_cases(time)

    def test_requires_explicit_utc_case_2(self):
        time = '2026-10-05T10:00:00+10:00'
        with self.assertRaises(ValueError):
            build_cases(time)

    def test_changed_and_populated_fixture_observations_follow_initial_capture(self):
        c = cases()
        self.assertEqual(c['create']['rows'][0]['RetrievedUTC'], '2026-10-05T00:00:00Z')
        self.assertEqual(c['changed_source_update']['rows'][0]['RetrievedUTC'], '2026-10-05T00:00:01+00:00')
        self.assertEqual(c['populated_deadline_update']['rows'][0]['RetrievedUTC'], '2026-10-05T00:00:02+00:00')
        self.assertEqual(c['same_key_replay']['rows'][0], c['create']['rows'][0])
