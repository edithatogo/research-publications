import hashlib
import json
import unittest
from scripts.ardc_activity_context import build


class ActivityContextTests(unittest.TestCase):
    def test_retained_context_preserves_nulls_and_separates_candidates(self):
        record = {'id': '12', 'key': 'original/key', 'title': 'CHHHS activity', 'amount': None}
        raw = json.dumps({'status': 'OK', 'code': 200, 'data': {'offset': 0, 'numFound': 1, 'records': [record]}}).encode()
        digest = hashlib.sha256(raw).hexdigest()
        reconciliation = json.dumps({'stored_generation_reconciled': True, 'activities': [{'id': '12', 'key': 'original/key'}], 'manifest_sha256': 'a'*64}).encode()
        native = {'format': 'ardc-bounded-increment-native-delivery-v1', 'exact_bytes_verified': True, 'sha256': digest, 'bytes': len(raw), 'records': 1, 'target': {'site': 'https://example.sharepoint.com/sites/Research', 'folder': '/Documents/Archive'}, 'name': 'activities-batch-000000000.json'}
        capture = {'exact_ids_and_source_keys_verified': True, 'response_sha256': digest, 'records': 1, 'source_reconciliation_sha256': hashlib.sha256(reconciliation).hexdigest(), 'manifest_sha256': 'a'*64, 'captured_at': '2026-10-29T00:00:00Z'}
        aliases = json.dumps({'units': [{'OrganisationKey': 'test', 'Aliases': ['CHHHS']}]}).encode()
        row = build(raw, native, capture, reconciliation, aliases, b'not-in-response')[0]
        self.assertEqual(row['ContextKind'], 'research_activity_candidate')
        self.assertEqual(row['RelatedID'], '')
        self.assertNotIn('OperatorNotes', row)
        self.assertIsNone(json.loads(row['SourceProjectionJSON'])['activity']['amount'])
        self.assertFalse(json.loads(row['SourceProvenanceJSON'])['source_complete_verified'])
        with self.assertRaises(ValueError):
            build(raw + b' ', native, capture, reconciliation, aliases, b'not-in-response')

        for name in ('', 'batch.json', '../activities-batch-000000000.json'):
            with self.assertRaisesRegex(ValueError, 'filename'):
                build(raw, {**native, 'name': name}, capture, reconciliation, aliases, b'not-in-response')
