import copy
import unittest

from scripts.preflight_publication_key_migration import assess


class KeyMigrationPreflightTests(unittest.TestCase):
    def setUp(self):
        self.aggregate = {
            "http": 200, "pagination_complete": True, "items_read": 3, "item_count": 3,
            "last_item_modified_utc": "2026-01-01T00:00:00Z", "blank_source_key": 1,
            "blank_canonical_key": 1, "duplicate_nonblank_source_keys": 0,
            "duplicate_nonblank_canonical_keys": 0,
            "field_constraints": {
                "SourceKey": {"internal_name": "field_1", "indexed": True, "unique": True, "required": True},
                "CanonicalKey": {"internal_name": "field_2", "indexed": True, "unique": False, "required": False},
            },
        }
        self.keyed = {"complete": True, "next_links":[], "total_rows": 3, "keyed_total": 2,
                      "max_modified": "2026-01-01T00:00:00Z",
                      "keyed_rows": [{"Id": 1, "SourceKey": "pubmed:1", "CanonicalKey": "PMID:1"},
                                     {"Id": 2, "SourceKey": "dora:abc", "CanonicalKey": "DORA:abc"}]}
        self.disposition = {"items": [{"Id": 3, "restore_ready": True}],
                            "candidate_count": 1, "cross_receipt_evidence_coherent": True,
                            "disposition_decided": True, "mutation_authorized": True}

    def test_cross_receipt_counts_and_mapping(self):
        result = assess(self.aggregate, self.keyed, self.disposition)
        self.assertFalse(result["constraint_preflight_ready"])
        self.assertFalse(result["native_integrity_accepted"])
        self.assertIn("blank_rows_remain", result["blockers"])

    def test_case_insensitive_collision_blocks(self):
        keyed = copy.deepcopy(self.keyed)
        keyed["keyed_rows"][1]["SourceKey"] = "PUBMED:1"
        self.assertIn("blank_or_case_insensitive_duplicate_SourceKey",
                      assess(self.aggregate, keyed, self.disposition)["blockers"])

    def test_shared_canonical_key_is_not_source_collision(self):
        keyed = copy.deepcopy(self.keyed)
        keyed["keyed_rows"][1]["CanonicalKey"] = "PMID:1"
        self.assertNotIn("blank_or_case_insensitive_duplicate_SourceKey",
                         assess(self.aggregate, keyed, self.disposition)["blockers"])

    def test_overlap_blocks(self):
        disposition = copy.deepcopy(self.disposition)
        disposition["items"][0]["Id"] = 2
        self.assertIn("invalid_or_overlapping_item_ids",
                      assess(self.aggregate, self.keyed, disposition)["blockers"])

    def test_unresolved_disposition_blocks(self):
        disposition = copy.deepcopy(self.disposition)
        disposition["mutation_authorized"] = False
        self.assertIn("stub_disposition_not_authorized",
                      assess(self.aggregate, self.keyed, disposition)["blockers"])

    def test_watermark_mismatch_blocks(self):
        aggregate = copy.deepcopy(self.aggregate)
        aggregate["last_item_modified_utc"] = "2026-01-02T00:00:00Z"
        self.assertIn("observation_watermark_mismatch",
                      assess(aggregate, self.keyed, self.disposition)["blockers"])

    def test_boolean_counts_ids_and_padded_keys_never_pass(self):
        for mode in ('count','id','padding','pagination'):
            aggregate,keyed=copy.deepcopy((self.aggregate,self.keyed))
            if mode=='count':aggregate['blank_source_key']=True
            elif mode=='id':keyed['keyed_rows'][0]['Id']=True
            elif mode=='padding':keyed['keyed_rows'][0]['SourceKey']=' pubmed:1'
            else:keyed['next_links']=['pending']
            result=assess(aggregate,keyed,self.disposition)
            self.assertTrue(result['blockers']);self.assertFalse(result['constraint_preflight_ready'])
            self.assertFalse(result['schema_change_authorized']);self.assertIsNone(result['write_payload'])

    def test_even_clean_observed_constraints_are_not_schema_authority(self):
        aggregate=copy.deepcopy(self.aggregate);aggregate.update(item_count=2,items_read=2,blank_source_key=0,blank_canonical_key=0)
        keyed=copy.deepcopy(self.keyed);keyed['total_rows']=2
        disposition={'items':[],'candidate_count':0,'cross_receipt_evidence_coherent':True,'disposition_decided':True,'mutation_authorized':True}
        result=assess(aggregate,keyed,disposition)
        self.assertTrue(result['constraint_preflight_ready'])
        self.assertTrue(result['constraint_diagnostics_passed'])
        self.assertEqual(result['constraint_preflight_ready_scope'],'diagnostic_checks_only')
        self.assertFalse(result['target_qualified_constraint_evidence'])
        for snapshot in (aggregate,keyed,disposition):
            snapshot['target']={'site_id':'fictional-site','list_id':'fictional-list'}
        qualified=assess(aggregate,keyed,disposition)
        self.assertTrue(qualified['target_qualified_constraint_evidence'])
        self.assertFalse(qualified['schema_change_authorized'])
        self.assertFalse(result['schema_change_authorized']);self.assertFalse(result['native_integrity_accepted'])


if __name__ == "__main__":
    unittest.main()
