import hashlib
import json
import unittest

from scripts.ardc_generation_lineage import overlay_verified_lineage


class LineageTests(unittest.TestCase):
    def fixture(self):
        scope = 'a' * 64
        baseline = {'source': 'ardc', 'complete': True, 'full_reconciliation': True,
                    'scope_sha256': scope, 'until': '2026-10-18T00:00:00Z',
                    'baseline_completed_at': '2026-10-18T00:00:00Z'}
        incremental = {'source': 'ardc', 'complete': True, 'full_reconciliation': False,
                       'scope_sha256': scope, 'until': '2026-10-25T00:00:00Z',
                       'baseline_completed_at': '2026-10-18T00:00:00Z'}
        raw_a, raw_b = json.dumps(baseline).encode(), json.dumps(incremental).encode()
        result_a = {'stored_generation_reconciled': True, 'full_reconciliation': True,
                    'manifest_sha256': hashlib.sha256(raw_a).hexdigest(), 'until': baseline['until'],
                    'records': 1, 'ids': ['1'], 'activities': [{'id': '1', 'key': 'a'}], 'tombstones': []}
        result_b = {'stored_generation_reconciled': True, 'full_reconciliation': False,
                    'manifest_sha256': hashlib.sha256(raw_b).hexdigest(), 'until': incremental['until'],
                    'from': '2026-10-15T00:00:00Z', 'records': 1, 'ids': ['1'],
                    'activities': [{'id': '1', 'key': 'b'}], 'tombstones': []}
        return result_a, result_b, raw_a, raw_b

    def test_verified_lineage_produces_tentative_overlay(self):
        result = overlay_verified_lineage(*self.fixture())
        self.assertTrue(result['generation_lineage_verified'])
        self.assertEqual(result['activities'], [{'id': '1', 'key': 'b'}])
        self.assertFalse(result['current_provider_snapshot_verified'])

    def test_modified_manifest_and_unrelated_baseline_are_rejected(self):
        a, b, raw_a, raw_b = self.fixture()
        with self.assertRaisesRegex(ValueError, 'hash'):
            overlay_verified_lineage(a, b, raw_a + b' ', raw_b)
        other = json.loads(raw_b)
        other['baseline_completed_at'] = '2026-10-17T00:00:00Z'
        changed = json.dumps(other).encode()
        b['manifest_sha256'] = hashlib.sha256(changed).hexdigest()
        with self.assertRaisesRegex(ValueError, 'lineage'):
            overlay_verified_lineage(a, b, raw_a, changed)


if __name__ == '__main__':
    unittest.main()
