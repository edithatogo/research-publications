"""Reject partial/error-bearing cycles without changing the accepted state."""

import copy
import unittest

from scripts.publication_policy import evaluate, validate_policy
from scripts.publication_retained_cycle import retain, validate_state
from scripts.publication_source_metadata_contract import _page_rows
from tests import test_prepare_dora_metadata_cycle as fixtures


class CycleBoundaryTests(unittest.TestCase):
    def test_invalid_empty_cycle_cannot_bypass_identity_and_state_checks(self):
        for state, generation, source in (
            ({}, "one", "PubMed"),
            (None, True, "PubMed"),
            (None, " one ", "PubMed"),
            (None, "one", "other"),
        ):
            with (
                self.subTest(state=state, generation=generation, source=source),
                self.assertRaises(ValueError),
            ):
                retain(
                    state,
                    [],
                    generation=generation,
                    observed_at="2026-10-29T00:00:00Z",
                    source=source,
                    complete=True,
                )

    def test_malformed_policy_shape_fails_closed(self):
        for policy in (None, [], "policy", True, {}):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                validate_policy(policy)

    def test_lost_cycle_and_cycle_key_reassignment_are_rejected(self):
        state = retain(
            None,
            [("123", {"Title": "Keep"})],
            generation="one",
            observed_at="2026-10-29T00:00:00Z",
            source="PubMed",
            complete=True,
        )
        for change in ("lost", "keys", "duplicate", "kind"):
            changed = copy.deepcopy(state)
            if change == "lost":
                changed["cycles"] = []
            elif change == "keys":
                changed["cycles"][0]["keys"] = []
            elif change == "duplicate":
                changed["cycles"].append(copy.deepcopy(changed["cycles"][0]))
            else:
                changed["kind"] = "unqualified"
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_state(changed)
            self.assertEqual(state["versions"][0]["Record"]["Title"], "Keep")

    def test_publication_policy_preserves_reviewed_values_and_temporal_uncertainty(
        self,
    ):
        original = {
            "Title": "Keep",
            "AffiliationsRaw": "Cairns Hospital",
            "OrganisationKeys": "reviewed:other",
            "OrganisationEvidence": "Human review",
        }
        output = evaluate("PubMed", "123", original)
        self.assertEqual(output["Record"], original)
        self.assertEqual(output["OrganisationKeys"], "reviewed:other")
        undated = evaluate("PubMed", "123", {"AffiliationsRaw": "Cairns Hospital"})
        self.assertEqual(undated["AffiliationAttribution"], "undetermined")
        self.assertIn("affiliation-unconfirmed", undated["UncertaintyFlags"])
        self.assertEqual(undated["RegistryDisposition"], "Included")

    def test_nested_page_error_envelopes_and_boolean_page_numbers_rejected(self):
        fixture = fixtures.DoraMetadataCycleTests()
        fixture.setUp()
        for level in ("body", "result", "table", "number"):
            pages, _ = fixture.inputs()
            source = pages["sources"]["DoraPublications"]
            page = source["pages"][0]
            if level == "number":
                page["page_number"] = False
            else:
                body = page["body"]
                node = (
                    body
                    if level == "body"
                    else body["results"][0]
                    if level == "result"
                    else body["results"][0]["tables"][0]
                )
                node["error"] = {}
            with self.subTest(level=level), self.assertRaises(ValueError):
                _page_rows(source, "DoraPublications", ("DORAKey",))

    def test_validation_error_cannot_hide_behind_passing_counts(self):
        from scripts.prepare_dora_metadata_cycle import prepare

        fixture = fixtures.DoraMetadataCycleTests()
        fixture.setUp()
        before = copy.deepcopy(fixture.state)
        for level in ("body", "result", "table"):
            pages, validation = fixture.inputs()
            body = validation["body"]
            node = (
                body
                if level == "body"
                else body["results"][0]
                if level == "result"
                else body["results"][0]["tables"][0]
            )
            node["error"] = {}
            with self.subTest(level=level), self.assertRaises(ValueError):
                prepare(pages, fixture.generation, validation, fixture.state)
            self.assertEqual(fixture.state, before)
