"""Focused collector structure; native save/run/readback are separate."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.prepare_qgip_source_collection import build


class QGIPCollectorTests(unittest.TestCase):
    def test_cli_overflow_and_candidate_serialization_fail_before_output_creation(self):
        from scripts import prepare_qgip_source_collection as module

        root = Path(__file__).resolve().parents[1]
        scratch = root / "private/ops"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            folder = Path(directory)
            reference = folder / "reference.json"
            out = folder / "bad.json"
            args = [
                "prepare_qgip_source_collection",
                "--site",
                "https://example.sharepoint.com/sites/dev",
                "--archive-parent",
                "/Documents/archive",
                "--reference",
                str(reference),
                "--output",
                str(out),
            ]
            valid = json.dumps(self.ref).encode()
            for number in (b"1e999", b"-1e999"):
                raw = valid[:-1] + b',"expansion":' + number + b"}"
                reference.write_bytes(raw)
                with (
                    self.subTest(number=number),
                    patch("sys.argv", args),
                    self.assertRaises(ValueError),
                ):
                    module.main()
                self.assertFalse(out.exists())
                self.assertEqual(reference.read_bytes(), raw)
            reference.write_bytes(valid)
            for bad in ({"nonfinite": float("inf")}, {"unsupported": object()}):
                with (
                    self.subTest(kind=list(bad)),
                    patch("sys.argv", args),
                    patch.object(module, "build", return_value=bad),
                    self.assertRaises((TypeError, ValueError)),
                ):
                    module.main()
                self.assertFalse(out.exists())
                self.assertEqual(reference.read_bytes(), valid)

    def test_absolute_direct_cli_without_site_or_pythonpath_from_outside_repo(self):
        root = Path(__file__).resolve().parents[1]
        scratch = root / "private/ops"
        scratch.mkdir(parents=True, exist_ok=True)
        with (
            tempfile.TemporaryDirectory(dir=scratch) as directory,
            tempfile.TemporaryDirectory() as outside,
        ):
            folder = Path(directory)
            reference = folder / "reference.json"
            reference.write_text(json.dumps(self.ref))
            out = folder / "candidate.json"
            env = dict(os.environ)
            env.pop("PYTHONPATH", None)
            command = [
                sys.executable,
                "-S",
                str(root / "scripts/prepare_qgip_source_collection.py"),
                "--site",
                "https://example.sharepoint.com/sites/dev",
                "--archive-parent",
                "/Documents/archive",
                "--reference",
                str(reference),
                "--output",
                str(out),
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
            self.assertEqual(
                json.loads(out.read_text())["properties"]["state"], "Stopped"
            )

    def test_page_failure_latch_stops_same_offset_reentry_and_completion(self):
        a = self.actions
        loop = a["Two_complete_reads"]["actions"]
        page = loop["Pages"]["actions"]

        def trace(initial):
            states = dict(initial)
            while True:
                pending = {}
                for name, node in page.items():
                    after = node.get("runAfter", {})
                    if name not in states and after and all(k in states for k in after):
                        pending[name] = (
                            "Succeeded"
                            if all(states[k] in allowed for k, allowed in after.items())
                            else "Skipped"
                        )
                if not pending:
                    return states
                states.update(pending)

        for failed, status in [
            ("HTTP_Page", "Failed"),
            ("HTTP_Page", "TimedOut"),
            ("Raw_Page", "Failed"),
            ("Save_Page", "Failed"),
            ("Read_Page", "TimedOut"),
            ("Verify_Page", "Failed"),
            ("Record_Page", "Failed"),
            ("Guard_Page", "Failed"),
            ("Guard_page_coverage", "Failed"),
        ]:
            initial = {"HTTP_Page": "Succeeded", failed: status}
            if failed == "HTTP_Page":
                initial["Guard_Page"] = (
                    "Failed"  # failed status cannot pass the existing HTTP200 guard
                )
            with self.subTest(failed=failed, status=status):
                states = trace(initial)
                self.assertEqual(states["Increment_offset"], "Skipped")
                self.assertEqual(states["Latch_page_failure"], "Succeeded")
                self.assertEqual(
                    page["Latch_page_failure"]["inputs"],
                    {"name": "PageFailed", "value": True},
                )
        success = trace({"HTTP_Page": "Succeeded"})
        self.assertEqual(success["Increment_offset"], "Succeeded")
        self.assertEqual(success["Latch_page_failure"], "Skipped")
        self.assertEqual(
            loop["Pages"]["expression"],
            "@or(variables('PageFailed'),greaterOrEquals(variables('Offset'),variables('Total')))",
        )
        self.assertIn(
            "not(variables('PageFailed'))", loop["Guard_page_entry"]["inputs"]
        )
        self.assertEqual(loop["Pages"]["runAfter"], {"Guard_page_entry": ["Succeeded"]})
        self.assertIn(
            "not(variables('PageFailed'))", loop["Guard_complete_keys"]["inputs"]
        )
        self.assertIn(
            "not(variables('PageFailed'))", a["Guard_stable_metadata"]["inputs"]
        )
        self.assertEqual(
            a["Initialize_PageFailed"]["inputs"]["variables"],
            [{"name": "PageFailed", "type": "boolean", "value": False}],
        )

        def latch_values(value):
            if isinstance(value, dict):
                if (
                    value.get("type") == "SetVariable"
                    and value.get("inputs", {}).get("name") == "PageFailed"
                ):
                    yield value["inputs"]["value"]
                for child in value.values():
                    yield from latch_values(child)
            elif isinstance(value, list):
                for child in value:
                    yield from latch_values(child)

        self.assertEqual(list(latch_values(loop)), [True, True])
        for node in page.values():
            if node.get("type") == "OpenApiConnection":
                self.assertEqual(node["inputs"]["retryPolicy"], {"type": "none"})

    def test_cli_rejects_duplicate_or_nonfinite_saved_reference(self):
        root = Path(__file__).resolve().parents[1]
        scratch = root / "private/ops"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            folder = Path(directory)
            source = folder / "reference.json"
            out = folder / "candidate.json"
            valid = json.dumps(self.ref).encode()
            command = [
                sys.executable,
                "-m",
                "scripts.prepare_qgip_source_collection",
                "--site",
                "https://example.sharepoint.com/sites/dev",
                "--archive-parent",
                "/Documents/archive",
                "--reference",
                str(source),
                "--output",
                str(out),
            ]
            source.write_bytes(valid)
            result = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            saved = out.read_bytes()
            for suffix in (
                b',"source":"Embedded"',
                b',"diagnostic":NaN',
                b',"diagnostic":Infinity',
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

    def setUp(self):
        self.ref = {
            "source": "Embedded",
            "id": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
            "connectionReferenceLogicalName": "example_sharepoint",
            "connectionName": "existing-example",
        }
        self.candidate = build(
            "https://example.sharepoint.com/sites/dev",
            "/Documents/Existing archive",
            self.ref,
        )
        self.actions = self.candidate["properties"]["definition"]["actions"]

    def test_manual_stopped_policy_and_existing_binding(self):
        p = self.candidate["properties"]
        self.assertEqual(p["state"], "Stopped")
        self.assertEqual(p["definition"]["triggers"]["manual"]["kind"], "Button")
        self.assertEqual(
            p["connectionReferences"], {"shared_sharepointonline": self.ref}
        )
        self.assertEqual(
            self.actions["Initialize_Files"]["runAfter"],
            {"Guard_source_policy": ["Succeeded"]},
        )
        self.assertNotIn("Recurrence", json.dumps(p))

    def test_capture_precedes_validation_and_commit_follows_readback(self):
        a = self.actions
        for name in ["Index", "Package", "Resource", "Schema"]:
            for phase in ["before", "after"]:
                k = name + "_" + phase
                self.assertEqual(
                    a["Guard_" + k]["runAfter"], {"Record_" + k: ["Succeeded"]}
                )
                self.assertEqual(
                    a["Record_" + k]["runAfter"], {"Verify_" + k: ["Succeeded"]}
                )
                self.assertEqual(
                    a["Read_" + k]["inputs"]["host"]["operationId"],
                    "GetFileContentByPath",
                )
                self.assertIn("Failed", a["Raw_" + k]["runAfter"]["HTTP_" + k])
        self.assertEqual(
            a["Manifest"]["runAfter"], {"Guard_stable_metadata": ["Succeeded"]}
        )
        self.assertEqual(a["Commit_manifest"]["runAfter"], {"Manifest": ["Succeeded"]})
        self.assertEqual(
            a["Verify_manifest"]["runAfter"], {"Read_manifest": ["Succeeded"]}
        )

    def test_two_bounded_serial_reads_keep_unknown_fields(self):
        two = self.actions["Two_complete_reads"]
        self.assertEqual(two["foreach"], "@createArray(1,2)")
        self.assertEqual(two["runtimeConfiguration"]["concurrency"]["repetitions"], 1)
        pages = two["actions"]["Pages"]
        self.assertEqual(pages["limit"], {"count": 10, "timeout": "PT10M"})
        p = pages["actions"]
        self.assertEqual(p["HTTP_Page"]["runAfter"], {})
        self.assertIn("Guard_Page", p["Parse_page"]["runAfter"])
        self.assertNotIn(
            "additionalProperties", json.dumps(p["Parse_page"]["inputs"]["schema"])
        )
        raw = p["Raw_Page"]["inputs"]["response"]
        self.assertEqual(raw, "@outputs('HTTP_Page')")
        self.assertFalse(self.actions["Manifest"]["inputs"]["candidate_filter_applied"])
        self.assertNotIn("SharePoint_Create_item", json.dumps(self.candidate))
        self.assertNotIn('"type": "Terminate"', json.dumps(self.candidate))

    def test_empty_source_still_requires_two_page_files(self):
        expression = self.actions["Guard_stable_metadata"]["inputs"]
        self.assertIn("max(1,div(add(variables('Total'),99),100))", expression)

    def test_rejects_unqualified_paths_and_invoker_binding(self):
        for site, path in [
            ("http://example.sharepoint.com", "/Documents/archive"),
            ("https://example.sharepoint.com", "/Documents/../archive"),
            ("https://example.sharepoint.com", "/Other/archive"),
        ]:
            with self.assertRaises(ValueError):
                build(site, path, self.ref)
        invalid = copy.deepcopy(self.ref)
        invalid["source"] = "Invoker"
        with self.assertRaises(ValueError):
            build("https://example.sharepoint.com", "/Documents/archive", invalid)

    def test_strict_paths_and_reference_identity_fail_without_mutating_input(self):
        for site in (
            "https://example.sharepoint.com/sites/x'",
            "https://example.sharepoint.com/sites/../dev",
            "https://example.sharepoint.com/sites/%2e%2e/dev",
            "https://example.sharepoint.com:444/sites/dev",
        ):
            with self.subTest(site=site), self.assertRaises(ValueError):
                build(site, "/Documents/archive", self.ref)
        for key, value in [
            ("connectionName", " padded "),
            ("connectionReferenceLogicalName", True),
            ("connectionReferenceLogicalName", " "),
        ]:
            ref = copy.deepcopy(self.ref)
            ref[key] = value
            before = copy.deepcopy(ref)
            with self.subTest(key=key), self.assertRaises(ValueError):
                build(
                    "https://example.sharepoint.com/sites/dev",
                    "/Documents/archive",
                    ref,
                )
            self.assertEqual(ref, before)

    def test_reference_expansions_and_caller_values_are_preserved(self):
        ref = copy.deepcopy(self.ref)
        ref["apiDefinition"] = {"fixture": "preserve"}
        before = copy.deepcopy(ref)
        result = build(
            "https://example.sharepoint.com/sites/dev", "/Documents/archive", ref
        )
        self.assertEqual(
            result["properties"]["connectionReferences"]["shared_sharepointonline"], ref
        )
        result["properties"]["connectionReferences"]["shared_sharepointonline"][
            "apiDefinition"
        ]["fixture"] = "changed"
        self.assertEqual(ref, before)

    def test_cli_create_only_and_invalid_reference_preserve_input_and_output(self):
        root = Path(__file__).resolve().parents[1]
        scratch = root / "private/ops"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            folder = Path(directory)
            reference = folder / "reference.json"
            reference.write_text(json.dumps(self.ref))
            raw = reference.read_bytes()
            out = folder / "candidate.json"
            command = [
                sys.executable,
                "-m",
                "scripts.prepare_qgip_source_collection",
                "--site",
                "https://example.sharepoint.com/sites/dev",
                "--archive-parent",
                "/Documents/archive",
                "--reference",
                str(reference),
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
            self.assertEqual(reference.read_bytes(), raw)
            invalid = copy.deepcopy(self.ref)
            invalid["source"] = "Invoker"
            reference.write_text(json.dumps(invalid))
            command[-1] = str(folder / "failed.json")
            self.assertNotEqual(
                subprocess.run(command, capture_output=True, check=False).returncode, 0
            )
            self.assertFalse(Path(command[-1]).exists())
            self.assertEqual(out.read_bytes(), saved)


if __name__ == "__main__":
    unittest.main()
