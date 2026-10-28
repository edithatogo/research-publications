"""Deterministic, advisory reconciliation cases; never mutates publication records."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any
from urllib.parse import parse_qsl, urlsplit

PROMPT_VERSION = "publication-reconciliation-advisory-v1"
ISSUES = {
    "identity_conflict",
    "metadata_conflict",
    "missing_evidence",
    "possible_duplicate",
}
RECOMMENDATIONS = {
    "keep_separate",
    "possible_duplicate",
    "correct_field",
    "needs_more_evidence",
    "no_recommendation",
}
POSITIVE = {"possible_duplicate", "correct_field"}


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    return value


@dataclass(frozen=True)
class ReconciliationCase:
    case_id: str
    source_fingerprint: str
    rule_version: str
    source_revision: str
    issue: str
    records: tuple[Mapping[str, Any], ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class ValidatedSuggestion:
    case_id: str
    source_fingerprint: str
    prompt_version: str
    recommendation: str
    candidate_record_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    reasoning: str
    uncertainty: str


@dataclass(frozen=True)
class ProcessResult:
    case: ReconciliationCase
    status: str
    suggestion: ValidatedSuggestion | None


def build_case(
    records, issue: str, rule_version: str, source_revision: str
) -> ReconciliationCase:
    """Build immutable case from 1..20 records; each record has record_id, source_key,
    values, evidence=[{evidence_id,url,excerpt?}]. Records are canonicalized by record_id.
    """
    if (
        issue not in ISSUES
        or not isinstance(rule_version, str)
        or not rule_version.strip()
        or not isinstance(source_revision, str)
        or not source_revision.strip()
    ):
        raise ValueError("invalid issue, rule_version, or source_revision")
    if not isinstance(records, (list, tuple)) or not 1 <= len(records) <= 20:
        raise ValueError("records must contain 1..20 items")
    clean = []
    all_evidence = []
    ids = set()
    for rec in records:
        if not isinstance(rec, Mapping) or set(rec) != {
            "record_id",
            "source_key",
            "values",
            "evidence",
        }:
            raise ValueError(
                "record shape must be record_id, source_key, values, evidence"
            )
        rid, sk, vals, evs = (
            rec["record_id"],
            rec["source_key"],
            rec["values"],
            rec["evidence"],
        )
        if (
            not isinstance(rid, str)
            or not rid.strip()
            or rid != rid.strip()
            or rid in ids
        ):
            raise ValueError("record_id must be unique, nonblank canonical text")
        if (
            not isinstance(sk, str)
            or not sk.strip()
            or sk != sk.strip()
            or not isinstance(vals, Mapping)
        ):
            raise ValueError("source_key must be canonical text and values an object")
        if not isinstance(evs, (list, tuple)) or len(evs) > 50:
            raise ValueError("evidence must contain at most 50 items per record")
        ids.add(rid)
        evidence = []
        for item in evs:
            if (
                not isinstance(item, Mapping)
                or set(item) - {"evidence_id", "url", "excerpt"}
                or not {"evidence_id", "url"} <= set(item)
            ):
                raise ValueError(
                    "evidence shape must include evidence_id and url, with optional excerpt"
                )
            eid, url = item["evidence_id"], item["url"]
            parts = urlsplit(url) if isinstance(url, str) else None
            query_keys = (
                {
                    key.lower()
                    for key, _ in parse_qsl(parts.query, keep_blank_values=True)
                }
                if parts
                else set()
            )
            if (
                not isinstance(eid, str)
                or not eid.strip()
                or eid != eid.strip()
                or eid in all_evidence
            ):
                raise ValueError(
                    "evidence IDs must be unique canonical text across case"
                )
            if (
                not parts
                or parts.scheme != "https"
                or not parts.hostname
                or parts.username
                or parts.password
                or any(ord(ch) < 32 or ord(ch) == 127 for ch in url)
                or query_keys.intersection(
                    {
                        "sig",
                        "token",
                        "access_token",
                        "api_key",
                        "key",
                        "code",
                        "client_secret",
                    }
                )
            ):
                raise ValueError(
                    "evidence URL must be HTTPS and contain no credentials"
                )
            if "excerpt" in item and not isinstance(item["excerpt"], str):
                raise ValueError("excerpt must be text")
            all_evidence.append(eid)
            evidence.append(
                {
                    "evidence_id": eid,
                    "url": url,
                    **({"excerpt": item["excerpt"]} if "excerpt" in item else {}),
                }
            )
        evidence.sort(key=lambda x: x["evidence_id"])
        clean.append(
            {
                "record_id": rid,
                "source_key": sk,
                "values": _plain(vals),
                "evidence": evidence,
            }
        )
    clean.sort(key=lambda x: x["record_id"])
    fingerprint = hashlib.sha256(
        _canonical({"records": clean, "source_revision": source_revision}).encode()
    ).hexdigest()
    case_id = hashlib.sha256(
        _canonical(
            {
                "records": clean,
                "rule_version": rule_version,
                "source_revision": source_revision,
                "issue": issue,
            }
        ).encode()
    ).hexdigest()
    return ReconciliationCase(
        case_id,
        fingerprint,
        rule_version,
        source_revision,
        issue,
        tuple(_freeze(x) for x in clean),
        tuple(sorted(all_evidence)),
    )


def validate_ai_result(
    case: ReconciliationCase, result: Mapping[str, Any]
) -> ValidatedSuggestion:
    """Validate an untrusted advisory payload. Text is data; no instructions are executed."""
    required = {
        "case_id",
        "source_fingerprint",
        "recommendation",
        "candidate_record_ids",
        "evidence_ids",
        "reasoning",
        "uncertainty",
    }
    if not isinstance(result, Mapping) or set(result) != required:
        raise ValueError("response has unknown or missing fields")
    if (
        result["case_id"] != case.case_id
        or result["source_fingerprint"] != case.source_fingerprint
    ):
        raise ValueError("stale or mismatched case")
    rec = result["recommendation"]
    if rec not in RECOMMENDATIONS:
        raise ValueError("unknown recommendation")
    record_ids = {x["record_id"] for x in case.records}
    evidence_ids = set(case.evidence_ids)
    candidates, refs = result["candidate_record_ids"], result["evidence_ids"]
    if (
        not isinstance(candidates, list)
        or len(set(candidates)) != len(candidates)
        or any(x not in record_ids for x in candidates)
    ):
        raise ValueError("unknown or malformed candidate record IDs")
    if (
        not isinstance(refs, list)
        or len(set(refs)) != len(refs)
        or any(x not in evidence_ids for x in refs)
    ):
        raise ValueError("unknown or malformed evidence references")
    if rec in POSITIVE and (not candidates or not refs):
        raise ValueError("positive proposal requires record and evidence references")
    if rec in {"keep_separate", "needs_more_evidence"} and not candidates:
        raise ValueError("substantive recommendation requires record references")
    if rec == "keep_separate" and not refs:
        raise ValueError("keep_separate requires evidence references")
    if rec == "needs_more_evidence" and refs and not candidates:
        raise ValueError("evidence references require a candidate record")
    if any(
        not isinstance(result[key], str)
        or not result[key].strip()
        or len(result[key]) > 4000
        for key in ("reasoning", "uncertainty")
    ):
        raise ValueError(
            "reasoning and uncertainty must be nonblank text of at most 4000 characters"
        )
    return ValidatedSuggestion(
        case.case_id,
        case.source_fingerprint,
        PROMPT_VERSION,
        rec,
        tuple(candidates),
        tuple(refs),
        result["reasoning"],
        result["uncertainty"],
    )


def process_ai_result(
    case: ReconciliationCase, result=None, error=None, existing_suggestion=None
) -> ProcessResult:
    """Reuse a current validated result; otherwise validate response and fail closed to review."""
    if existing_suggestion is not None and (
        isinstance(existing_suggestion, ValidatedSuggestion)
        and existing_suggestion.case_id == case.case_id
        and existing_suggestion.source_fingerprint == case.source_fingerprint
        and existing_suggestion.prompt_version == PROMPT_VERSION
    ):
        cached = {
            "case_id": existing_suggestion.case_id,
            "source_fingerprint": existing_suggestion.source_fingerprint,
            "recommendation": existing_suggestion.recommendation,
            "candidate_record_ids": list(existing_suggestion.candidate_record_ids),
            "evidence_ids": list(existing_suggestion.evidence_ids),
            "reasoning": existing_suggestion.reasoning,
            "uncertainty": existing_suggestion.uncertainty,
        }
        try:
            validated = validate_ai_result(case, cached)
        except (TypeError, ValueError):
            pass
        else:
            return ProcessResult(case, "needs_human_review", validated)
    # A changed source/case/prompt invalidates prior output; do not accept it.
    if error is not None:
        return ProcessResult(case, "unavailable", None)
    if result is None:
        return ProcessResult(case, "unavailable", None)
    try:
        suggestion = validate_ai_result(case, result)
    except (TypeError, ValueError):
        return ProcessResult(case, "invalid", None)
    return ProcessResult(case, "needs_human_review", suggestion)


IDENTITY_EXCEPTIONS = {
    "invalid-identifiers-needs-review": "identity_conflict",
    "conflicting-identifiers-needs-review": "identity_conflict",
    "ambiguous-identifiers-needs-review": "identity_conflict",
    "ambiguous-title+year": "possible_duplicate",
    "possible-title+year-needs-review": "possible_duplicate",
}


def cases_from_canonical(rows, *, source_revision, rule_version, complete):
    """Adapt the existing CanonicalPublications identity signals for preparation.

    No matching, adjudication, admission or source inference occurs here. Callers
    must supply a complete, revision-bound snapshot. Missing source links remain
    missing; AI can request evidence but cannot invent it. Native integration
    must use the same producer and retain paging rather than truncate at 20.
    """
    if complete is not True or not isinstance(rows, list):
        raise ValueError("complete canonical snapshot required")
    if (
        not isinstance(source_revision, str)
        or not source_revision.strip()
        or not isinstance(rule_version, str)
        or not rule_version.strip()
    ):
        raise ValueError("source and rule revisions required")
    seen = set()
    selected = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("canonical rows must be objects")  # noqa: TRY004 - retained validator ValueError contract
        key, method = row.get("CanonicalKey"), row.get("DedupMethod")
        if (
            not isinstance(key, str)
            or not key.strip()
            or key != key.strip()
            or key in seen
        ):
            raise ValueError("unique canonical record identity required")
        if not isinstance(method, str) or not method.strip():
            raise ValueError("canonical DedupMethod required")
        seen.add(key)
        if method not in IDENTITY_EXCEPTIONS:
            if (
                "needs-review" in method
                or "ambiguous" in method
                or "conflicting" in method
            ):
                raise ValueError(
                    "unknown exception signal; qualify producer rule before continuing"
                )
            continue
        evidence = []
        for field in ("PubMedURL", "DORAURL"):
            raw = row.get(field)
            if raw is None or raw == "":
                continue
            if not isinstance(raw, str):
                raise ValueError("source links must be text")  # noqa: TRY004 - retained validator ValueError contract
            for url in raw.split("; "):
                eid = hashlib.sha256((key + "\n" + url).encode()).hexdigest()
                if any(item["evidence_id"] == eid for item in evidence):
                    continue
                evidence.append({"evidence_id": eid, "url": url})
        # This is a canonical-view locator, not an inferred registry SourceKey.
        record = {
            "record_id": key,
            "source_key": "canonical:" + key,
            "values": row,
            "evidence": evidence,
        }
        selected.append(
            build_case(
                [record], IDENTITY_EXCEPTIONS[method], rule_version, source_revision
            )
        )
    return tuple(sorted(selected, key=lambda case: case.case_id))
