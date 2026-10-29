import copy
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from typing import ClassVar
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from scripts import capture_ckan_source as source
from scripts.source_capture_receipt import PRIVATE_ROOT

R1 = '00000000-0000-4000-8000-000000000001'
R2 = '00000000-0000-4000-8000-000000000002'
PK = '00000000-0000-4000-8000-000000000003'


class Response(BytesIO):
    status = 200
    headers: ClassVar[dict] = {}


class CKANCaptureTests(unittest.TestCase):
    def fixture(self, *, mutate=None):
        calls = []
        counts = {}
        def opener(request, timeout):
            self.assertEqual(timeout, 45)
            parsed = urlsplit(request.full_url)
            action = parsed.path.rsplit('/', 1)[-1]
            query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            calls.append((action, query))
            key = (action, query.get('id', query.get('resource_id')))
            counts[key] = counts.get(key, 0) + 1
            if action == 'datastore_search' and query['resource_id'] == source.INDEX_RESOURCE_ID:
                value = {'offset': 0, 'total': 2, 'total_was_estimated': False,
                    'fields': [{'id': '_id'}, {'id': 'Resource'}],
                    'records': [{'_id': 1, 'Resource': R1}, {'_id': 2, 'Resource': R2}]}
            elif action == 'resource_show':
                value = {'id': query['id'], 'package_id': PK, 'hash': 'unchanged', 'last_modified': '2026-09-01'}
            elif action == 'package_show':
                value = {'id': PK, 'name': source.DORA_PACKAGE, 'license_id': 'CC-BY-3.0',
                    'resources': [{'id': R1, 'format': 'CSV', 'datastore_active': True, 'last_modified': '2026-09-01'}]}
            elif action == 'datastore_info':
                value = {'fields': [{'id': '_id', 'type': 'int'}, {'id': 'UnmappedSourceField', 'type': 'json'}]}
            else:
                offset = int(query['offset'])
                value = {'offset': offset, 'total': 2, 'total_was_estimated': False,
                    'fields': [{'id': '_id', 'type': 'int'}, {'id': 'UnmappedSourceField', 'type': 'json'}],
                    'records': [{'_id': offset + 1, 'UnmappedSourceField': {'unknown': [None, False, query['resource_id']]}}]}
            if mutate:
                value = mutate(action, query, value, counts[key])
            return Response(json.dumps({'success': True, 'result': value}).encode())
        return opener, calls

    def run_capture(self, provider, output, opener):
        with patch.object(source, 'require_enabled_source'):
            return source.capture(provider, output, opener=opener, page_size=1, sleep=lambda _: None)

    def test_qgip_captures_every_agency_all_fields_and_two_reads(self):
        opener, calls = self.fixture()
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / 'capture'
            result = self.run_capture('qgip', output, opener)
            self.assertEqual(result['count'], 4)
            self.assertEqual({r['resource_id'] for r in result['resources']}, {R1, R2})
            self.assertFalse(result['accepted'])
            self.assertEqual(len(result['files']), 22)
            records = json.loads((output / 'records.json').read_bytes())
            self.assertTrue(all('UnmappedSourceField' in r['record'] for r in records))
            # Both agencies can have the same row IDs; resource identity remains.
            self.assertEqual([r['record']['_id'] for r in records], [1, 2, 1, 2])
            self.assertEqual(len([c for c in calls if c[0] == 'datastore_search']), 10)

    def test_dora_keeps_package_pages_raw_and_separate_resource_grain(self):
        opener, _ = self.fixture()
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / 'capture'
            result = self.run_capture('dora-activities', output, opener)
            self.assertEqual(result['count'], 2)
            self.assertEqual(result['resources'][0]['resource_id'], R1)
            first = json.loads((output / 'index-before.json').read_bytes())
            self.assertTrue(first['success'])
            self.assertEqual(first['result']['name'], source.DORA_PACKAGE)

    def test_drift_estimates_duplicates_and_missing_fields_never_commit(self):
        def mutate_for(case):
            def mutate(action, query, value, occurrence):
                value = copy.deepcopy(value)
                page = action == 'datastore_search' and query['resource_id'] != source.INDEX_RESOURCE_ID
                if case == 'estimate' and page: value['total_was_estimated'] = True
                if case == 'duplicate' and page: value['records'][0]['_id'] = 1
                if case == 'metadata' and action == 'resource_show' and occurrence == 2: value['hash'] = 'changed'
                if case == 'row' and page and occurrence == 3: value['records'][0]['UnmappedSourceField'] = 'changed'
                if case == 'field' and page: del value['records'][0]['UnmappedSourceField']
                if case == 'index' and action == 'datastore_search' and query['resource_id'] == source.INDEX_RESOURCE_ID and occurrence == 2:
                    value['records'][1]['Resource'] = PK
                return value
            return mutate
        for case in ('estimate', 'duplicate', 'metadata', 'row', 'field', 'index'):
            opener, _ = self.fixture(mutate=mutate_for(case))
            with self.subTest(case=case), tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
                output = Path(directory) / 'capture'
                with self.assertRaises(ValueError): self.run_capture('qgip', output, opener)
                self.assertFalse((output / 'manifest.json').exists())
                self.assertTrue((output / 'failed-generation.json').exists())

    def test_disabled_policy_stops_before_transport_and_output_creation(self):
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory, patch.object(source, 'require_enabled_source', side_effect=ValueError('disabled')):
            output = Path(directory) / 'capture'; opener = Mock()
            with self.assertRaisesRegex(ValueError, 'disabled'):
                source.capture('qgip', output, opener=opener)
            opener.assert_not_called()
            self.assertFalse(output.exists())

    def test_empty_resource_valid_ambiguous_dora_invalid(self):
        def empty(action, query, value, _):
            if action == 'datastore_search' and query['resource_id'] != source.INDEX_RESOURCE_ID:
                value.update(total=0, records=[])
            return value
        opener, _ = self.fixture(mutate=empty)
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            result = self.run_capture('dora-activities', Path(directory) / 'capture', opener)
            self.assertEqual(result['count'], 0)
        def ambiguous(action, query, value, _):
            if action == 'package_show': value['resources'].append({**value['resources'][0], 'id': R2})
            return value
        opener, _ = self.fixture(mutate=ambiguous)
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory, self.assertRaisesRegex(ValueError, 'Ambiguous'):
            self.run_capture('dora-activities', Path(directory) / 'capture', opener)


if __name__ == '__main__':
    unittest.main()
