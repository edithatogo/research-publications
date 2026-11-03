import base64
import json
import unittest

from scripts.deploy_report_definition import fingerprint, parts
from scripts.prepare_t18_source_quality import PAGE, prepare
from scripts.prepare_t18_indicator_model import DISPOSITIONS


def fixture():
    files = {
        PAGE + 'page.json': {'displayName': 'Publication Sources & Quality'},
        PAGE + 'visuals/reconciliation-register/visual.json': {
            'position': {'y': 552, 'height': 352}, 'name': 'reconciliation-register',
            'visual': {'visualType': 'tableEx', 'query': {'preserve': ['CanonicalKey', 'source links']}}},
        'definition/pages/ReportSection3/visuals/heading/visual.json': {'$schema': 'https://example.test/synthetic-schema'},
        'definition.pbir': {'binding': 'fictional retained target'},
    }
    return {'definition': {'parts': [{'path': p, 'payloadType': 'InlineBase64',
                'payload': base64.b64encode(json.dumps(d).encode()).decode()} for p, d in files.items()]}}


class SourceQualityTests(unittest.TestCase):
    def test_preserves_detail_query_binding_and_unrelated_parts(self):
        before = fixture()
        result = prepare(before, expected_sha256=fingerprint(before))
        a, b = parts(before), parts(result)
        for path in a:
            if path != PAGE + 'visuals/reconciliation-register/visual.json':
                self.assertEqual(a[path], b[path])
        path = PAGE + 'visuals/reconciliation-register/visual.json'
        old, new = json.loads(a[path]), json.loads(b[path])
        self.assertEqual(old['visual'], new['visual'])
        self.assertEqual(new['position']['y'] + new['position']['height'], 904)

    def test_every_known_and_unrecognised_disposition_has_a_measure_binding(self):
        before = fixture()
        result = parts(prepare(before, expected_sha256=fingerprint(before)))
        doc = json.loads(result[PAGE + 'visuals/t18-provider-dispositions/visual.json'])
        self.assertEqual(doc['visual']['visualType'], 'tableEx')
        projections = doc['visual']['query']['queryState']['Values']['projections']
        self.assertEqual(len(projections), len(DISPOSITIONS) + 1)
        self.assertEqual(doc['position']['y'] + doc['position']['height'] + 16, 712)
        self.assertEqual([p['displayName'] for p in projections[1:]],
                         [name.capitalize() for name in DISPOSITIONS])

    def test_refuses_layout_or_preimage_drift(self):
        before = fixture()
        with self.assertRaisesRegex(ValueError, 'preimage drift'):
            prepare(before, expected_sha256='0' * 64)
        after = prepare(before, expected_sha256=fingerprint(before))
        with self.assertRaisesRegex(ValueError, 'already exists'):
            prepare(after, expected_sha256=fingerprint(after))


if __name__ == '__main__':
    unittest.main()
