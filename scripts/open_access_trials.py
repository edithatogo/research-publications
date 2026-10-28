"""Open Access category evidence and Clinical Trial Registry linkage.

Deterministic, keyless processing for:
1. Open Access category classification (Gold, Hybrid, Green, Bronze, Closed)
2. Unknown policy compliance when applicability/version/timing evidence is absent
3. ANZCTR (ACTRN...) and ClinicalTrials.gov (NCT...) identification and URL resolution
"""
from __future__ import annotations

import re
from typing import Any

ANZCTR_PATTERN = re.compile(r"\bACTRN\d{14}\b", re.IGNORECASE)
NCT_PATTERN = re.compile(r"\bNCT\d{8}\b", re.IGNORECASE)


def classify_open_access_status(
    oa_status: str | None,
    license_str: str | None = None,
    is_oa: bool | None = None,
) -> tuple[str, str]:
    """Return an explicit provider category and unknown policy compliance.

    The legacy tuple/field names remain compatible. Category, licence text and
    an access flag cannot establish grant/policy applicability, version, timing,
    embargo, rights or an evidence-backed compliance decision. Licence hints also
    cannot identify a journal/repository route. Contradictions remain unknown.
    """
    if oa_status is not None and not isinstance(oa_status, str):
        return ("Unknown", "Unknown")
    if is_oa is not None and type(is_oa) is not bool:
        return ("Unknown", "Unknown")
    status = (oa_status or "").strip().lower()
    categories = {name.lower(): name for name in ("Gold", "Hybrid", "Green", "Bronze", "Closed")}
    category = categories.get(status, "Unknown")
    if ((category == "Closed" and is_oa is True)
            or (category not in {"Closed", "Unknown"} and is_oa is False)):
        category = "Unknown"
    return (category, "Unknown")


def extract_trial_registrations(text: str | None) -> list[dict[str, str]]:
    """Extract ANZCTR and ClinicalTrials.gov registration IDs and generate verified URLs."""
    if not text:
        return []

    results: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for m in ANZCTR_PATTERN.finditer(str(text)):
        trial_id = m.group(0).upper()
        if trial_id not in seen_ids:
            seen_ids.add(trial_id)
            results.append({
                "registry": "ANZCTR",
                "trial_id": trial_id,
                "trial_url": f"https://www.anzctr.org.au/Trial/Registration/TrialReview.aspx?id={trial_id}",
            })

    for m in NCT_PATTERN.finditer(str(text)):
        trial_id = m.group(0).upper()
        if trial_id not in seen_ids:
            seen_ids.add(trial_id)
            results.append({
                "registry": "ClinicalTrials.gov",
                "trial_id": trial_id,
                "trial_url": f"https://clinicaltrials.gov/study/{trial_id}",
            })

    return results


def format_trial_registry_summary(trials: list[dict[str, str]]) -> tuple[str | None, str | None]:
    """Format trial registrations into semicolon-separated ID and URL strings."""
    if not trials:
        return (None, None)
    ids = "; ".join(t["trial_id"] for t in trials)
    urls = "; ".join(t["trial_url"] for t in trials)
    return (ids, urls)


def enrich_record_open_access_trials(record: dict[str, Any]) -> dict[str, Any]:
    """Fill absent OA fields conservatively, preserving recorded assessments."""
    oa_status = record.get("OpenAccessStatus") or record.get("EuropePMC_OpenAccess")
    lic = record.get("License") or record.get("OALicense")
    is_oa = record.get("IsOpenAccess")

    category, compliance = classify_open_access_status(oa_status, license_str=lic, is_oa=is_oa)
    if record.get("OACategory") in (None, ""):
        record["OACategory"] = category
    if record.get("OAComplianceNHMRC") in (None, ""):
        record["OAComplianceNHMRC"] = compliance

    corpus = f"{record.get('Title', '')} {record.get('AttributionEvidence', '')} {record.get('MeSHHeadings', '')} {record.get('ClinicalTrialID', '')}"
    trials = extract_trial_registrations(corpus)
    t_ids, t_urls = format_trial_registry_summary(trials)
    if t_ids:
        record["TrialRegistryID"] = t_ids
        record["TrialRegistryURL"] = t_urls
    else:
        record.setdefault("TrialRegistryID", None)
        record.setdefault("TrialRegistryURL", None)

    return record
