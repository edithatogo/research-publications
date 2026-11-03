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
                 for n in ['oa-rate', 'oa-papers', 'trials-count', 'funded-papers', 'oa-assessed', 'oa-coverage']]
        self.assertTrue(all(a['x'] + a['width'] + 16 == b['x'] for a, b in zip(rects, rects[1:])))
        self.assertEqual(rects[-1]['x'] + rects[-1]['width'], 1888)

    def test_refuses_fingerprint_title_drift_or_second_application(self):
        before = fixture()
        with self.assertRaisesRegex(ValueError, 'preimage drift'):
            prepare(before, expected_sha256='0' * 64)
        after = prepare(before, expected_sha256=fingerprint(before))
        with self.assertRaisesRegex(ValueError, 'title preimage drift'):
            prepare(after, expected_sha256=fingerprint(after))


if __name__ == '__main__':
    unittest.main()
