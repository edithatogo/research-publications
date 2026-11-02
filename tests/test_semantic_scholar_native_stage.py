# SPDX-License-Identifier: Apache-2.0
"""Offline admission and preservation checks for cached native source staging."""

import argparse
import base64
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from collect_semantic_scholar_publications import FIELDS
from export_publication_register import key_hash
from publication_source_pass import field_paths
from stage_semantic_scholar_native import stage


class NativeStageTests(unittest.TestCase):
    def fixture(self, root):
        def put(name, value):
            path = root / name
            path.write_text(json.dumps(value))
            return path

        rows = [{"CanonicalKey": "doi:10.1234/test", "DOI": "10.1234/test"}]
        canonical = put("canonical.json", {"records": rows, "expected_canonical_count": 1, "expected_key_sha256": key_hash(rows)})
        paper = {"paperId": "paper-1", "externalIds": {"DOI": "10.1234/test"}, "title": "Retained title", "authors": [{"name": "Alice"}]}
        raw = json.dumps(paper).encode()
        receipt = put("cached.json", {"scope": json.dumps({"ids": ["DOI:10.1234/test"], "fields": FIELDS, "transport": "single"}, sort_keys=True), "httpStatus": 200, "sha256": hashlib.sha256(raw).hexdigest(), "raw": base64.b64encode(raw).decode()})
        coverage = put("coverage.json", {"canonical_key_sha256": key_hash(rows), "counts": {"matched": 1}, "manifest": [{"key": rows[0]["CanonicalKey"], "source": "Semantic Scholar", "identifier": "DOI:10.1234/test", "status": "matched", "observation": "DOI:10.1234/test"}], "observations": {"DOI:10.1234/test": {"record": paper, "observed": "2026-11-02T00:00:00Z", "archive": receipt.name}}, "field_presence": {p: 1 for p in set(field_paths(paper))}})
        old = put("old-page.json", [])
        manifest = put("upload.json", {"site_url": "https://example.invalid", "folder": "/approved", "files": [{"name": old.name, "path": str(old), "sha256": hashlib.sha256(old.read_bytes()).hexdigest()}]})
        text = 'Names={"old-page.json"},\nFiles=if Table.RowCount(Selected)=1 then Selected else error "missing",\nVerified=if Table.RowCount(Result)=2688 and Table.RowCount(Distinct)=2688 then Result else error "duplicate"'
        tables = ["PublicationSourceEvidence", "PublicationSourceRecordChunks", "PublicationSourceArchiveChunks", "PublicationSourceFields"]
        parts = [{"path": "definition/tables/" + t + ".tmdl", "payload": base64.b64encode(text.encode()).decode()} for t in tables]
        parts.append({"path": "definition/tables/Publication.tmdl", "payload": "unchanged"})
        definition = put("definition.json", {"definition": {"parts": parts}})
        return argparse.Namespace(canonical=canonical, coverage=coverage, upload_manifest=manifest, definition=definition, output=root / "staged")

    def test_complete_cache_preserves_fields_bytes_and_other_model_parts(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.fixture(Path(directory))
            result = stage(args)
            self.assertEqual(result["providerRequests"], 0)
            self.assertEqual(result["nativeWrites"], 0)
            candidate = json.loads((args.output / "model-candidate.json").read_text())
            self.assertEqual(candidate["definition"]["parts"][-1], {"path": "definition/tables/Publication.tmdl", "payload": "unchanged"})
            manifest = json.loads((args.output / "upload-manifest.json").read_text())
            row = json.loads(Path(manifest["files"][0]["path"]).read_text())[0]
            preserved = json.loads(base64.b64decode(row["requestEvidence"]["rawBase64"]))
            self.assertEqual(preserved, row["versions"][0]["record"])
            self.assertEqual(row["versions"][0]["record"]["authors"], [{"name": "Alice"}])

    def test_deferred_collection_creates_no_staging(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.fixture(Path(directory))
            coverage = json.loads(args.coverage.read_text())
            coverage["manifest"][0]["status"] = "deferred"
            args.coverage.write_text(json.dumps(coverage))
            with self.assertRaisesRegex(ValueError, "incomplete"):
                stage(args)
            self.assertFalse(args.output.exists())

    def test_modified_cached_response_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.fixture(Path(directory))
            receipt = args.coverage.parent / "cached.json"
            data = json.loads(receipt.read_text())
            data["sha256"] = "0" * 64
            receipt.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "integrity"):
                stage(args)
            self.assertFalse(args.output.exists())


if __name__ == "__main__":
    unittest.main()
