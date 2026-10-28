import copy
import unittest

from scripts.publication_metadata_conflicts import cases_from_metadata_differences


class MetadataConflictTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {
                "item_id": 1,
                "source_key": "fixture:1",
                "values": {
                    "Title": "Context",
                    "Authors": "Retained",
                    "PublicationMonth": "2026-04",
                },
                "evidence": [
                    {
                        "evidence_id": "fixture-evidence",
                        "url": "https://example.org/source",
                    }
                ],
            }
        ]
        self.diffs = [
            {
                "id": 1,
                "field": "Authors",
                "registry": "Retained",
                "canonical": "Source",
            },
            {
                "id": 1,
                "field": "PublicationMonth",
                "registry": "2026-04",
                "canonical": "2026-09",
            },
        ]

    def build(self, **kw):
        args = {
            "source_revision": "source-v1",
            "registry_revision": "registry-v1",
            "complete": True,
        }
        args.update(kw)
        return cases_from_metadata_differences(self.diffs, self.rows, **args)

    def test_preserves_pair_and_groups_without_author_identity_merge(self):
        before = copy.deepcopy(self.rows)
        cases = self.build()
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].issue, "metadata_conflict")
        self.assertEqual(self.rows, before)
        records = {r["record_id"]: r for r in cases[0].records}
        self.assertEqual(records["registry:1"]["values"]["Authors"], "Retained")
        self.assertEqual(records["canonical-for:1"]["values"]["Authors"], "Source")
        self.assertNotIn("Title", records["canonical-for:1"]["values"])
        self.assertEqual(
            records["canonical-for:1"]["values"]["ContextTitle"], "Context"
        )

    def test_input_order_stable_and_revision_invalidates(self):
        a = self.build()[0]
        self.diffs.reverse()
        self.assertEqual(self.build()[0].case_id, a.case_id)
        self.assertNotEqual(
            self.build(registry_revision="registry-v2")[0].source_fingerprint,
            a.source_fingerprint,
        )

    def test_stale_registry_pair_rejected(self):
        self.rows[0]["values"]["Authors"] = "Edited"
        self.assertRaises(ValueError, self.build)

    def test_duplicate_unknown_field_or_incomplete_rejected(self):
        self.diffs.append(copy.deepcopy(self.diffs[0]))
        self.assertRaises(ValueError, self.build)
        self.diffs.pop()
        self.diffs[0]["field"] = "ReviewStatus"
        self.assertRaises(ValueError, self.build)
        self.assertRaises(ValueError, self.build, complete=False)

    def test_empty_and_large_input_not_silently_truncated(self):
        self.diffs = []
        self.assertEqual(self.build(), ())
        self.rows = []
        for i in range(1, 23):
            self.rows.append(
                {
                    "item_id": i,
                    "source_key": f"fixture:{i}",
                    "values": {"Authors": "Retained"},
                    "evidence": [],
                }
            )
            self.diffs.append(
                {
                    "id": i,
                    "field": "Authors",
                    "registry": "Retained",
                    "canonical": "Source",
                }
            )
        self.assertEqual(len(self.build()), 22)


class MetadataRepresentationTests(unittest.TestCase):
    def test_nested_encoding_is_only_presentation(self):
        from scripts.publication_metadata_conflicts import (
            metadata_difference_kind as kind,
        )

        self.assertEqual(
            kind("Title", "primary&amp;#x2013;secondary", "primary&#x2013;secondary"),
            "text_representation_equivalent",
        )
        self.assertEqual(
            kind("Title", "<i>Organism</i>", "Organism"),
            "text_representation_equivalent",
        )
        self.assertEqual(
            kind("PublicationYear", 0, 2002), "populated_semantic_difference_preserved"
        )
        self.assertEqual(
            kind("Authors", "A; B", "B; A"), "populated_semantic_difference_preserved"
        )
        self.assertEqual(
            kind("CHHHSAffiliatedAuthors", "A; B; A", "B, A"),
            "equal_literal_segments_not_author_identity",
        )


class MetadataReviewPaginationTests(unittest.TestCase):
    def test_all_cases_recoverable_across_pages_and_invalid_pages_rejected(self):
        from scripts.publication_metadata_conflicts import (
            cases_from_metadata_differences,
            review_page,
        )

        rows = [
            {
                "item_id": i,
                "source_key": f"fixture:{i}",
                "values": {"Title": "Retained"},
                "evidence": [],
            }
            for i in range(1, 24)
        ]
        diffs = [
            {"id": i, "field": "Title", "registry": "Retained", "canonical": "Source"}
            for i in range(1, 24)
        ]
        cases = cases_from_metadata_differences(
            diffs, rows, source_revision="s1", registry_revision="r1", complete=True
        )
        first, second = review_page(cases, 0), review_page(cases, 1)
        self.assertEqual(first["cases"] + second["cases"], cases)
        self.assertEqual(
            (first["remaining_after_page"], second["remaining_after_page"]), (3, 0)
        )
        self.assertEqual(first["total_cases"], 23)
        for index, size in ((True, 20), (-1, 20), (2, 20), (0, True), (0, 21)):
            with self.assertRaises(ValueError):
                review_page(cases, index, size)
        with self.assertRaises(ValueError):
            review_page(cases + cases[:1], 0)
        with self.assertRaises(ValueError):
            review_page((), 0)
