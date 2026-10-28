# SPDX-License-Identifier: Apache-2.0
import unittest
import tempfile
from pathlib import Path
from unittest import mock
from scripts.patch_grants_solution_identity import CONTRACT
import copy
from scripts.patch_grants_solution_identity import patch_definition as guard
from scripts.patch_grants_solution_provenance import patch_definition
from tests.test_patch_grants_solution_identity import baseline as fixture

def baseline(contract_path=CONTRACT):
    result = guard(fixture(contract_path))
    for action in targets(result):
        action['inputs']['parameters']['item/URL'] = "@{item()?['URL']}"
        action['inputs']['parameters'].pop('item/SourceRowURL', None)
    return result

def targets(document):
    valid = document['properties']['definition']['actions']['Apply_to_each_Reviewed_Row']['actions']['Condition_OpportunityKey_Present']['actions']
    branch = valid['Condition_Conflicting_Source_Identity']['else']['actions']['Condition_Is_New_Opportunity']
    return (branch['actions']['SharePoint_Create_item'], branch['else']['actions']['Condition_Exactly_One_Opportunity']['actions']['SharePoint_Update_item'])

class ProvenancePatchTests(unittest.TestCase):

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='grants-provenance-test-')
        self.addCleanup(directory.cleanup)
        self.contract_path = Path(directory.name) / 'importer.json'
        self.contract_path.write_bytes(CONTRACT.read_bytes())
        binding = mock.patch('scripts.patch_grants_solution_identity.CONTRACT', self.contract_path)
        binding.start()
        self.addCleanup(binding.stop)

    def test_only_two_provenance_mappings_change_and_input_is_preserved(self):
        original = baseline(self.contract_path)
        saved = copy.deepcopy(original)
        patched = patch_definition(original)
        self.assertEqual(original, saved)
        self.assertEqual(patch_definition(patched), patched)
        for action in targets(patched):
            self.assertEqual(action['inputs']['parameters'].pop('item/SourceRowURL'), "@{item()?['SourceRowURL']}")
        self.assertEqual(patched, original)

    def test_mapping_drift_is_rejected_case_1(self):
        field = 'item/URL'
        value = 'changed'
        original = baseline(self.contract_path)
        targets(original)[1]['inputs']['parameters'][field] = value
        with self.assertRaises(ValueError):
            patch_definition(original)

    def test_mapping_drift_is_rejected_case_2(self):
        field = 'item/SourceRowURL'
        value = 'changed'
        original = baseline(self.contract_path)
        targets(original)[1]['inputs']['parameters'][field] = value
        with self.assertRaises(ValueError):
            patch_definition(original)

    def test_unguarded_definition_is_rejected(self):
        with self.assertRaises(KeyError):
            patch_definition(fixture())
