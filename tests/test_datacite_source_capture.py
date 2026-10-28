import json
import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ClassVar
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from scripts.datacite_source import capture
from scripts.source_capture_receipt import PRIVATE_ROOT


class DataCiteCaptureTests(unittest.TestCase):
    def test_failure_envelopes_and_terminal_next_link_refuse_commit_with_raw_retained(
        self,
    ):
        cases = [
            {flag: value}
            for flag, value in (
                ("error", "failed"),
                ("errors", [{"detail": "failed"}]),
                ("partial", True),
                ("complete", False),
                ("success", False),
            )
        ] + [{"links": {"next": "https://api.datacite.org/dois?page%5Bnumber%5D=2"}}]
        for extra in cases:
            raw = json.dumps(
                {"meta": {"page": 1, "total": 0, "totalPages": 0}, "data": [], **extra}
            ).encode()
            with (
                self.subTest(extra=extra),
                TemporaryDirectory(dir=PRIVATE_ROOT) as directory,
            ):
                root = Path(directory) / "capture"
                with (
                    patch(
                        "scripts.datacite_source.urlopen",
                        return_value=self.response(raw),
                    ),
                    self.assertRaises(ValueError),
                ):
                    capture(["10.5555/example"], root)
                receipt = json.loads((root / "failed-generation.json").read_bytes())
                self.assertEqual((root / receipt["files"][0]["name"]).read_bytes(), raw)
                self.assertFalse((root / "manifest.json").exists())
        from scripts.datacite_source import _validated_page

        payload = {
            "meta": {
                "page": 1,
                "total": 0,
                "totalPages": 0,
                "ordinary_metadata": {"partial": True},
            },
            "data": [],
            "links": {"next": None},
        }
        self.assertEqual(
            _validated_page(json.dumps(payload).encode(), "10.5555/example", 1)[:2],
            (0, 1),
        )

    def test_strict_page_types_unknowns_identity_and_duplicate_records(self):
        from scripts.datacite_source import _validated_page, project

        record = {
            "id": "10.7777/output",
            "attributes": {
                "doi": "10.7777/output",
                "types": {"resourceTypeGeneral": "Other"},
                "relatedIdentifiers": [
                    {
                        "relatedIdentifierType": "DOI",
                        "relatedIdentifier": "10.5555/example",
                        "relationType": "IsSupplementTo",
                    }
                ],
                "future": {"keep": [False, None, 0]},
            },
        }
        projected = project(record, "10.5555/example")
        self.assertEqual(projected["ResourceTypes"], {"resourceTypeGeneral": "Other"})
        self.assertEqual(
            projected["Interpretation"],
            "source_assertions; conceptual_output_count_not_inferred",
        )
        for field, value in (
            ("page", True),
            ("page", 1.0),
            ("totalPages", True),
            ("totalPages", 1.0),
            ("total", True),
            ("total", 2501),
        ):
            payload = {
                "meta": {"page": 1, "total": 1, "totalPages": 1},
                "data": [record],
            }
            payload["meta"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                _validated_page(json.dumps(payload).encode(), "10.5555/example", 1)
        for raw in (b'{"meta":{},"meta":{}}', b'{"x":NaN}', b'{"x":1e999}'):
            with self.assertRaises(ValueError):
                _validated_page(raw, "10.5555/example", 1)
        with self.assertRaisesRegex(ValueError, "Repeated"):
            _validated_page(
                json.dumps(
                    {
                        "meta": {"page": 1, "total": 2, "totalPages": 1},
                        "data": [record, record],
                    }
                ).encode(),
                "10.5555/example",
                1,
            )
        record["id"] = "10.7777/other"
        with self.assertRaisesRegex(ValueError, "identity"):
            project(record, "10.5555/example")

    @staticmethod
    def empty_page():
        return json.dumps(
            {"meta": {"page": 1, "total": 0, "totalPages": 0}, "data": []}
        ).encode()

    @staticmethod
    def response(raw):
        class Response:
            status = 200
            headers: ClassVar[dict] = {"Date": "Sun, 25 Oct 2026 05:00:00 GMT"}

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self, *_args):
                return raw

        return Response()

    def test_transient_page_get_is_retried_and_attempt_is_retained(self):
        temporary = HTTPError(
            "https://api.datacite.org/dois", 429, "limited", {}, BytesIO(b"")
        )
        with TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / "capture"
            with (
                patch(
                    "scripts.datacite_source.urlopen",
                    side_effect=[temporary, self.response(self.empty_page())],
                ) as fetch,
                patch("scripts.datacite_source.time.sleep") as sleep,
            ):
                result = capture(["10.5555/example"], output, max_attempts=4)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertTrue(result["complete"])
            self.assertEqual(fetch.call_count, 2)
            sleep.assert_called_once_with(10)
            self.assertEqual(manifest["request_attempts"][0]["attempt"], 1)
            self.assertTrue(manifest["request_attempts"][0]["retryable"])
            self.assertEqual(manifest["request_attempts"][0]["http_status"], 429)
            self.assertEqual(
                next(f for f in manifest["files"] if f["kind"] == "response")[
                    "request_attempts"
                ],
                2,
            )
            self.assertEqual(
                next(f for f in manifest["files"] if f["kind"] == "response")[
                    "transient_failure_count"
                ],
                1,
            )

    def test_permanent_http_error_is_not_retried_and_failure_receipt_keeps_attempt(
        self,
    ):
        permanent = HTTPError(
            "https://api.datacite.org/dois", 400, "bad request", {}, BytesIO(b"")
        )
        with TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / "capture"
            with (  # noqa: SIM117 - keep fixture and expected-failure scopes explicit
                patch(
                    "scripts.datacite_source.urlopen", side_effect=permanent
                ) as fetch,
                patch("scripts.datacite_source.time.sleep") as sleep,
            ):
                with self.assertRaises(HTTPError):
                    capture(["10.5555/example"], output)
            receipt = json.loads((output / "failed-generation.json").read_text())
            fetch.assert_called_once()
            sleep.assert_not_called()
            self.assertEqual(receipt["request_attempts"][0]["http_status"], 400)
            self.assertFalse(receipt["request_attempts"][0]["retryable"])

    def test_exhausted_transient_errors_retain_bounded_attempt_history(self):
        errors = [
            HTTPError(
                "https://api.datacite.org/dois", 503, "unavailable", {}, BytesIO(b"")
            )
            for _ in range(4)
        ]
        with TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / "capture"
            with (  # noqa: SIM117 - keep fixture and expected-failure scopes explicit
                patch("scripts.datacite_source.urlopen", side_effect=errors) as fetch,
                patch("scripts.datacite_source.time.sleep") as sleep,
            ):
                with self.assertRaises(HTTPError):
                    capture(["10.5555/example"], output, max_attempts=4)
            receipt = json.loads((output / "failed-generation.json").read_text())
            self.assertEqual(fetch.call_count, 4)
            self.assertEqual(
                [call.args[0] for call in sleep.call_args_list], [10, 20, 40]
            )
            self.assertEqual(
                [row["attempt"] for row in receipt["request_attempts"]], [1, 2, 3, 4]
            )
            self.assertTrue(
                all(row["retryable"] for row in receipt["request_attempts"])
            )

    def test_manifest_retains_provider_date_for_exact_related_identifier_page(self):
        raw = json.dumps(
            {"meta": {"page": 1, "total": 0, "totalPages": 0}, "data": []}
        ).encode()

        class Response:
            status = 200
            headers: ClassVar[dict] = {"Date": "Sun, 25 Oct 2026 05:00:00 GMT"}

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self, *_args):
                return raw

        with TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / "capture"
            with patch("scripts.datacite_source.urlopen", return_value=Response()):
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

    def test_invalid_page_is_retained_with_failed_generation_receipt(self):
        raw = json.dumps(
            {"meta": {"page": 1, "total": 1, "totalPages": 1}, "data": []}
        ).encode()

        class Response:
            status = 200
            headers: ClassVar[dict] = {"Date": "Sun, 25 Oct 2026 05:00:00 GMT"}

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self, *_args):
                return raw

        with TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / "capture"
            with patch("scripts.datacite_source.urlopen", return_value=Response()):  # noqa: SIM117 - keep fixture and expected-failure scopes explicit
                with self.assertRaisesRegex(ValueError, "page row count"):
                    capture(["10.5555/example"], output)
            receipt_path = output / "failed-generation.json"
            receipt_bytes = receipt_path.read_bytes()
            receipt = json.loads(receipt_bytes)
            self.assertFalse(receipt["complete"])
            self.assertEqual(receipt["failed_id"], "10.5555/example")
            self.assertEqual(receipt["completed_ids"], [])
            self.assertEqual(len(receipt["files"]), 1)
            self.assertEqual((output / receipt["files"][0]["name"]).read_bytes(), raw)
            self.assertEqual(receipt_path.read_bytes(), receipt_bytes)
            self.assertFalse((output / "manifest.json").exists())

    def test_capture_resumes_only_complete_doi_query_prefix_and_restarts_failed_query(
        self,
    ):
        completed_publication = "10.5555/completed"
        publication = "10.5555/publication"

        def record(number):
            doi = f"10.7777/output-{number:02d}"
            return {
                "id": doi,
                "attributes": {
                    "doi": doi,
                    "relatedIdentifiers": [
                        {
                            "relatedIdentifierType": "DOI",
                            "relatedIdentifier": publication,
                        }
                    ],
                },
            }

        def page(number, records):
            return json.dumps(
                {
                    "meta": {"page": number, "total": 26, "totalPages": 2},
                    "data": records,
                }
            ).encode()

        class Response:
            status = 200
            headers: ClassVar[dict] = {"Date": "Sun, 25 Oct 2026 05:00:00 GMT"}

            def __init__(self, raw):
                self.raw = raw

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self, *_args):
                return self.raw

        with TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            failed = Path(directory) / "failed"
            with patch(  # noqa: SIM117 - keep fixture and expected-failure scopes explicit
                "scripts.datacite_source.urlopen",
                side_effect=[
                    Response(
                        json.dumps(
                            {
                                "meta": {"page": 1, "total": 0, "totalPages": 0},
                                "data": [],
                            }
                        ).encode()
                    ),
                    Response(page(1, [record(i) for i in range(25)])),
                    URLError("offline"),
                ],
            ):
                with self.assertRaises(URLError):
                    capture([completed_publication, publication], failed)
            receipt = json.loads((failed / "failed-generation.json").read_text())
            self.assertEqual(receipt["completed_ids"], [completed_publication])
            self.assertEqual(receipt["failed_id"], publication)
            failed_snapshot = {
                path.name: path.read_bytes() for path in failed.iterdir()
            }

            output = Path(directory) / "resumed"
            with patch(
                "scripts.datacite_source.urlopen",
                side_effect=[
                    Response(page(1, [record(i) for i in range(25)])),
                    Response(page(2, [record(25)])),
                ],
            ) as fetch:
                result = capture(
                    [completed_publication, publication], output, resume_from=failed
                )
            self.assertEqual(fetch.call_count, 2)
            self.assertTrue(result["complete"])
            self.assertEqual(
                result["queries"],
                [
                    {
                        "publication_doi": completed_publication,
                        "returned_records": 0,
                        "pages": 1,
                    },
                    {
                        "publication_doi": publication,
                        "returned_records": 26,
                        "pages": 2,
                    },
                ],
            )
            self.assertEqual(result["relationship_assertions"], 26)
            self.assertEqual(
                [entry["publication_doi"] for entry in result["files"]],
                [completed_publication, publication, publication],
            )
            self.assertEqual(
                {path.name: path.read_bytes() for path in failed.iterdir()},
                failed_snapshot,
            )

    def test_resume_rejects_scope_change_tampering_and_provider_count_drift(self):
        publication = "10.5555/publication"

        def record(number):
            doi = f"10.7777/output-{number:02d}"
            return {
                "id": doi,
                "attributes": {
                    "doi": doi,
                    "relatedIdentifiers": [
                        {
                            "relatedIdentifierType": "DOI",
                            "relatedIdentifier": publication,
                        }
                    ],
                },
            }

        raw = json.dumps(
            {
                "meta": {"page": 1, "total": 26, "totalPages": 2},
                "data": [record(i) for i in range(25)],
            }
        ).encode()

        class Response:
            status = 200
            headers: ClassVar[dict] = {}

            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self, *_args):
                return self.body

        with TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            failed = Path(directory) / "failed"
            with patch(  # noqa: SIM117 - keep fixture and expected-failure scopes explicit
                "scripts.datacite_source.urlopen",
                side_effect=[Response(raw), URLError("offline")],
            ):
                with self.assertRaises(URLError):
                    capture([publication], failed)
            with patch("scripts.datacite_source.urlopen") as fetch:
                with self.assertRaisesRegex(ValueError, "scope or status"):
                    capture(
                        ["10.5555/changed"],
                        Path(directory) / "changed",
                        resume_from=failed,
                    )
                fetch.assert_not_called()
            filename = json.loads((failed / "failed-generation.json").read_text())[
                "files"
            ][0]["name"]
            (failed / filename).write_bytes(b"tampered")
            with patch("scripts.datacite_source.urlopen") as fetch:
                with self.assertRaisesRegex(ValueError, "raw bytes differ"):
                    capture(
                        [publication], Path(directory) / "tampered", resume_from=failed
                    )
                fetch.assert_not_called()

            # Restore the receipt-bound page; the resumed provider total must match it.
            import hashlib

            inventory = json.loads((failed / "failed-generation.json").read_text())
            original = inventory["files"][0]
            (failed / filename).write_bytes(raw)
            original["sha256"] = hashlib.sha256(raw).hexdigest()
            original["bytes"] = len(raw)
            (failed / "failed-generation.json").write_text(json.dumps(inventory))
            drift = json.dumps(
                {
                    "meta": {"page": 2, "total": 27, "totalPages": 2},
                    "data": [record(25), record(26)],
                }
            ).encode()
            with patch(  # noqa: SIM117 - keep fixture and expected-failure scopes explicit
                "scripts.datacite_source.urlopen",
                side_effect=[Response(raw), Response(drift)],
            ):
                with self.assertRaisesRegex(ValueError, "count/scope changed"):
                    capture(
                        [publication], Path(directory) / "drift", resume_from=failed
                    )


if __name__ == "__main__":
    unittest.main()
