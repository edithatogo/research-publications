# SPDX-License-Identifier: Apache-2.0
import copy
import json
import unittest
from tests import test_grants_reviewed_classification as mapping_fixtures
from scripts.grants_reviewed_classification import reviewed_mapping,apply_mapping,FIELDS
from scripts.grants_classification_promotion import inspect_classification,invalidate_source_change,review_invalidated,classified_projection


class SourceChangeTests(unittest.TestCase):
    def setUp(self):
        fixture=mapping_fixtures.ReviewedClassificationTests();fixture.setUp()
        self.raw=fixture.raw();self.row=apply_mapping(fixture.row,reviewed_mapping(fixture.row,self.raw),self.raw)
    def test_current_classification_does_not_approve_opportunity(self):
        self.assertTrue(inspect_classification(self.row,self.raw)['classification_current'])
        self.assertFalse(inspect_classification(self.row,self.raw)['opportunity_reviewed'])
        self.assertFalse(inspect_classification(self.row,self.raw)['delivery_ready'])
        self.assertEqual(invalidate_source_change(self.row,self.row,self.raw,self.raw)['state'],'unchanged')
    def test_changed_source_clears_keys_and_preserves_prior_review_journal(self):
        current={**self.row,'EvidenceHash':'c'*64}
        changed=invalidate_source_change(self.row,current,self.raw,self.raw)
        self.assertEqual(changed['state'],'classification_review_required')
        self.assertIsNone(changed['record']['FunderKey']);self.assertEqual(changed['record']['CategoryKeysJSON'],'[]')
        self.assertEqual(changed['record']['ReviewStatus'],'Needs Review')
        self.assertEqual(changed['journal']['previous']['ClassificationEvidenceJSON'],self.row['ClassificationEvidenceJSON'])
        with self.assertRaises(ValueError):classified_projection(changed['record'],self.raw)
        reviewed=review_invalidated(changed['record'],self.raw)
        self.assertTrue(inspect_classification(reviewed['record'],self.raw)['classification_current'])
        self.assertEqual(reviewed['record']['ReviewStatus'],'Needs Review')
    def test_raw_revision_change_alone_invalidates_even_when_codes_unchanged(self):
        changed=invalidate_source_change(self.row,self.row,self.raw,self.raw+b' ')
        self.assertFalse(inspect_classification(changed['record'],self.raw+b' ')['classification_current'])
        with self.assertRaises(ValueError):review_invalidated(changed['record'],self.raw)
    def test_other_opportunity_or_concurrent_classification_edit_is_refused(self):
        for patch in ({'OpportunityKey':'GRANT:'+'d'*24},{'FunderKey':'other'}):
            with self.assertRaises(ValueError):invalidate_source_change(self.row,{**self.row,**patch},self.raw,self.raw)
    def test_downstream_projection_retains_all_classification_fields(self):
        projection=classified_projection(self.row,self.raw)
        self.assertTrue(all(projection[k]==self.row[k] for k in FIELDS))
        self.assertEqual(projection['ReviewStatus'],'Needs Review')

    def test_schema_model_promotion_is_explicitly_unsupported(self):
        from scripts.grants_classification_promotion import promotion_candidate
        document={'synthetic':'unchanged'};before=copy.deepcopy(document)
        with self.assertRaisesRegex(ValueError,'outside this source-only'):
            promotion_candidate(self.row,self.raw,document,[])
        self.assertEqual(document,before)

    def test_malformed_transition_inputs_do_not_mutate_prior_classification(self):
        before=copy.deepcopy(self.row)
        for current,raw in [(None,self.raw),({**self.row,'EvidenceHash':False},self.raw),(self.row,'not bytes')]:
            with self.subTest(current=current),self.assertRaises(ValueError):
                invalidate_source_change(self.row,current,self.raw,raw)
        with self.assertRaises(ValueError):inspect_classification([],self.raw)
        with self.assertRaises(ValueError):review_invalidated({**self.row,'ClassificationEvidenceJSON':'[]'},self.raw)
        self.assertEqual(self.row,before)
