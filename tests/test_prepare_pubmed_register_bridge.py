import copy
import unittest

from scripts.prepare_pubmed_register_bridge import build
from tests import test_prepare_pubmed_acquisition as acquisition


class PubMedRegisterBridgeTests(unittest.TestCase):
    def fixture(self):
        collector = acquisition.PubMedAcquisitionTests().fixture()
        writer = {'properties': {'definition': {'actions': {
            'Get_Existing_Publication_Register': {
                'type': 'OpenApiConnection',
                'inputs': {'parameters': {'dataset': 'https://example.sharepoint.com/sites/dev', 'table': 'existing-list', '$filter': 'field_1 ne null'}, 'host': {'operationId': 'GetItems'}},
            },
            'Apply_to_each_Publication': {'type': 'Foreach', 'actions': {
                'Filter_OpenAlex_Context': {'inputs': {'from': 'model-context'}},
                'Condition_Is_New_Publication': {'actions': {'Create': {'type': 'OpenApiConnection'}}, 'else': {'actions': {'Update': {'type': 'OpenApiConnection'}}}},
            }},
        }}}}
        return collector, writer

    def test_failed_acquisition_cannot_reach_list_writes(self):
        collector, writer = self.fixture()
        actions = build(collector, writer)['properties']['definition']['actions']
        for failure in ['Failed', 'TimedOut']:
            states = acquisition.trace_failure(actions, 'Verify_complete_checkpoint', failure)
            self.assertNotEqual(states.get('Apply_to_each_Publication'), 'Succeeded')
            self.assertEqual(states['Registry_Before'], 'Skipped')

    def test_existing_row_branch_cannot_overwrite_reviewed_values(self):
        collector, writer = self.fixture()
        originals = copy.deepcopy((collector, writer))
        result = build(collector, writer)
        loop = result['properties']['definition']['actions']['Apply_to_each_Publication']
        self.assertEqual(loop['actions']['Condition_Is_New_Publication']['else'], {'actions': {}})
        self.assertEqual(loop['actions']['Condition_Is_New_Publication']['actions'], writer['properties']['definition']['actions']['Apply_to_each_Publication']['actions']['Condition_Is_New_Publication']['actions'])
        self.assertEqual((collector, writer), originals)

    def test_rejects_missing_completion_contract_and_double_install(self):
        collector, writer = self.fixture()
        with self.assertRaises(ValueError):
            build(build(collector, writer), writer)
        del collector['properties']['definition']['actions']['Verify_complete_checkpoint']
        with self.assertRaises(ValueError):
            build(collector, writer)

    def test_only_readback_verified_archive_members_are_projected(self):
        collector, writer = self.fixture()
        a = build(collector, writer)['properties']['definition']['actions']
        page = a['Read_Completed_PubMed_Files']['actions']
        self.assertIn("outputs('Manifest')?['archive_folder']", page['Read_Admission_XML']['inputs']['parameters']['path'])
        self.assertIn('Verify_Admission_Page', page['Admission_Articles']['runAfter'])
        self.assertNotIn('Fetch_xml', page['Admission_XML']['inputs'])
        self.assertIn('Registry_Preserved_Rows', a['Verify_Automatic_PubMed_Register']['runAfter'])


if __name__ == '__main__':
    unittest.main()
