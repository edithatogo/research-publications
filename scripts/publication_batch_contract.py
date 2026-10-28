"""Fail-closed checks for paged publication batches.

These checks validate a collector/export contract locally. They do not claim
that a Power BI or Power Automate response was obtained from the tenant.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping


PROTECTED_MANUAL_FIELDS = frozenset({
    "FirstObservedUTC", "ReviewStatus", "ReviewNotes", "Title", "Authors",
    "Journal", "PublicationYear", "PublicationMonth", "SourceKey",
    "CanonicalKey",
})
OBSERVED_UPDATE_FIELDS = frozenset({
    "LastObservedUTC", "CitationCount_OpenAlex", "OpenAccessStatus", "OAUrl",
    "CitationMetricsObservedUTC",
})


def validate_update_allowlist(
    fields: Iterable[str], *, internal_allowed: Iterable[str] = ()
) -> list[str]:
    """Reject writes outside the narrow observation-only update contract."""
    names = {str(field) for field in fields}
    errors: list[str] = []
    forbidden = names & PROTECTED_MANUAL_FIELDS
    allowed = OBSERVED_UPDATE_FIELDS | {str(field) for field in internal_allowed}
    unknown = names - allowed
    if forbidden:
        errors.append(f"manual fields are protected from update: {sorted(forbidden)}")
    if unknown:
        errors.append(f"update fields are outside the observation allowlist: {sorted(unknown)}")
    return errors


def validate_paged_batch(
    pages: Iterable[Mapping[str, object]],
    *,
    expected_count: int,
    expected_keys: Iterable[str],
    key_field: str = "SourceKey",
) -> list[str]:
    """Validate complete, ordered pages before allowing a batch to be applied."""
    errors: list[str] = []
    if type(expected_count) is not int or expected_count <= 0:
        errors.append("expected_count must be a positive integer")
    try:
        if isinstance(expected_keys, (str, bytes)):
            raise TypeError
        expected_values = list(expected_keys)
    except TypeError:
        errors.append("independent expected keys must be an iterable of text keys")
        expected_values = []
    expected: list[str] = []
    for key in expected_values:
        if not isinstance(key, str) or not key.strip() or key != key.strip():
            errors.append("independent expected keys must be nonblank, trimmed text")
            continue
        expected.append(key)
    try:
        if isinstance(pages, (str, bytes, Mapping)):
            raise TypeError
        page_list = list(pages)
    except TypeError:
        errors.append("pages must be an iterable of page objects")
        page_list = []
    expected_set = set(expected)
    seen: list[str] = []
    continuation_cursors: set[str] = set()
    previous_cursor: object = None
    for index, page in enumerate(page_list):
        if not isinstance(page, Mapping):
            errors.append(f"page {index} must be an object")
            continue
        rows = page.get("rows")
        if not isinstance(rows, list):
            errors.append(f"page {index} rows must be a list")
            continue
        # An empty error envelope still indicates a failed response. Do not let
        # truthiness turn it, or a malformed partial flag, into a complete page.
        if (("error" in page and page["error"] is not None)
                or ("partial" in page and page["partial"] is not False)):
            errors.append(f"page {index} is an error or partial response")
        cursor_before = page.get("cursor_before")
        cursor_after = page.get("cursor_after")
        if ("cursor_before" not in page or "cursor_after" not in page
                or not (isinstance(cursor_before, str) or
                        (index == 0 and cursor_before is None))
                or not isinstance(cursor_after, str)
                or (isinstance(cursor_before, str) and cursor_before != cursor_before.strip())
                or (isinstance(cursor_after, str) and cursor_after != cursor_after.strip())):
            errors.append(f"page {index} requires explicit text cursors")
        if index and cursor_before != previous_cursor:
            errors.append(f"page {index} cursor does not continue the previous page")
        if not rows and index != len(page_list) - 1:
            errors.append(f"page {index} terminates before the final page")
        if not rows and cursor_after != cursor_before:
            errors.append(f"page {index} terminal cursor changed")
        keys: list[str] = []
        for row in rows:
            if (not isinstance(row, Mapping)
                    or not isinstance(row.get(key_field), str)
                    or not row[key_field].strip()
                    or row[key_field] != row[key_field].strip()):
                errors.append(f"page {index} contains a row without {key_field}")
                continue
            keys.append(row[key_field])
        if len(keys) != len(set(keys)):
            errors.append(f"page {index} contains duplicate {key_field} values")
        seen.extend(keys)
        if rows and cursor_after in (None, ""):
            errors.append(f"page {index} with rows has no continuation cursor")
        if rows and cursor_before is not None and cursor_after == cursor_before:
            errors.append(f"page {index} cursor did not advance")
        if rows and isinstance(cursor_after, str) and cursor_after:
            if cursor_after in continuation_cursors:
                errors.append(f"page {index} repeats an earlier continuation cursor")
            continuation_cursors.add(cursor_after)
        previous_cursor = cursor_after
    if not page_list or not isinstance(page_list[-1], Mapping) or page_list[-1].get("rows") != []:
        errors.append("paged batch lacks a terminal empty page")
    if type(expected_count) is int and len(seen) != expected_count:
        errors.append(f"row count {len(seen)} does not match expected count {expected_count}")
    if len(seen) != len(set(seen)):
        errors.append(f"paged batch contains duplicate {key_field} values")
    if set(seen) != expected_set:
        errors.append(f"paged {key_field} set does not match the independent expected set")
    if len(expected) != len(expected_set):
        errors.append(f"independent expected {key_field} set contains duplicates")
    return errors
