# SPDX-License-Identifier: Apache-2.0
"""Adversarial no-send qualification tests; all records are fictional."""
import copy
import unittest
from scripts.e09_post_content import render_post_body
from scripts.e09_thread_mapping import prepare_thread, validate_thread
from scripts.e09_storage import envelope, transition
from scripts.e09_edition_storage import prepare_edition_snapshot
from tests.test_e09_thread_mapping import record, selection
from tests.test_e09_feed_contracts import delivery_receipt_record
from tests.test_e09_subscription_editions import preference, discovered


class NoSendStorageGuardTests(unittest.TestCase):
    def test_renderer_rejects_contradictory_labels_and_invented_dates_or_identity(self):
        for changes in [{'review_status':'Included'}, {'canonical_key':'PMID:01'},
                        {'discovered_on':'2026-02-30'}, {'PublicationMonth':'2026-13'},
                        {'publication_key':' qualification:e09-mapping '}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                render_post_body(selection(**changes))

    def test_preparation_does_not_infer_aliases_from_explicit_empty_or_malformed_input(self):
        for aliases in [[],['qualification:e09-mapping',{}],['qualification:e09-mapping',None]]:
            with self.subTest(aliases=aliases), self.assertRaises(ValueError):
                prepare_thread(selection(),revision=1,recorded_at='2026-10-24T12:00:00Z',
                    native_input_reference='fixture:readback',source_aliases=aliases)

    def test_receipt_identity_and_native_provenance_are_bound_to_thread(self):
        for field,value in [('receipt','unrelated-receipt'),('native',' padded '),('aliases',[{}])]:
            candidate=record()
            if field=='receipt':candidate['delivery_receipt']['receipt_id']=value
            elif field=='native':candidate['native_input_reference']=value
            else:candidate['source_aliases']=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_thread(candidate)

    def test_uncertain_standalone_receipt_cannot_be_relabelled_as_recorded(self):
        a=envelope('receipt',delivery_receipt_record(outcome='failed_uncertain',reconciliation_required=True),1)
        b=envelope('receipt',delivery_receipt_record(revision=2,recorded_at='2026-10-21T00:00:00Z'),2)
        with self.assertRaises(ValueError):transition(a,b)
        self.assertEqual(transition(a,a),'unchanged')

    def test_padded_delivered_identity_cannot_reenter_an_edition(self):
        with self.assertRaises(ValueError):
            prepare_edition_snapshot(preference(),[discovered()],start_date='2026-10-19',
                end_date='2026-10-26',already_delivered=[' pubmed:1 '])

    def test_human_text_and_keys_remain_exact_through_envelope_roundtrip(self):
        import json
        candidate=record();before=copy.deepcopy(candidate)
        packet=envelope('thread',candidate,1)
        self.assertEqual(json.loads(packet['payload_json']),before)
        self.assertEqual(candidate,before)
        self.assertTrue(packet['qualification_only'])
        self.assertEqual(candidate['dispatch_state'],'no_send')
        self.assertIsNone(candidate['delivery_receipt']['post_reference'])

    def test_malformed_typed_labels_and_uncertainty_are_never_coerced(self):
        for changes in [{'tier':[]},{'review_status':{}},{'discovered_on':False},{'suggested_trigger':[]}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                render_post_body(selection(**changes))
        for value in ['false',0,None]:
            with self.subTest(uncertain=value),self.assertRaises(ValueError):record(uncertain=value)
        for changes in [{'tier':[]},{'review_status':{}},{'suggested_trigger':[]}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                prepare_edition_snapshot(preference(),[discovered(**changes)],
                    start_date='2026-10-19',end_date='2026-10-26')
