import base64
import json
import unittest
from scripts.prepare_project_link_reader import prepare, TABLES
from scripts.deploy_report_definition import parts, fingerprint
from scripts.prepare_outcome_reader import emit

class ProjectLinkReaderTests(unittest.TestCase):
    def test_additive_model_and_report(self):
        model={'definition':{'parts':[]}};report={'definition':{'parts':[]}}
        for path,text in [('definition/model.tmdl','model Model\n'),('definition/expressions.tmdl','expression Existing = 1\n'),('definition/relationships.tmdl',''),('definition/tables/Existing.tmdl','table Existing\n')]:emit(model,path,text)
        for path,value in [('definition/pages/pages.json',{'pageOrder':['Existing'],'activePageName':'Existing'}),('definition/pages/Existing/page.json',{'$schema':'accepted-page','name':'Existing'}),('definition/pages/Existing/visuals/a/visual.json',{'$schema':'accepted-visual','visual':{'visualType':'tableEx'}}),('definition/report.json',{'existing':True,'linguisticSchemaSyncVersion':1}),('definition.pbir',{'datasetReference':'preserved'})]:emit(report,path,json.dumps(value))
        target={'listUrl':"https://example.invalid/site/_api/web/lists(guid'11111111-1111-1111-1111-111111111111')",'itemId':1,'journalField':'ProjectLinkJournal','projectionField':'ProjectLinkProjection'}
        r=prepare(model,report,target,model_sha256=fingerprint(model),report_sha256=fingerprint(report));mp,rp=parts(r['model']),parts(r['report'])
        self.assertEqual(mp['definition/tables/Existing.tmdl'],parts(model)['definition/tables/Existing.tmdl'])
        for path in ['definition.pbir','definition/pages/Existing/page.json','definition/pages/Existing/visuals/a/visual.json']:self.assertEqual(rp[path],parts(report)[path])
        self.assertEqual(json.loads(rp['definition/pages/pages.json'])['activePageName'],'Existing')
        self.assertIn(b'ProjectLinkProjection',mp['definition/expressions.tmdl'])
        self.assertIn(b'"history_sha256"',mp['definition/expressions.tmdl'])
        for name in TABLES:self.assertIn(b'Table.FromRecords(Rows, {',mp['definition/tables/'+name+'.tmdl'])
        self.assertIn(b'Record.Field(Payload, "bridges")',mp['definition/tables/ProjectOutputBridge.tmdl'])
        with self.assertRaises(ValueError):prepare(r['model'],r['report'],target,model_sha256=fingerprint(r['model']),report_sha256=fingerprint(r['report']))
