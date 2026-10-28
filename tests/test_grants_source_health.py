# SPDX-License-Identifier: Apache-2.0
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts.grants_source_health import evaluate

FID = '12345678-1234-1234-1234-123456789abc'
RID = 'run-one'
FLOW_PATH = '/providers/example/environments/private/flows/' + FID


def fixture():
    recurrence = {'frequency': 'Week', 'interval': 1, 'timeZone': 'E. Australia Standard Time',
                  'schedule': {'weekDays': ['Monday'], 'hours': [5], 'minutes': [0]}}
    flow = {'name': FID, 'id': FLOW_PATH, 'properties': {'state': 'Started',
            'definition': {'triggers': {'Recurrence': {'type': 'Recurrence', 'recurrence': recurrence}}}}}
    run = {'name': RID, 'id': FLOW_PATH + '/runs/' + RID, 'properties': {
        'startTime': '2026-10-25T19:00:51Z', 'endTime': '2026-10-25T19:01:30Z', 'status': 'Succeeded',
        'trigger': {'name': 'Recurrence', 'scheduledTime': '2026-10-25T19:00:51Z',
                    'originHistoryName': RID, 'correlation': {'clientTrackingId': RID}}}}
    return flow, [run]


class GrantsSourceHealthTests(unittest.TestCase):
    def check(self, flow=None, history=None, generations=None, **kw):
        f, h = fixture()
        args = dict(as_of='2026-10-28T08:00:00Z', history_from='2026-10-18T00:00:00Z',
                    history_through='2026-10-28T08:00:00Z', history_complete=True, reads_verified=True)
        args.update(kw)
        return evaluate('nhmrc', flow if flow is not None else f, history if history is not None else h,
                        generations if generations is not None else [], **args)

    def test_missing_occurrence_needs_complete_window_and_explicit_deadline(self):
        self.assertEqual(self.check(history=[])['status'], 'UNKNOWN')
        self.assertEqual(self.check(history=[], due_by='2026-10-26T08:00:00+10:00')['status'], 'MISSED')
        for kw in [dict(history_complete=False), dict(reads_verified=False),
                   dict(history_through='2026-10-25T18:00:00Z')]:
            self.assertEqual(self.check(history=[], due_by='2026-10-26T08:00:00+10:00', **kw)['status'], 'UNKNOWN')

    def test_failed_running_stopped_and_unqualified_schedule_are_distinct(self):
        f, h = fixture(); h[0]['properties']['status'] = 'Failed'
        self.assertEqual(self.check(history=h)['status'], 'FAILED')
        h[0]['properties']['status'] = 'Running'; h[0]['properties'].pop('endTime')
        self.assertEqual(self.check(history=h)['status'], 'IN_PROGRESS')
        f['properties']['state'] = 'Stopped'
        self.assertEqual(self.check(flow=f)['status'], 'STOPPED')
        f['properties']['definition']['triggers']['Recurrence']['recurrence']['schedule']['hours'] = [7]
        self.assertEqual(self.check(flow=f)['status'], 'UNKNOWN')
        f, _ = fixture();f['properties']['definition']['triggers']['Recurrence']['recurrence']['interval'] = True
        self.assertEqual(self.check(flow=f)['status'], 'UNKNOWN')

    def test_wrong_identity_duplicate_runs_manual_origin_and_future_times_cannot_pass(self):
        _, h = fixture()
        for mutate in [lambda r:r.update(id='/other/flow'),
                       lambda r:r['properties'].update(endTime='2026-11-01T00:00:00Z')]:
            bad = copy.deepcopy(h); mutate(bad[0])
            with self.assertRaises(ValueError):self.check(history=bad)
        with self.assertRaises(ValueError):self.check(history=h+h)
        bad = copy.deepcopy(h);bad[0]['properties']['trigger']['originHistoryName']='manual'
        self.assertEqual(self.check(history=bad)['status'], 'UNKNOWN')
        with self.assertRaises(ValueError):self.check(as_of='2026-10-28T08:00:00')

    def test_terminal_success_needs_exact_hashed_generation_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); folder=root/('nhmrc-'+RID);folder.mkdir()
            originals=[{'name':f'nhmrc-{i:02d}-original.xlsx','stored_bytes':3,'saved_readback_equal':True} for i in range(1,15)]
            manifest={'run':RID,'source':'nhmrc','complete':True,'files':originals}
            for f in originals:(folder/f['name']).write_bytes(b'xls')
            for n in ['source-page.html','source-page-after.html']:(folder/n).write_bytes(b'<html>')
            (folder/'manifest.json').write_text(json.dumps(manifest))
            files=[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in folder.iterdir()]
            evidence=[{'source':'nhmrc','run':RID,'manifest_exact_run':True,'files':files}]
            self.assertEqual(self.check(generations=evidence,archive_root=root)['status'],'VERIFIED_SAVED_OCCURRENCE')
            self.assertFalse(self.check(generations=evidence,archive_root=root)['native_acceptance'])
            _, h = fixture();h[0]['properties'].pop('endTime')
            self.assertEqual(self.check(history=h,generations=evidence,archive_root=root)['status'],'UNKNOWN')
            self.assertEqual(self.check(generations=[None],archive_root=root)['status'],'UNKNOWN')
            (folder/originals[0]['name']).write_bytes(b'bad')
            self.assertEqual(self.check(generations=evidence,archive_root=root)['status'],'UNKNOWN')
            self.assertEqual(self.check()['status'],'UNKNOWN')

    def test_late_recurrence_is_uncertain_not_a_false_missed_cycle(self):
        _,h=fixture();p=h[0]['properties'];p['trigger']['scheduledTime']='2026-10-25T19:05:00Z'
        p['startTime']='2026-10-25T19:05:01Z';p['endTime']='2026-10-25T19:06:00Z'
        result=self.check(history=h,due_by='2026-10-26T08:00:00+10:00')
        self.assertEqual(result['status'],'UNKNOWN')
        self.assertIn('later_recurrence_origin_needs_slot_reconciliation',result['reasons'])
