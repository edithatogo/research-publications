"""Prepare revision-bound metadata exceptions for the existing human review route.

Local preparation only. Never mutates source, registry, author identities or
review decisions. Native review-flow generation is outside this source slice.
"""

from __future__ import annotations

from collections import defaultdict

from .publication_reconciliation import build_case

METADATA_FIELDS = frozenset(
    {
        "Title",
        "Authors",
        "Journal",
        "PublicationYear",
        "PublicationMonth",
        "PublicationDateRaw",
        "PublicationDatePrecision",
        "CHHHSAffiliatedAuthors",
        "MatchedFacilities",
    }
)
RULE_VERSION = "source-registry-metadata-conflict-v2"


def metadata_difference_kind(field, retained, source):
    """Classify selected literal values without editing them or matching people.

    Two bounded HTML entity decodes cover nested publisher encodings. Literal
    affiliated-name segment equality is not author identity/order evidence.
    Numeric zero is not globally missing; date-range repair has its own guard.
    """
    import html
    import re

    if field not in METADATA_FIELDS:
        raise ValueError("Qualified metadata field required")
    if retained == source:
        return "exact"
    if source is None or isinstance(source, str) and not source.strip():
        return "source_unknown_retained"
    if retained is None or isinstance(retained, str) and not retained.strip():
        return "missing_destination"
    if isinstance(retained, str) and isinstance(source, str):

        def text(value):
            for _ in range(2):
                value = html.unescape(value)
            return re.sub(r"</?(?:i|b|em|strong|sub|sup)>", "", value)

        a, b = text(retained), text(source)
        if a == b:
            return "text_representation_equivalent"
        if a.casefold() == b.casefold():
            return "case_representation_equivalent"
        if field == "CHHHSAffiliatedAuthors":
            segments = lambda v: {t.strip() for t in re.split("[;,]", v) if t.strip()}
            if segments(retained) == segments(source):
                return "equal_literal_segments_not_author_identity"
    return "populated_semantic_difference_preserved"


def cases_from_metadata_differences(
    differences, registry_rows, *, source_revision, registry_revision, complete
):
    """Group selected differences by stable item, preserving both exact values.

    Revision denotes each input snapshot, not a inferred modification date.
    No equivalence, correction or author matching is inferred here. Unknown
    fields, duplicate fields/items, changed registry values and lost evidence
    stop preparation. All selected cases are returned, without truncation.
    """
    if (
        complete is not True
        or not isinstance(differences, list)
        or not isinstance(registry_rows, list)
    ):
        raise ValueError("Complete source and registry snapshots required")
    if any(
        not isinstance(x, str) or not x.strip() or x != x.strip()
        for x in (source_revision, registry_revision)
    ):
        raise ValueError("Exact source and registry revisions required")
    indexed = {}
    for row in registry_rows:
        if not isinstance(row, dict) or set(row) != {
            "item_id",
            "source_key",
            "values",
            "evidence",
        }:
            raise ValueError("Registry input needs item_id/source_key/values/evidence")
        ident = row["item_id"]
        if type(ident) is not int or ident <= 0 or ident in indexed:
            raise ValueError("Unique positive registry item ID required")
        if not isinstance(row["values"], dict):
            raise ValueError("Registry values must be an object")  # noqa: TRY004 - retained validator ValueError contract
        indexed[ident] = row
    grouped = defaultdict(dict)
    for diff in differences:
        if not isinstance(diff, dict) or set(diff) != {
            "id",
            "field",
            "registry",
            "canonical",
        }:
            raise ValueError("Exact difference shape required")
        ident, field = diff["id"], diff["field"]
        if (
            type(ident) is not int
            or ident not in indexed
            or field not in METADATA_FIELDS
        ):
            raise ValueError(
                "Difference must bind an existing item and qualified metadata field"
            )
        if field in grouped[ident] or field not in indexed[ident]["values"]:
            raise ValueError("No duplicate or absent registry field")
        if (
            diff["registry"] != indexed[ident]["values"][field]
            or diff["registry"] == diff["canonical"]
        ):
            raise ValueError("Stale registry difference or equal values")
        grouped[ident][field] = diff["canonical"]
    cases = []
    for ident, changed in grouped.items():
        row = indexed[ident]
        key = row["source_key"]
        original = dict(row["values"])
        candidate = dict(changed)
        # Record roles are explicit; neither panel is labelled an approved correction.
        original.update(
            ValueRole="Retained registry values; correction provenance unresolved",
            RegistryItemID=ident,
            SnapshotRevision=registry_revision,
        )
        candidate.update(
            ValueRole="Canonical source values for disputed fields; proposal only; context title from registry",
            ContextTitle=row["values"].get("Title"),
            RegistryItemID=ident,
            SnapshotRevision=source_revision,
        )
        for link in ("PubMedURL", "DORAURL"):
            if link in row["values"]:
                candidate[link] = row["values"][link]
        evidence = row["evidence"]
        if not isinstance(evidence, list):
            raise ValueError("Evidence must be an array")  # noqa: TRY004 - retained validator ValueError contract
        canonical_evidence = [
            dict(e, evidence_id="canonical:" + e["evidence_id"]) for e in evidence
        ]
        records = [
            {
                "record_id": f"registry:{ident}",
                "source_key": key,
                "values": original,
                "evidence": evidence,
            },
            {
                "record_id": f"canonical-for:{ident}",
                "source_key": key,
                "values": candidate,
                "evidence": canonical_evidence,
            },
        ]
        cases.append(
            build_case(
                records,
                "metadata_conflict",
                RULE_VERSION,
                source_revision + "|registry:" + registry_revision,
            )
        )
    return tuple(sorted(cases, key=lambda x: x.case_id))


def review_page(cases, page_index, page_size=20):
    """Explicit pages for the existing bounded reviewer; never silently truncates."""
    if (
        type(page_index) is not int
        or page_index < 0
        or type(page_size) is not int
        or not 1 <= page_size <= 20
    ):
        raise ValueError("Qualified zero-based page and size1..20 required")
    cases = tuple(cases)
    if len({c.case_id for c in cases}) != len(cases):
        raise ValueError("Unique cases required")
    pages = (len(cases) + page_size - 1) // page_size
    if page_index >= pages:
        raise ValueError("Page outside complete case set")
    return {
        "cases": cases[page_index * page_size : (page_index + 1) * page_size],
        "page_index": page_index,
        "page_count": pages,
        "total_cases": len(cases),
        "remaining_after_page": max(0, len(cases) - (page_index + 1) * page_size),
    }
