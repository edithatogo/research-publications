# SPDX-License-Identifier: Apache-2.0
import unittest
import tempfile
from pathlib import Path
from unittest import mock
import copy
from scripts.patch_grants_solution_deadlines import COUNT, FIELDS, patch_definition

def fixture():

    def action(operation):
        return {'inputs': {'host': {'operationId': operation, 'connectionName': 'preserved'}, 'parameters': {'dataset': 'preserved', 'item/Title': 'preserved'}}}
    return {'properties': {'connectionReferences': {'preserved': {}}, 'definition': {'triggers': {'preserved': {}}, 'actions': {'Apply_to_each_Reviewed_Row': {'actions': {'SharePoint_Get_items': {'inputs': {'parameters': {'$top': 2, '$filter': 'OpportunityKey eq test'}}}, 'Condition_Is_New_Opportunity': {'expression': {'equals': [COUNT, 0]}, 'actions': {'SharePoint_Create_item': action('PostItem')}, 'else': {'actions': {'Condition_Exactly_One_Opportunity': {'expression': {'equals': [COUNT, 1]}, 'actions': {'SharePoint_Update_item': action('PatchItem')}}}}}}}}}}}

def params(document):
    branch = document['properties']['definition']['actions']['Apply_to_each_Reviewed_Row']['actions']['Condition_Is_New_Opportunity']
    return (branch['actions']['SharePoint_Create_item']['inputs']['parameters'], branch['else']['actions']['Condition_Exactly_One_Opportunity']['actions']['SharePoint_Update_item']['inputs']['parameters'])

class DeadlinePatchTests(unittest.TestCase):

    def test_only_twelve_mappings_change_and_input_is_preserved(self):
        original = fixture()
        snapshot = copy.deepcopy(original)
        patched = patch_definition(original)
        self.assertEqual(original, snapshot)
        for target in params(patched):
            self.assertTrue(all(('item/' + field in target for field in FIELDS)))
            self.assertTrue(isinstance(target['item/DeadlineTemporalStatus'], dict))
            for field in FIELDS:
                del target['item/' + field]
        self.assertEqual(patched, original)

    def test_idempotent_and_conflicting_mapping_rejected(self):
        patched = patch_definition(fixture())
        self.assertEqual(patch_definition(patched), patched)
        params(patched)[0]['item/DeadlineTimezone'] = 'incorrect'
        with self.assertRaises(ValueError):
            patch_definition(patched)

    def test_wrong_update_guard_rejected(self):
        document = fixture()
        branch = document['properties']['definition']['actions']['Apply_to_each_Reviewed_Row']['actions']['Condition_Is_New_Opportunity']
        branch['else']['actions']['Condition_Exactly_One_Opportunity']['expression'] = {'equals': [COUNT, 2]}
        with self.assertRaises(ValueError):
            patch_definition(document)

    def test_package_preserves_rollback_and_rejects_wrong_hash_or_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='grants-package-test-') as directory:
            tmp_path = Path(directory)
            with mock.patch('scripts.patch_grants_solution_deadlines.ROOT', tmp_path):
                import hashlib
                import json
                import zipfile
                import scripts.patch_grants_solution_deadlines as module
                private = tmp_path / 'private'
                private.mkdir()
                source, output = (private / 'baseline.zip', private / 'candidate.zip')
                workflow = 'Workflows/Grants.json'
                with zipfile.ZipFile(source, 'w') as archive:
                    archive.writestr('solution.xml', '<Root><SolutionManifest><Managed>0</Managed><Version>1</Version></SolutionManifest></Root>')
                    archive.writestr('customizations.xml', '<Root />')
                    archive.writestr('[Content_Types].xml', '<Types />')
                    archive.writestr(workflow, json.dumps(fixture()))
                saved = source.read_bytes()
                digest = hashlib.sha256(saved).hexdigest()
                with self.assertRaises(ValueError):
                    module.patch_package(source, output, workflow, 'wrong')
                self.assertFalse(output.exists())
                result = module.patch_package(source, output, workflow, digest)
                self.assertEqual(result['changed_workflow_count'], 1)
                self.assertEqual(source.read_bytes(), saved)
                with self.assertRaises(ValueError):
                    module.patch_package(source, output, workflow, digest)
                with self.assertRaises(ValueError):
                    module.patch_package(source, private / 'other.zip', 'Workflows/Wrong.json', digest)
                self.assertFalse((private / 'other.zip').exists())
