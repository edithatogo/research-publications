# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from scripts.grants_http_faults import definition


class HttpFaultTests(unittest.TestCase):
    def fixture(self):
        return {'triggers':{'manual':{'type':'Request','kind':'Button','inputs':{'schema':{
            'type':'object','additionalProperties':False,'properties':{}}}}},
            'parameters':{'QualificationScenario':{'defaultValue':'inspect'}},
            'actions':{'old_writer':{'type':'OpenApiConnection'}}}

    def test_only_no_data_get_and_no_writer_actions_can_execute(self):
        before=self.fixture();original=copy.deepcopy(before)
        for status in [429,206]:
            d=definition(before,status);self.assertEqual(len(d['actions']),4)
            fetch=d['actions']['Fetch_controlled_response']['inputs']
            self.assertEqual(fetch,{'uri':'https://httpbin.org/status/'+str(status),
                                   'method':'GET','retryPolicy':{'type':'none'}})
            self.assertTrue(all(a['type'] in ['Http','Compose'] for a in d['actions'].values()))
            self.assertFalse(d['actions']['Qualification_result']['inputs']['DispatchEnabled'])
        self.assertEqual(before,original)

    def test_arbitrary_endpoint_codes_and_automatic_triggers_are_rejected(self):
        for status in [True,500,'429']:
            with self.assertRaises(ValueError):definition(self.fixture(),status)
        d=self.fixture();d['triggers']['manual']['type']='Recurrence'
        with self.assertRaises(ValueError):definition(d,429)
