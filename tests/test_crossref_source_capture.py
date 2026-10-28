import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ClassVar
from unittest.mock import patch
from urllib.error import URLError

from scripts.crossref_source import capture
from scripts.source_capture_receipt import PRIVATE_ROOT


class CrossrefCaptureTests(unittest.TestCase):
    def test_404_body_is_retained_without_json_or_absence_inference(self):
        from io import BytesIO
        from urllib.error import HTTPError

        raw = b"provider not found body"
        with TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / "capture"
            with patch(
                "scripts.crossref_source.urlopen",
                side_effect=HTTPError(
                    "https://api.crossref.org/works/10.5555%2Fexample",
                    404,
                    "missing",
                    {},
                    BytesIO(raw),
                ),
            ):
                result = capture(["10.5555/example"], output)
            self.assertEqual((output / result["files"][0]["name"]).read_bytes(), raw)
            row = json.loads((output / "publication-notices.json").read_bytes())[0]
            self.assertEqual(row["LookupStatus"], "not_found")
            self.assertEqual(row["Coverage"], "registered_metadata_only")
            self.assertIsNone(row["UpdateTo"])
            self.assertIs(result["accepted"], False)

    def test_wrong_doi_and_ambiguous_json_retain_raw_without_commit(self):
        from io import BytesIO

        class Response(BytesIO):
            status = 200
            headers: ClassVar[dict] = {}

        for raw in (
            b'{"status":"ok","message":{"DOI":"10.5555/other"}}',
            b'{"a":1,"a":2}',
            b'{"a":1e999}',
        ):
            with TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
                output = Path(directory) / "capture"
                with (
                    patch(
                        "scripts.crossref_source.urlopen", return_value=Response(raw)
                    ),
                    self.assertRaises(ValueError),
                ):
                    capture(["10.5555/example"], output)
                receipt = json.loads((output / "failed-generation.json").read_bytes())
                self.assertEqual(
                    (output / receipt["files"][0]["name"]).read_bytes(), raw
                )
                self.assertFalse((output / "manifest.json").exists())

    def test_manifest_retains_provider_date_header_with_raw_response(self):
        raw = json.dumps(
            {"status": "ok", "message": {"DOI": "10.5555/example"}}
        ).encode()

        class Response:
            status = 200
            headers: ClassVar[dict] = {"Date": "Sun, 25 Oct 2026 04:00:00 GMT"}

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self, *_args):
                return raw

        with TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / "capture"
            with patch("scripts.crossref_source.urlopen", return_value=Response()):
                result = capture(["10.5555/example"], output)

            manifest = json.loads(
                (output / "manifest.json").read_text(encoding="utf-8")
            )
            entry = manifest["files"][0]
            self.assertTrue(result["complete"])
            self.assertEqual(result["generation_id"], manifest["generation_id"])
            self.assertEqual(len(manifest["generation_id"]), 32)
            self.assertEqual(entry["response_date"], Response.headers["Date"])
            self.assertEqual((output / entry["name"]).read_bytes(), raw)

    def test_failure_after_raw_capture_writes_readback_receipt_without_completion(self):
        good = json.dumps(
            {"status": "ok", "message": {"DOI": "10.5555/first"}}
        ).encode()

        class Response:
            status = 200
            headers: ClassVar[dict] = {"Date": "Sun, 25 Oct 2026 04:00:00 GMT"}

            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self, *_args):
                return self.body

        with TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / "capture"
            with patch(  # noqa: SIM117 - keep fixture and expected-failure scopes explicit
                "scripts.crossref_source.urlopen",
                side_effect=[Response(good), URLError("offline")],
            ):
                with self.assertRaises(URLError):
                    capture(["10.5555/first", "10.5555/second"], output)
            receipt_path = output / "failed-generation.json"
            receipt_bytes = receipt_path.read_bytes()
            receipt = json.loads(receipt_bytes)
            self.assertFalse(receipt["complete"])
            self.assertEqual(receipt["format"], "rims-source-capture-failure-v1")
            self.assertEqual(receipt["completed_ids"], ["10.5555/first"])
            self.assertEqual(receipt["failed_id"], "10.5555/second")
            self.assertEqual(len(receipt["files"]), 1)
            self.assertEqual((output / receipt["files"][0]["name"]).read_bytes(), good)
            self.assertEqual(receipt_path.read_bytes(), receipt_bytes)
            self.assertFalse((output / "manifest.json").exists())

            resumed = Path(directory) / "resumed"
            second = json.dumps(
                {"status": "ok", "message": {"DOI": "10.5555/second"}}
            ).encode()
            original = {p.name: p.read_bytes() for p in output.iterdir()}
            with patch(
                "scripts.crossref_source.urlopen", return_value=Response(second)
            ) as fetch:
                result = capture(
                    ["10.5555/first", "10.5555/second"], resumed, resume_from=output
                )
            self.assertEqual(fetch.call_count, 1)
            self.assertTrue(result["complete"])
            self.assertEqual(result["count"], 2)
            self.assertEqual(
                result["resumed_from"]["sha256"],
                hashlib.sha256(receipt_bytes).hexdigest(),
            )
            self.assertEqual(
                {p.name: p.read_bytes() for p in output.iterdir()}, original
            )

    def test_resume_rejects_changed_scope_and_tampered_completed_raw(self):
        good = json.dumps(
            {"status": "ok", "message": {"DOI": "10.5555/first"}}
        ).encode()

        class Response:
            status = 200
            headers: ClassVar[dict] = {}

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self, *_args):
                return good

        with TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            failed = Path(directory) / "failed"
            with patch(  # noqa: SIM117 - keep fixture and expected-failure scopes explicit
                "scripts.crossref_source.urlopen",
                side_effect=[Response(), URLError("offline")],
            ):
                with self.assertRaises(URLError):
                    capture(["10.5555/first", "10.5555/second"], failed)
            with patch("scripts.crossref_source.urlopen") as fetch:
                with self.assertRaisesRegex(ValueError, "scope or status"):
                    capture(
                        ["10.5555/first", "10.5555/other"],
                        Path(directory) / "changed",
                        resume_from=failed,
                    )
                fetch.assert_not_called()
            receipt = json.loads((failed / "failed-generation.json").read_text())
            (failed / receipt["files"][0]["name"]).write_bytes(b"tampered")
            with patch("scripts.crossref_source.urlopen") as fetch:
                with self.assertRaisesRegex(ValueError, "raw bytes differ"):
                    capture(
                        ["10.5555/first", "10.5555/second"],
                        Path(directory) / "out",
                        resume_from=failed,
                    )
                fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
