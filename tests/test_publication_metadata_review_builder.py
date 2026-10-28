"""Source graph checks only; no native run or AI call."""

import copy
import unittest

from scripts.prepare_reconciliation_review_flow import (
    build_canonical_runtime_definition,
)
from scripts.publication_metadata_conflicts import (
    build_metadata_review_slice,
    cases_from_metadata_differences,
)
from scripts.publication_reconciliation import _plain


class MetadataReviewBuilderTests(unittest.TestCase):
    def inputs(self):
        rows = [
            {
                "item_id": 7,
                "source_key": "pubmed:123",
                "values": {"Title": "Retained", "Authors": "A"},
                "evidence": [],
            }
        ]
        cases = cases_from_metadata_differences(
            [{"id": 7, "field": "Authors", "registry": "A", "canonical": "B"}],
            rows,
            source_revision="source-one",
            registry_revision="registry-one",
            complete=True,
        )
        case = cases[0]
        serialized = [
            {
                "case_id": case.case_id,
                "source_fingerprint": case.source_fingerprint,
                "records": _plain(case.records),
                "issue": case.issue,
                "rule_version": case.rule_version,
                "source_revision": case.source_revision,
            }
        ]
        graph = build_canonical_runtime_definition(
            dataset="https://example.org",
            folder="/Documents/Fictional",
            group_id="fixture-group",
            model_id="fixture-model",
            ai_prompt_id="fixture-prompt",
            dataverse_ref="fixture-ref",
            ai_input_name="FixtureJSON",
            cache_name="fixture-cache.txt",
            prompt_revision="22222222-2222-4222-8222-222222222222",
            max_new_predictions=0,
        )
        kwargs = {
            "canonical_query": 'EVALUATE SELECTCOLUMNS(Fictional, "PMID", Fictional[PMID])',
            "canonical_rows": [{"[PMID]": "123", "[Authors]": "B"}],
            "dataset": "https://example.org",
            "list_id": "11111111-1111-4111-8111-111111111111",
            "registry_items": [
                {"Id": 7, "field_1": "pubmed:123", "Title": "Retained", "field_3": "A"}
            ],
            "sharepoint_host": {
                "connectionName": "fixture-sharepoint",
                "operationId": "HttpRequest",
                "apiId": "fixture-api",
            },
            "total_cases": 23,
        }
        return graph, serialized, kwargs

    def test_selected_metadata_slice_preserves_input_and_guards_both_snapshots(self):
        graph, cases, kwargs = self.inputs()
        before = copy.deepcopy(graph)
        candidate = build_metadata_review_slice(graph, cases, **kwargs)
        self.assertEqual(graph, before)
        guard = candidate["actions"]["Metadata_Guard_Snapshots"]
        self.assertEqual(
            guard["else"]["actions"]["Metadata_Stop_Drift"]["type"], "Terminate"
        )
        self.assertEqual(
            candidate["actions"]["Metadata_Frozen_Cases_Text"]["runAfter"],
            {"Metadata_Guard_Snapshots": ["Succeeded"]},
        )

        def walk(actions):
            for name, action in actions.items():
                yield name, action
                yield from walk(action.get("actions", {}))
                yield from walk(action.get("else", {}).get("actions", {}))

        text = next(
            action["inputs"]
            for name, action in walk(candidate["actions"])
            if name == "Review_HTML"
        )
        self.assertIn("Selected 1 of 23", text)
        self.assertEqual(
            candidate["parameters"]["reconciliationNewPredictionLimit"]["defaultValue"],
            0,
        )
        self.assertEqual(
            candidate["actions"]["Metadata_Read_Registry"]["inputs"]["parameters"][
                "parameters/method"
            ],
            "GET",
        )

    def test_changed_registry_source_or_enabled_predictions_rejected(self):
        for defect in ("registry", "canonical", "prediction", "fingerprint"):
            graph, cases, kwargs = self.inputs()
            if defect == "registry":
                kwargs["registry_items"][0]["field_3"] = "Edited"
            elif defect == "canonical":
                kwargs["canonical_rows"][0]["[Authors]"] = "Changed"
            elif defect == "prediction":
                graph["parameters"]["reconciliationNewPredictionLimit"][
                    "defaultValue"
                ] = 1
            else:
                cases[0]["source_fingerprint"] = "forged"
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                build_metadata_review_slice(graph, cases, **kwargs)
