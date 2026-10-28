"""Durable local evidence with fictional files only."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import source_capture_receipt as receipts


class ReceiptTests(unittest.TestCase):
    def test_resume_refuses_scope_hash_boolean_counts_unindexed_files_and_symlinks(
        self,
    ):
        for case in ("scope_hash", "count", "unindexed", "symlink"):
            with (
                self.subTest(case=case),
                tempfile.TemporaryDirectory(dir=receipts.PRIVATE_ROOT) as directory,
            ):
                root = Path(directory) / "failed"
                receipts.create_output(root)
                entry = receipts.write_verified(root, "raw.json", b"{}")
                scope = {"requested_ids": ["A", "B"]}
                receipts.write_failure_receipt(
                    root,
                    source="fictional",
                    scope=scope,
                    files=[entry],
                    completed_ids=["A"],
                    failed_id="B",
                    error=ValueError("fictional"),
                )
                receipt = root / "failed-generation.json"
                data = json.loads(receipt.read_bytes())
                if case == "scope_hash":
                    data["scope_sha256"] = "0" * 64
                    receipt.write_text(json.dumps(data))
                elif case == "count":
                    data["completed_count"] = True
                    receipt.write_text(json.dumps(data))
                elif case == "unindexed":
                    (root / "extra.json").write_bytes(b"{}")
                else:
                    (root / "raw.json").unlink()
                    (root / "raw.json").symlink_to(receipt)
                with self.assertRaises(ValueError):
                    receipts.verified_failure(root, "fictional", scope, ["A", "B"])

    def test_commit_rechecks_raw_hashes_and_preserves_drift_as_failure_evidence(self):
        with tempfile.TemporaryDirectory(dir=receipts.PRIVATE_ROOT) as directory:
            root = Path(directory) / "new"
            receipts.create_output(root)
            entry = receipts.write_verified(root, "raw.json", b"{}")
            (root / "raw.json").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "changed"):
                receipts.commit_generation(root, "rows.json", [], {"files": [entry]})
            self.assertFalse((root / "manifest.json").exists())
            self.assertFalse((root / "rows.json").exists())

    def test_strict_json_rejects_ambiguous_and_nonfinite_input(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                receipts.strict_json(raw)

    def test_private_create_only_durable_failure_receipt(self):
        with tempfile.TemporaryDirectory(dir=receipts.PRIVATE_ROOT) as directory:
            output = Path(directory) / "new"
            receipts.create_output(output)
            receipts.write_verified(output, "raw.json", b'{"unknown":[false,null]}')
            receipt = receipts.write_failure_receipt(
                output,
                source="fictional",
                scope={"requested_ids": ["A"]},
                files=[],
                completed_ids=[],
                failed_id="A",
                error=ValueError("fictional"),
            )
            self.assertIs(receipt["complete"], False)
            self.assertIs(receipt["accepted"], False)
            self.assertEqual(
                receipt["observed_files"][0]["bytes"], len(b'{"unknown":[false,null]}')
            )
            self.assertEqual(
                (output / "failed-generation.json").stat().st_mode & 0o777, 0o600
            )
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            before = (output / "failed-generation.json").read_bytes()
            with self.assertRaises(FileExistsError):
                receipts.write_verified(output, "failed-generation.json", b"new")
            self.assertEqual((output / "failed-generation.json").read_bytes(), before)

    def test_public_output_and_unsafe_file_rejected(self):
        with tempfile.TemporaryDirectory() as outside:  # noqa: SIM117 - keep fixture and expected-failure scopes explicit
            with self.assertRaises(ValueError):
                receipts.create_output(Path(outside) / "capture")
        with tempfile.TemporaryDirectory(dir=receipts.PRIVATE_ROOT) as directory:  # noqa: SIM117 - keep fixture and expected-failure scopes explicit
            with self.assertRaises(ValueError):
                receipts.write_verified(Path(directory), "../escape", b"raw")

    def test_serialization_happens_before_final_artifacts(self):
        with tempfile.TemporaryDirectory(dir=receipts.PRIVATE_ROOT) as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                receipts.commit_generation(
                    root, "rows.json", [{"bad": float("inf")}], {"source": "fictional"}
                )
            self.assertEqual(list(root.iterdir()), [])
            with patch.object(  # noqa: SIM117 - keep fixture and expected-failure scopes explicit
                receipts.os, "fsync", side_effect=OSError("fictional fsync")
            ):
                with self.assertRaises(OSError):
                    receipts.write_verified(root, "raw.json", b"{}")
            self.assertEqual((root / "raw.json").read_bytes(), b"{}")
