# SPDX-License-Identifier: Apache-2.0
"""Verified delivery to the existing RIMS consumer; no native calls."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from scripts.prepare_funding_relationship_context import prepare, prepare_consumer
from scripts.connect_g06_rims import consumer_from_delivery


def fixture():
    from tests.test_funding_relationship_context import FundingContextTests
    packet = prepare(*FundingContextTests().inputs())
    row = {**packet['relationships'][0], 'Id': 3,
           'EvidenceURL': {'Url': packet['relationships'][0]['EvidenceURL']},
           '__metadata': {'etag': '"7"'}}
    receipt = {'kind': 'g06-incremental-delivered-v1', 'native_verified': True,
               'state': {'sources': {'arc': {'sha256': 'a' * 64, 'packet': packet}}},
               'native': {'native_verified': True, 'current_rows': [row], 'at': '2026-10-29T07:20:00Z'},
               'coverage': {'source_complete_claim': False, 'candidate_keys': 1}}
    baseline = prepare_consumer({'complete': True, 'list': {'ItemCount': 1}, 'items': [row]}, packet)
    return receipt, baseline


class RimsConnectionTests(unittest.TestCase):
    def test_unchanged_material_preserves_counts_and_provenance(self):
        receipt, baseline = fixture(); before = copy.deepcopy((receipt, baseline))
        result = consumer_from_delivery(receipt, baseline)
        self.assertEqual((receipt, baseline), before)
        self.assertFalse(result['identity_update_required'])
        self.assertEqual(result['coverage']['native_rows'], 1)
        self.assertEqual(result['coverage']['candidates'], 1)
        self.assertEqual(result['coverage']['confirmed_reviewed'], 0)
        self.assertEqual(result['rows'][0]['NativeETag'], '"7"')
        self.assertEqual(result['source_provenance'][0]['packet_sha256'], 'a' * 64)
        self.assertFalse(result['live_refresh_verified'])
        self.assertFalse(result['native_model_modified'])

    def test_native_withdrawal_overrides_cached_review(self):
        receipt, baseline = fixture();receipt['native']['current_rows'][0]['ReviewStatus'] = ' Withdrawn '
        result = consumer_from_delivery(receipt, baseline)
        self.assertEqual(result['rows'][0]['ReviewStatusRaw'], ' Withdrawn ')
        self.assertEqual(result['rows'][0]['AdmissionState'], 'unclassified')
        self.assertFalse(result['identity_update_required'])

    def test_pending_or_unverified_receipt_rejected(self):
        receipt, _ = fixture();receipt['kind'] = 'g06-incremental-prepared-v1'
        with self.assertRaisesRegex(ValueError, 'native-verified'): consumer_from_delivery(receipt)
        receipt, _ = fixture();receipt['native']['native_verified'] = False
        with self.assertRaisesRegex(ValueError, 'native-verified'): consumer_from_delivery(receipt)

    def test_native_stage_can_prepare_consumer_without_claiming_model_deployment(self):
        receipt, baseline = fixture();receipt['kind'] = 'g06-native-delivery-verified-v1'
        result = consumer_from_delivery(receipt, baseline)
        self.assertFalse(result['native_acceptance'])
        self.assertFalse(result['native_model_modified'])
        self.assertFalse(result['live_refresh_verified'])

    def test_unknown_rows_retained_and_duplicate_context_collapsed(self):
        receipt, baseline = fixture()
        receipt['state']['sources']['other'] = copy.deepcopy(receipt['state']['sources']['arc'])
        receipt['native']['current_rows'].append({**receipt['native']['current_rows'][0], 'Id': 4,
                                                'RelationshipKey': 'REL:unknown', 'ToKey': 'PUB:unmapped'})
        result = consumer_from_delivery(receipt, baseline)
        self.assertEqual(result['coverage']['native_rows'], 2)
        self.assertEqual(result['coverage']['unresolved_identity'], 1)
        self.assertEqual(result['coverage']['candidates'], 1)
        self.assertEqual(len(result['source_provenance']), 2)
        self.assertFalse(result['identity_update_required'])

    def test_changed_evidence_requires_update_without_admission(self):
        receipt, baseline = fixture();receipt['native']['current_rows'][0]['EvidenceURL'] = {'Url': 'https://example.org/changed'}
        result = consumer_from_delivery(receipt, baseline)
        self.assertTrue(result['identity_update_required'])
        self.assertEqual(result['coverage']['candidates'], 0)
        self.assertEqual(result['coverage']['unclassified'], 1)

    def test_absent_baseline_is_not_current_model_proof(self):
        receipt, _ = fixture()
        self.assertIsNone(consumer_from_delivery(receipt)['identity_update_required'])
        receipt['state']['sources'] = {}
        with self.assertRaisesRegex(ValueError, 'Source provenance'): consumer_from_delivery(receipt)

    def test_cli_private_exclusive_output_and_pending_refusal(self):
        root = Path(__file__).resolve().parents[1];private = root / 'private/ops';private.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private) as folder:
            folder = Path(folder);receipt, _ = fixture();source = folder / 'receipt.json';source.write_text(json.dumps(receipt));output = folder / 'consumer.json'
            command = [sys.executable, 'scripts/connect_g06_rims.py', '--processing-receipt', str(source), '--output', str(output)]
            result = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(os.stat(output).st_mode & 0o777, 0o600)
            original = output.read_bytes();self.assertNotEqual(subprocess.run(command, cwd=root, capture_output=True).returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            receipt['native_verified'] = False;source.write_text(json.dumps(receipt));command[-1] = str(folder / 'pending.json')
            self.assertNotEqual(subprocess.run(command, cwd=root, capture_output=True).returncode, 0)
            self.assertFalse((folder / 'pending.json').exists())


if __name__ == '__main__': unittest.main()
