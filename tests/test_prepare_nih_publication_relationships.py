import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from scripts.prepare_nih_publication_relationships import ENDPOINT, project
from scripts.source_relationship_evidence import fingerprint


def fixture():
    pages = []
    for pmid, projects in ((11, ["R01AA000001", "R01AA000002"]), (22, [])):
        for offset in range(max(len(projects), 1)):
            records = (
                [
                    {
                        "coreproject": projects[offset],
                        "pmid": pmid,
                        "applid": 100 + offset,
                        "extra": {"original": [None, "unknown", "A\r\nB"]},
                    }
                ]
                if projects
                else []
            )
            request = {
                "criteria": {"pmids": [pmid]},
                "offset": offset,
                "limit": 1,
                "sort_field": "core_project_nums",
                "sort_order": "asc",
            }
            raw = json.dumps(
                {
                    "meta": {
                        "total": len(projects),
                        "offset": offset,
                        "limit": 1,
                        "sort_field": "core_project_nums",
                        "sort_order": "asc",
                    },
                    "results": records,
                    "facet_results": [],
                }
            ).encode()
            pages.append(
                {
                    "name": f"{pmid}-{offset}.json",
                    "complete": True,
                    "next_links": [],
                    "url": ENDPOINT,
                    "method": "POST",
                    "http_status": 200,
                    "observed_utc": None,
                    "request": request,
                    "raw": raw,
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
    scope = {
        "kind": "nih_reporter_publication_scope_v1",
        "complete": True,
        "next_links": [],
        "source_snapshot_id": "fictional-capture",
        "pmids": ["11", "22"],
    }
    pubs = [
        {"CanonicalKey": "PUB:fixture", "PMID": "11", "ReviewerNotes": "Human value"}
    ]
    return pages, scope, pubs


def prepare(values):
    pages, scope, pubs = values
    generation = {
        "kind": "nih_reporter_publication_generation_v1",
        "complete": True,
        "next_links": [],
        "source_snapshot_id": scope["source_snapshot_id"],
        "generation_id": "fictional-generation",
        "canonical_snapshot_id": "fictional-canonical",
        "scope_sha256": fingerprint(scope),
        "pages_sha256": fingerprint(pages),
        "publications_sha256": fingerprint(pubs),
        "publication_count": len(pubs),
        "page_count": len(pages),
    }
    pins = {
        "expected_pages_sha256": fingerprint(pages),
        "expected_scope_sha256": fingerprint(scope),
        "expected_generation_sha256": fingerprint(generation),
    }
    return generation, pins


def run(values):
    generation, pins = prepare(values)
    return project(*values, generation, **pins)


def change_response(page, change):
    doc = json.loads(page["raw"])
    change(doc)
    page["raw"] = json.dumps(doc).encode()
    page["bytes"] = len(page["raw"])
    page["sha256"] = hashlib.sha256(page["raw"]).hexdigest()


class NihPublicationRelationshipTests(unittest.TestCase):
    def test_copy_time_mutation_cannot_project_under_original_pin(self):
        values = fixture()
        generation, pins = prepare(values)
        original_deepcopy = copy.deepcopy

        def mutate_before_copy(inputs):
            change_response(
                values[0][0], lambda doc: doc["results"][0].update(applid=999)
            )
            return original_deepcopy(inputs)

        with patch(
            "scripts.prepare_nih_publication_relationships.copy.deepcopy",
            side_effect=mutate_before_copy,
        ), self.assertRaisesRegex(ValueError, "Pinned input changed"):
            project(*values, generation, **pins)

    def test_complete_candidates_preserve_values_and_zero_scope(self):
        values = fixture()
        before = copy.deepcopy(values)
        result = run(values)
        self.assertEqual(values, before)
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(result["canonical_publication_count"], 1)
        self.assertEqual(result["coverage"][1]["returned_references"], 0)
        self.assertEqual(
            result["coverage"][1]["page_evidence"][0]["sha256"], values[0][-1]["sha256"]
        )
        row = result["rows"][0]
        self.assertEqual(
            row["SourceRecord"]["extra"]["original"], [None, "unknown", "A\r\nB"]
        )
        self.assertEqual(row["ToKey"], "nih-reporter:core-project:R01AA000001")
        self.assertEqual(row["SourcePaths"], ["11-0.json:/results/0"])
        self.assertIsNone(row["ObservedUTC"])
        self.assertIsNone(row["FundingAttribution"])
        for flag in (
            "CanonicalAdmission",
            "NativeG06Admission",
            "MutationAuthorized",
            "IdentityQualified",
            "AwardIdentityQualified",
        ):
            self.assertIs(row[flag], False)

    def test_missing_and_ambiguous_canonical_are_visible_not_inferred(self):
        values = fixture()
        values[2].clear()
        self.assertEqual(run(values)["rows"][0]["CanonicalMatchCount"], 0)
        values[2].extend(
            [
                {"CanonicalKey": "PUB:a", "PMID": "11"},
                {"CanonicalKey": "PUB:b", "PMID": "11"},
            ]
        )
        row = run(values)["rows"][0]
        self.assertEqual(row["CanonicalCandidates"], ["PUB:a", "PUB:b"])
        self.assertEqual(row["CanonicalKey"], "")

    def test_missing_zero_query_does_not_mean_zero(self):
        values = fixture()
        values[0].pop()
        with self.assertRaisesRegex(ValueError, "Missing PMID"):
            run(values)

    def test_missing_duplicate_and_drifting_pages_fail(self):
        for mutation in (
            lambda p: p.pop(1),
            lambda p: p.insert(1, copy.deepcopy(p[0])),
            lambda p: change_response(p[1], lambda d: d["meta"].update(total=3)),
        ):
            values = fixture()
            mutation(values[0])
            with self.assertRaises(ValueError):
                run(values)

    def test_raw_hash_length_strict_json_and_error_envelopes(self):
        for mode in (
            "hash",
            "length",
            "duplicate_json",
            "root_error",
            "meta_partial",
            "record_error",
        ):
            with self.subTest(mode=mode):
                values = fixture()
                page = values[0][0]
                if mode == "hash":
                    page["sha256"] = "0" * 64
                elif mode == "length":
                    page["bytes"] += 1
                elif mode == "duplicate_json":
                    page["raw"] = b'{"meta":{},"meta":{}}'
                    page["bytes"] = len(page["raw"])
                    page["sha256"] = hashlib.sha256(page["raw"]).hexdigest()
                elif mode == "root_error":
                    change_response(page, lambda d: d.update(errors=[]))
                elif mode == "meta_partial":
                    change_response(page, lambda d: d["meta"].update(partial=True))
                else:
                    change_response(
                        page, lambda d: d["results"][0].update(error="failure")
                    )
                with self.assertRaises(ValueError):
                    run(values)

    def test_pins_and_generation_are_independent(self):
        values = fixture()
        generation, pins = prepare(values)
        values[2][0]["ReviewerNotes"] = "changed"
        with self.assertRaisesRegex(ValueError, "generation binding"):
            project(*values, generation, **pins)
        values = fixture()
        generation, pins = prepare(values)
        generation["generation_id"] = "other"
        with self.assertRaisesRegex(ValueError, "Pinned input"):
            project(*values, generation, **pins)

    def test_exact_request_identity_and_bounds(self):
        for mutation in (
            lambda p: p["request"]["criteria"].update(pmids=[True]),
            lambda p: p["request"]["criteria"].update(pmids=[11, 22]),
            lambda p: p["request"].update(offset=10000),
            lambda p: p["request"].update(limit=True),
            lambda p: p["request"].update(sort_order="desc"),
            lambda p: p.update(url=ENDPOINT + "?extra=1"),
            lambda p: p.update(name="../page.json"),
        ):
            values = fixture()
            mutation(values[0][0])
            with self.assertRaises(ValueError):
                run(values)

    def test_source_identifier_types_and_returned_scope(self):
        for field, value in (
            ("pmid", "11"),
            ("pmid", True),
            ("pmid", 12),
            ("coreproject", " R01AA000001"),
            ("coreproject", 123),
            ("applid", "00100"),
            ("applid", False),
            ("applid", 0),
        ):
            values = fixture()
            change_response(
                values[0][0],
                lambda d, field=field, value=value: d["results"][0].update(
                    {field: value}
                ),
            )
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                run(values)

    def test_unknown_latest_application_and_nested_metadata_survive(self):
        values = fixture()
        change_response(
            values[0][0],
            lambda d: d["results"][0].update(applid=None, notes={"partial": True}),
        )
        row = run(values)["rows"][0]
        self.assertIsNone(row["LatestApplicationID"])
        self.assertEqual(row["SourceRecord"]["notes"], {"partial": True})

    def test_duplicate_project_and_reversed_sort_fail(self):
        for project_id in ("R01AA000001", "A01AA000001"):
            values = fixture()
            change_response(
                values[0][1],
                lambda d, project_id=project_id: d["results"][0].update(
                    coreproject=project_id
                ),
            )
            with self.assertRaises(ValueError):
                run(values)

    def test_revision_preserves_stable_relation_without_deletion_authority(self):
        values = fixture()
        first = run(values)
        change_response(values[0][0], lambda d: d["results"][0].update(applid=201))
        second = run(values)
        self.assertEqual(
            first["rows"][0]["EvidenceKey"], second["rows"][0]["EvidenceKey"]
        )
        self.assertNotEqual(
            first["projection_revision_sha256"], second["projection_revision_sha256"]
        )
        self.assertEqual(first["rows"][0]["LatestApplicationID"], 100)
        self.assertFalse(second["mutation_authorized"])

    def test_duplicate_canonical_and_bad_pmid_text_fail(self):
        for record in (
            {"CanonicalKey": "pub:FIXTURE", "PMID": "22"},
            {"CanonicalKey": "PUB:other", "PMID": "011"},
        ):
            values = fixture()
            values[2].append(record)
            with self.assertRaises(ValueError):
                run(values)


if __name__ == "__main__":
    unittest.main()
