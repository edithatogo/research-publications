"""E09 Phase 4 first-discovery editions and cadence behaviour (local).

Deterministic edition selection over the committed Phase 1 subscription
preferences and the Phase 2 first-discovery selection outputs. The module is
local preparation for the later cloud-flow authoring; it sends nothing.

Semantics encoded here, fail-closed:

* only ``active`` subscriptions with cadence ``weekly`` or ``daily`` produce
  editions; ``off`` cadence and ``paused``/``withdrawn`` status produce an
  explicit empty outcome with the reason recorded, never silence;
* enrolment is a boundary, not a backfill: only first-discoveries with
  ``discovered_on >= enrolled_on`` (inclusive at the boundary day) are
  eligible, and anything earlier is counted so the skip is inspectable;
* windows are Brisbane-calendar windows (Australia/Brisbane, fixed UTC+10
  offset, no DST): a daily edition covers one calendar day, a weekly edition
  covers Monday through Sunday of the ISO week containing the discovery date;
* duplicate recovery is explicit: a publication already delivered for the
  subscription is skipped and counted, and repeated keys inside one input
  batch still fail closed so re-reads stay idempotent;
* every edition carries ``edition_kind`` ``first_discovery_feed`` and
  ``intended_outcome`` ``no_send`` with a null delivery authority — a real
  send stays behind the Phase 1 receipt contract's explicit
  ``delivery_authority_reference`` and recorded delivery authority;
* identical inputs produce byte-identical editions (no generated timestamps),
  so interrupted or repeated runs reconcile exactly.

The editorial digest is not touched; this module composes only the separate
first-discovery feed edition contract named in the track plan.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from scripts.e09_feed_contracts import (
    _required_identifier,
    publication_source_key,
    validate_subscription_preference,
)
from scripts.e09_first_discovery import STATUS_TIERS, _canonical_key

EDITION_KIND = "first_discovery_feed"
SELECTION_FIELDS = {
    "publication_key", "canonical_key", "tier", "review_status",
    "discovered_on", "suggested_trigger",
}
EDITION_FIELDS = {
    "edition_kind", "subscription_id", "subscriber_urn", "cadence",
    "window_start", "window_end", "publications", "publication_count",
    "intended_outcome", "delivery_authority_reference",
}


def _iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be YYYY-MM-DD text")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be a real YYYY-MM-DD date") from error
    return parsed


def _week_monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _window_for(cadence: str, day: date) -> dict[str, str]:
    if cadence == "daily":
        return {"start": day.isoformat(), "end": day.isoformat()}
    if cadence == "weekly":
        monday = _week_monday(day)
        return {"start": monday.isoformat(), "end": (monday + timedelta(days=6)).isoformat()}
    raise ValueError(f"cadence {cadence!r} does not produce editions")


def _parse_discovered(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("discovered records must be a list of first-discovery selection records")
    parsed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"discovered record {index} must be an object")
        unknown = set(row) - SELECTION_FIELDS
        if unknown:
            raise ValueError(f"discovered record {index} has fields outside the selection shape: {sorted(unknown)}")
        missing = SELECTION_FIELDS - set(row)
        if missing:
            raise ValueError(f"discovered record {index} is missing selection fields: {sorted(missing)}")
        key = publication_source_key(row["publication_key"], f"discovered record {index} publication_key")
        if key in seen:
            raise ValueError(f"discovered record {index} repeats publication_key {key!r}")
        seen.add(key)
        tier = row["tier"]
        if not isinstance(tier, str) or tier not in {"confirmed", "possible"}:
            raise ValueError(f"discovered record {index} tier {tier!r} is not thread-eligible")
        if not isinstance(row['review_status'], str) or STATUS_TIERS.get(row['review_status']) != tier:
            raise ValueError('Edition review status and tier disagree')
        _canonical_key(row['canonical_key'])
        if not isinstance(row['suggested_trigger'], str) or row['suggested_trigger'] not in {'first_discovery', 'catch_up'}:
            raise ValueError('Qualified selection trigger required')
        parsed.append({
            "publication_key": key,
            "discovered_on": _iso_date(row["discovered_on"], f"discovered record {index} discovered_on"),
            "tier": tier,
        })
    return parsed


def build_first_discovery_editions(
    subscription: Any,
    discovered: Any,
    *,
    already_delivered: Any = (),
) -> dict[str, Any]:
    """Build one subscription's first-discovery feed editions (no-send).

    ``subscription`` must satisfy the Phase 1 storage contract
    (``validate_subscription_preference``). ``discovered`` holds first-discovery
    selection records (Phase 2 output shape). ``already_delivered`` holds
    publication keys already receipt-delivered for this subscription; they are
    skipped with an explicit count for duplicate recovery.
    """
    preference = validate_subscription_preference(subscription)
    if not isinstance(already_delivered, (list, set, tuple, frozenset)):
        raise ValueError("already_delivered must be a collection of publication keys")
    delivered = set(already_delivered)

    skip = {
        "cadence_off": 0, "subscription_paused_or_withdrawn": 0,
        "enrolment_boundary": 0, "already_delivered": 0,
    }
    cadence = preference["cadence"]
    status = preference["status"]
    if cadence == "off" or status != "active":
        skip["cadence_off" if cadence == "off" else "subscription_paused_or_withdrawn"] = len(
            _parse_discovered(discovered))
        return {"editions": [], "skip_counts": skip, "edition_kind": EDITION_KIND}

    eligible = _parse_discovered(discovered)
    enrolled_on = _iso_date(preference["enrolled_on"], "enrolled_on")
    windows: dict[tuple[str, str], dict[str, Any]] = {}
    for record in eligible:
        if record["publication_key"] in delivered:
            skip["already_delivered"] += 1
            continue
        if record["discovered_on"] < enrolled_on:
            skip["enrolment_boundary"] += 1
            continue
        window = _window_for(cadence, record["discovered_on"])
        bucket = windows.setdefault((window["start"], window["end"]), {
            "window": window, "publication_keys": [], "tiers": {},
        })
        bucket["publication_keys"].append(record["publication_key"])
        bucket["tiers"][record["publication_key"]] = record["tier"]

    editions = []
    for (start, end) in sorted(windows):
        bucket = windows[(start, end)]
        keys = sorted(bucket["publication_keys"])
        editions.append({
            "edition_kind": EDITION_KIND,
            "subscription_id": preference["subscription_id"],
            "subscriber_urn": preference["subscriber_urn"],
            "cadence": cadence,
            "window_start": start,
            "window_end": end,
            "publications": [
                {"publication_key": key, "tier": bucket["tiers"][key]} for key in keys
            ],
            "publication_count": len(keys),
            "intended_outcome": "no_send",
            "delivery_authority_reference": None,
        })
    return {"editions": editions, "skip_counts": skip, "edition_kind": EDITION_KIND}


def enum_empty_windows(cadence: Any, start_date: Any, end_date: Any) -> list[dict[str, str]]:
    """Enumerate consecutive cadence windows inside a reporting span (inclusive).

    Lets a caller emit explicit empty editions for slots with no new
    first-discoveries, so silence is distinguishable from an empty edition.
    """
    cadence = _required_identifier(cadence, "cadence")
    if cadence not in {"weekly", "daily"}:
        raise ValueError("only weekly and daily cadences produce windows")
    start = _iso_date(start_date, "start_date")
    end = _iso_date(end_date, "end_date")
    if end < start:
        raise ValueError("end_date must not predate start_date")
    windows: list[dict[str, str]] = []
    if cadence == "daily":
        day = start
        while day <= end:
            windows.append({"start": day.isoformat(), "end": day.isoformat()})
            day += timedelta(days=1)
        return windows
    first_monday, last_monday = _week_monday(start), _week_monday(end)
    monday = first_monday
    while monday <= last_monday:
        windows.append({"start": monday.isoformat(), "end": (monday + timedelta(days=6)).isoformat()})
        monday += timedelta(days=7)
    return windows
