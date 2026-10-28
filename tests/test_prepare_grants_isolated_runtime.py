# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from scripts.build_grants_runtime_cases import build_cases
from scripts.prepare_grants_isolated_runtime import build

OLD='12345678-1234-1234-1234-123456789abc';NEW='22345678-1234-1234-1234-123456789abc'


class IsolatedRuntimeTests(unittest.TestCase):
    def fixture(self):
        source={'parameters':{},'triggers':{},'actions':{
            'Parse_Reviewed_Rows':{'type':'Compose','inputs':'old input'},
            'SharePoint_Get_items':{'type':'OpenApiConnection','inputs':{
                'host':{'apiId':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline','operationId':'GetItems'},
                'parameters':{'dataset':'https://example.invalid','table':OLD}}}}}
        diagnostic={'triggers':{'manual':{'type':'Request','kind':'Button','inputs':{'schema':{
            'type':'object','additionalProperties':False,'properties':{}}}}}}
        owned={'id':NEW,'marker':'TEST_ONLY_G07_RECOVERY_20261028','title':'TEST_ONLY_G07_RECOVERY_20261028_RESTORED'}
        case=build_cases('2026-10-28T00:00:00Z')['cases'][0]
        return source,diagnostic,owned,case

    def test_only_target_identity_and_fixed_input_are_rebound(self):
        s,d,o,c=self.fixture();before=copy.deepcopy(s);result=build(s,d,o,c)
        self.assertEqual(result['actions']['SharePoint_Get_items']['inputs']['parameters']['table'],NEW)
        self.assertEqual(result['actions']['Parse_Reviewed_Rows']['inputs'],"@json(parameters('QualificationRowsJson'))")
        self.assertEqual(s,before)
        self.assertEqual(result['triggers'],d['triggers'])

    def test_real_keys_sources_writes_and_automatic_triggers_are_rejected(self):
        for fault in ['key','source','write','trigger','receipt']:
            s,d,o,c=self.fixture()
            if fault=='key':c['rows'][0]['OpportunityKey']='GRANT:real-key'
            elif fault=='source':c['rows'][0]['Source']='real-source'
            elif fault=='write':s['actions']['External']={'type':'Http','inputs':{'method':'POST'}}
            elif fault=='trigger':d['triggers']['manual']['type']='Recurrence'
            else:o['title']='canonical'
            with self.assertRaises(ValueError):build(s,d,o,c)

    def test_hidden_dispatch_and_cross_site_operations_are_refused(self):
        for fault in ['child','unknown','foreign-site','unbound-write','wildcard-merge']:
            s,d,o,c=self.fixture()
            if fault in ['child','unknown']:
                s['actions']['Injected']={'type':'Workflow' if fault=='child' else 'Unknown','inputs':{}}
            else:
                node=copy.deepcopy(s['actions']['SharePoint_Get_items'])
                if fault=='foreign-site':node['inputs']['parameters']['dataset']='https://other.invalid'
                elif fault=='unbound-write':node['inputs']['host']['operationId']='PostItem';node['inputs']['parameters'].pop('table')
                else:
                    node['inputs']['host']['operationId']='HttpRequest';node['inputs']['parameters']={
                        'dataset':'https://example.invalid','parameters/uri':"_api/web/lists(guid'"+OLD+"')/items(1)",
                        'parameters/method':'POST','parameters/headers':{'X-HTTP-Method':'MERGE','IF-MATCH':'*'}}
                s['actions']['Injected']=node
            with self.subTest(fault=fault),self.assertRaises(ValueError):build(s,d,o,c)

    def test_noncanonical_receipt_id_and_source_row_labels_do_not_gain_authority(self):
        for target in [NEW.upper(),'{'+NEW+'}',None]:
            s,d,o,c=self.fixture();o['id']=target
            with self.subTest(target=target),self.assertRaises(ValueError):build(s,d,o,c)

    def test_target_uri_cannot_escape_owned_list(self):
        s,d,o,c=self.fixture()
        s['actions']['Escaped']={'type':'OpenApiConnection','inputs':{
            'host':{'apiId':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline','operationId':'HttpRequest'},
            'parameters':{'dataset':'https://example.invalid','parameters/method':'GET',
                'parameters/uri':"_api/web/lists(guid'"+OLD+"')/items(1)/../../other"}}}
        with self.assertRaises(ValueError):build(s,d,o,c)

    def test_conditional_merge_precondition_payload_and_archive_branch_are_retained(self):
        s,d,o,c=self.fixture()
        merge={'type':'OpenApiConnection','runAfter':{},'inputs':{
            'host':{'apiId':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline','operationId':'HttpRequest'},
            'parameters':{'dataset':'https://example.invalid','parameters/method':'POST',
                'parameters/uri':"_api/web/lists(guid'"+OLD+"')/items(1)",
                'parameters/headers':{'X-HTTP-Method':'MERGE','IF-MATCH':'"7"'},
                'parameters/body':{'DeadlineRaw':'source-stated unknown time','EvidenceHash':'c'*64}}}}
        s['actions']['Preserve_original']={'type':'If','expression':'@equals(1,1)','actions':{'Save':merge},'else':{'actions':{}}}
        result=build(s,d,o,c);out=result['actions']['Preserve_original']
        self.assertEqual(out['expression'],'@equals(1,1)')
        params=out['actions']['Save']['inputs']['parameters']
        self.assertEqual(params['parameters/headers'],merge['inputs']['parameters']['parameters/headers'])
        self.assertEqual(params['parameters/body'],merge['inputs']['parameters']['parameters/body'])
        self.assertEqual(params['parameters/uri'],"_api/web/lists(guid'"+NEW+"')/items(1)")
