"""Recorded-response tests; none certify native execution or freshness."""

import copy
import unittest

from scripts.audit_publication_writer_readiness import assess


def response(rows):
    return {"results": [{"tables": [{"rows": rows}]}]}


class WriterReadinessAuditTests(unittest.TestCase):
    def inputs(self):
        params = {
            "groupid": "11111111-1111-4111-8111-111111111111",
            "datasetid": "22222222-2222-4222-8222-222222222222",
        }
        flow = {
            "properties": {
                "state": "Stopped",
                "flowFailureAlertSubscribed": True,
                "definition": {
                    "actions": {
                        name: {"inputs": {"parameters": copy.deepcopy(params)}}
                        for name in (
                            "Run_a_query_against_a_dataset",
                            "Run_publication_rows_query",
                            "Run_OpenAlex_Context_Query",
                        )
                    }
                },
            }
        }
        storage = response(
            [
                {
                    "[SourceReadiness]": "READY_FOR_STORAGE_VALIDATION",
                    "[PublicationRows]": 2,
                    "[RetainedPubMed]": 2,
                    "[RetainedDORA]": 1,
                    "[HistoryRows]": 3,
                }
            ]
        )
        projection = response(
            [
                {
                    "[FreshAuditRows]": 9,
                    "[FreshAuditFailed]": 0,
                    "[SourceSnapshotRows]": 40,
                    "[FreshPublicationRows]": 2,
                    "[DoraAuditRows]": 10,
                    "[DoraAuditFailed]": 0,
                }
            ]
        )
        generations = response(
            [
                {
                    "RetainedHistoryKeys[Source]": source,
                    "RetainedHistoryKeys[LastBatchID]": "retained-" + source,
                    "[Records]": count,
                    "[LastObservedMinUTC]": date,
                    "[LastObservedMaxUTC]": date,
                }
                for source, count, date in [
                    ("PubMed", 2, "2026-10-21T20:04:50"),
                    ("DORA", 1, "2026-10-11T05:39:27"),
                ]
            ]
        )
        return flow, storage, projection, generations

    def assess(self, values):
        return assess(*values, as_of="2026-10-28T10:00:00Z")

    def test_passing_counts_do_not_certify_freshness_or_run_authority(self):
        result = self.assess(self.inputs())
        self.assertTrue(result["storage_validation_ready"])
        self.assertTrue(result["routine_projection_ready"])
        self.assertFalse(result["source_generation_freshness_accepted"])
        self.assertFalse(result["diagnostic_run_permitted"])
        self.assertTrue(result["failure_alerts_enabled"])
        self.assertNotIn("retained-PubMed", str(result))

    def test_same_count_different_model_binding_fails(self):
        values = self.inputs()
        values[0]["properties"]["definition"]["actions"]["Run_publication_rows_query"][
            "inputs"
        ]["parameters"]["datasetid"] = "33333333-3333-4333-8333-333333333333"
        with self.assertRaisesRegex(ValueError, "binding"):
            self.assess(values)

    def test_error_envelope_cannot_hide_behind_valid_rows(self):
        for error in ({"message": "Query failed"}, {}):
            values = self.inputs()
            values[1]["results"][0]["error"] = error
            with self.assertRaisesRegex(ValueError, "error"):
                self.assess(values)

    def test_partial_or_failed_audits_are_not_routine_ready(self):
        for key, value in [
            ("[FreshAuditRows]", 8),
            ("[DoraAuditRows]", 9),
            ("[FreshAuditFailed]", 1),
            ("[DoraAuditFailed]", 1),
            ("[SourceSnapshotRows]", 0),
        ]:
            values = self.inputs()
            values[2]["results"][0]["tables"][0]["rows"][0][key] = value
            self.assertFalse(self.assess(values)["routine_projection_ready"], key)

    def test_generations_must_cover_exact_retained_counts(self):
        values = self.inputs()
        values[3]["results"][0]["tables"][0]["rows"][0]["[Records]"] = 1
        with self.assertRaisesRegex(ValueError, "generation counts"):
            self.assess(values)

    def test_missing_duplicate_future_and_noninteger_evidence_rejected(self):
        for defect in ("missing", "duplicate", "future", "boolean"):
            values = self.inputs()
            rows = values[3]["results"][0]["tables"][0]["rows"]
            if defect == "missing":
                rows.pop()
            elif defect == "duplicate":
                rows.append(copy.deepcopy(rows[0]))
            elif defect == "future":
                rows[0]["[LastObservedMaxUTC]"] = "2027-01-01T00:00:00"
            else:
                rows[0]["[Records]"] = True
            with self.assertRaises(ValueError, msg=defect):
                self.assess(values)

    def test_empty_and_multiple_result_tables_are_not_evidence(self):
        for defect in ("empty", "tables"):
            values = self.inputs()
            if defect == "empty":
                values[1]["results"][0]["tables"][0]["rows"] = []
            else:
                values[1]["results"][0]["tables"].append({"rows": []})
            with self.assertRaises(ValueError):
                self.assess(values)
