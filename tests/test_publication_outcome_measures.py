import base64
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_publication_outcome_measures import PATH, MEASURES, prepare, reference_counts, add_comparison_parameter, COMPARISON_PATH


class PublicationOutcomesTests(unittest.TestCase):
    def test_missing_conflicting_unrecognised_and_undated_are_unknown(self):
        rows = [
            {"CanonicalKey": key, "Status": status, "ObservedUTC": when}
            for key, status, when in [
                ("open", "green", "2026-10-01"),
                ("open", "green", "2026-10-01"),
                ("closed", "closed", "2026-10-01"),
                ("conflict", "green", "2026-10-01"),
                ("conflict", "closed", "2026-10-01"),
                ("undated", "gold", None),
                ("unrecognised", "new-provider-status", "2026-10-01"),
                ("outside", "gold", "2026-10-01"),
            ]]
        actual = reference_counts(
            ["open", "closed", "conflict", "undated", "unrecognised", "absent"], rows)
        self.assertEqual(actual, {"Included": 6, "Assessed": 2, "Open": 1,
                                  "Closed": 1, "Unknown": 4, "Rate": .5,
                                  "Coverage": 1 / 3})
        self.assertEqual(reference_counts(["absent"], rows)["Rate"], None)
        self.assertEqual(reference_counts([], rows)["Coverage"], None)

    def test_filter_context_and_normalisation_do_not_multiply_works(self):
        rows = [{"CanonicalKey": "a", "Status": s, "ObservedUTC": "2026-10-01"}
                for s in [" GOLD ", "gold"]]
        self.assertEqual(reference_counts(["a", "a"], rows)["Open"], 1)
        self.assertEqual(reference_counts(["b"], rows)["Unknown"], 1)
        with self.assertRaises(ValueError):
            reference_counts([""], rows)

    @staticmethod
    def fixture():
        publication = ("table Publication\n\tlineageTag: retained-table-id\n\n\tmeasure Publications = 1\n"
                       "\tmeasure 'Publications Last Complete Month' = 1\n"
                       "\tmeasure 'Publications Last 24 Complete Months' = 1\n"
                       "\tmeasure 'Publications Without Usable Month' = 0\n"
                       "\tcolumn SourceSet\n"
                       "\tpartition Publication = m\n\t\tsource = KeepOriginal\n")
        context = "table OpenAlexPublicationContext\n" + "".join(
            "\tcolumn " + n + "\n" for n in
            ["CanonicalKey", "OpenAccessStatus_OpenAlex", "OpenAccessStatus_OpenAlex_ObservedUTC"])
        parts = [{"path": path, "payload": base64.b64encode(value.encode()).decode(),
                  "payloadType": "InlineBase64"} for path, value in
                 [(PATH, publication),
                  ("definition/tables/OpenAlexPublicationContext.tmdl", context),
                  ("definition/relationships.tmdl", "retain relationship bytes\r\n"),
                  ("definition/model.tmdl", "model Model\n\nref table Publication\n"),
                  ("definition/tables/Facility.tmdl", "table Facility\n\tcolumn FacilityName\n")]]
        return json.dumps({"definition": {"parts": parts}}).encode(), publication

    def test_exact_preimage_additive_preservation_and_replay_refusal(self):
        raw, original = self.fixture()
        result = prepare(raw, hashlib.sha256(raw).hexdigest())
        old = json.loads(raw)["definition"]["parts"]
        self.assertEqual(result["parts"][1:], old[1:])
        text = base64.b64decode(result["parts"][0]["payload"]).decode()
        for name in MEASURES:
            self.assertEqual(text.count("\tmeasure '" + name + "' ="), 1)
        # Original member bytes and partition remain a contiguous suffix.
        offset = original.index("\tmeasure Publications")
        self.assertTrue(text.startswith(original[:offset]))
        self.assertTrue(text.endswith(original[offset:]))
        self.assertLess(text.index("\tlineageTag: retained-table-id"), text.index("\tmeasure 'K02"))
        repeated = json.dumps({"definition": result}).encode()
        with self.assertRaisesRegex(ValueError, "Existing outcome measure"):
            prepare(repeated, hashlib.sha256(repeated).hexdigest())
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            prepare(raw, "0" * 64)

    def test_missing_native_contract_is_not_silently_substituted(self):
        raw, _ = self.fixture()
        value = json.loads(raw)
        value["definition"]["parts"].pop(1)
        raw = json.dumps(value).encode()
        with self.assertRaisesRegex(ValueError, "OA context missing"):
            prepare(raw, hashlib.sha256(raw).hexdigest())

    def test_incremental_adoption_preserves_previously_installed_measures(self):
        raw, _ = self.fixture()
        first = prepare(raw, hashlib.sha256(raw).hexdigest(), only=["K01 Publications in complete months"])
        first_raw = json.dumps({"definition": first}).encode()
        second = prepare(first_raw, hashlib.sha256(first_raw).hexdigest(),
                         only=[n for n in MEASURES if n.startswith("K02")])
        text = base64.b64decode(second["parts"][0]["payload"]).decode()
        self.assertEqual(text.count("measure 'K01 Publications in complete months'"), 1)
        for name in MEASURES:
            self.assertEqual(text.count("measure '" + name + "'"), 1)
        for selection in [[], ["unknown"], ["K02 Known open publications"] * 2]:
            with self.assertRaises(ValueError):
                prepare(raw, hashlib.sha256(raw).hexdigest(), only=selection)

    def test_comparison_parameter_adds_only_table_and_model_reference(self):
        raw, _ = self.fixture()
        original = json.loads(raw)["definition"]
        result = add_comparison_parameter(original)
        old = {p["path"]: p for p in original["parts"]}
        new = {p["path"]: p for p in result["parts"]}
        self.assertEqual(set(new) - set(old), {COMPARISON_PATH})
        self.assertEqual([p for p in old if old[p] != new[p]], ["definition/model.tmdl"])
        table = base64.b64decode(new[COMPARISON_PATH]["payload"]).decode()
        self.assertIn('ParameterMetadata = {"version":3,"kind":2}', table)
        self.assertIn("NAMEOF(Facility[FacilityName]), 0", table)
        self.assertIn("NAMEOF(Publication[SourceSet]), 1", table)
        with self.assertRaisesRegex(ValueError, "parameter exists"):
            add_comparison_parameter(result)


if __name__ == "__main__":
    unittest.main()
