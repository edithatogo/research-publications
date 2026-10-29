import base64
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from prepare_openalex_retention import build, CHUNK_CHARACTERS, require_ignored


class OpenAlexRetention(unittest.TestCase):
    def test_private_paths_require_actual_git_ignore_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '--quiet', str(root)], check=True)
            private = root / 'private' / 'ops'
            private.mkdir(parents=True)
            data = private / 'input.json'
            data.write_text('{}')
            output = private / 'output.json'
            with self.assertRaisesRegex(ValueError, 'must be ignored'):
                require_ignored(private, (data, output))
            (root / '.gitignore').write_text('private/\n')
            require_ignored(private, (data, output))
            with self.assertRaisesRegex(ValueError, 'must be ignored'):
                require_ignored(private, (root / 'not-private.json',))
            subprocess.run(['git', '-C', str(root), 'add', '-f', str(data)], check=True)
            with self.assertRaisesRegex(ValueError, 'must be ignored'):
                require_ignored(private, (data, output))

    def setUp(self):
        self.frozen = json.dumps([{'DORAKey': 'preserved', 'DOI': '10.1000/example',
                                  'Title': 'Original', 'PublicationDateRaw': None}]).encode()
        self.payload = {'id': 'https://openalex.org/W123', 'doi': 'https://doi.org/10.1000/example',
                        'cited_by_count': None, 'open_access': {'oa_status': None},
                        'unknown': {'nested': [None, {'field': 'δ' * 16000}]}}
        self.raw = json.dumps(self.payload, ensure_ascii=False, indent=2).encode()
        self.candidate = {'input_sha256': hashlib.sha256(self.frozen).hexdigest(),
                          'candidate_records': [{'Title': 'Untrusted derived overwrite'}],
                          'observations': {'10.1000/example': {
                              'status': 'success', 'http_status': 200,
                              'observed_utc': '2026-01-01T00:00:00Z',
                              'raw_payload': self.payload,
                              'raw_response_base64': base64.b64encode(self.raw).decode(),
                              'raw_response_sha256': hashlib.sha256(self.raw).hexdigest()}}}

    def reconstruct(self, result):
        parts = sorted(result['chunks'], key=lambda row: row['ChunkIndex'])
        self.assertEqual([p['ChunkIndex'] for p in parts], list(range(len(parts))))
        self.assertTrue(all(p['ChunkCount'] == len(parts) for p in parts))
        encoded = ''.join(p['MetadataChunk'] for p in parts)
        self.assertTrue(all(p['MetadataCharacters'] == len(encoded) for p in parts))
        return json.loads(bytes.fromhex(encoded))

    def test_full_bytes_unknown_fields_and_nulls_survive_native_chunk_format(self):
        before = copy.deepcopy(self.candidate)
        result = build(self.frozen, self.candidate)
        envelope = self.reconstruct(result)
        self.assertEqual(base64.b64decode(envelope['raw_response_base64']), self.raw)
        self.assertEqual(envelope['observed_schema']['fields']['cited_by_count'], {'type': 'null'})
        self.assertIn('unknown', envelope['observed_schema']['fields'])
        self.assertTrue(all(len(p['MetadataChunk']) <= CHUNK_CHARACTERS for p in result['chunks']))
        self.assertFalse(result['accepted_commit'])
        self.assertEqual(self.candidate, before)
        self.assertNotIn('Untrusted derived overwrite', json.dumps(result))

    def test_failed_attempts_cannot_replace_prior_source_records(self):
        observation = self.candidate['observations']['10.1000/example']
        observation.update(status='unavailable', http_status=503)
        result = build(self.frozen, self.candidate)
        self.assertEqual(result['chunks'], [])
        self.assertFalse(result['ready_for_native_stage'])
        self.assertTrue(result['retain_previous_on_failure'])
        self.assertEqual(result['attempt_statuses'][0]['Status'], 'unavailable')

    def test_foreign_input_generation_rejected(self):
        with self.assertRaises(ValueError):
            build(self.frozen + b' ', self.candidate)

    def test_truncated_response_rejected(self):
        self.candidate['observations']['10.1000/example']['raw_response_base64'] = base64.b64encode(self.raw[:-1]).decode()
        with self.assertRaises(ValueError):
            build(self.frozen, self.candidate)

    def test_typed_payload_cannot_differ_from_transport_bytes(self):
        self.candidate['observations']['10.1000/example']['raw_payload'] = {**self.payload, 'cited_by_count': 100}
        with self.assertRaises(ValueError):
            build(self.frozen, self.candidate)

    def test_provider_identity_cannot_enter_foreign_doi_scope(self):
        self.candidate['observations']['10.1000/foreign'] = self.candidate['observations'].pop('10.1000/example')
        with self.assertRaises(ValueError):
            build(self.frozen, self.candidate)

    def test_same_provider_work_cannot_replace_two_distinct_doi_identities(self):
        self.frozen = json.dumps([{'DOI': '10.1000/example'}, {'DOI': '10.1000/second'}]).encode()
        self.candidate['input_sha256'] = hashlib.sha256(self.frozen).hexdigest()
        payload = {**self.payload, 'doi': '10.1000/second'}
        raw = json.dumps(payload).encode()
        self.candidate['observations']['10.1000/second'] = {
            **self.candidate['observations']['10.1000/example'], 'raw_payload': payload,
            'raw_response_base64': base64.b64encode(raw).decode(),
            'raw_response_sha256': hashlib.sha256(raw).hexdigest()}
        with self.assertRaises(ValueError):
            build(self.frozen, self.candidate)


if __name__ == '__main__':
    unittest.main()
