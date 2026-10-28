"""Fictional complete archives; no provider or native operations."""

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import datacite_source as collector
from scripts.prepare_datacite_output_relationships import prepare
from scripts.source_capture_receipt import PRIVATE_ROOT, json_bytes, scope_sha256
from scripts.source_relationship_evidence import fingerprint


def record(doi="10.7777/output", kind="Dataset", targets=None, version="v1"):
    return {
        "id": doi,
        "attributes": {
            "doi": doi,
            "types": {"resourceTypeGeneral": kind},
            "version": version,
            "titles": [{"title": "Source literal"}],
            "relatedIdentifiers": targets
            if targets is not None
            else [
                {
                    "relatedIdentifierType": "DOI",
                    "relatedIdentifier": "10.5555/ARTICLE",
                    "relationType": "IsSupplementTo",
                }
            ],
            "future": {"errors": ["ordinary metadata"], "keep": [False, 0, None]},
        },
    }


def fixture(root, queries=None, publications=None):
    queries = queries if queries is not None else {"10.5555/ARTICLE": [record()]}
    publications = (
        publications
        if publications is not None
        else [{"CanonicalKey": "PUB:one", "DOI": "10.5555/article", "PMID": "123"}]
    )
    root.mkdir()
    files = []
    summaries = []
    projection = []
    for target, records in queries.items():
        pages = max(1, (len(records) + 24) // 25)
        for page in range(1, pages + 1):
            selected = records[(page - 1) * 25 : page * 25]
            payload = {
                "meta": {
                    "page": page,
                    "total": len(records),
                    "totalPages": pages if records else 0,
                },
                "data": selected,
                "links": {
                    "next": collector._query_url(target, page + 1)
                    if page < pages
                    else None
                },
                "future": {"keep": True},
            }
            raw = json_bytes(payload)
            name = collector._page_name(target, page)
            (root / name).write_bytes(raw)
            files.append(
                {
                    "name": name,
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "publication_doi": target,
                    "page": page,
                    "source_url": collector._query_url(target, page),
                    "http": 200,
                    "kind": "response",
                    "attempt_count": 1,
                    "request_attempts": 1,
                    "response_date": None,
                }
            )
            projection.extend(
                value
                for r in selected
                if (value := collector.project(r, target)) is not None
            )
        summaries.append(
            {
                "publication_doi": target,
                "returned_records": len(records),
                "pages": pages,
            }
        )
    scope = {
        "kind": "complete_related_identifier_queries_for_exact_publication_dois",
        "requested_publication_dois": list(queries),
    }
    projected = json_bytes(projection)
    (root / "related-outputs.json").write_bytes(projected)
    manifest = {
        "source": "datacite",
        "scope": scope["kind"],
        "scope_sha256": scope_sha256(scope),
        "generation_id": "fictional-source-1",
        "captured_utc": "2026-10-29T00:00:00Z",
        "complete": True,
        "accepted": False,
        "requested_publication_dois": list(queries),
        "queries": summaries,
        "files": files,
        "relationship_assertions": len(projection),
        "projection_sha256": hashlib.sha256(projected).hexdigest(),
        "request_attempts": [],
        "max_read_attempts": 1,
    }
    return repin(root, manifest, publications)


def repin(root, manifest, publications):
    raw = json_bytes(manifest)
    (root / "manifest.json").write_bytes(raw)
    pin = hashlib.sha256(raw).hexdigest()
    generation = {
        "source": "datacite",
        "generation_id": "fictional-consumer-1",
        "canonical_snapshot_id": "canonical-1",
        "source_snapshot_id": manifest["generation_id"],
        "complete": True,
        "next_links": [],
        "manifest_sha256": pin,
        "source_scope_sha256": manifest["scope_sha256"],
        "publications_sha256": fingerprint(publications),
        "publication_count": len(publications),
        "query_count": len(manifest["queries"]),
    }
    return manifest, publications, pin, generation


def run(root, packet):
    _, publications, pin, generation = packet
    return prepare(
        root, publications, expected_manifest_sha256=pin, generation=generation
    )


class DataCiteRelationshipTests(unittest.TestCase):
    def test_multiple_pages_duplicate_identity_and_wrong_request_are_checked(self):
        records = [record("10.7777/output-" + str(i)) for i in range(26)]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "archive"
            packet = fixture(root, {"10.5555/ARTICLE": records})
            result = run(root, packet)
            self.assertEqual(len(result["rows"]), 26)
            self.assertEqual(result["coverage"]["canonical_publication_count"], 1)
            self.assertEqual(
                result["coverage"]["resolved_canonical_publication_count"], 1
            )
            manifest, pubs, _, _ = packet
            entry = manifest["files"][1]
            path = root / entry["name"]
            body = json.loads(path.read_bytes())
            body["data"][0] = records[0]
            raw = json_bytes(body)
            path.write_bytes(raw)
            entry.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            with self.assertRaises(ValueError):
                run(root, repin(root, manifest, pubs))
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "archive"
            m, pubs, _, _ = fixture(root)
            m["files"][0]["source_url"] = "https://other.invalid/dois"
            with self.assertRaises(ValueError):
                run(root, repin(root, m, pubs))

    def test_completed_retry_retains_error_bytes_and_refuses_unbound_attempts(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "archive"
            m, pubs, _, _ = fixture(root)
            response = m["files"][0]
            response.update(attempt_count=2, request_attempts=2)
            url = response["source_url"]
            digest = hashlib.sha256(url.encode()).hexdigest()
            raw = b"available error body"
            name = "error-" + digest[:20] + "-attempt-1.bin"
            (root / name).write_bytes(raw)
            m["files"].insert(
                0,
                {
                    **response,
                    "name": name,
                    "kind": "http_error",
                    "http": 503,
                    "attempt_count": 1,
                    "request_attempts": 1,
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                },
            )
            m["max_read_attempts"] = 2
            m["request_attempts"] = [
                {
                    "request_sha256": digest,
                    "attempt": 1,
                    "http_status": 503,
                    "retryable": True,
                    "available_response_bytes": len(raw),
                    "error_type": "HTTPError",
                    "observed_at_utc": "2026-10-29T00:00:00Z",
                }
            ]
            result = run(root, repin(root, m, pubs))
            self.assertEqual(
                result["source_files"][name]["sha256"], hashlib.sha256(raw).hexdigest()
            )
            self.assertEqual(len(result["rows"]), 1)
            m["request_attempts"] = []
            with self.assertRaises(ValueError):
                run(root, repin(root, m, pubs))

    def test_frozen_source_revision_changes_and_conflicting_overlap_never_silently_merges(
        self,
    ):
        a = "10.5555/ARTICLE"
        b = "10.5555/second"
        targets = [
            {
                "relatedIdentifierType": "DOI",
                "relatedIdentifier": doi,
                "relationType": "IsSupplementTo",
            }
            for doi in (a, b)
        ]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "archive"
            packet = fixture(
                root, {a: [record(targets=targets)], b: [record(targets=targets)]}
            )
            self.assertEqual(len(run(root, packet)["rows"]), 2)
            m, pubs, _, _ = packet
            entry = m["files"][1]
            path = root / entry["name"]
            body = json.loads(path.read_bytes())
            body["data"][0]["attributes"]["version"] = "different"
            raw = json_bytes(body)
            path.write_bytes(raw)
            entry.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            rebuilt = []
            for item in m["files"]:
                for r in json.loads((root / item["name"]).read_bytes())["data"]:
                    value = collector.project(r, item["publication_doi"])
                    if value is not None:
                        rebuilt.append(value)
            projection = json_bytes(rebuilt)
            (root / "related-outputs.json").write_bytes(projection)
            m["projection_sha256"] = hashlib.sha256(projection).hexdigest()
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                run(root, repin(root, m, pubs))
        with tempfile.TemporaryDirectory() as d:
            first_root = Path(d) / "first"
            second_root = Path(d) / "second"
            first = run(first_root, fixture(first_root))
            second = run(
                second_root,
                fixture(second_root, {"10.5555/ARTICLE": [record(version="v2")]}),
            )
            self.assertNotEqual(
                first["SourceManifestSHA256"], second["SourceManifestSHA256"]
            )
            self.assertNotEqual(
                first["ProjectionRevisionSHA256"], second["ProjectionRevisionSHA256"]
            )

    def test_literal_direction_version_unknown_metadata_repeats_and_no_count_inflation(
        self,
    ):
        target = {
            "relatedIdentifierType": "DOI",
            "relatedIdentifier": "10.5555/ARTICLE",
            "relationType": "IsSupplementTo",
        }
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "archive"
            packet = fixture(
                root,
                {"10.5555/ARTICLE": [record(targets=[target, copy.deepcopy(target)])]},
            )
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            canonical = copy.deepcopy(packet[1])
            result = run(root, packet)
            self.assertEqual(len(result["rows"]), 1)
            row = result["rows"][0]
            self.assertEqual(row["FromKey"], "datacite:10.7777/output")
            self.assertEqual(row["ToKey"], "doi:10.5555/article")
            self.assertEqual(row["RelationTypeRaw"], "IsSupplementTo")
            self.assertEqual(row["VersionRaw"], "v1")
            self.assertEqual(row["RelatedIdentifierRaw"], "10.5555/ARTICLE")
            self.assertEqual(
                row["SourceRecord"]["attributes"]["future"],
                record()["attributes"]["future"],
            )
            self.assertEqual(
                [p["relation_path"] for p in row["SourcePaths"]],
                [
                    "/data/0/attributes/relatedIdentifiers/0",
                    "/data/0/attributes/relatedIdentifiers/1",
                ],
            )
            self.assertEqual(result["coverage"]["canonical_publication_count"], 1)
            self.assertEqual(
                result["coverage"]["resolved_canonical_publication_count"], 1
            )
            self.assertIs(row["NativeG06Admission"], False)
            self.assertIs(row["CanonicalAdmission"], False)
            self.assertEqual(packet[1], canonical)
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_dataset_software_versions_and_complete_zero_are_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "archive"
            result = run(
                root,
                fixture(
                    root,
                    {
                        "10.5555/ARTICLE": [
                            record(),
                            record("10.7777/code", "Software", version=None),
                        ]
                    },
                ),
            )
            self.assertEqual(
                {r["ResourceTypeGeneralRaw"] for r in result["rows"]},
                {"Dataset", "Software"},
            )
            self.assertIsNone(
                next(
                    r
                    for r in result["rows"]
                    if r["ResourceTypeGeneralRaw"] == "Software"
                )["VersionRaw"]
            )
            self.assertEqual(result["coverage"]["software_record_count"], 1)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "archive"
            result = run(root, fixture(root, {"10.5555/ARTICLE": []}))
            self.assertTrue(result["coverage"]["complete"])
            self.assertEqual(result["coverage"]["software_record_count"], 0)
            self.assertEqual(result["rows"], [])

    def test_unknown_types_values_and_missing_relation_type_are_visible_diagnostics(
        self,
    ):
        records = [
            record(kind={"future": "unknown"}),
            record("10.7777/other", "JournalArticle"),
            record(
                "10.7777/missing",
                targets=[
                    {
                        "relatedIdentifierType": "DOI",
                        "relatedIdentifier": "10.5555/ARTICLE",
                        "relationType": None,
                    }
                ],
            ),
        ]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "archive"
            result = run(root, fixture(root, {"10.5555/ARTICLE": records}))
            self.assertEqual(len(result["diagnostics"]), 3)
            self.assertEqual(result["rows"], [])
            self.assertIn(
                {"resourceTypeGeneral": {"future": "unknown"}},
                [
                    r["SourceRecord"]["attributes"]["types"]
                    for r in result["diagnostics"]
                ],
            )
            self.assertTrue(
                all(r["NativeG06Admission"] is False for r in result["diagnostics"])
            )

    def test_ambiguous_unmapped_and_incomplete_canonical_generation(self):
        for publications, state, count in (
            (
                [
                    {"CanonicalKey": "PUB:a", "DOI": "10.5555/article"},
                    {"CanonicalKey": "PUB:b", "DOI": "10.5555/article"},
                ],
                "Ambiguous publication",
                2,
            ),
            ([], "Unmapped publication", 0),
        ):
            with tempfile.TemporaryDirectory() as d:
                root = Path(d) / "archive"
                packet = fixture(root, publications=publications)
                result = run(root, packet)
                row = result["rows"][0]
                self.assertEqual(row["CanonicalKey"], "")
                self.assertEqual(row["CanonicalMatchCount"], count)
                self.assertEqual(row["AdmissionState"], state)
        for field, value in (
            ("complete", False),
            ("publication_count", True),
            ("publications_sha256", "0" * 64),
            ("source_snapshot_id", "wrong"),
            ("query_count", 0),
            ("next_links", ["next"]),
            ("errors", []),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as d:
                root = Path(d) / "archive"
                packet = fixture(root)
                packet[3][field] = value
                with self.assertRaises(ValueError):
                    run(root, packet)

    def test_duplicate_canonical_keys_are_not_merged_even_with_recomputed_generation(
        self,
    ):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "archive"
            packet = fixture(
                root,
                publications=[{"CanonicalKey": "PUB:a", "DOI": "10.5555/article"}] * 2,
            )
            with self.assertRaises(ValueError):
                run(root, packet)

    def test_cached_same_byte_hash_and_projection_reads_each_file_once(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "archive"
            packet = fixture(root)
            real = Path.read_bytes
            reads = {}

            def read(path):
                reads[path.name] = reads.get(path.name, 0) + 1
                if reads[path.name] > 1:
                    raise AssertionError("Mutable second read")
                return real(path)

            with (
                patch.object(Path, "read_bytes", read),
                patch.object(
                    collector, "urlopen", side_effect=AssertionError("No provider I/O")
                ),
            ):
                result = run(root, packet)
            self.assertEqual(set(reads), {p.name for p in root.iterdir()})
            self.assertTrue(all(n == 1 for n in reads.values()))
            self.assertEqual(
                result["rows"][0]["SourcePaths"][0]["sha256"],
                packet[0]["files"][0]["sha256"],
            )

    def test_exact_scope_pages_and_projection_must_reconcile_even_when_rehashed(self):
        for case in ("total", "bool_page", "duplicate_query", "scope", "projection"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as d:
                root = Path(d) / "archive"
                packet = fixture(root)
                m, publications, _, _ = packet
                if case in ("total", "bool_page"):
                    entry = m["files"][0]
                    path = root / entry["name"]
                    body = json.loads(path.read_bytes())
                    body["meta"]["total" if case == "total" else "page"] = (
                        2 if case == "total" else True
                    )
                    raw = json_bytes(body)
                    path.write_bytes(raw)
                    entry.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                elif case == "duplicate_query":
                    m["queries"].append(copy.deepcopy(m["queries"][0]))
                elif case == "scope":
                    m["scope_sha256"] = "0" * 64
                else:
                    raw = json_bytes([])
                    (root / "related-outputs.json").write_bytes(raw)
                    m["projection_sha256"] = hashlib.sha256(raw).hexdigest()
                    m["relationship_assertions"] = 0
                with self.assertRaises(ValueError):
                    run(root, repin(root, m, publications))

    def test_failed_partial_contradictory_and_unsafe_archive_never_become_zero(self):
        for case in (
            "failed_marker",
            "partial",
            "errors",
            "missing",
            "extra",
            "symlink",
            "unsafe_name",
            "native_cursor",
        ):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as d:
                root = Path(d) / "archive"
                packet = fixture(root)
                m, pubs, _, _ = packet
                if case == "failed_marker":
                    (root / "failed-generation.json").write_bytes(b"{}")
                elif case == "partial":
                    m["partial"] = True
                elif case == "errors":
                    m["errors"] = []
                elif case == "missing":
                    (root / m["files"][0]["name"]).unlink()
                elif case == "extra":
                    (root / "unlisted.json").write_bytes(b"{}")
                elif case == "symlink":
                    path = root / m["files"][0]["name"]
                    path.unlink()
                    path.symlink_to(root / "related-outputs.json")
                elif case == "unsafe_name":
                    m["files"][0]["name"] = "../escape.json"
                else:
                    m["scope"] = "native_cursor_shape"
                with self.assertRaises(ValueError):
                    run(root, repin(root, m, pubs))

    def test_terminal_continuation_and_payload_failure_refuse_even_with_valid_pin(self):
        for extra in (
            {"errors": []},
            {"partial": True},
            {"status": "failed"},
            {"links": {"next": "https://api.datacite.org/dois?page=2"}},
        ):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as d:
                root = Path(d) / "archive"
                m, pubs, _, _ = fixture(root)
                entry = m["files"][0]
                path = root / entry["name"]
                payload = json.loads(path.read_bytes())
                payload.update(extra)
                raw = json_bytes(payload)
                path.write_bytes(raw)
                entry.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                with self.assertRaises(ValueError):
                    run(root, repin(root, m, pubs))

    def test_replay_is_identical_and_revision_changes_with_pinned_input(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "archive"
            packet = fixture(root)
            first = run(root, packet)
            self.assertEqual(first, run(root, packet))
            packet[3]["canonical_snapshot_id"] = "new-canonical-snapshot"
            second = run(root, packet)
            self.assertNotEqual(
                first["ProjectionRevisionSHA256"], second["ProjectionRevisionSHA256"]
            )
            self.assertEqual(
                first["rows"][0]["EvidenceKey"], second["rows"][0]["EvidenceKey"]
            )

    def test_direct_cli_is_private_create_only_and_imports_without_site_packages(self):
        repo = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        with (
            tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as d,
            tempfile.TemporaryDirectory() as outside,
        ):
            folder = Path(d)
            root = folder / "archive"
            _, pubs, pin, generation = fixture(root)
            (folder / "publications.json").write_bytes(json_bytes(pubs))
            (folder / "generation.json").write_bytes(json_bytes(generation))
            output = folder / "review" / "relationships.json"
            command = [
                sys.executable,
                "-S",
                "-B",
                str(repo / "scripts/prepare_datacite_output_relationships.py"),
                "--capture",
                str(root),
                "--publications",
                str(folder / "publications.json"),
                "--generation",
                str(folder / "generation.json"),
                "--manifest-sha256",
                pin,
                "--output",
                str(output),
            ]
            result = subprocess.run(
                command,
                cwd=outside,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            raw = output.read_bytes()
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertNotEqual(
                subprocess.run(
                    command, cwd=outside, env=env, capture_output=True, check=False
                ).returncode,
                0,
            )
            self.assertEqual(output.read_bytes(), raw)
            command[-1] = str(root / "mutate-archive.json")
            self.assertNotEqual(
                subprocess.run(
                    command, cwd=outside, env=env, capture_output=True, check=False
                ).returncode,
                0,
            )
            self.assertFalse((root / "mutate-archive.json").exists())


def native_fixture(root, records=None):
    root.mkdir()
    target = "10.5555/ARTICLE"
    records = copy.deepcopy(records if records is not None else [record()])
    for r in records:
        r["attributes"]["xml"] = "<resource/>"
    options = {"detail": "true", "affiliation": "true", "publisher": "true"}
    cutoff = "2026-10-29T00:00:00Z"
    base = 'creators.affiliation.name:"Fictional"'
    related = 'relatedIdentifiers.relatedIdentifier:("' + target + '")'
    scope = {
        "scope_sha256": "f" * 64,
        "institutional_queries": [
            {"key": "institutional-0", "kind": "institutional", "query": base}
        ],
        "related_dois_per_query": 20,
        "rows_per_page": 1,
        "full_metadata_options": options,
    }
    source_queries = [
        *scope["institutional_queries"],
        {"key": "related-0", "kind": "related", "query": related},
    ]
    queries = []
    for spec in source_queries:
        expression = "(" + spec["query"] + ') AND created:[* TO "' + cutoff + '"]'
        pages = []
        for i in range(max(1, len(records))):
            subset = records[i : i + 1]
            name = spec["key"] + "-page-" + str(i) + ".json"
            params = {
                "query": expression,
                "page[cursor]": "1" if i == 0 else "cursor-" + str(i),
                "page[size]": 1,
                **options,
            }
            next_link = (
                "https://api.datacite.org/dois?page%5Bcursor%5D=cursor-" + str(i + 1)
                if i < len(records) - 1
                else None
            )
            outer = {
                "uri": collector.API,
                "http_status": 200,
                "parameters": params,
                "headers": {},
                "body": {
                    "meta": {"total": len(records), "totalPages": len(records)},
                    "data": subset,
                    "links": {"next": next_link},
                },
            }
            (root / name).write_bytes(json_bytes(outer))
            pages.append(
                {"file": name, "rows": len(subset), "saved_content_equal": True}
            )
        q = {
            "key": spec["key"],
            "kind": spec["kind"],
            "query": expression,
            "complete": True,
            "provider_total": len(records),
            "received": len(records),
            "unique_dois": len(records),
            "pages": pages,
        }
        queries.append(q)
        (root / (spec["key"] + "-complete.json")).write_bytes(json_bytes(q))
    manifest = {
        "source": "datacite",
        "format": "rims-datacite-discovery-v1",
        "complete": True,
        "archive_folder": "/Documents/Archive/datacite-discovery-fictional",
        "scope_sha256": scope["scope_sha256"],
        "full_reconciliation": True,
        "until": cutoff,
        "baseline_completed_at": cutoff,
        "capture_run": "fictional-native-run",
        "publication_dois": [target],
        "queries": queries,
        "full_metadata_options": options,
        "downstream_selection_applied": False,
        "publication_doi_population_kind": "fictional_source",
        "publication_doi_snapshot": "publication-doi-source.json",
    }
    inputs = {
        "publication_dois": [target],
        "rows": [{"source": "fictional"}],
        "source_count": 1,
        "queries": source_queries,
        "invalid_values": [],
        "population_kind": "fictional_source",
        "observed_utc": None,
    }
    for name, value in (
        ("manifest.json", manifest),
        ("scope.json", scope),
        ("publication-doi-source.json", inputs),
        ("datacite-discovery-complete-fictional-native-run.json", manifest),
    ):
        (root / name).write_bytes(json_bytes(value))
    return native_pin(root, [{"CanonicalKey": "PUB:one", "DOI": "10.5555/article"}])


def native_pin(root, publications):
    manifest = json.loads((root / "manifest.json").read_bytes())
    pin = hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
    files = {}
    for path in root.iterdir():
        if path.is_file():
            raw = path.read_bytes()
            files[path.name] = {
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
    receipt = json_bytes({"run": manifest["capture_run"], "files": files})
    receipt_pin = hashlib.sha256(receipt).hexdigest()
    generation = {
        "source": "datacite",
        "generation_id": "fictional-review",
        "canonical_snapshot_id": "canonical-1",
        "source_snapshot_id": manifest["capture_run"],
        "complete": True,
        "next_links": [],
        "manifest_sha256": pin,
        "source_scope_sha256": manifest["scope_sha256"],
        "publications_sha256": fingerprint(publications),
        "publication_count": len(publications),
        "query_count": len(manifest["queries"]),
        "native_receipt_sha256": receipt_pin,
    }
    return publications, pin, generation, receipt, receipt_pin


def native_run(root, packet, **extra):
    publications, pin, generation, receipt, receipt_pin = packet
    return prepare(
        root,
        publications,
        expected_manifest_sha256=pin,
        generation=generation,
        profile="native_cursor",
        native_receipt=receipt,
        expected_receipt_sha256=receipt_pin,
        **extra,
    )


class NativeDataCiteRelationshipTests(unittest.TestCase):
    def test_native_cursor_archive_reuses_pinned_bytes_and_combines_occurrences(self):
        relation = {
            "relatedIdentifierType": "DOI",
            "relatedIdentifier": "10.5555/ARTICLE",
            "relationType": "IsSupplementTo",
        }
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "native"
            packet = native_fixture(
                root,
                [
                    record(targets=[relation, copy.deepcopy(relation)]),
                    record("10.7777/code", "Software"),
                ],
            )
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            real = Path.read_bytes
            reads = {}

            def read(path):
                reads[path.name] = reads.get(path.name, 0) + 1
                if reads[path.name] > 1:
                    raise AssertionError("Native mutable second read")
                return real(path)

            with (
                patch.object(Path, "read_bytes", read),
                patch.object(
                    collector, "urlopen", side_effect=AssertionError("No acquisition")
                ),
            ):
                result = native_run(root, packet)
            self.assertEqual(len(result["rows"]), 2)
            dataset = next(
                r for r in result["rows"] if r["ResourceTypeGeneralRaw"] == "Dataset"
            )
            self.assertEqual(len(dataset["SourcePaths"]), 4)
            self.assertTrue(
                all(
                    p["relation_path"].startswith("/body/data/")
                    for p in dataset["SourcePaths"]
                )
            )
            self.assertIsNone(dataset["SourceCapturedUTC"])
            self.assertEqual(result["coverage"]["software_record_count"], 1)
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
            self.assertEqual(set(reads), set(before))

    def test_native_pagination_and_independent_proof_fail_closed(self):
        for case in (
            "next_origin",
            "cursor_cycle",
            "duplicate_id",
            "bool_http",
            "missing_xml",
            "receipt_hash",
            "scope_hash",
            "query_receipt",
            "failed_payload",
        ):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as d:
                root = Path(d) / "native"
                packet = native_fixture(
                    root, [record(), record("10.7777/code", "Software")]
                )
                path = root / "related-0-page-0.json"
                page = json.loads(path.read_bytes())
                if case == "next_origin":
                    page["body"]["links"]["next"] = (
                        "https://other.invalid/dois?page%5Bcursor%5D=x"
                    )
                elif case == "cursor_cycle":
                    page["body"]["links"]["next"] = (
                        "https://api.datacite.org/dois?page%5Bcursor%5D=1"
                    )
                elif case == "duplicate_id":
                    p = root / "related-0-page-1.json"
                    x = json.loads(p.read_bytes())
                    x["body"]["data"] = page["body"]["data"]
                    p.write_bytes(json_bytes(x))
                elif case == "bool_http":
                    page["http_status"] = True
                elif case == "missing_xml":
                    page["body"]["data"][0]["attributes"].pop("xml")
                elif case == "scope_hash":
                    p = root / "scope.json"
                    x = json.loads(p.read_bytes())
                    x["scope_sha256"] = "0" * 64
                    p.write_bytes(json_bytes(x))
                elif case == "query_receipt":
                    p = root / "related-0-complete.json"
                    x = json.loads(p.read_bytes())
                    x["complete"] = False
                    p.write_bytes(json_bytes(x))
                elif case == "failed_payload":
                    page["body"]["errors"] = []
                path.write_bytes(json_bytes(page))
                updated = native_pin(root, packet[0])
                if case == "receipt_hash":
                    updated = (*updated[:-1], "0" * 64)
                with self.assertRaises(ValueError):
                    native_run(root, updated)

    def test_native_complete_zero_is_not_unavailable(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "native"
            result = native_run(root, native_fixture(root, []))
            self.assertEqual(result["rows"], [])
            self.assertTrue(result["coverage"]["complete"])
            self.assertEqual(result["coverage"]["software_record_count"], 0)

    def test_native_overlap_requires_prior_pin_and_exact_seven_day_window(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "native"
            packet = native_fixture(root)
            manifest = json.loads((root / "manifest.json").read_bytes())
            prior = copy.deepcopy(manifest)
            prior_raw = json_bytes(prior)
            prior_pin = hashlib.sha256(prior_raw).hexdigest()
            manifest["full_reconciliation"] = False
            manifest["until"] = "2026-11-05T00:00:00Z"
            for q in manifest["queries"]:
                q["query"] = q["query"].replace(
                    'created:[* TO "2026-10-29T00:00:00Z"]',
                    'updated:["2026-10-22T00:00:00Z" TO "2026-11-05T00:00:00Z"]'
                    if q["kind"] == "institutional"
                    else 'created:[* TO "2026-11-05T00:00:00Z"]',
                )
                (root / (q["key"] + "-complete.json")).write_bytes(json_bytes(q))
                for entry in q["pages"]:
                    p = root / entry["file"]
                    x = json.loads(p.read_bytes())
                    x["parameters"]["query"] = q["query"]
                    p.write_bytes(json_bytes(x))
            (root / "manifest.json").write_bytes(json_bytes(manifest))
            (
                root / "datacite-discovery-complete-fictional-native-run.json"
            ).write_bytes(json_bytes(manifest))
            packet = native_pin(root, packet[0])
            packet[2]["prior_manifest_sha256"] = prior_pin
            result = native_run(
                root, packet, prior_manifest=prior_raw, expected_prior_sha256=prior_pin
            )
            self.assertEqual(result["coverage"]["scope"], "native_overlap_update")
            self.assertIsNone(result["rows"][0]["SourceCapturedUTC"])
            self.assertEqual(result["SourceCutoffUTC"], "2026-11-05T00:00:00Z")
            with self.assertRaises(ValueError):
                native_run(root, packet)
            with self.assertRaises(ValueError):
                native_run(
                    root,
                    packet,
                    prior_manifest=prior_raw,
                    expected_prior_sha256="0" * 64,
                )

    def test_native_reused_query_pointer_is_provenance_not_a_filesystem_instruction(
        self,
    ):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "native"
            packet = native_fixture(root)
            manifest = json.loads((root / "manifest.json").read_bytes())
            pointer = "/Documents/Archive/datacite-discovery-retained-prior"
            for q in manifest["queries"]:
                q["archive_folder"] = pointer
                for page in q["pages"]:
                    page["archive_folder"] = pointer
                (root / (q["key"] + "-complete.json")).write_bytes(json_bytes(q))
            for name in (
                "manifest.json",
                "datacite-discovery-complete-fictional-native-run.json",
            ):
                (root / name).write_bytes(json_bytes(manifest))
            result = native_run(root, native_pin(root, packet[0]))
            self.assertTrue(
                all(
                    p["native_archive_folder"] == pointer
                    for row in result["rows"]
                    for p in row["SourcePaths"]
                )
            )

    def test_native_cli_uses_only_the_frozen_archive_and_supplied_receipt(self):
        repo = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        with (
            tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as d,
            tempfile.TemporaryDirectory() as outside,
        ):
            folder = Path(d)
            root = folder / "native"
            pubs, pin, generation, receipt, receipt_pin = native_fixture(root)
            for name, value in (
                ("publications.json", json_bytes(pubs)),
                ("generation.json", json_bytes(generation)),
                ("receipt.json", receipt),
            ):
                (folder / name).write_bytes(value)
            output = folder / "review" / "native.json"
            command = [
                sys.executable,
                "-S",
                "-B",
                str(repo / "scripts/prepare_datacite_output_relationships.py"),
                "--profile",
                "native_cursor",
                "--capture",
                str(root),
                "--manifest-sha256",
                pin,
                "--publications",
                str(folder / "publications.json"),
                "--generation",
                str(folder / "generation.json"),
                "--native-receipt",
                str(folder / "receipt.json"),
                "--receipt-sha256",
                receipt_pin,
                "--output",
                str(output),
            ]
            result = subprocess.run(
                command,
                cwd=outside,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(output.read_bytes())["ArchiveProfile"], "native_cursor"
            )
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)


class DataCiteByteProofTests(unittest.TestCase):
    def test_strict_bytes_and_independent_manifest_pin_fail_before_projection(self):
        for case in (
            "pin",
            "raw_hash",
            "duplicate_manifest",
            "nonfinite_manifest",
            "duplicate_page",
        ):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as d:
                root = Path(d) / "archive"
                m, pubs, pin, generation = fixture(root)
                if case == "pin":
                    pin = "0" * 64
                elif case == "raw_hash":
                    path = root / m["files"][0]["name"]
                    path.write_bytes(path.read_bytes() + b" ")
                elif case in ("duplicate_manifest", "nonfinite_manifest"):
                    raw = (root / "manifest.json").read_bytes().rstrip()[:-1] + (
                        b',"complete":true}'
                        if case == "duplicate_manifest"
                        else b',"unexpected":1e999}'
                    )
                    (root / "manifest.json").write_bytes(raw)
                    pin = hashlib.sha256(raw).hexdigest()
                    generation["manifest_sha256"] = pin
                else:
                    entry = m["files"][0]
                    path = root / entry["name"]
                    raw = path.read_bytes().rstrip()[:-1] + b',"meta":{}}'
                    path.write_bytes(raw)
                    entry.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                    _, _, pin, generation = repin(root, m, pubs)
                with self.assertRaises(ValueError):
                    prepare(
                        root, pubs, expected_manifest_sha256=pin, generation=generation
                    )

    def test_reused_exact_query_lineage_does_not_follow_prior_private_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "archive"
            m, pubs, _, _ = fixture(root)
            digest = "a" * 64
            m["resumed_from"] = {
                "path": "/unread/fictional/failed-generation.json",
                "sha256": digest,
                "completed_ids": m["requested_publication_dois"],
            }
            m["files"][0]["reused_from_failure_receipt"] = digest
            result = run(root, repin(root, m, pubs))
            self.assertEqual(
                result["rows"][0]["SourcePaths"][0]["PriorFailureReceiptSHA256"], digest
            )
            m["files"][0]["reused_from_failure_receipt"] = "b" * 64
            with self.assertRaises(ValueError):
                run(root, repin(root, m, pubs))

    def test_unknown_type_keeps_repeated_occurrences_and_no_invented_software(self):
        relation = {
            "relatedIdentifierType": "DOI",
            "relatedIdentifier": "10.5555/ARTICLE",
            "relationType": "FutureRelation",
        }
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "archive"
            result = run(
                root,
                fixture(
                    root,
                    {
                        "10.5555/ARTICLE": [
                            record(
                                kind=None,
                                targets=[relation, copy.deepcopy(relation)],
                                version="",
                            )
                        ]
                    },
                ),
            )
            self.assertEqual(result["rows"], [])
            row = result["diagnostics"][0]
            self.assertEqual(len(row["SourcePaths"]), 2)
            self.assertEqual(row["RelationTypeRaw"], "FutureRelation")
            self.assertEqual(row["VersionRaw"], "")
            self.assertEqual(result["coverage"]["software_record_count"], 0)
            self.assertEqual(
                result["coverage"]["unselected_or_unknown_type_record_count"], 1
            )


class NativeCanonicalCoverageTests(unittest.TestCase):
    def test_institutional_reference_can_be_observed_without_claiming_it_was_queried(
        self,
    ):
        relation = {
            "relatedIdentifierType": "DOI",
            "relatedIdentifier": "10.5555/new",
            "relationType": "IsSupplementTo",
        }
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "native"
            native_fixture(root, [record(targets=[relation])])
            publications = [
                {"CanonicalKey": "PUB:old", "DOI": "10.5555/article"},
                {"CanonicalKey": "PUB:new", "DOI": "10.5555/new"},
            ]
            result = native_run(root, native_pin(root, publications))
            self.assertEqual(len(result["rows"]), 1)
            row = result["rows"][0]
            self.assertEqual(row["CanonicalKey"], "PUB:new")
            self.assertEqual(row["RelatedIdentifierRaw"], "10.5555/new")
            self.assertIsNone(row["SourcePaths"][0]["RequestedPublicationDOIRaw"])
            self.assertEqual(row["SourcePaths"][0]["query_target_dois"], [])
            self.assertEqual(result["coverage"]["canonical_publication_count"], 2)
            self.assertEqual(
                result["coverage"]["unqueried_canonical_publication_count"], 1
            )
