"""Prepare filterable report properties from accepted generation evidence only."""

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

FIELDS = {
    "RIMSPeriod": ("Reporting period", "Text"),
    "RIMSGeneration": ("Accepted generation", "Text"),
    "RIMSQueryVersion": ("Source query version", "Text"),
    "RIMSTemplateVersion": ("Template version SHA256", "Text"),
    "RIMSRecordCount": ("Included record count", "Number"),
    "RIMSOutputRevision": ("Output revision", "Text"),
    "RIMSReconciliation": ("Technical reconciliation", "Text"),
    "RIMSArtifactRole": ("Artifact role", "Text"),
    "RIMSGenerationManifest": ("Accepted generation manifest", "URL"),
    "RIMSArtifactManifest": ("Artifact manifest", "URL"),
}


def link(value):
    u = urlsplit(value)
    if (
        u.scheme != "https"
        or not u.hostname
        or u.username
        or u.password
        or u.query
        or u.fragment
    ):
        raise ValueError("Exact HTTPS manifest link required")
    return {"Url": value, "Description": "Authoritative manifest"}


def prepare(evidence):
    """The caller supplies native bytes/identity snapshots and accepted receipts."""
    evidence = copy.deepcopy(evidence)
    receipt, canonical, report = (
        evidence[k] for k in ("receipt", "canonical_manifest", "report_manifest")
    )
    if receipt.get("native_provenance_verified_by_this_script") is not True:
        raise ValueError("Accepted native generation receipt required")
    if (
        canonical["Status"] != "committed"
        or canonical.get("ReadbackVerified") is not True
        or report.get("complete") is not True
    ):
        raise ValueError("Complete accepted manifests required")
    context = report["source_context"]
    for key in (
        "generation_id",
        "source_snapshot_id",
        "query_version",
        "model_refresh_correlation",
    ):
        value = receipt[key]
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError("Known unpadded provenance required: " + key)
    for key in ("extraction_contract_sha256", "full_key_sha256", "monthly_key_sha256"):
        if not isinstance(receipt[key], str) or not re.fullmatch(
            "[a-f0-9]{64}", receipt[key]
        ):
            raise ValueError("Exact provenance SHA256 required: " + key)
    for key in ("full_count", "monthly_count"):
        if type(receipt[key]) is not int or receipt[key] < 0:
            raise ValueError("Nonnegative integer count required: " + key)
    if receipt["monthly_count"] > receipt["full_count"]:
        raise ValueError("Monthly count exceeds full count")
    bindings = evidence.get("field_bindings", {})
    if (
        not isinstance(bindings, dict)
        or set(bindings) - set(FIELDS)
        or any(
            not isinstance(v, str) or not v or v != v.strip() for v in bindings.values()
        )
    ):
        raise ValueError("Exact known field bindings required")
    resolved = [bindings.get(name, name) for name in FIELDS]
    if len(resolved) != len(set(resolved)):
        raise ValueError("Ambiguous native field bindings")
    for k in (
        "generation_id",
        "source_snapshot_id",
        "query_version",
        "model_refresh_correlation",
        "extraction_contract_sha256",
        "reporting_month",
        "full_count",
        "monthly_count",
        "full_key_sha256",
        "monthly_key_sha256",
    ):
        if receipt[k] != context[k]:
            raise ValueError("Report/generation mismatch: " + k)
    mapping = {
        "ReportingMonth": "reporting_month",
        "QueryVersion": "query_version",
        "AcceptedSourceBatchID": "source_snapshot_id",
        "ModelRefreshCorrelation": "model_refresh_correlation",
        "ExtractionContractSHA256": "extraction_contract_sha256",
        "PublicationCount": "monthly_count",
        "FullPublicationCount": "full_count",
        "CanonicalKeySetHash": "monthly_key_sha256",
        "FullCanonicalKeySetHash": "full_key_sha256",
    }
    for k, v in mapping.items():
        if canonical[k] != receipt[v]:
            raise ValueError("Companion/generation mismatch: " + k)
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", receipt["reporting_month"]):
        raise ValueError("Reporting month required")
    plans = []
    identities = set()
    item_ids = set()
    for artifact in evidence["artifacts"]:
        file, item = artifact["file"], artifact["item"]
        for value in (file["UniqueId"], artifact["role"]):
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError(
                    "Known stable file identity and artifact role required"
                )
        if (
            type(item["Id"]) is not int
            or item["Id"] < 1
            or item["Id"] in item_ids
            or type(artifact["file_item_id"]) is not int
            or type(artifact["bytes"]) is not int
            or artifact["bytes"] < 1
            or type(file["CheckOutType"]) is not int
        ):
            raise ValueError("Distinct exact item/byte/checkout evidence required")
        item_ids.add(item["Id"])
        if (
            file["UniqueId"] in identities
            or artifact["sha256"] != artifact["accepted_sha256"]
            or not re.fullmatch("[a-f0-9]{64}", artifact["sha256"])
            or int(file["Length"]) != artifact["bytes"]
            or file["CheckOutType"] != 2
            or artifact["file_item_id"] != item["Id"]
        ):
            raise ValueError("Exact file identity/content/checkout evidence required")
        identities.add(file["UniqueId"])
        if artifact["family"] not in {"report", "canonical"} or artifact[
            "count_scope"
        ] not in {"full", "monthly", "none"}:
            raise ValueError("Explicit accepted artifact family/count scope required")
        etag = item.get("odata.etag") or item.get("@odata.etag")
        if (
            not isinstance(etag, str)
            or not etag.strip()
            or etag != etag.strip()
            or etag == "*"
        ):
            raise ValueError("Exact native item ETag required")
        revision = (
            report["output_revision"]
            if artifact["family"] == "report"
            else canonical["RunID"]
        )
        if (
            not isinstance(revision, str)
            or not revision
            or revision != revision.strip()
        ):
            raise ValueError("Known artifact output revision required")
        props = {
            "RIMSPeriod": receipt["reporting_month"],
            "RIMSGeneration": receipt["generation_id"],
            "RIMSQueryVersion": receipt["query_version"],
            "RIMSOutputRevision": revision,
            "RIMSReconciliation": "Technical membership verified",
            "RIMSArtifactRole": artifact["role"],
            "RIMSGenerationManifest": link(evidence["generation_manifest_url"]),
            "RIMSArtifactManifest": link(
                evidence["report_manifest_url"]
                if artifact["family"] == "report"
                else evidence["generation_manifest_url"]
            ),
        }
        if artifact["count_scope"] != "none":
            props["RIMSRecordCount"] = receipt[artifact["count_scope"] + "_count"]
        if artifact["family"] == "report":
            version = report["html_template_sha256"]
            if not re.fullmatch("[a-f0-9]{64}", version):
                raise ValueError("Exact report template version required")
            props["RIMSTemplateVersion"] = version
        changes = {}
        for k, v in props.items():
            old = item.get(evidence.get("field_bindings", {}).get(k, k))
            if isinstance(v, dict) and isinstance(old, dict):
                old = {name: old.get(name) for name in ("Url", "Description")}
            if old == v:
                continue
            if old not in (None, ""):
                raise ValueError("Preserve conflicting existing metadata: " + k)
            if isinstance(v, str) and len(v.encode("utf-16-le")) > 510:
                raise ValueError("Text field exceeds native limit")
            changes[k] = v
        plans.append(
            {
                "file_id": file["UniqueId"],
                "item_id": item["Id"],
                "etag": etag,
                "file_preimage": file,
                "sha256": artifact["sha256"],
                "changes": changes,
                "before": {
                    k: item.get(evidence.get("field_bindings", {}).get(k, k))
                    for k in changes
                },
                "properties": props,
                "role": artifact["role"],
                "family": artifact["family"],
            }
        )
    if not plans:
        raise ValueError("Accepted artifacts required")
    return {
        "format": "rims-report-library-metadata-v1",
        "generation_id": receipt["generation_id"],
        "fields": copy.deepcopy(FIELDS),
        "items": plans,
        "content_writes": False,
        "manifest_writes": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("evidence", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    raw = a.evidence.read_bytes()
    plan = prepare(json.loads(raw))
    plan["evidence_path"] = str(a.evidence.resolve())
    plan["evidence_sha256"] = hashlib.sha256(raw).hexdigest()
    with a.output.open("x") as f:
        json.dump(plan, f, indent=2)
        f.write("\n")
    print("PREPARED_LOCAL_ONLY", len(plan["items"]))


if __name__ == "__main__":
    main()
