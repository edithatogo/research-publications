import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.organisation_enrichment import load_reference
from scripts.plan_publication_organisation_backfill import build_plan


class PublicationOrganisationBackfillPlanTests(unittest.TestCase):
    def test_script_direct_invocation_exposes_help_without_repo_pythonpath(self):
        script = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "plan_publication_organisation_backfill.py"
        )
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(script), "--help"],
                cwd=directory,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--input", result.stdout)

    def write_part(
        self,
        root: Path,
        rows: list[dict],
        part: int = 0,
        eligible: int | None = None,
        total: int | None = None,
    ) -> Path:
        path = root / f"part-{part}.json"
        path.write_text(
            json.dumps(
                {
                    "surface": "BrowserOS authenticated SharePoint REST read-only",
                    "list": "synthetic DEV list",
                    "total": len(rows) if total is None else total,
                    "eligible": len(rows) if eligible is None else eligible,
                    "part": part,
                    "rows": rows,
                }
            )
        )
        return path

    def test_explicit_affiliation_plans_only_additive_fields_and_preserves_unknown_dates(
        self,
    ):
        row = {
            "Id": 1,
            "SourceKey": "pubmed:synthetic",
            "CanonicalKey": "PUB:synthetic",
            "AffiliationsRaw": "Cairns Hospital",
            "OrganisationKeys": None,
        }
        reference = load_reference()
        for unit in reference.values():
            unit["_effective_from"] = ""
            unit["_effective_to"] = ""
        with (
            tempfile.TemporaryDirectory() as directory,
            patch(
                "scripts.plan_publication_organisation_backfill.load_reference",
                return_value=reference,
            ),
        ):
            plan = build_plan([self.write_part(Path(directory), [row])])
        self.assertEqual(plan["mode"], "DRY_RUN_ONLY")
        self.assertEqual(plan["candidate_update_count"], 1)
        values = plan["candidate_updates"][0]["fields"]
        self.assertEqual(values["OrganisationKeys"], "chhhs:cairns")
        self.assertEqual(values["OrganisationEffectiveFrom"], "")
        self.assertEqual(values["OrganisationEffectiveTo"], "")
        self.assertEqual(len(values), 8)

    def test_incomplete_or_prepopulated_readback_fails_closed(self):
        row = {
            "Id": 1,
            "SourceKey": "pubmed:synthetic",
            "CanonicalKey": "PUB:synthetic",
            "AffiliationsRaw": "Cairns Hospital",
            "OrganisationKeys": None,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            incomplete = self.write_part(root, [row], eligible=2, total=2)
            with self.assertRaisesRegex(ValueError, "cover every eligible"):
                build_plan([incomplete])
            row["OrganisationKeys"] = "chhhs:cairns"
            populated = self.write_part(root, [row])
            with self.assertRaisesRegex(ValueError, "already populated"):
                build_plan([populated])

    def test_dated_reference_needs_precise_source_interval_before_planning(self):
        reference = load_reference()
        reference["chhhs:cairns"]["_effective_from"] = "2020-07-01"
        base = {
            "Id": 1,
            "SourceKey": "pubmed:synthetic",
            "CanonicalKey": "PUB:synthetic",
            "AffiliationsRaw": "Cairns Hospital",
            "OrganisationKeys": None,
        }
        with (
            tempfile.TemporaryDirectory() as directory,
            patch(
                "scripts.plan_publication_organisation_backfill.load_reference",
                return_value=reference,
            ),
        ):
            path = self.write_part(Path(directory), [base])
            self.assertEqual(build_plan([path])["candidate_update_count"], 0)
            path = self.write_part(
                Path(directory),
                [
                    {
                        **base,
                        "PublicationDateRaw": "2020",
                        "PublicationDatePrecision": "year",
                    }
                ],
            )
            self.assertEqual(build_plan([path])["candidate_update_count"], 0)
            path = self.write_part(
                Path(directory),
                [
                    {
                        **base,
                        "PublicationDateRaw": "2021",
                        "PublicationDatePrecision": "year",
                    }
                ],
            )
            self.assertEqual(build_plan([path])["candidate_update_count"], 1)

    def test_missing_or_invalid_identity_and_evidence_fields_fail_closed(self):
        base = {
            "Id": 1,
            "SourceKey": "pubmed:synthetic",
            "CanonicalKey": "PUB:synthetic",
            "AffiliationsRaw": "Cairns Hospital",
            "OrganisationKeys": None,
        }
        invalid_rows = [
            ({**base, "Id": True}, "positive integer registry ID"),
            ({**base, "Id": 0}, "positive integer registry ID"),
            ({**base, "SourceKey": " "}, "SourceKey and CanonicalKey identity"),
            ({**base, "CanonicalKey": None}, "SourceKey and CanonicalKey identity"),
            (
                {**base, "AffiliationsRaw": ["Cairns Hospital"]},
                "explicit affiliation text",
            ),
            (
                {**base, "OrganisationKeys": 0},
                "already populated or has an invalid value",
            ),
        ]
        for row, message in invalid_rows:
            with (
                self.subTest(row=row),
                tempfile.TemporaryDirectory() as directory,
                self.assertRaisesRegex(ValueError, message),
            ):
                build_plan([self.write_part(Path(directory), [row])])

    def test_invalid_readback_count_or_part_provenance_fails_closed(self):
        row = {
            "Id": 1,
            "SourceKey": "pubmed:synthetic",
            "CanonicalKey": "PUB:synthetic",
            "AffiliationsRaw": "Cairns Hospital",
            "OrganisationKeys": None,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad_count = self.write_part(root, [row])
            payload = json.loads(bad_count.read_text())
            payload["eligible"] = True
            bad_count.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "valid list/count provenance"):
                build_plan([bad_count])

            bad_part = self.write_part(root, [row])
            payload = json.loads(bad_part.read_text())
            payload["part"] = False
            bad_part.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "consecutive and ordered"):
                build_plan([bad_part])


if __name__ == "__main__":
    unittest.main()


class OrganisationDiagnosticBoundaryTests(unittest.TestCase):
    write_part = PublicationOrganisationBackfillPlanTests.write_part

    def row(self):
        return {
            "Id": 1,
            "SourceKey": "dora:legacy",
            "CanonicalKey": "PUB:stable",
            "AffiliationsRaw": "Cairns Hospital",
            "OrganisationKeys": None,
            "PublicationDate": None,
            "PublicationDatePrecision": "unknown",
            "ReviewNotes": "Keep all wording",
            "OtherSourceField": {"keep": [1, None]},
        }

    def test_unknown_dates_and_original_values_survive_without_native_contract(self):
        row = self.row()
        with tempfile.TemporaryDirectory() as directory:
            plan = build_plan([self.write_part(Path(directory), [row])])
        self.assertEqual(plan["original_rows"], [row])
        self.assertEqual(plan["candidate_update_count"], 0)
        self.assertFalse(plan["native_field_contract_qualified"])
        self.assertEqual(
            plan["native_field_contract_dependency"],
            "config/publication-organisation-fields.schema.json",
        )
        self.assertFalse(plan["write_authorized"])
        self.assertFalse(plan["review_authority"])
        self.assertFalse(plan["routine_admission_prerequisite"])

    def test_partial_manual_attribution_and_whitespace_are_never_overwritten(self):
        for field, value in [
            ("OrganisationEvidence", "Human review"),
            ("OrganisationKeys", " "),
            ("OrganisationEffectiveFrom", "2001-01-01"),
        ]:
            row = self.row()
            row[field] = value
            with tempfile.TemporaryDirectory() as directory, self.subTest(field=field):
                path = self.write_part(Path(directory), [row])
                with self.assertRaisesRegex(ValueError, "already populated"):
                    build_plan([path])

    def test_declared_readback_error_cannot_become_an_empty_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_part(Path(directory), [self.row()])
            payload = json.loads(path.read_text())
            payload["error"] = {}
            path.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                build_plan([path])


if __name__ == "__main__":
    unittest.main()
