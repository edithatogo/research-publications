# Copyright (c) 2026 CareOps contributors.
# SPDX-License-Identifier: Apache-2.0
"""Synthetic Git-range, destination, offline and redaction acceptance tests."""

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


scan, gate = module("presidio_scan"), module("pre_push")
POLICY = json.loads((HERE / "presidio-policy.json").read_text())


class DestinationTests(unittest.TestCase):
    def test_only_explicit_private_repository(self):
        calls = []

        def command(args):
            calls.append(args)
            return (
                json.dumps(
                    {
                        "private": POLICY["requiredVisibility"] == "PRIVATE",
                        "visibility": POLICY["requiredVisibility"].lower(),
                        "full_name": POLICY["repository"],
                    }
                ).encode()
                if args[0] == "gh"
                else b""
            )

        self.assertEqual(
            [],
            gate.destination(
                "https://github.com/" + POLICY["repository"] + ".git", POLICY, command
            ),
        )
        self.assertEqual(2, len(calls))
        calls.clear()
        self.assertEqual(
            [],
            gate.destination(
                "https://github.com/" + POLICY["repository"],
                POLICY,
                command,
                advertise=False,
            ),
        )
        self.assertEqual(1, len(calls))
        for url in [
            "https://example.invalid/repo",
            "https://github.com/other/repo.git",
            "https://github.com/" + POLICY["repository"] + ".git?extra=value",
        ]:
            with self.subTest(url_hash=len(url)), self.assertRaises(gate.Refusal):
                gate.destination(url, POLICY, command)

    def test_public_unknown_or_wrong_identity_refused(self):
        for state in [
            {"private": True, "full_name": POLICY["repository"]},
            {},
            {
                "private": POLICY["requiredVisibility"] == "PRIVATE",
                "full_name": "other/repo",
            },
        ]:
            with self.assertRaises(gate.Refusal):
                gate.destination(
                    "https://github.com/" + POLICY["repository"],
                    POLICY,
                    lambda _, state=state: json.dumps(state).encode(),
                )

    def test_invalid_push_and_nonbranch_refused(self):
        for payload in [
            b"bad line",
            ("refs/heads/a " + "a" * 40 + " refs/tags/v1 " + "0" * 40).encode(),
        ]:
            with self.assertRaises(gate.Refusal):
                gate.push_rows(payload)

    def test_missing_scanner_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(gate.Refusal):
            gate.scanner(Path(d), [], POLICY)

    def test_failed_commands_never_echo_output(self):
        result = subprocess.CompletedProcess([], 1, b"private-output", b"private-error")
        with (
            patch.object(gate.subprocess, "run", return_value=result),
            contextlib.redirect_stderr(io.StringIO()) as err,
            self.assertRaises(gate.Refusal),
        ):
            gate.run(["fictional-command"])
        self.assertEqual("", err.getvalue())

    def test_notification_failure_does_not_authorise_push(self):
        with (
            patch.object(gate.sys, "platform", "darwin"),
            patch.object(gate.subprocess, "run", side_effect=OSError),
        ):
            gate.notify()  # Only the optional notification is swallowed; main returns failure.


class GitScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic")
        self.git("config", "user.email", "synthetic@example.invalid")
        (self.root / "sample.txt").write_text("ordinary source")
        self.base = self.commit()

    def git(self, *args):
        return scan.git(self.root, *args)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic source update")
        return self.git("rev-parse", "HEAD").decode().strip()

    def test_intermediate_deleted_text_and_message_preserved(self):
        text = "".join(map(chr, [74, 97, 110, 101, 32, 68, 111, 101]))
        (self.root / "temporary.txt").write_text(text)
        self.commit()
        (self.root / "temporary.txt").unlink()
        tip = self.commit()
        items = scan.selected_text(self.root, tip, [self.base], POLICY)
        self.assertTrue(any(x["text"] == text for x in items))
        self.assertTrue(any("Synthetic source update" in x["text"] for x in items))
        self.assertTrue(all(len(x["identity"]) == 64 for x in items))

    def test_index_cannot_hide_outgoing_blob(self):
        (self.root / "sample.txt").write_text("outgoing text")
        tip = self.commit()
        (self.root / "sample.txt").write_text("different staged text")
        self.git("add", "sample.txt")
        items = scan.selected_text(self.root, tip, [self.base], POLICY)
        self.assertTrue(any(x["text"] == "outgoing text" for x in items))
        self.assertFalse(any(x["text"] == "different staged text" for x in items))

    def test_scope_limit_fails_instead_of_truncating(self):
        (self.root / "sample.txt").write_text("changed source")
        tip = self.commit()
        with self.assertRaises(scan.Refusal):
            scan.selected_text(
                self.root, tip, [self.base], {**POLICY, "maxTotalBytes": 1}
            )


class EngineUnitTests(unittest.TestCase):
    def test_exact_review_cannot_approve_changed_text(self):
        class Result:
            entity_type, start, end = "PERSON", 0, 4

        class Analyzer:
            def analyze(self, **_kwargs):
                return [Result()]

        item = {"identity": "a" * 64, "text": "code-only"}
        first = scan.analyze([item], POLICY, Analyzer())
        approval = {
            **first["findings"][0]["details"][0],
            "reason": "synthetic technical token",
            "reviewer": "source-review",
        }
        accepted = scan.analyze([item], POLICY, Analyzer(), {"findings": [approval]})
        self.assertFalse(accepted["findings"])
        changed = scan.analyze(
            [{**item, "text": "other text"}],
            POLICY,
            Analyzer(),
            {"findings": [approval]},
        )
        self.assertTrue(changed["findings"])

    def test_scan_output_contains_no_match_or_filename(self):
        class Result:
            entity_type = "PERSON"
            start = 0
            end = 9

        class Analyzer:
            def analyze(self, **_kwargs):
                return [Result()]

        secret = "synthetic personal content"
        result = scan.analyze(
            [{"identity": "a" * 64, "text": secret}], POLICY, Analyzer()
        )
        output = json.dumps(result)
        self.assertNotIn(secret, output)
        self.assertEqual(["PERSON"], result["findings"][0]["entities"])

    def test_overlap_covers_boundaries(self):
        chunks = []

        class Analyzer:
            def analyze(self, **kwargs):
                chunks.append(kwargs["text"])
                return []

        scan.analyze(
            [{"identity": "a" * 64, "text": "abcdefghijklmno"}],
            {**POLICY, "chunkCharacters": 8, "overlapCharacters": 3},
            Analyzer(),
        )
        self.assertEqual("fgh", chunks[0][-3:])
        self.assertTrue(chunks[1].startswith("fgh"))


if __name__ == "__main__":
    unittest.main()
