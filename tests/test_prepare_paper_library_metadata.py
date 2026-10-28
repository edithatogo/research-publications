import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_paper_library_metadata import START, prepare

SITE_ORIGIN = "https://example-my.sharepoint.com/"


def fixture():
    digest = "a" * 64
    folder = "/personal/example_operator/Documents/papers/paper-1-example"
    url = "https://example-my.sharepoint.com" + folder + "/paper.pdf"
    manifest = {
        "state": "linked",
        "CanonicalKey": "fictional:1",
        "DOI": "10.9999/fictional",
        "verified_file_unique_id": "00000000-0000-4000-8000-000000000001",
        "sha256_status": "verified_native_readback",
        "sha256": digest,
        "file_url": url,
        "folder": folder,
        "source": "fictional-source",
        "licence": "cc-by",
        "article_version": "acceptedVersion",
        "retrieved_utc": "2030-01-01T00:00:00Z",
        "source_url": "https://example.invalid/fictional-paper.pdf",
    }
    return {
        "parent": {
            "Id": 1,
            "Title": "Fictional paper",
            "field_2": "fictional:1",
            "field_11": "10.9999/fictional",
            "OAArchiveState": "linked",
            "OAArchiveURL": {"Url": url},
        },
        "manifest": manifest,
        "file": {
            "UniqueId": manifest["verified_file_unique_id"],
            "ServerRelativeUrl": folder + "/paper.pdf",
            "Name": "paper.pdf",
            "CheckOutType": 2,
            "Length": "100",
        },
        "item": {
            "Id": 7,
            "odata.etag": '"1"',
            "Title": None,
            "OData__ExtendedDescription": None,
        },
        "sha256": digest,
        "bytes": 100,
        "item_url": "https://example-my.sharepoint.com/_api/example/items(7)",
        "register_url": "https://example-my.sharepoint.com/Lists/Publications/DispForm.aspx?ID=1",
    }


class PaperMetadataTests(unittest.TestCase):
    def test_minimum_projection_preserves_authoritative_inputs(self):
        source = fixture()
        before = copy.deepcopy(source)
        plan = prepare(source)
        self.assertEqual(set(plan["changes"]), {"Title", "OData__ExtendedDescription"})
        self.assertIn("fictional:1", plan["changes"]["OData__ExtendedDescription"])
        self.assertIn("acceptedVersion", plan["changes"]["Title"])
        self.assertFalse(plan["content_writes"])
        self.assertFalse(plan["manifest_writes"])
        self.assertEqual(source, before)

    def test_human_text_and_title_are_preserved_and_retry_is_noop(self):
        source = fixture()
        source["item"]["Title"] = "Curated title"
        human = "<p>Human note &amp; unresolved question</p>"
        source["item"]["OData__ExtendedDescription"] = human
        plan = prepare(source)
        self.assertNotIn("Title", plan["changes"])
        self.assertTrue(plan["changes"]["OData__ExtendedDescription"].startswith(human))
        source["item"].update(plan["changes"])
        source["item"]["OData__ExtendedDescription"] = (
            source["item"]["OData__ExtendedDescription"]
            .replace('href="' + SITE_ORIGIN.rstrip("/"), 'href="')
            .replace(":", "&#58;")
        )
        self.assertEqual(prepare(source)["changes"], {})

    def test_edited_managed_block_is_not_overwritten(self):
        source = fixture()
        source["item"].update(prepare(source)["changes"])
        source["item"]["OData__ExtendedDescription"] = source["item"][
            "OData__ExtendedDescription"
        ].replace("cc-by", "human disputed licence")
        with self.assertRaises(ValueError):
            prepare(source)
        source["item"]["OData__ExtendedDescription"] = START + "unresolved"
        with self.assertRaises(ValueError):
            prepare(source)

    def test_content_link_checkout_and_recovery_drift_are_refused(self):
        for target, key, value in [
            ("file", "UniqueId", "different"),
            ("file", "CheckOutType", 0),
            ("manifest", "state", "saved"),
            ("manifest", "sha256", "b" * 64),
            ("item", "odata.etag", "*"),
        ]:
            source = fixture()
            source[target][key] = value
            with self.assertRaises(ValueError):
                prepare(source)
        source = fixture()
        source["parent"]["OAArchiveURL"]["Url"] = "https://example.invalid/edited"
        with self.assertRaises(ValueError):
            prepare(source)

    def test_long_unicode_title_stays_within_native_limit(self):
        source = fixture()
        source["parent"]["Title"] = "😀" * 300
        title = prepare(source)["changes"]["Title"]
        self.assertLessEqual(len(title.encode("utf-16-le")), 510)
        self.assertTrue(title.endswith("acceptedVersion"))

    def test_qualified_public_source_queries_are_preserved_exactly(self):
        source = fixture()
        source["manifest"]["md5"] = "a" * 32
        source["manifest"]["source_url"] = (
            "https://pmc-oa-opendata.s3.amazonaws.com/paper.pdf?md5=" + "a" * 32
        )
        self.assertIn(
            "md5=" + "a" * 32, prepare(source)["changes"]["OData__ExtendedDescription"]
        )
        source["manifest"]["source_url"] = (
            "https://journals.plos.org/article/file?id=10.9999/fictional&type=printable"
        )
        self.assertIn(
            "type=printable", prepare(source)["changes"]["OData__ExtendedDescription"]
        )
        source["manifest"]["source_url"] += "&token=private"
        with self.assertRaises(ValueError):
            prepare(source)

    def test_sharepoint_relative_and_space_encoded_record_href_is_noop(self):
        import re

        source = fixture()
        source["register_url"] = source["register_url"].replace(
            "Publications", "Publication Registry"
        )
        source["item"].update(prepare(source)["changes"])
        description = source["item"]["OData__ExtendedDescription"]
        source["item"]["OData__ExtendedDescription"] = re.sub(
            r'href="([^"]+)"',
            lambda m: (
                'href="'
                + m[1].replace(SITE_ORIGIN.rstrip("/"), "").replace(" ", "%20")
                + '"'
            ),
            description,
        )
        self.assertEqual(prepare(source)["changes"], {})

    def test_token_bearing_source_links_are_not_copied(self):
        source = fixture()
        source["manifest"]["source_url"] = "https://example.invalid/paper?token=private"
        with self.assertRaises(ValueError):
            prepare(source)

    def test_plan_does_not_alias_source_version_evidence(self):
        source = fixture()
        before = copy.deepcopy(source)
        plan = prepare(source)
        plan["file_preimage"]["Length"] = "999"
        self.assertEqual(source, before)

    def test_register_link_must_identify_authoritative_parent(self):
        source = fixture()
        source["register_url"] = source["register_url"].replace("ID=1", "ID=9")
        before = copy.deepcopy(source)
        with self.assertRaises(ValueError):
            prepare(source)
        self.assertEqual(source, before)

    def test_malformed_native_evidence_is_refused_without_mutating_input(self):
        cases = [
            ("parent", "Id", True),
            ("item", "Id", 0),
            ("item", "odata.etag", {"unqualified": "etag"}),
            ("file", "CheckOutType", 2.0),
        ]
        for section, key, value in cases:
            with self.subTest(section=section, key=key):
                source = fixture()
                source[section][key] = value
                before = copy.deepcopy(source)
                with self.assertRaises(ValueError):
                    prepare(source)
                self.assertEqual(source, before)

    def test_unknown_capture_time_is_not_promoted_to_provenance(self):
        source = fixture()
        source["manifest"]["retrieved_utc"] = "unknown"
        with self.assertRaises(ValueError):
            prepare(source)

    def test_matching_but_empty_file_id_is_not_evidence(self):
        source = fixture()
        source["file"]["UniqueId"] = ""
        source["manifest"]["verified_file_unique_id"] = ""
        with self.assertRaises(ValueError):
            prepare(source)

    def test_cli_preserves_existing_output_and_recovery_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "snapshot.json"
            output = Path(directory) / "plan.json"
            snapshot = fixture()
            source.write_text(json.dumps(snapshot))
            command = [
                sys.executable,
                "-m",
                "scripts.prepare_paper_library_metadata",
                str(source),
                str(output),
            ]
            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = output.read_bytes()
            snapshot["manifest"]["verified_file_etag"] = "historical-content-etag"
            snapshot["file"]["ETag"] = "current-metadata-etag"
            original = copy.deepcopy(snapshot)
            prepare(snapshot)
            self.assertEqual(snapshot, original)
            replay = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertNotEqual(replay.returncode, 0)
            self.assertEqual(output.read_bytes(), saved)
            snapshot["manifest"]["state"] = "saved"
            source.write_text(json.dumps(snapshot))
            raw = source.read_bytes()
            command[-1] = str(Path(directory) / "failed-plan.json")
            failed = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertFalse(Path(command[-1]).exists())
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(output.read_bytes(), saved)


if __name__ == "__main__":
    unittest.main()
