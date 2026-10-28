import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_raw_publication_doi_inputs import with_raw_producer_dois


def checkpoint(name, *, values=None):
    pubmed = name == "pubmed"
    prefix = "pubmed-acquisition-" if pubmed else "dora-publications-"
    marker = {
        "format": "rims-pubmed-full-hedge-commit-v1"
        if pubmed
        else "rims-dora-publication-raw-commit-v1",
        "source": "pubmed" if pubmed else "dora",
        "complete": True,
        "run": "fictional-run-1",
        "archive_folder": "/Documents/Archive/" + prefix + "fictional-run-1",
        "count": 1,
        "pmids" if pubmed else "keys": ["123"],
        "publication_doi_values": values or ["10.1234/Own"],
        "doi_provenance": "Explicit own identifier fields only; citations excluded",
        "scope_sha256": "a" * 64,
        "downstream_selection_applied": False,
    }
    raw = json.dumps(marker, ensure_ascii=False, indent=2).encode()
    return {
        "raw_bytes": raw,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "length": len(raw),
        "name": prefix.replace("-", "-", 1) + "complete-fictional-run-1.json",
        "file_id": "00000000-0000-4000-8000-00000000000" + ("1" if pubmed else "2"),
        "etag": '"1"',
    }


def prepare_bound(document, parent, producers=("pubmed",), **kwargs):
    raw = json.dumps(document).encode()
    options = {
        "preimage_bytes": raw,
        "expected_preimage_sha256": hashlib.sha256(raw).hexdigest(),
        "checkpoints": kwargs.get("checkpoints")
        if "checkpoints" in kwargs
        else {name: checkpoint(name) for name in producers},
    }
    options.update(kwargs)
    return with_raw_producer_dois(document, parent, producers, **options)


class RawPublicationInputTests(unittest.TestCase):
    def fixture(self, source="datacite"):
        key = "All_dois" if source == "datacite" else "All_DOIs"
        return {
            "properties": {
                "state": "Stopped",
                "connectionReferences": {
                    "shared_sharepointonline": {
                        "source": "Embedded",
                        "id": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
                        "connectionName": "existing-connection",
                        "connectionReferenceLogicalName": "existing-reference",
                    }
                },
                "definition": {
                    "actions": {
                        "Manifest": {"inputs": {"source": source}},
                        "Get_publication_dois": {
                            "type": "OpenApiConnection",
                            "inputs": {
                                "host": {
                                    "apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
                                    "connectionName": "shared_sharepointonline",
                                    "operationId": "GetItems",
                                },
                                "parameters": {
                                    "dataset": "https://example.sharepoint.com/sites/dev",
                                    "table": "00000000-0000-4000-8000-000000000003",
                                },
                            },
                        },
                        key: {
                            "type": "Compose",
                            "inputs": "@union(body('Valid_dois'),outputs('Seed_dois'))",
                            "runAfter": {"Seed_dois": ["Succeeded"]},
                        },
                        "Doi_source_snapshot": {"inputs": {}},
                    }
                },
            }
        }

    def test_missing_or_mismatched_existing_sharepoint_binding_is_refused(self):
        def mutate(document, case):
            p = document["properties"]
            g = p["definition"]["actions"]["Get_publication_dois"]
            ref = p["connectionReferences"]["shared_sharepointonline"]
            if case == "references":
                p.pop("connectionReferences")
            elif case == "alias":
                g["inputs"]["host"]["connectionName"] = "not-bound"
            elif case == "missing-alias":
                g["inputs"]["host"].pop("connectionName")
            elif case == "two-aliases":
                g["inputs"]["host"]["connectionReferenceName"] = (
                    "shared_sharepointonline"
                )
            elif case == "action-type":
                g["type"] = "Http"
            elif case == "operation":
                g["inputs"]["host"]["operationId"] = "CreateItem"
            elif case == "api":
                g["inputs"]["host"]["apiId"] = (
                    "/providers/Microsoft.PowerApps/apis/shared_other"
                )
            elif case == "reference-api":
                ref["id"] = "/providers/Microsoft.PowerApps/apis/shared_other"
            elif case == "reference-mode":
                ref["source"] = "Unknown"
            elif case == "reference-connection":
                ref.pop("connectionName")
            elif case == "table":
                g["inputs"]["parameters"].pop("table")

        for case in (
            "references",
            "alias",
            "missing-alias",
            "two-aliases",
            "action-type",
            "operation",
            "api",
            "reference-api",
            "reference-mode",
            "reference-connection",
            "table",
        ):
            d = self.fixture()
            mutate(d, case)
            before = copy.deepcopy(d)
            with self.subTest(case=case), self.assertRaises(ValueError):
                prepare_bound(d, "/Documents/Archive")
            self.assertEqual(d, before)

    def test_valid_alternative_alias_and_source_mode_are_preserved(self):
        for mode in ("Embedded", "Invoker"):
            for alias_key in ("connectionName", "connectionReferenceName"):
                d = self.fixture()
                p = d["properties"]
                getter = p["definition"]["actions"]["Get_publication_dois"]
                reference = p["connectionReferences"].pop("shared_sharepointonline")
                reference["source"] = mode
                p["connectionReferences"]["selected_sp"] = reference
                getter["inputs"]["host"].pop("connectionName")
                getter["inputs"]["host"][alias_key] = "selected_sp"
                before = copy.deepcopy(d)
                result = prepare_bound(d, "/Documents/Archive")
                actions = result["properties"]["definition"]["actions"]
                self.assertEqual(
                    result["properties"]["connectionReferences"],
                    before["properties"]["connectionReferences"],
                )
                self.assertEqual(actions["Get_publication_dois"], getter)
                added = set(actions) - set(p["definition"]["actions"])
                for name in added:
                    if actions[name]["type"] == "OpenApiConnection":
                        host = actions[name]["inputs"]["host"]
                        expected = copy.deepcopy(getter["inputs"]["host"])
                        expected["operationId"] = host["operationId"]
                        self.assertEqual(host, expected)
                        self.assertIn(
                            host["operationId"], ("HttpRequest", "GetFileContentByPath")
                        )
                self.assertEqual(d, before)

    def test_all_newly_managed_manifest_and_snapshot_fields_refuse_collisions(self):
        managed = {
            "Manifest": (
                "raw_publication_producer_inputs",
                "invalid_raw_publication_doi_values",
                "related_doi_input_strategy",
                "raw_publication_input_preimage_sha256",
            ),
            "Doi_source_snapshot": (
                "raw_publication_producer_inputs",
                "invalid_raw_publication_doi_values",
            ),
        }
        for action, fields in managed.items():
            for field in fields:
                for existing in (None, {}, "human-owned"):
                    d = self.fixture()
                    d["properties"]["definition"]["actions"][action]["inputs"][
                        field
                    ] = existing
                    before = copy.deepcopy(d)
                    with (
                        self.subTest(action=action, field=field, existing=existing),
                        self.assertRaises(ValueError),
                    ):
                        prepare_bound(d, "/Documents/Archive")
                    self.assertEqual(d, before)

    def test_raw_union_preserves_legacy_population_and_source_preimage(self):
        old = self.fixture()
        before = copy.deepcopy(old)
        d = prepare_bound(old, "/Documents/Archive")
        self.assertEqual(old, before)
        a = d["properties"]["definition"]["actions"]
        self.assertIn(
            "union(body('Valid_dois'),outputs('Seed_dois'))", a["All_dois"]["inputs"]
        )
        self.assertIn("body('Valid_raw_publication_dois')", a["All_dois"]["inputs"])
        self.assertEqual(a["Find_raw_pubmed"]["runAfter"], {"Seed_dois": ["Succeeded"]})
        self.assertEqual(
            a["All_dois"]["runAfter"], {"Invalid_raw_publication_dois": ["Succeeded"]}
        )
        self.assertIn(
            "raw_publication_producer_inputs", a["Doi_source_snapshot"]["inputs"]
        )

    def test_only_complete_identity_matched_raw_receipts_are_accepted(self):
        a = prepare_bound(self.fixture(), "/Documents/Archive")["properties"][
            "definition"
        ]["actions"]
        schema = a["Parse_raw_pubmed"]["inputs"]["schema"]
        self.assertEqual(schema["properties"]["complete"]["enum"], [True])
        self.assertIn("publication_doi_values", schema["required"])
        self.assertIn("length(union(", a["Guard_raw_pubmed"]["inputs"])
        self.assertIn("pubmed-acquisition-", a["Guard_raw_pubmed"]["inputs"])
        self.assertIn("Invalid_raw_publication_dois", a)

    def test_crossref_recovery_graph_cannot_be_scheduled_or_rewired(self):
        d = self.fixture("crossref")
        d["properties"]["definition"]["actions"]["Manifest"]["inputs"]["recovery"] = {}
        with self.assertRaises(ValueError):
            prepare_bound(d, "/Documents/Archive")

    def test_dora_union_adds_anchored_resolver_normalization_without_altering_single_producer(
        self,
    ):
        one = prepare_bound(self.fixture(), "/Documents/Archive")["properties"][
            "definition"
        ]["actions"]
        two = prepare_bound(
            self.fixture(), "/Documents/Archive", ("pubmed", "dora_publications")
        )["properties"]["definition"]["actions"]
        self.assertNotIn("Canonical_raw_publication_dois", one)
        self.assertIn(
            "startsWith(item(),'https://doi.org/')",
            two["Canonical_raw_publication_dois"]["inputs"]["select"],
        )
        self.assertEqual(
            two["Valid_raw_publication_dois"]["runAfter"],
            {"Canonical_raw_publication_dois": ["Succeeded"]},
        )
        self.assertIn(
            "dora_publications",
            two["Manifest"]["inputs"]["raw_publication_producer_inputs"],
        )

    def test_exact_current_preimage_is_required(self):
        d = self.fixture()
        before = copy.deepcopy(d)
        for options in (
            {"expected_preimage_sha256": "0" * 64},
            {"preimage_bytes": json.dumps({"different": True}).encode()},
            {"preimage_bytes": None},
        ):
            with self.subTest(options=list(options)), self.assertRaises(ValueError):
                prepare_bound(d, "/Documents/Archive", **options)
            self.assertEqual(d, before)
        with self.assertRaises(ValueError):
            with_raw_producer_dois(d, "/Documents/Archive")

    def test_producer_bytes_hash_identity_and_provenance_are_pinned(self):
        d = self.fixture()
        proof = checkpoint("pubmed")
        before = copy.deepcopy(proof)
        result = prepare_bound(d, "/Documents/Archive", checkpoints={"pubmed": proof})
        a = result["properties"]["definition"]["actions"]
        binding = a["Manifest"]["inputs"]["raw_publication_producer_inputs"]["pubmed"]
        self.assertEqual(binding["checkpoint_sha256"], proof["sha256"])
        self.assertEqual(binding["file_id"], proof["file_id"])
        self.assertEqual(binding["etag"], proof["etag"])
        self.assertNotIn(
            "$orderby", a["Find_raw_pubmed"]["inputs"]["parameters"]["parameters/uri"]
        )
        self.assertIn(
            proof["file_id"],
            a["Find_raw_pubmed"]["inputs"]["parameters"]["parameters/uri"],
        )
        self.assertEqual(proof, before)
        self.assertIn("Guard_raw_bytes_pubmed", a["Parse_raw_pubmed"]["runAfter"])

    def test_malformed_marker_and_changed_native_proof_are_refused(self):
        for field, value in [
            ("complete", False),
            ("source", "other"),
            ("count", True),
            ("count", 2),
            ("pmids", ["123", "123"]),
            ("pmids", ["0123"]),
            ("run", "../other"),
            ("archive_folder", "/Documents/Elsewhere"),
            ("doi_provenance", ""),
            ("scope_sha256", "unknown"),
            ("publication_doi_values", [123]),
            ("downstream_selection_applied", True),
            ("error", {}),
        ]:
            proof = checkpoint("pubmed")
            marker = json.loads(proof["raw_bytes"])
            marker[field] = value
            proof["raw_bytes"] = json.dumps(marker).encode()
            proof["sha256"] = hashlib.sha256(proof["raw_bytes"]).hexdigest()
            proof["length"] = len(proof["raw_bytes"])
            with self.subTest(field=field), self.assertRaises(ValueError):
                prepare_bound(
                    self.fixture(), "/Documents/Archive", checkpoints={"pubmed": proof}
                )
        for field, value in [
            ("sha256", "0" * 64),
            ("length", True),
            ("length", 1),
            ("name", "other.json"),
            ("etag", "*"),
            ("file_id", "not-guid"),
        ]:
            proof = checkpoint("pubmed")
            proof[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                prepare_bound(
                    self.fixture(), "/Documents/Archive", checkpoints={"pubmed": proof}
                )

    def test_replay_is_deterministic_and_repeated_transform_is_refused(self):
        d = self.fixture()
        a = prepare_bound(d, "/Documents/Archive")
        b = prepare_bound(d, "/Documents/Archive")
        self.assertEqual(a, b)
        before = copy.deepcopy(a)
        with self.assertRaises(ValueError):
            prepare_bound(a, "/Documents/Archive")
        self.assertEqual(a, before)

    def test_only_intended_actions_change_and_auth_recurrence_remain_exact(self):
        d = self.fixture()
        definition = d["properties"]["definition"]
        definition["triggers"] = {
            "Recurrence": {
                "type": "Recurrence",
                "recurrence": {"frequency": "Day"},
                "evaluatedRecurrence": {"frequency": "Day"},
            }
        }
        definition["actions"]["Unrelated"] = {
            "type": "OpenApiConnection",
            "inputs": {
                "authentication": "@parameters('$authentication')",
                "host": {"unknown": "preserve"},
            },
        }
        before = copy.deepcopy(d)
        new = prepare_bound(d, "/Documents/Archive")
        a = new["properties"]["definition"]["actions"]
        old = before["properties"]["definition"]["actions"]
        for name in set(old) - {"All_dois", "Manifest", "Doi_source_snapshot"}:
            self.assertEqual(a[name], old[name])
        self.assertEqual(
            new["properties"]["definition"]["triggers"], definition["triggers"]
        )
        self.assertEqual(d, before)
        original_envelope = copy.deepcopy(before)
        proposed_envelope = copy.deepcopy(new)
        original_envelope["properties"]["definition"].pop("actions")
        proposed_envelope["properties"]["definition"].pop("actions")
        self.assertEqual(proposed_envelope, original_envelope)
        self.assertEqual(
            a["All_dois"]["inputs"],
            "@union(union(body('Valid_dois'),outputs('Seed_dois')),body('Valid_raw_publication_dois'))",
        )

    def test_namespace_collisions_and_unqualified_site_are_refused(self):
        for key in (
            "Find_raw_pubmed",
            "Valid_raw_publication_dois",
            "Pinned_valid_raw_publication_dois",
        ):
            d = self.fixture()
            d["properties"]["definition"]["actions"][key] = {
                "type": "Compose",
                "inputs": "human",
            }
            before = copy.deepcopy(d)
            with self.subTest(key=key), self.assertRaises(ValueError):
                prepare_bound(d, "/Documents/Archive")
            self.assertEqual(d, before)
        for site in (
            "https://user:password@example.sharepoint.com/sites/dev",
            "https://example.sharepoint.com/sites/dev?query=1",
            "https://example.sharepoint.com/sites/x'",
            "https://example.sharepoint.com/sites/../dev",
        ):
            d = self.fixture()
            d["properties"]["definition"]["actions"]["Get_publication_dois"]["inputs"][
                "parameters"
            ]["dataset"] = site
            with self.subTest(site=site), self.assertRaises(ValueError):
                prepare_bound(d, "/Documents/Archive")

    def test_raw_spelling_retained_and_invalid_dois_are_not_promoted(self):
        proof = checkpoint(
            "dora_publications",
            values=[
                " HTTPS://doi.org/10.1234/Own%2FPart ",
                "doi:10.9999/Other",
                "10.bad/not-a-doi",
                "",
            ],
        )
        result = prepare_bound(
            self.fixture(),
            "/Documents/Archive",
            ("dora_publications",),
            checkpoints={"dora_publications": proof},
        )
        a = result["properties"]["definition"]["actions"]
        self.assertEqual(
            a["Pinned_valid_raw_publication_dois"]["inputs"],
            ["10.1234/own%2fpart", "10.9999/other"],
        )
        self.assertIn(
            "checkpoint_sha256",
            a["Manifest"]["inputs"]["raw_publication_producer_inputs"][
                "dora_publications"
            ],
        )
        self.assertEqual(
            json.loads(proof["raw_bytes"])["publication_doi_values"][0],
            " HTTPS://doi.org/10.1234/Own%2FPart ",
        )

    def test_cli_preserves_inputs_and_never_overwrites_a_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "flow.json"
            source.write_text(json.dumps(self.fixture()))
            raw = source.read_bytes()
            proof = checkpoint("pubmed")
            marker = folder / "marker.json"
            marker.write_bytes(proof.pop("raw_bytes"))
            proof["path"] = str(marker)
            proofs = folder / "proofs.json"
            proofs.write_text(json.dumps({"pubmed": proof}))
            output = folder / "plan.json"
            command = [
                sys.executable,
                "-m",
                "scripts.prepare_raw_publication_doi_inputs",
                "--document",
                str(source),
                "--preimage-sha256",
                hashlib.sha256(raw).hexdigest(),
                "--checkpoints",
                str(proofs),
                "--archive-parent",
                "/Documents/Archive",
                "--output",
                str(output),
            ]
            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = output.read_bytes()
            self.assertNotEqual(
                subprocess.run(command, capture_output=True, check=False).returncode, 0
            )
            self.assertEqual(output.read_bytes(), saved)
            marker.write_bytes(marker.read_bytes() + b" ")
            command[-1] = str(folder / "failed.json")
            self.assertNotEqual(
                subprocess.run(command, capture_output=True, check=False).returncode, 0
            )
            self.assertFalse(Path(command[-1]).exists())
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(output.read_bytes(), saved)

    def test_malformed_current_action_shapes_fail_closed(self):
        for key, value in [
            ("Manifest", {"inputs": None}),
            ("All_dois", []),
            ("Get_publication_dois", {}),
        ]:
            d = self.fixture()
            d["properties"]["definition"]["actions"][key] = value
            before = copy.deepcopy(d)
            with self.subTest(key=key), self.assertRaises(ValueError):
                prepare_bound(d, "/Documents/Archive")
            self.assertEqual(d, before)
        for producers in ("pubmed", (["pubmed"],), ("unknown",), ("pubmed", "pubmed")):
            with self.subTest(producers=producers), self.assertRaises(ValueError):
                prepare_bound(
                    self.fixture(), "/Documents/Archive", producers, checkpoints={}
                )

    def test_nonfinite_json_and_duplicate_keys_are_not_frozen_as_valid_receipts(self):
        for suffix in (b',"unqualified":NaN', b',"complete":true'):
            proof = checkpoint("pubmed")
            proof["raw_bytes"] = proof["raw_bytes"].rstrip()[:-1] + suffix + b"}"
            proof["length"] = len(proof["raw_bytes"])
            proof["sha256"] = hashlib.sha256(proof["raw_bytes"]).hexdigest()
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                prepare_bound(
                    self.fixture(), "/Documents/Archive", checkpoints={"pubmed": proof}
                )
