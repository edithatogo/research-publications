"""Offline award projection and complete native source boundaries."""

import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import grants_arc_api as arc
from scripts.read_arc_committed_source import read_commit


def commit(root, *, empty=False):
    rows = (
        []
        if empty
        else [
            {
                "id": "A",
                "attributes": {
                    "code": "A",
                    "future": {"keep": [False, 0, None, "café"]},
                },
                "links": {"self": arc.API_BASE + "/A"},
            }
        ]
    )
    meta = {
        "requested-page-number": 1,
        "requested-page-size": 500,
        "actual-page-size": len(rows),
        "total-pages": 1,
        "total-size": len(rows),
    }
    files = []
    for read in (1, 2):
        name = f"pass-{read}-page-1.json"
        files.append(
            {"name": name, "verification": "exact_base64_stored_content_readback"}
        )
        (root / name).write_text(
            json.dumps(
                {
                    "pass": read,
                    "captured_utc": "2026-10-16T00:00:00Z",
                    "request": {
                        "method": "GET",
                        "uri": arc.API_BASE,
                        "queries": {"page[number]": 1, "page[size]": 500},
                    },
                    "response": {
                        "statusCode": 200,
                        "body": {
                            "data": rows,
                            "meta": meta,
                            "unknown-top-level": {"retained": True},
                        },
                    },
                }
            )
        )
    m = {
        "format": "rims-arc-source-commit-v1",
        "source_id": "arc-awards-api",
        "record_kind": "awards_only",
        "source_api": arc.API_BASE,
        "run": "synthetic-only",
        "committed_utc": "2026-10-16T00:01:00Z",
        "source_total": len(rows),
        "page_count": 1,
        "page_size": 500,
        "complete_reads": 2,
        "canonical_opportunity_admission": False,
        "candidate_filter_applied": False,
        "schedule": "manual_only",
        "files": files,
    }
    (root / "manifest.json").write_text(json.dumps(m))


class ArcNativeConsumerTests(unittest.TestCase):
    def test_direct_cli_is_offline_private_exclusive_and_preserves_inputs(self):
        repo = Path(__file__).resolve().parents[1]
        with (
            TemporaryDirectory(dir=repo / "private/ops") as output_directory,
            TemporaryDirectory() as source_directory,
            TemporaryDirectory() as outside,
        ):
            root = Path(source_directory)
            commit(root)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            output = Path(output_directory) / "derived.json"
            env = dict(os.environ)
            env.pop("PYTHONPATH", None)
            command = [
                sys.executable,
                "-S",
                str(repo / "scripts/read_arc_committed_source.py"),
                "--folder",
                str(root),
                "--catalogue",
                str(self.catalogue),
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
            saved = output.read_bytes()
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertNotEqual(
                subprocess.run(
                    command, cwd=outside, env=env, capture_output=True, check=False
                ).returncode,
                0,
            )
            self.assertEqual(output.read_bytes(), saved)
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_request_page_must_be_exact_integer_not_boolean_or_float(self):
        for page in (True, 1.0):
            with self.subTest(page=page), TemporaryDirectory() as directory:
                root = Path(directory)
                commit(root)
                path = root / "pass-1-page-1.json"
                data = json.loads(path.read_text())
                data["request"]["queries"]["page[number]"] = page
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    self.read(root)

    def test_all_twelve_fields_are_text_and_raw_hashes_remain_bound(self):
        from scripts.prepare_arc_award_export import FIELDS

        with TemporaryDirectory() as directory:
            root = Path(directory)
            commit(root)
            for filename in ("pass-1-page-1.json", "pass-2-page-1.json"):
                p = root / filename
                d = json.loads(p.read_text())
                attrs = d["response"]["body"]["data"][0]["attributes"]
                attrs.update(
                    {
                        "current-funding-amount": "001.250",
                        "grant-status": "Declined",
                        "grant-summary": None,
                    }
                )
                p.write_text(json.dumps(d))
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            result = self.read(root)
            record = result["records"][0]
            self.assertEqual(list(record), FIELDS)
            self.assertEqual(len(record), 12)
            self.assertTrue(all(type(v) is str for v in record.values()))
            self.assertEqual(record["Amount"], "001.250")
            self.assertEqual(record["Status"], "Declined")
            self.assertEqual(record["Title"], "")
            self.assertEqual(record["EvidenceHash"], "")
            self.assertFalse(result["canonical_opportunity_admission"])
            self.assertFalse(result["authoritative_lifecycle_semantics_proven"])
            for filename, hash_value in result["raw_source"][
                "stored_file_sha256"
            ].items():
                self.assertEqual(
                    hash_value, hashlib.sha256(before[filename]).hexdigest()
                )
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_ambiguous_or_nonfinite_saved_json_is_refused(self):
        for suffix in (',"run":"synthetic-only"', ',"extra":1e999', ',"extra":NaN'):
            with TemporaryDirectory() as directory:
                root = Path(directory)
                commit(root)
                p = root / "manifest.json"
                p.write_text(p.read_text().rstrip()[:-1] + suffix + "}")
                before = p.read_bytes()
                with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                    self.read(root)
                self.assertEqual(p.read_bytes(), before)

    def setUp(self):
        self.policy_directory = TemporaryDirectory()
        self.addCleanup(self.policy_directory.cleanup)
        # Fictional local declarations only; no native/source qualification is asserted.
        rows = json.loads(arc.DEFAULT_CATALOGUE.read_text())
        for row in rows:
            for value in row.get("qualification", {}).values():
                if isinstance(value, dict) and "evidence_refs" in value:
                    value["evidence_refs"] = [
                        "https://example.invalid/fictional-fixture-evidence"
                    ]
        self.catalogue = Path(self.policy_directory.name) / "catalogue.json"
        self.catalogue.write_text(json.dumps(rows))

    def read(self, root, **kwargs):
        return read_commit(root, catalogue_path=self.catalogue, **kwargs)

    def test_weekly_commit_requires_explicit_matching_schedule_without_weakening_replay(
        self,
    ):
        with TemporaryDirectory() as td:
            root = Path(td)
            commit(root)
            p = root / "manifest.json"
            d = json.loads(p.read_text())
            d["schedule"] = "weekly"
            p.write_text(json.dumps(d))
            before = {f.name: f.read_bytes() for f in root.iterdir()}
            with self.assertRaises(ValueError):
                self.read(root)
            result = self.read(root, expected_schedule="weekly")
            self.assertEqual(result["source_total"], 1)
            self.assertEqual(
                result["raw_source"]["native_manifest"]["schedule"], "weekly"
            )
            self.assertFalse(result["canonical_opportunity_admission"])
            self.assertEqual(before, {f.name: f.read_bytes() for f in root.iterdir()})
            page = root / "pass-2-page-1.json"
            data = json.loads(page.read_text())
            data["response"]["body"]["data"][0]["attributes"]["future"]["keep"].append(
                "drift"
            )
            page.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "content changed"):
                self.read(root, expected_schedule="weekly")

    def test_schedule_selection_rejects_unknown_values_and_manifest_mismatch(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            commit(root)
            for schedule in ("daily", "", None, True, []):
                with (
                    self.subTest(schedule=schedule),
                    self.assertRaisesRegex(ValueError, "Expected schedule"),
                ):
                    self.read(root, expected_schedule=schedule)
            with self.assertRaises(ValueError):
                self.read(root, expected_schedule="weekly")

    def test_complete_award_view_and_unknown_source_fields_retained(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            commit(root)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            d = self.read(root)
            self.assertEqual(d["source_total"], 1)
            self.assertEqual(d["records"][0]["SourceID"], "A")
            self.assertIn("future", d["source_attribute_fields"])
            self.assertFalse(d["canonical_opportunity_admission"])
            self.assertFalse(d["raw_source"]["original_transport_bytes_certified"])
            self.assertEqual(len(d["raw_source"]["stored_file_sha256"]), 2)
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_zero_awards_requires_both_page_files(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            commit(root, empty=True)
            d = self.read(root)
            self.assertEqual(d["records"], [])
            (root / "pass-2-page-1.json").unlink()
            with self.assertRaisesRegex(ValueError, "Missing"):
                self.read(root)

    def test_unknown_field_drift_rejects_even_when_typed_projection_equal(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            commit(root)
            p = root / "pass-2-page-1.json"
            d = json.loads(p.read_text())
            d["response"]["body"]["data"][0]["attributes"]["future"]["keep"].append(
                "changed"
            )
            p.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError, "content changed"):
                self.read(root)

    def test_manifest_and_request_purpose_cannot_be_swapped(self):
        for case in ("admission", "page", "extra"):
            with self.subTest(case=case), TemporaryDirectory() as td:
                root = Path(td)
                commit(root)
                if case == "admission":
                    p = root / "manifest.json"
                    d = json.loads(p.read_text())
                    d["canonical_opportunity_admission"] = True
                    p.write_text(json.dumps(d))
                elif case == "page":
                    p = root / "pass-1-page-1.json"
                    d = json.loads(p.read_text())
                    d["request"]["queries"]["page[number]"] = 2
                    p.write_text(json.dumps(d))
                else:
                    (root / "unexpected.json").write_text("{}")
                with self.assertRaises(ValueError):
                    self.read(root)


if __name__ == "__main__":
    unittest.main()
