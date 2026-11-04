# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from scripts.prepare_dora_metadata_bridge import build, FIELDS


class DoraMetadataTests(unittest.TestCase):
    def fixture(self):
        read = {'type': 'OpenApiConnection', 'inputs': {'parameters': {'dataset': 'example', 'table': 'fixture', 'path': 'archive'}}}
        parser = {'Read_Admission_HTML': copy.deepcopy(read), 'Admission_Month': {'type': 'Compose', 'inputs': None}, 'Append_DoRA_Admission': {'inputs': {'value': {key: '@null' for key in ['[Title]', '[Authors]', '[Journal]', '[PublicationYear]', '[PublicationMonth]', '[PublicationDateRaw]', '[PublicationDatePrecision]']}}}}
        return {'properties': {'connectionReferences': {'unchanged': {}}, 'definition': {'triggers': {'daily': {}}, 'actions': {'Verify_DoRA_Register': {}, 'Registry_After': read, 'Project_Missing_DoRA': {'actions': parser}, 'List_previous_checkpoints': read, 'Save_scope': read, 'Read_scope': read}}}}

    def test_additive_schedule_and_original_actions(self):
        c = self.fixture(); old = copy.deepcopy(c); b = build(c)
        self.assertEqual(c, old)
        self.assertEqual(b['properties']['definition']['triggers'], c['properties']['definition']['triggers'])
        self.assertEqual(b['properties']['connectionReferences'], c['properties']['connectionReferences'])
        for k, v in c['properties']['definition']['actions'].items():self.assertEqual(b['properties']['definition']['actions'][k], v)
        with self.assertRaises(ValueError):build(b)

    def test_precedence_and_complete_projection_before_write(self):
        a = build(self.fixture())['properties']['definition']['actions']
        self.assertIn("'dora:'", a['DoRA_Metadata_Targets']['inputs']['where'])
        self.assertIn("['keys']", a['DoRA_Metadata_Targets']['inputs']['where'])
        self.assertIn('@odata.nextLink', a['DoRA_Metadata_Complete']['inputs'])
        self.assertEqual(a['DoRA_Metadata_Apply']['runAfter'], {'DoRA_Metadata_Project': ['Succeeded']})
        self.assertIn('saved_readback_equal', a['DoRA_Metadata_Project']['actions']['DoRA_Metadata_File_Guard']['inputs'])

    def test_review_fields_excluded_and_conditional_write(self):
        a = build(self.fixture())['properties']['definition']['actions']
        p = a['DoRA_Metadata_Project']['actions']
        self.assertEqual(set(p['DoRA_Metadata_Expected']['inputs']), set(FIELDS))
        self.assertFalse(set(FIELDS) & {'field_1', 'field_2', 'field_9', 'field_10', 'field_11', 'field_14', 'field_15', 'field_16', 'field_17', 'field_18', 'field_19', 'field_20'})
        w = a['DoRA_Metadata_Apply']['actions']
        self.assertIn("['before']", w['DoRA_Metadata_Guard']['inputs'])
        self.assertIn('field_1', w['DoRA_Metadata_Guard']['inputs'])
        self.assertEqual(w['DoRA_Metadata_Update']['inputs']['retryPolicy'], {'type': 'none'})
        self.assertIn("['etag']", w['DoRA_Metadata_Update']['inputs']['parameters']['parameters/headers']['IF-MATCH'])
        self.assertIn('Metadata_Month', p)
        self.assertNotIn('Admission_Month', p)
        self.assertIn('not(and(', p['DoRA_Metadata_Append']['expression'])

    def test_absent_source_metadata_preserves_existing_values(self):
        p = build(self.fixture())['properties']['definition']['actions']['DoRA_Metadata_Project']['actions']['DoRA_Metadata_Expected']['inputs']
        for field in ('field_3', 'field_4'):
            self.assertIn('empty(trim(', p[field])
            self.assertIn("items('DoRA_Metadata_Project')?['" + field + "']", p[field])
        for field in ('field_5', 'field_6', 'field_7', 'field_8'):
            self.assertIn("equals(outputs('Metadata_Year'),null)", p[field])
            self.assertIn("items('DoRA_Metadata_Project')?['" + field + "']", p[field])

    def test_receipt_correlates_source_and_update_and_verifies_storage(self):
        a = build(self.fixture())['properties']['definition']['actions']
        receipt = a['DoRA_Metadata_Receipt']['inputs']
        self.assertIn("['run']", receipt['source_run'])
        self.assertIn('workflow()', receipt['list_update_run'])
        self.assertIn("['$content']", a['DoRA_Metadata_Verify_Receipt']['inputs'])
