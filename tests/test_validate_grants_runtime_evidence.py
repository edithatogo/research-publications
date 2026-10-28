# SPDX-License-Identifier: Apache-2.0
import unittest
import copy
import hashlib
import json
from scripts.build_grants_runtime_cases import build_cases
from scripts.validate_grants_runtime_evidence import evaluate

def fixture():
    packet = build_cases('2026-10-05T00:00:00Z')
    target = dict(environment='fixture', flow='fixture', site='fixture', list='fixture')
    evidence = dict(packet_sha256=hashlib.sha256(json.dumps(packet, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), target=target, data_layer_accepted=True, run_authorization_reference='fixture-only', rollback_reference='fixture-only', final_flow_state='Off', baseline_rows=[], cleanup_rows=[], cleanup_complete=True, cleanup_reference='fixture-only', cases=[])
    rows = []
    for i, case in enumerate(packet['cases']):
        before = copy.deepcopy(rows)
        if case['expected_write_count']:
            payload = case['rows'][0]
            existing = next((r for r in rows if r['OpportunityKey'] == payload['OpportunityKey']), None)
            if existing:
                existing.update({k: v for k, v in payload.items() if k not in ('ReviewStatus', 'ReviewNotes')})
                existing['versions'].append({'version': str(i + 1)})
            else:
                created = dict(payload, ID=len(rows) + 1, versions=[{'version': str(i + 1)}])
                created.update(case['expected_create_review'])
                rows.append(created)
        evidence['cases'].append(dict(case=case['case'], target=target, run_id=str(i), request_reference='fixture-only', action_reference='fixture-only', submitted_rows=case['rows'], run_status=case['expected_run_status'], write_count=case['expected_write_count'], diagnostics=[case['expected_diagnostic']], snapshots_complete=True, before_rows=before, after_rows=copy.deepcopy(rows)))
    return (packet, evidence)

class RuntimeEvidenceTests(unittest.TestCase):

    def test_complete_synthetic_evidence_passes_without_claiming_native_acceptance(self):
        packet, evidence = fixture()
        result = evaluate(packet, evidence)
        self.assertEqual(result['status'], 'PASS_RECORDED_EVIDENCE')
        self.assertEqual(result['errors'], [])
        self.assertIs(result['native_acceptance'], False)

    def test_execution_and_cleanup_gates_fail_closed_case_1(self):
        field = 'data_layer_accepted'
        value = False
        message = 'data-layer gate open'
        packet, evidence = fixture()
        evidence[field] = value
        self.assertIn(message, evaluate(packet, evidence)['errors'])

    def test_execution_and_cleanup_gates_fail_closed_case_2(self):
        field = 'final_flow_state'
        value = 'On'
        message = 'original Off state not restored'
        packet, evidence = fixture()
        evidence[field] = value
        self.assertIn(message, evaluate(packet, evidence)['errors'])

    def test_execution_and_cleanup_gates_fail_closed_case_3(self):
        field = 'cleanup_complete'
        value = False
        message = 'cleanup does not restore complete baseline'
        packet, evidence = fixture()
        evidence[field] = value
        self.assertIn(message, evaluate(packet, evidence)['errors'])

    def test_execution_and_cleanup_gates_fail_closed_case_4(self):
        field = 'packet_sha256'
        value = 'wrong'
        message = 'packet fingerprint mismatch'
        packet, evidence = fixture()
        evidence[field] = value
        self.assertIn(message, evaluate(packet, evidence)['errors'])

    def test_rejection_cannot_hide_version_only_write(self):
        packet, evidence = fixture()
        evidence['cases'][3]['after_rows'][0]['versions'].append({'version': 'unintended'})
        self.assertTrue(any(('rejected row changed data or versions' in e for e in evaluate(packet, evidence)['errors'])))

    def test_missing_case_and_reused_run_are_rejected(self):
        packet, evidence = fixture()
        evidence['cases'][1]['run_id'] = evidence['cases'][0]['run_id']
        evidence['cases'].pop()
        errors = evaluate(packet, evidence)['errors']
        self.assertIn('cases missing, duplicated or out of order', errors)
        self.assertTrue(any(('run correlation missing or reused' in e for e in errors)))

    def test_reviewer_change_and_lost_history_are_rejected(self):
        packet, evidence = fixture()
        row = evidence['cases'][2]['after_rows'][0]
        row['ReviewNotes'] = 'overwritten'
        row['versions'] = [{'version': 'replacement'}]
        errors = evaluate(packet, evidence)['errors']
        self.assertTrue(any(('reviewer field changed' in e for e in errors)))
        self.assertTrue(any(('prior versions lost' in e for e in errors)))

    def test_missing_version_history_is_failure_not_a_crash(self):
        packet, evidence = fixture()
        del evidence['cases'][1]['after_rows'][0]['versions']
        self.assertTrue(any(('IDs/version history missing' in e for e in evaluate(packet, evidence)['errors'])))

    def test_sharepoint_url_object_shape_and_provenance_loss(self):
        packet, evidence = fixture()
        for record in evidence['cases']:
            for group in ('before_rows', 'after_rows'):
                for row in record[group]:
                    for field in ('URL', 'SourceRowURL'):
                        row[field] = {'Url': row[field], 'Description': 'synthetic fixture'}
        self.assertEqual(evaluate(packet, evidence)['errors'], [])
        evidence['cases'][0]['after_rows'][0]['SourceRowURL']['Url'] = 'https://example.invalid/wrong'
        self.assertTrue(any(('field mismatch SourceRowURL' in e for e in evaluate(packet, evidence)['errors'])))

    def test_observation_and_deadline_mapping_loss_rejected_case_1(self):
        field = 'RetrievedUTC'
        packet, evidence = fixture()
        del evidence['cases'][0]['after_rows'][0][field]
        self.assertTrue(any(('field mismatch ' + field in e for e in evaluate(packet, evidence)['errors'])))

    def test_observation_and_deadline_mapping_loss_rejected_case_2(self):
        field = 'RetrievedTimestampStatus'
        packet, evidence = fixture()
        del evidence['cases'][0]['after_rows'][0][field]
        self.assertTrue(any(('field mismatch ' + field in e for e in evaluate(packet, evidence)['errors'])))

    def test_observation_and_deadline_mapping_loss_rejected_case_3(self):
        field = 'DeadlinePrecision'
        packet, evidence = fixture()
        del evidence['cases'][0]['after_rows'][0][field]
        self.assertTrue(any(('field mismatch ' + field in e for e in evaluate(packet, evidence)['errors'])))

    def test_observation_and_deadline_mapping_loss_rejected_case_4(self):
        field = 'DeadlineTimezone'
        packet, evidence = fixture()
        del evidence['cases'][0]['after_rows'][0][field]
        self.assertTrue(any(('field mismatch ' + field in e for e in evaluate(packet, evidence)['errors'])))

    def test_observation_and_deadline_mapping_loss_rejected_case_5(self):
        field = 'DeadlineLocalTime'
        packet, evidence = fixture()
        del evidence['cases'][0]['after_rows'][0][field]
        self.assertTrue(any(('field mismatch ' + field in e for e in evaluate(packet, evidence)['errors'])))

    def test_observation_and_deadline_mapping_loss_rejected_case_6(self):
        field = 'DeadlineUTCInstant'
        packet, evidence = fixture()
        del evidence['cases'][0]['after_rows'][0][field]
        self.assertTrue(any(('field mismatch ' + field in e for e in evaluate(packet, evidence)['errors'])))

    def test_observation_and_deadline_mapping_loss_rejected_case_7(self):
        field = 'DeadlineBrisbaneDate'
        packet, evidence = fixture()
        del evidence['cases'][0]['after_rows'][0][field]
        self.assertTrue(any(('field mismatch ' + field in e for e in evaluate(packet, evidence)['errors'])))

    def test_observation_and_deadline_mapping_loss_rejected_case_8(self):
        field = 'DeadlineBrisbaneTime'
        packet, evidence = fixture()
        del evidence['cases'][0]['after_rows'][0][field]
        self.assertTrue(any(('field mismatch ' + field in e for e in evaluate(packet, evidence)['errors'])))

    def test_observation_and_deadline_mapping_loss_rejected_case_9(self):
        field = 'DeadlineTemporalStatus'
        packet, evidence = fixture()
        del evidence['cases'][0]['after_rows'][0][field]
        self.assertTrue(any(('field mismatch ' + field in e for e in evaluate(packet, evidence)['errors'])))

    def test_native_empty_text_and_choice_values_accepted(self):
        packet, evidence = fixture()
        for record in evidence['cases']:
            for group in ('before_rows', 'after_rows'):
                for row in record[group]:
                    for field in ('DeadlineTimezone', 'DeadlineLocalTime', 'DeadlineUTCInstant', 'DeadlineBrisbaneDate', 'DeadlineBrisbaneTime'):
                        if row[field] == '':
                            row[field] = None
                    for field in ('RetrievedTimestampStatus', 'DeadlinePrecision', 'DeadlineTemporalStatus'):
                        row[field] = {'Value': row[field]}
        self.assertEqual(evaluate(packet, evidence)['errors'], [])
        evidence['cases'][0]['after_rows'][0]['DeadlineTemporalStatus'] = {'Value': 'invented'}
        self.assertTrue(any(('field mismatch DeadlineTemporalStatus' in e for e in evaluate(packet, evidence)['errors'])))
