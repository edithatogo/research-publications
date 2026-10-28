"""E09 Phase 2 first-discovery selection and baseline/catch-up behaviour (local).

Deterministic thread-selection behaviour over committed ``Publication Registry``
row shapes, using only field identities documented in
``docs/SHAREPOINT_LIST_REGISTRY.md``:

* ``SourceKey`` — stable ``source:SourceID`` identity (``pubmed:…``/``dora:…``);
* ``CanonicalKey`` — exact retained PUB deduplication or PMID/official DoRA
  candidate reference; syntax alone establishes no accepted canonical membership;
* ``ReviewStatus`` — retained ``Included`` / ``Needs Review`` / ``Excluded``
  labels, where Needs Review is uncertainty, not an approval gate;
* ``FirstObservedUTC`` — registry processing first-seen UTC instant, written at
  create and never overwritten on replay; it is not an external
  source-observation timestamp;
* ``LastObservedUTC`` — latest registry upsert processing time (optional in
  selection), not independent evidence of upstream harvest freshness;
* ``Title`` — indexed registry publication title (documented field; optional in
  the row shape because the historical DEV readback found it optional).

Behaviour boundaries required by the track:

* excluded rows never open a thread; confirmed (``Included``) and possible
  (``Needs Review``) tiers are preserved explicitly, never silently dropped;
* the initial baseline is exclusive: nothing first observed at or before the
  baseline opens a new thread on first discovery; a catch-up window
  (inclusive of both ends) must be selected explicitly to backfill earlier rows;
* duplicate SourceKeys inside an input batch fail closed, so idempotent
  re-reads remain provable;
* unknown, missing or malformed fields fail closed; no register row is mutated,
  no tenant object is touched and no message is sent by this module.

Delivery-trigger mapping matches the Phase 1 storage contract: new-since-baseline
selection suggests ``first_discovery``; explicit catch-up backfill suggests
``catch_up``. Send behaviour stays governed by the delivery-receipt contract and
real delivery authority — this module only classifies and selects.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from scripts.e09_feed_contracts import (
    _parse_aware_instant,
    _required_identifier,
    _required_text,
    publication_source_key,
)

REVIEW_STATUSES = {"Included", "Needs Review", "Excluded"}
STATUS_TIERS = {"Included": "confirmed", "Needs Review": "possible", "Excluded": "rejected"}
CANONICAL_KEY_RE = re.compile(
    r"(?:PUB:[0-9a-f]+|PMID:[1-9][0-9]*|"
    r"DORA:https://dora\.health\.qld\.gov\.au/qldresearchjspui/handle/"
    r"[1-9][0-9]*/[1-9][0-9]*)"
)

REGISTRY_ROW_FIELDS = {
    "SourceKey", "CanonicalKey", "ReviewStatus",
    "FirstObservedUTC", "LastObservedUTC", "PublicationMonth", "Title",
}


def _utc_instant(value: Any, field: str) -> datetime:
    """Parse a UTC-stamped instant; only Z or +00:00 offsets are accepted."""
    parsed = _parse_aware_instant(value, field)
    if parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{field} is a UTC registry stamp and must carry a zero offset (Z or +00:00)")
    return parsed


def _canonical_key(value: Any) -> str:
    key = _required_identifier(value, "CanonicalKey")
    if not CANONICAL_KEY_RE.fullmatch(key):
        raise ValueError("CanonicalKey must be exact PUB hex, positive ASCII PMID or official DoRA handle reference")
    return key


def _exact_shape(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("registry row must be an object")
    unknown = set(row) - REGISTRY_ROW_FIELDS
    if unknown:
        raise ValueError(f"registry row has undocumented fields for selection: {sorted(unknown)}")
    required = {"SourceKey", "CanonicalKey", "ReviewStatus", "FirstObservedUTC"}
    missing = required - set(row)
    if missing:
        raise ValueError(f"registry row is missing selection fields: {sorted(missing)}")
    return row


def parse_registry_row(row: dict[str, Any]) -> dict[str, Any]:
    """Fail-closed parse of one committed registry row into a selection record."""
    row = _exact_shape(row)
    source_key = publication_source_key(row["SourceKey"], "SourceKey")
    canonical_key = _canonical_key(row["CanonicalKey"])
    status = row["ReviewStatus"]
    if not isinstance(status, str) or status not in REVIEW_STATUSES:
        raise ValueError("ReviewStatus must be exactly one of 'Included', 'Needs Review' or 'Excluded'")
    first_observed_utc = _utc_instant(row["FirstObservedUTC"], "FirstObservedUTC")
    last_observed_utc = None
    if row.get("LastObservedUTC") is not None:
        last_observed_utc = _utc_instant(row["LastObservedUTC"], "LastObservedUTC")
        if last_observed_utc < first_observed_utc:
            raise ValueError("LastObservedUTC must not predate FirstObservedUTC")
    publication_month = row.get("PublicationMonth")
    if publication_month is not None:
        if not isinstance(publication_month, str) or not re.fullmatch(r"\d{4}-\d{2}|", publication_month):
            raise ValueError("PublicationMonth must be 'YYYY-MM' text or blank when unverified")
        if publication_month:
            year, month = (int(part) for part in publication_month.split("-"))
            if not 1 <= month <= 12:
                raise ValueError("PublicationMonth must carry a real calendar month")
    title = None
    if row.get("Title") is not None:
        title = _required_text(row["Title"], "Title")
    return {
        "publication_key": source_key,
        "canonical_key": canonical_key,
        "review_status": status,
        "tier": STATUS_TIERS[status],
        "first_observed_utc": first_observed_utc.isoformat().replace("+00:00", "Z"),
        "last_observed_utc": last_observed_utc.isoformat().replace("+00:00", "Z")
        if last_observed_utc else None,
        "publication_month": publication_month if publication_month else None,
        "discovered_on": first_observed_utc.date().isoformat(),
        "Title": title,
    }


def select_new_threads(rows: Any, *, baseline_utc: str, through_utc: str) -> dict[str, Any]:
    """Select first-discovery threads for rows first observed inside a window.

    ``baseline_utc`` is the exclusive lower bound and ``through_utc`` the
    inclusive upper bound. Rows at/below the baseline are returned under
    ``requires_catch_up`` (counts only, tiered) so that skipping them is an
    explicit, inspectable outcome rather than a silent drop.
    """
    baseline = _utc_instant(baseline_utc, "baseline_utc")
    through = _utc_instant(through_utc, "through_utc")
    if through < baseline:
        raise ValueError("through_utc must not predate baseline_utc")
    if not isinstance(rows, list):
        raise ValueError("rows must be a list of registry row objects")
    seen: set[str] = {}
    parsed: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        record = parse_registry_row(row)
        source_key = record["publication_key"]
        if source_key in seen:
            raise ValueError(f"row {index} repeats SourceKey {source_key!r}; input must stay idempotent")
        seen[source_key] = index
        parsed.append(record)

    new_threads: list[dict[str, Any]] = []
    requires_catch_up = {"confirmed": 0, "possible": 0, "rejected": 0}
    future_tier_counts = {"confirmed": 0, "possible": 0, "rejected": 0}
    in_window_excluded_count = 0
    for record in parsed:
        moment = datetime.fromisoformat(record["first_observed_utc"][:-1] + "+00:00")
        if moment > through:
            future_tier_counts[record["tier"]] += 1
            continue
        if moment <= baseline:
            requires_catch_up[record["tier"]] += 1
            continue
        if record["tier"] == "rejected":
            # Excluded rows stay stored elsewhere and are omitted from readers;
            # record the skip explicitly instead of dropping it silently.
            in_window_excluded_count += 1
            continue
        new_threads.append({
            "publication_key": record["publication_key"],
            "canonical_key": record["canonical_key"],
            "tier": record["tier"],
            "review_status": record["review_status"],
            "discovered_on": record["discovered_on"],
            "suggested_trigger": "first_discovery",
        })
    return {
        "new_threads": new_threads,
        "requires_catch_up_tier_counts": requires_catch_up,
        "future_tier_counts": future_tier_counts,
        "in_window_excluded_count": in_window_excluded_count,
        "total_parseable": len(parsed),
    }


def select_catch_up_threads(rows: Any, *, catch_up_from_utc: str, catch_up_to_utc: str) -> list[dict[str, Any]]:
    """Explicit backfill selection inside an inclusively bounded window.

    Only confirmed and possible rows become catch-up thread candidates;
    rejected rows are skipped, and both boundary instants are inclusive.
    """
    start = _utc_instant(catch_up_from_utc, "catch_up_from_utc")
    end = _utc_instant(catch_up_to_utc, "catch_up_to_utc")
    if end < start:
        raise ValueError("catch_up_to_utc must not predate catch_up_from_utc")
    if not isinstance(rows, list):
        raise ValueError("rows must be a list of registry row objects")
    seen: set[str] = set()
    selected: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        record = parse_registry_row(row)
        source_key = record["publication_key"]
        if source_key in seen:
            raise ValueError(f"row {index} repeats SourceKey {source_key!r}; input must stay idempotent")
        seen.add(source_key)
        moment = datetime.fromisoformat(record["first_observed_utc"][:-1] + "+00:00")
        if not start <= moment <= end or record["tier"] == "rejected":
            continue
        selected.append({
            "publication_key": source_key,
            "canonical_key": record["canonical_key"],
            "tier": record["tier"],
            "review_status": record["review_status"],
            "discovered_on": record["discovered_on"],
            "suggested_trigger": "catch_up",
        })
    return selected
