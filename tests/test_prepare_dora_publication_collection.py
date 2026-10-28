import copy
import unittest

from scripts.prepare_dora_publication_collection import (
    COLLECTION,
    build,
    with_daily_updates,
)


def checkpoint(document, **overrides):
    from scripts.patch_clinicaltrials_read_retries import definition_sha256
    from scripts.prepare_dora_publication_collection import with_raw_doi_checkpoint

    options = {
        "expected_definition_sha256": definition_sha256(
            document["properties"]["definition"]
        )
    }
    options.update(overrides)
    return with_raw_doi_checkpoint(document, **options)


class PublicationCollectionTests(unittest.TestCase):
    def fixture(self):
        return build(
            "https://example.sharepoint.com/sites/dev",
            "/Documents/Archive",
            {
                "source": "Embedded",
                "id": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
                "connectionName": "existing",
                "connectionReferenceLogicalName": "existing",
            },
            {"source": "dora"},
        )

    def test_collection_boundaries_and_full_metadata_are_preserved(self):
        a = self.fixture()["properties"]["definition"]["actions"]
        self.assertEqual(a["Scope"]["inputs"]["collection_url"], COLLECTION)
        p = a["Scan_collection_Before"]["actions"]
        self.assertEqual(
            p["Guard_collection_shape_Before"]["runAfter"],
            {"Verify_collection_Before": ["Succeeded"]},
        )
        self.assertIn(
            "?mode=full",
            a["For_each_record"]["actions"]["Get_full_record"]["inputs"]["uri"],
        )
        self.assertEqual(
            a["For_each_record"]["actions"]["Guard_record"]["runAfter"],
            {"Identifier_row": ["Succeeded"]},
        )

    def test_marker_requires_complete_before_after_keys_and_every_record(self):
        a = self.fixture()["properties"]["definition"]["actions"]
        self.assertEqual(
            a["Scan_collection_After"]["runAfter"],
            {"Reset_ScanDone_After": ["Succeeded"]},
        )
        self.assertIn("RecordFiles", a["Guard_collection_stable"]["inputs"])
        self.assertEqual(
            a["Manifest"]["runAfter"], {"Guard_collection_stable": ["Succeeded"]}
        )
        self.assertFalse(a["Manifest"]["inputs"]["downstream_selection_applied"])
        self.assertEqual(
            a["Read_manifest"]["runAfter"], {"Save_manifest": ["Succeeded"]}
        )

    def test_daily_keeps_original_manual_definition(self):
        d = self.fixture()
        before = copy.deepcopy(d)
        with self.assertRaisesRegex(ValueError, "manual"):
            with_daily_updates(d)
        self.assertEqual(before, d)

    def test_own_doi_fields_decode_html_entities_without_citation_selection(self):
        import xml.etree.ElementTree as ET

        d = self.fixture()
        new = checkpoint(d)
        a = new["properties"]["definition"]["actions"]
        loop = a["For_each_record"]["actions"]
        metadata = '<tr><td>dc.identifier.doi</td><td headers="s2" class="metadataFieldValue">10.1000&#x2F;own&#x28;1&#x29;</td></tr><tr><td>dc.relation.reference</td><td class="metadataFieldValue">10.1000/cited</td></tr>'
        fragments = metadata.split("dc.identifier.doi</td>")[1:]
        values = []
        for part in fragments:
            value = part.split('class="metadataFieldValue">')[1].split("</td>")[0]
            values.append(
                "".join(
                    ET.fromstring(
                        "<r>" + value.replace("&nbsp;", "&#160;") + "</r>"
                    ).itertext()
                )
                .strip()
                .lower()
            )
        self.assertEqual(values, ["10.1000/own(1)"])
        self.assertEqual(
            loop["Record_file"]["runAfter"], {"Set_own_dois": ["Succeeded"]}
        )
        self.assertEqual(
            a["Save_complete_checkpoint"]["runAfter"],
            {"Verify_manifest": ["Succeeded"]},
        )
        self.assertEqual(
            a["Save_complete_checkpoint"]["inputs"]["parameters"]["folderPath"],
            "/Documents/Archive",
        )
        self.assertNotIn(
            "publication_doi_values",
            d["properties"]["definition"]["actions"]["Manifest"]["inputs"],
        )

    def test_policy_and_completed_checkpoint_collisions_are_preserved(self):
        policy = {"source": "dora", "nested": {"fixture": True}}
        before = copy.deepcopy(policy)
        d = build(
            "https://example.sharepoint.com/sites/dev",
            "/Documents/archive",
            {
                "source": "Embedded",
                "id": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
                "connectionName": "existing",
                "connectionReferenceLogicalName": "existing",
            },
            policy,
        )
        d["properties"]["definition"]["actions"]["Scope"]["inputs"]["policy"]["nested"][
            "fixture"
        ] = False
        self.assertEqual(policy, before)
        for name in (
            "Save_complete_checkpoint",
            "Read_complete_checkpoint",
            "Verify_complete_checkpoint",
        ):
            d = self.fixture()
            d["properties"]["definition"]["actions"][name] = {
                "type": "Compose",
                "inputs": "human",
            }
            original = copy.deepcopy(d)
            with self.subTest(name=name), self.assertRaises(ValueError):
                checkpoint(d)
            self.assertEqual(d, original)

    def test_doi_fields_and_loop_actions_refuse_existing_values(self):
        for field in ("publication_doi_values", "doi_provenance"):
            d = self.fixture()
            d["properties"]["definition"]["actions"]["Manifest"]["inputs"][field] = None
            before = copy.deepcopy(d)
            with self.subTest(field=field), self.assertRaises(ValueError):
                checkpoint(d)
            self.assertEqual(d, before)

    def test_checkpoint_requires_exact_current_definition(self):
        from scripts.prepare_dora_publication_collection import with_raw_doi_checkpoint

        d = self.fixture()
        before = copy.deepcopy(d)
        with self.assertRaises(ValueError):
            with_raw_doi_checkpoint(d)
        with self.assertRaisesRegex(ValueError, "drift"):
            checkpoint(d, expected_definition_sha256="0" * 64)
        self.assertEqual(d, before)
