# SPDX-License-Identifier: Apache-2.0
import copy
import unittest

from scripts.prepare_dora_register_bridge import build


class DoRARegisterBridgeTests(unittest.TestCase):
    def fixture(self):
        read = {'type': 'OpenApiConnection', 'inputs': {'parameters': {'path': 'archive'}}}
        collector = {'properties': {'definition': {'triggers': {'daily': {'recurrence': {'hour': 4}}}, 'actions': {
            'Verify_complete_checkpoint': {'type': 'Compose', 'inputs': True},
            'For_each_record': {'actions': {'Read_record': read}},
        }}, 'connectionReferences': {'existing': {'connectionName': 'fixture'}}}}
        writer = {'properties': {'definition': {'actions': {
            'Get_Existing_Publication_Register': {'type': 'OpenApiConnection', 'inputs': {'parameters': {'$filter': 'nonblank keys', '$top': 5000}}},
            'Apply_to_each_Publication': {'actions': {
                'Filter_OpenAlex_Context': {'inputs': {'from': 'old model'}},
                'SharePoint_Get_items': {'type': 'OpenApiConnection', 'inputs': {'parameters': {'$filter': 'qualified identity lookup'}}},
                'Condition_Is_New_Publication': {'actions': {'SharePoint_Create_item': {'inputs': {'parameters': {'item/Title': 'source title'}}}}, 'else': {'actions': {'old_update': {}}}},
            }},
        }}}}
        return collector, writer

    def test_source_graph_and_inputs_are_preserved(self):
        c, w = self.fixture()
        old = copy.deepcopy((c, w))
        result = build(c, w)
        self.assertEqual((c, w), old)
        self.assertEqual(result['properties']['definition']['triggers'], c['properties']['definition']['triggers'])
        for name, node in c['properties']['definition']['actions'].items():
            self.assertEqual(result['properties']['definition']['actions'][name], node)
        self.assertEqual(result['properties']['connectionReferences'], c['properties']['connectionReferences'])

    def test_failed_archive_or_partial_inventory_blocks_admission(self):
        a = build(*self.fixture())['properties']['definition']['actions']
        self.assertEqual(a['Registry_Before']['runAfter'], {'Verify_complete_checkpoint': ['Succeeded']})
        self.assertNotIn('$filter', a['Registry_Before']['inputs']['parameters'])
        self.assertIn('@odata.nextLink', a['Registry_Complete']['inputs'])
        self.assertIn('5000', a['Registry_Complete']['inputs'])
        self.assertEqual(a['Registry_SourceKeys']['runAfter'], {'Registry_Complete': ['Succeeded']})
        self.assertEqual(a['Apply_to_each_Publication']['runAfter'], {'Project_Missing_DoRA': ['Succeeded']})

    def test_existing_rows_and_aliases_are_protected(self):
        a = build(*self.fixture())['properties']['definition']['actions']
        query = a['Missing_DoRA_Records']['inputs']['where']
        for alias in ['dora:1/', 'dora:DORA:', 'Registry_CanonicalKeys', 'Registry_URLs', 'http://']:
            self.assertIn(alias, query)
        loop = a['Apply_to_each_Publication']
        self.assertEqual(loop['runtimeConfiguration']['concurrency']['repetitions'], 1)
        self.assertEqual(loop['actions']['Condition_Is_New_Publication']['else'], {'actions': {}})
        self.assertEqual(loop['actions']['Filter_OpenAlex_Context']['inputs']['from'], [])
        self.assertEqual(loop['actions']['Condition_Is_New_Publication']['actions']['SharePoint_Create_item']['inputs']['retryPolicy'], {'type': 'none'})
        self.assertEqual(loop['actions']['Read_Admission_After']['runAfter'], {'Condition_Is_New_Publication': ['Succeeded']})
        self.assertIn('Preserved_Registry_Rows', a['Verify_DoRA_Register']['inputs'])

    def test_source_identity_and_uncertain_attribution_are_explicit(self):
        a = build(*self.fixture())['properties']['definition']['actions']['Project_Missing_DoRA']['actions']
        self.assertIn('dc.identifier.uri', a['Verify_Admission_Identity']['inputs'])
        self.assertIn('dc.title', a['Verify_Admission_Identity']['inputs'])
        self.assertIn('Appears in Sites:', a['Admission_Table']['inputs'])
        row = a['Append_DoRA_Admission']['inputs']['value']
        self.assertIsNone(row['[CHHHSAffiliatedAuthors]'])
        self.assertIsNone(row['[MatchedFacilities]'])
        self.assertIn('affiliation attribution not evaluated', row['[AttributionEvidence]'])
        self.assertIn('Full source HTML', row['[AttributionEvidence]'])

    def test_reapplication_or_missing_checkpoint_is_rejected(self):
        c, w = self.fixture()
        with self.assertRaises(ValueError):
            build(build(c, w), w)
        del c['properties']['definition']['actions']['Verify_complete_checkpoint']
        with self.assertRaises(ValueError):
            build(c, w)
