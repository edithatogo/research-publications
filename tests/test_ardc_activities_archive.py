import json
import hashlib
import unittest
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from scripts.ardc_activities_archive import activities_fetcher, capture, capture_reconciled_ids, decode_page, exact_activity, extract_archive_page, overlay_incremental, reconcile_archive


def page(offset, ids, total=3):
    return json.dumps({'status': 'OK', 'code': '200', 'data': {
        'offset': offset, 'numFound': total,
        'records': [{'id': i, 'source': 'original'} for i in ids],
    }}).encode()


class ActivitiesArchiveTests(unittest.TestCase):
    def test_incremental_overlay_handles_reclassification_and_tombstone(self):
        baseline = {'stored_generation_reconciled': True, 'full_reconciliation': True,
                    'until': '2026-10-18T00:00:00Z', 'records': 3, 'ids': ['1', '2', '3'],
                    'activities': [{'id': '1', 'key': 'old'}, {'id': '2', 'key': 'removed'}],
                    'tombstones': []}
        incremental = {'stored_generation_reconciled': True, 'full_reconciliation': False,
                       'from': '2026-10-15T00:00:00Z', 'until': '2026-10-25T00:00:00Z',
                       'records': 3, 'ids': ['1', '2', '3'],
                       'activities': [{'id': '1', 'key': 'new'}, {'id': '3', 'key': 'added'}],
                       'tombstones': ['2']}
        result = overlay_incremental(baseline, incremental)
        self.assertEqual(result['activities'], [{'id': '1', 'key': 'new'}, {'id': '3', 'key': 'added'}])
        self.assertEqual(result['tombstones_observed'], ['2'])
        self.assertFalse(result['per_record_version_order_verified'])
        self.assertFalse(result['downstream_deletions_authorized'])
        incremental['from'] = '2026-10-19T00:00:00Z'
        with self.assertRaisesRegex(ValueError, 'does not cover'):
            overlay_incremental(baseline, incremental)

    def test_incremental_archive_requires_opt_in_and_valid_utc_window(self):
        page_raw = b'''<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords>
          <record><header status="deleted"><identifier>oai:ands.org.au::1</identifier></header></record>
          <resumptionToken/></ListRecords></OAI-PMH>'''
        start, end = '2026-10-15T00:00:00Z', '2026-10-25T00:00:00Z'
        initial = f'https://researchdata.edu.au/registry/services/oai?verb=ListRecords&metadataPrefix=rif&from={start}&until={end}'
        manifest = {'source': 'ardc', 'format': 'rims-ardc-public-registry-v1', 'complete': True,
                    'full_reconciliation': False, 'metadata_prefix': 'rif',
                    'scope': 'complete_public_registry_metadata_before_local_selection',
                    'records': 1, 'unique_identifiers': 1, 'provider_total': 1, 'until': end,
                    'initial_uri': initial, 'pages': [{'file': 'page-0.xml', 'rows': 1,
                    'next_token': '', 'deleted_headers': 1, 'saved_content_equal': True, 'request': initial}]}
        raw = json.dumps(manifest).encode(); digest = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, 'explicit qualification'):
            reconcile_archive(raw, digest, lambda n: page_raw)
        result = reconcile_archive(raw, digest, lambda n: page_raw, allow_incremental=True)
        self.assertEqual(result['from'], start)
        self.assertFalse(result['full_reconciliation'])
        manifest['initial_uri'] = initial.replace(start, 'not-a-date')
        manifest['pages'][0]['request'] = manifest['initial_uri']
        raw = json.dumps(manifest).encode()
        with self.assertRaisesRegex(ValueError, 'window'):
            reconcile_archive(raw, hashlib.sha256(raw).hexdigest(), lambda n: page_raw, allow_incremental=True)

    def test_exact_id_capture_checks_counts_reconciles_and_replays(self):
        archive = {'stored_generation_reconciled': True,
                   'activities': [{'id': '1', 'key': 'source:1'}, {'id': '2', 'key': 'source:2'}]}
        def fetch(identity):
            return json.dumps({'status': 'OK', 'code': 200, 'data': {'offset': 0, 'numFound': 1,
                              'records': [{'id': identity, 'key': 'source:' + identity}]}}).encode()
        storage, calls = {}, []
        def counted(identity):
            calls.append(identity)
            return fetch(identity)
        result = capture_reconciled_ids(archive, lambda: 2, counted, storage.__setitem__,
                                        storage.__getitem__, credential=b'private-key')
        self.assertEqual(calls, ['1', '2', '1', '2'])
        self.assertEqual(result['records'], 2)
        self.assertFalse(result['native_completion_marker'])
        self.assertFalse(result['archive_freshness_independently_verified'])
        storage.clear()
        with self.assertRaisesRegex(ValueError, 'totals do not reconcile'):
            capture_reconciled_ids(archive, lambda: 1, counted, storage.__setitem__,
                                   storage.__getitem__, credential=b'private-key')
        self.assertFalse(storage)

    def test_exact_id_capture_rejects_duplicate_identity_and_changed_replay(self):
        archive = {'stored_generation_reconciled': True,
                   'activities': [{'id': '1', 'key': 'source:1'}]}
        def response(title):
            return json.dumps({'status': 'OK', 'code': 200, 'data': {'offset': 0, 'numFound': 1,
                              'records': [{'id': '1', 'key': 'source:1', 'title': title}]}}).encode()
        replies = iter([response('first'), response('changed')])
        storage = {}
        with self.assertRaisesRegex(ValueError, 'changed during replay'):
            capture_reconciled_ids(archive, lambda: 1, lambda i: next(replies), storage.__setitem__,
                                   storage.__getitem__, credential=b'private-key')
        archive['activities'].append({'id': '1', 'key': 'source:other'})
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            capture_reconciled_ids(archive, lambda: 2, None, None, None, credential=b'private-key')

    def test_reconciles_manifest_and_token_chain_without_claiming_source_bytes(self):
        def xml(identifier, token):
            return (f'<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords>'
                    f'<record><header status="deleted"><identifier>oai:ands.org.au::{identifier}</identifier></header></record>'
                    f'<resumptionToken>{token}</resumptionToken></ListRecords></OAI-PMH>').encode()
        pages = {'page-0.xml': xml('1', 'abc'), 'page-1.xml': xml('2', '')}
        manifest = {'source': 'ardc', 'format': 'rims-ardc-public-registry-v1',
                    'complete': True, 'full_reconciliation': True, 'metadata_prefix': 'rif',
                    'scope': 'complete_public_registry_metadata_before_local_selection',
                    'records': 2, 'unique_identifiers': 2, 'provider_total': 2,
                    'initial_uri': 'https://researchdata.edu.au/registry/services/oai?verb=ListRecords&metadataPrefix=rif',
                    'pages': [
                        {'file': 'page-0.xml', 'rows': 1, 'next_token': 'abc', 'deleted_headers': 1,
                         'saved_content_equal': True, 'request': 'https://researchdata.edu.au/registry/services/oai?verb=ListRecords&metadataPrefix=rif'},
                        {'file': 'page-1.xml', 'rows': 1, 'next_token': '', 'deleted_headers': 1,
                         'saved_content_equal': True, 'request': 'https://researchdata.edu.au/registry/services/oai?verb=ListRecords&resumptionToken=abc'}]}
        raw = json.dumps(manifest).encode()
        digest = hashlib.sha256(raw).hexdigest()
        result = reconcile_archive(raw, digest, pages.__getitem__)
        self.assertEqual(result['tombstones'], ['1', '2'])
        self.assertTrue(result['stored_generation_reconciled'])
        self.assertFalse(result['original_transport_bytes_verified'])
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            reconcile_archive(raw, 'bad', pages.__getitem__)
        pages['page-1.xml'] = xml('1', '')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            reconcile_archive(raw, digest, pages.__getitem__)
        pages['page-1.xml'] = xml('2', 'unexpected')
        with self.assertRaisesRegex(ValueError, 'token mismatch'):
            reconcile_archive(raw, digest, pages.__getitem__)

    def test_extracts_activity_and_preserves_unclassified_tombstone(self):
        raw = b'''<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
          <ListRecords>
            <record><header><identifier>oai:ands.org.au::123</identifier></header>
              <metadata><registryObjects xmlns="http://ands.org.au/standards/rif-cs/registryObjects">
                <registryObject><key>source:123</key><activity type="grant"/></registryObject>
              </registryObjects></metadata></record>
            <record><header status="deleted"><identifier>oai:ands.org.au::124</identifier></header></record>
          </ListRecords></OAI-PMH>'''
        result = extract_archive_page(raw)
        self.assertEqual(result['activities'], [{'id': '123', 'key': 'source:123'}])
        self.assertEqual(result['tombstones'], ['124'])
        self.assertFalse(result['complete_generation'])

    def test_oai_rejects_duplicates_provider_errors_and_doctype(self):
        duplicate = b'''<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords>
          <record><header status="deleted"><identifier>oai:ands.org.au::1</identifier></header></record>
          <record><header status="deleted"><identifier>oai:ands.org.au::1</identifier></header></record>
        </ListRecords></OAI-PMH>'''
        error = b'<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><error code="badArgument"/></OAI-PMH>'
        for raw in (duplicate, error, b'<!DOCTYPE x><x/>', '<!DOCTYPE x><x/>'.encode('utf-16')):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                extract_archive_page(raw)

    def test_keyed_fetch_uses_documented_parameters(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, length): return page(0, ['1'], 1)
        class Opener:
            def open(self, request, timeout):
                self.request = request
                self.timeout = timeout
                return Response()
        opener = Opener()
        result = activities_fetcher(b'private-key', opener=opener)(0, 1)
        self.assertEqual(result, page(0, ['1'], 1))
        self.assertEqual(parse_qs(urlsplit(opener.request.full_url).query),
                         {'api_key': ['private-key'], 'limit': ['1'], 'offset': ['0']})
        self.assertEqual(opener.timeout, 30)

    def test_transport_errors_do_not_expose_credential(self):
        class Opener:
            def __init__(self, error): self.error = error
            def open(self, request, timeout): raise self.error(request.full_url)
        errors = [lambda url: HTTPError(url, 403, 'denied', {}, None),
                  lambda url: URLError(url)]
        for error in errors:
            with self.subTest(error=error):
                fetch = activities_fetcher(b'private-key', opener=Opener(error))
                with self.assertRaises(ValueError) as caught:
                    fetch(0, 1)
                self.assertNotIn('private-key', str(caught.exception))
                self.assertIsNone(caught.exception.__cause__)

    def test_exact_id_query_and_identity_guard(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, length):
                return json.dumps({'status': 'OK', 'code': '200', 'data': {
                    'offset': 0, 'numFound': 1,
                    'records': [{'id': '123', 'key': 'source:123'}]}}).encode()
        class Opener:
            def open(self, request, timeout):
                self.request = request
                return Response()
        opener = Opener()
        raw = activities_fetcher(b'private-key', opener=opener, activity_id='123')(0, 2)
        self.assertEqual(parse_qs(urlsplit(opener.request.full_url).query)['q'], ['id:123'])
        self.assertEqual(exact_activity(raw, '123', source_key='source:123')['id'], '123')
        with self.assertRaisesRegex(ValueError, 'identity'):
            exact_activity(raw, '124', source_key='source:123')
        with self.assertRaisesRegex(ValueError, 'identity'):
            exact_activity(raw, '123', source_key='source:other')
        with self.assertRaisesRegex(ValueError, 'source key'):
            exact_activity(raw, '123', source_key='')
        with self.assertRaises(ValueError):
            activities_fetcher(b'private-key', activity_id='123 OR *:*')
        with self.assertRaisesRegex(ValueError, 'full source'):
            capture(activities_fetcher(b'private-key', opener=opener, activity_id='123'),
                    lambda n, b: None, lambda n: b'', credential=b'private-key')

    def test_complete_capture_reads_back_and_replays_raw_pages(self):
        raw = {0: page(0, ['1', '2']), 2: page(2, ['3'])}
        stored = {}
        calls = []
        def fetch(offset, limit):
            calls.append(offset)
            return raw[offset]
        def put(name, value):
            self.assertNotIn(name, stored)
            stored[name] = value
        result = capture(fetch, put, stored.__getitem__, credential=b'private-key', limit=2)
        self.assertEqual(calls, [0, 0, 2, 0, 2])
        self.assertEqual(result['records'], 3)
        self.assertFalse(result['native_completion_marker'])
        self.assertEqual(list(stored.values()), list(raw.values()))

    def test_rejects_truncated_wrong_offset_and_duplicate_ids(self):
        for raw in (page(0, ['1']), page(1, ['1', '2']), page(0, ['1', '1'])):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                decode_page(raw, 0, 2)

    def test_rejects_duplicate_across_pages_without_replay(self):
        raw = {0: page(0, ['1', '2']), 2: page(2, ['2'])}
        stored = {}
        with self.assertRaisesRegex(ValueError, 'across pages'):
            capture(lambda offset, limit: raw[offset], stored.__setitem__, stored.__getitem__, credential=b'private-key', limit=2)

    def test_rejects_changed_source_during_replay(self):
        replies = iter([page(0, ['1'], 1), page(0, ['1'], 1), page(0, ['2'], 1)])
        stored = {}
        with self.assertRaisesRegex(ValueError, 'changed during replay'):
            capture(lambda offset, limit: next(replies), stored.__setitem__, stored.__getitem__, credential=b'private-key', limit=1)

    def test_rejects_corrupt_archive_readback(self):
        with self.assertRaisesRegex(ValueError, 'readback'):
            capture(lambda offset, limit: page(0, ['1'], 1), lambda n, b: None,
                    lambda n: b'corrupt', credential=b'private-key', limit=1)

    def test_documented_empty_response_is_replayed(self):
        raw = b'{"status":"OK","code":"200","data":[]}'
        stored = {}
        receipt = capture(lambda offset, limit: raw, stored.__setitem__, stored.__getitem__, credential=b'private-key')
        self.assertEqual(receipt['records'], 0)
        self.assertEqual(len(receipt['pages']), 1)

    def test_rejects_boolean_page_size(self):
        with self.assertRaises(ValueError):
            capture(None, None, None, credential=b'private-key', limit=True)

    def test_refuses_a_response_containing_the_credential_before_storage(self):
        stored = {}
        with self.assertRaisesRegex(ValueError, 'contains credential'):
            capture(lambda offset, limit: page(0, ['private-key'], 1),
                    stored.__setitem__, stored.__getitem__, credential=b'private-key', limit=1)
        self.assertFalse(stored)

    def test_refuses_percent_encoded_credential_before_storage(self):
        stored = {}
        with self.assertRaisesRegex(ValueError, 'contains credential'):
            capture(lambda offset, limit: page(0, ['private%2Bkey'], 1),
                    stored.__setitem__, stored.__getitem__, credential=b'private+key', limit=1)
        self.assertFalse(stored)

    def test_unstable_first_page_is_rejected_before_any_archive_write(self):
        replies = iter([page(0, ['1'], 1), page(0, ['2'], 1)])
        stored = {}
        with self.assertRaisesRegex(ValueError, 'unstable'):
            capture(lambda offset, limit: next(replies), stored.__setitem__,
                    stored.__getitem__, credential=b'private-key', limit=1)
        self.assertFalse(stored)


if __name__ == '__main__':
    unittest.main()
