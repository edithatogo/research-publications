"""Indicator revisions must preserve native definitions and fail closed on drift."""
import base64
import copy
import json
from pathlib import Path
import unittest

from scripts.deploy_report_definition import fingerprint, parts
from scripts.prepare_t18_indicator_model import PATH, dictionary_rows, prepare


class IndicatorTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((Path(__file__).resolve().parents[1] / 'contracts/t18-outcome-indicators.json').read_text())
        texts = {'definition/model.tmdl': 'model Model\n\nref table Publication\n'}
        for metric in self.contract['metrics']:
            if metric.get('measure'):
                path = 'definition/tables/' + metric['source_table'] + '.tmdl'
                texts.setdefault(path, "table '" + metric['source_table'] + "'\n")
                texts[path] += "\tmeasure '" + metric['measure'] + "' = 1\n"
        self.before = {'definition': {'parts': [{'path': p, 'payloadType': 'InlineBase64',
                        'payload': base64.b64encode(v.encode()).decode()} for p, v in texts.items()]}}

    def test_only_dictionary_and_model_reference_change(self):
        before = copy.deepcopy(self.before)
        result = prepare(before, self.contract, expected_sha256=fingerprint(before))
        self.assertEqual(before, self.before)
        a, b = parts(before), parts(result)
        self.assertEqual(set(b) - set(a), {PATH})
        for path in a:
            if path != 'definition/model.tmdl':
                self.assertEqual(a[path], b[path])

    def test_missing_evidence_has_reason_no_invented_owner_target_or_metric(self):
        rows = dictionary_rows(self.contract)
        missing = [r for r in rows if r['Readiness'] == 'evidence-dependent']
        self.assertTrue(missing)
        self.assertTrue(all(r['UnavailableReason'] for r in missing))
        self.assertTrue(all(not r['MeasureName'] for r in missing))
        changed = copy.deepcopy(self.contract)
        changed['metrics'][0]['target'] = 100
        with self.assertRaisesRegex(ValueError, 'Authority-bound'):
            dictionary_rows(changed)

    def test_rejects_duplicate_identity_missing_measure_and_preimage_drift(self):
        changed = copy.deepcopy(self.contract)
        changed['metrics'].append(copy.deepcopy(changed['metrics'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            dictionary_rows(changed)
        changed = copy.deepcopy(self.contract)
        changed['metrics'][0]['measure'] = 'Unavailable legacy alias'
        with self.assertRaisesRegex(ValueError, 'Existing measure missing'):
            prepare(self.before, changed, expected_sha256=fingerprint(self.before))
        with self.assertRaisesRegex(ValueError, 'preimage drift'):
            prepare(self.before, self.contract, expected_sha256='0' * 64)


if __name__ == '__main__':
    unittest.main()
