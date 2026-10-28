import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from grants_registry import merge_observations, normalize_opportunity, normalize_source_row_url, normalize_url, sharepoint_field_map


class GrantsRegistryTests(unittest.TestCase):
    def test_rss_atom_and_api_shapes_normalize_to_same_key(self):
        rss = {"Source": "NHMRC", "SourceID": "G-1", "title": "Tropical Health Grant", "link": "HTTPS://Funder.example/opportunity/1/", "deadline": "2027-04"}
        api = {"Source": "NHMRC", "ExternalID": "G-1", "Title": "Tropical Health Grant", "URL": "https://funder.example/opportunity/1", "ClosingDate": "2027-04"}
        self.assertEqual(normalize_opportunity(rss)["OpportunityKey"], normalize_opportunity(api)["OpportunityKey"])
        self.assertEqual(normalize_opportunity(rss)["DeadlinePrecision"], "month")

    def test_unqualified_funder_or_category_assignments_fail_instead_of_disappearing(self):
        for field, value in (("FunderKey", "FUNDER:nhmrc"),
                             ("CategoryKeys", ["health"]),
                             ("CategoryKeysJSON", '["health"]')):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "evidence-backed reviewed classification"):
                normalize_opportunity({"Source":"NHMRC","SourceID":"G-1","Title":"Call",
                    "URL":"https://example.org/call", field:value})
        baseline=normalize_opportunity({"Source":"NHMRC","SourceID":"G-1","Title":"Call",
            "URL":"https://example.org/call"})
        unclassified=normalize_opportunity({"Source":"NHMRC","SourceID":"G-1","Title":"Call",
            "URL":"https://example.org/call","FunderKey":None,"CategoryKeys":[]})
        self.assertEqual(unclassified['OpportunityKey'],baseline['OpportunityKey'])

    def test_rejected_classification_does_not_mutate_input_or_approve_it(self):
        import copy
        row={'Source':'NHMRC','SourceID':'G-1','Title':'Call','Funder':'Stated funder label',
             'URL':'https://example.org/call','ReviewStatus':'Needs Review',
             'FunderKey':'funder:unverified','CategoryKeysJSON':'["health"]'}
        original=copy.deepcopy(row)
        with self.assertRaises(ValueError):normalize_opportunity(row)
        self.assertEqual(row,original)
        for field in ['FunderKey','CategoryKeysJSON']:row.pop(field)
        normal=normalize_opportunity(row,retrieved_at='2026-10-29T00:00:00Z')
        self.assertEqual(normal['Funder'],'Stated funder label')
        self.assertEqual(normal['ReviewStatus'],'Needs Review')
        self.assertNotIn('FunderKey',normal)
        self.assertNotIn('CategoryKeysJSON',normal)

    def test_canonical_normalizer_rejects_non_text_and_falsey_source_values(self):
        for field, value in (("SourceID", 0), ("Title", False), ("URL", []),
                             ("Deadline", 2027), ("RetrievedUTC", {}),
                             ("ReviewStatus", 0)):
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                normalize_opportunity({"Title": "Call", "URL": "https://example.org/call", field: value})
        with self.assertRaisesRegex(ValueError, "object"):
            normalize_opportunity([("Title", "Call")])

    def test_canonical_normalizer_rejects_padded_stable_identity_fields(self):
        for field in ("Source", "SourceID", "ExternalID", "RoundID"):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                normalize_opportunity({"Title": "Call", "URL": "https://example.org/call",
                                       field: " stable-id "})

    def test_missing_date_stays_unknown(self):
        item = normalize_opportunity({"Source": "DGR", "Title": "Open call", "URL": "https://example.org/call"})
        self.assertIsNone(item["Deadline"])
        self.assertEqual(item["DeadlinePrecision"], "unknown")

    def test_offset_deadline_keeps_source_local_day_and_exact_raw_instant(self):
        raw = "2026-11-11T00:15:00+11:00"
        item = normalize_opportunity({"Title": "Call", "URL": "https://example.org/call", "ClosingDate": raw})
        self.assertEqual(item["Deadline"], "2026-11-11")
        self.assertEqual(item["DeadlineRaw"], raw)
        self.assertEqual(item["DeadlinePrecision"], "day")
        utc = normalize_opportunity({"Title": "Call", "URL": "https://example.org/call",
                                     "deadline": "2026-11-10T13:15:00Z"})
        self.assertEqual(utc["Deadline"], "2026-11-10")

    def test_deadline_exposes_named_zone_utc_instant_and_brisbane_view(self):
        row = normalize_opportunity({
            "Title": "Call", "URL": "https://example.org/call",
            "Deadline": "2026-01-01T23:30:00Z", "DeadlineTimezone": "Australia/Sydney",
        })
        self.assertEqual(row["Deadline"], "2026-01-02")
        self.assertEqual(row["DeadlineLocalTime"], "10:30:00")
        self.assertEqual(row["DeadlineTimezone"], "Australia/Sydney")
        self.assertEqual(row["DeadlineUTCInstant"], "2026-01-01T23:30:00Z")
        self.assertEqual(row["DeadlineBrisbaneDate"], "2026-01-02")
        self.assertEqual(row["DeadlineBrisbaneTime"], "09:30:00")
        self.assertEqual(row["DeadlineTemporalStatus"], "zone_resolved")

    def test_naive_named_zone_deadline_resolves_dst_and_rejects_fold_and_gap(self):
        summer = normalize_opportunity({
            "Title": "Call", "URL": "https://example.org/call",
            "Deadline": "2026-01-15T12:00:00", "DeadlineTimezone": "Australia/Sydney",
        })
        self.assertEqual(summer["DeadlineUTCInstant"], "2026-01-15T01:00:00Z")
        self.assertEqual(summer["DeadlineBrisbaneTime"], "11:00:00")
        self.assertEqual(summer["DeadlineTemporalStatus"], "zone_resolved")

        ambiguous = normalize_opportunity({
            "Title": "Call", "URL": "https://example.org/call",
            "Deadline": "2026-04-05T02:30:00", "DeadlineTimezone": "Australia/Sydney",
        })
        self.assertEqual(ambiguous["Deadline"], "2026-04-05")
        self.assertEqual(ambiguous["DeadlineTemporalStatus"], "ambiguous_local_time")
        self.assertEqual(ambiguous["DeadlineUTCInstant"], "")
        self.assertEqual(ambiguous["DeadlineBrisbaneDate"], "")

        nonexistent = normalize_opportunity({
            "Title": "Call", "URL": "https://example.org/call",
            "Deadline": "2026-10-04T02:30:00", "DeadlineTimezone": "Australia/Sydney",
        })
        self.assertEqual(nonexistent["Deadline"], "2026-10-04")
        self.assertEqual(nonexistent["DeadlineTemporalStatus"], "nonexistent_local_time")
        self.assertEqual(nonexistent["DeadlineUTCInstant"], "")

    def test_deadline_zone_offset_mismatch_preserves_raw_instant_and_flags_review(self):
        row = normalize_opportunity({
            "Title": "Call", "URL": "https://example.org/call",
            "Deadline": "2026-01-15T12:00:00+10:00", "DeadlineTimezone": "Australia/Sydney",
        })
        self.assertEqual(row["Deadline"], "2026-01-15")
        self.assertEqual(row["DeadlineRaw"], "2026-01-15T12:00:00+10:00")
        self.assertEqual(row["DeadlineUTCInstant"], "2026-01-15T02:00:00Z")
        self.assertEqual(row["DeadlineBrisbaneTime"], "12:00:00")
        self.assertEqual(row["DeadlineTemporalStatus"], "zone_offset_mismatch")

    def test_naive_local_deadline_without_zone_preserves_stated_day_and_time_only(self):
        row = normalize_opportunity({
            "Title": "Call", "URL": "https://example.org/call",
            "Deadline": "2026-05-18T17:00:00",
        })
        self.assertEqual(row["Deadline"], "2026-05-18")
        self.assertEqual(row["DeadlinePrecision"], "day")
        self.assertEqual(row["DeadlineLocalTime"], "17:00:00")
        self.assertEqual(row["DeadlineTimezone"], "")
        self.assertEqual(row["DeadlineTemporalStatus"], "missing_timezone")
        self.assertEqual(row["DeadlineUTCInstant"], "")
        self.assertEqual(row["DeadlineBrisbaneDate"], "")
        self.assertEqual(row["DeadlineBrisbaneTime"], "")

    def test_date_only_and_unknown_deadlines_do_not_gain_invented_times(self):
        exact = normalize_opportunity({
            "Title": "Call", "URL": "https://example.org/call",
            "Deadline": "2026-11-11", "DeadlineTimezone": "Australia/Sydney",
        })
        self.assertEqual(exact["Deadline"], "2026-11-11")
        self.assertEqual(exact["DeadlineTemporalStatus"], "date_only")
        self.assertEqual(exact["DeadlineUTCInstant"], "")
        self.assertEqual(exact["DeadlineBrisbaneTime"], "")
        self.assertEqual(normalize_opportunity({"Deadline": "2026-11"})["DeadlineTemporalStatus"], "partial_date")

    def test_invalid_or_nontext_source_timezone_fails_closed(self):
        invalid = normalize_opportunity({
            "Title": "Call", "URL": "https://example.org/call",
            "Deadline": "2026-01-15T12:00:00", "DeadlineTimezone": "Not/A_Zone",
        })
        self.assertEqual(invalid["DeadlineTemporalStatus"], "invalid_timezone")
        self.assertEqual(invalid["DeadlineUTCInstant"], "")
        with self.assertRaisesRegex(ValueError, "DeadlineTimezone"):
            normalize_opportunity({"DeadlineTimezone": 10})

    def test_conflicting_timezone_aliases_are_not_resolved_by_precedence(self):
        naive = normalize_opportunity({
            "Title": "Call", "URL": "https://example.org/call",
            "Deadline": "2026-05-18T17:00:00",
            "DeadlineTimezone": "Australia/Sydney", "SourceTimezone": "Australia/Brisbane",
        })
        self.assertEqual(naive["Deadline"], "2026-05-18")
        self.assertEqual(naive["DeadlineLocalTime"], "17:00:00")
        self.assertEqual(naive["DeadlineTimezone"], "")
        self.assertEqual(naive["DeadlineTemporalStatus"], "timezone_conflict")
        self.assertEqual(naive["DeadlineUTCInstant"], "")
        self.assertEqual(naive["DeadlineBrisbaneDate"], "")

        offset = normalize_opportunity({
            "Title": "Call", "URL": "https://example.org/call",
            "Deadline": "2026-05-18T17:00:00+10:00",
            "DeadlineTimezone": "Australia/Sydney", "Timezone": "Australia/Brisbane",
        })
        self.assertEqual(offset["DeadlineTemporalStatus"], "timezone_conflict")
        self.assertEqual(offset["DeadlineUTCInstant"], "2026-05-18T07:00:00Z")
        self.assertEqual(offset["DeadlineBrisbaneDate"], "2026-05-18")
        self.assertEqual(offset["DeadlineBrisbaneTime"], "17:00:00")

    def test_lowercase_machine_timezone_alias_is_preserved(self):
        row = normalize_opportunity({
            "Title": "Call", "URL": "https://example.org/call",
            "Deadline": "2026-05-18T17:00:00", "deadline_timezone": "Australia/Sydney",
        })
        self.assertEqual(row["DeadlineTimezone"], "Australia/Sydney")
        self.assertEqual(row["DeadlineUTCInstant"], "2026-05-18T07:00:00Z")
        self.assertEqual(row["DeadlineTemporalStatus"], "zone_resolved")

    def test_naive_or_invalid_deadline_instant_fails_closed(self):
        for raw in ("2026-02-30T17:00:00+11:00",
                    "2026-11-11T25:00:00+11:00", "2026-11-11T17:00:00+25:00",
                    "2026-11-11 17:00:00+11:00", "2026-11-11T17:00:00+1100"):
            with self.subTest(raw=raw):
                item = normalize_opportunity({"Title": "Call", "URL": "https://example.org/call", "Deadline": raw})
                self.assertIsNone(item["Deadline"])
                self.assertEqual(item["DeadlineRaw"], raw)
                self.assertEqual(item["DeadlinePrecision"], "unknown")

    def test_duplicate_merge_retains_source_observations(self):
        records = merge_observations([
            {"Source": "A", "SourceID": "1", "Title": "Call", "URL": "https://a.example/1"},
            {"Source": "A", "SourceID": "1", "Title": "Call", "URL": "https://a.example/1"},
        ])
        self.assertEqual(len(records), 1)
        self.assertEqual(len(records[0]["SourceObservations"]), 2)

    def test_source_isolation_and_sharepoint_mapping(self):
        record = normalize_opportunity({"Source": "B", "SourceID": "2", "Title": "Call", "URL": "https://b.example/2"})
        mapped = sharepoint_field_map(record)
        self.assertEqual(mapped["Source"], "B")
        self.assertIn("EvidenceHash", mapped)
        self.assertEqual(normalize_url("HTTPS://B.EXAMPLE/2/"), "https://b.example/2")

    def test_source_row_url_is_optional_provenance_and_preserves_fragment(self):
        source_url = "HTTPS://Source.Example/opportunities#round-7"
        row = normalize_opportunity({
            "Source": "source", "SourceID": "7", "Title": "Call",
            "URL": "https://funder.example/call", "SourceRowURL": source_url,
        })
        self.assertEqual(row["URL"], "https://funder.example/call")
        self.assertEqual(row["SourceRowURL"], "https://source.example/opportunities#round-7")
        self.assertEqual(normalize_source_row_url("https://source.example/opportunities#round-8"),
                         "https://source.example/opportunities#round-8")
        self.assertEqual(normalize_opportunity({"Source": "source", "SourceID": "7",
                                                 "Title": "Call", "URL": "https://funder.example/call"})["SourceRowURL"], "")
        self.assertEqual(row["OpportunityKey"], normalize_opportunity({
            "Source": "source", "SourceID": "7", "Title": "Call",
            "URL": "https://funder.example/call", "SourceRowURL": "https://other.example/x#different",
        })["OpportunityKey"])

    def test_source_row_url_is_retained_in_observation_history(self):
        row = merge_observations([{
            "Source": "source", "SourceID": "7", "Title": "Call",
            "URL": "https://funder.example/call", "SourceRowURL": "https://source.example/list#row-7",
        }])[0]
        self.assertEqual(row["SourceObservations"][0]["SourceRowURL"], "https://source.example/list#row-7")

    def test_source_id_and_round_identity_ignore_case_but_keep_distinct_rounds(self):
        base = {"Source": "NHMRC", "SourceID": "PROGRAM-42", "RoundID": "Round-A"}
        equivalent = {**base, "SourceID": "program-42", "RoundID": "round-a"}
        next_round = {**base, "RoundID": "Round-B"}
        self.assertEqual(normalize_opportunity(base)["OpportunityKey"],
                         normalize_opportunity(equivalent)["OpportunityKey"])
        self.assertNotEqual(normalize_opportunity(base)["OpportunityKey"],
                            normalize_opportunity(next_round)["OpportunityKey"])

    def test_source_identity_preserves_internal_whitespace(self):
        base = {"Source": "NHMRC", "SourceID": "PROGRAM 42", "RoundID": "Round A"}
        different_source_id = {**base, "SourceID": "PROGRAM  42"}
        different_round = {**base, "RoundID": "Round  A"}
        normalized = normalize_opportunity(different_source_id)
        self.assertEqual(normalized["SourceID"], "PROGRAM  42")
        self.assertEqual(normalized["RoundID"], "Round A")
        self.assertNotEqual(normalize_opportunity(base)["OpportunityKey"],
                            normalized["OpportunityKey"])
        self.assertNotEqual(normalize_opportunity(base)["OpportunityKey"],
                            normalize_opportunity(different_round)["OpportunityKey"])

    def test_delimiter_bearing_identity_tuples_cannot_alias(self):
        # Both tuples previously produced the same legacy basis:
        # A:B:C|round:D. Ordinary identities retain their persisted GRANT key.
        first = {"Source": "A:B", "SourceID": "C", "RoundID": "D"}
        second = {"Source": "A", "SourceID": "B:C", "RoundID": "D"}
        first_key = normalize_opportunity(first)["OpportunityKey"]
        second_key = normalize_opportunity(second)["OpportunityKey"]
        self.assertNotEqual(first_key, second_key)
        self.assertTrue(first_key.startswith("GRANTX:"))
        self.assertTrue(second_key.startswith("GRANTX:"))
        equivalent = {**first, "SourceID": "c", "RoundID": "d"}
        self.assertEqual(first_key, normalize_opportunity(equivalent)["OpportunityKey"])

        round_only_a = {"Source": "A:round:B", "RoundID": "C"}
        round_only_b = {"Source": "A", "RoundID": "B:round:C"}
        self.assertNotEqual(normalize_opportunity(round_only_a)["OpportunityKey"],
                            normalize_opportunity(round_only_b)["OpportunityKey"])

        merged = merge_observations([first, second])
        self.assertEqual(len(merged), 2)

    def test_delimiter_free_identity_keeps_legacy_key_namespace(self):
        item = normalize_opportunity({"Source": "NHMRC", "SourceID": "PROGRAM-42", "RoundID": "Round-A"})
        self.assertTrue(item["OpportunityKey"].startswith("GRANT:"))

    def test_naive_or_invalid_observation_timestamp_is_reviewed(self):
        naive = normalize_opportunity({"Title": "Call", "URL": "https://example.org/call", "RetrievedUTC": "2026-09-20T12:00:00"})
        invalid = normalize_opportunity({"Title": "Call", "URL": "https://example.org/call", "RetrievedUTC": "not-a-timestamp"})
        self.assertEqual(naive["RetrievedTimestampStatus"], "missing_timezone")
        self.assertEqual(invalid["RetrievedTimestampStatus"], "invalid")
        self.assertEqual(naive["ReviewStatus"], "Needs Review")
        self.assertEqual(invalid["ReviewStatus"], "Needs Review")

    def test_observation_timestamp_accepts_only_strict_offset_bearing_instants(self):
        valid = normalize_opportunity({"Title": "Call", "URL": "https://example.org/call",
                                       "RetrievedUTC": "2026-09-20T12:00:00.125+10:00"})
        self.assertEqual(valid["RetrievedTimestampStatus"], "valid")
        for raw in ("2026-09-20 12:00:00+10:00", "2026-09-20T12:00+10:00",
                    "2026-09-20T12:00:00+1000", "2026-09-20T12:00:00+25:00"):
            with self.subTest(raw=raw):
                item = normalize_opportunity({"Title": "Call", "URL": "https://example.org/call",
                                              "RetrievedUTC": raw})
                self.assertEqual(item["RetrievedTimestampStatus"], "invalid")
                self.assertEqual(item["ReviewStatus"], "Needs Review")

    def test_older_review_decision_survives_newer_source_observation(self):
        newer = {"Source": "A", "SourceID": "1", "Title": "Updated call",
                 "URL": "https://a.example/1", "RetrievedUTC": "2026-09-21T00:00:00Z"}
        reviewed = {"Source": "A", "SourceID": "1", "Title": "Original call",
                    "URL": "https://a.example/1", "RetrievedUTC": "2026-09-20T00:00:00Z",
                    "ReviewStatus": "Reviewed", "ReviewNotes": "Authority checked"}
        for observations in ([newer, reviewed], [reviewed, newer]):
            merged = merge_observations(observations)[0]
            self.assertEqual(merged["Title"], "Updated call")
            self.assertEqual(merged["ReviewStatus"], "Reviewed")
            self.assertEqual(merged["ReviewNotes"], "Authority checked")
            self.assertEqual(len(merged["SourceObservations"]), 2)


if __name__ == "__main__":
    unittest.main()
