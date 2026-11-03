import unittest
import json
import hashlib
import tempfile
from pathlib import Path
try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:  # Optional test extra; runtime has no third-party dependencies.
    Draft202012Validator = FormatChecker = None

from scripts.grants_universities import (
    load_universities, reconcile_institution_facts, reconcile_receipted_institution_fact,
    validate_reviewed_fact_receipt,
    prepare_reviewed_institution_import,
)
from scripts.grants_registry import stable_key


class GrantsUniversityTests(unittest.TestCase):
    def preparation_inputs(self):
        catalogue, _, factory = self.synthetic_inputs()
        row = {"Source": "funder", "SourceID": "round-1", "Title": "Synthetic grant",
               "URL": "https://funder.example/round-1", "Deadline": "2027-06-30",
               "RetrievedUTC": "2026-09-25T10:00:00Z", "ReviewStatus": "Reviewed",
               "ReviewNotes": "Synthetic official funder observation"}
        receipts = []
        for institution in ("uq", "jcu"):
            receipt = self.reviewed_receipt()
            receipt["receipt_id"] += institution
            receipt["fact"] = factory(institution, OpportunityKey=stable_key(row))
            receipt["fact_sha256"] = hashlib.sha256(json.dumps(
                receipt["fact"], ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()
            receipt["evidence"].update(url=receipt["fact"]["evidence_url"])
            receipts.append(receipt)
        return row, receipts, catalogue

    def prepare(self, row, receipts, catalogue, **kwargs):
        return prepare_reviewed_institution_import(
            [row], receipts, catalogue, expected_source="funder",
            official_hosts={"funder.example"}, **kwargs)

    def test_prepare_reviewed_import_preserves_canonical_and_institution_facts(self):
        row, receipts, catalogue = self.preparation_inputs()
        before = json.dumps([row, receipts, catalogue], sort_keys=True)
        result = self.prepare(row, receipts, catalogue,
                              verify_evidence=lambda _: True, verify_reviewer=lambda _: True)
        self.assertFalse(result["imported"])
        self.assertEqual(result["intake"], "manual_review")
        self.assertEqual(result["feed_rights"], "unverified")
        self.assertEqual(len(result["opportunities"]), 1)
        self.assertEqual(len(result["institution_facts"]), 2)
        for fact in result["institution_facts"]:
            self.assertEqual(fact["OpportunityKey"], stable_key(row))
            self.assertEqual(fact["external_deadline"], "2027-06-30")
            self.assertEqual(len(fact["internal_deadlines"]), 2)
            self.assertIsNone(fact["policy_provenance"]["timezone"])
            self.assertEqual(fact["institutional_eligibility"]["status"], "restricted")
            self.assertTrue(fact["ReviewReceiptFactSHA256"])
        self.assertEqual(before, json.dumps([row, receipts, catalogue], sort_keys=True))
        replay = self.prepare(row, reversed(receipts), catalogue,
                              verify_evidence=lambda _: True, verify_reviewer=lambda _: True)
        self.assertEqual(result, replay)

    def test_prepare_reviewed_import_fails_closed_at_both_boundaries(self):
        row, receipts, catalogue = self.preparation_inputs()
        with self.assertRaisesRegex(ValueError, "artifact is unverified"):
            self.prepare(row, receipts, catalogue)
        row["OpportunityKey"] = "GRANT:" + "a" * 24
        with self.assertRaisesRegex(ValueError, "OpportunityKey_mismatch"):
            self.prepare(row, receipts, catalogue,
                         verify_evidence=lambda _: True, verify_reviewer=lambda _: True)

    def test_prepare_reviewed_import_rejects_unresolved_rights_and_duplicate_facts(self):
        for change, message in (({"format": "rss"}, "machine feed rights"),
                                ({"format": "pdf"}, "format is unsupported"),
                                ({"entitlement_status": "revoked"}, "revoked entitlement"),
                                ({"eligibility": {"status": "unknown", "restrictions": []}},
                                 "manual resolution")):
            row, receipts, catalogue = self.preparation_inputs()
            receipts[0]["fact"].update(change)
            receipts[0]["fact_sha256"] = hashlib.sha256(json.dumps(
                receipts[0]["fact"], ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()
            receipts[0]["evidence"]["format"] = receipts[0]["fact"]["format"]
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, message):
                self.prepare(row, receipts, catalogue,
                             verify_evidence=lambda _: True, verify_reviewer=lambda _: True)
        row, receipts, catalogue = self.preparation_inputs()
        with self.assertRaisesRegex(ValueError, "duplicate reviewed fact receipt"):
            self.prepare(row, [receipts[0], receipts[0]], catalogue,
                         verify_evidence=lambda _: True, verify_reviewer=lambda _: True)

    @staticmethod
    def synthetic_inputs():
        catalogue = [
            {"institution_id": "uq", "authority_url": "https://research-support.uq.edu.au/policy"},
            {"institution_id": "jcu", "authority_url": "https://www.jcu.edu.au/policy"},
        ]
        opportunities = [{"OpportunityKey": "GRANT:0123456789abcdef01234567", "Deadline": "2027-06-30"}]
        def fact(institution_id, **changes):
            row = {
                "fact_id": "case-1", "institution_id": institution_id,
                "OpportunityKey": "GRANT:0123456789abcdef01234567", "entitlement_status": "verified_active",
                "format": "csv", "evidence_url": ("https://research-support.uq.edu.au/policy/round-1" if institution_id == "uq"
                                                      else "https://www.jcu.edu.au/policy/round-1"),
                "observed_at": "2026-09-25T10:00:00+10:00", "review_status": "Reviewed",
                "eligibility": {"status": "restricted", "restrictions": ["affiliated researchers only"]},
                "policy_provenance": {"status": "public_summary_unversioned", "version": None,
                                      "effective_from": None, "timezone": None},
                "internal_deadlines": [
                    {"deadline_id": "faculty", "kind": "internal_close", "date": "2027-06-10", "label": "Faculty review"},
                    {"deadline_id": "research-office", "kind": "internal_submission", "date": "2027-06-20", "label": "Research Office submission"},
                ],
            }
            row.update(changes)
            return row
        return catalogue, opportunities, fact

    def reviewed_receipt(self):
        _, _, fact_factory = self.synthetic_inputs()
        fact = fact_factory("uq")
        canonical = json.dumps(fact, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        return {
            "schema_version": "g05-reviewed-fact-receipt/v1",
            "receipt_id": "G05R-20260925-UQ-0001",
            "fact": fact,
            "fact_sha256": hashlib.sha256(canonical).hexdigest(),
            "evidence": {
                "url": fact["evidence_url"], "format": fact["format"],
                "observed_at": fact["observed_at"],
                "private_ref": "private/ops/synthetic-policy-evidence.html",
                "sha256": "a" * 64,
            },
            "reviewer": {
                "reviewer_id": "reviewer-123", "reviewed_at": "2026-09-25T12:00:00+10:00",
                "decision": "Reviewed", "notes": "Synthetic fixture review",
                "verification_ref": "private/ops/synthetic-reviewer-verification.json",
            },
        }

    def test_required_university_sources_are_explicitly_manual_until_access_proven(self):
        rows = load_universities(Path(__file__).parents[1] / "config/grants-universities.json")
        self.assertEqual({row["institution_id"] for row in rows}, {"jcu", "uq", "qut", "griffith"})
        self.assertTrue(all(row["intake"] == "manual_review" for row in rows))

    def test_last_verified_covers_latest_recorded_source_evidence(self):
        path = Path(__file__).parents[1] / "config/grants-universities.json"
        rows = load_universities(path)
        by_id = {row["institution_id"]: row for row in rows}
        self.assertEqual(by_id["jcu"]["last_verified"], "2026-10-23")
        for institution_id in ("uq", "qut"):
            self.assertEqual(by_id[institution_id]["last_verified"], "2026-10-23")
        self.assertEqual(by_id["griffith"]["last_verified"], "2026-11-03")
        # A failed fetch must not silently refresh the evidence date.
        jcu_evidence = by_id["jcu"]["source_evidence"]
        self.assertEqual([item["observed_on"] for item in jcu_evidence
                      if item["claim"] == "lead_time_and_submission_route"], ["2026-10-07"])
        self.assertEqual([item["observed_on"] for item in jcu_evidence
                      if item["claim"] == "lead_time_and_submission_route_2026_10_23_recheck"],
                    ["2026-10-23"])
        uq_evidence = by_id["uq"]["source_evidence"]
        self.assertEqual([item["observed_on"] for item in uq_evidence
                          if item["claim"] == "scheme_specific_myresearch_certification_transition"],
                    ["2026-10-03"])
        self.assertEqual([item["observed_on"] for item in uq_evidence
                          if item["claim"] == "governing_policy_status"], ["2026-10-07"])
        self.assertEqual(
            [item["observed_on"] for item in uq_evidence
             if item["claim"] == "governing_policy_status_2026_10_23_recheck"],
            ["2026-10-23"],
        )
        self.assertEqual(
            [item["version"] for item in uq_evidence
             if item["claim"] == "governing_policy_status_2026_10_23_recheck"],
            ["3"],
        )
        griffith_evidence = by_id["griffith"]["source_evidence"]
        self.assertEqual(
            [item["observed_on"] for item in griffith_evidence
             if item["claim"] == "scheme_specific_2026_call_and_expired_internal_deadline"],
            ["2026-09-25"],
        )
        self.assertEqual(
            [item["observed_on"] for item in griffith_evidence
             if item["claim"] == "griffith_wun_internal_selection_elapsed_while_page_labels_call_open"],
            ["2026-10-07"],
        )
        self.assertEqual(
            [item["observed_on"] for item in griffith_evidence
             if item["claim"] == "research_grants_support_access_scope"],
            ["2026-10-07"],
        )
        self.assertEqual(
            [item["observed_on"] for item in griffith_evidence
             if item["claim"] == "research_grants_support_access_scope_2026_10_23_recheck"],
            ["2026-10-23"],
        )
        self.assertEqual(
            [item["observed_on"] for item in griffith_evidence
             if item["claim"] == "griffith_wun_rdf_2026_call_now_closed"],
            ["2026-10-23"],
        )
        self.assertEqual(
            [item["version"] for item in griffith_evidence
             if item["claim"] == "griffith_wun_rdf_2026_call_now_closed"],
            ["2026 call"],
        )
        self.assertEqual(
            [item["observed_on"] for item in griffith_evidence
             if item["claim"] == "griffith_staff_wun_knowledge_exchange_round1_2026_dates"],
            ["2026-10-23"],
        )
        self.assertIn("call is closed", by_id["griffith"]["policy_note"])
        self.assertIn("open 2026-11-02", by_id["griffith"]["policy_note"])
        self.assertIn("close 2026-11-23", by_id["griffith"]["policy_note"])

        stale = json.loads(path.read_text(encoding="utf-8"))
        stale[0]["last_verified"] = "2026-09-25"
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "universities.json"
            candidate.write_text(json.dumps(stale), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "last_verified predates source evidence"):
                load_universities(candidate)

    def test_published_deadlines_keep_their_units_and_qualifiers(self):
        rows = load_universities(Path(__file__).parents[1] / "config/grants-universities.json")
        by_id = {row["institution_id"]: row for row in rows}
        self.assertEqual(by_id["jcu"]["internal_lead_time"]["major_arc_nhmrc"], {
            "value": 4, "unit": "weeks", "qualifier": "generally; verify scheme-specific instructions"})
        self.assertEqual(by_id["jcu"]["internal_lead_time"]["other_australian"]["value"], 1)
        self.assertEqual(by_id["uq"]["internal_lead_time"]["standard"], {"value": 10, "unit": "working_days"})
        self.assertEqual(by_id["uq"]["internal_lead_time"]["major_high_volume_or_strategic"], {
            "value": 4, "unit": "weeks", "qualifier": "up to; scheme-specific"})
        self.assertIsNone(by_id["qut"]["internal_lead_time"])
        self.assertIsNone(by_id["griffith"]["internal_lead_time"])

    def test_policy_provenance_keeps_unversioned_summaries_distinct_from_verified_policy(self):
        rows = load_universities(Path(__file__).parents[1] / "config/grants-universities.json")
        by_id = {row["institution_id"]: row for row in rows}
        self.assertEqual(by_id["jcu"]["policy_provenance"], {
            "status": "public_summary_unversioned", "version": None,
            "effective_from": None, "timezone": None,
        })
        self.assertEqual(by_id["qut"]["policy_provenance"], {
            "status": "verified_versioned", "version": "4",
            "effective_from": "2025-11-07", "timezone": None})
        self.assertEqual(by_id["griffith"]["policy_provenance"], {
            "status": "verified_current_unversioned", "version": None,
            "effective_from": "2025-01-01", "timezone": None})
        self.assertEqual(by_id["griffith"]["intake"], "manual_review")

    def test_current_unversioned_catalogue_policy_requires_exact_current_evidence(self):
        source = Path(__file__).parents[1] / "config/grants-universities.json"
        for mutation in ("missing", "wrong_url", "stale", "invented_version", "wrong_effective", "future_effective"):
            rows = json.loads(source.read_text(encoding="utf-8"))
            row = next(item for item in rows if item["institution_id"] == "griffith")
            item = next(item for item in row["source_evidence"] if item["claim"] == "publisher_current_policy_search")
            if mutation == "missing":
                row["source_evidence"].remove(item)
            elif mutation == "wrong_url":
                item["url"] = "https://www.griffith.edu.au/"
            elif mutation == "stale":
                item["observed_on"] = "2026-10-30"
            elif mutation == "invented_version":
                row["policy_provenance"]["version"] = "2024/0001156"
            elif mutation == "wrong_effective":
                row["policy_provenance"]["effective_from"] = "2024-01-01"
            else:
                row["policy_provenance"]["effective_from"] = "2027-01-01"
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                candidate = Path(directory) / "universities.json"
                candidate.write_text(json.dumps(rows), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_universities(candidate)

    def test_current_unversioned_catalogue_status_does_not_admit_facts(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        row = fact("uq")
        row["policy_provenance"] = {"status": "verified_current_unversioned", "version": None,
                                    "effective_from": "2025-01-01", "timezone": None}
        with self.assertRaises(ValueError):
            reconcile_institution_facts(opportunities, [row], catalogue)
        row = fact("griffith")
        row["evidence_url"] = "https://policies.griffith.edu.au/"
        with self.assertRaises(ValueError):
            reconcile_institution_facts(opportunities, [row], catalogue)

    def test_internal_deadline_preserves_local_time_and_unknown_timezone(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        row = fact("uq")
        row["internal_deadlines"] = [{"deadline_id": "office", "kind": "internal_close",
            "date": "2027-06-20", "time": "17:00", "timezone": None, "label": "Research Office close"}]
        result = reconcile_institution_facts(opportunities, [row], catalogue)[0]
        self.assertEqual(result["internal_deadlines"][0]["time"], "17:00")
        self.assertIsNone(result["internal_deadlines"][0]["timezone"])

    def test_internal_deadline_rejects_invalid_local_time(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        row = fact("uq")
        row["internal_deadlines"][0]["time"] = "25:00"
        with self.assertRaisesRegex(ValueError, "HH:MM"):
            reconcile_institution_facts(opportunities, [row], catalogue)

    def test_internal_deadline_requires_canonical_calendar_date(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        for value in ("20270610", "2027-W24-4", "2027-06-10T00:00:00Z"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "full ISO date"):
                reconcile_institution_facts(
                    opportunities,
                    [fact("uq", internal_deadlines=[{
                        "deadline_id": "faculty", "kind": "internal_close", "date": value,
                    }])],
                    catalogue,
                )

    def test_catalogue_rejects_claimed_versioned_policy_without_effective_date(self):
        path = Path(__file__).parents[1] / "config/grants-universities.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        rows[0]["policy_provenance"] = {
            "status": "verified_versioned", "version": "v1",
            "effective_from": None, "timezone": None,
        }
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "universities.json"
            candidate.write_text(json.dumps(rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "needs version and effective date"):
                load_universities(candidate)

    def test_catalogue_rejects_padded_policy_and_source_evidence_versions(self):
        source = Path(__file__).parents[1] / "config/grants-universities.json"
        for field in ("policy", "source_evidence"):
            rows = json.loads(source.read_text(encoding="utf-8"))
            qut = next(row for row in rows if row["institution_id"] == "qut")
            if field == "policy":
                qut["policy_provenance"]["version"] = " 4 "
            else:
                evidence = next(item for item in qut["source_evidence"]
                                if item["version"] is not None)
                evidence["version"] = f" {evidence['version']} "
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                candidate = Path(directory) / "universities.json"
                candidate.write_text(json.dumps(rows), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "version"):
                    load_universities(candidate)

    def test_catalogue_rejects_evidence_outside_the_institution_authority(self):
        path = Path(__file__).parents[1] / "config/grants-universities.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        rows[0]["source_evidence"][0]["url"] = "https://example.org/policy"
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "universities.json"
            candidate.write_text(json.dumps(rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "official HTTPS HTML page"):
                load_universities(candidate)

    def test_catalogue_rejects_authority_url_outside_the_institution_domain(self):
        path = Path(__file__).parents[1] / "config/grants-universities.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        rows[0]["authority_url"] = "https://example.org/research"
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "universities.json"
            candidate.write_text(json.dumps(rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "official authority URL"):
                load_universities(candidate)

    def test_catalogue_dates_require_canonical_full_iso_calendar_days(self):
        source = Path(__file__).parents[1] / "config/grants-universities.json"
        original = json.loads(source.read_text(encoding="utf-8"))
        candidates = []
        bad_last_verified = json.loads(json.dumps(original))
        bad_last_verified[0]["last_verified"] = "20260928"
        candidates.append(bad_last_verified)
        bad_effective_from = json.loads(json.dumps(original))
        versioned = next(row for row in bad_effective_from
                         if row["policy_provenance"]["status"] == "verified_versioned")
        versioned["policy_provenance"]["effective_from"] = "2025-W45-5"
        candidates.append(bad_effective_from)
        bad_observed_on = json.loads(json.dumps(original))
        bad_observed_on[0]["source_evidence"][0]["observed_on"] = "20260928"
        candidates.append(bad_observed_on)
        for rows in candidates:
            with self.subTest(rows=rows[0]["last_verified"]), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "universities.json"
                path.write_text(json.dumps(rows), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
                    load_universities(path)

    def test_catalogue_rejects_mixed_or_invented_lead_time_units(self):
        path = Path(__file__).parents[1] / "config/grants-universities.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        rows[0]["internal_lead_time"]["major_arc_nhmrc"]["unit"] = "business_days"
        rows[0]["internal_lead_time"]["major_arc_nhmrc"]["value"] = True
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "universities.json"
            candidate.write_text(json.dumps(rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-negative integers"):
                load_universities(candidate)

    def test_same_canonical_opportunity_retains_institution_scoped_restrictions_and_deadlines(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        records = reconcile_institution_facts(
            opportunities, [fact("uq"), fact("jcu", fact_id="case-2")], catalogue)
        self.assertEqual(len(records), 2)
        self.assertEqual({row["OpportunityKey"] for row in records}, {"GRANT:0123456789abcdef01234567"})
        uq = next(row for row in records if row["institution_id"] == "uq")
        self.assertEqual(uq["external_deadline"], "2027-06-30")
        self.assertEqual([row["date"] for row in uq["internal_deadlines"]], ["2027-06-10", "2027-06-20"])
        self.assertEqual(uq["institutional_eligibility"]["restrictions"], ["affiliated researchers only"])

    def test_canonical_opportunity_keys_must_use_stable_registry_format(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        for invalid in ("GRANT:synthetic-1", "grant:0123456789abcdef01234567",
                        "GRANT:0123456789ABCDEF01234567"):
            with self.subTest(key=invalid), self.assertRaisesRegex(ValueError, "invalid stable OpportunityKey"):
                malformed = [{**opportunities[0], "OpportunityKey": invalid}]
                reconcile_institution_facts(malformed, [fact("uq")], catalogue)

    def test_institutional_fact_identity_and_evidence_fields_reject_coercion(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        cases = [
            ({"institution_id": 7}, "institution_id"),
            ({"OpportunityKey": {"key": "GRANT:synthetic-1"}}, "OpportunityKey"),
            ({"fact_id": 1}, "fact_id"),
            ({"format": ["csv"]}, "format"),
            ({"review_status": 1}, "review_status"),
            ({"entitlement_status": ["public"]}, "entitlement status"),
            ({"internal_deadlines": [{"deadline_id": 1, "kind": "internal_close", "date": "2027-06-10"}]}, "deadline_id"),
            ({"internal_deadlines": [{"deadline_id": "faculty", "kind": ["internal_close"], "date": "2027-06-10"}]}, "deadline kind"),
            ({"internal_deadlines": [{"deadline_id": "faculty", "kind": "internal_close", "date": 20270610}]}, "full ISO date"),
            ({"internal_deadlines": [{"deadline_id": "faculty", "kind": "internal_close", "date": "2027-06-10", "label": 42}]}, "label must be text"),
        ]
        for changes, message in cases:
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, message):
                malformed = fact("uq")
                malformed.update(changes)
                reconcile_institution_facts(opportunities, [malformed], catalogue)

    def test_padded_stable_identities_are_rejected_not_normalized(self):
        catalogue, opportunities, make_fact = self.synthetic_inputs()
        valid = make_fact("uq")
        cases = [
            ([{**opportunities[0], "OpportunityKey": f" {opportunities[0]['OpportunityKey']}"}],
             [valid], "OpportunityKey must not include surrounding whitespace"),
            (opportunities, [{**valid, "institution_id": " uq"}],
             "institution_id must not include surrounding whitespace"),
            (opportunities, [{**valid, "fact_id": "fact-1 "}],
             "fact_id must not include surrounding whitespace"),
            (opportunities, [{**valid, "internal_deadlines": [{
                **valid["internal_deadlines"][0], "deadline_id": " office"}]}],
             "deadline_id must not include surrounding whitespace"),
        ]
        for candidate_opportunities, facts, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                reconcile_institution_facts(candidate_opportunities, facts, catalogue)

    def test_fact_and_eligibility_shapes_reject_unknown_fields(self):
        catalogue, opportunities, make_fact = self.synthetic_inputs()
        fact = make_fact("uq")
        with self.assertRaisesRegex(ValueError, "unknown or missing fields"):
            reconcile_institution_facts(opportunities, [{**fact, "eligiblity": fact["eligibility"]}], catalogue)
        malformed = make_fact("uq")
        malformed["eligibility"] = {**malformed["eligibility"], "basis": "not a contract field"}
        with self.assertRaisesRegex(ValueError, "exact eligibility fields"):
            reconcile_institution_facts(opportunities, [malformed], catalogue)

    def test_university_catalogue_rejects_non_object_and_coerced_identity(self):
        source = Path(__file__).parents[1] / "config/grants-universities.json"
        rows = json.loads(source.read_text(encoding="utf-8"))
        for candidate, message in (([None, *rows[1:]], "row 0 must be an object"),
                                   ([{**rows[0], "institution_id": 7}, *rows[1:]], "institution_id must be non-empty text")):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "universities.json"
                path.write_text(json.dumps(candidate), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    load_universities(path)

    def test_duplicate_catalogue_identity_cannot_shadow_authority(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        conflicting = [catalogue[0], {**catalogue[0], "authority_url": "https://attacker.example"}]
        with self.assertRaisesRegex(ValueError, "duplicate or missing identity"):
            reconcile_institution_facts(opportunities, [fact("uq")], conflicting)

    def test_revoked_entitlement_is_rejected(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        with self.assertRaisesRegex(ValueError, "revoked entitlement"):
            reconcile_institution_facts(opportunities, [fact("uq", entitlement_status="revoked")], catalogue)

    def test_unsupported_format_is_rejected(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        with self.assertRaisesRegex(ValueError, "unsupported format"):
            reconcile_institution_facts(opportunities, [fact("uq", format="screen-scrape")], catalogue)

    def test_ambiguous_eligibility_is_not_promoted(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        with self.assertRaisesRegex(ValueError, "eligibility requires manual resolution"):
            reconcile_institution_facts(opportunities, [fact("uq", eligibility={"status": "ambiguous", "restrictions": []})], catalogue)

    def test_restricted_eligibility_requires_preserved_restriction_text(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        with self.assertRaisesRegex(ValueError, "restricted eligibility needs explicit restrictions"):
            reconcile_institution_facts(opportunities, [fact("uq", eligibility={"status": "restricted", "restrictions": []})], catalogue)

    def test_unversioned_policy_facts_cannot_gain_invented_version_timezone_or_dates(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        with self.assertRaisesRegex(ValueError, "cannot invent unversioned policy details"):
            reconcile_institution_facts(opportunities, [fact("uq", policy_provenance={
                "status": "public_summary_unversioned", "version": "v2",
                "effective_from": None, "timezone": None})], catalogue)

    def test_versioned_policy_effective_date_requires_full_iso_date(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        for invalid in ("2026-W40-1", "20261001", "2026-10-1"):
            with self.subTest(effective_from=invalid), self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
                row = fact("uq")
                row["policy_provenance"] = {
                    "status": "verified_versioned", "version": "v1",
                    "effective_from": invalid, "timezone": None}
                reconcile_institution_facts(opportunities, [row], catalogue)
        row = fact("uq")
        row["policy_provenance"] = {
            "status": "verified_versioned", "version": "v1",
            "effective_from": "2026-10-01", "timezone": None}
        self.assertTrue(reconcile_institution_facts(opportunities, [row], catalogue))

    def test_versioned_policy_fact_rejects_padded_version_identity(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        row = fact("uq", policy_provenance={
            "status": "verified_versioned", "version": " v1 ",
            "effective_from": "2026-10-01", "timezone": None})
        with self.assertRaisesRegex(ValueError, "versioned policy needs version"):
            reconcile_institution_facts(opportunities, [row], catalogue)

    def test_multiple_institution_deadlines_cannot_be_collapsed_or_duplicated(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        row = fact("uq")
        row["internal_deadlines"] = [row["internal_deadlines"][0], row["internal_deadlines"][0]]
        with self.assertRaisesRegex(ValueError, "repeats an internal deadline id"):
            reconcile_institution_facts(opportunities, [row], catalogue)

    def test_reviewed_fact_receipt_requires_evidence_and_identity_verifiers(self):
        receipt = self.reviewed_receipt()
        with self.assertRaisesRegex(ValueError, "evidence artifact is unverified"):
            validate_reviewed_fact_receipt(receipt)
        with self.assertRaisesRegex(ValueError, "reviewer identity is unverified"):
            validate_reviewed_fact_receipt(receipt, verify_evidence=lambda _: True)

    def test_reviewed_fact_receipt_cannot_predate_evidence_observation(self):
        receipt = self.reviewed_receipt()
        receipt["reviewer"]["reviewed_at"] = "2026-09-25T09:59:59+10:00"
        with self.assertRaisesRegex(ValueError, "review decision predates observed evidence"):
            validate_reviewed_fact_receipt(receipt, verify_evidence=lambda _: True,
                                           verify_reviewer=lambda _: True)

    def test_reviewed_receipt_and_fact_timestamps_require_strict_offset_instants(self):
        for field, value in (
            ("evidence", "2026-09-25 10:00:00+10:00"),
            ("evidence", "2026-09-25T10:00+10:00"),
            ("reviewer", "2026-09-25T12:00:00"),
        ):
            receipt = self.reviewed_receipt()
            if field == "evidence":
                receipt["evidence"]["observed_at"] = value
                receipt["fact"]["observed_at"] = value
                receipt["fact_sha256"] = hashlib.sha256(json.dumps(
                    receipt["fact"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()).hexdigest()
            else:
                receipt["reviewer"]["reviewed_at"] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, "RFC3339"):
                validate_reviewed_fact_receipt(receipt, verify_evidence=lambda _: True,
                                               verify_reviewer=lambda _: True)

    def test_institution_fact_timestamp_requires_strict_offset_instant(self):
        catalogue, opportunities, fact = self.synthetic_inputs()
        for value in ("2026-09-25 10:00:00+10:00", "2026-09-25T10:00+10:00", "2026-09-25T10:00:00"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "RFC3339"):
                reconcile_institution_facts(opportunities, [fact("uq", observed_at=value)], catalogue)

    def test_verifier_callbacks_receive_receipt_and_fact_binding_context(self):
        receipt = self.reviewed_receipt()
        evidence_claims = []
        reviewer_claims = []
        result = validate_reviewed_fact_receipt(
            receipt,
            verify_evidence=lambda claim: evidence_claims.append(claim) or True,
            verify_reviewer=lambda claim: reviewer_claims.append(claim) or True,
        )
        expected_binding = {"receipt_id": receipt["receipt_id"], "fact_sha256": receipt["fact_sha256"]}
        self.assertEqual({key: evidence_claims[0][key] for key in expected_binding}, expected_binding)
        self.assertEqual(evidence_claims[0]["evidence"], receipt["evidence"])
        self.assertEqual({key: reviewer_claims[0][key] for key in expected_binding}, expected_binding)
        self.assertEqual(reviewer_claims[0]["reviewer"], receipt["reviewer"])
        self.assertEqual(reviewer_claims[0]["verification_ref"], receipt["reviewer"]["verification_ref"])
        self.assertEqual(result["status"], "validated_local_only")

    def test_reviewed_fact_receipt_binds_fact_and_external_evidence(self):
        receipt = self.reviewed_receipt()
        result = validate_reviewed_fact_receipt(
            receipt, verify_evidence=lambda claim: claim["evidence"]["sha256"] == "a" * 64
            and claim["fact_sha256"] == receipt["fact_sha256"]
            and claim["receipt_id"] == receipt["receipt_id"],
            verify_reviewer=lambda claim: claim["reviewer"]["reviewer_id"] == "reviewer-123"
            and claim["verification_ref"] == claim["reviewer"]["verification_ref"]
            and claim["fact_sha256"] == receipt["fact_sha256"]
            and claim["receipt_id"] == receipt["receipt_id"],
        )
        self.assertEqual(result["status"], "validated_local_only")
        self.assertFalse(result["imported"])
        receipt["fact"]["eligibility"]["status"] = "supported"
        with self.assertRaisesRegex(ValueError, "fact hash mismatch"):
            validate_reviewed_fact_receipt(receipt, verify_evidence=lambda _: True,
                                           verify_reviewer=lambda _: True)

    def test_reviewed_fact_receipt_rejects_evidence_rebinding_and_unsafe_paths(self):
        receipt = self.reviewed_receipt()
        receipt["evidence"]["url"] = "https://research-support.uq.edu.au/not-the-observed-page"
        with self.assertRaisesRegex(ValueError, "does not bind"):
            validate_reviewed_fact_receipt(receipt, verify_evidence=lambda _: True,
                                           verify_reviewer=lambda _: True)
        receipt = self.reviewed_receipt()
        receipt["evidence"]["private_ref"] = "private/ops/../raw.html"
        with self.assertRaisesRegex(ValueError, "private/ops evidence"):
            validate_reviewed_fact_receipt(receipt, verify_evidence=lambda _: True,
                                           verify_reviewer=lambda _: True)

    def test_reviewed_fact_receipt_rejects_non_text_evidence_format(self):
        receipt = self.reviewed_receipt()
        receipt["evidence"]["format"] = ["csv"]
        with self.assertRaisesRegex(ValueError, "format is unsupported"):
            validate_reviewed_fact_receipt(receipt, verify_evidence=lambda _: True,
                                           verify_reviewer=lambda _: True)

    @unittest.skipIf(Draft202012Validator is None, "optional jsonschema package is not installed")
    def test_receipt_schema_matches_runtime_contract_and_path_rules(self):
        schema_path = Path(__file__).parents[1] / "contracts/g05-reviewed-fact-receipt.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        receipt = self.reviewed_receipt()
        self.assertEqual(list(validator.iter_errors(receipt)), [])
        grantx = json.loads(json.dumps(receipt))
        grantx["fact"]["OpportunityKey"] = stable_key({"Source": "A:B", "SourceID": "C"})
        grantx["fact_sha256"] = hashlib.sha256(json.dumps(
            grantx["fact"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        self.assertEqual(list(validator.iter_errors(grantx)), [])
        catalogue, opportunities, _ = self.synthetic_inputs()
        for ref in ("private/ops/a..b.html", "private/ops/nested/evidence.html"):
            candidate = json.loads(json.dumps(receipt))
            candidate["evidence"]["private_ref"] = ref
            candidate["reviewer"]["verification_ref"] = ref
            self.assertEqual(list(validator.iter_errors(candidate)), [], ref)
            self.assertEqual(reconcile_receipted_institution_fact(
                candidate, opportunities, catalogue,
                verify_evidence=lambda _: True, verify_reviewer=lambda _: True,
            )["status"], "validated_local_only")
        for ref in ("private/ops/../evidence.html", "private/ops/a/../evidence.html",
                    "private/ops/a\\\\evidence.html", "private/ops//evidence.html",
                    "private/ops/evidence.html/"):
            candidate = json.loads(json.dumps(receipt))
            candidate["evidence"]["private_ref"] = ref
            candidate["reviewer"]["verification_ref"] = ref
            self.assertTrue(list(validator.iter_errors(candidate)), ref)
            with self.assertRaisesRegex(ValueError, "private/ops"):
                validate_reviewed_fact_receipt(candidate, verify_evidence=lambda _: True,
                                               verify_reviewer=lambda _: True)
        for location, field in (("fact", "fact_id"), ("fact", "OpportunityKey"),
                                ("reviewer", "reviewer_id")):
            candidate = json.loads(json.dumps(receipt))
            candidate[location][field] = f" {candidate[location][field]} "
            if location == "fact":
                candidate["fact_sha256"] = hashlib.sha256(json.dumps(
                    candidate["fact"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()).hexdigest()
            self.assertTrue(list(validator.iter_errors(candidate)), (location, field))
        candidate = json.loads(json.dumps(receipt))
        candidate["fact"]["uncontracted_extra"] = "not in the reconciled fact model"
        candidate["fact_sha256"] = hashlib.sha256(json.dumps(
            candidate["fact"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        self.assertTrue(list(validator.iter_errors(candidate)))
        with self.assertRaisesRegex(ValueError, "bound fact identity"):
            validate_reviewed_fact_receipt(candidate, verify_evidence=lambda _: True,
                                           verify_reviewer=lambda _: True)

    def test_receipt_gates_validation_reconciler_without_importing(self):
        catalogue, opportunities, _ = self.synthetic_inputs()
        receipt = self.reviewed_receipt()
        output = reconcile_receipted_institution_fact(
            receipt, opportunities, catalogue, verify_evidence=lambda _: True,
            verify_reviewer=lambda _: True,
        )
        self.assertEqual(output["status"], "validated_local_only")
        self.assertFalse(output["imported"])
        self.assertEqual(output["records"][0]["ReviewReceiptID"], receipt["receipt_id"])
        with self.assertRaisesRegex(ValueError, "evidence artifact is unverified"):
            reconcile_receipted_institution_fact(receipt, opportunities, catalogue)

    def test_receipt_accepts_both_canonical_opportunity_key_families(self):
        catalogue, _, fact_factory = self.synthetic_inputs()
        for identity in ({"Source": "official", "SourceID": "go-1"},
                         {"Source": "A:B", "SourceID": "C"}):
            key = stable_key(identity)
            with self.subTest(key=key):
                self.assertRegex(key, r"^GRANTX?:[0-9a-f]{24}$")
                fact = fact_factory("uq", OpportunityKey=key)
                receipt = self.reviewed_receipt()
                receipt["fact"] = fact
                receipt["fact_sha256"] = hashlib.sha256(json.dumps(
                    fact, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()).hexdigest()
                result = reconcile_receipted_institution_fact(
                    receipt, [{"OpportunityKey": key, "Deadline": "2027-06-30"}], catalogue,
                    verify_evidence=lambda _: True, verify_reviewer=lambda _: True,
                )
                self.assertEqual(result["records"][0]["OpportunityKey"], key)

    def test_receipt_rejects_padded_fact_and_reviewer_identities(self):
        receipt = self.reviewed_receipt()
        candidates = []
        for location, field in (("fact", "fact_id"), ("fact", "OpportunityKey"),
                                ("reviewer", "reviewer_id")):
            candidate = json.loads(json.dumps(receipt))
            candidate[location][field] = f" {candidate[location][field]} "
            if location == "fact":
                candidate["fact_sha256"] = hashlib.sha256(json.dumps(
                    candidate["fact"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()).hexdigest()
            candidates.append((candidate, location, field))
        for candidate, location, field in candidates:
            with self.subTest(location=location, field=field):
                with self.assertRaisesRegex(ValueError, "bound fact identity|reviewer_id"):
                    validate_reviewed_fact_receipt(
                        candidate, verify_evidence=lambda _: True, verify_reviewer=lambda _: True)


if __name__ == "__main__":
    unittest.main()
