import base64
import copy
import json
import sys
import unittest
from pathlib import Path
from scripts.prepare_arc_award_report_page import PAGE_ID, TABLE, prepare as raw_prepare, projection, page_visuals
from scripts.reconcile_arc_awards_snapshots import fingerprint


def prepare(data):
    return raw_prepare(data,expected_sha256=fingerprint(data),
                       expected_parts=[p['path'] for p in data['definition']['parts']])

class ARCAwardReaderTests(unittest.TestCase):
    def baseline(self):
        report={'config':'{}','sections':[{'name':str(i),'displayName':'Existing '+str(i),'ordinal':i,'visualContainers':[]} for i in range(8)]}
        return {'definition':{'format':'PBIR-Legacy','parts':[{'path':'report.json','payloadType':'InlineBase64','payload':base64.b64encode(json.dumps(report).encode()).decode()},{'path':'definition.pbir','payloadType':'InlineBase64','payload':base64.b64encode(b'preserved binding').decode()}]}}
    def decode(self,d):return json.loads(base64.b64decode(d['definition']['parts'][0]['payload']))
    def test_complete_preimage_drift_inventory_and_six_page_e04_rejected(self):
        data=self.baseline();pins=dict(expected_sha256=fingerprint(data),expected_parts=[p['path'] for p in data['definition']['parts']])
        changed=copy.deepcopy(data);changed['protected_human_edit']='retained'
        with self.assertRaises(ValueError):raw_prepare(changed,**pins)
        with self.assertRaises(ValueError):raw_prepare(data,expected_sha256=fingerprint(data),expected_parts=['report.json'])
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
