import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_report_library_metadata import FIELDS, prepare


def fixture():
    receipt = {
        "generation_id": "accepted-generation-1",
        "source_snapshot_id": "accepted-source-1",
        "query_version": "query-v1",
        "model_refresh_correlation": "refresh-1",
        "extraction_contract_sha256": "a" * 64,
        "reporting_month": "2026-09",
        "full_count": 3,
        "monthly_count": 2,
        "full_key_sha256": "b" * 64,
        "monthly_key_sha256": "c" * 64,
        "native_provenance_verified_by_this_script": True,
    }
    canonical = {
        "Status": "committed",
        "ReadbackVerified": True,
        "RunID": "canonical-revision-1",
    }
    for a, b in {
        "ReportingMonth": "reporting_month",
        "QueryVersion": "query_version",
        "AcceptedSourceBatchID": "source_snapshot_id",
        "ModelRefreshCorrelation": "model_refresh_correlation",
        "ExtractionContractSHA256": "extraction_contract_sha256",
        "PublicationCount": "monthly_count",
        "FullPublicationCount": "full_count",
        "CanonicalKeySetHash": "monthly_key_sha256",
        "FullCanonicalKeySetHash": "full_key_sha256",
    }.items():
        canonical[a] = receipt[b]
    return {
        "receipt": receipt,
        "canonical_manifest": canonical,
        "report_manifest": {
            "complete": True,
            "source_context": copy.deepcopy(receipt),
            "output_revision": "html-1",
            "html_template_sha256": "d" * 64,
        },
        "generation_manifest_url": "https://example.sharepoint.com/Documents/canonical/manifest.json",
        "report_manifest_url": "https://example.sharepoint.com/Documents/report/manifest.json",
        "artifacts": [
            {
                "file": {"UniqueId": "file-1", "Length": "7", "CheckOutType": 2},
                "item": {
                    "Id": 1,
                    "odata.etag": '"1"',
                    "Title": "Human title",
                    "OData__ExtendedDescription": "Human provenance",
                },
                "file_item_id": 1,
                "sha256": "e" * 64,
                "accepted_sha256": "e" * 64,
                "bytes": 7,
                "family": "report",
                "count_scope": "monthly",
                "role": "Structured monthly HTML",
            }
        ],
    }


class ReportMetadataTests(unittest.TestCase):
    def test_properties_preserve_human_fields_and_replay(self):
        e = fixture()
        p = prepare(e)
        changes = p["items"][0]["changes"]
        self.assertNotIn("Title", changes)
        self.assertNotIn("OData__ExtendedDescription", changes)
        self.assertEqual(changes["RIMSRecordCount"], 2)
        e["artifacts"][0]["item"].update(changes)
        self.assertEqual(prepare(e)["items"][0]["changes"], {})

    def test_cross_generation_or_count_mismatch_refused(self):
        for key in [
            "generation_id",
            "source_snapshot_id",
            "full_count",
            "monthly_key_sha256",
        ]:
            e = fixture()
            e["report_manifest"]["source_context"][key] = "other"
            with self.assertRaises(ValueError):
                prepare(e)
        e = fixture()
        e["canonical_manifest"]["FullPublicationCount"] = 99
        with self.assertRaises(ValueError):
            prepare(e)

    def test_content_checkout_and_association_drift_refused(self):
        for key, value in [("sha256", "f" * 64), ("bytes", 9), ("file_item_id", 2)]:
            e = fixture()
            e["artifacts"][0][key] = value
            with self.assertRaises(ValueError):
                prepare(e)
        e = fixture()
        e["artifacts"][0]["file"]["CheckOutType"] = 0
        with self.assertRaises(ValueError):
            prepare(e)

    def test_existing_metadata_conflict_preserved(self):
        e = fixture()
        e["artifacts"][0]["item"]["RIMSGeneration"] = "human-edited"
        with self.assertRaises(ValueError):
            prepare(e)

    def test_actual_internal_name_binding_preserves_conflicts_and_replay(self):
        e = fixture()
        e["field_bindings"] = {"RIMSGeneration": "Accepted_x0020_generation"}
        e["artifacts"][0]["item"]["Accepted_x0020_generation"] = "human-edited"
        with self.assertRaises(ValueError):
            prepare(e)
        e["artifacts"][0]["item"]["Accepted_x0020_generation"] = "accepted-generation-1"
        self.assertNotIn("RIMSGeneration", prepare(e)["items"][0]["changes"])

    def test_full_export_uses_full_count_and_own_revision_without_invented_template(
        self,
    ):
        e = fixture()
        a = e["artifacts"][0]
        a.update(family="canonical", count_scope="full", role="Full CSV")
        c = prepare(e)["items"][0]["changes"]
        self.assertEqual(c["RIMSRecordCount"], 3)
        self.assertEqual(c["RIMSOutputRevision"], "canonical-revision-1")
        self.assertNotIn("RIMSTemplateVersion", c)
        self.assertEqual(c["RIMSGenerationManifest"], c["RIMSArtifactManifest"])

    def test_unaccepted_duplicate_and_unsafe_links_refused(self):
        e = fixture()
        e["receipt"]["native_provenance_verified_by_this_script"] = False
        with self.assertRaises(ValueError):
            prepare(e)
        e = fixture()
        e["artifacts"] *= 2
        with self.assertRaises(ValueError):
            prepare(e)
        e = fixture()
        e["generation_manifest_url"] += "?token=secret"
        with self.assertRaises(ValueError):
            prepare(e)

    def test_plan_cannot_mutate_input_or_later_field_contract(self):
        e = fixture()
        before = copy.deepcopy(e)
        expected_fields = copy.deepcopy(FIELDS)
        p = prepare(e)
        p["items"][0]["file_preimage"]["Length"] = "999"
        p["fields"]["RIMSPeriod"] = ("Changed", "Number")
        self.assertEqual(e, before)
        self.assertEqual(FIELDS, expected_fields)

    def test_equal_but_invalid_counts_and_hashes_are_not_accepted(self):
        for key, value in [
            ("full_count", True),
            ("monthly_count", -1),
            ("full_key_sha256", "unknown"),
            ("generation_id", ""),
            ("query_version", " padded "),
        ]:
            with self.subTest(key=key):
                e = fixture()
                old = e["receipt"][key]
                e["receipt"][key] = value
                e["report_manifest"]["source_context"][key] = value
                for k, v in e["canonical_manifest"].items():
                    if v == old:
                        e["canonical_manifest"][k] = value
                before = copy.deepcopy(e)
                with self.assertRaises(ValueError):
                    prepare(e)
                self.assertEqual(e, before)

    def test_duplicate_item_identity_is_refused_even_for_distinct_files(self):
        e = fixture()
        other = copy.deepcopy(e["artifacts"][0])
        other["file"]["UniqueId"] = "file-2"
        e["artifacts"].append(other)
        with self.assertRaises(ValueError):
            prepare(e)

    def test_property_alias_collision_cannot_hide_a_human_edit(self):
        e = fixture()
        e["field_bindings"] = {"RIMSGeneration": "Shared", "RIMSPeriod": "Shared"}
        with self.assertRaises(ValueError):
            prepare(e)

    def test_missing_file_identity_and_role_cannot_be_associated(self):
        for key in ("UniqueId", "role"):
            e = fixture()
            target = (
                e["artifacts"][0]["file"] if key == "UniqueId" else e["artifacts"][0]
            )
            target[key] = ""
            with self.subTest(key=key), self.assertRaises(ValueError):
                prepare(e)

    def test_output_revision_must_be_known_before_association(self):
        for family, container, key in [
            ("report", "report_manifest", "output_revision"),
            ("canonical", "canonical_manifest", "RunID"),
        ]:
            e = fixture()
            e["artifacts"][0]["family"] = family
            e[container][key] = ""
            with self.subTest(family=family), self.assertRaises(ValueError):
                prepare(e)

    def test_cli_preserves_existing_output_and_invalid_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "evidence.json"
            output = Path(directory) / "plan.json"
            source.write_text(json.dumps(fixture()))
            command = [
                sys.executable,
                "-m",
                "scripts.prepare_report_library_metadata",
                str(source),
                str(output),
            ]
            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = output.read_bytes()
            replay = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertNotEqual(replay.returncode, 0)
            self.assertEqual(output.read_bytes(), saved)
            bad = fixture()
            bad["artifacts"][0]["item"]["RIMSGeneration"] = "unresolved human edit"
            source.write_text(json.dumps(bad))
            original = source.read_bytes()
            command[-1] = str(Path(directory) / "failed-plan.json")
            failure = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertNotEqual(failure.returncode, 0)
            self.assertFalse(Path(command[-1]).exists())
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(output.read_bytes(), saved)


if __name__ == "__main__":
    unittest.main()
