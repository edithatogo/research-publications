# SPDX-License-Identifier: Apache-2.0
import copy
import unittest

from scripts.e09_storage import envelope, validate_envelope, transition
from tests.test_e09_feed_contracts import contribution_record, subscription_record, delivery_receipt_record


class StorageTests(unittest.TestCase):
    def test_three_record_types_round_trip_without_coercion(self):
        import json
        for kind, record in [('contribution', contribution_record()),
                             ('subscription', subscription_record()),
                             ('receipt', delivery_receipt_record())]:
            before = copy.deepcopy(record)
            packet = envelope(kind, record, 1)
            self.assertEqual(json.loads(packet['payload_json']), before)
            self.assertEqual(validate_envelope(packet), packet)
            self.assertEqual(transition(packet, packet), 'unchanged')
            self.assertEqual(record, before)

    def test_typed_identity_and_exact_fingerprints(self):
        a = envelope('subscription', subscription_record(subscription_id='same'), 1)
        b = envelope('receipt', delivery_receipt_record(receipt_id='same'), 1)
        self.assertNotEqual(a['key'], b['key'])
        for change in [{'key': b['key']}, {'payload_sha256': '0' * 64},
                       {'qualification_only': False}, {'schema': True}, {'extra': 1}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_envelope({**a, **change})

    def test_revision_conflict_and_immutable_subscriber(self):
        a = envelope('subscription', subscription_record(), 1)
        b = envelope('subscription', subscription_record(revision=2, cadence='off',
                         status='withdrawn', revised_on='2026-10-24'), 2)
        self.assertEqual(transition(a, b), 'update')
        for record, revision in [(subscription_record(cadence='off'), 1),
                                 (subscription_record(revision=3), 3),
                                 (subscription_record(revision=2, subscriber_urn='subscriber:other'), 2)]:
            with self.assertRaises(ValueError):
                transition(a, envelope('subscription', record, revision))

    def test_no_delivery_capacity_or_provenance_bypass(self):
        with self.assertRaises(ValueError):
            envelope('subscription', subscription_record(delivery_authority_active=True,
                      delivery_authority_reference='authority:example'), 1)
        with self.assertRaises(ValueError):
            envelope('contribution', contribution_record(evidence='x' * 60000), 1)
        with self.assertRaises(ValueError):
            envelope('receipt', delivery_receipt_record(revision=2), 1)
        a = envelope('contribution', contribution_record(), 1)
        with self.assertRaises(ValueError):
            transition(a, envelope('contribution', contribution_record(source_revision=2), 2))

    def test_exact_unicode_human_text_survives_revision(self):
        import json
        r = contribution_record(evidence='Human note: café\nretain spacing  and unknowns')
        a = envelope('contribution', r, 1)
        revised = {**r, 'suggested_keywords': ['proposed-only']}
        b = envelope('contribution', revised, 2)
        self.assertEqual(transition(a, b), 'update')
        self.assertEqual(json.loads(b['payload_json'])['evidence'], r['evidence'])
