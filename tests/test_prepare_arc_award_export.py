"""Changed native ARC retained-source export behaviour; runtime proof separate."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_arc_award_export import FIELDS, build


class ArcAwardExportTests(unittest.TestCase):
    def test_manifest_fields_independent_and_failure_guards_preserved(self):
        expected = list(FIELDS)
        self.a["Manifest"]["inputs"]["fields"].append("not-a-field")
        self.assertEqual(FIELDS, expected)
        self.assertIn(
            "not(variables('PageFailed'))", self.a["Guard_manifest_coverage"]["inputs"]
        )
        self.assertIn(
            "variables('PageFailed')",
            self.a["Two_complete_reads"]["actions"]["Read_pages"]["expression"],
        )
        self.assertEqual(
            self.pages["Latch_page_failure"]["runAfter"],
            {"Increment_page": ["Failed", "TimedOut", "Skipped"]},
        )

    def test_direct_cli_strict_inputs_no_native_entry_or_overwrite(self):
        root = Path(__file__).resolve().parents[1]
        scratch = root / "private/ops"
        scratch.mkdir(parents=True, exist_ok=True)
        with (
            tempfile.TemporaryDirectory(dir=scratch) as directory,
            tempfile.TemporaryDirectory() as outside,
        ):
            folder = Path(directory)
            reference = folder / "ref.json"
            reference.write_text(json.dumps(self.ref))
            out = folder / "candidate.json"
            env = dict(os.environ)
            env.pop("PYTHONPATH", None)
            cmd = [
                sys.executable,
                "-S",
                str(root / "scripts/prepare_arc_award_export.py"),
                "--site",
                "https://example.sharepoint.com/sites/dev",
                "--archive-parent",
                "/Documents/archive",
                "--reference",
                str(reference),
                "--output",
                str(out),
            ]
            good = subprocess.run(
                cmd, cwd=outside, env=env, capture_output=True, text=True, check=False
            )
            self.assertEqual(good.returncode, 0, good.stderr)
            saved = out.read_bytes()
            reference.write_text(json.dumps(self.ref)[:-1] + ',"expanded":NaN}')
            cmd[-1] = str(folder / "bad.json")
            self.assertNotEqual(
                subprocess.run(
                    cmd, cwd=outside, env=env, capture_output=True, check=False
                ).returncode,
                0,
            )
            self.assertFalse(Path(cmd[-1]).exists())
            self.assertEqual(out.read_bytes(), saved)

    def setUp(self):
        self.ref = {
            "source": "Embedded",
            "id": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
            "connectionName": "existing-example",
            "connectionReferenceLogicalName": "existing_reference",
        }
        self.p = build(
            "https://example.sharepoint.com/sites/dev",
            "/Documents/Existing archive",
            self.ref,
        )["properties"]
        self.a = self.p["definition"]["actions"]
        self.pages = self.a["Two_complete_reads"]["actions"]["Read_pages"]["actions"]
        self.out = self.pages["Compare_passes"]["actions"]

    def test_manual_stopped_no_source_acquisition_or_registry(self):
        self.assertEqual(self.p["state"], "Stopped")
        self.assertEqual(
            self.p["connectionReferences"]["shared_sharepointonline"], self.ref
        )
        text = json.dumps(self.p)
        self.assertNotIn('"type": "Http"', text)
        self.assertNotIn("SharePoint_Create_item", text)
        self.assertIn(
            "SourceRun",
            self.p["definition"]["triggers"]["manual"]["inputs"]["schema"]["required"],
        )
        self.assertIn("triggerBody()", self.a["Run_folder"]["inputs"])
        self.assertEqual(
            self.a["Create_exclusive_folder"]["inputs"]["host"]["operationId"],
            "GetFileContentByPath",
        )

    def test_source_policy_manifest_paging_duplicate_and_replay_guards_preserved(self):
        self.assertIn("context_only", self.a["Guard_source_policy"]["inputs"])
        self.assertIn("..", self.a["Guard_source_run"]["inputs"])
        self.assertIn("source_total", self.pages["Guard_exact_page"]["inputs"])
        self.assertIn("Guard_no_duplicate_keys", self.pages)
        self.assertIn("Guard_full_page_replay", self.out)
        self.assertIn("['data'],'id')", self.out["Guard_full_page_replay"]["inputs"])
        self.assertIn("ticks(", self.pages["Verify_Page"]["inputs"])
        self.assertIn(
            "body('Source_manifest')?['files']",
            self.a["Guard_manifest_coverage"]["inputs"],
        )

    def test_all_award_fields_bounded_page_outputs_exact_readback(self):
        self.assertEqual(list(self.out["Award_page"]["inputs"]["select"]), FIELDS)
        self.assertEqual(len(FIELDS), 12)
        projection = self.out["Award_page"]["inputs"]["select"]
        self.assertEqual(
            projection["RetrievedUTC"],
            "@string(body('Source_manifest')?['committed_utc'])",
        )
        self.assertEqual(projection["EvidenceHash"], "")
        self.assertIn("string(", projection["Amount"])
        for kind in ("JSON", "CSV"):
            self.assertEqual(
                self.out["Read_" + kind]["runAfter"], {"Save_" + kind: ["Succeeded"]}
            )
            self.assertEqual(
                self.out["Record_" + kind]["runAfter"],
                {"Verify_" + kind: ["Succeeded"]},
            )
            self.assertIn(
                "awards-page-", self.out["Save_" + kind]["inputs"]["parameters"]["name"]
            )
        self.assertIn("Invalid_award_links", self.out)
        self.assertNotIn("Initialize_Records", self.a)

    def test_final_manifest_and_source_manifest_recheck(self):
        self.assertEqual(
            self.a["Manifest"]["runAfter"], {"Guard_manifest_unchanged": ["Succeeded"]}
        )
        self.assertEqual(
            self.a["Commit_manifest"]["runAfter"], {"Manifest": ["Succeeded"]}
        )
        manifest = self.a["Manifest"]["inputs"]
        self.assertFalse(manifest["canonical_opportunity_admission"])
        self.assertFalse(manifest["lifecycle_semantics_proven"])
        self.assertEqual(manifest["record_kind"], "awards_only")
        self.assertIn("source_manifest_base64", manifest)
        self.assertIn(
            "Output_folder",
            self.a["Commit_manifest"]["inputs"]["parameters"]["folderPath"],
        )


if __name__ == "__main__":
    unittest.main()
