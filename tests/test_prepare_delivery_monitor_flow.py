import copy
import unittest
from datetime import datetime, timezone

from scripts.prepare_delivery_monitor_flow import prepare, prepare_schedule_repair


def source():
    return {'schemaVersion': '1.0.0.0', 'properties': {
        'connectionReferences': {'shared_sharepointonline': {
            'runtimeSource': 'embedded', 'connection': {'connectionReferenceLogicalName': 'example_existing'}}},
        'definition': {'$schema': 'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#',
            'contentVersion': '1.0.0.0', 'parameters': {'$authentication': {'type': 'SecureObject', 'defaultValue': {}}},
            'triggers': {'Recurrence': {'type': 'Recurrence', 'recurrence': {
                'frequency': 'Month', 'interval': 1, 'timeZone': 'E. Australia Standard Time',
                'startTime': '2026-11-01T09:00:00', 'schedule': {'monthDays': [1], 'hours': ['9'], 'minutes': [0]}}}},
            'actions': {'Export_Run': {'type': 'Scope', 'actions': {
                'Printable_Save_completion_manifest': {'inputs': {'parameters': {
                    'dataset': 'https://example.sharepoint.com/sites/research',
                    'folderPath': '/Documents/Reporting'}}}}}}}}}


class DeliveryMonitorPreparationTests(unittest.TestCase):
    runtime = '11111111-2222-4333-8444-555555555555'

    def test_source_and_existing_binding_are_preserved(self):
        before = source()
        pinned = copy.deepcopy(before)
        result = prepare(before, self.runtime)
        self.assertEqual(before, pinned)
        self.assertEqual(result['properties']['connectionReferences'], before['properties']['connectionReferences'])
        self.assertNotIn('Export_Run', result['properties']['definition']['actions'])

    def test_commissioning_body_cannot_be_a_recurring_monitor(self):
        result = prepare(source(), self.runtime, commissioning_run='08500000000000000000000000000CU01')
        definition = result['properties']['definition']
        self.assertEqual(set(definition['triggers']), {'manual'})
        receipt = definition['actions']['Observation_receipt']['inputs']
        self.assertTrue(receipt['commissioning'])
        self.assertFalse(receipt['scheduled_trigger_proved'])

    def test_source_schedule_drift_requires_reconciliation(self):
        for field, value in [('startTime', '2026-12-01T09:00:00'), ('frequency', 'Week'),
                             ('timeZone', 'UTC'), ('schedule', {'monthDays': [2], 'hours': [9], 'minutes': [0]})]:
            with self.subTest(field=field):
                candidate = source()
                candidate['properties']['definition']['triggers']['Recurrence']['recurrence'][field] = value
                with self.assertRaises(ValueError):
                    prepare(candidate, self.runtime)

    def test_unsafe_paths_identity_and_new_connections_are_refused(self):
        with self.assertRaises(ValueError):
            prepare(source(), '-'*36)
        with self.assertRaises(ValueError):
            prepare(source(), self.runtime, commissioning_run='../another-folder')
        for key, value in [('folderPath', '/Documents/../Issued'),
                           ('dataset', 'https://user:password@example.sharepoint.com/sites/research')]:
            candidate = source()
            candidate['properties']['definition']['actions']['Export_Run']['actions']['Printable_Save_completion_manifest']['inputs']['parameters'][key] = value
            with self.assertRaises(ValueError):
                prepare(candidate, self.runtime)
        candidate = source()
        candidate['properties']['connectionReferences']['new_mail_connection'] = {}
        with self.assertRaises(ValueError):
            prepare(candidate, self.runtime)


class ExistingScheduleRepairTests(unittest.TestCase):
    def inputs(self):
        exporter = source()
        recurrence = exporter['properties']['definition']['triggers']['Recurrence']['recurrence']
        recurrence['startTime'] = '2026-11-01T07:00:00'
        recurrence['schedule']['hours'] = ['7']
        observer = prepare(source(), DeliveryMonitorPreparationTests.runtime)
        definition = observer['properties']['definition']
        definition['triggers']['Recurrence']['recurrence'].update(
            startTime='2026-11-01T07:45:00', schedule={'hours': [7], 'minutes': [45]})
        definition['actions']['Expected_at']['inputs'] = definition['actions']['Expected_at']['inputs'].replace('09:00', '07:00')
        return exporter, observer

    def test_existing_flows_keep_bindings_and_export_actions(self):
        exporter, observer = self.inputs()
        before = copy.deepcopy((exporter, observer))
        fixed_exporter, fixed_observer = prepare_schedule_repair(
            exporter, observer, as_of=datetime(2026, 11, 2, 10, tzinfo=timezone.utc))
        self.assertEqual((exporter, observer), before)
        self.assertEqual(fixed_exporter['properties']['definition']['actions'], exporter['properties']['definition']['actions'])
        for fixed, original in ((fixed_exporter, exporter), (fixed_observer, observer)):
            self.assertEqual(fixed['properties']['connectionReferences'], original['properties']['connectionReferences'])
        er = fixed_exporter['properties']['definition']['triggers']['Recurrence']['recurrence']
        mr = fixed_observer['properties']['definition']['triggers']['Recurrence']['recurrence']
        self.assertEqual(er['startTime'], '2026-10-01T07:00:00')
        self.assertEqual(mr['startTime'], '2026-10-01T10:05:00')
        self.assertEqual(mr['schedule'], {'hours': [10], 'minutes': [5]})
        self.assertEqual(fixed_observer['properties']['definition']['actions']['Due']['expression'],
                         "@greaterOrEquals(ticks(outputs('Observed_at')),ticks(outputs('Deadline')))")

    def test_inconsistent_deadline_or_expected_clock_is_not_silently_rewritten(self):
        for action, expression in [('Deadline', "@addHours(outputs('Expected_at'),1)"),
                                   ('Expected_at', "@utcNow()")]:
            exporter, observer = self.inputs()
            observer['properties']['definition']['actions'][action]['inputs'] = expression
            with self.subTest(action=action), self.assertRaises(ValueError):
                prepare_schedule_repair(exporter, observer, as_of=datetime(2026, 11, 2, tzinfo=timezone.utc))

    def test_naive_clock_and_ambiguous_source_schedule_are_refused(self):
        exporter, observer = self.inputs()
        with self.assertRaises(ValueError):
            prepare_schedule_repair(exporter, observer, as_of=datetime(2026, 11, 2))
        exporter['properties']['definition']['triggers']['Recurrence']['recurrence']['schedule']['hours'] = [7, 9]
        with self.assertRaises(ValueError):
            prepare_schedule_repair(exporter, observer, as_of=datetime(2026, 11, 2, tzinfo=timezone.utc))

    def test_past_anchor_handles_year_and_short_month_rollovers(self):
        for clock, expected_month in ((datetime(2027, 1, 1, tzinfo=timezone.utc), '2026-12'),
                                      (datetime(2026, 3, 1, tzinfo=timezone.utc), '2026-02')):
            exporter, observer = self.inputs()
            with self.subTest(clock=clock):
                fixed_exporter, fixed_observer = prepare_schedule_repair(exporter, observer, as_of=clock)
                er = fixed_exporter['properties']['definition']['triggers']['Recurrence']['recurrence']
                mr = fixed_observer['properties']['definition']['triggers']['Recurrence']['recurrence']
                self.assertEqual(er['startTime'], expected_month + '-01T07:00:00')
                self.assertEqual(mr['startTime'], expected_month + '-01T10:05:00')


if __name__ == '__main__':
    unittest.main()
