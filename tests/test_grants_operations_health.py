# SPDX-License-Identifier: Apache-2.0
import unittest
from scripts.grants_operations import evaluate_run


class MissingHealthTests(unittest.TestCase):
    def test_absent_health_cannot_certify_nonempty_or_verified_empty(self):
        prior = [{'OpportunityKey': 'GRANT:old'}]
        for rows, verified in [([{'OpportunityKey': 'GRANT:new'}], False), ([], True)]:
            with self.subTest(verified_empty=verified):
                r = evaluate_run(rows, [], prior, verified_empty=verified)
                self.assertEqual(r['status'], 'rejected')
                self.assertIn('source_health_missing', r['errors'])
                self.assertEqual(r['records'], prior)
                self.assertTrue(r['preserved_prior'])
                self.assertFalse(r['verified_empty'])

    def test_explicit_successful_health_preserves_selected_empty_semantics(self):
        r = evaluate_run([], [{'source': 'fictional-source', 'status': 'succeeded'}],
                         [{'OpportunityKey': 'GRANT:old'}], verified_empty=True)
        self.assertEqual(r['status'], 'accepted')
        self.assertTrue(r['verified_empty'])
