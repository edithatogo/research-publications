"""Optional presence diagnostics; no identity merge or routine human gate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

if __package__:
    from scripts.reconcile_publication_sources import (
        _direct_source_key,
        _member_identity,
    )
else:
    from reconcile_publication_sources import _direct_source_key, _member_identity


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_historical_review_snapshot(
    pubmed: dict, dora: dict, committed: dict, model: dict
) -> dict:
    pub_rows = pubmed["rows"]
    dora_rows = dora["rows"]
    members = committed["rows"]
    if (
        not committed.get("complete")
        or committed.get("next_links")
        or len(pub_rows) != 16
        or len(dora_rows) != 709
    ):
        raise ValueError("Expected complete 16 PubMed / 709 DoRA source inventory")
    member_set = {_member_identity(r) for r in members}
    if len(member_set) != len(members):
        raise ValueError("Duplicate retained source members")
    try:
        model_rows = model["results"][0]["tables"][0]["rows"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(
            "Model identity export requires one result table with rows"
        ) from exc
    if (
        not isinstance(model_rows, list)
        or not model_rows
        or not all(isinstance(r, dict) for r in model_rows)
    ):
        raise ValueError("Model identity export requires nonempty object rows")
    model_keys = [r.get("[CanonicalKey]") for r in model_rows]
    if any(
        not isinstance(key, str) or not key or key != key.strip() for key in model_keys
    ):
        raise ValueError(
            "Model identity export contains a blank or malformed CanonicalKey"
        )
    if len(set(model_keys)) != len(model_keys):
        raise ValueError("Model identity export contains duplicate CanonicalKey values")
    model_keys = set(model_keys)
    model_dora_urls = {r.get("[DORAURL]") for r in model_rows if r.get("[DORAURL]")}
    queue = []
    for r in pub_rows:
        key = r["source_key"]
        if (
            not key.startswith("pubmed:")
            or r.get("registry_review_status") != "Needs Review"
        ):
            raise ValueError("Unexpected PubMed review row")
        pmid = key.partition(":")[2]
        _member_identity({"Source": "PubMed", "SourceID": pmid})
        in_pubmed_archive = ("PubMed", pmid) in member_set
        if r.get("in_committed_pubmed_archive") is not in_pubmed_archive:
            raise ValueError(
                "PubMed diagnostic membership disagrees with retained export"
            )
        dora_id = r.get("dora_source_record_id")
        in_dora_archive = bool(dora_id and ("DORA", "DORA:" + dora_id) in member_set)
        if r.get("in_committed_dora_archive_by_pmid") is not in_dora_archive:
            raise ValueError(
                "PubMed DoRA cross-reference disagrees with retained export"
            )
        official = r.get("official_pubmed_record")
        if (
            not isinstance(official, dict)
            or not isinstance(official.get("title"), str)
            or not official["title"].strip()
            or official.get("pubmed_url")
            != "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/"
        ):
            raise ValueError(
                "PubMed diagnostic lacks an exact official EFetch record identity"
            )
        canonical = r.get("registry_canonical_key")
        queue.append(
            {
                "source": "PubMed",
                "source_id": pmid,
                "source_key": key,
                "source_membership": {
                    "official_efetch_record": True,
                    "retained_pubmed_archive": in_pubmed_archive,
                    "retained_dora_archive_by_pmid": in_dora_archive,
                },
                "model_presence": {
                    "pubmed_source_export_keyset": bool(r.get("in_model_pubmed_keyset"))
                },
                "canonical_presence": {
                    "registry_canonical_key": canonical,
                    "final_publication_row_with_registry_key": canonical in model_keys
                    if canonical
                    else False,
                    "final_publication_row_with_pmid_key": "PMID:" + pmid in model_keys,
                },
                "admission": {
                    "registry_review_status": r["registry_review_status"],
                    "disposition": None,
                    "reviewed_admission_proven": False,
                },
                "evidence": {
                    "registry_item_id": r.get("registry_item_id"),
                    "diagnostic_source_key": key,
                },
            }
        )
    for r in dora_rows:
        source_id = r["SourceID"]
        _member_identity({"Source": "DORA", "SourceID": source_id})
        if r.get("ReviewStatus") != "Pending" or r.get("Disposition") is not None:
            raise ValueError(
                "DoRA source has disposition; rebuild with reviewed evidence"
            )
        if ("DORA", source_id) not in member_set:
            raise ValueError("DoRA review source absent from retained export")
        refs = r.get("registry_refs") or {}
        if not isinstance(refs, dict) or any(
            not isinstance(refs.get(key, []), list)
            for key in ("direct", "stage_key", "pmid")
        ):
            raise ValueError("Registry reference evidence must use declared lists")
        reference_values = [
            value
            for key in ("direct", "stage_key", "pmid")
            for value in refs.get(key, [])
        ]
        queue.append(
            {
                "source": "DORA",
                "source_id": source_id,
                "source_key": _direct_source_key("DORA", source_id),
                "source_membership": {
                    "retained_dora_archive": True,
                    "historical_stage_evidence": bool(r.get("stage_indices")),
                    "direct_current_registry_evidence": bool(refs.get("direct")),
                },
                "canonical_presence": {
                    "dora_url_in_observed_model": source_id.removeprefix("DORA:")
                    in model_dora_urls,
                    "registry_reference_evidence": bool(reference_values),
                    "canonical_key_unresolved": True,
                },
                "admission": {
                    "review_status": "Pending",
                    "disposition": None,
                    "reviewed_admission_proven": False,
                },
                "evidence": {
                    "navigation_source_id": source_id,
                    "tier": r.get("tier"),
                    "archive_indices": r.get("archive_indices", []),
                    "evidence_gaps": r.get("evidence_gaps", []),
                },
            }
        )
    if len({(r["source"], r["source_id"]) for r in queue}) != 725:
        raise ValueError("Duplicate or missing review source")
    return copy.deepcopy(
        {
            "kind": "unified_publication_source_review_queue_v1",
            "candidate_only": True,
            "historical_snapshot_only": True,
            "routine_admission_prerequisite": False,
            "identity_merge_authorized": False,
            "review_authority": False,
            "registry_write_authorized": False,
            "consumer_accepted": False,
            "presence_scope": {
                "pubmed_source_export_keyset": "Prior PubMed source-key export diagnostic, not a final Publication row",
                "final_publication_row": f"Observed {len(model_rows)}-row DAX Publication identity export; canonical presence is not admission",
            },
            "counts": {
                "pubmed_needs_review": 16,
                "dora_pending": 709,
                "total_pending": 725,
                "reviewed_admitted": 0,
            },
            "rows": queue,
        }
    )


def build(pubmed, dora, committed, model):
    """Compatibility entry for the dated 16/709 snapshot; never a routine gate."""
    return build_historical_review_snapshot(pubmed, dora, committed, model)


def build_diagnostic(pubmed, dora, committed, model):
    """Optional complete-cohort presence diagnostic, independent of review status."""
    inputs = {"pubmed": pubmed, "dora": dora, "committed": committed}
    for name, document in inputs.items():
        if (
            not isinstance(document, dict)
            or document.get("complete") is not True
            or document.get("next_links")
            or not isinstance(document.get("rows"), list)
            or any(not isinstance(row, dict) for row in document["rows"])
        ):
            raise ValueError("Complete structured source snapshot required: " + name)
        if "row_count" in document and (
            type(document["row_count"]) is not int
            or document["row_count"] != len(document["rows"])
        ):
            raise ValueError("Source snapshot row count mismatch")
    if (
        not isinstance(model, dict)
        or model.get("complete") is not True
        or model.get("next_links")
    ):
        raise ValueError("Complete model snapshot required")
    results = model.get("results")
    result = results[0] if isinstance(results, list) and len(results) == 1 else None
    tables = result.get("tables") if isinstance(result, dict) else None
    table = tables[0] if isinstance(tables, list) and len(tables) == 1 else None
    if any(
        not isinstance(node, dict)
        or "error" in node
        or node.get("errors")
        or ("partial" in node and node["partial"] is not False)
        for node in (model, result, table)
    ):
        raise ValueError("Successful complete model query envelope required")
    model_rows = table.get("rows")
    if not isinstance(model_rows, list) or any(
        not isinstance(row, dict) for row in model_rows
    ):
        raise ValueError("Structured model rows required")
    keys = [row.get("[CanonicalKey]") for row in model_rows]
    if any(
        not isinstance(key, str) or not key.strip() or key != key.strip()
        for key in keys
    ) or len(set(keys)) != len(keys):
        raise ValueError("Unique exact model canonical keys required")
    members = [_member_identity(row) for row in committed["rows"]]
    if len(set(members)) != len(members):
        raise ValueError("Duplicate retained source member")
    member_set = set(members)
    rows, seen = [], set()
    for name, source in [("pubmed", "PubMed"), ("dora", "DORA")]:
        for original in inputs[name]["rows"]:
            if source == "PubMed":
                key = original.get("source_key")
                if not isinstance(key, str) or not key.startswith("pubmed:"):
                    raise ValueError("Exact PubMed source key required")
                source_id = key[7:]
            else:
                source_id = original.get("SourceID")
            identity = _member_identity({"Source": source, "SourceID": source_id})
            if identity in seen:
                raise ValueError("Duplicate source identity in diagnostic")
            seen.add(identity)
            matching = [
                row
                for row in model_rows
                if (
                    row["[CanonicalKey]"] == "PMID:" + source_id
                    if source == "PubMed"
                    else row.get("[DORAURL]") == source_id.removeprefix("DORA:")
                )
            ]
            rows.append(
                {
                    "source": source,
                    "source_id": source_id,
                    "source_key": _direct_source_key(source, source_id),
                    "original_record": copy.deepcopy(original),
                    "retained_source_membership": identity in member_set,
                    "model_exact_reference_rows": copy.deepcopy(matching),
                    "model_exact_reference_count": len(matching),
                    "model_presence_is_admission": False,
                    "candidate_only": True,
                }
            )
    return {
        "kind": "publication_source_presence_diagnostic_v1",
        "candidate_only": True,
        "historical_snapshot_only": False,
        "routine_admission_prerequisite": False,
        "registry_write_authorized": False,
        "consumer_accepted": False,
        "identity_merge_authorized": False,
        "review_authority": False,
        "counts": {
            "pubmed_sources": len(pubmed["rows"]),
            "dora_sources": len(dora["rows"]),
            "source_rows": len(rows),
            "model_rows": len(model_rows),
        },
        "rows": rows,
        "boundary": "Literal identity and presence evidence only. Original review states, dispositions and dates remain unchanged; no admission or identity resolution is decided.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ("pubmed", "dora", "committed", "model", "output"):
        ap.add_argument("--" + key, type=Path, required=True)
    ap.add_argument(
        "--historical-review-snapshot",
        action="store_true",
        help="Explicitly select the dated 16/709 evidence profile",
    )
    a = ap.parse_args()
    paths = {
        k: getattr(a, k).resolve() for k in ("pubmed", "dora", "committed", "model")
    }
    out = a.output.resolve()
    private = (Path(__file__).resolve().parents[1] / "private/ops").resolve()
    if (
        not all(p.is_relative_to(private) for p in [*paths.values(), out])
        or out in paths.values()
    ):
        ap.error("All inputs/output must be distinct files under private/ops")
    raw = {k: p.read_bytes() for k, p in paths.items()}
    data = {k: json.loads(value) for k, value in raw.items()}
    packet = (
        build_historical_review_snapshot
        if a.historical_review_snapshot
        else build_diagnostic
    )(**data)
    packet["input_sha256"] = {
        k: hashlib.sha256(value).hexdigest() for k, value in raw.items()
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(packet, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(out),
                "counts": packet["counts"],
                "input_sha256": packet["input_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
