import copy
import unittest

from scripts.reconcile_publication_stub_disposition import _digest, reconcile


def fixture():
    candidates = {"candidate_count": 1, "items": [{"id": 7}]}
    correlation = {"candidate_count": 1, "read_only": True,
                   "disposition_decided": False, "exact_match_count": 1,
                   "unmatched_candidate_count": 0,
                   "candidate_snapshot_sha256": _digest(candidates),
                   "items": [{"id": 7, "grade": "direct_action_id_match",
                              "action": {"evidence_ref": "private proof"}}]}
    evidence = {name: {"sha256": name} for name in ("details", "versions", "schema")}
    evidence["candidates"] = {"sha256": _digest(candidates)}
    rehearsal = {"candidate_count": 1, "read_only": True,
                 "mutation_authorized": False, "historical_value_item_count": 0,
                 "input_sha256": {**{name: name for name in ("details", "versions", "schema")},
                                  "correlation": _digest(correlation)},
                 "items": [{"Id": 7, "historical_value_field_names": []}]}
    readiness = {"candidate_count": 1, "read_only": True,
                 "mutation_authorized": False, "restore_ready_count": 0,
                 "item_export_complete_count": 1, "input_evidence": evidence,
                 "items": [{"Id": 7, "item_export_complete": True,
                            "restore_ready": False}]}
    return candidates, correlation, rehearsal, readiness


class DispositionEvidenceTests(unittest.TestCase):
    def test_exact_match_is_not_disposition(self):
        result = reconcile(*fixture())
        self.assertEqual(result["counts"]["exact_create_match"], 1)
        self.assertEqual(result["counts"]["restore_ready"], 0)
        self.assertFalse(result["disposition_decided"])
        self.assertTrue(result["cross_receipt_evidence_coherent"])

    def test_mixed_version_receipts_fail_closed(self):
        parts = list(fixture())
        parts[3] = copy.deepcopy(parts[3])
        parts[3]["input_evidence"]["versions"]["sha256"] = "different"
        parts[3]["items"][0]["restore_ready"] = True
        parts[3]["restore_ready_count"] = 1
        result = reconcile(*parts)
        self.assertEqual(result["cross_receipt_mismatches"], ["versions"])
        self.assertEqual(result["counts"]["restore_ready"], 0)

    def test_different_candidate_set_rejected(self):
        parts = list(fixture())
        parts[3] = copy.deepcopy(parts[3])
        parts[3]["items"][0]["Id"] = 8
        with self.assertRaisesRegex(ValueError, "candidate sets differ"):
            reconcile(*parts)

    def test_unmatched_action_has_item_specific_diagnostic(self):
        parts = list(fixture())
        parts[1] = copy.deepcopy(parts[1])
        parts[1]["items"][0] = {"id": 7, "grade": "unmatched", "action": None}
        parts[1]["exact_match_count"] = 0
        parts[1]["unmatched_candidate_count"] = 1
        parts[2] = copy.deepcopy(parts[2])
        parts[2]["input_sha256"]["correlation"] = _digest(parts[1])
        result = reconcile(*parts)
        self.assertEqual(result["unmatched_action_item_ids"], [7])
        self.assertIn("item_specific_create_output_not_reconciled", result["items"][0]["evidence_gaps"])
        self.assertFalse(result["mutation_authorized"])

    def test_unmatched_aggregate_must_reconcile(self):
        parts = list(fixture())
        parts[1] = copy.deepcopy(parts[1])
        parts[1]["unmatched_candidate_count"] = 1
        parts[2] = copy.deepcopy(parts[2])
        parts[2]["input_sha256"]["correlation"] = _digest(parts[1])
        with self.assertRaisesRegex(ValueError, "unmatched correlation aggregate"):
            reconcile(*parts)

    def test_legacy_ready_claim_is_visible_but_never_authority(self):
        parts=list(fixture());parts[3]['items'][0]['restore_ready']=True;parts[3]['restore_ready_count']=1
        result=reconcile(*parts)
        self.assertEqual(result['counts']['restore_ready'],0)
        self.assertFalse(result['items'][0]['restore_ready'])
        self.assertTrue(result['items'][0]['legacy_restore_ready_claim'])
        self.assertFalse(result['mutation_authorized'])

    def test_boolean_aggregate_and_duplicate_ids_rejected(self):
        for mode in ('bool','duplicate'):
            parts=list(fixture())
            if mode=='bool':parts[0]['candidate_count']=True
            else:parts[3]['items'].append(copy.deepcopy(parts[3]['items'][0]))
            with self.subTest(mode=mode), self.assertRaises(ValueError):reconcile(*parts)

    def test_fictional_exact_correlation_through_rehearsal_and_planning_stays_read_only(self):
        from datetime import datetime,timezone
        from scripts.match_publication_stub_actions import correlate
        from scripts.plan_publication_stub_restore import plan,schema_field_inventory_sha256
        from scripts.rehearse_publication_stub_restore import rehearse
        stamp='2026-09-24T12:00:00Z'
        candidates={'candidate_count':1,'observed_at_utc':stamp,'items':[{'id':7}]}
        actions={'schema_version':'publication-create-action-outputs/v1','actions':[
            {'run_id':'fictional-run','action_id':'fictional-action','status':'Succeeded','created_item_id':7,'evidence_ref':'fixture://exact-action'}]}
        correlation=correlate(candidates,actions)
        schema={'inventory_complete':True,'source':'fixture://schema','observed_at_utc':stamp,'count':3,
                'fields':[{'internal_name':n,'type':'Text'} for n in ('Title','field_1','field_2')]}
        schema['inventory_sha256']=schema_field_inventory_sha256(schema['fields'])
        current={'Title':'','field_1':None,'field_2':None}
        details={'complete':True,'next_links':[],'observed_at_utc':stamp,'items':[
            {'Id':7,'GUID':'fictional-guid','ETag':'"2"','Created':stamp,'Modified':stamp,'fields':current}]}
        versions={'complete':True,'next_links':[],'observed_at_utc':stamp,'items':[
            {'Id':7,'version_history_complete':True,'version_next_links':[],'versions':[
                dict(current,Title='Fictional earlier evidence',VersionLabel='1.0',IsCurrentVersion=False),
                dict(current,VersionLabel='2.0',IsCurrentVersion=True)]}]}
        attachments={'complete':True,'next_links':[],'observed_at_utc':stamp,'items':[{'Id':7,'attachments':[]}]}
        registry={'complete':True,'next_links':[],'observed_at_utc':stamp,'rows':[{'Id':7,'SourceKey':''}]}
        policy={'policy_id':'fictional','evidence_ref':'fixture://policy','max_age_hours':48,
                'max_skew_hours':24,'max_context_skew_hours':1,'max_review_age_hours':48}
        before=copy.deepcopy((registry,candidates,schema,details,versions,attachments))
        rehearsal=rehearse(details,versions,correlation,schema)
        readiness=plan(registry,candidates,schema,details,versions,attachments,
                       now=datetime(2026,9,24,13,tzinfo=timezone.utc),freshness_policy=policy)
        result=reconcile(candidates,correlation,rehearsal,readiness)
        self.assertEqual(before,(registry,candidates,schema,details,versions,attachments))
        self.assertTrue(result['cross_receipt_evidence_coherent'])
        self.assertEqual(result['counts']['older_values_available'],1)
        self.assertEqual(result['counts']['exact_create_match'],1)
        self.assertEqual(result['counts']['restore_ready'],0)
        self.assertFalse(result['mutation_authorized']);self.assertIsNone(rehearsal['write_payload'])


if __name__ == "__main__":
    unittest.main()
