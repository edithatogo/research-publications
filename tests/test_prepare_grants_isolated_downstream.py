# SPDX-License-Identifier: Apache-2.0
"""Fictional supplied-flow preparation; no service, model or private targets."""
import copy
import unittest
from scripts.prepare_grants_isolated_downstream import build, namespace_actions

KINDS=['calendar','changes','watchlist','ledger']
SOURCE='10000000-0000-0000-0000-000000000000'
OLD={k:f'20000000-0000-0000-0000-00000000000{i}' for i,k in enumerate(KINDS)}
NEW={k:f'30000000-0000-0000-0000-00000000000{i}' for i,k in enumerate(KINDS)}


def fixture():
    marker='TEST_ONLY_G0708_20261028'
    stores={k:dict(id=NEW[k],key=k,marker=marker,title=marker+'_'+k) for k in KINDS}
    def connector(kind):
        return {'type':'OpenApiConnection','inputs':{'host':{'apiId':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline','operationId':'HttpRequest'},
            'parameters':{'dataset':'https://example.invalid','parameters/method':'POST',
             'parameters/uri':"_api/web/lists(guid'"+OLD[kind]+"')/items",'parameters/body':'FICTIONAL payload'},'retryPolicy':{'type':'none'}}}
    c={'properties':{'definition':{'$schema':'fictional-flow','parameters':{},'actions':{
        'Parse_Calendar_Rows':{'type':'ParseJson','inputs':{'content':[]}},'Write':connector('calendar'),
        'Result':{'type':'Compose','inputs':'no_send'}}},'connectionReferences':{'shared_sharepointonline':{'source':'Invoker','connectionName':'FICTIONAL'}}}}
    l={'properties':{'definition':{'parameters':{},'actions':{
        'Caller_identity':connector('ledger'),'Validate_request':{'type':'ParseJson','inputs':{'content':{}}},
        'Write':connector('ledger'),'Result':{'type':'Compose','inputs':'no_send'}}}}}
    l['properties']['connectionReferences']=copy.deepcopy(c['properties']['connectionReferences'])
    caller=l['properties']['definition']['actions']['Caller_identity']['inputs']['parameters']
    caller['parameters/method']='GET';caller['parameters/uri']='_api/web/currentuser'
    args=dict(source_stores=OLD,source_list_id=SOURCE,source_item_id=1,
        mapping={'OpportunityKey':'GRANT:'+'a'*24,'source_response_sha256':'b'*64,'FunderKey':"funder:o'brien",'CategoryKeys':["category:o'brien"]},marker=marker)
    return c,l,stores,args


class DownstreamTests(unittest.TestCase):
    def test_supplied_targets_only_no_send_and_inputs_unchanged(self):
        c,l,s,args=fixture();before=copy.deepcopy((c,l,s,args));result=build(c,l,s,**args)
        self.assertEqual((c,l,s,args),before)
        self.assertEqual(result['properties']['state'],'Stopped')
        d=result['properties']['definition'];self.assertEqual(d['triggers']['manual']['kind'],'Button')
        self.assertFalse(d['actions']['Qualification_result']['inputs']['DeliveryEnabled'])
        cases=d['actions']['Select_operation']['cases']
        self.assertIn(NEW['calendar'],cases['Calendar_copy']['actions']['Cal_Write']['inputs']['parameters']['parameters/uri'])
        self.assertIn(NEW['ledger'],cases['Ledger_copy']['actions']['Led_Write']['inputs']['parameters']['parameters/uri'])
        self.assertEqual(d['actions']['Read_source_copy']['inputs']['parameters']['parameters/method'],'GET')
        predicate=d['actions']['Guard_classification_current']['inputs']
        self.assertIn("funder:o''brien",predicate)
        self.assertIn("category:o''brien",predicate)
        self.assertEqual(cases['Ledger_copy']['actions']['Led_Validate_request']['inputs']['content']['Operation'],'plan')

    def test_ambiguous_receipts_source_or_dispatch_cannot_enter_output(self):
        for fault in ['same','duplicate','marker','bool-item','child','http','foreign','unbound','mapping']:
            c,l,s,args=fixture()
            if fault=='same':s['calendar']['id']=OLD['calendar']
            elif fault=='duplicate':s['calendar']['id']=NEW['ledger']
            elif fault=='marker':s['calendar']['marker']='forged'
            elif fault=='bool-item':args['source_item_id']=True
            elif fault in ['child','http']:c['properties']['definition']['actions']['Injected']={'type':'Workflow' if fault=='child' else 'Http','inputs':{}}
            elif fault=='foreign':c['properties']['definition']['actions']['Write']['inputs']['host']['apiId']='foreign'
            elif fault=='unbound':c['properties']['definition']['actions']['Write']['inputs']['parameters']['parameters/uri']='_api/web/lists'
            else:args['mapping']['source_response_sha256']='bad'
            with self.subTest(fault=fault),self.assertRaises(ValueError):build(c,l,s,**args)

    def test_namespace_changes_only_action_names_and_references(self):
        original={'Same':{'type':'Scope','runAfter':{},'actions':{'Nested':{'type':'Compose','inputs':"@outputs('Same')"}}},
                  'Result':{'type':'Compose','runAfter':{'Same':['Succeeded']},'inputs':{'Same':'literal','expression':"@body('Nested')"}}}
        result=namespace_actions(original,'Cal_')
        self.assertEqual(result['Cal_Result']['runAfter'],{'Cal_Same':['Succeeded']})
        self.assertEqual(result['Cal_Result']['inputs'],{'Same':'literal','expression':"@body('Cal_Nested')"})
        self.assertEqual(result['Cal_Same']['actions']['Cal_Nested']['inputs'],"@outputs('Cal_Same')")
        self.assertIn('Same',original)

    def test_namespace_preserves_literal_human_text_and_target_paths_cannot_escape(self):
        actions={'One':{'type':'Compose','inputs':{'note':"human text body('One')"}}}
        self.assertEqual(namespace_actions(actions,'Cal_')['Cal_One']['inputs']['note'],"human text body('One')")
        c,l,s,args=fixture()
        c['properties']['definition']['actions']['Write']['inputs']['parameters']['parameters/uri']="_api/web/lists(guid'"+OLD['calendar']+"')/items/../../other"
        with self.assertRaises(ValueError):build(c,l,s,**args)
