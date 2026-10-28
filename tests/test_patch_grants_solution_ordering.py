# SPDX-License-Identifier: Apache-2.0
import unittest
import tempfile
from pathlib import Path
from unittest import mock
import copy
import json
from datetime import datetime
from scripts.patch_grants_solution_identity import CONTRACT
from scripts.patch_grants_solution_ordering import patch_definition, INCOMING, EXISTING

def exact(document):
    permitted = document['properties']['definition']['actions']['Apply_to_each_Reviewed_Row']['actions']['Condition_OpportunityKey_Present']['actions']['Condition_Conflicting_Source_Identity']['else']['actions']
    return permitted['Condition_Is_New_Opportunity']['else']['actions']['Condition_Exactly_One_Opportunity']

def baseline(contract_path=CONTRACT):
    result = json.loads(contract_path.read_text())
    branch = exact(result)
    branch['actions'] = branch['actions']['Condition_Observation_Time_Known']['actions']['Condition_Observation_Not_Older']['actions']
    return result

class OrderingPatchTests(unittest.TestCase):

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='grants-test-')
        self.addCleanup(directory.cleanup)
        self.contract_path = Path(directory.name) / 'importer.json'
        self.contract_path.write_bytes(CONTRACT.read_bytes())

    def test_only_update_is_wrapped_and_native_mappings_are_preserved(self):
        original = baseline(self.contract_path)
        snapshot = copy.deepcopy(original)
        patched = patch_definition(original)
        self.assertEqual(original, snapshot)
        self.assertEqual(patch_definition(patched), patched)
        wrapper = exact(patched)['actions']['Condition_Observation_Time_Known']
        exact(patched)['actions'] = wrapper['actions']['Condition_Observation_Not_Older']['actions']
        self.assertEqual(patched, original)

    def test_unknown_and_older_branches_have_diagnostics_and_no_writes(self):
        wrapper = exact(patch_definition(baseline(self.contract_path)))['actions']['Condition_Observation_Time_Known']
        for condition, code in [(wrapper, 'UNCERTAIN_GRANTS_OBSERVATION_TIME'), (wrapper['actions']['Condition_Observation_Not_Older'], 'OLDER_GRANTS_OBSERVATION')]:
            actions = condition['else']['actions']
            self.assertEqual([v['type'] for v in actions.values()], ['Compose', 'IncrementVariable'])
            self.assertEqual(next(iter(actions.values()))['inputs'], code)
            self.assertEqual(list(actions.values())[1]['inputs'], {'name': 'RowFailureCount', 'value': 1})

    def test_actual_ordering_predicate_compares_instants_case_1(self):
        incoming = '2026-10-04T00:00:00Z'
        prior = '2026-10-05T00:00:00Z'
        permitted = False
        wrapper = exact(patch_definition(baseline(self.contract_path)))['actions']['Condition_Observation_Time_Known']
        predicate = wrapper['actions']['Condition_Observation_Not_Older']['expression']
        self.assertEqual(predicate, {'greaterOrEquals': ['@ticks(' + INCOMING + ')', '@ticks(' + EXISTING + ')']})
        left, right = (datetime.fromisoformat(t.replace('Z', '+00:00')) for t in (incoming, prior))
        self.assertIs(left >= right, permitted)

    def test_actual_ordering_predicate_compares_instants_case_2(self):
        incoming = '2026-10-05T00:00:00Z'
        prior = '2026-10-05T00:00:00+00:00'
        permitted = True
        wrapper = exact(patch_definition(baseline(self.contract_path)))['actions']['Condition_Observation_Time_Known']
        predicate = wrapper['actions']['Condition_Observation_Not_Older']['expression']
        self.assertEqual(predicate, {'greaterOrEquals': ['@ticks(' + INCOMING + ')', '@ticks(' + EXISTING + ')']})
        left, right = (datetime.fromisoformat(t.replace('Z', '+00:00')) for t in (incoming, prior))
        self.assertIs(left >= right, permitted)

    def test_actual_ordering_predicate_compares_instants_case_3(self):
        incoming = '2026-10-06T00:00:00+00:00'
        prior = '2026-10-05T00:00:00Z'
        permitted = True
        wrapper = exact(patch_definition(baseline(self.contract_path)))['actions']['Condition_Observation_Time_Known']
        predicate = wrapper['actions']['Condition_Observation_Not_Older']['expression']
        self.assertEqual(predicate, {'greaterOrEquals': ['@ticks(' + INCOMING + ')', '@ticks(' + EXISTING + ')']})
        left, right = (datetime.fromisoformat(t.replace('Z', '+00:00')) for t in (incoming, prior))
        self.assertIs(left >= right, permitted)

    def test_non_utc_or_missing_observations_cannot_reach_ticks_or_update(self):
        wrapper = exact(patch_definition(baseline(self.contract_path)))['actions']['Condition_Observation_Time_Known']
        predicates = wrapper['expression']['and']
        self.assertEqual(predicates[0], {'equals': ["@item()?['RetrievedTimestampStatus']", 'valid']})
        for value, predicate in zip((INCOMING, EXISTING), predicates[1:]):
            self.assertEqual(predicate, {'or': [{'equals': ['@endsWith(string(coalesce(' + value + ", '')), 'Z')", True]}, {'equals': ['@endsWith(string(coalesce(' + value + ", '')), '+00:00')", True]}]})
        self.assertNotIn('ticks', json.dumps(wrapper['expression']))

    def test_guard_drift_and_missing_failure_aggregation_are_rejected(self):
        patched = patch_definition(baseline(self.contract_path))
        exact(patched)['actions']['Condition_Observation_Time_Known']['expression'] = {'equals': [1, 1]}
        with self.assertRaises(ValueError):
            patch_definition(patched)
        original = baseline(self.contract_path)
        del original['properties']['definition']['actions']['Condition_Any_Row_Failures']
        with self.assertRaises(ValueError):
            patch_definition(original)

    def test_iso_preservation_stays_inside_chronology_gate_without_field_changes(self):
        original = baseline(self.contract_path)
        actions = exact(original)['actions']
        preserve = {'type': 'OpenApiConnection', 'inputs': {'host': {'operationId': 'HttpRequest'}}, 'runAfter': {'SharePoint_Update_item': ['Succeeded']}}
        actions['SharePoint_Update_item_Preserve_ISO_Text'] = preserve
        result = patch_definition(original)
        guarded = exact(result)['actions']['Condition_Observation_Time_Known']['actions']['Condition_Observation_Not_Older']['actions']
        self.assertEqual(guarded, actions)
        self.assertEqual(patch_definition(result), result)
