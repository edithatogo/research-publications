"""Focused candidate-consumer graph boundaries; native execution remains separate."""

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote

from scripts.prepare_qgip_candidate_export import build


def evaluate_csv_cell(expression, cell):
    """Restricted generated-expression oracle; not a native WDL engine."""
    expression = (
        re.sub(r"item\(\)\?\['[^']+'\]", "cell", expression.removeprefix("@"))
        .replace("if(", "choose(")
        .replace("or(", "any_of(")
    )

    def string(value):
        if value is None:
            return ""
        if isinstance(value, bool):
            return str(value).lower()
        return str(value)

    functions = {
        "choose": lambda condition, yes, no: yes if condition else no,
        "any_of": lambda *values: any(values),
        "startsWith": lambda value, prefix: value.startswith(prefix),
        "trim": lambda value: value.strip(),
        "string": string,
        "contains": lambda value, part: part in value,
        "concat": lambda *values: "".join(values),
        "decodeUriComponent": unquote,
    }

    def run(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name) and node.id == "cell":
            return cell
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in functions
            and not node.keywords
        ):
            return functions[node.func.id](*(run(arg) for arg in node.args))
        raise AssertionError("Unexpected generated CSV expression")

    return run(ast.parse(expression, mode="eval").body)


class CandidateExportTests(unittest.TestCase):
    def test_csv_only_projection_transforms_actual_cells_and_preserves_json(self):
        from scripts.prepare_arc_award_export import build as awards

        arc = awards(
            "https://example.sharepoint.com/sites/dev", "/Documents/archive", self.ref
        )["properties"]["definition"]["actions"]["Two_complete_reads"]["actions"][
            "Read_pages"
        ]["actions"]["Compare_passes"]["actions"]
        for actions, prefix, source, title in (
            (self.a, "Candidate", "Candidate_export", "ProgramTitleSource"),
            (arc, "Award", "Award_page", "Title"),
        ):
            with self.subTest(export=prefix):
                original = json.dumps(actions[source], sort_keys=True)
                display = actions[prefix + "_CSV_display"]
                projection = display["inputs"]["select"]
                self.assertEqual(display["runAfter"], {source: ["Succeeded"]})
                self.assertEqual(display["inputs"]["from"], "@body('" + source + "')")
                self.assertEqual(
                    actions[prefix + "_CSV"]["runAfter"],
                    {prefix + "_CSV_display": ["Succeeded"]},
                )
                self.assertEqual(
                    actions[prefix + "_CSV"]["inputs"]["from"],
                    "@body('" + prefix + "_CSV_display')",
                )
                self.assertEqual(
                    list(projection), list(actions[source]["inputs"]["select"])
                )
                for value in (
                    "=1+1",
                    "+SUM(A1)",
                    "-1",
                    "@SUM(A1)",
                    "  =1+1",
                    "\ttext",
                    " \rtext",
                    "\n=1",
                    "\u00a0@SUM(A1)",
                    "ordinary\ttext",
                ):
                    self.assertEqual(
                        evaluate_csv_cell(projection[title], value), "'" + value
                    )
                for value in ("ordinary", "001.250", "", None, 0):
                    self.assertEqual(evaluate_csv_cell(projection[title], value), value)
                self.assertEqual(json.dumps(actions[source], sort_keys=True), original)
                json_body = actions["Save_JSON"]["inputs"]["parameters"]["body"]
                self.assertIn("string(body('" + source + "'))", json_body)
                self.assertNotIn("CSV_display", json_body)
                if prefix == "Candidate":
                    self.assertIs(
                        actions[source]["inputs"]["select"]["CanonicalAdmission"], False
                    )
                    self.assertIs(
                        evaluate_csv_cell(projection["CanonicalAdmission"], False),
                        False,
                    )
                else:
                    self.assertEqual(
                        actions[source]["inputs"]["select"]["EvidenceHash"], ""
                    )

    def test_source_run_and_failure_latch_are_not_weakened_by_conversion(self):
        self.assertIn(
            "uriComponent(triggerBody()?['SourceRun'])",
            self.a["Guard_source_run"]["inputs"],
        )
        self.assertIn(
            "not(variables('PageFailed'))", self.a["Guard_manifest_files"]["inputs"]
        )
        pages = self.a["Two_complete_reads"]["actions"]["Pages"]
        self.assertIn("variables('PageFailed')", pages["expression"])
        self.assertIn("Latch_page_failure", pages["actions"])

    def test_direct_cli_strict_reference_and_private_exclusive_output(self):
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
                str(root / "scripts/prepare_qgip_candidate_export.py"),
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
            self.assertNotEqual(
                subprocess.run(
                    cmd, cwd=outside, env=env, capture_output=True, check=False
                ).returncode,
                0,
            )
            self.assertEqual(out.read_bytes(), saved)
            reference.write_text(json.dumps(self.ref)[:-1] + ',"expanded":-1e999}')
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

    def actions(self, a=None):
        for k, v in (self.a if a is None else a).items():
            yield k, v
            if "actions" in v:
                yield from self.actions(v["actions"])
            if "else" in v:
                yield from self.actions(v["else"]["actions"])

    def test_stopped_manual_existing_binding_no_acquisition_or_register_writes(self):
        self.assertEqual(self.p["state"], "Stopped")
        trigger = self.p["definition"]["triggers"]["manual"]
        self.assertEqual(trigger["kind"], "Button")
        self.assertEqual(
            set(trigger["inputs"]["schema"]["required"]), {"SourceRun", "CatalogueJson"}
        )
        self.assertEqual(
            self.p["connectionReferences"], {"shared_sharepointonline": self.ref}
        )
        for k, v in self.actions():
            self.assertNotEqual(v["type"], "Http", k)
            if v["type"] == "OpenApiConnection":
                self.assertIn(
                    v["inputs"]["host"]["operationId"],
                    ["GetFileContentByPath", "CreateFile", "HttpRequest"],
                )
                if v["inputs"]["host"]["operationId"] == "CreateFile":
                    self.assertEqual(
                        v["inputs"]["parameters"]["folderPath"],
                        "@outputs('Output_folder')",
                    )

    def test_each_retained_response_is_bound_before_validation(self):
        for k, v in self.actions():
            if k.startswith("HTTP_"):
                tag = k[5:]
                self.assertEqual(v["type"], "Compose")
                self.assertEqual(v["runAfter"], {"Bind_" + tag: ["Succeeded"]})
        pages = self.a["Two_complete_reads"]["actions"]["Pages"]["actions"]
        self.assertEqual(pages["Load_Page"]["runAfter"], {})
        self.assertIn("variables('Offset')", pages["Bind_Page"]["inputs"])
        self.assertNotIn('"offset":"@variables', pages["Bind_Page"]["inputs"])
        self.assertIn("['body']", pages["Parse_page"]["inputs"]["content"])
        self.assertEqual(
            self.a["Two_complete_reads"]["runtimeConfiguration"]["concurrency"][
                "repetitions"
            ],
            1,
        )

    def test_source_commit_and_manifest_unchanged_before_candidate_selection(self):
        self.assertIn(
            "sort(body('Source_manifest')?['files'],'name')",
            self.a["Guard_manifest_files"]["inputs"],
        )
        self.assertEqual(
            self.a["Parse_classifiers"]["runAfter"],
            {"Guard_manifest_unchanged": ["Succeeded"]},
        )
        self.assertIn("['$content']", self.a["Guard_manifest_unchanged"]["inputs"])
        where = self.a["Candidate_rows"]["inputs"]["where"]
        self.assertIn("'open'", where)
        for i in range(1, 4):
            self.assertIn("Assistance type" + str(i), where)
        self.assertNotIn("contains(", where)

    def test_outputs_verified_before_manifest_and_source_uncertainty_preserved(self):
        a = self.a
        self.assertEqual(
            a["Candidate_manifest"]["runAfter"], {"Verify_CSV": ["Succeeded"]}
        )
        self.assertEqual(
            a["Commit_candidate_manifest"]["runAfter"],
            {"Candidate_manifest": ["Succeeded"]},
        )
        self.assertEqual(
            a["Verify_candidate_manifest"]["runAfter"],
            {"Read_candidate_manifest": ["Succeeded"]},
        )
        fields = a["Candidate_export"]["inputs"]["select"]
        self.assertFalse(fields["CanonicalAdmission"])
        self.assertEqual(fields["IdentityStatus"], "CandidateUnproven")
        self.assertEqual(fields["Status"], "Needs Review")
        self.assertIn("SourceRun", fields)
        self.assertIn("qgip-candidates-", a["Output_folder"]["inputs"])
        self.assertNotIn('"type": "Terminate"', json.dumps(self.p))


if __name__ == "__main__":
    unittest.main()
