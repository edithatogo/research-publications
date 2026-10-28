# SPDX-License-Identifier: Apache-2.0
import unittest
from scripts.audit_grants_classification import audit


class ClassificationCoverageTests(unittest.TestCase):
    def test_labels_do_not_infer_keys_and_empty_is_unqualified(self):
        result = audit({'value': [{'OpportunityKey': 'one', 'Funder': 'NIH', 'Category': 'Health'}]})
        self.assertEqual(result['status'], 'INCOMPLETE_CLASSIFICATION')
        self.assertEqual(result['rows_with_both_key_types'], 0)
        self.assertEqual(audit([])['status'], 'EMPTY_UNQUALIFIED')

    def test_present_keys_never_certify_provenance_or_activation(self):
        result = audit([{'OpportunityKey': 'one', 'FunderKey': 'funder:one',
                         'CategoryKeysJSON': '["category:health"]'}])
        self.assertEqual(result['status'], 'KEYS_PRESENT_PROVENANCE_UNQUALIFIED')
        self.assertFalse(result['reviewed_provenance_accepted'])
        self.assertFalse(result['native_propagation_accepted'])
        self.assertFalse(result['notification_activation_authorized'])

    def test_malformed_or_conflicting_keys_fail(self):
        for extra in ({'FunderKey': []}, {'CategoryKeysJSON': '{}'},
                      {'CategoryKeys': ['x'], 'CategoryKeysJSON': '["y"]'},
                      {'CategoryKeys': ['x', 'x']}, {'CategoryKeys': [{}]},
                      {'CategoryKeys': [' padded ']}, {'CategoryKeys': 'x'}):
            with self.subTest(extra=extra):
                self.assertEqual(audit([{'OpportunityKey': 'one', **extra}])['status'], 'INVALID')

    def test_duplicate_missing_and_invalid_readbacks_refused(self):
        for doc in ({}, [{}], [{'OpportunityKey': ' padded '}],
                    [{'OpportunityKey': 'x'}, {'OpportunityKey': 'x'}]):
            with self.subTest(doc=doc), self.assertRaises(ValueError):
                audit(doc)
