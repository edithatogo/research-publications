import unittest

from scripts.publication_batch_contract import (
    validate_paged_batch,
    validate_update_allowlist,
)


class PublicationBatchContractTests(unittest.TestCase):
    def test_complete_pages_reconcile_count_and_keys(self):
        pages = [
            {"rows": [{"SourceKey": "PMID:1"}], "cursor_before": "", "cursor_after": "PMID:1"},
            {"rows": [{"SourceKey": "PMID:2"}], "cursor_before": "PMID:1", "cursor_after": "PMID:2"},
            {"rows": [], "cursor_before": "PMID:2", "cursor_after": "PMID:2"},
        ]
        self.assertEqual(validate_paged_batch(pages, expected_count=2, expected_keys=["PMID:1", "PMID:2"]), [])

    def test_partial_response_and_duplicate_key_fail_closed(self):
        pages = [
            {"rows": [{"SourceKey": "PMID:1"}], "cursor_before": "", "cursor_after": "PMID:1", "partial": True},
            {"rows": [{"SourceKey": "PMID:1"}], "cursor_before": "PMID:1", "cursor_after": "PMID:1"},
        ]
        errors = validate_paged_batch(pages, expected_count=2, expected_keys=["PMID:1", "PMID:2"])
        self.assertTrue(any("partial" in error for error in errors))
        self.assertTrue(any("duplicate" in error for error in errors))

    def test_missing_progress_and_wrong_independent_set_fail_closed(self):
        pages = [{"rows": [{"SourceKey": "PMID:1"}], "cursor_before": "", "cursor_after": ""}]
        errors = validate_paged_batch(pages, expected_count=1, expected_keys=["PMID:2"])
        self.assertTrue(any("continuation cursor" in error for error in errors))
        self.assertTrue(any("set does not match" in error for error in errors))

    def test_matching_key_set_without_terminal_page_is_incomplete(self):
        pages = [{"rows": [{"SourceKey": "PMID:1"}], "cursor_before": "", "cursor_after": "PMID:1"}]
        errors = validate_paged_batch(pages, expected_count=1, expected_keys=["PMID:1"])
        self.assertTrue(any("terminal empty page" in error for error in errors))

    def test_intermediate_empty_page_and_non_text_key_fail_closed(self):
        pages = [
            {"rows": [], "cursor_before": "", "cursor_after": ""},
            {"rows": [{"SourceKey": 1}], "cursor_before": "", "cursor_after": "1"},
            {"rows": [], "cursor_before": "1", "cursor_after": "1"},
        ]
        errors = validate_paged_batch(pages, expected_count=1, expected_keys=["1"])
        self.assertTrue(any("terminates before" in error for error in errors))
        self.assertTrue(any("row without SourceKey" in error for error in errors))

    def test_malformed_page_returns_failure_instead_of_crashing(self):
        errors = validate_paged_batch([None], expected_count=0, expected_keys=[])
        self.assertTrue(any("must be an object" in error for error in errors))
        self.assertTrue(any("positive integer" in error for error in errors))

    def test_non_iterable_batch_inputs_fail_closed(self):
        errors = validate_paged_batch(None, expected_count=1, expected_keys=None)
        self.assertTrue(any("pages must be an iterable" in error for error in errors))
        self.assertTrue(any("expected keys must be an iterable" in error for error in errors))

    def test_string_inputs_are_not_treated_as_iterable_batches(self):
        errors = validate_paged_batch("not-pages", expected_count=1, expected_keys="PMID:1")
        self.assertTrue(any("pages must be an iterable" in error for error in errors))
        self.assertTrue(any("expected keys must be an iterable" in error for error in errors))

    def test_whitespace_key_is_rejected_in_page_and_expected_set(self):
        pages = [
            {"rows": [{"SourceKey": " PMID:1 "}], "cursor_before": "", "cursor_after": "PMID:1"},
            {"rows": [], "cursor_before": "PMID:1", "cursor_after": "PMID:1"},
        ]
        errors = validate_paged_batch(pages, expected_count=1, expected_keys=[" PMID:1 "])
        self.assertTrue(any("without SourceKey" in error for error in errors))
        self.assertTrue(any("expected keys must be nonblank, trimmed text" in error for error in errors))

    def test_duplicate_expected_keys_and_nonpositive_counts_are_rejected(self):
        pages = [{"rows": [], "cursor_before": "", "cursor_after": ""}]
        errors = validate_paged_batch(pages, expected_count=0, expected_keys=["PMID:1", "PMID:1"])
        self.assertTrue(any("positive integer" in error for error in errors))
        self.assertTrue(any("expected SourceKey set contains duplicates" in error for error in errors))

    def test_update_allowlist_protects_manual_fields(self):
        self.assertEqual(validate_update_allowlist(["LastObservedUTC", "OAUrl"]), [])
        errors = validate_update_allowlist(["ReviewStatus", "FirstObservedUTC", "Unexpected"])
        self.assertTrue(any("manual fields" in error for error in errors))
        self.assertTrue(any("outside" in error for error in errors))

    def test_error_envelopes_and_non_boolean_partial_flags_fail_closed(self):
        for marker in ({"error": {}}, {"error": []}, {"error": ""},
                       {"partial": "true"}, {"partial": 1}, {"partial": None}):
            with self.subTest(marker=marker):
                pages = [dict(rows=[{"SourceKey": "PMID:1"}],
                              cursor_before="", cursor_after="a", **marker),
                         dict(rows=[], cursor_before="a", cursor_after="a")]
                self.assertTrue(validate_paged_batch(
                    pages, expected_count=1, expected_keys=["PMID:1"]))

    def test_explicit_complete_page_with_null_initial_cursor_remains_valid(self):
        pages = [dict(rows=[{"SourceKey": "PMID:1"}], cursor_before=None,
                      cursor_after="opaque-a", error=None, partial=False),
                 dict(rows=[], cursor_before="opaque-a", cursor_after="opaque-a")]
        self.assertEqual(validate_paged_batch(
            pages, expected_count=1, expected_keys=["PMID:1"]), [])

    def test_missing_or_structured_cursors_fail_closed(self):
        for cursor in ({}, {"cursor_before": [], "cursor_after": {}},
                       {"cursor_before": "", "cursor_after": " a "}):
            with self.subTest(cursor=cursor):
                pages = [dict(rows=[{"SourceKey": "PMID:1"}], **cursor),
                         dict(rows=[], cursor_before="a", cursor_after="a")]
                self.assertTrue(validate_paged_batch(
                    pages, expected_count=1, expected_keys=["PMID:1"]))

    def test_cursor_cycle_is_rejected_despite_matching_count_and_keys(self):
        pages = [dict(rows=[{"SourceKey": str(i)}], cursor_before=before,
                      cursor_after=after)
                 for i, before, after in [(1, "", "a"), (2, "a", "b"), (3, "b", "a")]]
        pages.append(dict(rows=[], cursor_before="a", cursor_after="a"))
        self.assertTrue(any("repeats" in e for e in validate_paged_batch(
            pages, expected_count=3, expected_keys=["1", "2", "3"])))


if __name__ == "__main__":
    unittest.main()
