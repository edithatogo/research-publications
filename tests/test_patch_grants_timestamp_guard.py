# SPDX-License-Identifier: Apache-2.0
import copy
import json
from pathlib import Path
import unittest
from scripts.grants_order_guard import find
from scripts.patch_grants_timestamp_guard import patch


class TimestampGuardTests(unittest.TestCase):
    def source(self):
        return json.loads(Path('config/flows/grants-registry-reviewed-import.definition.json').read_text())['properties']['definition']

    def test_caught_parse_failure_increments_domain_failure_before_writers(self):
        source=self.source();before=copy.deepcopy(source);result=patch(source)
        actions=find(result['actions'],'Condition_OpportunityKey_Present')['actions']
        self.assertEqual(actions['Validate_Observation_Instant']['actions']['Parse_Observation_Ticks']['inputs'],"@ticks(string(coalesce(item()?['RetrievedUTC'], '')))")
        self.assertEqual(actions['Condition_Conflicting_Source_Identity']['runAfter'],{'Validate_Incoming_Observation_UTC':['Succeeded']})
        self.assertEqual(actions['Validate_Incoming_Observation_UTC']['runAfter'],{'Validate_Observation_Instant':['Succeeded']})
        failure=actions['Handle_Malformed_Observation']
        self.assertEqual(failure['runAfter'],{'Validate_Observation_Instant':['Failed','TimedOut']})
        self.assertEqual(failure['actions']['Compose_Malformed_Observation_Failure']['inputs'],'MALFORMED_GRANTS_OBSERVATION_TIME')
        self.assertEqual(failure['actions']['Increment_Malformed_Observation_Failure']['inputs'],{'name':'RowFailureCount','value':1})
        self.assertNotIn('OpenApiConnection',json.dumps(failure))
        del actions['Validate_Observation_Instant'];del actions['Handle_Malformed_Observation']
        del actions['Validate_Incoming_Observation_UTC'];del actions['Handle_Uncertain_Incoming_Observation']
        actions['Condition_Conflicting_Source_Identity']['runAfter']={'SharePoint_Get_source_identity':['Succeeded']}
        self.assertEqual(result,before);self.assertEqual(source,before)

    def test_drift_and_double_patch_are_rejected(self):
        source=self.source()
        with self.assertRaises(ValueError):patch(patch(source))
        find(source['actions'],'Condition_Conflicting_Source_Identity')['runAfter']={}
        with self.assertRaises(ValueError):patch(source)
