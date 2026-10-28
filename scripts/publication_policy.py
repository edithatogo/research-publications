"""Generic permissive inclusion with evidence-preserving automatic attribution."""

import copy
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from scripts.organisation_enrichment import _norm, load_reference
from scripts.publication_notice_evidence import collect_notice_evidence

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/publication-policy.json"


ATTRIBUTION_FIELDS = (
    "OrganisationKeys",
    "OrganisationNames",
    "OrganisationMatchMethod",
    "OrganisationMatchConfidence",
    "OrganisationEvidence",
    "OrganisationReferenceVersion",
    "OrganisationEffectiveFrom",
    "OrganisationEffectiveTo",
)


def _publication_window(record: dict[str, Any]) -> tuple[date, date] | None:
    """Return the full interval represented by a source date, never a guessed day."""
    precision = record.get("PublicationDatePrecision")
    raw = record.get("PublicationDateRaw")
    if not isinstance(raw, str) or not isinstance(precision, str):
        return None
    try:
        if precision == "day" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            value = date.fromisoformat(raw)
            return value, value
        if precision == "month" and re.fullmatch(r"\d{4}-\d{2}", raw):
            start = date.fromisoformat(raw + "-01")
            next_month = (
                date(start.year + 1, 1, 1)
                if start.month == 12
                else date(start.year, start.month + 1, 1)
            )
            return start, date.fromordinal(next_month.toordinal() - 1)
        if precision == "year" and re.fullmatch(r"\d{4}", raw):
            year = int(raw)
            return date(year, 1, 1), date(year, 12, 31)
    except (ValueError, OverflowError):
        return None
    return None


def _inside_reference_window(record: dict[str, Any], unit: dict[str, Any]) -> bool:
    start, end = unit["_effective_from"], unit["_effective_to"]
    if not start and not end:
        return True
    publication = _publication_window(record)
    if publication is None:
        return False
    first, last = publication
    return (not start or first >= date.fromisoformat(start)) and (
        not end or last <= date.fromisoformat(end)
    )


def _enrich_policy_evidence(
    record: dict[str, Any], reference: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    # Existing attribution may have been corrected by a reviewer. This local
    # matcher has no provenance that would justify replacing any such value.
    if any(record.get(field) not in (None, "") for field in ATTRIBUTION_FIELDS):
        return record
    if reference is None:
        reference = load_reference()
    affiliation = ""
    for field in (
        "AffiliationsRaw",
        "Affiliations",
        "AuthorAffiliations",
        "AffiliationText",
    ):
        candidate = record.get(field)
        if candidate is None or candidate == "":
            continue
        if not isinstance(candidate, str):
            raise ValueError("affiliation evidence must be text")  # noqa: TRY004 - retained validator ValueError contract
        affiliation = candidate
        break
    text = _norm(affiliation)
    matches = []
    evidence = []
    temporal_review_required = False
    for key, unit in reference.items():
        aliases = sorted(
            (
                a
                for a in unit["_aliases"]
                if re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", text)
            ),
            key=len,
            reverse=True,
        )
        if aliases:
            if _inside_reference_window(record, unit):
                matches.append(key)
                evidence.append(f"{unit['OrganisationName']}: {aliases[0]}")
            else:
                temporal_review_required = True
    matches = sorted(set(matches))
    record["OrganisationKeys"] = ";".join(matches)
    record["OrganisationNames"] = ";".join(
        reference[k]["OrganisationName"] for k in matches
    )
    record["OrganisationMatchMethod"] = (
        "explicit-affiliation-alias"
        if matches
        else "review-required"
        if temporal_review_required
        else "unmatched"
    )
    record["OrganisationMatchConfidence"] = "high" if matches else "unknown"
    record["OrganisationEvidence"] = "; ".join(sorted(set(evidence)))
    record["OrganisationReferenceVersion"] = (
        next(iter(reference.values()), {}).get("_reference_version", "")
        if reference
        else ""
    )

    # A SharePoint date column is single-valued. Mixed or unknown validity
    # across matched units must stay unknown rather than becoming a joined date.
    def shared_date(field: str) -> str:
        values = {reference[k][field] for k in matches}
        return next(iter(values)) if len(values) == 1 and "" not in values else ""

    record["OrganisationEffectiveFrom"] = shared_date("_effective_from")
    record["OrganisationEffectiveTo"] = shared_date("_effective_to")
    return record


def load_policy(path=POLICY_PATH):
    policy = json.loads(Path(path).read_text())
    return validate_policy(policy)


def validate_policy(policy):
    expected = {
        "version",
        "inclusion",
        "retention",
        "default_projection",
        "uncertain_affiliation",
        "ambiguous_identity",
        "source_disappearance",
        "corrections_and_retractions",
        "fuzzy_names",
        "manual_record_approval",
    }
    if (
        not isinstance(policy, dict)
        or set(policy) != expected
        or not isinstance(policy["version"], str)
        or not policy["version"].strip()
    ):
        raise ValueError("Invalid publication policy schema")
    required = {
        "inclusion": "all-valid-configured-source-records",
        "retention": "every-observation-and-version",
        "default_projection": "latest-valid-version",
        "uncertain_affiliation": "include-with-label",
        "ambiguous_identity": "preserve-separate-source-records",
        "source_disappearance": "retain-last-good",
        "corrections_and_retractions": "retain-and-label",
        "fuzzy_names": "candidate-signal-only",
        "manual_record_approval": False,
    }
    if any(
        type(policy[k]) is not type(v) or policy[k] != v for k, v in required.items()
    ):
        raise ValueError(
            "Unsupported policy behaviour; implement changes before selecting them"
        )
    return policy


def notice_flags(record):
    """Compatibility labels from exact declared notice evidence, never prose."""
    evidence = collect_notice_evidence(record)
    return [
        flag
        for flag in ("retraction-notice", "correction-notice")
        if flag in evidence["flags"]
    ]


def evaluate(source, source_id, record, *, policy=None, reference=None):
    policy = load_policy() if policy is None else validate_policy(policy)
    if not isinstance(record, dict):
        raise ValueError("Source record must be an object")  # noqa: TRY004 - retained validator ValueError contract
    if (
        source not in ("PubMed", "DORA")
        or not isinstance(source_id, str)
        or source_id != source_id.strip()
        or not source_id
    ):
        raise ValueError("Valid configured source and source identity required")
    if source == "PubMed" and not re.fullmatch(r"[1-9][0-9]*", source_id):
        raise ValueError("Invalid PubMed identity")
    if source == "DORA" and (not source_id.startswith("DORA:") or not source_id[5:]):
        raise ValueError("DoRA identity must preserve its namespace")
    key = "pubmed:" + source_id if source == "PubMed" else "dora:" + source_id[5:]
    enriched = _enrich_policy_evidence(
        copy.deepcopy(record), reference if reference is not None else load_reference()
    )
    matched = enriched.get("OrganisationMatchMethod") == "explicit-affiliation-alias"
    flags = []
    if not matched:
        flags.append("affiliation-unconfirmed")
    if not record.get("PublicationDateRaw") or record.get(
        "PublicationDatePrecision"
    ) not in ("day", "month", "year"):
        flags.append("publication-date-uncertain")
    notice = collect_notice_evidence(
        record, source_key=key if source == "PubMed" else None
    )
    flags.extend(
        flag
        for flag in ("retraction-notice", "correction-notice")
        if flag in notice["flags"]
    )
    if notice["issues"]:
        flags.append("notice-evidence-unverified")
    # Preserve every original field; no employment inference or author-name merge.
    return {
        "SourceKey": key,
        "CanonicalSourceKey": key,
        "RegistryDisposition": "Included",
        "SourceEligibility": "eligible",
        "AffiliationAttribution": "attributed" if matched else "undetermined",
        "OrganisationKeys": enriched.get("OrganisationKeys", ""),
        "OrganisationEvidence": enriched.get("OrganisationEvidence", ""),
        "OrganisationReferenceVersion": enriched.get(
            "OrganisationReferenceVersion", ""
        ),
        "UncertaintyFlags": flags,
        "NoticeEvidence": notice,
        "PolicyVersion": policy["version"],
        "PolicySHA256": hashlib.sha256(
            json.dumps(policy, sort_keys=True).encode()
        ).hexdigest(),
        "IdentityMergeMethod": "source-identity-only",
        "Record": copy.deepcopy(record),
    }
