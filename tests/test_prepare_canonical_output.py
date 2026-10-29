import copy
import unittest

from scripts.prepare_canonical_output import build


class CanonicalOutputTests(unittest.TestCase):
    def inputs(self):
        def operation(name, params, connector='shared_sharepointonline'):
            return {'type': 'OpenApiConnection', 'inputs': {
                'host': {'apiId': '/providers/Microsoft.PowerApps/apis/' + connector,
                         'connectionName': connector, 'operationId': name},
                'parameters': params}, 'runAfter': {}}
        exporter = {'properties': {'connectionReferences': {'shared_sharepointonline': {'pin': 'sp'}},
            'definition': {'triggers': {'Recurrence': {'type': 'Recurrence', 'recurrence': {'frequency': 'Month', 'interval': 1}}},
            'actions': {'Export_Run': {'type': 'Scope', 'runAfter': {}, 'actions': {
                'Save_Registered_Publications_CSV': operation('CreateFile', {'dataset': 'site', 'folderPath': '/reporting', 'name': 'old.csv', 'body': 'old'}),
                'Printable_Read_manifest': operation('GetFileContentByPath', {'dataset': 'site', 'path': '/reporting/old.json', 'inferContentType': False}),
                'Printable_Verify_manifest': {'type': 'Compose', 'inputs': True, 'runAfter': {}}}},
                'Monitor_Success_receipt': {'type': 'Compose', 'inputs': 'success', 'runAfter': {'Export_Run': ['Succeeded']}},
                'Monitor_Retain_failed_status': {'type': 'Terminate', 'inputs': {'runStatus': 'Failed'}, 'runAfter': {'Export_Run': ['Failed']}}}}}}
        writer = {'properties': {'connectionReferences': {'shared_sharepointonline': {'pin': 'sp'}, 'shared_powerbi': {'pin': 'pbi'}},
            'definition': {'actions': {'Query': operation('ExecuteDatasetQuery', {'groupid': 'group', 'datasetid': 'model', 'specification/query': 'old'}, 'shared_powerbi')}}}}
        return exporter, writer

    def test_existing_actions_schedule_and_references_preserved(self):
        exporter, writer = self.inputs()
        frozen = copy.deepcopy(exporter)
        after = build(exporter, writer, reporting_month='2026-09')
        self.assertEqual(exporter, frozen)
        original = exporter['properties']['definition']
        actual = after['properties']['definition']
        self.assertEqual(actual['triggers'], original['triggers'])
        for name, action in original['actions'].items():
            if name == 'Export_Run':
                for key, value in action['actions'].items():
                    self.assertEqual(actual['actions'][name]['actions'][key], value)
            else:
                self.assertEqual(actual['actions'][name], action)
        self.assertEqual(after['properties']['connectionReferences'], writer['properties']['connectionReferences'])

    def test_all_added_actions_form_one_checked_chain_and_manifest_is_last(self):
        exporter, writer = self.inputs()
        actions = build(exporter, writer, reporting_month='2026-09')['properties']['definition']['actions']['Export_Run']['actions']
        seen = set(exporter['properties']['definition']['actions']['Export_Run']['actions'])
        for name, action in actions.items():
            if not name.startswith('Canonical_'):
                continue
            self.assertEqual(len(action['runAfter']), 1)
            dependency, statuses = next(iter(action['runAfter'].items()))
            self.assertIn(dependency, seen)
            self.assertEqual(statuses, ['Succeeded'])
            self.assertNotIn(action['type'], {'Http', 'Terminate'})
            seen.add(name)
        self.assertEqual(list(actions)[-1], 'Canonical_Verify_manifest')
        self.assertEqual(len(actions['Canonical_Manifest']['inputs']['verified_files']), 4)
        self.assertIn('Canonical_Verify_keys', actions['Canonical_Full_safe_cells']['runAfter'])
        self.assertIn('COUNTROWS', actions['Canonical_Query_Counts']['inputs']['parameters']['specification/query'])
        self.assertNotIn('1344', str(actions))

    def test_rejects_changed_connection_missing_readback_and_duplicate_scope(self):
        for mutation in ('connection', 'readback', 'query', 'duplicate'):
            exporter, writer = self.inputs()
            if mutation == 'connection':
                writer['properties']['connectionReferences']['shared_sharepointonline']['pin'] = 'other'
            elif mutation == 'readback':
                del exporter['properties']['definition']['actions']['Export_Run']['actions']['Printable_Verify_manifest']
            elif mutation == 'query':
                writer['properties']['definition']['actions'] = {}
            else:
                exporter = build(exporter, writer, reporting_month='2026-09')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                build(exporter, writer, reporting_month='2026-09')

    def test_rejects_ambiguous_model_and_implicit_period(self):
        exporter, writer = self.inputs()
        for period in (None, '', '2026-9', '2026-13', '@utcNow()'):
            with self.subTest(period=period), self.assertRaises(ValueError):
                build(exporter, writer, reporting_month=period)
        query = writer['properties']['definition']['actions']['Query']
        other = copy.deepcopy(query)
        other['inputs']['parameters']['datasetid'] = 'other'
        writer['properties']['definition']['actions']['Other'] = other
        with self.assertRaises(ValueError):
            build(exporter, writer, reporting_month='2026-09')


if __name__ == '__main__':
    unittest.main()
