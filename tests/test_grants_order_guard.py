# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from scripts.grants_order_guard import definition


class OrderGuardTests(unittest.TestCase):
    def fixture(self):
        diag={'triggers':{'manual':{'type':'Request','kind':'Button','inputs':{'schema':{'type':'object','additionalProperties':False,'properties':{}}}}},'actions':{}}
        importer={'actions':{'SharePoint_Get_items':{'type':'OpenApiConnection','inputs':{'host':{'operationId':'GetItems','apiId':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline'},'parameters':{'dataset':'https://example.invalid','table':'old'}}},'Condition_Observation_Not_Older':{'runAfter':{'SharePoint_Get_items':['Succeeded']},'expression':{'greater':["@ticks(item()?['RetrievedUTC'])","@ticks(first(body('SharePoint_Get_items')?['value'])?['RetrievedUTC'])"]}}}}
        return diag,importer

    def test_exact_predicate_clone_and_read_only_loop(self):
        d,i=self.fixture();old=copy.deepcopy(i);current={'RetrievedUTC':'2026-10-28T00:00:00Z'}
        result=definition(d,i,'12345678-1234-1234-1234-123456789abc',current)
        loop=result['actions']['For_each_observation'];a=loop['actions']
        self.assertEqual(a['Condition_Observation_Not_Older']['expression'],i['actions']['Condition_Observation_Not_Older']['expression'])
        self.assertEqual(a['SharePoint_Get_items']['inputs']['host']['operationId'],'GetItems')
        self.assertEqual(loop['foreach'][0]['RetrievedUTC'],'2026-10-27T00:00:00+00:00')
        self.assertEqual(i,old);self.assertEqual(current,{'RetrievedUTC':'2026-10-28T00:00:00Z'})

    def test_automatic_or_write_source_and_uncertain_time_fail_closed(self):
        for fault in ['trigger','write','time']:
            d,i=self.fixture();current={'RetrievedUTC':'2026-10-28T00:00:00Z'}
            if fault=='trigger':d['triggers']['manual']['type']='Recurrence'
            elif fault=='write':i['actions']['SharePoint_Get_items']['inputs']['host']['operationId']='PostItem'
            else:current['RetrievedUTC']='2026-10-28T00:00:00'
            with self.assertRaises(ValueError):definition(d,i,'12345678-1234-1234-1234-123456789abc',current)

    def test_find_rejects_missing_and_ambiguous_matches(self):
        from scripts.grants_order_guard import find
        self.assertEqual(find({'Scope':{'actions':{'Needle':{'type':'Compose'}}}},'Needle'),{'type':'Compose'})
        for actions in [{},{'A':{'actions':{'Needle':{}}},'Needle':{}}]:
            with self.assertRaises(ValueError):find(actions,'Needle')
