import unittest

from scripts.build_publication_identity_review import build


class IdentityReviewTests(unittest.TestCase):
    def fixtures(self):
        source = "dora:abc123"
        differences = {
            "invalid": [
                {
                    "side": "registry",
                    "reason": "invalid PubMed source or positive PMID",
                    "row": {
                        "Id": 7,
                        "SourceKey": source,
                        "CanonicalKey": "PUB:stable",
                        "PMID": "0",
                        "ReviewStatus": "Included",
                    },
                }
            ]
        }
        queue = {
            "kind": "unified_publication_source_review_queue_v1",
            "candidate_only": True,
            "counts": {"total_pending": 1},
            "rows": [
                {
                    "source_key": source,
                    "source_id": "a",
                    "admission": {"reviewed_admission_proven": False},
                }
            ],
        }
        return differences, queue

    def test_exact_match_is_evidence_not_admission(self):
        packet = build(*self.fixtures())
        self.assertEqual(packet["counts"]["exact_pending_queue_matches"], 1)
        self.assertFalse(packet["rows"][0]["admission_proven"])
        self.assertIsNone(packet["rows"][0]["disposition"])

    def test_unmatched_source_stays_unmatched(self):
        differences, queue = self.fixtures()
        queue["rows"][0]["source_key"] = "dora:abc123-extra"
        packet = build(differences, queue)
        self.assertEqual(packet["counts"]["unmatched_pending_queue_sources"], 1)

    def test_rejects_key_coercion(self):
        differences, queue = self.fixtures()
        differences["invalid"][0]["row"]["CanonicalKey"] = "PMID:0"
        with self.assertRaisesRegex(ValueError, "unexpected invalid key"):
            build(differences, queue)

    def test_rejects_admitted_queue(self):
        differences, queue = self.fixtures()
        queue["rows"][0]["admission"]["reviewed_admission_proven"] = True
        with self.assertRaisesRegex(ValueError, "admitted candidate"):
            build(differences, queue)


class IdentityReviewBoundaryTests(unittest.TestCase):
    fixtures = IdentityReviewTests.fixtures

    def test_malformed_queue_and_difference_envelopes_fail_closed(self):
        for change in (
            "boolean-count",
            "row",
            "admission",
            "blank",
            "whitespace",
            "invalid-item",
        ):
            with self.subTest(change=change):
                differences, queue = self.fixtures()
                if change == "boolean-count":
                    queue["counts"]["total_pending"] = True
                elif change == "row":
                    queue["rows"][0] = None
                elif change == "admission":
                    queue["rows"][0]["admission"] = None
                elif change == "blank":
                    queue["rows"][0]["source_key"] = ""
                elif change == "whitespace":
                    queue["rows"][0]["source_key"] += " "
                else:
                    differences["invalid"][0] = None
                with self.assertRaises(ValueError):
                    build(differences, queue)
        for differences, queue in ((None, {}), ({}, None)):
            with self.assertRaises(ValueError):
                build(differences, queue)

    def test_untrimmed_legacy_keys_and_coercible_pmids_rejected(self):
        for field, value in (
            ("SourceKey", "dora: "),
            ("SourceKey", "dora:abc123 "),
            ("CanonicalKey", "PUB: "),
            ("CanonicalKey", "PUB:stable "),
            ("PMID", False),
            ("PMID", 0.0),
            ("PMID", "00"),
        ):
            with self.subTest(field=field, value=value):
                differences, queue = self.fixtures()
                differences["invalid"][0]["row"][field] = value
                with self.assertRaises(ValueError):
                    build(differences, queue)
        differences, queue = self.fixtures()
        differences["invalid"][0]["row"]["PMID"] = 0
        self.assertFalse(build(differences, queue)["rows"][0]["admission_proven"])

    def test_cli_hashes_consumed_bytes_and_preserves_existing_packet(self):
        import contextlib
        import hashlib
        import io
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from scripts.build_publication_identity_review import main

        private = Path(__file__).resolve().parents[1] / "private/ops"
        private.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=private, prefix="identity-test-"
        ) as directory:
            root = Path(directory)
            differences, queue = self.fixtures()
            for name, value in (("differences", differences), ("queue", queue)):
                (root / name).write_text(json.dumps(value))
            output = root / "packet.json"
            argv = [
                "review",
                "--differences",
                str(root / "differences"),
                "--queue",
                str(root / "queue"),
                "--output",
                str(output),
            ]
            with patch("sys.argv", argv), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
                before = output.read_bytes()
                receipt = json.loads(before)
                self.assertEqual(
                    receipt["input_sha256"]["queue"],
                    hashlib.sha256((root / "queue").read_bytes()).hexdigest(),
                )
                with self.assertRaises(FileExistsError):
                    main()
                self.assertEqual(output.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
