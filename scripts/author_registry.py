"""Build a conservative, derived author registry from retained source evidence.

This module deliberately does not harvest ResearchGate or promote name-only
matches. It creates auditable author-publication relationships and statistics
for review and reporting.
"""
from __future__ import annotations

import hashlib
import re
from numbers import Integral
from typing import Any, Iterable, Mapping


IDENTIFIER_FIELDS = ("ORCID", "AuthorORCID", "OpenAlexAuthorID", "ScopusAuthorID", "WoSResearcherID")



def _clean(value: Any) -> str:
    """Normalize optional text without coercing malformed source values."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("text fields must be strings or None")
    return re.sub(r"\s+", " ", value.strip())


def _validated_row(row: Any, source: str, index: int) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise ValueError(f"{source} row {index} must be a mapping")
    result = dict(row)
    text_fields = IDENTIFIER_FIELDS + ("PMID", "AuthorName", "AffiliationText", "EvidenceKind",
                                       "DORAKey", "Authors", "DORAURL", "PubMedURL", "AttributionEvidence",
                                       "CHHHSAffiliatedAuthors", "SourceObservedUTC")
    for field in text_fields:
        if field in result and result[field] is not None and not isinstance(result[field], str):
            raise ValueError(f"{source} row {index} field {field} must be text or None")
    return result


def _positive_index(row: Mapping[str, Any], field: str, source: str, row_index: int,
                    *, required: bool) -> int | None:
    value = row.get(field)
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 1:
        qualifier = "required " if required else ""
        raise ValueError(f"{source} row {row_index} field {field} must be a {qualifier}positive integer")
    return int(value)


def normalise_name(value: Any) -> str:
    """Return a comparison form without changing the displayed name."""
    return re.sub(r"[^a-z0-9]", "", _clean(value).casefold())


def author_key(name: Any, identifier: Any = None) -> str:
    """Create a stable non-semantic key; identifiers prevent same-name merging."""
    basis = _clean(identifier) or f"name:{normalise_name(name)}"
    return "AUTH:" + hashlib.sha256(basis.casefold().encode("utf-8")).hexdigest()[:24]


def identity_status(identifier: Any = None, affiliation: Any = None) -> str:
    if _clean(identifier):
        return "Confirmed"
    if _clean(affiliation):
        return "Probable"
    return "Unresolved"


def _identifier(row: dict[str, Any]) -> str:
    for field in IDENTIFIER_FIELDS:
        if _clean(row.get(field)):
            return _clean(row[field])
    return ""


def build_author_registry(
    pubmed_author_rows: Iterable[dict[str, Any]] = (),
    dora_records: Iterable[dict[str, Any]] = (),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(authors, evidence)`` from structured PubMed and DORA records.

    PubMed rows should contain PMID, AuthorIndex, AuthorName, AffiliationText,
    AffiliationIndex and EvidenceKind. DORA records may contain DORAKey,
    Authors, DORAURL, CHHHSAffiliatedAuthors and AttributionEvidence.
    """
    authors: dict[str, dict[str, Any]] = {}
    evidence: list[dict[str, Any]] = []

    def add(name: Any, source: str, publication_key: str, row: dict[str, Any], order: int, affiliation: str = "") -> None:
        display = _clean(name)
        if not display:
            return
        if not publication_key:
            raise ValueError(f"{source} author evidence requires a stable publication key")
        identifier = _identifier(row)
        key = author_key(display, identifier)
        status = identity_status(identifier, affiliation)
        record = authors.setdefault(key, {
            "AuthorKey": key,
            "DisplayName": display,
            "NameVariants": display,
            "IdentityStatus": status,
            "IdentityConfidence": "high" if identifier else ("medium" if affiliation else "low"),
            "ExternalIdentifiers": identifier,
            "PublicationCount": 0,
            "FirstAuthorCount": 0,
            "SeniorAuthorCount": 0,
            "CollaborativeCount": 0,
            "Sources": set(),
        })
        if display not in record["NameVariants"].split("; "):
            record["NameVariants"] += "; " + display
        if status == "Confirmed" or record["IdentityStatus"] == "Unresolved":
            record["IdentityStatus"] = status
            record["IdentityConfidence"] = {"Confirmed": "high", "Probable": "medium", "Unresolved": "low"}[status]
        record["Sources"].add(source)
        relation = {
            "AuthorKey": key,
            "Source": source,
            "SourceKey": f"{source.lower()}:{publication_key}",
            "AuthorName": display,
            "AuthorOrder": order,
            "AffiliationText": affiliation,
            "AffiliationIndex": row.get("AffiliationIndex"),
            "EvidenceKind": _clean(row.get("EvidenceKind")) or ("DORA attribution text" if source == "DORA" else "author record"),
            "EvidenceURL": _clean(row.get("DORAURL" if source == "DORA" else "PubMedURL")),
            "AttributionEvidence": _clean(row.get("AttributionEvidence")),
            "SourceObservedUTC": row.get("SourceObservedUTC"),
            "ReviewStatus": "Needs Review" if status in {"Candidate", "Unresolved"} else "Needs Review",
        }
        evidence.append(relation)

    for row_index, raw_row in enumerate(pubmed_author_rows, 1):
        row = _validated_row(raw_row, "PubMed", row_index)
        author_index = _positive_index(row, "AuthorIndex", "PubMed", row_index, required=True)
        _positive_index(row, "AffiliationIndex", "PubMed", row_index, required=False)
        pmid = _clean(row.get("PMID"))
        if pmid and not pmid.isdecimal():
            raise ValueError(f"PubMed row {row_index} field PMID must contain decimal digits")
        add(row.get("AuthorName"), "PubMed", pmid, row, author_index, _clean(row.get("AffiliationText")))

    for row_index, raw_row in enumerate(dora_records, 1):
        row = _validated_row(raw_row, "DORA", row_index)
        names = [_clean(n) for n in re.split(r";|\n", row.get("Authors") or "") if _clean(n)]
        explicit_name = _clean(row.get("AuthorName"))
        matches = [index for index, name in enumerate(names, 1)
                   if explicit_name and _clean(name).casefold() == explicit_name.casefold()]
        identifier_owner = (matches[0] if len(matches) == 1 else None) if explicit_name else (1 if len(names) == 1 else None)
        for index, name in enumerate(names, 1):
            # A publication-level identifier is not evidence for every coauthor.
            author_row = row if index == identifier_owner else {k: v for k, v in row.items() if k not in IDENTIFIER_FIELDS}
            affiliation = _clean(row.get("AffiliationText")) if index == identifier_owner else ""
            add(name, "DORA", _clean(row.get("DORAKey")), author_row, index, affiliation)

    publication_last_order: dict[str, int] = {}
    author_positions: dict[str, dict[str, set[int]]] = {}
    for relation in evidence:
        source_key, order = relation["SourceKey"], relation["AuthorOrder"]
        publication_last_order[source_key] = max(publication_last_order.get(source_key, 0), order)
        author_positions.setdefault(relation["AuthorKey"], {}).setdefault(source_key, set()).add(order)

    for record in authors.values():
        record["Sources"] = "; ".join(sorted(record["Sources"]))
        # Count each publication once while retaining every affiliation row.
        positions = author_positions[record["AuthorKey"]]
        record["PublicationCount"] = len(positions)
        record["FirstAuthorCount"] = sum(1 in orders for orders in positions.values())
        record["SeniorAuthorCount"] = sum(publication_last_order[key] in orders for key, orders in positions.items())
        record["CollaborativeCount"] = sum(
            1 not in orders and publication_last_order[key] not in orders
            for key, orders in positions.items()
        )
    return sorted(authors.values(), key=lambda r: r["DisplayName"].casefold()), evidence


def author_statistics(authors: Iterable[dict[str, Any]], evidence: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Summarise the derived registry without inventing completeness."""
    authors = list(authors)
    evidence = list(evidence)
    return {
        "AuthorCount": len(authors),
        "RelationshipCount": len(evidence),
        "ConfirmedAuthorCount": sum(a.get("IdentityStatus") == "Confirmed" for a in authors),
        "ProbableAuthorCount": sum(a.get("IdentityStatus") == "Probable" for a in authors),
        "UnresolvedAuthorCount": sum(a.get("IdentityStatus") == "Unresolved" for a in authors),
        "SourceCounts": {source: sum(e.get("Source") == source for e in evidence) for source in sorted({e.get("Source") for e in evidence})},
        "Completeness": "not_established",
    }
