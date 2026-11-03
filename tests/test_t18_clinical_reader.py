"""Bounded repair tests; fictional definitions do not establish native rendering."""
import base64
import copy
import json
import unittest

from scripts.deploy_report_definition import fingerprint, parts
from scripts.prepare_t18_clinical_reader import PAGE, TEXT, TITLES, literal, prepare


def fixture():
    files = {'definition.pbir': {'datasetReference': {'fixture': 'unchanged'}},
             PAGE + 'page.json': {'displayName': 'Clinical Analytics', 'name': 'ReportSection4'},
             'definition/pages/Other/page.json': {'name': 'Other', 'filters': ['retained']}}
    for name, (old, _) in TITLES.items():
        files[PAGE + 'visuals/' + name + '/visual.json'] = {
            'name': name, 'position': {'x': 32, 'y': 112, 'width': 440, 'height': 96},
            'visual': {'visualType': 'card', 'visualContainerObjects': {
                'title': [{'properties': {'text': {'expr': {'Literal': {'Value': literal(old)}}}}}]},
                'query': {'field': {'Measure': {'Expression': {'SourceRef': {'Entity': 'Publication'}},
                                               'Property': 'Open Access Rate'}},
                          'queryRef': 'Publication.Open Access Rate'}}}
    for name, (prefix, _) in TEXT.items():
        files[PAGE + 'visuals/' + name + '/visual.json'] = {'name': name, 'visual': {
            'objects': {'general': [{'properties': {'paragraphs': [{'textRuns': [{'value': prefix + ' fixture'}]}]}}]}}}
    return {'definition': {'parts': [{'path': p, 'payloadType': 'InlineBase64',
            'payload': base64.b64encode(json.dumps(v).encode()).decode()} for p, v in files.items()]}}


class RepairTests(unittest.TestCase):
    def test_preserves_bindings_queries_unrelated_parts_and_preimage(self):
        before = fixture()
        original = copy.deepcopy(before)
        after = prepare(before, expected_sha256=fingerprint(before))
        self.assertEqual(before, original)
        a, b = parts(before), parts(after)
        for path in a:
            if not path.startswith(PAGE + 'visuals/'):
                self.assertEqual(a[path], b[path])
            elif path.split('/')[-2] in TITLES:
                self.assertEqual(json.loads(a[path])['visual']['query'], json.loads(b[path])['visual']['query'])
                self.assertEqual(json.loads(a[path])['name'], json.loads(b[path])['name'])
        self.assertEqual(len(b), len(a) + 2)

    def test_coverage_cards_bind_to_distinct_existing_measures(self):
        before = fixture()
        after = parts(prepare(before, expected_sha256=fingerprint(before)))
        for name, measure in [('oa-assessed', 'K02 OA assessed publications'),
                              ('oa-coverage', 'K02 OA assessment coverage')]:
            d = json.loads(after[PAGE + 'visuals/' + name + '/visual.json'])
            self.assertEqual(d['visual']['query']['field']['Measure']['Property'], measure)
            self.assertEqual(d['visual']['query']['queryRef'], 'Publication.' + measure)
        rects = [json.loads(after[PAGE + 'visuals/' + n + '/visual.json'])['position']
                 for n in ['oa-rate', 'oa-papers', 'oa-assessed', 'oa-coverage', 'trials-count', 'funded-papers']]
        self.assertTrue(all(a['x'] + a['width'] + 16 == b['x'] for a, b in zip(rects, rects[1:])))
        self.assertEqual(rects[-1]['x'] + rects[-1]['width'], 1888)

    def test_refuses_fingerprint_title_drift_or_second_application(self):
        before = fixture()
        with self.assertRaisesRegex(ValueError, 'preimage drift'):
            prepare(before, expected_sha256='0' * 64)
        after = prepare(before, expected_sha256=fingerprint(before))
        with self.assertRaisesRegex(ValueError, 'title preimage drift'):
            prepare(after, expected_sha256=fingerprint(after))

    def test_native_height_repair_keeps_controls_and_detail_inside_canvas(self):
        before = fixture()
        docs = {p: json.loads(v) for p, v in parts(before).items()}
        docs[PAGE + 'page.json'].update(width=1920, height=1296)
        for name, x, width in [('facility-filter', 32, 608), ('year-filter', 656, 304),
                               ('oa-filter', 976, 440), ('study-filter', 1432, 456),
                               ('49abdc3e306c680aa070', 32, 1856)]:
            docs[PAGE + 'visuals/' + name + '/visual.json'] = {
                'name': name, 'position': {'x': x, 'width': width, 'y': 212, 'height': 96},
                'visual': {'query': {'retained': name}}}
        for name, x in [('specialty-distribution', 32), ('for-division', 960),
                        ('oa-distribution', 32), ('study-design-breakdown', 960)]:
            docs[PAGE + 'visuals/' + name + '/visual.json']['position'].update(x=x, width=912)
        docs[PAGE + 'visuals/footer/visual.json']['position'] = {
            'x': 32, 'y': 960, 'width': 1856, 'height': 40}
        before['definition']['parts'] = [{'path': p, 'payloadType': 'InlineBase64',
            'payload': base64.b64encode(json.dumps(v).encode()).decode()} for p, v in docs.items()]
        after = {p: json.loads(v) for p, v in parts(prepare(before, expected_sha256=fingerprint(before))).items()}
        self.assertEqual(after[PAGE + 'page.json']['height'], 1080)
        rects = [v['position'] for p, v in after.items() if p.startswith(PAGE + 'visuals/') and 'position' in v]
        self.assertTrue(all(r['x'] + r['width'] <= 1920 and r['y'] + r['height'] <= 1080 for r in rects))
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                self.assertTrue(a['x'] + a['width'] <= b['x'] or b['x'] + b['width'] <= a['x']
                                or a['y'] + a['height'] <= b['y'] or b['y'] + b['height'] <= a['y'])
        for name in ['facility-filter', 'year-filter', 'oa-filter', 'study-filter']:
            self.assertEqual(after[PAGE + 'visuals/' + name + '/visual.json']['position']['height'], 96)


if __name__ == '__main__':
    unittest.main()
