import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from author_registry import author_key, author_statistics, build_author_registry, normalise_name


class AuthorRegistryTests(unittest.TestCase):
    def test_existing_identifier_key_is_preserved(self):
        self.assertEqual(author_key("Jane", "0000-0001"), "AUTH:ca0fee7d46f7df8a2d92b027")

    def test_author_evidence_without_stable_publication_key_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "stable publication key"):
            build_author_registry(dora_records=[{"Authors": "Doe, Jane"}])

    def test_source_rows_reject_non_text_identity_and_evidence_values(self):
        bad_pubmed = [
            {"PMID": "123", "AuthorIndex": 1, "AuthorName": 42},
            {"PMID": "123", "AuthorIndex": 1, "AuthorName": "Doe", "ORCID": 123},
            {"PMID": "12x", "AuthorIndex": 1, "AuthorName": "Doe"},
        ]
        for row in bad_pubmed:
            with self.subTest(row=row), self.assertRaises(ValueError):
                build_author_registry(pubmed_author_rows=[row])
        with self.assertRaisesRegex(ValueError, "AttributionEvidence"):
            build_author_registry(dora_records=[{"DORAKey": "1/9", "Authors": "Doe", "AttributionEvidence": 7}])

    def test_pubmed_order_and_affiliation_indexes_must_be_positive_integers(self):
        base = {"PMID": "123", "AuthorName": "Doe"}
        for value in (True, False, 1.0, "1", 0, -1):
            with self.subTest(author_index=value), self.assertRaisesRegex(ValueError, "AuthorIndex"):
                build_author_registry(pubmed_author_rows=[{**base, "AuthorIndex": value}])
        for value in (True, 1.5, "2", 0, -1):
            with self.subTest(affiliation_index=value), self.assertRaisesRegex(ValueError, "AffiliationIndex"):
                build_author_registry(pubmed_author_rows=[{**base, "AuthorIndex": 1, "AffiliationIndex": value}])

    def test_valid_pubmed_author_order_is_preserved(self):
        _, evidence = build_author_registry(pubmed_author_rows=[
            {"PMID": "123", "AuthorIndex": 2, "AffiliationIndex": 1, "AuthorName": "Doe"},
        ])
        self.assertEqual(evidence[0]["AuthorOrder"], 2)

    def test_affiliation_confidence_does_not_depend_on_evidence_order(self):
        rows = [
            {"PMID": "123", "AuthorIndex": 1, "AuthorName": "Jane", "AffiliationIndex": 1},
            {"PMID": "123", "AuthorIndex": 1, "AuthorName": "Jane", "AffiliationIndex": 2, "AffiliationText": "Cairns Hospital"},
        ]
        for ordered in (rows, list(reversed(rows))):
            authors, evidence = build_author_registry(ordered)
            self.assertEqual(len(evidence), 2)
            self.assertEqual(authors[0]["IdentityStatus"], "Probable")
            self.assertEqual(authors[0]["IdentityConfidence"], "medium")

    def test_dora_publication_attribution_is_not_individual_affiliation(self):
        attribution = "Publication associated with Cairns Hospital"
        authors, evidence = build_author_registry(dora_records=[
            {"DORAKey": "1/9", "Authors": "Jane; Alex", "AttributionEvidence": attribution,
             "CHHHSAffiliatedAuthors": "Jane"}
        ])
        self.assertTrue(all(a["IdentityStatus"] == "Unresolved" for a in authors))
        self.assertTrue(all(r["AffiliationText"] == "" for r in evidence))
        self.assertTrue(all(r["AttributionEvidence"] == attribution for r in evidence))

    def test_dora_explicit_affiliation_is_linked_only_to_its_author(self):
        authors, evidence = build_author_registry(dora_records=[
            {"DORAKey": "1/9", "Authors": "Jane; Alex", "AuthorName": "Jane", "AffiliationText": "Cairns Hospital"}
        ])
        self.assertEqual({a["DisplayName"]: a["IdentityStatus"] for a in authors},
                         {"Jane": "Probable", "Alex": "Unresolved"})
        self.assertEqual([r["AffiliationText"] for r in evidence], ["Cairns Hospital", ""])

    def test_relationship_links_follow_their_source(self):
        pubmed_url = "https://pubmed.ncbi.nlm.nih.gov/123/"
        dora_url = "https://dora.example/1/9"
        _, evidence = build_author_registry([
            {"PMID": "123", "AuthorIndex": 1, "AuthorName": "Jane", "PubMedURL": pubmed_url, "DORAURL": dora_url},
            {"PMID": "456", "AuthorIndex": 1, "AuthorName": "Alex"},
        ], [{"DORAKey": "1/9", "Authors": "Jane", "DORAURL": dora_url, "PubMedURL": pubmed_url}])
        self.assertEqual([r["EvidenceURL"] for r in evidence], [pubmed_url, "", dora_url])

    def test_non_text_pubmed_evidence_link_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "PubMedURL"):
            build_author_registry([{"PMID": "123", "AuthorIndex": 1, "AuthorName": "Jane", "PubMedURL": 42}])

    def test_observation_times_are_preserved_per_source_relationship(self):
        observed = "2026-10-14T11:59:41.2290370Z"
        rows = [{"PMID": "1", "AuthorIndex": 1, "AuthorName": "Jane", "ORCID": "jane", "SourceObservedUTC": observed}]
        _, evidence = build_author_registry(rows, [
            {"DORAKey": "1/9", "Authors": "Jane", "ORCID": "jane", "SourceObservedUTC": "2026-10-13T00:00:00Z"},
            {"DORAKey": "1/10", "Authors": "Alex"},
        ])
        self.assertEqual([r["SourceObservedUTC"] for r in evidence], [observed, "2026-10-13T00:00:00Z", None])
        self.assertEqual(rows[0]["SourceObservedUTC"], observed)

    def test_non_text_observation_time_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "SourceObservedUTC"):
            build_author_registry(dora_records=[{"DORAKey": "1/9", "Authors": "Jane", "SourceObservedUTC": 42}])

    def test_role_counts_use_publications_and_preserve_affiliation_evidence(self):
        rows = [
            {"PMID": "1", "AuthorIndex": 1, "AuthorName": "Jane", "ORCID": "jane", "AffiliationIndex": 1},
            {"PMID": "1", "AuthorIndex": 1, "AuthorName": "Jane", "ORCID": "jane", "AffiliationIndex": 2},
            {"PMID": "1", "AuthorIndex": 2, "AuthorName": "Other"},
            {"PMID": "2", "AuthorIndex": 2, "AuthorName": "Jane", "ORCID": "jane"},
            {"PMID": "2", "AuthorIndex": 3, "AuthorName": "Other"},
            {"PMID": "3", "AuthorIndex": 1, "AuthorName": "Other"},
            {"PMID": "3", "AuthorIndex": 5, "AuthorName": "Jane", "ORCID": "jane"},
            {"PMID": "4", "AuthorIndex": 1, "AuthorName": "Jane", "ORCID": "jane"},
        ]
        authors, evidence = build_author_registry(rows)
        jane = next(a for a in authors if a["ExternalIdentifiers"] == "jane")
        self.assertEqual(len(evidence), len(rows))
        self.assertEqual(jane["PublicationCount"], 4)
        self.assertEqual(jane["FirstAuthorCount"], 2)
        self.assertEqual(jane["SeniorAuthorCount"], 2)
        self.assertEqual(jane["CollaborativeCount"], 1)

    def test_structured_pubmed_evidence_is_preserved(self):
        authors, evidence = build_author_registry([
            {"PMID": "123", "AuthorIndex": 1, "AuthorName": "Doe, Jane", "AffiliationIndex": 1,
             "AffiliationText": "Cairns Hospital", "EvidenceKind": "structured", "ORCID": "0000-0001"},
            {"PMID": "123", "AuthorIndex": 2, "AuthorName": "Smith, Alex", "AffiliationIndex": 2,
             "AffiliationText": "University", "EvidenceKind": "structured"},
        ])
        self.assertEqual(len(authors), 2)
        self.assertEqual(authors[0]["IdentityStatus"], "Confirmed")
        self.assertEqual(len(evidence), 2)
        self.assertEqual(evidence[0]["AffiliationText"], "Cairns Hospital")

    def test_name_only_dora_records_do_not_become_confirmed(self):
        authors, evidence = build_author_registry(dora_records=[
            {"DORAKey": "1/9", "DORAURL": "https://dora.example/1/9", "Authors": "Doe, Jane; Doe, Jane"}
        ])
        self.assertEqual(len(authors), 1)
        self.assertEqual(authors[0]["IdentityStatus"], "Unresolved")
        self.assertEqual(len(evidence), 2)
        self.assertTrue(all(item["ReviewStatus"] == "Needs Review" for item in evidence))

    def test_statistics_expose_unknown_completeness(self):
        authors, evidence = build_author_registry(dora_records=[{"DORAKey": "1/9", "Authors": "Doe, Jane"}])
        stats = author_statistics(authors, evidence)
        self.assertEqual(stats["AuthorCount"], 1)
        self.assertEqual(stats["Completeness"], "not_established")

    def test_name_normalisation_is_non_destructive(self):
        self.assertEqual(normalise_name("Doe, Jane"), "doejane")


if __name__ == "__main__":
    unittest.main()
