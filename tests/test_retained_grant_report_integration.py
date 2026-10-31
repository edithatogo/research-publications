"""One focused suite for the new additive report/model connection."""
import base64
import copy
import json
import unittest

from scripts.prepare_retained_grant_report import build, digest, PAGE, TABLE_PATH


def inputs():
    def wire(x):
        return json.dumps(x).encode()
    root = 'definition/pages/Existing/'
    files = {'definition.pbir': wire({'datasetReference': {'byConnection': {
        'connectionString': 'semanticmodelid=model-id'}}}),
        'definition/pages/pages.json': wire({'pageOrder': ['Existing'], 'activePageName': 'Existing'}),
        root + 'page.json': wire({'name': 'Existing', 'width': 1280, 'height': 720}),
        'unknown-preserved.json': b'{"unknown":true}'}
    for kind in ['textbox', 'tableEx', 'slicer']:
        files[root+'visuals/'+kind+'/visual.json'] = wire(dict(name=kind, visual=dict(
            visualType=kind, query={'stale': True}, objects={'stale': True}), filterConfig={'stale': True}))
    columns = ['PublicationPMID', 'ToLabel', 'ToKey', 'IdentityStatus', 'ReviewState',
               'SourceURL', 'SourceVersion', 'SourcePaths', 'EvidenceKey']
    table = 'table RetainedGrantReferences\n' + ''.join('\tcolumn '+c+'\n' for c in columns)
    publication = 'table Publication\n\tcolumn CanonicalKey\n\tcolumn Title\n'
    packet = {'modelDefinition': {'definition': {'parts': [dict(path=p, payloadType='InlineBase64',
              payload=base64.b64encode(t.encode()).decode()) for p,t in [
                  (TABLE_PATH,table),('definition/tables/Publication.tmdl',publication)]]}}}
    return files, packet


class GrantReportIntegrationTests(unittest.TestCase):
    def test_additive_page_exact_model_fields_filter_and_protected_content(self):
        files, packet = inputs()
        before = copy.deepcopy((files,packet))
        result = build(files,packet,expected_report_sha256=digest(files),expected_model_id='model-id')
        for path, raw in files.items():
            if path != 'definition/pages/pages.json':
                self.assertEqual(result[path],raw)
        order = json.loads(result['definition/pages/pages.json'])
        self.assertEqual(order['pageOrder'],['Existing',PAGE])
        self.assertEqual(order['activePageName'],'Existing')
        selector = json.loads(result[f'definition/pages/{PAGE}/visuals/publication-selector/visual.json'])
        self.assertIn('CanonicalKey',json.dumps(selector))
        self.assertNotIn('stale',json.dumps(selector))
        self.assertTrue(selector['visual']['query']['queryState']['Values']['projections'][0]['active'])
        self.assertIn("'Dropdown'",json.dumps(selector))
        evidence = json.loads(result[f'definition/pages/{PAGE}/visuals/grant-reference-evidence/visual.json'])
        self.assertIn('RetainedGrantReferences',json.dumps(evidence))
        self.assertIn('SourcePaths',json.dumps(evidence))
        self.assertEqual(len(evidence['visual']['objects']['columnWidth']),10)
        self.assertNotIn('SourceRelationshipEvidence',json.dumps(result,default=lambda x:x.decode()))
        self.assertEqual((files,packet),before)

    def test_refuses_capture_binding_field_and_existing_page_drift(self):
        for kind in ['capture','binding','fields','page']:
            with self.subTest(kind=kind):
                files,packet=inputs()
                expected=digest(files)
                model_id='model-id'
                if kind=='capture': files['unknown-preserved.json']=b'changed'
                elif kind=='binding': model_id='different'
                elif kind=='fields': packet['modelDefinition']['definition']['parts'][0]['payload']=base64.b64encode(b'table Missing\n').decode()
                else:
                    files[f'definition/pages/{PAGE}/page.json']=b'{}'
                    expected=digest(files)
                with self.assertRaises(ValueError):
                    build(files,packet,expected_report_sha256=expected,expected_model_id=model_id)
