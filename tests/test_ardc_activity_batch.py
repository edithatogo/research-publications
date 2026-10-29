import json
import unittest
from urllib.parse import parse_qs, urlsplit

from scripts.ardc_activity_batch import capture_batches, lookup_batch


def response(records, total=None):
    return json.dumps({'status': 'OK', 'code': 200, 'data': {'offset': 0,
                       'numFound': len(records) if total is None else total,
                       'records': records}}).encode()


class Opener:
    def __init__(self, raw): self.raw = raw
    def open(self, request, timeout):
        self.request = request
        self.timeout = timeout
        return self
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, length): return self.raw
    status = 200


class BatchTests(unittest.TestCase):
    def test_batch_capture_gates_total_then_readback_and_replay(self):
        overlay = {'generation_lineage_verified': True, 'baseline_manifest_sha256': 'a' * 64, 'incremental_manifest_sha256': 'b' * 64,
                   'activities': [{'id': '10', 'key': 'a'}, {'id': '20', 'key': 'b'}]}
        stored, calls = {}, []
        def fetch(batch):
            calls.append(len(batch))
            return response([{'id': row['id'], 'key': row['key']} for row in batch])
        with self.assertRaisesRegex(ValueError, 'no archive files created'):
            capture_batches(overlay, lambda: 3, fetch, stored.get, stored.__setitem__, stored.__getitem__, credential=b'private-key')
        self.assertFalse(stored)
        result = capture_batches(overlay, lambda: 2, fetch, stored.get, stored.__setitem__, stored.__getitem__, credential=b'private-key')
        self.assertEqual(calls, [2, 2])
        self.assertEqual(result['records'], 2)
        self.assertFalse(result['native_completion_marker'])
        self.assertFalse(result['provider_snapshot_isolation_verified'])
        overlay['generation_lineage_verified'] = False
        with self.assertRaisesRegex(ValueError, 'configuration'):
            capture_batches(overlay, lambda: 2, fetch, stored.get, stored.__setitem__,
                            stored.__getitem__, credential=b'private-key')

    def test_batch_capture_rejects_cross_batch_duplicate_and_bad_readback(self):
        overlay = {'generation_lineage_verified': True, 'baseline_manifest_sha256': 'a' * 64, 'incremental_manifest_sha256': 'b' * 64,
                   'activities': [{'id': '10', 'key': 'a'}, {'id': '10', 'key': 'b'}]}
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            capture_batches(overlay, lambda: 2, None, None, None, None, credential=b'private-key', batch_size=1)
        overlay['activities'] = [{'id': '10', 'key': 'a'}]
        with self.assertRaisesRegex(ValueError, 'readback'):
            capture_batches(overlay, lambda: 1, lambda b: response([{'id': '10', 'key': 'a'}]),
                            lambda n: None, lambda n, b: None, lambda n: b'wrong', credential=b'private-key')

    def test_replay_allows_order_change_but_rejects_record_changes(self):
        overlay = {'generation_lineage_verified': True, 'baseline_manifest_sha256': 'a' * 64, 'incremental_manifest_sha256': 'b' * 64,
                   'activities': [{'id': '10', 'key': 'a'}, {'id': '20', 'key': 'b'}]}
        records = [{'id': '10', 'key': 'a', 'title': 'A'}, {'id': '20', 'key': 'b', 'title': 'B'}]
        replies = iter([response(records), response(list(reversed(records)))])
        stored = {}
        result = capture_batches(overlay, lambda: 2, lambda b: next(replies), stored.get, stored.__setitem__,
                                 stored.__getitem__, credential=b'private-key')
        self.assertTrue(result['record_fields_replayed'])
        self.assertFalse(result['byte_replay'])
        changed = [records[0], {'id': '20', 'key': 'b', 'title': 'changed'}]
        replies = iter([response(records), response(changed)])
        with self.assertRaisesRegex(ValueError, 'fields changed'):
            capture_batches(overlay, lambda: 2, lambda b: next(replies), lambda n: None, lambda n, b: stored.__setitem__(n, b),
                            stored.__getitem__, credential=b'private-key')

    def test_resume_reuses_original_bytes_and_never_treats_probe_error_as_absence(self):
        overlay = {'generation_lineage_verified': True, 'baseline_manifest_sha256': 'a' * 64, 'incremental_manifest_sha256': 'b' * 64,
                   'activities': [{'id': '10', 'key': 'a'}, {'id': '20', 'key': 'b'}]}
        rows = [{'id': '10', 'key': 'a'}, {'id': '20', 'key': 'b'}]
        original, reordered = response(rows), response(list(reversed(rows)))
        stored = {'activities-batch-000000000.json': original}
        writes = []
        result = capture_batches(overlay, lambda: 2, lambda b: reordered, stored.get,
                                 lambda n, b: writes.append(n), stored.__getitem__, credential=b'private-key')
        self.assertTrue(result['batches'][0]['reused'])
        self.assertFalse(result['byte_replay'])
        self.assertEqual(stored['activities-batch-000000000.json'], original)
        self.assertFalse(writes)
        def denied(name):
            raise PermissionError('not an absence')
        with self.assertRaises(PermissionError):
            capture_batches(overlay, lambda: 2, lambda b: original, denied,
                            lambda n, b: writes.append(n), stored.__getitem__, credential=b'private-key')
        self.assertFalse(writes)

    def test_lost_write_acknowledgement_is_not_retried_and_next_run_reuses(self):
        overlay = {'generation_lineage_verified': True, 'baseline_manifest_sha256': 'a' * 64, 'incremental_manifest_sha256': 'b' * 64,
                   'activities': [{'id': '10', 'key': 'a'}]}
        raw = response([{'id': '10', 'key': 'a'}])
        stored, writes = {}, []
        def ambiguous_write(name, value):
            writes.append(name)
            stored[name] = value
            raise TimeoutError('synthetic lost acknowledgement')
        with self.assertRaises(TimeoutError):
            capture_batches(overlay, lambda: 1, lambda b: raw, stored.get,
                            ambiguous_write, stored.__getitem__, credential=b'private-key')
        self.assertEqual(len(writes), 1)
        result = capture_batches(overlay, lambda: 1, lambda b: raw, stored.get,
                                 lambda n, b: writes.append(n), stored.__getitem__, credential=b'private-key')
        self.assertEqual(len(writes), 1)
        self.assertTrue(result['batches'][0]['reused'])

    def test_rejects_duplicate_json_keys(self):
        raw = b'{"status":"OK","code":200,"data":{"offset":0,"numFound":1,"records":[{"id":"1","id":"1","key":"a"}]}}'
        with self.assertRaisesRegex(ValueError, 'ambiguous JSON'):
            lookup_batch([{'id': '1', 'key': 'a'}], b'private-key', opener=Opener(raw))

    def test_exact_batch_preserves_raw_bytes_and_checks_id_key_set(self):
        identities = [{'id': '10', 'key': 'a'}, {'id': '20', 'key': 'b'}]
        raw = response([{'id': '20', 'key': 'b'}, {'id': '10', 'key': 'a'}])
        opener = Opener(raw)
        self.assertEqual(lookup_batch(identities, b'private-key', opener=opener), raw)
        self.assertEqual(parse_qs(urlsplit(opener.request.full_url).query)['q'], ['id:(10 OR 20)'])
        self.assertEqual(opener.timeout, 30)

    def test_missing_wrong_key_and_duplicate_records_fail_closed(self):
        expected = [{'id': '10', 'key': 'a'}, {'id': '20', 'key': 'b'}]
        invalid = [response([{'id': '10', 'key': 'a'}]),
                   response([{'id': '10', 'key': 'a'}, {'id': '20', 'key': 'wrong'}]),
                   response([{'id': '10', 'key': 'a'}, {'id': '10', 'key': 'a'}])]
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                lookup_batch(expected, b'private-key', opener=Opener(raw))

    def test_query_injection_and_encoded_key_echo_are_rejected(self):
        with self.assertRaises(ValueError):
            lookup_batch([{'id': '1 OR *:*', 'key': 'a'}], b'private-key', opener=Opener(b''))
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            lookup_batch([{'id': '1', 'key': 'a'}], b'private+key',
                         opener=Opener(response([{'id': '1', 'key': 'private%2Bkey'}])))


if __name__ == '__main__':
    unittest.main()
