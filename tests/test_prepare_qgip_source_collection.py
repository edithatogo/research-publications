"""Focused collector structure; native save/run/readback are separate."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_qgip_source_collection import build


class QGIPCollectorTests(unittest.TestCase):
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
