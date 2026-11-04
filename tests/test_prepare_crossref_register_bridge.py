# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from scripts.prepare_crossref_register_bridge import build


class CrossrefRegisterBridgeTests(unittest.TestCase):
    def fixture(self):
        read = {'type': 'OpenApiConnection', 'inputs': {'parameters': {'path': 'archive'}, 'host': {'operationId': 'GetFileContentByPath'}}}
        http = {'type': 'OpenApiConnection', 'inputs': {'parameters': {'dataset': 'https://example.sharepoint.com/sites/dev', 'parameters/uri': "_api/web/lists(guid'fixture')?$select=ItemCount"}, 'host': {'operationId': 'HttpRequest'}}}
        return {'properties': {'connectionReferences': {'existing': {'connectionName': 'fixture'}}, 'definition': {'triggers': {'Recurrence': {'type': 'Recurrence'}}, 'actions': {
            'Verify_incremental_checkpoint': {'type': 'Compose', 'inputs': True},
            'Get_publication_dois': {'type': 'OpenApiConnection', 'inputs': {'parameters': {'table': 'fixture'}}},
            'Read_coverage': read, 'Read_scope': read,
            'Read_publication_count': http,
            'Save_scope': {'type': 'OpenApiConnection', 'inputs': {'parameters': {'folderPath': "@outputs('Run_folder')"}}},
        }}}}

    def test_original_source_schedule_connections_and_objects_preserved(self):
        c = self.fixture();before = copy.deepcopy(c);b = build(c)
        self.assertEqual(c, before)
        self.assertEqual(b['properties']['definition']['triggers'], c['properties']['definition']['triggers'])
        self.assertEqual(b['properties']['connectionReferences'], c['properties']['connectionReferences'])
        for k, v in c['properties']['definition']['actions'].items():
            self.assertEqual(b['properties']['definition']['actions'][k], v)

    def test_only_missing_or_explicitly_refreshed_successful_dois_selected(self):
        a = build(self.fixture())['properties']['definition']['actions']
        self.assertEqual(a['Crossref_Register_Before']['runAfter'], {'Verify_incremental_checkpoint': ['Succeeded']})
        self.assertIn('@odata.nextLink', a['Crossref_Register_Complete']['inputs'])
        self.assertIn('200', a['Crossref_Successful_Entries']['inputs']['where'])
        predicate = a['Crossref_Target_Rows']['inputs']['where']
        self.assertIn('CitationCount_Crossref', predicate)
        self.assertIn('Batch_DOIs', predicate)
        self.assertIn('Crossref_Successful_DOIs', predicate)

    def test_all_raw_projection_finishes_before_first_write(self):
        a = build(self.fixture())['properties']['definition']['actions']
        self.assertEqual(a['Crossref_Apply_Updates']['runAfter'], {'Crossref_Project_Updates': ['Succeeded']})
        p = a['Crossref_Project_Updates']['actions']
        self.assertIn('requested_doi', p['Crossref_Verify_Raw']['inputs'])
        self.assertIn("['DOI']", p['Crossref_Verify_Raw']['inputs'])
        self.assertIn('isInt', p['Crossref_Verify_Raw']['inputs'])
        self.assertIn('greaterOrEquals', p['Crossref_Verify_Count']['inputs'])

    def test_single_field_update_requires_exact_identity_preimage_and_etag(self):
        a = build(self.fixture())['properties']['definition']['actions']['Crossref_Apply_Updates']['actions']
        self.assertIn("?['before']", a['Crossref_Verify_Target']['inputs'])
        self.assertIn('field_11', a['Crossref_Verify_Target']['inputs'])
        patch = a['Crossref_If_Changed']['actions']['Crossref_Update_Count']['inputs']
        self.assertEqual(patch['retryPolicy'], {'type': 'none'})
        self.assertIn("['etag']", patch['parameters']['parameters/headers']['IF-MATCH'])
        self.assertEqual(patch['parameters']['parameters/headers']['X-HTTP-Method'], 'MERGE')
        body = patch['parameters']['parameters/body']
        self.assertIn('CitationCount_Crossref', body)
        for protected in ['Title', 'field_17', 'field_18', 'CitationCount_OpenAlex', 'CitationMetricsObservedUTC']:
            self.assertNotIn(protected, body)
        self.assertEqual(a['Crossref_Read_After']['runAfter'], {'Crossref_If_Changed': ['Succeeded']})

    def test_receipt_is_source_correlated_unique_and_read_back(self):
        a = build(self.fixture())['properties']['definition']['actions']
        self.assertIn("['capture_run']", a['Crossref_List_Receipt']['inputs']['source_run'])
        self.assertIn("workflow()?['run']", a['Crossref_Save_List_Receipt']['inputs']['parameters']['name'])
        self.assertIn("['$content']", a['Crossref_Verify_List_Receipt']['inputs'])
        self.assertEqual(a['Crossref_List_Receipt']['runAfter'], {'Crossref_Apply_Updates': ['Succeeded']})

    def test_reapplication_refused(self):
        with self.assertRaises(ValueError):build(build(self.fixture()))
