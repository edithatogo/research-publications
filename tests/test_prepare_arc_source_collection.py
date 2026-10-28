"""Focused native ARC graph guards; native save/run proof is separate."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.grants_arc_api import MAX_TOTAL_AWARDS
from scripts.patch_clinicaltrials_read_retries import definition_sha256
from scripts.prepare_arc_source_collection import (
    MAX_PAGES,
    PAGE_SIZE,
    build,
    with_configured_catalogue,
    with_weekly_updates,
)


class ArcCollectorTests(unittest.TestCase):
    def test_serialization_failure_never_creates_partial_output(self):
        import importlib
        from unittest.mock import patch

        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / "private/ops") as directory:
            folder = Path(directory)
            reference = folder / "ref.json"
            reference.write_text(json.dumps(self.ref))
            for name in (
                "prepare_arc_source_collection",
                "prepare_arc_award_export",
                "prepare_qgip_candidate_export",
                "read_arc_committed_source",
            ):
                module = importlib.import_module("scripts." + name)
                output = folder / (name + ".json")
                arguments = ["tool", "--output", str(output)]
                if name == "read_arc_committed_source":
                    arguments += ["--folder", str(folder)]
                    producer = "read_commit"
                else:
                    arguments += [
                        "--site",
                        "https://example.sharepoint.com/sites/dev",
                        "--archive-parent",
                        "/Documents/archive",
                        "--reference",
                        str(reference),
                    ]
                    producer = "build"
                with (
                    self.subTest(module=name),
                    patch.object(sys, "argv", arguments),
                    patch.object(
                        module, producer, return_value={"invalid": float("inf")}
                    ),
                    self.assertRaises(ValueError),
                ):
                    module.main()
                self.assertFalse(output.exists())

    def test_all_builder_dependency_graphs_are_closed_serial_and_retry_free(self):
        from scripts.prepare_arc_award_export import build as awards
        from scripts.prepare_qgip_candidate_export import build as candidates

        def check(actions):
            visited = set()
            active = set()

            def visit(name):
                self.assertIn(name, actions)
                self.assertNotIn(name, active, "cyclic runAfter")
                if name in visited:
                    return
                active.add(name)
                for parent in actions[name].get("runAfter", {}):
                    visit(parent)
                active.remove(name)
                visited.add(name)

            for name, node in actions.items():
                visit(name)
                if node["type"] in ("Http", "OpenApiConnection"):
                    self.assertEqual(node["inputs"]["retryPolicy"], {"type": "none"})
                if "actions" in node:
                    check(node["actions"])
                if "else" in node:
                    check(node["else"]["actions"])
            return visited

        for constructor in (build, awards, candidates):
            with self.subTest(constructor=constructor.__module__):
                actions = constructor(
                    "https://example.sharepoint.com/sites/dev",
                    "/Documents/archive",
                    self.ref,
                )["properties"]["definition"]["actions"]
                check(actions)
                ancestors = set()

                def collect(name, actions=actions, ancestors=ancestors):
                    for parent in actions[name].get("runAfter", {}):
                        if parent not in ancestors:
                            ancestors.add(parent)
                            collect(parent)

                collect("Run_folder")
                self.assertIn("Initialize_PageFailed", ancestors)

    def test_page_dependency_failures_latch_before_increment_can_repeat(self):
        from scripts.prepare_arc_award_export import build as awards

        for constructor in (build, awards):
            actions = constructor(
                "https://example.sharepoint.com/sites/dev",
                "/Documents/archive",
                self.ref,
            )["properties"]["definition"]["actions"]["Two_complete_reads"]["actions"][
                "Read_pages"
            ]["actions"]
            failures = (
                "HTTP_Page",
                "Read_Page",
                "Verify_Page",
                "Guard_exact_page",
                "Compare_passes",
            )
            if constructor is build:
                failures += ("Save_Page",)
            for failed in failures:
                with self.subTest(constructor=constructor.__module__, failed=failed):
                    # Model only runAfter status propagation, not native WDL execution.
                    statuses = {}
                    pending = set(actions)
                    while pending:
                        ready = [
                            key
                            for key in pending
                            if set(actions[key].get("runAfter", {})) <= statuses.keys()
                        ]
                        self.assertTrue(ready, "dependency deadlock")
                        for key in ready:
                            node = actions[key]
                            eligible = all(
                                statuses[parent] in allowed
                                for parent, allowed in node.get("runAfter", {}).items()
                            )
                            statuses[key] = (
                                ("Failed" if key == failed else "Succeeded")
                                if eligible
                                else "Skipped"
                            )
                            pending.remove(key)
                    if failed == "HTTP_Page" and constructor is build:
                        # Raw failure capture deliberately runs; its HTTP guard
                        # predicate is outside this runAfter-only model.
                        self.assertEqual(statuses["Latch_http_failure"], "Succeeded")
                    else:
                        self.assertEqual(statuses["Increment_page"], "Skipped")
                        self.assertEqual(statuses["Latch_page_failure"], "Succeeded")
                    self.assertEqual(
                        actions["Latch_page_failure"]["inputs"],
                        {"name": "PageFailed", "value": True},
                    )

    def test_page_failure_latch_and_completion_guards_do_not_reset(self):
        self.assertIn("variables('PageFailed')", self.loop["Read_pages"]["expression"])
        self.assertEqual(
            self.pages["Latch_page_failure"]["runAfter"],
            {"Increment_page": ["Failed", "TimedOut", "Skipped"]},
        )
        self.assertEqual(
            self.pages["Latch_page_failure"]["inputs"],
            {"name": "PageFailed", "value": True},
        )
        self.assertEqual(
            self.loop["Read_pages"]["runAfter"], {"Guard_page_entry": ["Succeeded"]}
        )
        for node in (
            self.loop["Guard_complete_set"],
            self.a["Guard_manifest_coverage"],
        ):
            self.assertIn("not(variables('PageFailed'))", node["inputs"])
        self.assertNotIn("Reset_PageFailed", self.loop)

    def test_manual_scope_strict_catalogue_and_reference_preservation(self):
        record = {
            "source_id": "arc-awards-api",
            "enabled": True,
            "record_kind": "awarded_grant_context",
            "api_url": "https://dataportal.arc.gov.au/NCGP/API/grants",
            "reconciliation": {"admission": "context_only"},
        }
        d = {"properties": copy.deepcopy(self.p)}
        before = copy.deepcopy(d)
        with self.assertRaisesRegex(ValueError, "manual"):
            with_weekly_updates(d, [record])
        for url in (
            "https://user:password@dataportal.arc.gov.au/NCGP/API/grants",
            "https://dataportal.arc.gov.au:444/NCGP/API/grants",
            "https://dataportal.arc.gov.au/NCGP/API/grants#fragment",
            "https://dataportal.arc.gov.au/NCGP/API/grants?page%5Bsize%5D=1",
        ):
            bad = copy.deepcopy(record)
            bad["api_url"] = url
            with self.subTest(url=url), self.assertRaises(ValueError):
                with_configured_catalogue(
                    d,
                    [bad],
                    expected_definition_sha256=definition_sha256(
                        d["properties"]["definition"]
                    ),
                )
        self.assertEqual(d, before)

    def test_direct_cli_strict_json_and_exclusive_output(self):
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
                str(root / "scripts/prepare_arc_source_collection.py"),
                "--site",
                "https://example.sharepoint.com/sites/dev",
                "--archive-parent",
                "/Documents/Archive",
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
            self.assertNotEqual(
                subprocess.run(
                    cmd, cwd=outside, env=env, capture_output=True, check=False
                ).returncode,
                0,
            )
            self.assertEqual(out.read_bytes(), saved)
            for suffix in (',"source":"Embedded"', ',"extra":1e999'):
                reference.write_text(json.dumps(self.ref)[:-1] + suffix + "}")
                cmd[-1] = str(folder / "bad.json")
                self.assertNotEqual(
                    subprocess.run(
                        cmd, cwd=outside, env=env, capture_output=True, check=False
                    ).returncode,
                    0,
                )
                self.assertFalse(Path(cmd[-1]).exists())

    def setUp(self):
        self.ref = {
            "source": "Embedded",
            "id": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
            "connectionName": "existing-example",
            "connectionReferenceLogicalName": "example_reference",
        }
        self.p = build(
            "https://example.sharepoint.com/sites/dev",
            "/Documents/Existing archive",
            self.ref,
        )["properties"]
        self.a = self.p["definition"]["actions"]
        self.loop = self.a["Two_complete_reads"]["actions"]
        self.pages = self.loop["Read_pages"]["actions"]

    def test_stopped_manual_existing_reference_source_policy_before_effects(self):
        self.assertEqual(self.p["state"], "Stopped")
        self.assertEqual(
            self.p["connectionReferences"], {"shared_sharepointonline": self.ref}
        )
        self.assertEqual(self.p["definition"]["triggers"]["manual"]["kind"], "Button")
        self.assertIn(
            "'arc-awards-api'", self.a["Selected_source_policy"]["inputs"]["where"]
        )
        self.assertIn("'context_only'", self.a["Guard_source_policy"]["inputs"])
        self.assertEqual(
            self.a["Initialize_Files"]["runAfter"],
            {"Guard_source_policy": ["Succeeded"]},
        )
        self.assertIn("arc-source-", self.a["Run_folder"]["inputs"])

    def test_all_response_values_stored_and_read_back_before_validation(self):
        a = self.pages
        self.assertEqual(a["Raw_Page"]["inputs"]["response"], "@outputs('HTTP_Page')")
        self.assertEqual(
            a["Raw_Page"]["runAfter"]["HTTP_Page"], ["Succeeded", "Failed", "TimedOut"]
        )
        self.assertEqual(a["Guard_HTTP"]["runAfter"], {"Record_Page": ["Succeeded"]})
        self.assertEqual(a["Record_Page"]["runAfter"], {"Verify_Page": ["Succeeded"]})
        self.assertEqual(a["Verify_Page"]["runAfter"], {"Read_Page": ["Succeeded"]})
        self.assertNotIn("additionalProperties", json.dumps(a["Parse_Page"]))
        self.assertNotIn("Select", a["Raw_Page"]["type"])

    def test_bounded_page_replay_and_global_id_coverage(self):
        self.assertEqual(PAGE_SIZE, 500)
        self.assertEqual(MAX_PAGES * PAGE_SIZE, MAX_TOTAL_AWARDS)
        self.assertEqual(
            self.loop["Read_pages"]["limit"], {"count": MAX_PAGES, "timeout": "PT1H"}
        )
        self.assertEqual(self.a["Two_complete_reads"]["foreach"], "@createArray(1,2)")
        self.assertEqual(
            self.a["Two_complete_reads"]["runtimeConfiguration"]["concurrency"][
                "repetitions"
            ],
            1,
        )
        self.assertIn("max(1,div(", self.pages["Guard_exact_page"]["inputs"])
        self.assertIn("Guard_no_duplicate_keys", self.pages)
        replay = self.pages["Compare_passes"]["actions"]["Guard_full_page_replay"][
            "inputs"
        ]
        self.assertIn("['data'],'id')", replay)
        self.assertNotIn("Title", replay)
        self.assertIn(
            "variables('Rows'),variables('Total')",
            self.loop["Guard_complete_set"]["inputs"],
        )
        self.assertNotIn("Initialize_Records", self.a)
        self.assertIn(
            "Guard_equal_keys", self.loop["Compare_key_sets"]["else"]["actions"]
        )

    def test_manifest_last_no_opportunity_or_delivery(self):
        a = self.a
        self.assertEqual(
            a["Manifest"]["runAfter"], {"Guard_manifest_coverage": ["Succeeded"]}
        )
        self.assertEqual(a["Commit_manifest"]["runAfter"], {"Manifest": ["Succeeded"]})
        self.assertEqual(
            a["Verify_manifest"]["runAfter"], {"Read_manifest": ["Succeeded"]}
        )
        m = a["Manifest"]["inputs"]
        self.assertFalse(m["canonical_opportunity_admission"])
        self.assertFalse(m["candidate_filter_applied"])
        self.assertEqual(m["record_kind"], "awards_only")
        self.assertEqual(m["complete_reads"], 2)
        self.assertEqual(m["schedule"], "manual_only")
        self.assertNotIn('"type": "Terminate"', json.dumps(self.p))
        self.assertNotIn("SharePoint_Create_item", json.dumps(self.p))
        self.assertIn("page membership drift rejects commit", m["replay_scope"])

    def test_configured_operator_preserves_complete_capture_and_source_policy(self):
        record = {
            "source_id": "arc-awards-api",
            "enabled": True,
            "record_kind": "awarded_grant_context",
            "api_url": "https://dataportal.arc.gov.au/NCGP/API/grants",
            "reconciliation": {"admission": "context_only"},
        }
        document = {"properties": copy.deepcopy(self.p)}
        before = copy.deepcopy(document)
        pin = definition_sha256(document["properties"]["definition"])
        configured = with_configured_catalogue(
            document, [record], expected_definition_sha256=pin
        )
        self.assertEqual(document, before)
        a = configured["properties"]["definition"]["actions"]
        self.assertEqual(a["Parse_source_catalogue"]["inputs"]["content"], [record])
        self.assertEqual(a["Two_complete_reads"], self.a["Two_complete_reads"])
        self.assertNotIn(
            "CatalogueJson",
            json.dumps(configured["properties"]["definition"]["triggers"]),
        )
        with self.assertRaisesRegex(ValueError, "manual"):
            with_weekly_updates(document, [record])
        with self.assertRaises(ValueError):
            with_configured_catalogue(
                document, [record], expected_definition_sha256="wrong"
            )
        record["enabled"] = False
        with self.assertRaises(ValueError):
            with_configured_catalogue(
                document, [record], expected_definition_sha256=pin
            )


if __name__ == "__main__":
    unittest.main()
