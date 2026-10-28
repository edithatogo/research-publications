import base64
import copy
import json
import sys
import unittest
from pathlib import Path
from scripts.prepare_arc_award_report_page import PAGE_ID, TABLE, prepare as raw_prepare, projection, page_visuals
from scripts.reconcile_arc_awards_snapshots import fingerprint


MODEL_ID='11111111-1111-4111-8111-111111111111'
REPORT_ID='22222222-2222-4222-8222-222222222222'


def encoded_part(path,text):
    return {'path':path,'payloadType':'InlineBase64','payload':base64.b64encode(text.encode()).decode()}


def bound_pbir():
    return json.dumps({'datasetReference':{'byConnection':{'connectionString':
        'Data Source=fixture;initial catalog=fixture;integrated security=ClaimsToken;semanticmodelid='+MODEL_ID+';'}}})


def model_fixture():
    from scripts.prepare_arc_award_model import FIELDS
    text='table ARCAwardContext\n'
    for field in FIELDS:
        text+='\tcolumn '+field+'\n\t\tdataType: string\n\t\tsummarizeBy: none\n\t\tsourceColumn: '+field+'\n'
        if field=='URL':text+='\t\tdataCategory: WebUrl\n'
    return {'format':'TMDL','parts':[encoded_part('definition/model.tmdl','model Model\nref table ARCAwardContext\n'),
        encoded_part('definition/tables/ARCAwardContext.tmdl',text)]}


def binding_fixture(data,model):
    return dict(complete=True,report_id=REPORT_ID,model_id=MODEL_ID,
        report_preimage_sha256=fingerprint(data),model_preimage_sha256=fingerprint(model),
        report_capture_ref='fixture://report-capture',model_capture_ref='fixture://model-capture',
        observed_at_utc='2026-10-29T01:00:00Z',report_binding_readback={
        'status_code':200,'text':{'id':REPORT_ID,'datasetId':MODEL_ID}})


def reader_args(data,model=None):
    model=model_fixture() if model is None else model
    evidence=binding_fixture(data,model)
    return dict(expected_sha256=fingerprint(data),expected_parts=[p['path'] for p in data['definition']['parts']],
        model_definition=model,model_expected_sha256=fingerprint(model),model_expected_parts=[p['path'] for p in model.get('definition',model)['parts']],
        binding_evidence=evidence,binding_sha256=fingerprint(evidence))


def prepare(data):
    return raw_prepare(data,**reader_args(data))

class ARCAwardReaderTests(unittest.TestCase):
    def baseline(self):
        report={'config':'{}','sections':[{'name':str(i),'displayName':'Existing '+str(i),'ordinal':i,'visualContainers':[]} for i in range(8)]}
        return {'definition':{'format':'PBIR-Legacy','parts':[{'path':'report.json','payloadType':'InlineBase64','payload':base64.b64encode(json.dumps(report).encode()).decode()},{'path':'definition.pbir','payloadType':'InlineBase64','payload':base64.b64encode(bound_pbir().encode()).decode()}]}}
    def decode(self,d):return json.loads(base64.b64decode(d['definition']['parts'][0]['payload']))
    def test_missing_wrong_and_ambiguous_model_dependencies_rejected(self):
        for mode in ('missing-table','wrong-table','missing-column','wrong-type','summary','url','duplicate-column','missing-reference'):
            data=self.baseline();model=model_fixture()
            table=base64.b64decode(model['parts'][1]['payload']).decode()
            if mode=='missing-table':model['parts'].pop()
            elif mode=='missing-reference':model['parts'][0]=encoded_part('definition/model.tmdl','model Model\n')
            else:
                if mode=='wrong-table':table=table.replace('table ARCAwardContext','table Other')
                elif mode=='missing-column':table=table.replace('column Amount','column Other')
                elif mode=='wrong-type':table=table.replace('dataType: string','dataType: int64',1)
                elif mode=='summary':table=table.replace('summarizeBy: none','summarizeBy: sum',1)
                elif mode=='url':table=table.replace('dataCategory: WebUrl','dataCategory: Uncategorized')
                else:table+='\tcolumn Amount\n\t\tdataType: string\n'
                model['parts'][1]=encoded_part('definition/tables/ARCAwardContext.tmdl',table)
            with self.subTest(mode=mode),self.assertRaises(ValueError):raw_prepare(data,**reader_args(data,model))

    def test_independent_binding_identity_and_capture_evidence_required(self):
        for mode in ('missing','dataset','report','http','capture','model-digest','complete','connection','duplicate-connection','unsupported'):
            data=self.baseline()
            if mode in ('connection','duplicate-connection','unsupported'):
                text=bound_pbir()
                if mode=='connection':text=text.replace(MODEL_ID,'33333333-3333-4333-8333-333333333333')
                elif mode=='duplicate-connection':text=text.replace('semanticmodelid='+MODEL_ID,'semanticmodelid='+MODEL_ID+';SemanticModelId='+MODEL_ID)
                else:text=json.dumps({'datasetReference':{'byPath':{'path':'../unqualified'}}})
                data['definition']['parts'][1]=encoded_part('definition.pbir',text)
            args=reader_args(data);evidence=args['binding_evidence']
            if mode=='missing':args['binding_evidence']=None
            elif mode=='dataset':evidence['report_binding_readback']['text']['datasetId']='33333333-3333-4333-8333-333333333333'
            elif mode=='report':evidence['report_binding_readback']['text']['id']='33333333-3333-4333-8333-333333333333'
            elif mode=='http':evidence['report_binding_readback']['status_code']=True
            elif mode=='capture':evidence['model_capture_ref']=''
            elif mode=='model-digest':evidence['model_preimage_sha256']='0'*64
            elif mode=='complete':evidence['complete']=False
            args['binding_sha256']=fingerprint(args['binding_evidence'])
            with self.subTest(mode=mode),self.assertRaises(ValueError):raw_prepare(data,**args)
        data=self.baseline();before=copy.deepcopy(data)
        self.assertEqual(prepare(data)['definition']['parts'][1],data['definition']['parts'][1])
        self.assertEqual(data,before)
        wrapped={'definition':model_fixture()}
        result=raw_prepare(data,**reader_args(data,wrapped))
        self.assertEqual(result['definition']['parts'][1],data['definition']['parts'][1])

    def test_complete_preimage_drift_inventory_and_six_page_e04_rejected(self):
        data=self.baseline();pins=reader_args(data)
        changed=copy.deepcopy(data);changed['protected_human_edit']='retained'
        with self.assertRaises(ValueError):raw_prepare(changed,**pins)
        with self.assertRaises(ValueError):raw_prepare(data,**dict(reader_args(data),expected_parts=['report.json']))
        report=self.decode(data);report['sections']=report['sections'][:6]
        data['definition']['parts'][0]['payload']=base64.b64encode(json.dumps(report).encode()).decode()
        with self.assertRaisesRegex(ValueError,'eight-page'):prepare(data)
        with self.assertRaisesRegex(ValueError,'Legacy'):prepare({'definition':{'format':'PBIR','parts':[]}})

    def test_ambiguous_inner_report_and_duplicate_parts_rejected(self):
        data=self.baseline();data['definition']['parts'][0]['payload']=base64.b64encode(b'{"sections":[],"sections":[]}').decode()
        with self.assertRaisesRegex(ValueError,'Duplicate JSON'):prepare(data)
        data=self.baseline();data['definition']['parts'].append(copy.deepcopy(data['definition']['parts'][0]))
        with self.assertRaises(ValueError):prepare(data)

    def test_additive_preserves_eight_pages_and_binding_and_source(self):
        before=self.baseline();saved=copy.deepcopy(before);after=prepare(before)
        self.assertEqual(before,saved);self.assertEqual(self.decode(before)['sections'],self.decode(after)['sections'][:-1]);self.assertEqual(before['definition']['parts'][1:],after['definition']['parts'][1:]);self.assertEqual(self.decode(after)['sections'][-1]['name'],PAGE_ID)
    def test_existing_page_rejected(self):
        with self.assertRaises(ValueError):prepare(prepare(self.baseline()))
    def test_unexpected_baseline_rejected(self):
        b=self.baseline();r=self.decode(b);r['sections'].pop();b['definition']['parts'][0]['payload']=base64.b64encode(json.dumps(r).encode()).decode()
        with self.assertRaises(ValueError):prepare(b)
    def test_count_uses_nonempty_unique_source_id_not_amount(self):
        p=projection('SourceID',count=True);self.assertEqual(p['field']['Aggregation']['Function'],5);self.assertEqual(p['field']['Aggregation']['Expression']['Column']['Property'],'SourceID')
        with self.assertRaises(ValueError):projection('Amount',count=True)
    def test_semantics_filters_links_and_no_amount_aggregation(self):
        visuals,_=page_visuals();s=json.dumps(visuals);self.assertIn('not funding opportunities or applications',s);self.assertIn('not CHHHS',s);self.assertIn('Blank source amounts',s)
        by={json.loads(v['config'])['name']:json.loads(v['config'])['singleVisual'] for v in visuals}
        self.assertEqual(by['arc-source']['visualType'],'slicer');self.assertEqual(by['arc-status']['visualType'],'slicer');self.assertIn('urlIcon',json.dumps(by['arc-records']['objects']));self.assertNotIn('Aggregation',json.dumps([x for x in by['arc-records']['prototypeQuery']['Select'] if x['Name']==TABLE+'.Amount']))
        self.assertNotIn('webURL',json.dumps(by['arc-records']['objects']))
    def test_visual_rectangles_stay_on_page(self):
        _,visuals=page_visuals()
        for v in visuals:
            p=v['position'];self.assertGreaterEqual(p['x'],0);self.assertGreaterEqual(p['y'],0);self.assertLessEqual(p['x']+p['width'],1920);self.assertLessEqual(p['y']+p['height'],1080)
if __name__=='__main__':unittest.main()
