"""Validate university source and institutional-deadline discovery records."""
from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from datetime import date
from datetime import datetime
from typing import Any, Callable, Iterable

try:
    from .grants_registry import OPPORTUNITY_KEY_PREFIXES, valid_official_url
except ImportError:  # direct script execution
    from grants_registry import OPPORTUNITY_KEY_PREFIXES, valid_official_url

REQUIRED_INSTITUTIONS = {"jcu", "uq", "qut", "griffith"}
SUPPORTED_FORMATS = {"rss", "atom", "api", "csv", "xlsx", "html"}
SUPPORTED_LEAD_TIME_UNITS = {"business_days", "working_days", "calendar_days", "weeks"}
INSTITUTION_SOURCE_HOSTS = {
    "jcu": {"www.jcu.edu.au"},
    "uq": {"research-support.uq.edu.au", "policies.uq.edu.au"},
    "qut": {"mopp.qut.edu.au", "www.mopp.qut.edu.au"},
    "griffith": {"www.griffith.edu.au"},
}
# This publisher-search evidence is catalogue-only; it does not add a host to
# the allowed institutional fact or automated intake sources.
CURRENT_POLICY_SEARCH = "https://policies.griffith.edu.au/?collection=griff~sp-policy-library&form=custom&profile=_default&query=External+Research+Funding+Management"
CURRENT_POLICY_EFFECTIVE = "2025-01-01"
RFC3339_INSTANT = re.compile(
    r"^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d"
    r"(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
)
INSTITUTION_FACT_FIELDS = {
    "fact_id", "institution_id", "OpportunityKey", "entitlement_status",
    "format", "evidence_url", "observed_at", "review_status", "eligibility",
    "policy_provenance", "internal_deadlines",
}
OPPORTUNITY_KEY_RE = re.compile(
    rf"(?:{'|'.join(re.escape(prefix[:-1]) for prefix in OPPORTUNITY_KEY_PREFIXES)}):[0-9a-f]{{24}}"
)


def _parse_aware_instant(value: Any, field: str) -> datetime:
    """Parse a strict timestamp with an explicit UTC offset."""
    if not isinstance(value, str) or not RFC3339_INSTANT.fullmatch(value):
        raise ValueError(f"{field} must be a timezone-aware RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise ValueError(f"{field} must be a timezone-aware RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware RFC3339 timestamp")
    return parsed


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _required_identifier(value: Any, field: str) -> str:
    """Require canonical identity text instead of silently trimming aliases."""
    text = _required_text(value, field)
    if value != text:
        raise ValueError(f"{field} must not include surrounding whitespace")
    return text


def _full_iso_date(value: Any) -> date:
    """Parse only canonical YYYY-MM-DD dates, not other fromisoformat forms."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("full ISO date must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("full ISO date must be a real YYYY-MM-DD calendar date") from exc


def _canonical_sha256(value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _is_private_ops_ref(value: Any) -> bool:
    """Accept a relative private/ops path without traversal or separator tricks."""
    if not isinstance(value, str) or not value.startswith("private/ops/") or "\\" in value:
        return False
    parts = value.split("/")
    return len(parts) >= 3 and parts[:2] == ["private", "ops"] and all(
        part not in {"", ".", ".."} for part in parts[2:]
    )


def validate_reviewed_fact_receipt(
    receipt: Any,
    *,
    verify_evidence: Callable[[dict[str, Any]], bool] | None = None,
    verify_reviewer: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    """Validate a local receipt envelope, requiring an external identity verifier.

    This is an untrusted validation seam, not a production trust boundary. It
    does not import or persist facts. Injected callbacks must be supplied only
    by an approved caller that independently reads/verifies the referenced
    artifacts and identities; arbitrary callbacks (including test lambdas) do
    not establish provenance.
    """
    if not isinstance(receipt, dict) or set(receipt) != {
        "schema_version", "receipt_id", "fact", "fact_sha256", "evidence", "reviewer",
    }:
        raise ValueError("reviewed fact receipt has invalid top-level schema")
    if receipt["schema_version"] != "g05-reviewed-fact-receipt/v1":
        raise ValueError("reviewed fact receipt schema_version is unsupported")
    receipt_id = receipt.get("receipt_id")
    if not isinstance(receipt_id, str) or not re.fullmatch(r"G05R-[A-Za-z0-9-]{8,80}", receipt_id):
        raise ValueError("reviewed fact receipt receipt_id is invalid")
    fact = receipt.get("fact")
    fact_fields = {
        "fact_id", "institution_id", "OpportunityKey", "entitlement_status", "format",
        "evidence_url", "observed_at", "review_status", "eligibility", "policy_provenance",
        "internal_deadlines",
    }
    if not isinstance(fact, dict) or set(fact) != fact_fields:
        raise ValueError("reviewed fact receipt needs bound fact identity")
    try:
        fact_id = _required_identifier(fact.get("fact_id"), "reviewed fact receipt fact_id")
        institution_id = _required_identifier(
            fact.get("institution_id"), "reviewed fact receipt institution_id")
        opportunity_key = _required_identifier(
            fact.get("OpportunityKey"), "reviewed fact receipt OpportunityKey")
    except ValueError as exc:
        raise ValueError("reviewed fact receipt needs bound fact identity") from exc
    if not OPPORTUNITY_KEY_RE.fullmatch(opportunity_key):
        raise ValueError("reviewed fact receipt needs a canonical OpportunityKey")
    if institution_id not in INSTITUTION_SOURCE_HOSTS:
        raise ValueError("reviewed fact receipt institution is unsupported")
    digest = receipt.get("fact_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("reviewed fact receipt fact_sha256 is invalid")
    if _canonical_sha256(fact) != digest:
        raise ValueError("reviewed fact receipt fact hash mismatch")
    evidence = receipt.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != {"url", "format", "observed_at", "private_ref", "sha256"}:
        raise ValueError("reviewed fact receipt evidence schema is invalid")
    if not isinstance(evidence.get("format"), str) or evidence["format"] not in SUPPORTED_FORMATS:
        raise ValueError("reviewed fact receipt evidence format is unsupported")
    if not valid_official_url(evidence.get("url"), INSTITUTION_SOURCE_HOSTS[institution_id]):
        raise ValueError("reviewed fact receipt evidence URL is not official for institution")
    if (evidence.get("url") != fact.get("evidence_url")
            or evidence.get("observed_at") != fact.get("observed_at")
            or evidence.get("format") != fact.get("format")):
        raise ValueError("reviewed fact receipt evidence does not bind to the fact")
    observed = _parse_aware_instant(evidence.get("observed_at"), "reviewed fact receipt evidence time")
    private_ref = evidence.get("private_ref")
    if not _is_private_ops_ref(private_ref):
        raise ValueError("reviewed fact receipt evidence must reference private/ops evidence")
    if not isinstance(evidence.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", evidence["sha256"]):
        raise ValueError("reviewed fact receipt evidence sha256 is invalid")
    reviewer = receipt.get("reviewer")
    if not isinstance(reviewer, dict) or set(reviewer) != {
        "reviewer_id", "reviewed_at", "decision", "notes", "verification_ref",
    }:
        raise ValueError("reviewed fact receipt reviewer schema is invalid")
    try:
        _required_identifier(reviewer.get("reviewer_id"),
                             "reviewed fact receipt reviewer_id")
    except ValueError:
        raise ValueError("reviewed fact receipt reviewer_id is required")
    reviewed_at = _parse_aware_instant(reviewer.get("reviewed_at"), "reviewed fact receipt reviewed_at")
    if reviewed_at < observed:
        raise ValueError("review decision predates observed evidence")
    if reviewer.get("decision") != "Reviewed" or not isinstance(reviewer.get("notes"), str) or not reviewer["notes"].strip():
        raise ValueError("reviewed fact receipt needs a Reviewed decision and notes")
    verification_ref = reviewer.get("verification_ref")
    if not _is_private_ops_ref(verification_ref):
        raise ValueError("reviewed fact receipt needs a private identity-verification reference")
    # The verifiers receive the binding context so a real adapter can prove
    # that the cited artifact supports this exact fact/receipt, not just that
    # some file or person exists.
    evidence_claim = {"receipt_id": receipt_id, "fact_sha256": digest, "evidence": evidence}
    reviewer_claim = {
        "receipt_id": receipt_id, "fact_sha256": digest,
        "reviewer": reviewer, "verification_ref": verification_ref,
    }
    if verify_evidence is None or verify_evidence(evidence_claim) is not True:
        raise ValueError("reviewed fact receipt evidence artifact is unverified")
    if verify_reviewer is None or verify_reviewer(reviewer_claim) is not True:
        raise ValueError("reviewed fact receipt reviewer identity is unverified")
    return {
        "status": "validated_local_only",
        "receipt_id": receipt_id,
        "fact_id": fact_id,
        "institution_id": institution_id,
        "OpportunityKey": opportunity_key,
        "fact_sha256": digest,
        "evidence_verifier_used": True,
        "identity_verifier_used": True,
        "imported": False,
    }


def _validate_lead_time(institution_id: str, lead_time: Any) -> None:
    """Validate source-backed per-rule lead times without flattening units."""
    if lead_time is None:
        return
    if not isinstance(lead_time, dict) or not lead_time:
        raise ValueError(f"institution {institution_id!r} has invalid internal lead-time structure")
    for rule_name, rule in lead_time.items():
        if not isinstance(rule_name, str) or not rule_name.strip() or not isinstance(rule, dict):
            raise ValueError(f"institution {institution_id!r} lead-time rules must be named objects")
        if set(rule) - {"value", "unit", "qualifier"}:
            raise ValueError(f"institution {institution_id!r} lead-time rule has unknown fields")
        if type(rule.get("value")) is not int or rule["value"] < 0:
            raise ValueError(f"institution {institution_id!r} lead-time values must be non-negative integers")
        if not isinstance(rule.get("unit"), str) or rule["unit"] not in SUPPORTED_LEAD_TIME_UNITS:
            raise ValueError(f"institution {institution_id!r} has unsupported lead-time unit")
        qualifier = rule.get("qualifier")
        if qualifier is not None and (not isinstance(qualifier, str) or not qualifier.strip()):
            raise ValueError(f"institution {institution_id!r} lead-time qualifier must be non-empty text")


def load_universities(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("university catalogue must be a list")
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"university catalogue row {index} must be an object")
        key = _required_identifier(row.get("institution_id"), f"university catalogue row {index} institution_id")
        if not key or key in seen:
            raise ValueError(f"duplicate or missing institution_id: {key!r}")
        if key not in INSTITUTION_SOURCE_HOSTS:
            raise ValueError(f"institution {key!r} is not an admitted catalogue identity")
        seen.add(key)
        for field in ("name", "authority_url", "access", "format", "intake", "eligibility_scope", "policy_note", "last_verified"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"institution {key!r} needs {field}")
        if row["intake"] != "manual_review":
            raise ValueError(f"institution {key!r} must remain manual_review until access is proven")
        try:
            if not valid_official_url(row["authority_url"], INSTITUTION_SOURCE_HOSTS[key]):
                raise ValueError
            last_verified = _full_iso_date(row["last_verified"])
        except ValueError as exc:
            raise ValueError(f"institution {key!r} needs an official authority URL and real YYYY-MM-DD verification date") from exc
        provenance = row.get("policy_provenance")
        if not isinstance(provenance, dict) or set(provenance) != {"status", "version", "effective_from", "timezone"}:
            raise ValueError(f"institution {key!r} needs explicit policy provenance and unknown fields")
        if (not isinstance(provenance["status"], str)
                or provenance["status"] not in {"public_summary_unversioned", "verified_versioned", "verified_current_unversioned", "unverified"}):
            raise ValueError(f"institution {key!r} has unsupported policy provenance status")
        if provenance["status"] in {"public_summary_unversioned", "unverified"} and any(provenance[field] is not None for field in ("version", "effective_from", "timezone")):
            raise ValueError(f"institution {key!r} must not invent policy version, effective date or timezone")
        if provenance["status"] == "verified_current_unversioned":
            if key != "griffith" or provenance["version"] is not None or provenance["timezone"] is not None:
                raise ValueError(f"institution {key!r} unversioned current policy must retain null version and timezone")
            try:
                effective = _full_iso_date(provenance["effective_from"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"institution {key!r} current policy needs a valid effective date") from exc
            if provenance["effective_from"] != CURRENT_POLICY_EFFECTIVE or effective > last_verified:
                raise ValueError(f"institution {key!r} current policy effective date differs from evidence")
        if provenance["status"] == "verified_versioned":
            if (not isinstance(provenance["version"], str)
                    or not provenance["version"].strip()
                    or provenance["version"] != provenance["version"].strip()
                    or not isinstance(provenance["effective_from"], str)
                    or not provenance["effective_from"].strip()):
                raise ValueError(f"institution {key!r} versioned policy needs version and effective date")
            if provenance["timezone"] is not None and (not isinstance(provenance["timezone"], str) or not provenance["timezone"].strip()):
                raise ValueError(f"institution {key!r} policy timezone must be null or non-empty text")
            try:
                _full_iso_date(provenance["effective_from"])
            except ValueError as exc:
                raise ValueError(f"institution {key!r} policy effective_from must be a real YYYY-MM-DD date") from exc
        evidence = row.get("source_evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"institution {key!r} needs source_evidence")
        claims = set()
        latest_evidence_date = None
        for item in evidence:
            if not isinstance(item, dict) or set(item) != {"claim", "url", "format", "observed_on", "version"}:
                raise ValueError(f"institution {key!r} has malformed source evidence")
            if not isinstance(item["claim"], str) or not item["claim"].strip():
                raise ValueError(f"institution {key!r} source evidence needs a claim")
            current_policy_evidence = (key == "griffith" and item["claim"] == "publisher_current_policy_search"
                                       and item["url"] == CURRENT_POLICY_SEARCH and item["version"] is None)
            if item["format"] != "html" or not (current_policy_evidence or valid_official_url(item["url"], INSTITUTION_SOURCE_HOSTS[key])):
                raise ValueError(f"institution {key!r} source evidence must use an official HTTPS HTML page")
            try:
                observed_on = _full_iso_date(item["observed_on"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"institution {key!r} source evidence needs a valid YYYY-MM-DD observed_on date") from exc
            latest_evidence_date = max(latest_evidence_date, observed_on) if latest_evidence_date else observed_on
            if item["version"] is not None and (
                    not isinstance(item["version"], str) or not item["version"].strip()
                    or item["version"] != item["version"].strip()):
                raise ValueError(f"institution {key!r} source evidence version must be null or unpadded text")
            claims.add(item["claim"])
        if latest_evidence_date and last_verified < latest_evidence_date:
            raise ValueError(f"institution {key!r} last_verified predates source evidence")
        if row.get("internal_lead_time") is not None and "lead_time_and_submission_route" not in claims and "lead_time_and_application_route" not in claims:
            raise ValueError(f"institution {key!r} lead times need matching source evidence")
        if provenance["status"] == "verified_versioned" and not any(item["version"] == provenance["version"] for item in evidence):
            raise ValueError(f"institution {key!r} versioned policy lacks matching source evidence")
        if provenance["status"] == "verified_current_unversioned" and not any(
            item["claim"] == "publisher_current_policy_search" and item["url"] == CURRENT_POLICY_SEARCH
            and item["version"] is None and item["observed_on"] == row["last_verified"] for item in evidence
        ):
            raise ValueError(f"institution {key!r} current policy needs exact publisher-search evidence")
        lead_time = row.get("internal_lead_time")
        _validate_lead_time(key, lead_time)
    missing = REQUIRED_INSTITUTIONS - seen
    if missing:
        raise ValueError(f"required universities missing: {sorted(missing)}")
    return rows


def reconcile_institution_facts(
    opportunities: Iterable[dict[str, Any]],
    facts: Iterable[dict[str, Any]],
    catalogue: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate institution-scoped facts against canonical opportunities.

    The output is a separate, deterministic fact list: multiple universities
    may refer to one canonical opportunity, and each may retain multiple
    distinct internal deadlines. It never projects those facts onto the
    funder's external deadline or upgrades eligibility to a global decision.
    """
    canonical: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(opportunities):
        if not isinstance(row, dict):
            raise ValueError(f"canonical opportunity row {index} must be an object")
        key = _required_identifier(row.get("OpportunityKey"), f"canonical opportunity row {index} OpportunityKey")
        if not OPPORTUNITY_KEY_RE.fullmatch(key):
            raise ValueError(f"canonical opportunity row {index} has invalid stable OpportunityKey")
        if key in canonical:
            raise ValueError(f"duplicate canonical OpportunityKey: {key}")
        canonical[key] = row
    institutions: dict[str, dict[str, Any]] = {}
    for row in catalogue:
        if not isinstance(row, dict):
            raise ValueError("institution catalogue entries must be objects")
        institution_id = _required_identifier(row.get("institution_id"), "institution catalogue institution_id")
        if not institution_id or institution_id in institutions:
            raise ValueError("institution catalogue contains duplicate or missing identity")
        institutions[institution_id] = row
    accepted: list[dict[str, Any]] = []
    seen_fact_ids: set[tuple[str, str, str]] = set()
    for index, fact in enumerate(facts):
        if not isinstance(fact, dict):
            raise ValueError(f"institution fact {index} must be an object")
        if set(fact) != INSTITUTION_FACT_FIELDS:
            raise ValueError(f"institution fact {index} has unknown or missing fields")
        institution_id = _required_identifier(fact.get("institution_id"), f"institution fact {index} institution_id")
        opportunity_key = _required_identifier(fact.get("OpportunityKey"), f"institution fact {index} OpportunityKey")
        institution = institutions.get(institution_id)
        if institution is None or opportunity_key not in canonical:
            raise ValueError(f"institution fact {index} has unknown institution or canonical opportunity")
        entitlement = fact.get("entitlement_status")
        if not isinstance(entitlement, str) or entitlement not in {"public", "verified_active", "revoked", "unknown"}:
            raise ValueError(f"institution fact {index} has invalid entitlement status")
        if entitlement in {"revoked", "unknown"}:
            raise ValueError(f"institution fact {index} cannot be admitted with {entitlement} entitlement")
        source_format = _required_text(fact.get("format"), f"institution fact {index} format").casefold()
        if source_format not in SUPPORTED_FORMATS:
            raise ValueError(f"institution fact {index} uses unsupported format")
        evidence_url = _required_text(fact.get("evidence_url"), f"institution fact {index} evidence_url")
        if not valid_official_url(evidence_url, INSTITUTION_SOURCE_HOSTS[institution_id]):
            raise ValueError(f"institution fact {index} needs official HTTPS evidence URL")
        retrieved = fact.get("observed_at")
        parsed = _parse_aware_instant(retrieved, f"institution fact {index} observed_at")
        if _required_text(fact.get("review_status"), f"institution fact {index} review_status").casefold() != "reviewed":
            raise ValueError(f"institution fact {index} requires human review")
        eligibility = fact.get("eligibility")
        if (not isinstance(eligibility, dict) or set(eligibility) != {"status", "restrictions"}
                or not isinstance(eligibility.get("status"), str)
                or eligibility["status"] not in {"supported", "restricted", "ambiguous", "unknown"}):
            raise ValueError(f"institution fact {index} needs exact eligibility fields and explicit status")
        if eligibility["status"] in {"ambiguous", "unknown"}:
            raise ValueError(f"institution fact {index} eligibility requires manual resolution")
        restrictions = eligibility.get("restrictions")
        if not isinstance(restrictions, list) or any(not isinstance(item, str) or not item.strip() for item in restrictions):
            raise ValueError(f"institution fact {index} must preserve eligibility restrictions as a list")
        if eligibility["status"] == "restricted" and not restrictions:
            raise ValueError(f"institution fact {index} restricted eligibility needs explicit restrictions")
        policy = fact.get("policy_provenance")
        if not isinstance(policy, dict) or set(policy) != {"status", "version", "effective_from", "timezone"}:
            raise ValueError(f"institution fact {index} needs explicit policy provenance")
        if (not isinstance(policy["status"], str)
                or policy["status"] not in {"public_summary_unversioned", "verified_versioned"}):
            raise ValueError(f"institution fact {index} policy provenance is not admissible")
        if policy["status"] == "public_summary_unversioned":
            if any(policy[key] is not None for key in ("version", "effective_from", "timezone")):
                raise ValueError(f"institution fact {index} cannot invent unversioned policy details")
        else:
            if (not isinstance(policy["version"], str)
                    or not policy["version"].strip()
                    or policy["version"] != policy["version"].strip()
                    or not isinstance(policy["effective_from"], str)
                    or not policy["effective_from"].strip()):
                raise ValueError(f"institution fact {index} versioned policy needs version and effective date")
            if policy["timezone"] is not None and (not isinstance(policy["timezone"], str) or not policy["timezone"].strip()):
                raise ValueError(f"institution fact {index} policy timezone must be null or non-empty text")
            try:
                _full_iso_date(policy["effective_from"])
            except ValueError as exc:
                raise ValueError(f"institution fact {index} policy effective_from must be a real YYYY-MM-DD date") from exc
        deadlines = fact.get("internal_deadlines")
        if not isinstance(deadlines, list):
            raise ValueError(f"institution fact {index} internal_deadlines must be a list")
        normalized_deadlines = []
        for deadline in deadlines:
            if (not isinstance(deadline, dict) or not deadline.get("deadline_id")
                    or set(deadline) - {"deadline_id", "kind", "date", "time", "timezone", "label"}):
                raise ValueError(f"institution fact {index} has an incomplete internal deadline")
            deadline_id = _required_identifier(deadline.get("deadline_id"), f"institution fact {index} deadline_id")
            deadline_kind = _required_text(deadline.get("kind"), f"institution fact {index} deadline kind")
            date_value = deadline.get("date")
            if not isinstance(date_value, str):
                raise ValueError(f"institution fact {index} internal deadline needs a full ISO date")
            try:
                _full_iso_date(date_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"institution fact {index} internal deadline needs a full ISO date") from exc
            if deadline_kind not in {"internal_close", "internal_submission", "internal_approval"}:
                raise ValueError(f"institution fact {index} has invalid internal deadline kind")
            time_value = deadline.get("time")
            if time_value is not None and (not isinstance(time_value, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?", time_value)):
                raise ValueError(f"institution fact {index} internal deadline time must be local HH:MM[:SS] or null")
            timezone_value = deadline.get("timezone")
            if timezone_value is not None and (not isinstance(timezone_value, str) or not timezone_value.strip()):
                raise ValueError(f"institution fact {index} internal deadline timezone must be null or text")
            label = deadline.get("label", "")
            if not isinstance(label, str):
                raise ValueError(f"institution fact {index} internal deadline label must be text")
            normalized_deadlines.append({
                "deadline_id": deadline_id,
                "kind": deadline_kind, "date": date_value,
                "time": time_value, "timezone": timezone_value,
                "label": label.strip(),
            })
        normalized_deadlines.sort(key=lambda item: (item["date"], item["time"] or "", item["kind"], item["deadline_id"]))
        ids = [item["deadline_id"] for item in normalized_deadlines]
        if len(ids) != len(set(ids)):
            raise ValueError(f"institution fact {index} repeats an internal deadline id")
        fact_id = _required_identifier(fact.get("fact_id"), f"institution fact {index} fact_id")
        dedupe_key = (institution_id, opportunity_key, fact_id)
        if dedupe_key in seen_fact_ids:
            raise ValueError(f"duplicate institution fact: {fact_id}")
        seen_fact_ids.add(dedupe_key)
        accepted.append({
            "InstitutionFactKey": f"{institution_id}:{opportunity_key}:{fact_id}",
            "institution_id": institution_id,
            "OpportunityKey": opportunity_key,
            "external_deadline": canonical[opportunity_key].get("Deadline"),
            "institutional_eligibility": {
                "status": eligibility["status"],
                "restrictions": sorted(set(item.strip() for item in restrictions)),
            },
            "policy_provenance": dict(policy),
            "internal_deadlines": normalized_deadlines,
            "entitlement_status": entitlement,
            "format": source_format,
            "evidence_url": evidence_url,
            "observed_at": parsed.isoformat(),
            "review_status": "Reviewed",
        })
    return sorted(accepted, key=lambda row: (row["institution_id"], row["OpportunityKey"], row["InstitutionFactKey"]))


def reconcile_receipted_institution_fact(
    receipt: Any,
    opportunities: Iterable[dict[str, Any]],
    catalogue: Iterable[dict[str, Any]],
    *,
    verify_evidence: Callable[[dict[str, Any]], bool] | None = None,
    verify_reviewer: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    """Run local G05 reconciliation only after both receipt verifiers pass.

    This returns a validation artifact. It deliberately has no importer or
    persistence side effect and remains blocked without real verifier adapters.
    """
    validated = validate_reviewed_fact_receipt(
        receipt, verify_evidence=verify_evidence, verify_reviewer=verify_reviewer,
    )
    records = reconcile_institution_facts(opportunities, [receipt["fact"]], catalogue)
    for row in records:
        row["ReviewReceiptID"] = validated["receipt_id"]
        row["ReviewReceiptFactSHA256"] = validated["fact_sha256"]
    return {"status": "validated_local_only", "imported": False,
            "receipt_id": validated["receipt_id"], "records": records}


def prepare_reviewed_institution_import(
    rows: Iterable[dict[str, Any]],
    receipts: Iterable[dict[str, Any]],
    catalogue: Iterable[dict[str, Any]],
    *,
    expected_source: str,
    official_hosts: Iterable[str],
    verify_evidence: Callable[[dict[str, Any]], bool] | None = None,
    verify_reviewer: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    """Prepare canonical funder rows and separate reviewed institutional facts.

    This manual, local boundary reuses G04 normalization; it cannot establish
    feed/export rights or persist records. Evidence adapters must verify the
    exact artifact and entitlement as well as its binding to the reviewed fact.
    Unknown eligibility remains unresolved and rejects the entire preparation.
    """
    try:
        from .grants_reviewed_import import import_reviewed_rows
    except ImportError:
        from grants_reviewed_import import import_reviewed_rows

    source = _required_identifier(expected_source, "expected_source")
    hosts = tuple(official_hosts)
    if not hosts or any(not isinstance(host, str) or not host.strip() for host in hosts):
        raise ValueError("reviewed institution import needs explicit official funder hosts")
    opportunities = import_reviewed_rows(rows, expected_source=source, official_hosts=hosts)
    materialized = list(receipts)
    institutions = list(catalogue)
    if not materialized:
        raise ValueError("reviewed institution import needs fact receipts")
    facts = []
    validated = []
    seen_receipts = set()
    for receipt in materialized:
        binding = validate_reviewed_fact_receipt(
            receipt, verify_evidence=verify_evidence, verify_reviewer=verify_reviewer,
        )
        if receipt["fact"]["format"] not in {"html", "csv", "xlsx"}:
            raise ValueError("manual reviewed import cannot establish machine feed rights")
        if binding["receipt_id"] in seen_receipts:
            raise ValueError("duplicate reviewed fact receipt identity")
        seen_receipts.add(binding["receipt_id"])
        facts.append(receipt["fact"])
        validated.append(binding)
    # Reconcile as one batch so duplicate institution/fact identities fail closed.
    records = reconcile_institution_facts(opportunities, facts, institutions)
    bindings = {":".join((item["institution_id"], item["OpportunityKey"], item["fact_id"])): item
                for item in validated}
    for row in records:
        binding = bindings[row["InstitutionFactKey"]]
        row["ReviewReceiptID"] = binding["receipt_id"]
        row["ReviewReceiptFactSHA256"] = binding["fact_sha256"]
    return {"status": "prepared_local_only", "imported": False,
            "intake": "manual_review", "feed_rights": "unverified",
            "opportunities": sorted(opportunities, key=lambda row: row["OpportunityKey"]),
            "institution_facts": records}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("catalogue", type=Path)
    args = parser.parse_args()
    print(f"validated {len(load_universities(args.catalogue))} university rows")
