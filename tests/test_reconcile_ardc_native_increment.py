import json
import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.reconcile_ardc_native_increment import verify_accepted_target, verify_with_checkpoint


def fixture():
    def page(identifier, token):
        return (f'<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords>'
                f'<record><header status="deleted"><identifier>oai:ands.org.au::{identifier}</identifier></header></record>'
                f'<resumptionToken>{token}</resumptionToken></ListRecords></OAI-PMH>').encode()
    first = 'https://researchdata.edu.au/registry/services/oai?verb=ListRecords&metadataPrefix=rif&from=2026-10-15T00:00:00Z&until=2026-10-25T00:00:00Z'
    second = 'https://researchdata.edu.au/registry/services/oai?verb=ListRecords&resumptionToken=next'
    manifest = {'source': 'ardc', 'format': 'rims-ardc-public-registry-v1', 'complete': True,
                'full_reconciliation': False, 'metadata_prefix': 'rif',
                'scope': 'complete_public_registry_metadata_before_local_selection',
                'records': 2, 'unique_identifiers': 2, 'provider_total': 2,
                'initial_uri': first, 'until': '2026-10-25T00:00:00Z', 'pages': [
                    {'file': 'page-0.xml', 'rows': 1, 'next_token': 'next', 'deleted_headers': 1,
                     'saved_content_equal': True, 'request': first},
                    {'file': 'page-1.xml', 'rows': 1, 'next_token': '', 'deleted_headers': 1,
                     'saved_content_equal': True, 'request': second}]}
    return json.dumps(manifest).encode(), {'page-0.xml': page('1', 'next'), 'page-1.xml': page('2', '')}


class NativeIncrementTests(unittest.TestCase):
    def test_native_reader_requires_independently_accepted_marker_and_folder(self):
        manifest, _ = fixture()
        document = json.loads(manifest)
        document['archive_folder'] = '/Documents/Archive/run'
        accepted = json.dumps(document).encode()
        digest = hashlib.sha256(accepted).hexdigest()
        receipt = json.dumps({'manifest_sha256': digest,
                              'status': 'PASS_COMPLETE_NATIVE_PUBLIC_ARDC_REGISTRY_BASELINE'}).encode()
        self.assertTrue(verify_accepted_target(accepted, accepted, accepted, receipt)['exact_target_validated'])
        with self.assertRaisesRegex(ValueError, 'accepted manifest'):
            verify_accepted_target(accepted + b' ', accepted + b' ', accepted, receipt)
        with self.assertRaisesRegex(ValueError, 'acceptance receipt'):
            verify_accepted_target(accepted, accepted, accepted, b'{"manifest_sha256":"bad"}')
        for status in (None, 'FAILED'):
            with self.assertRaisesRegex(ValueError, 'acceptance receipt'):
                verify_accepted_target(accepted, accepted, accepted,
                                       json.dumps({'manifest_sha256': digest, 'status': status}).encode())

    def test_interrupted_read_resumes_without_refetching_completed_page(self):
        manifest, pages = fixture()
        with tempfile.TemporaryDirectory() as temp:
            checkpoint = Path(temp) / 'checkpoint'
            def interrupted(name):
                if name == 'page-1.xml':
                    raise ConnectionResetError('synthetic interruption')
                return pages[name]
            with self.assertRaises(ConnectionResetError):
                verify_with_checkpoint(manifest, interrupted, checkpoint)
            calls = []
            def resumed(name):
                calls.append(name)
                return pages[name]
            result = verify_with_checkpoint(manifest, resumed, checkpoint)
            self.assertEqual(calls, ['page-1.xml'])
            self.assertEqual(result['records'], 2)
            self.assertFalse(result['current_sharepoint_page_immutability_verified'])

    def test_changed_cache_and_changed_manifest_fail_closed(self):
        manifest, pages = fixture()
        with tempfile.TemporaryDirectory() as temp:
            checkpoint = Path(temp) / 'checkpoint'
            verify_with_checkpoint(manifest, pages.__getitem__, checkpoint)
            (checkpoint / 'page-0.xml').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                verify_with_checkpoint(manifest, pages.__getitem__, checkpoint)
            with self.assertRaisesRegex(ValueError, 'different manifest'):
                verify_with_checkpoint(manifest + b' ', pages.__getitem__, checkpoint)


if __name__ == '__main__':
    unittest.main()
