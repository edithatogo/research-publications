# Copyright (c) 2026 CareOps contributors.
# SPDX-License-Identifier: Apache-2.0
"""Focused preservation, document-byte and installation acceptance tests."""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("guard", HERE / "pre_push.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
POLICY = json.loads((HERE / "presidio-policy.json").read_text())


class InstallationTests(unittest.TestCase):
    def test_preserves_legacy_failure_redacts_and_refuses_changed_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            subprocess.run(
                ["git", "init", "-q", str(root)], check=True, capture_output=True
            )
            source = root / ".privacy-guard"
            source.mkdir()
            for name in [
                "install_hooks.py",
                "pre_push.py",
                "presidio_scan.py",
                "presidio-policy.json",
                "presidio-reviewed-findings.json",
                "document-approvals.json",
            ]:
                shutil.copyfile(HERE / name, source / name)
            env = root / ".venv-privacy-hooks"
            subprocess.run(
                [sys._base_executable, "-m", "venv", "--without-pip", str(env)],
                check=True,
                capture_output=True,
            )
            legacy = b"#!/bin/sh\necho synthetic-private-diagnostic\nexit 9\n"
            hook = root / ".git/hooks/pre-commit"
            hook.write_bytes(legacy)
            hook.chmod(0o700)
            command = [str(env / "bin/python"), "-I", str(source / "install_hooks.py")]
            installed = subprocess.run(
                command, cwd=root, capture_output=True, check=False
            )
            self.assertEqual(0, installed.returncode)
            self.assertEqual(
                legacy, (root / ".git/privacy-hooks-v1/pre-commit.legacy").read_bytes()
            )
            result = subprocess.run(
                [str(hook)], cwd=root, capture_output=True, check=False
            )
            self.assertNotEqual(0, result.returncode)
            self.assertNotIn(
                b"synthetic-private-diagnostic", result.stdout + result.stderr
            )
            pushed = subprocess.run(
                [
                    str(root / ".git/hooks/pre-push"),
                    "origin",
                    "https://example.invalid/unapproved",
                ],
                cwd=root,
                input=b"",
                env={**os.environ, "CI": "1"},
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, pushed.returncode)
            self.assertNotIn(str(root).encode(), pushed.stdout + pushed.stderr)
            hook.write_text("other-owner-hook\n")
            refused = subprocess.run(
                command, cwd=root, capture_output=True, check=False
            )
            self.assertNotEqual(0, refused.returncode)
            self.assertEqual("other-owner-hook\n", hook.read_text())


class DocumentTests(unittest.TestCase):
    def test_exact_document_approval_invalidated_by_changed_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            guard.git(root, "init", "-q")
            guard.git(root, "config", "user.name", "synthetic")
            guard.git(root, "config", "user.email", "synthetic@example.invalid")

            def commit(data):
                (root / "sample.pdf").write_bytes(data)
                guard.git(root, "add", ".")
                guard.git(root, "commit", "-qm", "source fixture")
                return guard.git(root, "rev-parse", "HEAD").decode().strip()

            (root / "base.txt").write_text("ordinary source")
            guard.git(root, "add", ".")
            guard.git(root, "commit", "-qm", "source fixture")
            base = guard.git(root, "rev-parse", "HEAD").decode().strip()
            tip = commit(b"synthetic\0document")
            approvals = root / "document-approvals.json"
            approvals.write_text('{"schemaVersion":1,"approvals":[]}')
            with patch.object(guard, "HERE", root):
                with self.assertRaises(guard.Refusal):
                    guard.documents(root, tip, [base], POLICY)
                approvals.write_text(
                    json.dumps(
                        {
                            "schemaVersion": 1,
                            "approvals": [
                                {
                                    "path": "sample.pdf",
                                    "sha256": hashlib.sha256(
                                        b"synthetic\0document"
                                    ).hexdigest(),
                                    "reason": "fictional test document",
                                    "reviewer": "synthetic fixture",
                                }
                            ],
                        }
                    )
                )
                guard.documents(root, tip, [base], POLICY)
                tip = commit(b"changed\0document")
                with self.assertRaises(guard.Refusal):
                    guard.documents(root, tip, [base], POLICY)


if __name__ == "__main__":
    unittest.main()


class SecretScopeTests(unittest.TestCase):
    def test_real_secret_scanner_rejects_added_then_deleted_synthetic_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            guard.git(root, "init", "-q")
            guard.git(root, "config", "user.name", "synthetic")
            guard.git(root, "config", "user.email", "synthetic@example.invalid")

            def commit(text):
                (root / "sample.txt").write_text(text)
                guard.git(root, "add", ".")
                guard.git(root, "commit", "-qm", "source fixture")
                return guard.git(root, "rev-parse", "HEAD").decode().strip()

            base = commit("ordinary source")
            guard.secrets(root, base, [base])
            marker = chr(45) * 5 + "BEGIN " + "PRIVATE" + " KEY" + chr(45) * 5
            footer = chr(45) * 5 + "END " + "PRIVATE" + " KEY" + chr(45) * 5
            # Meet the shipped rule minimum body length with fictional material.
            commit(
                marker
                + "\n"
                + "ZmFrZSBmaWN0aW9uYWwgbWF0ZXJpYWw=" * 4
                + "\n"
                + footer
                + "\n"
            )
            tip = commit("ordinary source")
            with self.assertRaises(guard.Refusal):
                guard.secrets(root, tip, [base])


class ReviewMetadataTests(unittest.TestCase):
    def item(self, text):
        raw = text.encode()
        oid = hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False
        ).hexdigest()
        return {
            "identity": hashlib.sha256(
                (".privacy-guard/presidio-reviewed-findings.json:" + oid).encode()
            ).hexdigest(),
            "text": text,
        }

    def test_only_exact_typed_control_numbers_not_free_text_or_other_paths(self):
        row = {
            "identity": "a" * 64,
            "blob_sha256": "b" * 64,
            "start": 1689,
            "end": 1692,
            "entity_index": 0,
            "value_sha256": "c" * 64,
            "reason": "contact 131000",
            "reviewer": "synthetic source review",
        }
        manifest = {
            "schemaVersion": 1,
            "policy_sha256": hashlib.sha256(
                (HERE / "presidio-policy.json").read_bytes()
            ).hexdigest(),
            "findings": [row],
        }
        text = json.dumps(manifest, separators=(",", ":"))
        item = self.item(text)
        offset = text.index("1689")
        candidate = {
            "entity_index": POLICY["entities"].index("PHONE_NUMBER"),
            "start": offset,
            "end": offset + 4,
        }
        self.assertTrue(guard.review_control_number(item, candidate, POLICY))
        self.assertFalse(
            guard.review_control_number(
                {**item, "identity": "d" * 64}, candidate, POLICY
            )
        )
        offset = text.index("131000")
        self.assertFalse(
            guard.review_control_number(
                item, {**candidate, "start": offset, "end": offset + 6}, POLICY
            )
        )

    def test_invalid_control_schema_cannot_clear_a_numeric_finding(self):
        text = '{"schemaVersion":1,"start":1689}'
        offset = text.index("1689")
        candidate = {
            "entity_index": POLICY["entities"].index("PHONE_NUMBER"),
            "start": offset,
            "end": offset + 4,
        }
        self.assertFalse(
            guard.review_control_number(self.item(text), candidate, POLICY)
        )
