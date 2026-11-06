"""Refresh policy, review quarantine and PPG-reference boundaries using fictional data."""
import copy
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.collect_pubmed import canonical_json
from scripts.dora_study_projection import read_directory
from scripts.refresh_study_registry import reconcile
from scripts.study_explorer import render, explore_dora
import tests.test_study_reviewed_evidence as reviewed_fixtures


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def seal(value):
    value = copy.deepcopy(value)
    rows = value['records']
    value.update(expected_count=len(rows), retrieved_count=len(rows),
                 records_sha256=sha(canonical_json(rows).encode()),
                 record_id_sha256=sha(canonical_json(sorted(str(row['_id']) for row in rows)).encode()))
    return json.dumps(value).encode()


class StudyRefreshTests(unittest.TestCase):
    def setUp(self):
        self.fixture = reviewed_fixtures.StudyReviewedEvidenceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.old = self.fixture.raw
        self.facilities = json.dumps({'rows': [{'FacilityKey': 'fixture-site', 'FacilityName': 'CHHHS'}]}).encode()
        self.packet = copy.deepcopy(self.fixture.packet)
        self.packet['association_evidence'][self.fixture.key]['facilities_contract_sha256'] = sha(self.facilities)
        self.current = json.loads(self.old)
        self.current['observed_at'] = '2026-11-07T00:00:00Z'

    def ppg(self):
        self.packet.update(schema_version=2, refresh_lineage=None, ppg_references=[{
            'source_key': self.fixture.key, 'frameworkKey': 'fixture-framework-v1', 'requirementKey': 'action-1',
            'relationshipScope': 'service', 'receipt': {'sourceId': 'fixture-evidence',
                'canonicalUrl': 'https://example.invalid/ppg/evidence', 'retrievedAtUtc': '2026-11-06T00:00:00Z',
                'nativeUniqueId': 'fixture-native-id', 'nativeVersionRef': '1.0', 'sha256': 'c'*64,
                'authorityLabel': 'captured-reference-unconfirmed', 'status': 'retrieved'}}])

    def refresh(self, current=None, facilities=None, references=None):
        review = json.dumps(self.packet).encode()
        reference = self.facilities if facilities is None else facilities
        current_raw = seal(self.current if current is None else current)
        current_receipt = 'a'*64 if current_raw == self.old else 'd'*64
        return reconcile(self.old, current_raw, 'a'*64, current_receipt,
                         review, sha(review), reference, sha(reference), 'fictional-refresh', ppg_references=references)

    def test_observation_advance_carries_unchanged_reviews_without_renewing_registry_or_ppg_dates(self):
        self.ppg()
        result = self.refresh()
        packet = json.loads(result['next_packet_raw'])
        self.assertEqual(result['summary']['unchanged'], 3)
        self.assertEqual(result['summary']['carried_reviewed_associations'], 1)
        self.assertEqual(result['summary']['review_queue'], 0)
        self.assertEqual(packet['association_evidence'][self.fixture.key]['source_observed_at'], '2026-11-07T00:00:00Z')
        self.assertEqual(packet['registry_decisions'][0]['registry_evidence']['snapshot_at'], '2026-11-06T00:00:00Z')
        self.assertEqual(packet['ppg_references'][0]['receipt']['retrievedAtUtc'], '2026-11-06T00:00:00Z')
        self.assertEqual(packet['refresh_lineage']['previous_review_id'], self.packet['review_id'])
        document = render(result['view'])
        self.assertIn('PPG service reference', document)
        self.assertIn('reference presence is not compliance', document)
        self.assertEqual(result['view']['ppg_reference_count'], 1)
        filtered = explore_dora(seal(self.current), packet['capture_sha256'], associations=packet['associations'],
                                reviewed_evidence=packet, study_type='Non-trial activity (clinical scope unverified)')
        self.assertEqual(filtered['ppg_reference_count'], 0)
        self.assertEqual(filtered['ppg_packet_reference_count'], 1)

    def test_changed_row_quarantines_previous_decisions_and_evidence_but_keeps_candidate_elsewhere(self):
        self.ppg()
        self.current['records'][0]['Full Project Title'] = 'Changed fictional protocol'
        before = copy.deepcopy(self.packet)
        result = self.refresh()
        packet = json.loads(result['next_packet_raw'])
        self.assertEqual(packet['associations'], [])
        self.assertEqual([link['decision'] for link in packet['registry_decisions']], ['candidate'])
        self.assertEqual(len(result['quarantined_review']['registry_decisions']), 1)
        self.assertEqual(len(result['quarantined_review']['ppg_references']), 1)
        self.assertEqual(result['review_queue'][0]['changed_fields'], ['Full Project Title'])
        self.assertNotIn('private@example.invalid', json.dumps(result, default=lambda x: 'bytes'))
        self.assertEqual(self.packet, before)

    def test_source_missing_and_same_project_id_addition_do_not_infer_identity_or_closure(self):
        previous = self.current['records'].pop(0)
        previous['_id'] = 4
        self.current['records'].append(previous)
        result = self.refresh()
        self.assertEqual(result['summary']['source_missing'], 1)
        self.assertEqual(result['summary']['added'], 1)
        self.assertEqual(result['summary']['carried_reviewed_associations'], 0)
        self.assertEqual(len(result['view']['source_history']), 1)
        self.assertIn('not study closure', render(result['view']))
        self.assertTrue(any(item['candidate_site_matches'] for item in result['review_queue']))
        empty = copy.deepcopy(self.current)
        empty['records'] = []
        result = self.refresh(empty)
        self.assertEqual(result['summary']['current_rows'], 0)
        self.assertEqual(result['summary']['source_missing'], 3)
        self.assertEqual(len(result['view']['source_history']), 3)

    def test_replacement_resource_never_reuses_row_number_or_project_id(self):
        self.current['source_payload']['resource']['id'] = 'replacement-resource'
        result = self.refresh()
        self.assertTrue(result['summary']['resource_replaced'])
        self.assertEqual(result['summary']['carried_reviewed_associations'], 0)
        self.assertEqual(result['summary']['source_missing'], 3)
        self.assertEqual(result['summary']['added'], 3)
        self.assertEqual(len(result['quarantined_review']['registry_decisions']), 2)

    def test_out_of_order_scope_and_facility_drift_are_explicit(self):
        stale = copy.deepcopy(self.current)
        stale['observed_at'] = '2026-11-05T00:00:00Z'
        with self.assertRaisesRegex(ValueError, 'Out-of-order'):
            self.refresh(stale)
        different = copy.deepcopy(self.current)
        different['source_payload']['api'] = 'https://example.invalid/different-source'
        with self.assertRaisesRegex(ValueError, 'scope/schema changed'):
            self.refresh(different)
        result = self.refresh(facilities=json.dumps({'rows': [{'FacilityKey': 'new', 'FacilityName': 'Changed name'}]}).encode())
        self.assertEqual(result['summary']['carried_reviewed_associations'], 0)
        self.assertEqual(result['review_queue'][0]['reason'], 'facility_reference_changed')

    def test_denied_unversioned_or_content_bearing_ppg_references_refused(self):
        self.ppg()
        original = copy.deepcopy(self.packet)
        for field, value in [('status', 'denied'), ('nativeVersionRef', ''), ('quote', 'Evidence content must stay in PPG')]:
            self.packet = copy.deepcopy(original)
            self.packet['ppg_references'][0]['receipt'][field] = value
            with self.assertRaises(ValueError):
                self.refresh()

    def test_explicit_ppg_receipts_add_links_without_overwriting_versions_or_promoting_changed_studies(self):
        self.ppg()
        reference = copy.deepcopy(self.packet['ppg_references'][0])
        self.packet['ppg_references'] = []
        result = self.refresh(references=[reference])
        self.assertEqual(result['view']['ppg_reference_count'], 1)
        self.assertIn('PPG service reference', render(result['view']))
        self.packet['ppg_references'] = [reference]
        replay = self.refresh(current=json.loads(self.old), references=[reference])
        self.assertEqual(replay['summary']['outcome'], 'unchanged_replay')
        self.assertEqual(replay['summary']['added_ppg_references'], 0)
        changed = copy.deepcopy(reference)
        changed['receipt']['sha256'] = 'e'*64
        with self.assertRaisesRegex(ValueError, 'metadata changed'):
            self.refresh(references=[changed])
        self.current['records'][0]['Full Project Title'] = 'Changed'
        with self.assertRaisesRegex(ValueError, 'unchanged reviewed CHHHS'):
            self.refresh(references=[reference])

    def test_cli_replay_commit_last_and_overwrite_refusal_preserve_last_good(self):
        root = self.fixture.root
        capture = root/'capture'
        capture.mkdir()
        data = json.loads(self.old)
        records = data.pop('records')
        receipt = json.dumps(data).encode()
        (capture/'receipt.json').write_bytes(receipt)
        (capture/'records.json').write_text(json.dumps(records))
        self.packet['capture_sha256'] = sha(read_directory(capture, sha(receipt)))
        self.packet['association_evidence'][self.fixture.key]['source_receipt_sha256'] = sha(receipt)
        review = json.dumps(self.packet).encode()
        (root/'review.json').write_bytes(review)
        (root/'facilities.json').write_bytes(self.facilities)
        output = root/'maintenance'
        command = [sys.executable, '-m', 'scripts.refresh_study_registry',
            '--previous-directory', str(capture), '--current-directory', str(capture),
            '--previous-receipt-sha256', sha(receipt), '--current-receipt-sha256', sha(receipt),
            '--reviewed-evidence', str(root/'review.json'), '--reviewed-evidence-sha256', sha(review),
            '--facilities', str(root/'facilities.json'), '--facilities-sha256', sha(self.facilities),
            '--revision-id', 'fixture-refresh', '--output', str(output)]
        completed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual((output/'next-reviewed-evidence.json').read_bytes(), review)
        manifest = json.loads((output/'maintenance-manifest.json').read_text())
        for name, metadata in manifest['files'].items():
            self.assertEqual(sha((output/name).read_bytes()), metadata['sha256'])
        self.assertEqual(json.loads((output/'reconciliation.json').read_text())['outcome'], 'unchanged_replay')
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertEqual((capture/'receipt.json').read_bytes(), receipt)
        self.assertEqual((root/'review.json').read_bytes(), review)
        # All source rows may disappear without bypassing the new receipt's byte pin.
        empty = copy.deepcopy(data)
        empty['records'] = []
        empty['observed_at'] = '2026-11-07T00:00:00Z'
        empty = json.loads(seal(empty))
        empty_records = empty.pop('records')
        empty_directory = root/'empty-capture'
        empty_directory.mkdir()
        empty_receipt = json.dumps(empty).encode()
        (empty_directory/'receipt.json').write_bytes(empty_receipt)
        (empty_directory/'records.json').write_text(json.dumps(empty_records))
        empty_command = command.copy()
        empty_command[empty_command.index('--current-directory')+1] = str(empty_directory)
        empty_command[empty_command.index('--current-receipt-sha256')+1] = sha(empty_receipt)
        empty_command[-1] = str(root/'empty-result')
        completed = subprocess.run(empty_command, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads((root/'empty-result/next-reviewed-evidence.json').read_text())['associations'], [])
        empty_command[empty_command.index('--current-receipt-sha256')+1] = '0'*64
        empty_command[-1] = str(root/'wrong-empty-receipt')
        self.assertNotEqual(subprocess.run(empty_command, capture_output=True).returncode, 0)
        self.assertFalse((root/'wrong-empty-receipt').exists())
        references = root/'bad-ppg.json'
        references.write_text('{}')
        invalid = command.copy()
        invalid[-1] = str(root/'invalid-ppg')
        invalid += ['--ppg-references', str(references), '--ppg-references-sha256', sha(references.read_bytes())]
        rejected = subprocess.run(invalid, capture_output=True, text=True)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn('must be a JSON array', rejected.stderr)
