import unittest
from scripts.prepare_outcome_flow import prepare
from scripts.deploy_report_definition import fingerprint
from scripts.outcome_persistence import prepare as journal_plan
from test_outcome_persistence import Transport
from test_outcome_evidence import event,encode,references

class OutcomeFlowTests(unittest.TestCase):
    def test_frozen_update_preserves_reference_no_retry_and_manual_trigger(self):
        e={'properties':{'definition':{'triggers':{'manual':{'type':'Request','kind':'Button'}},'actions':{}},'connectionReferences':{'shared_sharepointonline':{'preserved':'fixture'}}}}
        a={'type':'OpenApiConnection','inputs':{'host':{'operationId':'HttpRequest','apiId':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline','connectionName':'shared_sharepointonline'},'parameters':{}},'runAfter':{}}
        p=journal_plan(Transport().read(1),encode(event()),references())
        r=prepare(e,p,expected_sha256=fingerprint(e),accepted_action=a,action_sha256=fingerprint(a),site_url='https://example.sharepoint.com/sites/fictional',list_id='00000000-0000-0000-0000-000000000001',field_name='OutcomeJournal')
        self.assertEqual(r['candidate']['properties']['connectionReferences'],e['properties']['connectionReferences'])
        write=r['candidate']['properties']['definition']['actions']['Apply_or_replay']['else']['actions']['Write_once']
        self.assertEqual(write['inputs']['retryPolicy'],{'type':'none'})
        self.assertEqual(write['inputs']['parameters']['parameters/headers']['IF-MATCH'],p['etag'])
        self.assertEqual(e['properties']['definition']['actions'],{})
        self.assertFalse(r['native_ready'])
        from scripts.powerplatform_validation import validate_flow
        check = validate_flow(r['candidate'])
        self.assertEqual(check['status'], 'PASS', check)
