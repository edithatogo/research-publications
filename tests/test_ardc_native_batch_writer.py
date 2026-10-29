import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from scripts.ardc_native_batch_writer import ROOT, make_writer


class NativeBatchWriterTests(unittest.TestCase):
    def test_capture_callback_builds_checked_private_plan_for_exact_batch(self):
        with tempfile.TemporaryDirectory(prefix='ardc-plan-test-', dir=ROOT / 'private/ops') as tmp:
            base = Path(tmp)
            site = 'https://example.sharepoint.com/sites/Research'
            folder = '/Documents/Archive/Activities'
            binding = {'resources': ['https://example.sharepoint.com'],
                       'ardcActivitiesArchiveTarget': {'site': site, 'folder': folder}}
            binding_path = base / 'binding.json'
            binding_path.write_text(json.dumps(binding))
            identities = [{'id': '10', 'key': 'k'}]
            overlay = {'generation_lineage_verified': True, 'activities': identities}
            raw = json.dumps({'status': 'OK', 'code': 200, 'data': {'numFound': 1, 'offset': 0,
                                                                     'records': identities}}).encode()
            calls = []
            def fake_run(command, **kwargs):
                calls.append(command)
                plan = json.loads(Path(command[3]).read_bytes())
                self.assertEqual(plan['identities'], identities)
                self.assertEqual((Path(command[3]).parent / command[4]).read_bytes(), raw)
                return SimpleNamespace(returncode=0)
            put = make_writer(overlay, b'credential', binding_path, base, run=fake_run)
            put('activities-batch-000000000.json', raw)
            self.assertEqual(len(calls), 1)
            staged = Path(calls[0][3]).parent / calls[0][4]
            with self.assertRaisesRegex(ValueError, 'preserve'):
                put.cleanup_verified('activities-batch-000000000.json', raw + b' ')
            self.assertTrue(staged.exists())
            put.cleanup_verified('activities-batch-000000000.json', raw)
            self.assertFalse(staged.exists())
            with self.assertRaises(ValueError):
                put('activities-batch-000000001.json', raw)
            self.assertEqual(len(calls), 1)
