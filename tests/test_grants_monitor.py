# SPDX-License-Identifier: Apache-2.0
from datetime import datetime
import unittest
from scripts.grants_monitor import expected_slot,archive_names,checked_inventory,delivery_healthy,backup_counts


class GrantsMonitorTests(unittest.TestCase):
    def test_monday_slots_before_and_after_cutover(self):
        before=datetime.fromisoformat('2026-10-26T04:59:00+10:00')
        after=datetime.fromisoformat('2026-10-26T06:01:00+10:00')
        self.assertEqual(expected_slot('nhmrc',before).day,19)
        self.assertEqual(expected_slot('nhmrc',after).isoformat(),'2026-10-26T05:00:00+10:00')
        self.assertEqual(expected_slot('mrff',after).hour,6)

    def test_native_archive_shape_cannot_hide_missing_or_cross_target_files(self):
        folder='/owned/mrff-run';rows=[{'Name':n,'ServerRelativeUrl':folder+'/'+n,'Length':'4'} for n in archive_names('mrff')]
        self.assertEqual(checked_inventory('mrff','run',folder,rows),rows)
        for wrong in [rows[:-1],rows+[rows[0]],[{**r,'ServerRelativeUrl':'/other/'+r['Name']} for r in rows]]:
            with self.assertRaises(ValueError):checked_inventory('mrff','run',folder,wrong)

    def test_delivery_failure_or_uncertainty_is_not_service_health(self):
        self.assertTrue(delivery_healthy({}))
        self.assertTrue(delivery_healthy({'submissions':[{'accepted_once':True,'terminal_or_pending':'Succeeded'}]}))
        for value in [{'error':'expired'}, {'submissions':[{'error':'refused'}]},
                      {'submissions':[{'accepted_once':True,'terminal_or_pending':'Running'}]},
                      {'submissions':[{'disposition':'prior_one_send_journal_preserved; reconcile rather than retry'}]}]:
            self.assertFalse(delivery_healthy(value))

    def test_failed_backup_read_is_not_verified_empty(self):
        full={'metadata':{},'fields':{'value':[]},'items':{'value':[]}}
        self.assertEqual(backup_counts({'empty':full,'missing':{'metadata':{},'fields':{}}}),{'empty':0,'missing':None})
