"""Paired declared notices are evidence; never correction or exclusion authority."""

import copy
import json
import unittest

from scripts.publication_notice_evidence import collect_notice_evidence
from scripts.publication_policy import evaluate, notice_flags
from scripts.publication_retained_cycle import retain


def object_record(pmid, ref_type, related):
    return {
        "Title": "Keep original title",
        "ReviewNotes": "Keep reviewer wording",
        "MetadataJSON": json.dumps(
            {
                "PubmedArticle": {
                    "MedlineCitation": {"PMID": pmid},
                    "PubmedData": {
                        "CommentsCorrectionsList": {
                            "CommentsCorrections": {
                                "@RefType": ref_type,
                                "PMID": related,
                                "RefSource": "Supplied citation",
                                "Note": "Literal source note",
                            }
                        }
                    },
                }
            }
        ),
    }


def xml_record(pmid, ref_type, related):
    node = lambda name, value, attrs=None: {
        "Name": name,
        "Namespace": "",
        "Value": value,
        "Attributes": attrs or [],
    }
    attributes = [{"Name": "RefType", "Namespace": "", "Value": ref_type}]
    tree = [
        node("MedlineCitation", [node("PMID", pmid)]),
        node(
            "PubmedData",
            [
                node(
                    "CommentsCorrectionsList",
                    [
                        node(
                            "CommentsCorrections",
                            [
                                node("PMID", related),
                                node("RefSource", "Supplied citation"),
                                node("Note", "Literal source note"),
                            ],
                            attributes,
                        )
                    ],
                )
            ],
        ),
    ]
    return {
        "Title": "Keep original title",
        "ReviewNotes": "Keep reviewer wording",
        "MetadataJSON": json.dumps(tree),
    }


class NoticeEvidenceTests(unittest.TestCase):
    def test_exact_directional_pairs_for_object_and_retained_xml_shapes(self):
        pairs = [
            (
                "RetractionIn",
                "RetractionOf",
                "retraction-notice",
                "subject-record",
                "notice-record",
            ),
            (
                "ErratumIn",
                "ErratumFor",
                "correction-notice",
                "subject-record",
                "notice-record",
            ),
            (
                "CorrectedandRepublishedIn",
                "CorrectedandRepublishedFrom",
                "correction-notice",
                "original-record",
                "corrected-version",
            ),
        ]
        for builder in (object_record, xml_record):
            for forward, reverse, flag, first_role, second_role in pairs:
                with self.subTest(shape=builder.__name__, forward=forward):
                    a, b = (
                        builder("123", forward, "456"),
                        builder("456", reverse, "123"),
                    )
                    before = copy.deepcopy((a, b))
                    first = collect_notice_evidence(
                        a, source_key="pubmed:123", snapshot_revision="snapshot-one"
                    )
                    second = collect_notice_evidence(
                        b, source_key="pubmed:456", snapshot_revision="snapshot-one"
                    )
                    self.assertEqual(first["flags"], [flag])
                    self.assertEqual(second["flags"], [flag])
                    self.assertEqual(
                        first["links"][0]["current_record_role"], first_role
                    )
                    self.assertEqual(
                        second["links"][0]["current_record_role"], second_role
                    )
                    self.assertEqual(first["links"][0]["related_pmid"], "456")
                    self.assertEqual(second["links"][0]["related_pmid"], "123")
                    self.assertTrue(first["source_identity_bound"])
                    self.assertFalse(first["authoritative_linkage_verified"])
                    self.assertFalse(first["consumer_accepted"])
                    self.assertFalse(first["correction_authorized"])
                    self.assertTrue(first["candidate_only"])
                    self.assertEqual((a, b), before)

    def test_retracted_republished_from_labels_republication_without_retracting_new_record(
        self,
    ):
        old = collect_notice_evidence(
            xml_record("123", "RetractedandRepublishedIn", "456"),
            source_key="pubmed:123",
        )
        new = collect_notice_evidence(
            xml_record("456", "RetractedandRepublishedFrom", "123"),
            source_key="pubmed:456",
        )
        self.assertEqual(old["flags"], ["retraction-notice"])
        self.assertEqual(new["flags"], ["correction-notice"])
        self.assertEqual(new["links"][0]["current_record_role"], "republished-version")
        self.assertEqual(new["links"][0]["related_record_role"], "retracted-original")
        self.assertFalse(new["correction_authorized"])

    def test_types_explicit_booleans_and_nested_xml_declarations_are_labels_only(self):
        for record, flag in [
            (
                {"PublicationTypes": "Journal Article; Retracted Publication"},
                "retraction-notice",
            ),
            (
                {
                    "PublicationTypeList": {
                        "PublicationType": {"#text": "Published Erratum"}
                    }
                },
                "correction-notice",
            ),
            (
                {
                    "MetadataJSON": json.dumps(
                        [
                            {
                                "Name": "PublicationType",
                                "Namespace": "",
                                "Attributes": [],
                                "Value": "Retraction Notice",
                            }
                        ]
                    )
                },
                "retraction-notice",
            ),
            ({"Retraction": True}, "retraction-notice"),
        ]:
            with self.subTest(record=record):
                result = evaluate("PubMed", "123", record)
                self.assertIn(flag, result["UncertaintyFlags"])
                self.assertEqual(result["RegistryDisposition"], "Included")
                self.assertEqual(result["Record"], record)

    def test_negations_titles_abstracts_and_ordinary_comment_links_do_not_retract(self):
        records = [
            {"Notice": "not retracted or corrected"},
            {"Notice": "uncorrected"},
            {
                "Title": "Retracted Publication",
                "Abstract": {"PublicationType": "Published Erratum"},
            },
            {
                "MetadataJSON": json.dumps(
                    {"Abstract": {"PublicationType": "Retracted Publication"}}
                )
            },
            xml_record("123", "CommentOn", "456"),
            xml_record("123", "ExpressionOfConcernIn", "456"),
        ]
        for record in records:
            with self.subTest(record=record):
                self.assertEqual(notice_flags(record), [])

    def test_missing_or_malformed_related_identity_never_becomes_linkage_proof(self):
        for related in (None, "", "0", " 456", "４５６", 456):
            record = object_record("123", "ErratumIn", related)
            result = collect_notice_evidence(record, source_key="pubmed:123")
            with self.subTest(related=related):
                self.assertIsNone(result["links"][0]["related_pmid"])
                self.assertEqual(result["links"][0]["related_pmid_raw"], related)
                self.assertFalse(result["links"][0]["authoritative_linkage_verified"])
                self.assertEqual(
                    result["links"][0]["related_ref_source"], "Supplied citation"
                )

    def test_known_foreign_metadata_does_not_label_the_requested_source(self):
        record = xml_record("999", "RetractionIn", "456")
        before = copy.deepcopy(record)
        result = evaluate("PubMed", "123", record)
        self.assertNotIn("retraction-notice", result["UncertaintyFlags"])
        self.assertIn("notice-evidence-unverified", result["UncertaintyFlags"])
        self.assertFalse(result["NoticeEvidence"]["source_identity_bound"])
        self.assertEqual(result["Record"], before)
        self.assertEqual(result["RegistryDisposition"], "Included")

    def test_invalid_metadata_retains_bytes_and_exposes_unverified_evidence(self):
        record = {"MetadataJSON": "{broken", "ReviewNotes": "Keep"}
        result = evaluate("PubMed", "123", record)
        self.assertEqual(result["Record"], record)
        self.assertIn("notice-evidence-unverified", result["UncertaintyFlags"])
        self.assertFalse(result["NoticeEvidence"]["correction_authorized"])

    def test_new_notice_observation_appends_without_erasing_history_or_reviews(self):
        original = {"Title": "Retained title", "ReviewNotes": "Retained review"}
        state = retain(
            None,
            [("123", original)],
            generation="old",
            observed_at="2026-10-01T00:00:00Z",
            source="PubMed",
            complete=True,
        )
        before = copy.deepcopy(state)
        current = xml_record("123", "ErratumIn", "456")
        candidate = retain(
            state,
            [("123", current)],
            generation="new",
            observed_at="2026-10-02T00:00:00Z",
            source="PubMed",
            complete=True,
        )
        self.assertEqual(state, before)
        self.assertEqual(candidate["versions"][0]["Record"], original)
        self.assertIn("correction-notice", candidate["versions"][1]["UncertaintyFlags"])
        self.assertEqual(candidate["versions"][1]["Record"], current)
        self.assertFalse(
            candidate["versions"][1]["NoticeEvidence"]["correction_authorized"]
        )

    def test_duplicate_source_ids_unknown_types_and_foreign_namespaces_stay_unqualified(
        self,
    ):
        for defect in ("identity", "type", "namespace", "attribute-namespace"):
            record = xml_record("123", "ErratumIn", "456")
            metadata = json.loads(record["MetadataJSON"])
            relation = metadata[1]["Value"][0]["Value"][0]
            if defect == "identity":
                metadata[0]["Value"].append(copy.deepcopy(metadata[0]["Value"][0]))
            elif defect == "type":
                relation["Attributes"][0]["Value"] = "FutureCorrectionIn"
            elif defect == "namespace":
                relation["Namespace"] = "urn:other-source"
            else:
                relation["Attributes"][0]["Namespace"] = "urn:other-source"
            record["MetadataJSON"] = json.dumps(metadata)
            result = collect_notice_evidence(record, source_key="pubmed:123")
            with self.subTest(defect=defect):
                self.assertTrue(result["issues"])
                self.assertFalse(result["correction_authorized"])
                self.assertFalse(result["authoritative_linkage_verified"])
                self.assertEqual(result["flags"], [])
