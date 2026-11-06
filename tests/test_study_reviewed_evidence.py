"""Fictional reviewed-study integration and drift/cardinality boundaries."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.source_capture_receipt import PRIVATE_ROOT
from scripts.study_explorer import explore_dora, render
from scripts.study_reviewed_evidence import load_review
from tests.test_dora_study_projection import envelope


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class StudyReviewedEvidenceTests(unittest.TestCase):
    def setUp(self):
        PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=PRIVATE_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = json.dumps(envelope()).encode()
        page = {'response': {'statusCode': 200, 'body': {'studies': [
            {'protocolSection': {'identificationModule': {'nctId': 'NCT00000001'}}},
            {'protocolSection': {'identificationModule': {'nctId': 'NCT00000002'}}}]}}}
        self.registry = self.root/'registry.json'
        payload = json.dumps(page).encode()
        self.registry.write_bytes(payload)
        self.key = 'dora-activity:fixture-resource:1'
        association = {'source_key': self.key, 'review_status': 'Reviewed',
                       'involvement': 'conducting_site', 'evidence_url': 'https://example.invalid/source',
                       'ppg_evidence_urls': []}
        proof = {'basis': 'source_reported_site', 'source_field': 'Site Name', 'source_value': 'CHHHS',
                 'source_observed_at': '2026-11-06T00:00:00Z', 'source_receipt_sha256': 'a'*64,
                 'facilities_contract_sha256': 'b'*64, 'matched_facility_keys': ['fixture-site']}
        confirmed = {'source_key': self.key, 'registry_key': 'clinicaltrials.gov:NCT00000001',
                     'registry_url': 'https://clinicaltrials.gov/study/NCT00000001', 'decision': 'confirmed',
                     'basis': 'Reviewed multiple fields, not title alone',
                     'corroboration': ['Distinctive protocol', 'Independent design/population evidence'],
                     'differences': ['Source site absent from registry; <script>example</script>'],
                     'review_scope': 'Fictional local review; no current activity claim',
                     'registry_evidence': {'file': str(self.registry), 'sha256': digest(payload),
                         'locator': 'NCT00000001', 'snapshot_at': '2026-11-06T00:00:00Z', 'last_update_source': None}}
        candidate = copy.deepcopy(confirmed)
        candidate.update(source_key='dora-activity:fixture-resource:2', registry_key='clinicaltrials.gov:NCT00000002',
                         registry_url='https://clinicaltrials.gov/study/NCT00000002', decision='candidate',
                         basis='Weak topic overlap, unconfirmed', corroboration=[])
        candidate['registry_evidence']['locator'] = 'NCT00000002'
        self.packet = {'schema_version': 1, 'capture_sha256': digest(self.raw), 'review_id': 'fictional-review',
                       'scope': 'Source-specific reviewed identity assertions', 'associations': [association],
                       'association_evidence': {self.key: proof}, 'registry_decisions': [confirmed, candidate]}

    def view(self, packet=None, **filters):
        packet = self.packet if packet is None else packet
        raw = json.dumps(packet).encode()
        loaded = load_review(raw, digest(raw))
        return explore_dora(self.raw, digest(self.raw), associations=loaded['associations'],
                            reviewed_evidence=loaded, **filters)

    def test_reviewed_and_ambiguous_links_preserve_counts_source_values_and_visible_differences(self):
        result = self.view()
        self.assertEqual(result['capture_records'], 3)
        self.assertEqual(result['selected_records'], 3)
        confirmed = result['views']['chhhs_associated'][0]
        self.assertIsNone(confirmed['OverallStatus'])
        self.assertEqual(confirmed['RegistryLinks'][0]['decision'], 'confirmed')
        candidate = next(row for row in result['views']['external_discovery'] if row['SourceKey'].endswith(':2'))
        self.assertEqual(candidate['RegistryLinks'][0]['decision'], 'candidate')
        document = render(result)
        self.assertIn('Reviewed identity match', document)
        self.assertIn('Unconfirmed candidate', document)
        self.assertIn('&lt;script&gt;', document)
        self.assertNotIn('<script>', document)
        self.assertIn('Source-reported site', document)

    def test_filtered_view_retains_full_domain_validation_without_promoting_candidates(self):
        result = self.view(study_type='Clinical trial')
        self.assertEqual(result['selected_records'], 1)
        self.assertEqual(result['views']['external_discovery'], [])
        self.assertEqual(result['review_id'], 'fictional-review')

    def test_hash_snapshot_site_and_payload_drift_refused(self):
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            load_review(json.dumps(self.packet).encode(), '0'*64)
        for field, value, message in [('capture_sha256', '0'*64, 'different study capture'),
                                      ('association_evidence', {}, 'source evidence')]:
            packet = copy.deepcopy(self.packet)
            packet[field] = value
            with self.assertRaisesRegex(ValueError, message):
                self.view(packet)
        packet = copy.deepcopy(self.packet)
        packet['association_evidence'][self.key]['source_value'] = 'Different site'
        with self.assertRaisesRegex(ValueError, 'source site differs'):
            self.view(packet, study_type='Non-trial activity (clinical scope unverified)')
        self.registry.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'payload hash mismatch'):
            self.view()

    def test_duplicate_orphan_wrong_registry_and_update_claims_refused(self):
        for change, message in [('duplicate', 'Duplicate or conflicting'), ('orphan', 'absent from capture'),
                                ('identity', 'absent from pinned'), ('update', 'update metadata differs'),
                                ('namespace', 'Qualified retained')]:
            packet = copy.deepcopy(self.packet)
            if change == 'duplicate':
                packet['registry_decisions'].append(copy.deepcopy(packet['registry_decisions'][0]))
            elif change == 'orphan':
                packet['registry_decisions'][0]['source_key'] = 'dora-activity:missing:99'
            elif change == 'identity':
                packet['registry_decisions'][0].update(registry_key='clinicaltrials.gov:NCT00000009',
                    registry_url='https://clinicaltrials.gov/study/NCT00000009')
                packet['registry_decisions'][0]['registry_evidence']['locator'] = 'NCT00000009'
            elif change == 'namespace':
                packet['registry_decisions'][0]['registry_key'] = 'clinicaltrialsXgov:NCT00000001'
            else:
                packet['registry_decisions'][0]['registry_evidence']['last_update_source'] = {'date': '2026-11-06'}
            with self.assertRaisesRegex(ValueError, message):
                self.view(packet)

    def test_cli_populates_view_and_rejects_stale_packet_before_output(self):
        data = envelope()
        records = data.pop('records')
        receipt = json.dumps(data).encode()
        (self.root/'receipt.json').write_bytes(receipt)
        (self.root/'records.json').write_text(json.dumps(records))
        self.packet['association_evidence'][self.key]['source_receipt_sha256'] = digest(receipt)
        self.packet['capture_sha256'] = digest(json.dumps({**data, 'records': records}, ensure_ascii=False, allow_nan=False).encode())
        # CLI combines the original receipt and records with the same JSON serialization.
        raw = json.dumps(self.packet).encode()
        (self.root/'review.json').write_bytes(raw)
        output = self.root/'output'
        command = [sys.executable, '-m', 'scripts.study_explorer', '--dora-directory', str(self.root),
                   '--sha256', digest(receipt), '--reviewed-evidence', str(self.root/'review.json'),
                   '--reviewed-evidence-sha256', digest(raw), '--output', str(output)]
        completed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads((output/'study-explorer.json').read_text())
        self.assertEqual(result['reviewed_evidence_sha256'], digest(raw))
        self.assertEqual(result['views']['chhhs_associated'][0]['RegistryLinks'][0]['decision'], 'confirmed')
        (self.root/'review.json').write_text('{}')
        command[-1] = str(self.root/'stale-output')
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertFalse((self.root/'stale-output').exists())
