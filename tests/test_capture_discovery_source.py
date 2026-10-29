import copy
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from typing import ClassVar
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from scripts import capture_discovery_source as source
from scripts.source_capture_receipt import PRIVATE_ROOT


class Response(BytesIO):
    status = 200
    headers: ClassVar[dict] = {}


class DiscoveryTests(unittest.TestCase):
    def scope(self, provider='clinicaltrials.gov'):
        parameters = ({'query.term': 'AREA[LocationCountry]Australia', 'format': 'json',
                       'countTotal': 'true', 'pageSize': '1'} if provider == 'clinicaltrials.gov'
                      else {'query.affiliation': 'fictional', 'rows': '500',
                            'filter': 'until-created-date:2026-09-30T23:59:59'})
        return {'source': provider, 'kind': 'complete_discovery',
                'queries': [{'key': 'selected', 'parameters': parameters}]}

    def study(self, identity=1):
        return {'protocolSection': {'identificationModule': {'nctId': f'NCT{identity:08d}'}},
                'unknown_metadata': {'complete': False, 'raw': ['preserve', None, 0]}}

    def version(self):
        return {'apiVersion': 'fixture-v2', 'dataTimestamp': '2026-09-30T00:00:00Z'}

    def opener(self, values):
        return Mock(side_effect=[Response(json.dumps(v).encode()) for v in values])

    def test_complete_trial_discovery_preserves_raw_metadata_and_two_passes(self):
        one = {'studies': [self.study()], 'totalCount': 2, 'nextPageToken': 'opaque+/='}
        two = {'studies': [self.study(2)]}
        read = self.opener([self.version(), one, two, one, two, self.version()])
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / 'capture'
            result = source.capture(self.scope(), output, opener=read, sleep=lambda _: None)
            self.assertTrue(result['complete'])
            self.assertFalse(result['accepted'])
            self.assertEqual(result['count'], 2)
            self.assertEqual(len(result['files']), 6)
            self.assertEqual(json.loads((output / 'records.json').read_bytes()), [self.study(), self.study(2)])
            request = read.call_args_list[2].args[0]
            query = parse_qs(urlsplit(request.full_url).query)
            self.assertEqual(query['pageToken'], ['opaque+/='])
            self.assertEqual(query['query.term'], ['AREA[LocationCountry]Australia'])
            self.assertNotIn('filter.ids', query)
            self.assertNotIn('fields', query)

    def test_empty_query_is_complete_only_with_explicit_zero_total(self):
        for provider in source.ENDPOINTS:
            page = ({'status': 'ok', 'message-type': 'work-list', 'message': {'items': [], 'total-results': 0}}
                    if provider == 'crossref' else {'studies': [], 'totalCount': 0})
            values = [page, page] if provider == 'crossref' else [self.version(), page, page, self.version()]
            with self.subTest(provider=provider), tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
                result = source.capture(self.scope(provider), Path(directory) / 'capture',
                                        opener=self.opener(values), sleep=lambda _: None)
                self.assertEqual(result['count'], 0)

    def test_crossref_full_page_requires_terminal_page_and_keeps_all_fields(self):
        rows = [{'DOI': f'10.5555/fixture-{n}', 'extra': {'items': [None, False]}} for n in range(500)]
        page = {'status': 'ok', 'message-type': 'work-list', 'message': {'items': rows, 'total-results': 500, 'next-cursor': 'opaque'}}
        terminal = copy.deepcopy(page); terminal['message']['items'] = []
        read = self.opener([page, terminal, page, terminal])
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / 'capture'
            result = source.capture(self.scope('crossref'), output, opener=read, sleep=lambda _: None)
            self.assertEqual(result['count'], 500)
            self.assertEqual(read.call_count, 4)
            saved = json.loads((output / 'records.json').read_bytes())
            self.assertEqual({r['DOI']: r for r in saved}, {r['DOI']: r for r in rows})

    def test_truncation_duplicates_drift_missing_total_and_version_change_fail_closed(self):
        good = {'studies': [self.study()], 'totalCount': 1}
        variants = []
        variants.append([self.version(), {'studies': [], 'totalCount': 1}])
        variants.append([self.version(), {'studies': [self.study()]}])
        variants.append([self.version(), {**good, 'partial': True}])
        variants.append([self.version(), {**good, 'studies': [self.study(), self.study()]}])
        changed = copy.deepcopy(good); changed['studies'][0]['unknown_metadata']['raw'] = ['changed']
        variants.append([self.version(), good, changed])
        variants.append([self.version(), good, good, {**self.version(), 'dataTimestamp': 'different'}])
        variants.append([self.version(), {**good, 'totalCount': 2, 'nextPageToken': 'repeat'}, good])
        for values in variants:
            with self.subTest(values=len(values)), tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
                output = Path(directory) / 'capture'
                with self.assertRaises(ValueError):
                    source.capture(self.scope(), output, opener=self.opener(values), sleep=lambda _: None)
                self.assertFalse((output / 'manifest.json').exists())
                failure = json.loads((output / 'failed-generation.json').read_bytes())
                self.assertFalse(failure['complete'])
                self.assertTrue(failure['files'])

    def test_scope_rejected_before_network_or_directory_creation(self):
        for parameter in ('fields', 'filter.ids', 'pageToken', 'url'):
            scope = self.scope(); scope['queries'][0]['parameters'][parameter] = 'unexpected'
            with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
                output = Path(directory) / 'capture'; opener = Mock()
                with self.assertRaises(ValueError):
                    source.capture(scope, output, opener=opener)
                opener.assert_not_called()
                self.assertFalse(output.exists())

    def test_http_failure_is_retained_once_and_caps_prevent_completion(self):
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / 'capture'
            error = HTTPError('https://api.crossref.org/works', 503, 'fixture failure', {}, BytesIO(b'failure body'))
            opener = Mock(side_effect=error)
            with self.assertRaises(HTTPError):
                source.capture(self.scope('crossref'), output, opener=opener)
            self.assertEqual(opener.call_count, 1)
            self.assertFalse((output / 'manifest.json').exists())
            self.assertTrue(any(p.read_bytes() == b'failure body' for p in output.iterdir()))
        page = {'studies': [self.study()], 'totalCount': 2, 'nextPageToken': 'more'}
        for cap in ('MAX_PAGES', 'MAX_TOTAL_BYTES'):
            with self.subTest(cap=cap), tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory, patch.object(source, cap, 1):
                output = Path(directory) / 'capture'
                with self.assertRaises(ValueError):
                    source.capture(self.scope(), output, opener=self.opener([self.version(), page]), sleep=lambda _: None)
                self.assertFalse((output / 'manifest.json').exists())


if __name__ == '__main__':
    unittest.main()
