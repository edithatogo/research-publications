import hashlib
import json
import unittest
from scripts.prepare_outcome_reader import prepare, TABLES
from scripts.deploy_report_definition import fingerprint, parts
from test_definition_packet import definition


class OutcomeReaderTests(unittest.TestCase):
    def setUp(self):
        self.expression = 'expression OutcomeProjection = "FICTIONAL JSON fixture"\n'
        self.model = definition(**{'definition/expressions.tmdl': self.expression, 'definition/model.tmdl': 'model Model\n', 'unknown.txt': 'preserved'})
        self.report = definition(**{'definition/pages/pages.json': json.dumps({'pageOrder': ['Existing'], 'activePageName': 'Existing'}),
            'definition.pbir': 'retained binding', 'card.json': json.dumps({'visual': {'visualType': 'cardVisual'}}),
            'table.json': json.dumps({'visual': {'visualType': 'tableEx'}})})
    def build(self):
        return prepare(self.model, self.report, model_sha256=fingerprint(self.model), report_sha256=fingerprint(self.report),
            source_expression_sha256=hashlib.sha256(self.expression.encode()).hexdigest(), card_template_path='card.json', table_template_path='table.json')
    def test_additive_candidate_preserves_parts_and_existing_page(self):
        result = self.build(); mp, rp = parts(result['model']), parts(result['report'])
        self.assertEqual(mp['unknown.txt'], b'preserved'); self.assertEqual(rp['definition.pbir'], b'retained binding')
        self.assertEqual(json.loads(rp['definition/pages/pages.json'])['pageOrder'], ['Existing','OutcomeEvidence'])
        self.assertTrue(all('definition/tables/'+name+'.tmdl' in mp for name in TABLES))
        self.assertEqual(result, self.build()); self.assertFalse(result['native_ready'])
    def test_existing_table_and_missing_source_refused(self):
        self.expression = 'expression Other = "fixture"\n'
        with self.assertRaises(ValueError): self.build()
