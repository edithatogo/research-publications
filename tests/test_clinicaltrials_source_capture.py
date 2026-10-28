"""Exact trial scope with fictional injected transport."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from typing import ClassVar
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from scripts import clinicaltrials_source as source
from scripts.source_capture_receipt import PRIVATE_ROOT


def raw_study(identity):
    return json.dumps(
        {
            "protocolSection": {
                "identificationModule": {"nctId": identity, "briefTitle": "x" * 400},
                "statusModule": {
                    "startDateStruct": {"date": "2026-10", "type": "ESTIMATED"}
                },
            },
            "unknown": {"keep": [False, None, 0]},
        }
    ).encode()


class Response(BytesIO):
    status = 200
    headers: ClassVar[dict] = {}


class ClinicalTrialsTests(unittest.TestCase):
    def test_all_collectors_default_to_no_retry_and_retain_http_error_bodies(self):
        from scripts import crossref_source, datacite_source

        for module, identity, url in (
            (source, "NCT00000001", source.API + "NCT00000001"),
            (
                crossref_source,
                "10.5555/example",
                crossref_source.API + "10.5555%2Fexample",
            ),
            (datacite_source, "10.5555/example", datacite_source.API),
        ):
            with (
                self.subTest(source=module.__name__),
                tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory,
            ):
                output = Path(directory) / "capture"
                error = HTTPError(
                    url, 503, "fictional", {}, BytesIO(b"complete unknown error body")
                )
                transport = Mock(side_effect=error)
                with self.assertRaises(HTTPError):
                    module.capture([identity], output, opener=transport)
                transport.assert_called_once()
                receipt = json.loads((output / "failed-generation.json").read_bytes())
                self.assertFalse(receipt["complete"])
                self.assertEqual(receipt["request_attempts"][0]["attempt"], 1)
                self.assertEqual(
                    (output / receipt["files"][0]["name"]).read_bytes(),
                    b"complete unknown error body",
                )
                self.assertFalse((output / "manifest.json").exists())

    def test_storage_failure_is_never_retried_and_keeps_partial_file_inventory(self):
        from scripts import source_capture_receipt as receipts

        real = receipts.write_verified

        def fail_after_raw(output, name, raw):
            result = real(output, name, raw)
            if name == "NCT00000001.json":
                raise OSError("fictional post-write failure")
            return result

        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            root = Path(directory) / "capture"
            transport = Mock(return_value=Response(raw_study("NCT00000001")))
            with (
                patch.object(receipts, "write_verified", side_effect=fail_after_raw),
                self.assertRaises(OSError),
            ):
                source.capture(["NCT00000001"], root, opener=transport, max_attempts=4)
            transport.assert_called_once()
            receipt = json.loads((root / "failed-generation.json").read_bytes())
            self.assertEqual(receipt["files"], [])
            self.assertEqual(receipt["observed_files"][0]["name"], "NCT00000001.json")
            self.assertFalse((root / "manifest.json").exists())

    def test_final_manifest_failure_invalidates_completion_and_allows_fresh_verified_reuse(
        self,
    ):
        from scripts import source_capture_receipt as receipts

        real = receipts.write_verified

        def fail_after_manifest(output, name, raw):
            result = real(output, name, raw)
            if name == "manifest.json":
                raise OSError("fictional final verification failure")
            return result

        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            failed = Path(directory) / "failed"
            with (
                patch.object(
                    receipts, "write_verified", side_effect=fail_after_manifest
                ),
                self.assertRaises(OSError),
            ):
                source.capture(
                    ["NCT00000001"],
                    failed,
                    opener=Mock(return_value=Response(raw_study("NCT00000001"))),
                )
            receipt = json.loads((failed / "failed-generation.json").read_bytes())
            self.assertFalse(receipt["complete"])
            self.assertIsNone(receipt["failed_id"])
            self.assertIn(
                "manifest.json", {f["name"] for f in receipt["observed_files"]}
            )
            before = {p.name: p.read_bytes() for p in failed.iterdir()}
            transport = Mock()
            result = source.capture(
                ["NCT00000001"],
                Path(directory) / "fresh",
                resume_from=failed,
                opener=transport,
            )
            self.assertTrue(result["complete"])
            transport.assert_not_called()
            self.assertEqual(before, {p.name: p.read_bytes() for p in failed.iterdir()})

    def test_complete_bytes_unknown_fields_title_and_date_precision(self):
        raw = raw_study("NCT00000001")
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            root = Path(directory) / "capture"
            result = source.capture(
                ["NCT00000001"], root, opener=Mock(return_value=Response(raw))
            )
            self.assertEqual((root / "NCT00000001.json").read_bytes(), raw)
            self.assertEqual(
                result["files"][0]["sha256"], hashlib.sha256(raw).hexdigest()
            )
            row = json.loads((root / "studies.json").read_bytes())[0]
            row["OperatorNotes"] = "human"
            fields = source.register_fields(
                row,
                hashlib.sha256(raw).hexdigest(),
                "2026-10-29T00:00:00Z",
                "https://example.invalid/archive",
            )
            self.assertEqual(len(fields["Title"]), 255)
            self.assertEqual(fields["FullStudyTitle"], "x" * 400)
            self.assertEqual(
                json.loads(fields["StartDateSource"]),
                {"date": "2026-10", "type": "ESTIMATED"},
            )
            self.assertNotIn("OperatorNotes", fields)

    def test_identity_invalid_json_and_duplicate_scope_do_not_commit(self):
        for raw in (raw_study("NCT00000002"), b'{"x":1,"x":2}', b'{"x":1e999}'):
            with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
                root = Path(directory) / "capture"
                with self.assertRaises((ValueError, KeyError)):
                    source.capture(
                        ["NCT00000001"], root, opener=Mock(return_value=Response(raw))
                    )
                self.assertEqual((root / "NCT00000001.json").read_bytes(), raw)
                self.assertTrue((root / "failed-generation.json").exists())
                self.assertFalse((root / "manifest.json").exists())
        transport = Mock()
        with self.assertRaises(ValueError):
            source.capture(
                ["NCT00000001"] * 2, PRIVATE_ROOT / "never-created", opener=transport
            )
        transport.assert_not_called()

    def test_resume_reuses_exact_verified_prefix_in_fresh_folder(self):
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            failed = Path(directory) / "failed"
            scope = ["NCT00000001", "NCT00000002"]
            with self.assertRaises(URLError):
                source.capture(
                    scope,
                    failed,
                    opener=Mock(
                        side_effect=[
                            Response(raw_study(scope[0])),
                            URLError("fictional"),
                        ]
                    ),
                )
            before = {p.name: p.read_bytes() for p in failed.iterdir()}
            transport = Mock()
            with self.assertRaises(ValueError):
                source.capture(
                    scope, failed / "nested", resume_from=failed, opener=transport
                )
            transport.assert_not_called()
            self.assertFalse((failed / "nested").exists())
            transport = Mock(return_value=Response(raw_study(scope[1])))
            result = source.capture(
                scope, Path(directory) / "resumed", resume_from=failed, opener=transport
            )
            self.assertTrue(result["complete"])
            transport.assert_called_once()
            self.assertEqual(before, {p.name: p.read_bytes() for p in failed.iterdir()})
            (failed / (scope[0] + ".json")).write_bytes(b"tampered")
            transport = Mock()
            with self.assertRaises(ValueError):
                source.capture(
                    scope,
                    Path(directory) / "refused",
                    resume_from=failed,
                    opener=transport,
                )
            transport.assert_not_called()

    def test_direct_entrypoints_and_imports_work_without_site_or_network(self):
        repo = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        with tempfile.TemporaryDirectory() as outside:
            for name in ("clinicaltrials_source", "crossref_source", "datacite_source"):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-S",
                        "-B",
                        str(repo / "scripts" / f"{name}.py"),
                        "--help",
                    ],
                    cwd=outside,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
