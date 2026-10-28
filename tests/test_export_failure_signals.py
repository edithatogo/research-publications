"""Failure-bearing extraction must not replace an accepted bibliography."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.export_publication_register import (
    assemble_paginated_export,
    export_errors,
    key_hash,
    render_exports,
)


class ExportFailureSignalsTests(unittest.TestCase):
    def setUp(self):
        fixture = Path(__file__).parent / "fixtures/webfirst-export-synthetic.json"
        self.envelope = json.loads(fixture.read_text())
        self.envelope["expected_canonical_count"] = len(self.envelope["records"])
        self.envelope["expected_key_sha256"] = key_hash(self.envelope["records"])

    def paged(self):
        envelope = copy.deepcopy(self.envelope)
        rows = envelope.pop("records")
        envelope.update(
            generation_id="synthetic-failure-check",
            expected_keys_generation_id="synthetic-failure-check",
            expected_canonical_keys=[r["CanonicalKey"] for r in rows],
            pages=[
                {
                    "page_number": 1,
                    "generation_id": "synthetic-failure-check",
                    "has_more": False,
                    "records": rows,
                }
            ],
        )
        return envelope

    def test_matching_keys_do_not_hide_extraction_or_page_failure(self):
        for field, value in [
            ("error", {"code": "QueryUserError"}),
            ("errors", ["source unavailable"]),
            ("partial", True),
            ("truncated", True),
        ]:
            for location in ("envelope", "page"):
                with self.subTest(field=field, location=location):
                    envelope = self.paged()
                    target = (
                        envelope if location == "envelope" else envelope["pages"][0]
                    )
                    target[field] = value
                    with self.assertRaisesRegex(ValueError, "failure"):
                        assemble_paginated_export(envelope)

    def test_failed_empty_response_is_not_a_verified_empty_export(self):
        envelope = self.paged()
        envelope.update(
            expected_canonical_count=0,
            expected_canonical_keys=[],
            expected_key_sha256=key_hash([]),
        )
        envelope["pages"][0]["records"] = []
        self.assertEqual(assemble_paginated_export(envelope)["records"], [])
        envelope["pages"][0]["error"] = {"code": "SourceUnavailable"}
        with self.assertRaisesRegex(ValueError, "failure"):
            assemble_paginated_export(envelope)

    def test_direct_render_rejects_failure_and_preserves_previous_output(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path(directory) / "last-good.csv"
            previous.write_bytes(b"preserved accepted output")
            destination = Path(directory) / "rejected-generation"
            self.envelope["error"] = {"code": "private-provider-diagnostic"}
            self.assertTrue(export_errors(self.envelope))
            with self.assertRaisesRegex(ValueError, "failure") as caught:
                render_exports(self.envelope, destination)
            self.assertNotIn("private-provider-diagnostic", str(caught.exception))
            self.assertFalse(destination.exists())
            self.assertEqual(previous.read_bytes(), b"preserved accepted output")

    def test_explicit_clear_markers_and_false_flags_are_accepted(self):
        envelope = self.paged()
        envelope.update(error=None, errors=[], partial=False, truncated=False)
        envelope["pages"][0].update(
            error=None, errors=[], partial=False, truncated=False
        )
        assembled = assemble_paginated_export(envelope)
        self.assertEqual(export_errors(assembled), [])


class MalformedExportSignalsTests(unittest.TestCase):
    setUp = ExportFailureSignalsTests.setUp
    paged = ExportFailureSignalsTests.paged

    def test_empty_error_objects_and_malformed_flags_cannot_mask_matching_keys(self):
        for field, value in [
            ("error", {}),
            ("errors", {}),
            ("partial", None),
            ("partial", 0),
            ("truncated", ""),
            ("truncated", []),
        ]:
            for location in ("envelope", "page"):
                envelope = self.paged()
                target = envelope if location == "envelope" else envelope["pages"][0]
                target[field] = value
                with (
                    self.subTest(field=field, value=value, location=location),
                    self.assertRaises(ValueError),
                ):
                    assemble_paginated_export(envelope)


if __name__ == "__main__":
    unittest.main()
