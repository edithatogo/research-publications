"""Canonical, review-gated grants and funding opportunities registry.

The module accepts already-collected RSS/Atom or API-shaped dictionaries. It
does not fetch external sites, submit applications, or infer eligibility.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    from .grants_deadline_schedule import canonical_object, normalize_schedule
except ImportError:
    from grants_deadline_schedule import canonical_object, normalize_schedule

OPPORTUNITY_KEY_PREFIXES = ("GRANT:", "GRANTX:")

_RFC3339_INSTANT = re.compile(
    r"^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d"
    r"(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
)
_LOCAL_INSTANT = re.compile(
    r"^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?$"
)
_TEXT_INPUT_FIELDS = {
    "Source", "SourceID", "ExternalID", "RoundID", "Title", "title", "URL",
    "Link", "link", "SourceRowURL", "Description", "Summary", "summary",
    "Eligibility", "Geography", "Amount", "Deadline", "ClosingDate", "deadline",
    "DeadlineTimezone", "deadlineTimezone", "deadline_timezone",
    "SourceTimezone", "sourceTimezone", "source_timezone", "Timezone", "timezone", "time_zone",
    "Status", "Contact", "DeadlineScheduleJSON", "SourceDateFactsJSON", "SourceAttribution",
    "CHHHSRelevance", "ReviewStatus", "ReviewNotes", "RetrievedUTC",
}


def parse_offset_instant(value: Any) -> datetime:
    """Parse a full RFC3339 instant and require its explicit UTC offset."""
    if not isinstance(value, str) or not _RFC3339_INSTANT.fullmatch(value):
        raise ValueError("timestamp must be a timezone-aware RFC3339 instant")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError("timestamp must be a timezone-aware RFC3339 instant") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be a timezone-aware RFC3339 instant")
    return parsed


def _text(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("canonical text fields must be text or null")
    return re.sub(r"\s+", " ", value.strip())


def _identity_text(value: Any) -> str:
    """Return a source identity verbatim after rejecting surrounding padding."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("canonical identity fields must be text or null")
    if value != value.strip():
        raise ValueError("canonical identity fields must be unpadded text")
    return value


def normalize_url(value: Any) -> str:
    raw = _text(value)
    if not raw:
        return ""
    parts = urlsplit(raw)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))


def normalize_source_row_url(value: Any) -> str:
    """Normalize a source-row provenance URL while preserving its fragment.

    Unlike ``URL``, this field identifies the specific row/anchor in the
    source system. Its fragment can distinguish rows on a shared page and is
    therefore retained; it is not used to derive OpportunityKey.
    """
    raw = _text(value)
    if not raw:
        return ""
    parts = urlsplit(raw)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, parts.fragment))


def valid_official_url(value: Any, allowed_hosts: Iterable[str]) -> bool:
    """Require an HTTPS row URL on an explicitly admitted authority host."""
    raw = str(value or "")
    if raw != raw.strip() or any(char.isspace() or ord(char) < 32 for char in raw):
        return False
    try:
        parts = urlsplit(raw)
        host = parts.hostname
        return (parts.scheme == "https" and bool(host) and host in set(allowed_hosts)
                and not parts.username and not parts.password and not parts.port)
    except ValueError:
        return False


def normalize_title(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _text(value).casefold())


def stable_key(record: dict[str, Any]) -> str:
    source = _identity_text(record.get("Source")) or "unknown"
    identifier = _identity_text(record.get("SourceID") or record.get("ExternalID"))
    round_id = _identity_text(record.get("RoundID"))
    # Keep every previously safe key byte-for-byte stable. The legacy basis
    # uses ':' and '|round:' as separators, so values containing either can
    # alias another (Source, SourceID, RoundID) tuple. Give only those tuples
    # a separate, unambiguous namespace; this is a key-scheme change for such
    # values and any existing tenant rows require explicit reconciliation.
    identity_values = (source, identifier, round_id)
    if (identifier or round_id) and any(char in value for value in identity_values for char in ":|"):
        encoded_identity = json.dumps(
            ["grant-stable-key/v2", source, identifier.casefold(),
             round_id.casefold() if round_id else None],
            ensure_ascii=False, separators=(",", ":"),
        )
        return "GRANTX:" + hashlib.sha256(encoded_identity.encode("utf-8")).hexdigest()[:24]
    if identifier:
        basis = f"{source}:{identifier.casefold()}"
    elif round_id:
        # A reviewed round can move to another official URL without becoming a
        # second opportunity. Scope the round identifier to its authority.
        basis = f"{source}:round:{round_id.casefold()}"
    elif normalize_url(record.get("URL")):
        basis = f"url:{normalize_url(record['URL'])}"
    else:
        basis = f"title:{normalize_title(record.get('Title'))}|funder:{normalize_title(record.get('Funder'))}"
    if identifier and round_id:
        # Round identity is case-insensitive in the round-only branch as well.
        # Keep distinct rounds distinct, but do not mint another key solely
        # because a source changes the case of its round identifier. Existing
        # persisted mixed-case round keys need an explicit old-to-new mapping
        # before any rekey; this function does not migrate tenant records.
        basis += '|round:' + round_id.casefold()
    return "GRANT:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]


def _date(value: Any) -> tuple[str | None, str]:
    raw = _text(value)
    if not raw:
        return None, "unknown"
    # A source-stated closing instant has an exact local calendar day. Keep
    # the instant and offset in DeadlineRaw; the date-only calendar projection
    # must not silently convert it to a different UTC day.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", raw):
        try:
            parsed = datetime.fromisoformat(raw[:-1] + "+00:00" if raw.endswith("Z") else raw)
            if parsed.utcoffset() is not None:
                return parsed.date().isoformat(), "day"
        except ValueError:
            pass
        return None, "unknown"
    match = re.fullmatch(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?", raw)
    if not match:
        return None, "unknown"
    year, month, day = match.groups()
    try:
        date(int(year), int(month or 1), int(day or 1))
    except ValueError:
        return None, 'unknown'
    if month and day:
        return f"{year}-{month}-{day}", "day"
    if month:
        return f"{year}-{month}", "month"
    return year, "year"


def _deadline_temporal_projection(value: Any, source_timezone: Any) -> dict[str, str | None]:
    """Preserve source-local deadline facts and derive exact Brisbane views.

    A named source zone is used only when supplied. Offset-bearing timestamps
    identify an instant; naive local timestamps require an IANA zone and are
    rejected as instants when they fall in a DST fold or gap.
    """
    raw = _text(value)
    zone_name = _text(source_timezone)
    projection: dict[str, str | None] = {
        "Deadline": None,
        "DeadlinePrecision": "unknown",
        "DeadlineTimezone": zone_name,
        "DeadlineLocalTime": "",
        "DeadlineUTCInstant": "",
        "DeadlineBrisbaneDate": "",
        "DeadlineBrisbaneTime": "",
        "DeadlineTemporalStatus": "unknown",
    }
    if not raw:
        return projection

    source_date, precision = _date(raw)
    if _RFC3339_INSTANT.fullmatch(raw):
        try:
            instant = parse_offset_instant(raw)
        except ValueError:
            projection["DeadlineTemporalStatus"] = "invalid"
            return projection
        explicit_zone = zone_name or ("UTC" if raw.endswith("Z") else "")
        local = instant
        status = "offset_only"
        if explicit_zone:
            try:
                zone = ZoneInfo(explicit_zone)
            except (ZoneInfoNotFoundError, ValueError):
                status = "invalid_timezone"
            else:
                local = instant.astimezone(zone)
                if (not raw.endswith("Z")
                        and local.utcoffset() != instant.utcoffset()):
                    status = "zone_offset_mismatch"
                    local = instant
                else:
                    status = "zone_resolved"
            projection["DeadlineTimezone"] = explicit_zone
        projection.update({
            "Deadline": local.date().isoformat(),
            "DeadlinePrecision": "day",
            "DeadlineLocalTime": local.timetz().replace(tzinfo=None).isoformat(),
            "DeadlineUTCInstant": instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "DeadlineTemporalStatus": status,
        })
        brisbane = instant.astimezone(ZoneInfo("Australia/Brisbane"))
        projection["DeadlineBrisbaneDate"] = brisbane.date().isoformat()
        projection["DeadlineBrisbaneTime"] = brisbane.timetz().replace(tzinfo=None).isoformat()
        return projection

    if _LOCAL_INSTANT.fullmatch(raw):
        try:
            naive = datetime.fromisoformat(raw)
        except ValueError:
            projection["DeadlineTemporalStatus"] = "invalid"
            return projection
        if not zone_name:
            # The source's calendar date and wall-clock text are still known
            # even when its zone is not. Preserve those facts for review, but
            # do not invent an instant or a Brisbane conversion.
            projection.update({
                "Deadline": naive.date().isoformat(),
                "DeadlinePrecision": "day",
                "DeadlineLocalTime": naive.time().isoformat(),
                "DeadlineTemporalStatus": "missing_timezone",
            })
            return projection
        try:
            zone = ZoneInfo(zone_name)
        except (ZoneInfoNotFoundError, ValueError):
            projection.update({
                "Deadline": naive.date().isoformat(),
                "DeadlinePrecision": "day",
                "DeadlineLocalTime": naive.time().isoformat(),
                "DeadlineTemporalStatus": "invalid_timezone",
            })
            return projection

        candidates: list[datetime] = []
        for fold in (0, 1):
            candidate = naive.replace(tzinfo=zone, fold=fold)
            round_trip = candidate.astimezone(timezone.utc).astimezone(zone)
            if round_trip.replace(tzinfo=None) == naive:
                candidates.append(candidate)
        offsets = {candidate.utcoffset() for candidate in candidates}
        projection.update({
            "Deadline": naive.date().isoformat(),
            "DeadlinePrecision": "day",
            "DeadlineTimezone": zone_name,
            "DeadlineLocalTime": naive.time().isoformat(),
        })
        if not candidates:
            projection["DeadlineTemporalStatus"] = "nonexistent_local_time"
            return projection
        if len(offsets) > 1:
            projection["DeadlineTemporalStatus"] = "ambiguous_local_time"
            return projection
        instant = candidates[0].astimezone(timezone.utc)
        brisbane = instant.astimezone(ZoneInfo("Australia/Brisbane"))
        projection.update({
            "DeadlineUTCInstant": instant.isoformat().replace("+00:00", "Z"),
            "DeadlineBrisbaneDate": brisbane.date().isoformat(),
            "DeadlineBrisbaneTime": brisbane.timetz().replace(tzinfo=None).isoformat(),
            "DeadlineTemporalStatus": "zone_resolved",
        })
        return projection

    if source_date is not None:
        status = "partial_date" if precision != "day" else "date_only"
        if zone_name:
            try:
                ZoneInfo(zone_name)
            except (ZoneInfoNotFoundError, ValueError):
                status = "invalid_timezone"
        projection["Deadline"] = source_date
        projection["DeadlinePrecision"] = precision
        projection["DeadlineTemporalStatus"] = status
        return projection

    projection["DeadlineTemporalStatus"] = "invalid"
    return projection


def _retrieved_utc(value: Any) -> tuple[str, str]:
    """Validate an observation timestamp without silently assuming a timezone."""
    raw = _text(value)
    if not raw:
        return datetime.now(timezone.utc).isoformat(), "generated"
    if _LOCAL_INSTANT.fullmatch(raw):
        return raw, "missing_timezone"
    try:
        parsed = parse_offset_instant(raw)
    except ValueError:
        return raw, "invalid"
    return parsed.astimezone(timezone.utc).isoformat(), "valid"


def _timestamp_sort_key(value: Any) -> datetime:
    try:
        parsed = parse_offset_instant(_text(value))
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def normalize_opportunity(record: dict[str, Any], retrieved_at: str | None = None) -> dict[str, Any]:
    """Normalize RSS/Atom/API-shaped records without inventing missing values."""
    if not isinstance(record, dict):
        raise ValueError("opportunity record must be an object")
    record = dict(record)
    classification_fields = {"FunderKey", "CategoryKeys", "CategoryKeysJSON"}
    if any(record.get(field) not in (None, "", []) for field in classification_fields):
        raise ValueError(
            "funder/category assignments require an evidence-backed reviewed classification contract"
        )
    for field in _TEXT_INPUT_FIELDS:
        if field in record and record[field] is not None and not isinstance(record[field], str):
            raise ValueError(f"{field} must be text or null")
    for field in ("Source", "SourceID", "ExternalID", "RoundID"):
        value = record.get(field)
        if isinstance(value, str) and value != value.strip():
            raise ValueError(f"{field} must be unpadded text")
    record['Title'] = record.get('Title') or record.get('title') or ''
    record['URL'] = record.get('URL') or record.get('Link') or record.get('link') or ''
    record['Funder'] = record.get('Funder') or record.get('Organization') or record.get('funder') or ''
    raw_deadline = record.get("Deadline") or record.get("ClosingDate") or record.get("deadline")
    timezone_aliases = [
        _text(record.get(field)) for field in (
            "DeadlineTimezone", "deadlineTimezone", "deadline_timezone",
            "SourceTimezone", "sourceTimezone", "source_timezone",
            "Timezone", "timezone", "time_zone",
        )
        if _text(record.get(field))
    ]
    timezone_conflict = len(set(timezone_aliases)) > 1
    deadline_temporal = _deadline_temporal_projection(
        raw_deadline, "" if timezone_conflict else (timezone_aliases[0] if timezone_aliases else ""),
    )
    if timezone_conflict:
        # Keep offset-defined instants and their Brisbane conversion, but do
        # not select one of two conflicting source-zone claims. A naive local
        # time remains unresolved and its stated date/time stays visible.
        deadline_temporal["DeadlineTimezone"] = ""
        deadline_temporal["DeadlineTemporalStatus"] = "timezone_conflict"
    retrieved, retrieved_status = _retrieved_utc(
        record.get("RetrievedUTC") if retrieved_at is None else retrieved_at
    )
    result = {
        "OpportunityKey": stable_key(record),
        "Title": _text(record.get("Title") or record.get("title")),
        "Funder": _text(record.get("Funder") or record.get("Organization") or record.get("funder")),
        "Source": _identity_text(record.get("Source")) or "unknown",
        "SourceID": _identity_text(record.get("SourceID") or record.get("ExternalID")),
        "RoundID": _identity_text(record.get('RoundID')),
        "URL": normalize_url(record.get("URL") or record.get("Link") or record.get("link")),
        "SourceRowURL": normalize_source_row_url(record.get("SourceRowURL")),
        "Description": _text(record.get("Description") or record.get("Summary") or record.get("summary")),
        "Eligibility": _text(record.get("Eligibility")),
        "Geography": _text(record.get("Geography")),
        "Amount": _text(record.get("Amount")),
        **deadline_temporal,
        "DeadlineRaw": _text(raw_deadline),
        "DeadlineScheduleJSON": normalize_schedule(record.get("DeadlineScheduleJSON"), record),
        "SourceDateFactsJSON": canonical_object(record.get("SourceDateFactsJSON")),
        "SourceAttribution": _text(record.get("SourceAttribution")),
        "Status": _text(record.get("Status")) or "Unknown",
        "Contact": _text(record.get("Contact")),
        "CHHHSRelevance": _text(record.get("CHHHSRelevance")) or "Unknown",
        "ReviewStatus": _text(record.get("ReviewStatus")) or "Needs Review",
        "ReviewNotes": _text(record.get("ReviewNotes")),
        "RetrievedUTC": retrieved,
        "RetrievedTimestampStatus": retrieved_status,
        "EvidenceHash": hashlib.sha256(repr(sorted(record.items())).encode("utf-8")).hexdigest(),
    }
    if not result["Title"] or not result["URL"] or retrieved_status != "valid":
        result["ReviewStatus"] = "Needs Review"
    return result


def merge_observations(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge exact stable keys while retaining source-specific observations."""
    grouped: dict[str, dict[str, Any]] = {}
    for raw in records:
        normalized = normalize_opportunity(raw, raw.get("RetrievedUTC"))
        key = normalized["OpportunityKey"]
        if key not in grouped:
            grouped[key] = {**normalized, "SourceObservations": []}
        elif _timestamp_sort_key(normalized["RetrievedUTC"]) >= _timestamp_sort_key(grouped[key]["RetrievedUTC"]):
            prior = grouped[key]
            preserved_review = prior.get("ReviewStatus") not in (None, "", "Needs Review")
            grouped[key] = {
                **normalized,
                "ReviewStatus": prior.get("ReviewStatus") if preserved_review else normalized["ReviewStatus"],
                "ReviewNotes": prior.get("ReviewNotes") if preserved_review else normalized["ReviewNotes"],
                "SourceObservations": prior["SourceObservations"],
            }
        # Source recency governs the observed fields, not a human review
        # decision. An older reviewed observation can arrive after a newer
        # unreviewed one without erasing that decision or replacing the facts.
        if (grouped[key].get("ReviewStatus") in (None, "", "Needs Review")
                and normalized["ReviewStatus"] not in (None, "", "Needs Review")):
            grouped[key]["ReviewStatus"] = normalized["ReviewStatus"]
            grouped[key]["ReviewNotes"] = normalized["ReviewNotes"]
        grouped[key]["SourceObservations"].append({
            "Source": normalized["Source"], "SourceID": normalized["SourceID"],
            "URL": normalized["URL"], "RetrievedUTC": normalized["RetrievedUTC"],
            "SourceRowURL": normalized["SourceRowURL"],
            "EvidenceHash": normalized["EvidenceHash"],
            "Snapshot": dict(normalized),
        })
        if grouped[key]["Title"] == "" and normalized["Title"]:
            grouped[key]["Title"] = normalized["Title"]
    return sorted(grouped.values(), key=lambda item: (item["Deadline"] or "9999", item["Title"].casefold()))


def sharepoint_field_map(record: dict[str, Any]) -> dict[str, Any]:
    """Map the canonical record to stable display names for a future list."""
    return {field: record.get(field) for field in (
        "OpportunityKey", "Title", "Funder", "Source", "SourceID", "RoundID", "URL", "SourceRowURL", "Description",
        "Eligibility", "Geography", "Amount", "Deadline", "DeadlineRaw",
        "DeadlineTimezone", "DeadlineLocalTime", "DeadlineUTCInstant",
        "DeadlineBrisbaneDate", "DeadlineBrisbaneTime", "DeadlineTemporalStatus",
        "DeadlinePrecision", "DeadlineScheduleJSON", "SourceDateFactsJSON", "SourceAttribution",
        "Status", "Contact", "CHHHSRelevance", "ReviewStatus", "ReviewNotes", "RetrievedUTC",
        "RetrievedTimestampStatus", "EvidenceHash",
    )}
