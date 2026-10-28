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
    def test_failed_or_timed_out_http_routes_preserve_outputs_and_block_success(self):
        # Same small dependency-routing model as the PubMed suite; no WDL execution.
        def trace(actions, stage, status):
            states = {stage: status}
            while True:
                pending = {}
                for name, node in actions.items():
                    after = node.get("runAfter", {})
                    if (
                        name not in states
                        and after
                        and all(key in states for key in after)
                    ):
                        pending[name] = (
                            "Succeeded"
                            if all(
                                states[key] in allowed for key, allowed in after.items()
                            )
                            else "Skipped"
                        )
                if not pending:
                    return states
                states.update(pending)

        a = self.fixture()["properties"]["definition"]["actions"]
        cases = [
            (
                a["Scan_collection_" + suffix]["actions"],
                "Get_collection_" + suffix,
                "Raw_collection_" + suffix,
            )
            for suffix in ("Before", "After")
        ]
        cases.append((a["For_each_record"]["actions"], "Get_full_record", "Raw_record"))
        for actions, stage, success in cases:
            for status in ("Failed", "TimedOut"):
                with self.subTest(stage=stage, status=status):
                    states = trace(actions, stage, status)
                    self.assertEqual(states["Verify_failure_" + stage], "Succeeded")
                    self.assertEqual(states[success], "Skipped")
                    self.assertNotEqual(states.get("Record_file"), "Succeeded")
                    envelope = actions["Raw_failure_" + stage]["inputs"]
                    self.assertEqual(envelope["response"], "@outputs('" + stage + "')")
                    self.assertIn("'unavailable'", envelope["content_state"])
                    self.assertFalse(envelope["accepted"])
                    self.assertEqual(
                        actions["Mark_failure_" + stage]["inputs"],
                        {"name": "ScanFailed", "value": True},
                    )
                    self.assertEqual(
                        actions["Save_failure_" + stage]["inputs"]["retryPolicy"],
                        {"type": "none"},
                    )
        self.assertIn(
            "not(variables('ScanFailed'))", a["Guard_collection_stable"]["inputs"]
        )
        self.assertEqual(
            a["For_each_record"]["actions"]["Raw_record"]["inputs"],
            "@string(body('Get_full_record'))",
        )

    def test_record_dependencies_and_status_conditions_are_preserved(self):
        d = self.fixture()
        loop = d["properties"]["definition"]["actions"]["For_each_record"]["actions"]
        loop["Caller_guard"] = {
            "type": "Compose",
            "inputs": True,
            "runAfter": {"Guard_record": ["Succeeded"]},
        }
        loop["Record_file"]["runAfter"]["Caller_guard"] = ["Succeeded", "Skipped"]
        before = copy.deepcopy(d)
        result = checkpoint(d)
        dependencies = result["properties"]["definition"]["actions"]["For_each_record"][
            "actions"
        ]["Record_file"]["runAfter"]
        self.assertEqual(
            dependencies,
            {
                "Guard_record": ["Succeeded"],
                "Caller_guard": ["Succeeded", "Skipped"],
                "Set_own_dois": ["Succeeded"],
            },
        )
        self.assertEqual(d, before)

    def test_record_cycles_and_incompatible_guards_are_refused(self):
        for case in ("cycle", "incompatible", "unknown", "incompatible-ancestor"):
            d = self.fixture()
            loop = d["properties"]["definition"]["actions"]["For_each_record"][
                "actions"
            ]
            if case == "cycle":
                loop["Caller_guard"] = {
                    "type": "Compose",
                    "inputs": True,
                    "runAfter": {"Record_file": ["Succeeded"]},
                }
                loop["Record_file"]["runAfter"]["Caller_guard"] = ["Succeeded"]
            elif case == "incompatible":
                loop["Record_file"]["runAfter"]["Guard_record"] = ["Failed"]
            elif case == "incompatible-ancestor":
                loop["Caller_guard"] = {
                    "type": "Compose",
                    "inputs": True,
                    "runAfter": {"Guard_record": ["Failed"]},
                }
                loop["Record_file"]["runAfter"]["Caller_guard"] = ["Succeeded"]
            else:
                loop["Record_file"]["runAfter"]["Missing_guard"] = ["Succeeded"]
            before = copy.deepcopy(d)
            with self.subTest(case=case), self.assertRaises(ValueError):
                checkpoint(d)
            self.assertEqual(d, before)

    def test_alternate_and_nested_variable_declarations_are_refused(self):
        for nested in (False, True):
            d = self.fixture()
            actions = d["properties"]["definition"]["actions"]
            declaration = {
                "type": "InitializeVariable",
                "runAfter": {},
                "inputs": {
                    "variables": [
                        {"name": "OwnPublicationDOIs", "type": "array", "value": []}
                    ]
                },
            }
            actions["Different_name"] = (
                {"type": "Scope", "actions": {"Nested_initializer": declaration}}
                if nested
                else declaration
            )
            before = copy.deepcopy(d)
            with self.subTest(nested=nested), self.assertRaises(ValueError):
                checkpoint(d)
            self.assertEqual(d, before)

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
            loop["Record_file"]["runAfter"],
            {"Guard_record": ["Succeeded"], "Set_own_dois": ["Succeeded"]},
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
