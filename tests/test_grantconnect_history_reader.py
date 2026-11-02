"""Retained history must stay additive and never imply institutional funding."""
import base64
import json
import unittest

from scripts.deploy_report_definition import fingerprint, parts
from scripts.prepare_grantconnect_history_reader import prepare, TABLES


def document(files, format):
    return {'definition': {'format': format, 'parts': [
        {'path': path, 'payloadType': 'InlineBase64',
         'payload': base64.b64encode(raw.encode()).decode()}
        for path, raw in files.items()]}}


class HistoryReader(unittest.TestCase):
    def test_additive_entities_and_fail_closed_bindings(self):
        site = 'https://fictional.sharepoint.com/sites/research'
        model = document({'definition/model.tmdl': 'model Existing\n',
            'definition/tables/Existing.tmdl': 'table Existing\n\tpartition Existing = m\n\t\tsource = SharePoint.Tables("' + site + '")\n',
            'definition/relationships.tmdl': 'relationship protected\n'}, 'TMDL')
        report = document({'definition/pages/pages.json': json.dumps({'pageOrder': ['Original'], 'activePageName': 'Original'}),
                           'definition/pages/Original/page.json': '{"name":"Original"}',
                           'definition.pbir': '{"datasetReference":{"unchanged":true}}'}, 'PBIR')
        lists = {k: f'00000000-0000-4000-8000-{i:012d}' for i, k in enumerate(TABLES, 1)}
        options = dict(model_sha256=fingerprint(model), report_sha256=fingerprint(report), site=site, lists=lists)
        result = prepare(model, report, **options)
        mp, rp = parts(result['model']), parts(result['report'])
        self.assertEqual(mp['definition/relationships.tmdl'], parts(model)['definition/relationships.tmdl'])
        self.assertEqual(rp['definition.pbir'], parts(report)['definition.pbir'])
        order = json.loads(rp['definition/pages/pages.json'])
        self.assertEqual(order['activePageName'], 'Original')
        self.assertEqual(order['pageOrder'], ['Original', 'GrantConnectHistory'])
        self.assertEqual(result['process_tables'], list(TABLES.values()))
        self.assertFalse(result['native_verified'])
        self.assertIn('may be partial', rp['definition/pages/GrantConnectHistory/visuals/history-heading/visual.json'].decode())
        for entity in TABLES:
            table = json.loads(rp[f'definition/pages/GrantConnectHistory/visuals/history-{entity}/visual.json'])
            self.assertTrue(table['visual']['visualContainerObjects']['title'])
        for name in TABLES.values():
            self.assertIn(b'MissingField.Error', mp[f'definition/tables/{name}.tmdl'])
        for delta in ({'site': 'https://other.sharepoint.com/sites/research'},
                      {'lists': dict.fromkeys(TABLES, lists['awards'])},
                      {'model_sha256': '0' * 64}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                prepare(model, report, **(options | delta))
        with self.assertRaises(ValueError):
            prepare(result['model'], result['report'], **(options | {
                'model_sha256': fingerprint(result['model']),
                'report_sha256': fingerprint(result['report'])}))


if __name__ == '__main__':
    unittest.main()
