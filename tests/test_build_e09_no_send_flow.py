# SPDX-License-Identifier: Apache-2.0
import unittest
import copy
import json
from scripts.build_e09_no_send_flow import definition, validate_no_send_definition


class FlowContractTests(unittest.TestCase):
    def test_only_owned_sharepoint_target_no_sender_no_recurrence(self):
        guid = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
        graph = definition('https://example.sharepoint.com/sites/qualification', guid)
        self.assertEqual(graph['triggers']['manual']['kind'], 'Button')
        self.assertEqual(graph['triggers']['manual']['runtimeConfiguration']['concurrency']['runs'], 1)
        connectors = []
        def visit(value):
            if isinstance(value, dict):
                if value.get('type') == 'OpenApiConnection':
                    inputs = value['inputs']; connectors.append(inputs['host']['apiId'])
                    self.assertEqual(inputs['retryPolicy'], {'type': 'none'})
                    self.assertIn(guid, inputs['parameters']['parameters/uri'])
                if value.get('type') == 'ParseJson':
                    self.assertNotIn('"pattern"', __import__('json').dumps(value['inputs']['schema']))
                for child in value.values(): visit(child)
            elif isinstance(value, list):
                for child in value: visit(child)
        visit(graph)
        self.assertEqual(set(connectors), {'/providers/Microsoft.PowerApps/apis/shared_sharepointonline'})
        guard = graph['actions']['Require_no_send_identity']['inputs']['content']['ok']
        self.assertIn('NoSendOnly', guard)
        self.assertIn('delivery_authority_reference', guard)
        condition = graph['actions']['Persist_or_preserve_mapping']['else']['actions']['Check_uncertain_outcome']
        self.assertIn('reconciliation_required', condition['expression'])
        self.assertNotIn('Update_mapping', condition['actions'])

    def test_unqualified_target_refused_before_native_work(self):
        for site, identity in [('http://example.sharepoint.com', 'x'),
                               ('https:///missing-host', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),
                               ('https://other.invalid', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa')]:
            with self.assertRaises(ValueError): definition(site, identity)

    def graph(self):
        return definition('https://example.sharepoint.com/sites/qualification', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa')

    def validate(self, graph):
        return validate_no_send_definition(graph,'https://example.sharepoint.com/sites/qualification','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa')

    def test_artifact_roundtrip_and_explicit_no_authority_schemas(self):
        graph=self.graph();self.assertEqual(self.validate(json.loads(json.dumps(graph))),graph)
        schema=graph['triggers']['manual']['inputs']['schema']
        self.assertEqual(schema['properties']['NoSendOnly'],{'type':'boolean','enum':[True]})
        self.assertFalse(schema['additionalProperties'])
        receipt=graph['actions']['Parse_thread']['inputs']['schema']['properties']['delivery_receipt']['properties']
        self.assertEqual(receipt['intended_outcome'],{'enum':['no_send']})
        self.assertEqual(receipt['post_reference'],{'type':'null'})
        self.assertEqual(receipt['delivery_authority_reference'],{'type':'null'})

    def test_nested_sender_http_child_workflow_and_unknown_nodes_are_rejected(self):
        for node in [dict(type='Http',inputs={'method':'POST','uri':'https://graph.microsoft.com/v1.0/me/sendMail'}),
                     dict(type='Workflow',inputs={'name':'other-flow'}),dict(type='Unknown'),
                     dict(type='OpenApiConnection',inputs={'host':{'apiId':'shared_office365','operationId':'SendEmailV2'}})]:
            graph=self.graph();graph['actions']['Persist_or_preserve_mapping']['else']['actions']['Injected_dispatch']=node
            with self.subTest(node=node['type']),self.assertRaises(ValueError):self.validate(graph)

    def test_connector_target_operation_and_retry_changes_are_rejected(self):
        for change in ['site','uri','method','connector','retry']:
            graph=self.graph();inputs=graph['actions']['Read_thread']['inputs'];params=inputs['parameters']
            if change=='site':params['dataset']='https://other.sharepoint.com/sites/qualification'
            elif change=='uri':params['parameters/uri']="_api/web/lists(guid'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb')/items"
            elif change=='method':params['parameters/method']='DELETE'
            elif change=='connector':inputs['host']['operationId']='SendEmailV2'
            else:inputs['retryPolicy']={'type':'exponential'}
            with self.subTest(change=change),self.assertRaises(ValueError):self.validate(graph)

    def test_delivery_authority_schedule_guard_bypass_and_provider_outputs_are_rejected(self):
        for change in ['trigger','default','receipt','guard','runAfter','provider','compose-dispatch']:
            graph=self.graph()
            if change=='trigger':graph['triggers']['recurrence']={'type':'Recurrence','recurrence':{'frequency':'Day','interval':1}}
            elif change=='default':graph['parameters']['delivery_authority_active']={'type':'Bool','defaultValue':True}
            elif change=='receipt':graph['actions']['Parse_thread']['inputs']['schema']['properties']['delivery_receipt']['properties']['delivery_authority_reference']={'type':'string','default':'authority:unqualified'}
            elif change=='guard':graph['actions']['Require_no_send_identity']['inputs']['content']['ok']='@true'
            elif change=='runAfter':graph['actions']['Read_thread']['runAfter']={}
            elif change=='provider':graph['actions']['No_send_result']['inputs']['provider_reference']='invented:post'
            else:graph['actions']['Injected_dispatch']={'type':'Compose','inputs':{'dispatch':True}}
            with self.subTest(change=change),self.assertRaises(ValueError):self.validate(graph)

    def test_encoded_traversal_ports_padded_or_malformed_targets_fail_before_build(self):
        for site in [' https://example.sharepoint.com/sites/qualification',
                     'https://example.sharepoint.com:8443/sites/qualification',
                     'https://example.sharepoint.com/sites/../other',
                     'https://example.sharepoint.com/sites/%252fother',
                     'https://example.sharepoint.com/sites/qualification#fragment',None]:
            with self.subTest(site=site),self.assertRaises(ValueError):definition(site,'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa')
        with self.assertRaises(ValueError):definition('https://example.sharepoint.com/sites/qualification',False)

    def test_factory_policy_rejects_accidental_sender_even_in_new_template(self):
        from unittest.mock import patch
        graph=self.graph();graph['actions']['Factory_sender']={'type':'Http','inputs':{}}
        with patch('scripts.build_e09_no_send_flow._definition',return_value=graph):
            with self.assertRaises(ValueError):definition('https://example.sharepoint.com/sites/qualification','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa')

    def test_factory_policy_independently_rejects_new_implicit_authority(self):
        from unittest.mock import patch
        for change in ['no-send-input','authority','result','outputs']:
            graph=self.graph()
            if change=='no-send-input':graph['triggers']['manual']['inputs']['schema']['properties']['NoSendOnly']={'type':'boolean'}
            elif change=='authority':graph['actions']['Parse_thread']['inputs']['schema']['properties']['delivery_receipt']['properties']['delivery_authority_reference']={'type':'string'}
            elif change=='result':graph['actions']['No_send_result']['inputs']['message_created']=True
            else:graph['outputs']={'dispatch_enabled':{'type':'Bool','value':True}}
            with self.subTest(change=change),patch('scripts.build_e09_no_send_flow._definition',return_value=graph):
                with self.assertRaises(ValueError):definition('https://example.sharepoint.com/sites/qualification','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa')
