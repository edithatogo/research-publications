import unittest

from scripts.build_unified_publication_review_queue import build


class UnifiedReviewQueueTests(unittest.TestCase):
    def fixtures(self):
        pubs = [
            {
                "source_key": f"pubmed:{i}",
                "registry_review_status": "Needs Review",
                "registry_canonical_key": f"PMID:{i}",
                "in_committed_pubmed_archive": False,
                "in_committed_dora_archive_by_pmid": False,
                "dora_source_record_id": None,
                "official_pubmed_record": {
                    "title": "x",
                    "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{i}/",
                },
            }
            for i in range(1, 17)
        ]
        doras = [
            {
                "SourceID": f"DORA:https://example.org/{i}",
                "ReviewStatus": "Pending",
                "Disposition": None,
                "registry_refs": {},
                "archive_indices": [i],
            }
            for i in range(709)
        ]
        members = [{"Source": "DORA", "SourceID": r["SourceID"]} for r in doras]
        model = {
            "results": [
                {
                    "tables": [
                        {"rows": [{"[CanonicalKey]": "PMID:1", "[DORAURL]": None}]}
                    ]
                }
            ]
        }
        return {
            "pubmed": {"rows": pubs},
            "dora": {"rows": doras},
            "committed": {"complete": True, "next_links": [], "rows": members},
            "model": model,
        }

    def test_separates_membership_presence_and_admission(self):
        packet = build(**self.fixtures())
        self.assertEqual(packet["counts"]["total_pending"], 725)
        self.assertTrue(
            packet["rows"][0]["canonical_presence"][
                "final_publication_row_with_pmid_key"
            ]
        )
        self.assertFalse(
            packet["rows"][0]["model_presence"]["pubmed_source_export_keyset"]
        )
        self.assertFalse(packet["rows"][0]["admission"]["reviewed_admission_proven"])
        self.assertTrue(
            packet["rows"][16]["source_membership"]["retained_dora_archive"]
        )
        self.assertFalse(
            packet["rows"][16]["canonical_presence"]["registry_reference_evidence"]
        )
        self.assertIn(
            "Observed 1-row DAX", packet["presence_scope"]["final_publication_row"]
        )

    def test_fails_on_uncommitted_dora_member(self):
        f = self.fixtures()
        f["committed"]["rows"].pop()
        with self.assertRaisesRegex(ValueError, "absent from retained export"):
            build(**f)

    def test_fails_on_incomplete_export(self):
        f = self.fixtures()
        f["committed"]["next_links"] = ["more"]
        with self.assertRaisesRegex(ValueError, "complete"):
            build(**f)

    def test_fails_on_disposition_drift(self):
        f = self.fixtures()
        f["dora"]["rows"][0]["Disposition"] = "admitted"
        with self.assertRaisesRegex(ValueError, "disposition"):
            build(**f)

    def test_rejects_noncanonical_source_identities(self):
        cases = (
            ("pubmed", "source_key", "pubmed:01"),
            ("dora", "SourceID", "https://example.org/no-prefix"),
        )
        for source, field, value in cases:
            with self.subTest(source=source):
                f = self.fixtures()
                f[source]["rows"][0][field] = value
                with self.assertRaises(ValueError):
                    build(**f)

    def test_rejects_duplicate_model_identity_before_presence_claim(self):
        f = self.fixtures()
        f["model"]["results"][0]["tables"][0]["rows"].append(
            {"[CanonicalKey]": "PMID:1"}
        )
        with self.assertRaisesRegex(ValueError, "duplicate CanonicalKey"):
            build(**f)

    def test_rejects_malformed_model_export_before_presence_claim(self):
        f = self.fixtures()
        f["model"]["results"][0]["tables"][0]["rows"] = []
        with self.assertRaisesRegex(ValueError, "nonempty object rows"):
            build(**f)

    def test_rejects_pubmed_archive_membership_drift(self):
        f = self.fixtures()
        f["pubmed"]["rows"][0]["in_committed_pubmed_archive"] = True
        with self.assertRaisesRegex(ValueError, "membership disagrees"):
            build(**f)

    def test_rejects_dora_cross_reference_without_member(self):
        f = self.fixtures()
        f["pubmed"]["rows"][0]["in_committed_dora_archive_by_pmid"] = True
        f["pubmed"]["rows"][0]["dora_source_record_id"] = "https://example.org/absent"
        with self.assertRaisesRegex(ValueError, "cross-reference disagrees"):
            build(**f)

    def test_accepts_exact_dora_cross_reference_as_candidate_only(self):
        f = self.fixtures()
        f["pubmed"]["rows"][0]["in_committed_dora_archive_by_pmid"] = True
        f["pubmed"]["rows"][0]["dora_source_record_id"] = "https://example.org/0"
        packet = build(**f)
        self.assertTrue(
            packet["rows"][0]["source_membership"]["retained_dora_archive_by_pmid"]
        )
        self.assertFalse(packet["rows"][0]["admission"]["reviewed_admission_proven"])

    def test_rejects_official_record_identity_mismatch(self):
        f = self.fixtures()
        f["pubmed"]["rows"][0]["official_pubmed_record"]["pubmed_url"] = (
            "https://pubmed.ncbi.nlm.nih.gov/2/"
        )
        with self.assertRaisesRegex(ValueError, "exact official EFetch"):
            build(**f)


class CurrentPresenceDiagnosticTests(unittest.TestCase):
    def fixtures(self):
        pub = {
            "source_key": "pubmed:123",
            "registry_review_status": "Included",
            "ReviewNotes": "Keep\nreview",
            "PublicationDate": None,
        }
        dora = {
            "SourceID": "DORA:https://example.test/handle/1/7",
            "ReviewStatus": "Reviewed",
            "Disposition": "excluded",
            "PublicationDateRaw": "2001-2003",
            "PublicationDate": None,
        }
        return {
            "pubmed": {"complete": True, "row_count": 1, "rows": [pub]},
            "dora": {"complete": True, "row_count": 1, "rows": [dora]},
            "committed": {
                "complete": True,
                "rows": [
                    {"Source": "PubMed", "SourceID": "123"},
                    {"Source": "DORA", "SourceID": dora["SourceID"]},
                ],
            },
            "model": {
                "complete": True,
                "results": [
                    {
                        "tables": [
                            {
                                "rows": [
                                    {"[CanonicalKey]": "PMID:123", "[DORAURL]": None},
                                    {
                                        "[CanonicalKey]": "PUB:other",
                                        "[DORAURL]": "https://example.test/handle/1/7",
                                    },
                                ]
                            }
                        ]
                    }
                ],
            },
        }

    def test_current_cohort_has_no_historical_count_or_review_prerequisite(self):
        import copy

        from scripts.build_unified_publication_review_queue import build_diagnostic

        data = self.fixtures()
        before = copy.deepcopy(data)
        result = build_diagnostic(**data)
        self.assertEqual(result["counts"]["source_rows"], 2)
        self.assertEqual(
            result["rows"][0]["original_record"], data["pubmed"]["rows"][0]
        )
        self.assertEqual(result["rows"][1]["original_record"], data["dora"]["rows"][0])
        self.assertEqual(
            result["rows"][1]["source_key"], "dora:https://example.test/handle/1/7"
        )
        self.assertEqual(data, before)
        self.assertFalse(result["routine_admission_prerequisite"])
        self.assertFalse(result["review_authority"])
        self.assertFalse(result["identity_merge_authorized"])
        self.assertFalse(result["rows"][1]["model_presence_is_admission"])
        self.assertNotIn("admission", result["rows"][1])

    def test_exact_presence_preserves_ambiguity_and_does_not_match_url_suffix(self):
        from scripts.build_unified_publication_review_queue import build_diagnostic

        data = self.fixtures()
        rows = data["model"]["results"][0]["tables"][0]["rows"]
        rows.append(dict(rows[1], **{"[CanonicalKey]": "PUB:second"}))
        self.assertEqual(
            build_diagnostic(**data)["rows"][1]["model_exact_reference_count"], 2
        )
        for row in rows[1:]:
            row["[DORAURL]"] = (
                "https://other.test/proxy/https://example.test/handle/1/7"
            )
        self.assertEqual(
            build_diagnostic(**data)["rows"][1]["model_exact_reference_count"], 0
        )

    def test_error_partial_duplicate_or_incomplete_evidence_fails_closed(self):
        from scripts.build_unified_publication_review_queue import build_diagnostic

        for defect in ("error", "partial", "duplicate", "incomplete", "boolean-count"):
            data = self.fixtures()
            if defect == "error":
                data["model"]["results"][0]["error"] = {}
            elif defect == "partial":
                data["model"]["results"][0]["tables"][0]["partial"] = 0
            elif defect == "duplicate":
                data["pubmed"]["rows"] *= 2
                data["pubmed"]["row_count"] = 2
            elif defect == "incomplete":
                data["committed"]["complete"] = 1
            else:
                data["pubmed"]["row_count"] = True
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                build_diagnostic(**data)

    def test_historical_snapshot_is_explicitly_non_routine(self):
        result = build(**UnifiedReviewQueueTests().fixtures())
        self.assertTrue(result["historical_snapshot_only"])
        self.assertFalse(result["routine_admission_prerequisite"])
        self.assertFalse(result["review_authority"])


if __name__ == "__main__":
    unittest.main()
