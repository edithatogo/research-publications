# SPDX-License-Identifier: Apache-2.0
import unittest
from scripts.grants_acquisition_guard import strict_http_guard

class AcquisitionGuardTests(unittest.TestCase):
 def test_status_is_checked_before_json_body_shape(self):
  original="@if(and(equals(outputs('Fetch_response')?['statusCode'],200),equals(body('Fetch_response')?['errorcode'],0)),true,json('NIH_SOURCE_REJECTED'))"
  source={'actions':{'Guard_source':{'type':'Compose','inputs':original}}};result=strict_http_guard(source)
  self.assertEqual(source['actions']['Guard_source']['inputs'],original)
  self.assertTrue(result['actions']['Guard_source']['inputs'].startswith("@if(equals(outputs('Fetch_response')?['statusCode'],200),if(and("))
  self.assertTrue(result['actions']['Guard_source']['inputs'].endswith(",json('NIH_HTTP_RESPONSE_REJECTED'))"))
  with self.assertRaises(ValueError):strict_http_guard(result)

 def test_malformed_guard_preimages_are_rejected_explicitly(self):
  for node in [{'type':'Compose','inputs':True},{'type':'Http','inputs':"@if(and(equals(outputs('Fetch_response')?['statusCode'],200),true),true,false)"}]:
   with self.assertRaises(ValueError):strict_http_guard({'actions':{'Guard_source':node}})

 def fixture(self):
  from tests.test_grants_http_faults import HttpFaultTests
  diag=HttpFaultTests().fixture()
  fetch={'type':'Http','inputs':{'uri':'https://example.invalid/fixture','method':'GET','retryPolicy':{'type':'none'}}}
  sp=lambda operation,parameters:{'type':'OpenApiConnection','inputs':{'host':{'apiId':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline','operationId':operation},'parameters':parameters}}
  actions={'Guard_source':{'type':'Compose','inputs':"@if(and(equals(outputs('Fetch_response')?['statusCode'],200),true),true,false)"},
   'Processing':{'type':'Scope','actions':{}},'Acquisition':{'type':'Scope','actions':{'Fetch_response':fetch,'Fetch_attachment':fetch}},
   'Observe_processing_failure':{'type':'Scope','actions':{}},'Run_folder':{'type':'Compose','inputs':'fixture'},
   'Save_failure':sp('CreateFile',{'folderPath':"@outputs('Run_folder')"}),
   'Read_failure':sp('GetFileContentByPath',{'path':"@concat(outputs('Run_folder'),'/failure.json')"})}
  return {'actions':actions},diag

 def test_fault_graph_refuses_unknown_actions_and_transmission_nodes(self):
  from scripts.grants_acquisition_guard import fault_definition
  import copy
  source,diag=self.fixture();before=copy.deepcopy(source)
  result=fault_definition(source,diag,429)
  self.assertEqual(source,before)
  self.assertEqual(result['triggers'],diag['triggers'])
  self.assertEqual(result['actions']['Acquisition']['actions']['Fetch_response']['inputs']['uri'],'https://httpbin.org/status/429')
  for node in [{'type':'Workflow','inputs':{'name':'forbidden-child'}},{'type':'Unknown'},{'type':'Http','inputs':{'uri':'https://example.invalid/upload','method':'POST'}}]:
   source,diag=self.fixture();source['actions']['Injected']=node
   with self.assertRaises(ValueError):fault_definition(source,diag,429)
