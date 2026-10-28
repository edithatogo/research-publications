import json
import unittest

from scripts.prepare_reconciliation_review_flow import (
    AI_SCHEMA,
    build_canonical_runtime_definition,
    build_definition,
    fixtures,
)


def definition(**kwargs):
    return build_definition(
        fixtures(),
        dataset="https://example.org",
        folder="/Documents/Fictional",
        **kwargs,
    )


def walk(actions):
    for action in actions.values():
        yield action
        yield from walk(action.get("actions", {}))
        yield from walk(action.get("else", {}).get("actions", {}))


class ReconciliationReviewFlowTests(unittest.TestCase):
    def test_native_graph_dependencies_and_no_authoritative_mutations(self):
        graph = definition()
        self.assertEqual(
            graph["actions"]["For_each_case"]["runAfter"],
            {"Initialize_Results": ["Succeeded"]},
        )
        operations = [
            a["inputs"]["host"]["operationId"]
            for a in walk(graph["actions"])
            if a["type"] == "OpenApiConnection"
        ]
        self.assertEqual(operations, ["CreateFile", "GetFileContentByPath"])
        self.assertFalse(
            graph["actions"]["Review_receipt"]["inputs"]["native_ai_execution"]
        )
        self.assertFalse(
            graph["actions"]["Review_receipt"]["inputs"][
                "authoritative_records_changed"
            ]
        )

    def test_guard_is_strict_and_failure_preserves_human_review(self):
        case = definition()["actions"]["For_each_case"]["actions"]
        guard = case["Evaluate_AI"]["actions"]["Validate_advice"]["expression"]
        for fragment in [
            "source_fingerprint",
            "Unknown_candidates",
            "Unknown_evidence",
            "trim(body('Parse_AI_response')?['reasoning'])",
        ]:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, guard)
        self.assertFalse(AI_SCHEMA["additionalProperties"])
        self.assertEqual(
            case["AI_failure_fallback"]["runAfter"]["Evaluate_AI"],
            ["Failed", "TimedOut"],
        )
        self.assertEqual(
            case["Append_panel"]["runAfter"]["AI_failure_fallback"],
            ["Succeeded", "Skipped"],
        )
        self.assertIn("&lt;", case["Append_panel"]["inputs"]["value"])

    def test_native_ai_requires_both_qualified_bindings(self):
        for kwargs in (
            {"ai_prompt_id": "saved-prompt"},
            {"dataverse_ref": "existing-reference"},
            {"ai_prompt_id": "saved-prompt", "dataverse_ref": "existing-reference"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                definition(**kwargs)
        graph = definition(
            ai_prompt_id="saved-prompt",
            dataverse_ref="existing-reference",
            ai_input_name="CaseJSON_native",
        )
        self.assertEqual(
            graph["actions"]["For_each_case"]["actions"]["Evaluate_AI"]["actions"][
                "Run_a_prompt"
            ]["inputs"]["host"]["operationId"],
            "aibuilderpredict_customprompt",
        )

    def test_frozen_case_rejects_source_tampering(self):
        cases = fixtures()
        cases[0]["records"][0]["values"]["Title"] = "changed since snapshot"
        with self.assertRaisesRegex(ValueError, "differs"):
            build_definition(
                cases, dataset="https://example.org", folder="/Documents/Fictional"
            )

    def test_snapshot_mode_is_not_labelled_fictional(self):
        graph = definition(commissioning=False)
        self.assertNotIn(
            "fictional commissioning", graph["actions"]["Review_HTML"]["inputs"]
        )
        self.assertEqual(
            graph["actions"]["Review_receipt"]["inputs"]["kind"],
            "reconciliation_exception_review",
        )

    def test_native_acquisition_is_read_only_bounded_and_keeps_original_values(self):
        graph = build_canonical_runtime_definition(
            dataset="https://example.org",
            folder="/Documents/Fictional",
            group_id="group",
            model_id="model",
        )
        actions = graph["actions"]
        self.assertIn(
            "TOPN(21",
            actions["Read_canonical_exceptions"]["inputs"]["parameters"][
                "specification/query"
            ],
        )
        selected = actions["Select_runtime_cases"]["inputs"]["select"]
        self.assertEqual(selected["records"][0]["values"], "@item()")
        self.assertIsNone(selected["ai_result"])
        self.assertEqual(selected["source_fingerprint"], "@string(item())")
        guard = actions["Guard_source_batch"]
        self.assertIn("[BlankRevisions]", guard["expression"])
        self.assertIn("lessOrEquals", guard["expression"])
        self.assertIn("Unknown_exception_rules", guard["expression"])
        self.assertEqual(
            guard["else"]["actions"]["Reject_source_batch"]["type"], "Terminate"
        )
        empty = guard["actions"]["If_exceptions_present"]["else"]["actions"]
        self.assertEqual(list(empty), ["No_exceptions"])
        operations = [
            a["inputs"]["host"]["operationId"]
            for a in walk(actions)
            if a["type"] == "OpenApiConnection"
        ]
        self.assertEqual(
            sorted(operations),
            sorted(
                [
                    "ExecuteDatasetQuery",
                    "ExecuteDatasetQuery",
                    "CreateFile",
                    "GetFileContentByPath",
                ]
            ),
        )

    def test_exact_ai_input_and_connection_key_are_used_without_inference(self):
        graph = definition(
            ai_prompt_id="saved-prompt",
            dataverse_ref="qualified_dataverse_key",
            ai_input_name="CaseJSON_native",
        )
        case = graph["actions"]["For_each_case"]["actions"]
        action = case["Evaluate_AI"]["actions"]["Run_a_prompt"]
        self.assertEqual(
            action["inputs"]["host"]["connectionName"], "qualified_dataverse_key"
        )
        self.assertEqual(
            [k for k in action["inputs"]["parameters"] if k != "recordId"],
            ["item/requestv2/CaseJSON_native"],
        )
        self.assertIn(
            "actions('Run_a_prompt')", case["AI_failure_fallback"]["inputs"]["value"]
        )

    def test_unconfigured_ai_uses_normal_manual_fallback_without_parse_error(self):
        action = definition()["actions"]["For_each_case"]["actions"]["Evaluate_AI"]
        self.assertEqual(action["type"], "If")
        self.assertEqual(list(action["else"]["actions"]), ["No_AI_available"])

    def test_ai_binding_defaults_off_and_never_sends_fixture_answers(self):
        graph = definition(
            ai_prompt_id="saved", dataverse_ref="dv", ai_input_name="CaseJSON"
        )
        branch = graph["actions"]["For_each_case"]["actions"]["Evaluate_AI"]
        self.assertEqual(branch["expression"], "@equals(false,true)")
        text = branch["actions"]["Run_a_prompt"]["inputs"]["parameters"][
            "item/requestv2/CaseJSON"
        ]
        self.assertTrue(
            all(
                fragment in text
                for fragment in ("'ai_result'", "'expected'", "removeProperty")
            )
        )
        self.assertFalse(
            graph["actions"]["Review_receipt"]["inputs"]["native_ai_execution"]
        )
        enabled = definition(
            ai_prompt_id="saved",
            dataverse_ref="dv",
            ai_input_name="CaseJSON",
            ai_runtime_enabled=True,
        )
        self.assertEqual(
            enabled["actions"]["For_each_case"]["actions"]["Evaluate_AI"]["expression"],
            "@equals(true,true)",
        )
        with self.assertRaises(ValueError):
            definition(ai_runtime_enabled=True)

    def test_bounded_cache_payload_preserves_unselected_and_other_revision_entries(
        self,
    ):
        from scripts.prepare_reconciliation_review_flow import (
            preserve_other_cache_outcomes,
        )

        graph = {
            "actions": {
                "Cache_payload": {
                    "inputs": {"entries": "@variables('NextCacheEntries')"},
                    "runAfter": {"For_each_case": ["Succeeded"]},
                }
            }
        }
        preserve_other_cache_outcomes(graph)
        actions = graph["actions"]
        keys = actions["Select_replacement_cache_keys"]["inputs"]["select"]
        for field in (
            "case_id",
            "source_fingerprint",
            "rule_version",
            "source_revision",
        ):
            with self.subTest(field=field):
                self.assertIn(field, keys)
        self.assertEqual(
            actions["Keep_unreplaced_cache_entries"]["inputs"]["from"],
            "@variables('CacheEntries')",
        )
        self.assertEqual(
            actions["For_each_retained_cache_entry"]["runtimeConfiguration"][
                "concurrency"
            ]["repetitions"],
            1,
        )
        self.assertEqual(
            actions["Cache_payload"]["runAfter"],
            {"For_each_retained_cache_entry": ["Succeeded"]},
        )
        self.assertNotIn("union", str(actions))

    def test_year_aliases_and_frozen_source_text_are_data(self):
        from scripts.prepare_reconciliation_review_flow import (
            _record_panel_expression,
            workflow_data_text,
        )

        expression = _record_panel_expression()
        year = expression[
            expression.index("'<dt>Year</dt><dd>'") : expression.index(
                "'<dt>Journal</dt><dd>'"
            )
        ]
        self.assertLess(
            year.index("['Publication[PublicationYear]']"),
            year.index("['PublicationYear']"),
        )
        self.assertLess(year.index("['PublicationYear']"), year.index("['Year']"))
        self.assertLess(len(expression), 8192)
        graph = definition()
        records = graph["actions"]["For_each_case"]["actions"]["Collect_ids"]["actions"]
        self.assertEqual(
            records["Append_record_panel"]["runAfter"], {"RecordValues": ["Succeeded"]}
        )
        original = {
            "Title": "@{add(1,2)}",
            "Email": "a@example.org",
            "LiteralEscape": r"\u0040keep",
            "Unicode": "β",
        }
        literal = workflow_data_text(original)
        self.assertNotIn("@", literal)
        self.assertEqual(json.loads(literal[5:]), original)
        self.assertEqual(
            graph["actions"]["Frozen_cases"]["inputs"],
            "@json(substring(outputs('Frozen_case_data'),5))",
        )


if __name__ == "__main__":
    unittest.main()
