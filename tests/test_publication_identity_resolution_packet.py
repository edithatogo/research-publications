import unittest

from scripts.build_publication_identity_resolution_packet import build


class IdentityResolutionPacketTests(unittest.TestCase):
    def setUp(self):
        self.registry = {
            "complete": True,
            "keyed_total": 1,
            "keyed_rows": [
                {
                    "Id": 1,
                    "SourceKey": "dora:1/7",
                    "CanonicalKey": "PUB:legacy",
                    "PMID": "0",
                    "DORAURL": "https://example.test/handle/1/7",
                    "ReviewStatus": "Included",
                }
            ],
        }
        self.differences = {
            "invalid": [{"side": "registry", "raw_key": "dora:1/7"}],
            "model_additional_membership": [
                {
                    "typed_identity": "PMID:123",
                    "model_membership": "PubMed; DORA",
                    "registry_primary": "PubMed",
                }
            ],
        }
        self.tiered = {
            "candidate_only": True,
            "reviewed_membership": False,
            "rows": [
                {
                    "SourceID": "DORA:https://example.test/handle/1/7",
                    "stage_pmid": "123",
                    "registry_pmid_ids": ["2"],
                    "tier": "three_source_identifier_corroborated",
                }
            ],
        }

    def test_exact_joins_remain_review_only(self):
        packet = build(self.registry, self.differences, self.tiered)
        self.assertFalse(packet["registry_write_authorized"])
        self.assertEqual(packet["counts"]["legacy_invalid_registry_identities"], 1)
        self.assertEqual(packet["model_additional_membership"][0]["candidate_count"], 1)
        self.assertEqual(
            packet["model_additional_membership"][0][
                "linked_legacy_conflict_registry_ids"
            ],
            [1],
        )
        self.assertEqual(
            packet["model_additional_membership"][0]["disposition"],
            "legacy_registry_identity_conflict_review",
        )
        self.assertEqual(
            packet["counts"]["membership_candidates_with_legacy_conflicts"], 1
        )
        self.assertEqual(
            packet["legacy_invalid_registry_identities"][0][
                "candidate_current_pmid_registry_ids"
            ],
            [["2"]],
        )

    def test_suffix_url_does_not_match_different_dora_source(self):
        self.tiered["rows"][0]["SourceID"] = (
            "DORA:https://other.test/proxy/https://example.test/handle/1/7"
        )
        packet = build(self.registry, self.differences, self.tiered)
        self.assertEqual(
            packet["legacy_invalid_registry_identities"][0]["candidate_count"], 0
        )
        self.assertEqual(
            packet["model_additional_membership"][0][
                "linked_legacy_conflict_registry_ids"
            ],
            [],
        )
        self.assertEqual(
            packet["model_additional_membership"][0]["disposition"],
            "review_candidate_only",
        )

    def test_incomplete_registry_rejected(self):
        self.registry["complete"] = False
        with self.assertRaises(ValueError):
            build(self.registry, self.differences, self.tiered)

    def test_promoted_tiered_packet_rejected(self):
        self.tiered["reviewed_membership"] = True
        with self.assertRaises(ValueError):
            build(self.registry, self.differences, self.tiered)


class IdentityResolutionBoundaryTests(unittest.TestCase):
    def fixtures(self):
        source = IdentityResolutionPacketTests()
        source.setUp()
        return source.registry, source.differences, source.tiered

    def test_shared_handle_preserves_every_legacy_registry_identity(self):
        import copy

        registry, differences, tiered = self.fixtures()
        registry["keyed_rows"].append(
            dict(
                registry["keyed_rows"][0],
                Id=2,
                SourceKey="dora:other",
                CanonicalKey="PUB:other",
                PublicationDate=None,
            )
        )
        registry["keyed_total"] = 2
        differences["invalid"].append({"side": "registry", "raw_key": "dora:other"})
        before = copy.deepcopy((registry, differences, tiered))
        packet = build(registry, differences, tiered)
        self.assertEqual(
            packet["model_additional_membership"][0][
                "linked_legacy_conflict_registry_ids"
            ],
            [1, 2],
        )
        self.assertEqual(len(packet["legacy_invalid_registry_identities"]), 2)
        self.assertEqual(packet["original_registry_rows"], registry["keyed_rows"])
        self.assertEqual((registry, differences, tiered), before)
        self.assertEqual(packet["original_registry_rows"][0]["PMID"], "0")
        self.assertFalse(packet["identity_merge_authorized"])
        self.assertFalse(packet["review_authority"])
        self.assertFalse(packet["routine_admission_prerequisite"])

    def test_ambiguous_source_evidence_is_preserved_without_selecting_identity(self):
        registry, differences, tiered = self.fixtures()
        tiered["rows"].append(
            dict(tiered["rows"][0], SourceID="DORA:https://example.test/handle/other")
        )
        packet = build(registry, differences, tiered)
        row = packet["model_additional_membership"][0]
        self.assertEqual(row["candidate_count"], 2)
        self.assertEqual(row["disposition"], "ambiguous_or_missing_evidence")
        self.assertEqual(len(row["candidate_dora_source_ids"]), 2)
        self.assertFalse(packet["registry_write_authorized"])

    def test_noncanonical_and_duplicate_typed_identities_are_rejected(self):
        for value in ("PMID:0", "PMID:0123", "PMID:１２３", " PMID:123", None):
            registry, differences, tiered = self.fixtures()
            differences["model_additional_membership"][0]["typed_identity"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                build(registry, differences, tiered)
        registry, differences, tiered = self.fixtures()
        differences["model_additional_membership"] *= 2
        with self.assertRaises(ValueError):
            build(registry, differences, tiered)

    def test_unrelated_pubmed_rows_with_unknown_dora_url_are_preserved(self):
        registry, differences, tiered = self.fixtures()
        registry["keyed_rows"].append(
            {
                "Id": 2,
                "SourceKey": "pubmed:456",
                "CanonicalKey": "PMID:456",
                "DORAURL": None,
                "PMID": "456",
                "PublicationDate": None,
                "ReviewNotes": "Keep",
            }
        )
        registry["keyed_total"] = 2
        packet = build(registry, differences, tiered)
        self.assertEqual(packet["original_registry_rows"][1], registry["keyed_rows"][1])
        self.assertEqual(packet["counts"]["legacy_invalid_registry_identities"], 1)

    def test_editing_a_diagnostic_does_not_mutate_input_evidence(self):
        registry, differences, tiered = self.fixtures()
        packet = build(registry, differences, tiered)
        packet["legacy_invalid_registry_identities"][0][
            "candidate_current_pmid_registry_ids"
        ][0].append("changed")
        packet["original_registry_rows"][0]["CanonicalKey"] = "edited output"
        self.assertEqual(tiered["rows"][0]["registry_pmid_ids"], ["2"])
        self.assertEqual(registry["keyed_rows"][0]["CanonicalKey"], "PUB:legacy")


if __name__ == "__main__":
    unittest.main()
