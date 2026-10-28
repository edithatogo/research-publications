# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from scripts.e09_thread_mapping import prepare_thread, validate_thread, transition_thread
from scripts.e09_storage import envelope, transition


def selection(**changes):
    return {**dict(publication_key='qualification:e09-mapping', canonical_key='PUB:abcd',
                   tier='possible', review_status='Needs Review', discovered_on='2026-10-24',
                   suggested_trigger='first_discovery', Title='FICTIONAL mapping example',
                   PublicationMonth=None), **changes}


def record(revision=1, **changes):
    return prepare_thread(selection(), revision=revision, recorded_at='2026-10-24T12:00:00Z',
                          native_input_reference='fictional:qualified-case',
                          human_notes='Retain the fictional human edit', **changes)


class MappingTests(unittest.TestCase):
    def test_exact_no_send_mapping_and_replay(self):
        a = record(); original = copy.deepcopy(a)
        self.assertEqual(validate_thread(a), original)
        self.assertEqual(transition(envelope('thread', a, 1), envelope('thread', a, 1)), 'unchanged')
        self.assertIsNone(a['delivery_receipt']['post_reference'])
        self.assertFalse(a['delivery_receipt']['reconciliation_required'])

    def test_uncertain_attempt_blocks_every_changed_retry(self):
        a = record(uncertain=True)
        self.assertEqual(transition_thread(a, a), 'unchanged')
        for b in [record(2), record(2, uncertain=True)]:
            with self.assertRaisesRegex(ValueError, 'independent reconciliation'):
                transition_thread(a, b)

    def test_revision_update_preserves_human_notes_and_rejects_identity_drift(self):
        a, b = record(), record(2)
        self.assertEqual(transition_thread(a, b), 'update')
        for field, value in [('human_notes', 'Overwrite the original'),
                             ('canonical_key', 'PUB:ffff')]:
            c = copy.deepcopy(b); c[field] = value
            with self.assertRaises(ValueError):
                transition_thread(a, c)

    def test_tampered_post_receipt_and_aliases_fail(self):
        a = record()
        for kind in ['post', 'receipt', 'alias', 'hash']:
            b = copy.deepcopy(a)
            if kind == 'post': b['rendered_post']['subject'] = 'Altered'
            elif kind == 'receipt': b['delivery_receipt']['post_reference'] = 'invented:message'
            elif kind == 'alias': b['source_aliases'] = []
            else: b['input_fingerprint'] = '0' * 64
            with self.assertRaises(ValueError):
                validate_thread(b)

    def test_receipt_time_cannot_move_backwards(self):
        a, b = record(), record(2)
        b['delivery_receipt']['recorded_at'] = '2026-10-24T11:59:00Z'
        with self.assertRaisesRegex(ValueError, 'chronology'):
            transition_thread(a, b)
