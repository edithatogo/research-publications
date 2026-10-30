import copy
import unittest
from scripts.outcome_intake import prepare_batch, recovery_plan
from scripts.outcome_persistence import load_snapshot, encode as journal_encode, restore
from scripts.prepare_outcome_binding import prepare as bind
from scripts.prepare_outcome_reader import prepare as reader
from scripts.prepare_outcome_flow import prepare_paired
from scripts.deploy_report_definition import fingerprint, parts
from scripts.powerplatform_validation import validate_flow
from test_outcome_evidence import event, observation, references, encode, revised
import test_outcome_reader as reader_fixtures

CONTEXT = dict(cutoff_utc='2026-03-01T00:00:00Z',source_snapshot='FIC-SOURCE',model_revision='FIC-MODEL',report_revision='FIC-REPORT')
TARGET = dict(listUrl="https://example.sharepoint.com/sites/fictional/_api/web/lists(guid'00000000-0000-0000-0000-000000000001')",itemId=1,journalField='OutcomeJournal',projectionField='OutcomeProjection')
def snapshot():
    return dict(item_id=1,etag='"1"',journal=journal_encode({'version':1,'entries':[]}),projection='{}')

class IntakeTests(unittest.TestCase):
    def test_complete_fictional_batch_projection_binding_flow_reader(self):
        p=prepare_batch(snapshot(),[(encode(event()),None),(encode(observation()),None)],references(),CONTEXT)
        tables=load_snapshot(p['after']['projection'])
        self.assertEqual(len(tables['OutcomeObservation']),1)
        self.assertEqual(len(tables['EventProject']),2)
        f=reader_fixtures.OutcomeReaderTests();f.setUp()
        f.model['definition']['format']='TMDL'
        f.report['definition']['format']='PBIR'
        # Replace the fixture expression with an unrelated, preserved expression.
        import base64
        f.model['definition']['parts'][0]['payload']=base64.b64encode(b'expression Retained = 1\n').decode()
        binding=bind(f.model,TARGET,expected_sha256=fingerprint(f.model))
        built=reader(binding['candidate'],f.report,model_sha256=fingerprint(binding['candidate']),report_sha256=fingerprint(f.report),source_expression_sha256=binding['expression_sha256'],card_template_path='card.json',table_template_path='table.json')
        self.assertEqual(parts(built['model'])['unknown.txt'],b'preserved')
        self.assertEqual(built['model']['definition']['format'],'TMDL')
        self.assertEqual(built['report']['definition']['format'],'PBIR')
        self.assertIn(b'SharePoint.Tables',parts(built['model'])['definition/expressions.tmdl'])
        e={'properties':{'definition':{'triggers':{'manual':{'type':'Request','kind':'Button'}},'actions':{}},'connectionReferences':{'shared_sharepointonline':{}}}}
        a={'type':'OpenApiConnection','inputs':{'host':{'operationId':'HttpRequest','apiId':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline','connectionName':'shared_sharepointonline'},'parameters':{}},'runAfter':{}}
        flow=prepare_paired(e,p,item_id=1,projection_field='OutcomeProjection',expected_sha256=fingerprint(e),accepted_action=a,action_sha256=fingerprint(a),site_url='https://example.sharepoint.com/sites/fictional',list_id='00000000-0000-0000-0000-000000000001',field_name='OutcomeJournal')
        self.assertEqual(validate_flow(flow['candidate'])['status'],'PASS')
        body=flow['candidate']['properties']['definition']['actions']['Apply_or_replay']['else']['actions']['Write_once']['inputs']['parameters']['parameters/body']
        self.assertEqual(body,dict(OutcomeJournal=p['after']['journal'],OutcomeProjection=p['after']['projection']))

    def test_replay_revision_withdrawal_and_recovery_preserve_preimages(self):
        records=[(encode(event()),None),(encode(observation()),{'limitations':'FICTIONAL protected'})]
        p=prepare_batch(snapshot(),records,references(),CONTEXT)
        current=dict(item_id=1,etag='"2"',**p['after'])
        replay=prepare_batch(current,records,references(),CONTEXT)
        self.assertEqual(replay['after'],p['after'])
        withdrawal=revised(event(),'FIC-T-R2','FIC-T-R1');withdrawal['verification']['status']='withdrawn'
        next_plan=prepare_batch(current,[(encode(withdrawal),None)],references(),CONTEXT)
        self.assertEqual(load_snapshot(next_plan['after']['projection'])['OutcomeObservation'],[])
        self.assertIn('FICTIONAL protected',restore(load_snapshot(next_plan['after']['journal']))[1].effective_json)
        self.assertEqual(recovery_plan(p,current)['after'],p['before'])
        current['projection']='{"human":"changed"}'
        with self.assertRaisesRegex(ValueError,'Intervening'): recovery_plan(p,current)

    def test_invalid_batch_never_produces_partial_candidate(self):
        original=snapshot();before=copy.deepcopy(original)
        with self.assertRaises(ValueError): prepare_batch(original,[(encode(event()),None),(b'{"kind":1,"kind":2}',None)],references(),CONTEXT)
        self.assertEqual(original,before)
        with self.assertRaises(ValueError): prepare_batch(original,[],references(),CONTEXT)
