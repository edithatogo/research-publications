import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_ardc_capture_pipeline as runner


class RunnerTests(unittest.TestCase):
    def test_full_runner_saves_receipt_and_secondary_projection(self):
        with tempfile.TemporaryDirectory(prefix='ardc-run-success-', dir=runner.ROOT / 'private/ops') as temp:
            root = Path(temp)
            def file(name, value):
                path = root / name
                path.write_bytes(value)
                return path
            credential = file('key', b'secret-key')
            binding = file('binding.json', b'{}')
            base = file('base.json', b'{}')
            inc = file('increment.json', b'{}')
            bm = file('base-manifest.json', b'{}')
            im = file('increment-manifest.json', b'{}')
            aliases = file('aliases.json', json.dumps({'units': [{'OrganisationKey': 'chhhs',
                                                                  'Aliases': ['CHHHS']}]}).encode())
            identity = {'id': '10', 'key': 'k'}
            record = {**identity, 'title': 'CHHHS project'}
            overlay = {'generation_lineage_verified': True, 'activities': [identity],
                       'baseline_manifest_sha256': 'a' * 64, 'incremental_manifest_sha256': 'b' * 64}
            page = json.dumps({'status': 'OK', 'code': 200, 'data': {'numFound': 1, 'offset': 0,
                                                                     'records': [record]}}).encode()
            saved = {}
            with (patch.object(runner, 'overlay_verified_lineage', return_value=overlay),
                  patch.object(runner, 'verify_shared_binding', return_value={'ardcActivitiesCredentialFile': str(credential)}),
                  patch.object(runner, 'make_archive_io', return_value=(saved.get, saved.__getitem__)),
                  patch.object(runner, 'make_writer', return_value=saved.__setitem__),
                  patch.object(runner, 'activities_fetcher', return_value=lambda *_: page),
                  patch.object(runner, 'lookup_batch', return_value=page)):
                result = runner.run_capture(baseline=base, incremental=inc, baseline_manifest=bm, incremental_manifest=im,
                                            credential=credential, binding=binding, workdir=root / 'job', aliases=aliases)
            self.assertEqual(result['records'], 1)
            self.assertEqual(result['candidates'], 1)
            self.assertTrue((root / 'job/capture-receipt.json').is_file())
            self.assertTrue((root / 'job/partial-projections/activities-batch-000000000.json').is_file())
            self.assertEqual(json.loads((root / 'job/candidate-projection.json').read_bytes())['candidates'][0]['activity_id'], '10')
            self.assertFalse(result['source_complete_verified'])

    def test_count_drift_fails_before_any_native_write(self):
        with tempfile.TemporaryDirectory(prefix='ardc-run-test-', dir=runner.ROOT / 'private/ops') as temp:
            root = Path(temp)
            def file(name, value):
                path = root / name
                path.write_bytes(value)
                return path
            credential = file('key', b'secret-key')
            binding = file('binding.json', json.dumps({'ardcActivitiesCredentialFile': str(credential)}).encode())
            base = file('base.json', b'{}')
            inc = file('increment.json', b'{}')
            bm = file('base-manifest.json', b'{}')
            im = file('increment-manifest.json', b'{}')
            aliases = file('aliases.json', b'{}')
            writes = []
            overlay = {'generation_lineage_verified': True, 'activities': [{'id': '10', 'key': 'k'}],
                       'baseline_manifest_sha256': 'a' * 64, 'incremental_manifest_sha256': 'b' * 64}
            page = json.dumps({'status': 'OK', 'code': 200, 'data': {'numFound': 2, 'offset': 0,
                                                                     'records': [{'id': '10'}]}}).encode()
            with (patch.object(runner, 'overlay_verified_lineage', return_value=overlay),
                  patch.object(runner, 'verify_shared_binding', return_value={'ardcActivitiesCredentialFile': str(credential)}),
                  patch.object(runner, 'make_archive_io', return_value=(lambda _: None, lambda _: b'')),
                  patch.object(runner, 'make_writer', return_value=lambda *args: writes.append(args)),
                  patch.object(runner, 'activities_fetcher', return_value=lambda *_: page)):
                with self.assertRaisesRegex(ValueError, 'total differs'):
                    runner.run_capture(baseline=base, incremental=inc, baseline_manifest=bm, incremental_manifest=im,
                                       credential=credential, binding=binding, workdir=root / 'job', aliases=aliases)
            self.assertEqual(writes, [])
            self.assertFalse((root / 'job/capture-receipt.json').exists())

    def test_archive_binding_must_share_identity_and_lock_directory(self):
        with tempfile.TemporaryDirectory(prefix='ardc-binding-test-', dir=runner.ROOT / 'private/ops') as temp:
            root = Path(temp)
            base = root / 'base.json'
            binding = root / 'derived.json'
            pins = {'sdkRoot': '/sdk', 'sdkVersion': '1', 'connectionName': 'c', 'appId': 'a',
                    'tenantId': 't', 'username': 'u', 'resources': ['r'], 'readUrlPrefixes': ['p']}
            base.write_text(json.dumps(pins))
            binding.write_text(json.dumps({**pins, 'ardcActivitiesArchiveTarget': {}}))
            with patch.object(runner, 'SHARED_BINDING', base):
                self.assertEqual(runner.verify_shared_binding(binding)['appId'], 'a')
                site = 'https://example.sharepoint.com/sites/Research'
                extended = {**pins, 'resources': ['https://example.sharepoint.com']}
                base.write_text(json.dumps(extended))
                target = {'site': site, 'folder': '/Documents/Activities'}
                exact = site + "/_api/web/GetFolderByServerRelativePath(DecodedUrl='/sites/Research/Documents/Activities')"
                candidate = {**extended, 'ardcActivitiesArchiveTarget': target,
                             'readUrlPrefixes': ['p', exact]}
                binding.write_text(json.dumps(candidate))
                self.assertEqual(runner.verify_shared_binding(binding)['readUrlPrefixes'], ['p', exact])
                for prefixes in (['p', site], [exact], ['p', exact, 'https://other.example']):
                    binding.write_text(json.dumps({**candidate, 'readUrlPrefixes': prefixes}))
                    with self.assertRaisesRegex(ValueError, 'read scope'):
                        runner.verify_shared_binding(binding)
                base.write_text(json.dumps(pins))
                binding.write_text(json.dumps({**pins, 'appId': 'other'}))
                with self.assertRaisesRegex(ValueError, 'identity'):
                    runner.verify_shared_binding(binding)
                other = root / 'other'
                other.mkdir()
                outside = other / 'binding.json'
                outside.write_text(json.dumps(pins))
                with self.assertRaisesRegex(ValueError, 'lock directory'):
                    runner.verify_shared_binding(outside)
