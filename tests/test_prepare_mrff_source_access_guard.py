import copy
import unittest

from scripts.capture_official_workbooks import SOURCES
from scripts.prepare_mrff_source_access_guard import build


class MRFFSourceGuardTests(unittest.TestCase):
    def baseline(self):
        actions = {'Guard_source_coverage': {'inputs': 'unchanged coverage gate'},
                   'Save_completion': {'inputs': 'unchanged immutable completion'}}
        for suffix in ('', '_after'):
            actions['Get_source_page' + suffix] = {
                'type': 'Http', 'inputs': {'uri': SOURCES['mrff'][0], 'method': 'GET',
                                          'retryPolicy': {'type': 'none'}}}
            actions['Verify_page' + suffix] = {'inputs': 'unchanged byte readback'}
            actions['Href_values' + suffix] = {
                'inputs': 'unchanged parser', 'runAfter': {'Verify_page' + suffix: ['Succeeded']}}
        return {'name': 'synthetic-collector', 'properties': {'state': 'Started',
            'connectionReferences': {'existing': 'unchanged'},
            'definition': {'triggers': {'Recurrence': {'type': 'Recurrence'}}, 'actions': actions}}}

    def test_guards_both_verified_reads_without_changing_source_or_archive_contract(self):
        baseline = self.baseline()
        before = copy.deepcopy(baseline)
        result = build(baseline)
        self.assertEqual(baseline, before)
        self.assertEqual(result['properties']['definition']['triggers'],
                         baseline['properties']['definition']['triggers'])
        self.assertEqual(result['properties']['connectionReferences'],
                         baseline['properties']['connectionReferences'])
        expected = copy.deepcopy(result)
        a = expected['properties']['definition']['actions']
        for suffix in ('', '_after'):
            guard = a.pop('Guard_source_access' + suffix)
            self.assertEqual(guard['runAfter'], {'Verify_page' + suffix: ['Succeeded']})
            stop = guard['actions']['Stop_blocked_source' + suffix]
            self.assertEqual(stop['inputs']['runError']['code'], 'MRFF_SOURCE_ACCESS_BLOCKED')
            self.assertEqual(stop['inputs']['runStatus'], 'Failed')
            self.assertEqual(guard['else'], {'actions': {}})
            self.assertIn("body('Get_source_page" + suffix + "')", guard['expression'])
            self.assertEqual(a['Href_values' + suffix]['runAfter'],
                             {'Guard_source_access' + suffix: ['Succeeded']})
            a['Href_values' + suffix]['runAfter'] = {'Verify_page' + suffix: ['Succeeded']}
        self.assertEqual(expected, baseline)

    def test_refuses_repeat_foreign_source_and_changed_dependency(self):
        with self.assertRaises(ValueError):
            build(build(self.baseline()))
        for field, value in [('uri', 'https://other.invalid/'), ('method', 'POST')]:
            baseline = self.baseline()
            baseline['properties']['definition']['actions']['Get_source_page']['inputs'][field] = value
            with self.assertRaises(ValueError):
                build(baseline)
        baseline = self.baseline()
        baseline['properties']['definition']['actions']['Href_values_after']['runAfter'] = {}
        with self.assertRaises(ValueError):
            build(baseline)


if __name__ == '__main__':
    unittest.main()
