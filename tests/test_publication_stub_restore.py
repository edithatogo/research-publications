import unittest
from datetime import datetime, timezone

from scripts.plan_publication_stub_restore import plan, schema_field_inventory_sha256


def verified_no_retention_policy():
    return {
        "applicability": "no_policy_applies",
        "scope_evidence": "authoritative site and list policy inventory",
        "authoritative_policy_owner": "records policy owner",
        "control_inventory": {
            name: {"status": "verified_none", "evidence_ref": f"receipt#{name}"}
            for name in ("site_policy", "list_policy", "retention_labels", "holds", "record_declarations")
        },
    }


def seal_schema(schema):
    schema["inventory_sha256"] = schema_field_inventory_sha256(schema["fields"])
    return schema


class StubRestorePlanTests(unittest.TestCase):
    def setUp(self):
        self.registry = {"complete": True, "next_links": [], "observed_at_utc": "2026-09-24T12:00:00Z", "rows": [
            {"Id": 1, "SourceKey": "pubmed:1"},
            {"Id": 2, "SourceKey": "", "ReviewStatus": "Needs Review"},
        ]}
        self.candidates = {"candidate_count": 1, "observed_at_utc": "2026-09-24T12:01:00Z", "items": [{"id": 2, "created": "now"}]}
        self.schema = seal_schema({"count": 2, "inventory_complete": True,
                    "source": "saved complete list-schema readback",
                    "observed_at_utc": "2026-09-24T12:02:00Z", "fields": [
            {"internal_name": "field_1", "type":"Text"}, {"internal_name": "field_2", "type":"Text"},
        ]})

    def run_plan(self, *args, **kwargs):
        for snapshot in (*args[3:7], kwargs.get("details"), kwargs.get("versions"), kwargs.get("attachments")):
            if isinstance(snapshot, dict) and "items" in snapshot:
                snapshot.setdefault("observed_at_utc", "2026-09-24T12:03:00Z")
        return plan(*args, **kwargs, now=datetime(2026, 9, 24, 13, tzinfo=timezone.utc), freshness_policy={
            'policy_id':'fictional-policy', 'evidence_ref':'fixture://governed-policy',
            'max_age_hours':48, 'max_skew_hours':24, 'max_context_skew_hours':1, 'max_review_age_hours':48})

    def test_saved_json_rejects_duplicate_keys_and_nonfinite_numbers(self):
        from scripts.plan_publication_stub_restore import strict_json_loads
        for raw in ('{"Id":2,"Id":3}', '{"nested":{"x":1,"x":2}}',
                    '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                strict_json_loads(raw)

    def test_missing_target_is_unqualified_and_conflicting_targets_rejected(self):
        from scripts.plan_publication_stub_restore import target_qualification
        self.assertFalse(target_qualification({}, {})['qualified'])
        a={'target':{'site_id':'site','list_id':'list'}}
        self.assertTrue(target_qualification(a,a)['qualified'])
        with self.assertRaises(ValueError): target_qualification(a,{})

    def test_missing_exports_are_explicit_gaps(self):
        report = self.run_plan(self.registry, self.candidates, self.schema)
        self.assertEqual(report["candidate_count"], 1)
        self.assertFalse(report["all_exports_complete"])
        self.assertIn("complete_version_history_missing", report["items"][0]["gaps"])
        self.assertFalse(report["mutation_authorized"])

    def test_complete_saved_snapshots_are_inventory_only(self):
        details = {"complete": True, "next_links": [], "items": [{"Id": 2, "ETag": '"1"', "GUID":"fictional-guid",
                    "Created": "2026-09-24T12:00:00Z", "Modified": "2026-09-24T12:00:00Z",
                    "fields": {"field_1": None, "field_2": None}}]}
        versions = {"complete": True, "next_links": [], "items": [{"Id": 2, "versions": [{"VersionLabel":"1.0", "IsCurrentVersion":True}], "version_history_complete": True, "version_next_links": []}]}
        attachments = {"complete": True, "next_links": [], "items": [{"Id": 2, "attachments": []}]}
        section = {"complete": True, "source": "saved native readback",
                   "observed_at_utc": "2026-09-24T12:00:00Z", "data": {"enabled": False}}
        context = {"complete": True, **{key: section for key in
                   ("list", "permissions", "retention", "versioning")}}
        context["retention"] = {**section, "data": verified_no_retention_policy()}
        report = self.run_plan(self.registry, self.candidates, self.schema,
                      details, versions, attachments, context)
        self.assertTrue(report["item_exports_complete"])
        self.assertFalse(report["all_restore_exports_complete"])
        self.assertEqual(report["restore_ready_count"], 0)
        self.assertEqual(report["restore_rehearsal"], "not_performed")
        self.assertEqual(report["items"][0]["provenance_status"], "unresolved")
        self.assertIn("item_provenance_review_missing_or_invalid",
                      report["items"][0]["restore_readiness_gaps"])

    def test_fresh_item_level_provenance_disposition_is_required_for_restore_readiness(self):
        details = {"complete": True, "next_links": [], "items": [{"Id": 2, "ETag": '"1"', "GUID":"fictional-guid",
                    "Created": "2026-09-24T12:00:00Z", "Modified": "2026-09-24T12:00:00Z",
                    "fields": {"field_1": None, "field_2": None}}]}
        versions = {"complete": True, "next_links": [], "items": [{"Id": 2, "versions": [{"VersionLabel":"1.0", "IsCurrentVersion":True}], "version_history_complete": True, "version_next_links": []}]}
        attachments = {"complete": True, "next_links": [], "items": [{"Id": 2, "attachments": []}]}
        section = {"complete": True, "source": "saved native readback",
                   "observed_at_utc": "2026-09-24T12:00:00Z", "data": {"enabled": False}}
        context = {"complete": True, **{key: section for key in
                   ("list", "permissions", "retention", "versioning")}}
        context["retention"] = {**section, "data": verified_no_retention_policy()}
        review = {"status": "reviewed", "decision": "remove_and_restore",
                  "reviewer": "reviewer-1", "evidence_ref": "private-ledger#2",
                  "rationale": "individual action evidence reconciled",
                  "reviewed_at_utc": "2026-09-24T12:30:00Z"}
        report = self.run_plan(self.registry, self.candidates, self.schema,
                      details, versions, attachments, context,
                      flow_evidence={"item_provenance_reviews": {"2": review}})
        self.assertEqual(report["restore_ready_count"], 0)
        self.assertEqual(report["candidate_evidence_complete_count"], 1)
        self.assertFalse(report["items"][0]["restore_ready"])
        self.assertTrue(report["items"][0]["candidate_evidence_complete"])
        self.assertEqual(report["items"][0]["provenance_status"], "reviewed")
        self.assertEqual(report["items"][0]["provenance_decision"], "remove_and_restore")
        self.assertFalse(report["mutation_authorized"])

        stale = {**review, "reviewed_at_utc": "2026-09-20T12:00:00Z"}
        stale_report = self.run_plan(self.registry, self.candidates, self.schema,
                      details, versions, attachments, context,
                      flow_evidence={"item_provenance_reviews": {"2": stale}})
        self.assertEqual(stale_report["restore_ready_count"], 0)
        self.assertEqual(stale_report["items"][0]["provenance_status"], "unresolved")

    def test_rejects_stale_candidate_set(self):
        self.candidates["items"] = [{"id": 3}]
        with self.assertRaisesRegex(ValueError, "candidate IDs differ"):
            self.run_plan(self.registry, self.candidates, self.schema)

    def test_rejects_incomplete_registry(self):
        self.registry["complete"] = False
        with self.assertRaisesRegex(ValueError, "not explicitly complete"):
            self.run_plan(self.registry, self.candidates, self.schema)

    def test_rejects_non_candidate_snapshot_rows(self):
        details = {"complete": True, "next_links": [], "items": [{"Id": 1}]}
        with self.assertRaisesRegex(ValueError, "non-candidate"):
            self.run_plan(self.registry, self.candidates, self.schema, details=details)

    def test_paginated_item_exports_cannot_be_called_complete(self):
        details = {"complete": True, "next_links": [], "items": [{"Id": 2,
                    "ETag": '"1"', "GUID":"fictional-guid", "Created": "2026-09-24T12:00:00Z", "Modified": "2026-09-24T12:00:00Z",
                    "fields": {"field_1": None, "field_2": None}}]}
        versions = {"complete": True, "next_links": [], "items": [{"Id": 2, "versions": [{"VersionLabel":"1.0", "IsCurrentVersion":True}], "version_history_complete": True, "version_next_links": []}]}
        attachments = {"complete": True, "next_links": [], "items": [{"Id": 2, "attachments": []}]}
        for label, gap in (("details", "complete_item_detail_export_missing"),
                           ("versions", "complete_version_history_missing"),
                           ("attachments", "complete_attachment_export_missing")):
            with self.subTest(label=label):
                snapshots = {"details": details.copy(), "versions": versions.copy(),
                             "attachments": attachments.copy()}
                snapshots[label]["next_links"] = ["pending-page"]
                report = self.run_plan(self.registry, self.candidates, self.schema,
                                       **snapshots)
                self.assertIn(gap, report["items"][0]["item_export_gaps"])
                self.assertEqual(report["item_export_complete_count"], 0)

    def test_outer_version_export_does_not_prove_each_history_is_unpaged(self):
        details = {"complete": True, "next_links": [], "items": [{"Id": 2,
                    "ETag": '"1"', "GUID":"fictional-guid", "Created": "2026-09-24T12:00:00Z", "Modified": "2026-09-24T12:00:00Z",
                    "fields": {"field_1": None, "field_2": None}}]}
        attachments = {"complete": True, "next_links": [], "items": [
            {"Id": 2, "attachments": []}]}
        for version_item in (
            {"Id": 2, "versions": [{"VersionLabel": "1.0"}]},
            {"Id": 2, "versions": [{"VersionLabel": "1.0"}],
             "version_history_complete": True, "version_next_links": ["next"]},
        ):
            with self.subTest(version_item=version_item):
                versions = {"complete": True, "next_links": [], "items": [version_item]}
                report = self.run_plan(self.registry, self.candidates, self.schema,
                                       details, versions, attachments)
                self.assertIn("complete_version_history_missing",
                              report["items"][0]["item_export_gaps"])
                self.assertEqual(report["item_export_complete_count"], 0)

    def test_computed_and_attachment_fields_are_excluded_from_scalar_values(self):
        self.schema["fields"] += [
            {"internal_name": "ContentType", "type": "Computed"},
            {"internal_name": "Attachments", "type": "Attachments"},
        ]
        self.schema["count"] = 4
        seal_schema(self.schema)
        details = {"complete": True, "next_links": [], "items": [{"Id": 2, "ETag": '"1"', "GUID":"fictional-guid",
                    "Created": "2026-09-24T12:00:00Z", "Modified": "2026-09-24T12:00:00Z",
                    "fields": {"field_1": None, "field_2": None}}]}
        report = self.run_plan(self.registry, self.candidates, self.schema, details=details)
        self.assertEqual(report["excluded_non_scalar_fields"], ["Attachments", "ContentType"])
        self.assertNotIn("full_field_values_missing", report["items"][0]["gaps"])
        self.assertIn("complete_attachment_export_missing", report["items"][0]["gaps"])

    def test_extra_detail_field_is_not_counted_as_a_complete_scalar_export(self):
        details = {"complete": True, "next_links": [], "items": [{"Id": 2, "ETag": '"1"', "GUID":"fictional-guid",
                    "Created": "2026-09-24T12:00:00Z", "Modified": "2026-09-24T12:00:00Z",
                    "fields": {"field_1": None, "field_2": None, "unexpected": "redacted"}}]}
        report = self.run_plan(self.registry, self.candidates, self.schema, details=details)
        self.assertIn("unrecognized_field_values_present", report["items"][0]["gaps"])
        self.assertEqual(report["items"][0]["extra_detail_field_values"], ["unexpected"])
        self.assertFalse(report["items"][0]["item_export_complete"])

    def test_missing_scalar_field_names_are_reported(self):
        details = {"complete": True, "next_links": [], "items": [{"Id": 2, "ETag": '"1"', "GUID":"fictional-guid",
                    "Created": "2026-09-24T12:00:00Z", "Modified": "2026-09-24T12:00:00Z", "fields": {"field_1": None}}]}
        report = self.run_plan(self.registry, self.candidates, self.schema, details=details)
        item = report["items"][0]
        self.assertIn("scalar_field_values_missing", item["gaps"])
        self.assertEqual(item["missing_scalar_field_values"], ["field_2"])

    def test_excluded_schema_fields_in_details_do_not_count_as_scalar_extras(self):
        self.schema["fields"] += [
            {"internal_name": "ContentType", "type": "Computed"},
            {"internal_name": "Attachments", "type": "Attachments"},
        ]
        self.schema["count"] = 4
        seal_schema(self.schema)
        details = {"complete": True, "next_links": [], "items": [{"Id": 2, "ETag": '"1"', "GUID":"fictional-guid",
                    "Created": "2026-09-24T12:00:00Z", "Modified": "2026-09-24T12:00:00Z", "fields": {
                        "field_1": None, "field_2": None,
                        "ContentType": "ignored", "Attachments": True,
                    }}]}
        report = self.run_plan(self.registry, self.candidates, self.schema, details=details)
        item = report["items"][0]
        self.assertNotIn("unrecognized_field_values_present", item["gaps"])
        self.assertEqual(item["missing_scalar_field_values"], [])
        self.assertEqual(item["extra_detail_field_values"], [])

    def test_schema_inventory_requires_provenance_and_matching_digest(self):
        for change, gap in (
            ({"source": ""}, "schema_inventory_provenance_missing"),
            ({"inventory_sha256": "0" * 64}, "schema_inventory_digest_missing_or_mismatched"),
        ):
            with self.subTest(gap=gap):
                schema = {**self.schema, **change}
                report = self.run_plan(self.registry, self.candidates, schema)
                self.assertIn(gap, report["schema_inventory_gaps"])
                self.assertFalse(report["schema_inventory_complete"])
                self.assertIn(f"restore_{gap}", report["items"][0]["restore_readiness_gaps"])

    def test_schema_inventory_must_be_explicitly_complete_for_restore(self):
        self.schema["inventory_complete"] = False
        report = self.run_plan(self.registry, self.candidates, self.schema)
        self.assertFalse(report["schema_inventory_complete"])
        self.assertEqual(report["schema_inventory_gaps"], ["complete_schema_inventory_not_declared"])
        self.assertIn("restore_complete_schema_inventory_not_declared",
                      report["items"][0]["restore_readiness_gaps"])

    def test_stale_snapshot_evidence_keeps_restore_blocked(self):
        self.candidates["observed_at_utc"] = "2026-09-20T12:00:00Z"
        report = self.run_plan(self.registry, self.candidates, self.schema)
        self.assertIn("candidates", report["snapshot_freshness"]["stale_snapshots"])
        self.assertIn("restore_snapshot_evidence_exceeds_governed_age",
                      report["items"][0]["restore_readiness_gaps"])

    def test_incoherent_snapshot_window_keeps_restore_blocked(self):
        self.candidates["observed_at_utc"] = "2026-09-22T12:00:00Z"
        report = self.run_plan(self.registry, self.candidates, self.schema)
        self.assertIn("snapshot_observation_window_exceeds_governed_skew",
                      report["snapshot_freshness"]["gaps"])
        self.assertIn("restore_snapshot_observation_window_exceeds_governed_skew",
                      report["items"][0]["restore_readiness_gaps"])

    def test_receipt_fingerprints_inputs_without_copying_private_rows(self):
        report = self.run_plan(self.registry, self.candidates, self.schema)
        evidence = report["input_evidence"]
        self.assertEqual(set(evidence), {"registry", "candidates", "schema"})
        self.assertEqual(len(evidence["registry"]["sha256"]), 64)
        self.assertEqual(evidence["registry"]["entry_count"], 2)
        self.assertNotIn("items", str(evidence))
        before = evidence["candidates"]["sha256"]
        self.candidates["items"][0]["created"] = "changed"
        after = self.run_plan(self.registry, self.candidates, self.schema)["input_evidence"]["candidates"]["sha256"]
        self.assertNotEqual(before, after)

    def test_unknown_retention_context_does_not_close_restore_gap(self):
        section = {"complete": True, "source": "saved native readback",
                   "observed_at_utc": "2026-09-24T12:00:00Z", "data": {"enabled": False}}
        context = {"complete": True, **{key: section for key in
                   ("list", "permissions", "retention", "versioning")}}
        context["retention"] = "unknown"
        report = self.run_plan(self.registry, self.candidates, self.schema, context=context)
        self.assertIn("retention", report["context_section_gaps"])
        self.assertIn("context_retention_missing", report["items"][0]["restore_readiness_gaps"])
        self.assertNotIn("context_retention_missing", report["items"][0]["item_export_gaps"])

    def test_complete_item_exports_are_separate_from_restore_clearance(self):
        details = {"complete": True, "next_links": [], "items": [{"Id": 2, "ETag": '"1"', "GUID":"fictional-guid",
                    "Created": "2026-09-24T12:00:00Z", "Modified": "2026-09-24T12:00:00Z",
                    "fields": {"field_1": None, "field_2": None}}]}
        versions = {"complete": True, "next_links": [], "items": [{"Id": 2, "versions": [{"VersionLabel":"1.0", "IsCurrentVersion":True}], "version_history_complete": True, "version_next_links": []}]}
        attachments = {"complete": True, "next_links": [], "items": [{"Id": 2, "attachments": []}]}
        section = {"complete": True, "source": "saved native readback",
                   "observed_at_utc": "2026-09-24T12:00:00Z", "data": {"enabled": False}}
        context = {"complete": True, **{key: section for key in
                   ("list", "permissions", "retention", "versioning")}}
        context["retention"] = "unknown"
        report = self.run_plan(self.registry, self.candidates, self.schema,
                      details, versions, attachments, context)
        self.assertTrue(report["item_exports_complete"])
        self.assertEqual(report["item_export_complete_count"], 1)
        self.assertFalse(report["all_restore_exports_complete"])
        self.assertEqual(report["restore_ready_count"], 0)
        item = report["items"][0]
        self.assertTrue(item["item_export_complete"])
        self.assertFalse(item["restore_ready"])
        self.assertEqual(item["policy_clearance"], "unknown")
        self.assertEqual(item["item_export_gaps"], [])

    def test_flow_evidence_distinguishes_direct_match_from_cohort_link(self):
        registry = {"complete": True, "next_links": [], "rows": [
            {"Id": i, "SourceKey": ""} for i in (1369, 1370, 1500)
        ]}
        candidates = {"candidate_count": 3, "items": [
            {"id": 1369}, {"id": 1370}, {"id": 1500},
        ]}
        details = {"complete": True, "next_links": [], "items": [
            {"Id": i, "ETag": '"1"', "GUID":"fictional-guid", "Created": "2026-09-20T20:00:51Z",
             "Modified": "2026-09-20T20:00:51Z", "fields": {"field_1": None, "field_2": None}}
            for i in (1369, 1370, 1500)
        ]}
        flow = {"candidate_flow_run": {
            "run_id": "run-1", "first_iteration_created_item_id": 1369,
            "direct_created_item_id_match_proven": True,
            "current_contiguous_id_cohort": "1369-1468: cohort only",
            "matching_stub_created_utc_hour": "2026-09-20T20",
        }}
        report = self.run_plan(registry, candidates, self.schema, details=details,
                      flow_evidence=flow)
        grades = {row["Id"]: row["flow_correlation"]["grade"] for row in report["items"]}
        self.assertEqual(grades, {
            1369: "direct_action_match",
            1370: "cohort_correlation_only",
            1500: "no_individual_flow_correlation",
        })
        self.assertTrue(all(row["provenance_status"] == "unresolved" for row in report["items"]))

    def test_item_metadata_does_not_establish_retention_scope(self):
        section = {"complete": True, "source": "saved native readback",
                   "observed_at_utc": "2026-09-24T12:00:00Z", "data": {"enabled": False}}
        context = {"complete": True, **{key: section for key in
                   ("list", "permissions", "retention", "versioning")}}
        report = self.run_plan(self.registry, self.candidates, self.schema, context=context)
        self.assertEqual(report["context_section_gaps"], ["retention"])

    def test_retention_requires_owner_and_each_authoritative_control_surface(self):
        section = {"complete": True, "source": "saved native readback",
                   "observed_at_utc": "2026-09-24T12:00:00Z", "data": {"enabled": False}}
        context = {"complete": True, **{key: section for key in
                   ("list", "permissions", "versioning")}}
        context["retention"] = {**section, "data": {
            "applicability": "no_policy_applies",
            "scope_evidence": "site and list policy assignment readback",
        }}
        report = self.run_plan(self.registry, self.candidates, self.schema, context=context)
        self.assertEqual(report["context_section_gaps"], ["retention"])

        retention = verified_no_retention_policy()
        retention["control_inventory"]["holds"]["status"] = "not_observable"
        context["retention"] = {**section, "data": retention}
        report = self.run_plan(self.registry, self.candidates, self.schema, context=context)
        self.assertEqual(report["context_section_gaps"], ["retention"])

    def test_retention_applicability_must_match_control_inventory(self):
        section = {"complete": True, "source": "saved native readback",
                   "observed_at_utc": "2026-09-24T12:00:00Z", "data": {"enabled": False}}
        context = {"complete": True, **{key: section for key in
                   ("list", "permissions", "versioning")}}
        retention = verified_no_retention_policy()
        retention["control_inventory"]["site_policy"] = {
            "status": "present", "evidence_ref": "receipt#site-policy",
        }
        context["retention"] = {**section, "data": retention}
        report = self.run_plan(self.registry, self.candidates, self.schema, context=context)
        self.assertEqual(report["context_section_gaps"], ["retention"])

    def test_present_retention_policy_requires_explicit_restore_clearance(self):
        section = {"complete": True, "source": "saved native readback",
                   "observed_at_utc": "2026-09-24T12:00:00Z", "data": {"enabled": False}}
        context = {"complete": True, **{key: section for key in
                   ("list", "permissions", "versioning")}}
        retention = verified_no_retention_policy()
        retention["applicability"] = "policy_applies"
        retention["control_inventory"]["site_policy"] = {
            "status": "present", "evidence_ref": "receipt#site-policy",
        }
        context["retention"] = {**section, "data": retention}
        report = self.run_plan(self.registry, self.candidates, self.schema, context=context)
        self.assertEqual(report["context_section_gaps"], [])
        self.assertEqual(report["items"][0]["policy_clearance"], "pending")
        self.assertIn("retention_restore_pending", report["items"][0]["restore_readiness_gaps"])
        self.assertNotIn("retention_restore_pending", report["items"][0]["item_export_gaps"])

        retention["restore_clearance"] = {"decision": "permitted",
                                          "decision_owner": "records policy owner",
                                          "evidence_ref": "receipt#restore-decision"}
        report = self.run_plan(self.registry, self.candidates, self.schema, context=context)
        self.assertEqual(report["items"][0]["policy_clearance"], "permitted")
        self.assertNotIn("retention_restore_pending", report["items"][0]["restore_readiness_gaps"])

        retention["restore_clearance"] = {"decision": "prohibited"}
        report = self.run_plan(self.registry, self.candidates, self.schema, context=context)
        self.assertEqual(report["items"][0]["policy_clearance"], "prohibited")
        self.assertIn("retention_restore_prohibited", report["items"][0]["restore_readiness_gaps"])

    def test_future_context_observation_is_not_accepted(self):
        section = {"complete": True, "source": "saved native readback",
                   "observed_at_utc": "2999-09-24T12:00:00Z", "data": {"enabled": False}}
        context = {"complete": True, **{key: section for key in
                   ("list", "permissions", "versioning")}}
        context["retention"] = {**section, "data": verified_no_retention_policy()}
        report = self.run_plan(self.registry, self.candidates, self.schema, context=context)
        self.assertIn("list", report["context_section_gaps"])
        self.assertIn("context_list_missing", report["items"][0]["restore_readiness_gaps"])

    def test_incoherent_context_observation_window_keeps_restore_blocked(self):
        base = {"complete": True, "source": "saved native readback",
                "observed_at_utc": "2026-09-24T12:00:00Z", "data": {"enabled": False}}
        context = {"complete": True, **{key: base for key in
                   ("list", "permissions", "versioning")}}
        context["retention"] = {**base, "observed_at_utc": "2026-09-24T14:00:00Z",
                                 "data": verified_no_retention_policy()}
        report = self.run_plan(self.registry, self.candidates, self.schema, context=context)
        self.assertIn("context_observations_exceed_governed_window", report["context_section_gaps"])
        self.assertIn("context_context_observations_exceed_governed_window_missing",
                      report["items"][0]["restore_readiness_gaps"])

    def test_clock_and_governed_policy_are_required_not_implicit_defaults(self):
        with self.assertRaisesRegex(ValueError,'planning time'):
            plan(self.registry,self.candidates,self.schema)
        with self.assertRaisesRegex(ValueError,'governed freshness'):
            plan(self.registry,self.candidates,self.schema,now=datetime(2026,9,24,13,tzinfo=timezone.utc))
        policy={'policy_id':'fictional','evidence_ref':'fixture://policy','max_age_hours':96,
                'max_skew_hours':96,'max_context_skew_hours':1,'max_review_age_hours':48}
        self.candidates['observed_at_utc']='2026-09-22T12:00:00Z'
        result=plan(self.registry,self.candidates,self.schema,now=datetime(2026,9,24,13,tzinfo=timezone.utc),freshness_policy=policy)
        self.assertEqual(result['snapshot_freshness']['stale_snapshots'],[])
        self.assertEqual(result['generated_at_utc'],'2026-09-24T13:00:00+00:00')
        policy['max_age_hours']=False
        with self.assertRaises(ValueError): plan(self.registry,self.candidates,self.schema,now=datetime(2026,9,24,13,tzinfo=timezone.utc),freshness_policy=policy)

    def test_strict_item_schema_and_count_identities(self):
        import copy
        for bad in (True,2.0,'2',' 2'):
            candidates=copy.deepcopy(self.candidates); candidates['items'][0]['id']=bad
            with self.subTest(value=bad),self.assertRaises(ValueError): self.run_plan(self.registry,candidates,self.schema)
        schema=copy.deepcopy(self.schema);schema['count']=True
        with self.assertRaises(ValueError):self.run_plan(self.registry,self.candidates,schema)
        schema=copy.deepcopy(self.schema);schema['fields'][0]['internal_name']=' field_1'
        with self.assertRaises(ValueError):self.run_plan(self.registry,self.candidates,schema)
        registry=copy.deepcopy(self.registry);registry['rows'][0]['SourceKey']=' pubmed:1'
        with self.assertRaises(ValueError):self.run_plan(registry,self.candidates,self.schema)

    def test_unknown_dates_are_retained_as_gaps_and_output_cannot_edit_source(self):
        details={'complete':True,'next_links':[],'items':[{'Id':2,'GUID':'fictional','ETag':'"1"',
                 'Created':'unknown','Modified':'2026-09-24T12:00:00Z','fields':{'field_1':None,'field_2':None}}]}
        report=self.run_plan(self.registry,self.candidates,self.schema,details=details)
        self.assertIn('created_date_unknown',report['items'][0]['gaps'])
        self.assertEqual(report['items'][0]['item_detail']['Created'],'unknown')
        report['items'][0]['item_detail']['fields']['field_1']='overwrite'
        self.assertIsNone(details['items'][0]['fields']['field_1'])
        self.assertFalse(report['items'][0]['restore_ready'])
        self.assertIsNone(report['items'][0]['write_payload'])

    def test_private_create_only_guard_preserves_inputs_and_existing_receipts(self):
        from pathlib import Path
        import tempfile
        from scripts.plan_publication_stub_restore import private_output
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);private=root/'private/ops';private.mkdir(parents=True)
            source=private/'source.json';source.write_text('fictional input')
            existing=private/'receipt.json';existing.write_text('preserved human receipt')
            for output in (source,existing,root/'public.json'):
                with self.subTest(output=output),self.assertRaises(ValueError):private_output(output,[source],root=root)
            alias=private/'alias.json';alias.symlink_to(source)
            with self.assertRaises(ValueError):private_output(private/'new.json',[alias],root=root)
            self.assertEqual(existing.read_text(),'preserved human receipt')
            self.assertEqual(source.read_text(),'fictional input')
            self.assertEqual(private_output(private/'new.json',[source],root=root),(private/'new.json').resolve())


if __name__ == "__main__":
    unittest.main()
