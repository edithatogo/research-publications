"""Regression tests for the bounded same-GET patch; no native retry claim."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.patch_clinicaltrials_read_retries import (
    PATHS,
    POLICY,
    definition_sha256,
    prepare,
)


class ClinicalTrialsRetryPatchTests(unittest.TestCase):
    def test_overflow_parser_and_candidate_serialization_refuse_partial_output(self):
        from scripts import patch_clinicaltrials_read_retries as module

        for raw in (b'{"value":1e999}', b'{"value":-1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                module.strict_json(raw)
        self.assertEqual(module.strict_json(b'{"value":1.25}')["value"], 1.25)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "source.json"
            source.write_text(json.dumps(self.fixture()))
            before = source.read_bytes()
            out = folder / "bad.json"
            args = [
                "patch_clinicaltrials_read_retries",
                "--source",
                str(source),
                "--expected-definition-sha256",
                definition_sha256(self.fixture()["properties"]["definition"]),
                "--action",
                "detail",
                "--output",
                str(out),
            ]
            for bad in ({"nonfinite": float("-inf")}, {"unsupported": object()}):
                with (
                    self.subTest(kind=list(bad)),
                    patch("sys.argv", args),
                    patch.object(
                        module, "prepare", return_value=(bad, {"status": "fictional"})
                    ),
                    self.assertRaises((TypeError, ValueError)),
                ):
                    module.main()
                self.assertFalse(out.exists())
                self.assertEqual(source.read_bytes(), before)

    def test_cli_rejects_duplicate_or_nonfinite_saved_definition(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "definition.json"
            out = folder / "candidate.json"
            valid = json.dumps(self.fixture()).encode()
            source.write_bytes(valid)
            command = [
                sys.executable,
                "-m",
                "scripts.patch_clinicaltrials_read_retries",
                "--source",
                str(source),
                "--expected-definition-sha256",
                definition_sha256(self.fixture()["properties"]["definition"]),
                "--action",
                "detail",
                "--output",
                str(out),
            ]
            result = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            saved = out.read_bytes()
            for suffix in (
                b',"unused":1,"unused":2',
                b',"unused":NaN',
                b',"unused":-Infinity',
            ):
                raw = valid[:-1] + suffix + b"}"
                source.write_bytes(raw)
                command[-1] = str(folder / "bad.json")
                with self.subTest(suffix=suffix):
                    result = subprocess.run(
                        command, capture_output=True, text=True, check=False
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(Path(command[-1]).exists())
                    self.assertEqual(source.read_bytes(), raw)
                    self.assertEqual(out.read_bytes(), saved)

    def fixture(self):
        # A minimal fictional definition, never a native observer or runtime receipt.
        def read(uri):
            return {
                "type": "Http",
                "inputs": {
                    "uri": uri,
                    "method": "GET",
                    "headers": {"Accept": "application/json"},
                    "retryPolicy": {"type": "none"},
                },
            }

        page = {
            "Discovery_uri": {
                "type": "Compose",
                "inputs": "@concat('https://clinicaltrials.gov/api/v2/studies?format=json&countTotal=true&pageSize=100&query.term=',uriComponent(outputs('Acquisition_scope')?['query_term']),if(empty(variables('DiscoveryToken')),'',concat('&pageToken=',uriComponent(variables('DiscoveryToken')))))",
            },
            "Get_discovery_page": read("@outputs('Discovery_uri')"),
        }
        doc = {
            "properties": {
                "state": "Started",
                "connectionReferences": {
                    "fixture": {"source": "Embedded", "connectionName": "fictional"}
                },
                "definition": {
                    "triggers": {"Recurrence": {"recurrence": {"interval": 1}}},
                    "actions": {
                        "Manifest": {
                            "inputs": {
                                "format": "rims-ctgov-discovery-commit-v1",
                                "source": "clinicaltrials.gov",
                                "discovery_complete_reads": 2,
                            }
                        },
                        "Two_discovery_reads": {
                            "actions": {"Discovery_pages": {"actions": page}}
                        },
                        "For_each_trial": {
                            "actions": {
                                "Get_trial": read(
                                    "@concat('https://clinicaltrials.gov/api/v2/studies/',items('For_each_trial'))"
                                )
                            }
                        },
                        "Preserved_storage": {
                            "type": "OpenApiConnection",
                            "inputs": {
                                "host": {"operationId": "CreateFile"},
                                "retryPolicy": {"type": "none"},
                            },
                        },
                    },
                },
            }
        }
        return doc

    def action(self, document, path):
        actions = document["properties"]["definition"]["actions"]
        for name in path[:-1]:
            actions = actions[name]["actions"]
        return actions[path[-1]]

    def patch(self, document):
        return prepare(
            document,
            expected_definition_sha256=definition_sha256(
                document["properties"]["definition"]
            ),
            selected_paths=PATHS,
        )

    def test_only_read_retry_policies_change_and_input_is_preserved(self):
        old = self.fixture()
        before = copy.deepcopy(old)
        new, receipt = self.patch(old)
        self.assertEqual(old, before)
        self.assertEqual(len(receipt["changed_action_paths"]), 2)
        for path in PATHS:
            self.assertEqual(self.action(new, path)["inputs"]["retryPolicy"], POLICY)
            self.action(new, path)["inputs"]["retryPolicy"] = {"type": "none"}
        self.assertEqual(
            new, old
        )  # Includes trigger, cursor, writes, guards and bindings.
        self.assertFalse(receipt["native_saved"])
        self.assertFalse(receipt["cross_run_resume_proved"])

    def test_repeat_preparation_is_noop(self):
        new, _ = self.patch(self.fixture())
        repeated, receipt = self.patch(new)
        self.assertEqual(new, repeated)
        self.assertEqual(receipt["changed_action_paths"], [])
        self.assertEqual(receipt["status"], "UNCHANGED_LOCAL_ONLY")

    def test_definition_drift_refuses_update(self):
        old = self.fixture()
        fingerprint = definition_sha256(old["properties"]["definition"])
        old["properties"]["definition"]["triggers"]["Recurrence"]["recurrence"][
            "interval"
        ] = 2
        with self.assertRaisesRegex(ValueError, "drift"):
            prepare(old, expected_definition_sha256=fingerprint)

    def test_non_get_cannot_be_retried_by_this_patch(self):
        old = self.fixture()
        self.action(old, PATHS[0])["inputs"]["method"] = "POST"
        with self.assertRaisesRegex(ValueError, "HTTP GET"):
            self.patch(old)

    def test_changed_provider_or_custom_policy_is_not_overwritten(self):
        for mutation in ("provider", "policy"):
            with self.subTest(mutation=mutation):
                old = self.fixture()
                action = self.action(old, PATHS[1])
                if mutation == "provider":
                    action["inputs"]["uri"] = "https://example.invalid/studies/"
                else:
                    action["inputs"]["retryPolicy"] = {
                        "type": "fixed",
                        "count": 7,
                        "interval": "PT1M",
                    }
                with self.assertRaises(ValueError):
                    self.patch(old)

    def test_missing_actions_or_incorrect_collector_are_refused(self):
        for mutation in ("missing", "format", "state"):
            with self.subTest(mutation=mutation):
                old = self.fixture()
                if mutation == "missing":
                    del old["properties"]["definition"]["actions"]["For_each_trial"]
                elif mutation == "format":
                    old["properties"]["definition"]["actions"]["Manifest"]["inputs"][
                        "format"
                    ] = "another-source"
                else:
                    del old["properties"]["state"]
                with self.assertRaises(ValueError):
                    self.patch(old)

    def test_embedded_hostname_and_body_cannot_expand_the_get_allowlist(self):
        for uri in (
            "@concat('https://evil.invalid/?next=https://clinicaltrials.gov/api/v2/studies/',items('For_each_trial'))",
            "@concat('https://clinicaltrials.gov.evil.invalid/api/v2/studies/',items('For_each_trial'))",
        ):
            d = self.fixture()
            self.action(d, PATHS[1])["inputs"]["uri"] = uri
            before = copy.deepcopy(d)
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                self.patch(d)
            self.assertEqual(d, before)
        d = self.fixture()
        self.action(d, PATHS[1])["inputs"]["body"] = {"write": "record"}
        with self.assertRaises(ValueError):
            self.patch(d)

    def test_implicit_or_mutation_path_selection_is_refused(self):
        d = self.fixture()
        fingerprint = definition_sha256(d["properties"]["definition"])
        with self.assertRaises(ValueError):
            prepare(d, expected_definition_sha256=fingerprint)
        with self.assertRaises(ValueError):
            prepare(
                d,
                expected_definition_sha256=fingerprint,
                selected_paths=(("Preserved_storage",),),
            )

    def test_selection_and_discovery_expression_are_exact(self):
        d = self.fixture()
        before = copy.deepcopy(d)
        new, receipt = prepare(
            d,
            expected_definition_sha256=definition_sha256(d["properties"]["definition"]),
            selected_paths=(PATHS[1],),
        )
        self.assertEqual(receipt["changed_action_paths"], [".".join(PATHS[1])])
        self.assertEqual(self.action(new, PATHS[0]), self.action(before, PATHS[0]))
        page = d["properties"]["definition"]["actions"]["Two_discovery_reads"][
            "actions"
        ]["Discovery_pages"]["actions"]
        page["Discovery_uri"]["inputs"] = page["Discovery_uri"]["inputs"].replace(
            "https://clinicaltrials.gov/",
            "https://evil.invalid/?next=https://clinicaltrials.gov/",
        )
        with self.assertRaises(ValueError):
            self.patch(d)

    def test_cli_requires_explicit_read_selection_and_preserves_failed_output(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "definition.json"
            source.write_text(json.dumps(self.fixture()))
            raw = source.read_bytes()
            out = folder / "candidate.json"
            command = [
                sys.executable,
                "-m",
                "scripts.patch_clinicaltrials_read_retries",
                "--source",
                str(source),
                "--expected-definition-sha256",
                definition_sha256(self.fixture()["properties"]["definition"]),
                "--action",
                "detail",
                "--output",
                str(out),
            ]
            result = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            saved = out.read_bytes()
            self.assertNotEqual(
                subprocess.run(command, capture_output=True, check=False).returncode, 0
            )
            self.assertEqual(out.read_bytes(), saved)
            self.assertEqual(source.read_bytes(), raw)
            command[command.index("--expected-definition-sha256") + 1] = "0" * 64
            command[-1] = str(folder / "bad.json")
            self.assertNotEqual(
                subprocess.run(command, capture_output=True, check=False).returncode, 0
            )
            self.assertFalse(Path(command[-1]).exists())
            self.assertEqual(out.read_bytes(), saved)
