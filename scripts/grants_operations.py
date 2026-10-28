"""Fail-closed local operational checks for a future grants ingestion run."""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Iterable, Mapping

try:
    from .grants_registry import parse_offset_instant
except ImportError:  # direct script execution with scripts/ on sys.path
    from grants_registry import parse_offset_instant


def evaluate_source_freshness(
    health: Iterable[dict[str, Any]],
    source_policy: Mapping[str, Mapping[str, Any]],
    *,
    now: datetime,
) -> dict[str, Any]:
    """Check required source ownership and freshness against an explicit policy.

    Each policy entry is keyed by source id and contains ``owner`` and
    ``max_age_seconds``. Health rows must contain matching ``source``,
    ``owner``, ``status`` and ISO-8601 ``checked_at`` fields. This deliberately
    does not infer freshness from catalogue verification dates.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if not isinstance(source_policy, Mapping):
        return {
            "status": "unhealthy",
            "errors": ["policy:not_mapping"],
            "sources": [],
            "unexpected_sources": [],
            "malformed_health_rows": 0,
        }
    rows = list(health)
    by_source: dict[str, list[dict[str, Any]]] = {}
    malformed_count = 0
    for row in rows:
        if not isinstance(row, dict):
            malformed_count += 1
            continue
        source = row.get("source")
        if isinstance(source, str) and source and source == source.strip():
            by_source.setdefault(source, []).append(row)
        else:
            malformed_count += 1

    results = []
    errors = []
    for source, policy in source_policy.items():
        if not isinstance(source, str) or not source or source != source.strip():
            errors.append("policy:source_id_invalid")
            continue
        issues = []
        matches = by_source.get(source, [])
        if not matches:
            issues.append("missing_health")
            row = {}
        elif len(matches) != 1:
            issues.append("duplicate_health")
            row = matches[0]
        else:
            row = matches[0]
        if not isinstance(policy, Mapping):
            issues.append("invalid_policy_entry")
            policy = {}
        expected_owner = policy.get("owner")
        max_age = policy.get("max_age_seconds")
        if (not isinstance(expected_owner, str) or not expected_owner
                or expected_owner != expected_owner.strip()):
            issues.append("policy_owner_invalid")
        elif row.get("owner") != expected_owner:
            issues.append("owner_mismatch")
        if (not isinstance(max_age, (int, float)) or isinstance(max_age, bool)
                or not math.isfinite(max_age) or max_age <= 0):
            issues.append("invalid_freshness_policy")
        if row.get("status") != "succeeded":
            issues.append("source_failure")
        checked_raw = row.get("checked_at")
        checked = None
        if not isinstance(checked_raw, str):
            issues.append("checked_at_missing")
        else:
            try:
                checked = parse_offset_instant(checked_raw)
                checked = checked.astimezone(timezone.utc)
            except ValueError:
                issues.append("checked_at_invalid")
                checked = None
        age_seconds = None
        if checked is not None:
            age_seconds = (now.astimezone(timezone.utc) - checked).total_seconds()
            if age_seconds < 0:
                issues.append("checked_at_in_future")
            elif (isinstance(max_age, (int, float)) and not isinstance(max_age, bool)
                  and math.isfinite(max_age) and max_age > 0 and age_seconds > max_age):
                issues.append("stale")
        errors.extend(f"{source}:{issue}" for issue in issues)
        results.append({
            "source": source,
            "owner": row.get("owner"),
            "checked_at": checked.isoformat().replace("+00:00", "Z") if checked else None,
            "age_seconds": age_seconds,
            "max_age_seconds": max_age,
            "status": "healthy" if not issues else "unhealthy",
            "issues": issues,
        })
    unexpected = sorted(set(by_source) - set(source_policy))
    errors.extend(f"{source}:unexpected_health" for source in unexpected)
    if malformed_count:
        errors.append("health:source_id_missing")
    return {"status": "healthy" if not errors else "unhealthy", "errors": errors,
            "sources": results, "unexpected_sources": unexpected,
            "malformed_health_rows": malformed_count}


def evaluate_run(records: Iterable[dict[str, Any]], health: Iterable[dict[str, Any]], prior_records=None,
                 *, source_policy: Mapping[str, Mapping[str, Any]] | None = None,
                 now: datetime | None = None, verified_empty: bool = False):
    records = list(records)
    health = list(health)
    if prior_records is not None:
        prior_records = list(prior_records)
    errors = []
    if not health:
        errors.append("source_health_missing")
    if not records and verified_empty is not True:
        errors.append('empty_batch')
    if any(not isinstance(row, dict) for row in records):
        errors.append('malformed_record')
    keys = [row.get('OpportunityKey') if isinstance(row, dict) else None for row in records]
    if any(not isinstance(key, str) or not key.strip() for key in keys):
        errors.append('missing_opportunity_key')
    if any(isinstance(key, str) and key != key.strip() for key in keys):
        errors.append('padded_opportunity_key')
    valid_keys = [key for key in keys if isinstance(key, str) and key.strip()]
    if len(valid_keys) != len(set(valid_keys)):
        errors.append('duplicate_opportunity_key')
    # A replay may carry a different supplied key for the same exact source
    # observation. Do not silently create a second opportunity or rewrite the
    # persisted key: require an explicit reviewed migration instead.
    evidence_keys: dict[tuple[str, str, str], str] = {}
    for row in [*records, *(prior_records or [])]:
        if not isinstance(row, dict):
            continue
        identity_fields = ('Source', 'SourceID', 'EvidenceHash')
        identity_values = [row.get(field) for field in identity_fields]
        malformed_identity = any(
            value is not None and (
                not isinstance(value, str) or value != value.strip()
            ) for value in identity_values
        )
        if malformed_identity:
            errors.append('malformed_source_evidence_identity')
            continue
        identity = tuple(value or '' for value in identity_values)
        key = row.get('OpportunityKey')
        if not all(identity) or not isinstance(key, str) or not key.strip():
            continue
        prior_key = evidence_keys.setdefault(identity, key)
        if prior_key != key:
            errors.append('conflicting_opportunity_key_for_source_evidence')
            break
    for item in health:
        if not isinstance(item, dict) or item.get('status') != 'succeeded':
            errors.append('source_failure')
        source = item.get('source') if isinstance(item, dict) else None
        if not isinstance(source, str) or not source or source != source.strip():
            errors.append('invalid_source_identity')
    freshness = None
    if source_policy is not None:
        if now is None:
            raise ValueError("now is required when source_policy is supplied")
        freshness = evaluate_source_freshness(health, source_policy, now=now)
        errors.extend(f"source_health:{error}" for error in freshness["errors"])
    accepted = not errors
    # An explicitly supplied empty snapshot is still a rollback target. Keep
    # its presence separate from its truthiness so receipts accurately record
    # that the pre-run state was preserved (even when that state had zero rows).
    has_prior_snapshot = prior_records is not None
    return {
        'status': 'accepted' if accepted else 'rejected',
        'errors': errors,
        'records': records if accepted else list(prior_records or []),
        'preserved_prior': bool(errors and has_prior_snapshot),
        'verified_empty': bool(not records and verified_empty is True and not errors),
        'source_health': freshness,
    }
