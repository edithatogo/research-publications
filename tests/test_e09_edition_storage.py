# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from scripts.e09_edition_storage import prepare_edition_snapshot, validate_edition_snapshot, brisbane_discovery_date
from scripts.e09_storage import envelope, transition
from tests.test_e09_subscription_editions import preference, discovered

class EditionStorageTests(unittest.TestCase):
    def test_brisbane_midnight_and_week_boundary_require_aware_time(self):
        self.assertEqual(brisbane_discovery_date('2026-10-25T13:59:59Z'),'2026-10-25')
        self.assertEqual(brisbane_discovery_date('2026-10-25T14:00:00Z'),'2026-10-26')
        with self.assertRaises(ValueError): brisbane_discovery_date('2026-10-25T14:00:00')

    def snapshot(self, **changes):
        args=dict(subscription=preference(enrolled_on='2026-10-20'),
                  discovered=[discovered(publication_key='qualification:before', discovered_on='2026-10-19'),
                              discovered(publication_key='qualification:boundary', discovered_on='2026-10-20')],
                  start_date='2026-10-19', end_date='2026-10-26')
        return prepare_edition_snapshot(**{**args, **changes})

    def test_saved_replay_empty_week_and_enrolment(self):
        r=self.snapshot(); self.assertEqual(validate_edition_snapshot(r),r)
        self.assertEqual(r['result']['skip_counts']['enrolment_boundary'],1)
        self.assertEqual([e['publication_count'] for e in r['result']['editions']],[1,0])
        e=envelope('edition',r,1); self.assertEqual(transition(e,e),'unchanged')
        self.assertFalse(r['delivered'])

    def test_input_order_replay_and_duplicate_recovery_are_distinct(self):
        r=self.snapshot(); self.assertEqual(r,self.snapshot(discovered=list(reversed(r['inputs']['discovered']))))
        recovery=self.snapshot(already_delivered=['qualification:boundary'])
        self.assertEqual(recovery['result']['skip_counts']['already_delivered'],1)
        self.assertTrue(all(e['publication_count']==0 for e in recovery['result']['editions']))
        self.assertNotEqual(r['edition_snapshot_id'],recovery['edition_snapshot_id'])

    def test_changed_preferences_cannot_overwrite_original(self):
        a=envelope('edition',self.snapshot(),1)
        b=envelope('edition',self.snapshot(subscription=preference(cadence='daily')),1)
        with self.assertRaisesRegex(ValueError,'immutable'): transition(a,b)
        for changes in [dict(cadence='off'),dict(status='withdrawn')]:
            r=self.snapshot(subscription=preference(**changes))
            self.assertEqual(r['result']['editions'],[])

    def test_forged_output_unknown_fields_and_duplicate_inputs_fail(self):
        r=self.snapshot()
        for field,value in [('delivered',True),('input_sha256','0'*64),('revision',True)]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                validate_edition_snapshot({**r,field:value})
        d=discovered()
        with self.assertRaises(ValueError): self.snapshot(discovered=[d,d])
        with self.assertRaises(ValueError): self.snapshot(discovered=[discovered(discovered_on='2026-11-01')])
        for bad in ['qualification:one', [None], [{}]]:
            with self.subTest(delivered=bad), self.assertRaises(ValueError):
                self.snapshot(already_delivered=bad)
        with self.assertRaises(ValueError): self.snapshot(discovered=[None])
        for changes in [dict(review_status='Excluded'), dict(tier='possible'),
                        dict(canonical_key='unknown'), dict(suggested_trigger='send')]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.snapshot(discovered=[discovered(**changes)])
