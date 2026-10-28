import copy
import json
import unittest

from scripts.publication_policy import evaluate, load_policy
from scripts.publication_retained_cycle import latest_projection, retain


class PublicationPolicyTests(unittest.TestCase):
    def test_inclusion_rule_is_identity_agnostic_across_valid_source_keys(self):
        records = [
            {"Title": "Uncertain affiliation and date"},
            {"Retraction": True, "Title": "Notice metadata is preserved"},
            {"MetadataJSON": json.dumps({"PublicationType": "Correction"})},
        ]
        outcomes = []
        for index in range(64):
            source_id = str(100000000 + index)
            result = evaluate("PubMed", source_id, records[index % len(records)])
            outcomes.append(
                (
                    result["RegistryDisposition"],
                    result["SourceEligibility"],
                    result["PolicySHA256"],
                )
            )
        self.assertEqual({item[0] for item in outcomes}, {"Included"})
        self.assertEqual({item[1] for item in outcomes}, {"eligible"})
        self.assertEqual(len({item[2] for item in outcomes}), 1)
        self.assertFalse(load_policy()["manual_record_approval"])

    def test_unknown_affiliation_and_dates_do_not_block_inclusion(self):
        row = {
            "Title": "A paper",
            "Notice": "retracted",
            "UnknownSourceField": {"keep": [1, 2]},
        }
        result = evaluate("PubMed", "123", row)
        self.assertEqual(result["RegistryDisposition"], "Included")
        self.assertEqual(result["AffiliationAttribution"], "undetermined")
        self.assertEqual(result["Record"], row)
        self.assertFalse(load_policy()["manual_record_approval"])

    def test_exact_aliases_are_generic(self):
        for alias in (
            "Cairns Hospital",
            "Cairns Base Hospital",
            "Cairns and Hinterland Hospital and Health Service",
        ):
            with self.subTest(alias=alias):
                result = evaluate(
                    "PubMed",
                    "123",
                    {
                        "AffiliationsRaw": alias,
                        "PublicationDateRaw": "2026-10-04",
                        "PublicationDatePrecision": "day",
                    },
                )
                self.assertEqual(result["AffiliationAttribution"], "attributed")

    def test_similar_names_or_titles_never_merge_sources(self):
        a = evaluate("PubMed", "123", {"Authors": "J Smith", "Title": "Same title"})
        b = evaluate(
            "DORA", "DORA:abc", {"Authors": "John Smith", "Title": "Same title"}
        )
        self.assertNotEqual(a["CanonicalSourceKey"], b["CanonicalSourceKey"])

    def test_invalid_ids_fail_without_modifying_input(self):
        row = {"Title": "Keep"}
        for key in ("0123", " 123", "1.0", "１２３"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                evaluate("PubMed", key, row)
        self.assertEqual(row, {"Title": "Keep"})

    def test_nested_source_notices_are_labelled_without_exclusion(self):
        row = {
            "MetadataJSON": json.dumps(
                {
                    "PubmedArticle": {
                        "MedlineCitation": {
                            "Article": {
                                "PublicationTypeList": {
                                    "PublicationType": [
                                        {
                                            "#text": "Retracted Publication",
                                            "@UI": "D016441",
                                        }
                                    ]
                                }
                            }
                        },
                        "PubmedData": {
                            "CommentsCorrectionsList": {
                                "CommentsCorrections": {
                                    "@RefType": "ErratumIn",
                                    "PMID": "456",
                                }
                            }
                        },
                    }
                }
            )
        }
        before = copy.deepcopy(row)
        result = evaluate("PubMed", "123", row)
        self.assertIn("retraction-notice", result["UncertaintyFlags"])
        self.assertIn("correction-notice", result["UncertaintyFlags"])
        self.assertEqual(result["RegistryDisposition"], "Included")
        self.assertEqual(result["Record"], before)
        self.assertEqual(row, before)

    def test_titles_and_abstracts_do_not_become_notice_decisions(self):
        result = evaluate(
            "PubMed",
            "123",
            {
                "Title": "Retraction and error correction",
                "MetadataJSON": json.dumps({"Abstract": "Study of correcting errors"}),
            },
        )
        self.assertNotIn("retraction-notice", result["UncertaintyFlags"])
        self.assertNotIn("correction-notice", result["UncertaintyFlags"])

    def test_explicit_notice_and_boolean_retraction_are_labelled(self):
        for record in ({"Retraction": True}, {"Notice": "RetractionIn"}):
            with self.subTest(record=record):
                self.assertIn(
                    "retraction-notice",
                    evaluate("PubMed", "123", record)["UncertaintyFlags"],
                )


class RetainedCycleTests(unittest.TestCase):
    def cycle(
        self,
        state,
        rows,
        generation,
        time="2026-10-04T01:00:00Z",
        source="PubMed",
        complete=True,
    ):
        return retain(
            state,
            rows,
            generation=generation,
            observed_at=time,
            source=source,
            complete=complete,
        )

    def test_append_update_missing_and_replay(self):
        first = self.cycle(
            None,
            [("123", {"Title": "Old"}), ("124", {"Title": "Missing later"})],
            "first",
        )
        before = copy.deepcopy(first)
        second = self.cycle(
            first,
            [("123", {"Title": "New", "Retraction": True})],
            "second",
            "2026-10-04T02:00:00Z",
        )
        self.assertEqual(first, before)
        self.assertEqual(len(second["versions"]), 3)
        self.assertEqual(set(second["latest"]), {"pubmed:123", "pubmed:124"})
        self.assertEqual(second["versions"][0]["Record"]["Title"], "Old")
        self.assertEqual(
            second["versions"][second["latest"]["pubmed:123"]]["Record"]["Title"], "New"
        )
        replay = self.cycle(
            second,
            [("123", {"Title": "New", "Retraction": True})],
            "second",
            "2026-10-04T02:00:00Z",
        )
        self.assertEqual(replay, second)
        latest = {r["SourceKey"]: r for r in latest_projection(second)}
        self.assertFalse(latest["pubmed:124"]["PresentInLatestSourceCycle"])
        self.assertTrue(latest["pubmed:123"]["PresentInLatestSourceCycle"])

    def test_corrupted_previous_version_or_projection_rejected(self):
        first = self.cycle(None, [("123", {"Title": "Old"})], "first")
        changed = copy.deepcopy(first)
        changed["versions"][0]["Record"]["Title"] = "Forged"
        with self.assertRaises(ValueError):
            self.cycle(changed, [], "second")
        changed = copy.deepcopy(first)
        changed["latest"] = {}
        with self.assertRaises(ValueError):
            latest_projection(changed)

    def test_empty_cycle_keeps_all_history(self):
        first = self.cycle(None, [("123", {})], "first")
        second = self.cycle(first, [], "empty", "2026-10-04T02:00:00Z")
        self.assertEqual(first["latest"], second["latest"])
        self.assertEqual(first["versions"], second["versions"])

    def test_other_source_retained(self):
        first = self.cycle(None, [("DORA:abc", {})], "dora", source="DORA")
        second = self.cycle(first, [("123", {})], "pubmed")
        self.assertEqual(set(second["latest"]), {"dora:abc", "pubmed:123"})

    def test_failure_duplicate_and_backdated_preserve_last_good(self):
        first = self.cycle(None, [("123", {})], "first")
        before = copy.deepcopy(first)
        cases = [{"complete": False}, {"time": "2026-10-03T01:00:00Z"}]
        for kwargs in cases:
            with self.assertRaises(ValueError):
                self.cycle(first, [("124", {})], "bad", **kwargs)
            self.assertEqual(first, before)
        with self.assertRaises(ValueError):
            self.cycle(first, [("123", {}), ("123", {})], "duplicate")
        self.assertEqual(first, before)

    def test_same_generation_changed_payload_rejected(self):
        first = self.cycle(None, [("123", {"Title": "Old"})], "first")
        with self.assertRaises(ValueError):
            self.cycle(first, [("123", {"Title": "New"})], "first")
