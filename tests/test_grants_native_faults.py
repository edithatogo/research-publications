# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from scripts.grants_native_faults import CASES, fault_definition


def fixture():
    return {'triggers': {'manual': {'type': 'Request', 'kind': 'Button', 'inputs': {'schema': {
        'type': 'object', 'additionalProperties': False, 'properties': {}}}}},
        'parameters': {'QualificationScenario': {'defaultValue': 'inspect'}},
        'actions': {'Read_source_copy': {'type': 'OpenApiConnection', 'inputs': {
            'host': {'operationId': 'HttpRequest','apiId':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline'}, 'retryPolicy': {'type': 'none'},
            'parameters': {'parameters/method': 'GET',
                           'parameters/uri': "_api/web/lists(guid'fictional')/items(1)?$select=Id,OpportunityKey"}}},
            'Source': {'type': 'Compose', 'inputs': "@body('Read_source_copy')"},
            'Guard_classification_current': {'type': 'Compose', 'inputs': 'existing guard'},
            'Select_operation': {'type': 'Switch', 'cases': {'writer': {'actions': {'write': {'type': 'OpenApiConnection'}}}}},
            'Qualification_result': {'type': 'Compose', 'inputs': {'DeliveryEnabled': False}}}}


class NativeFaultTests(unittest.TestCase):
    def test_all_cases_remove_dormant_writers_and_preserve_preimage(self):
        base = fixture(); before = copy.deepcopy(base)
        for case in CASES:
            with self.subTest(case=case):
                d = fault_definition(base, case)
                self.assertEqual(d['actions']['Select_operation']['type'], 'Compose')
                self.assertFalse(d['actions']['Select_operation']['inputs']['DispatchEnabled'])
                self.assertEqual(d['actions']['Guard_classification_current'], base['actions']['Guard_classification_current'])
                self.assertEqual(d['actions']['Read_source_copy']['inputs']['parameters']['parameters/method'], 'GET')
        self.assertEqual(base, before)

    def test_unsafe_trigger_source_and_scenario_are_rejected(self):
        for path, value in [('kind', 'Http'), ('method', 'POST'), ('scenario', 'plan'), ('retry', {'type': 'fixed'})]:
            d = fixture()
            if path == 'kind': d['triggers']['manual']['kind'] = value
            elif path == 'method': d['actions']['Read_source_copy']['inputs']['parameters']['parameters/method'] = value
            elif path == 'retry': d['actions']['Read_source_copy']['inputs']['retryPolicy'] = value
            else: d['parameters']['QualificationScenario']['defaultValue'] = value
            with self.assertRaises(ValueError): fault_definition(d, CASES[0])
        with self.assertRaises(ValueError): fault_definition(fixture(), 'credential-revocation')
        d = fixture(); d['actions']['Source']['type'] = 'OpenApiConnection'
        with self.assertRaises(ValueError): fault_definition(d, CASES[0])
        d = fixture(); d['triggers']['manual']['type'] = 'Recurrence'
        with self.assertRaises(ValueError): fault_definition(d, CASES[0])

    def test_connector_faults_keep_native_read_separate_from_shape_faults(self):
        b = fixture(); uri = lambda d: d['actions']['Read_source_copy']['inputs']['parameters']['parameters/uri']
        self.assertIn('TEST_ONLY_MISSING_COLUMN', uri(fault_definition(b, 'schema-missing')))
        self.assertIn('/items(2147483000)', uri(fault_definition(b, 'item-missing')))
        self.assertTrue(uri(fault_definition(b, 'partial-key')).endswith('?$select=Id'))
        for case in CASES[3:]: self.assertEqual(uri(fault_definition(b, case)), uri(b))

    def test_non_sharepoint_connector_is_not_a_read_only_diagnostic(self):
        b=fixture();b['actions']['Read_source_copy']['inputs']['host']['apiId']='shared_foreign'
        with self.assertRaises(ValueError):fault_definition(b,CASES[0])
