"""Join saved registry/model discrepancies to retained DoRA review evidence.

This optional diagnostic preserves evidence without a routine human gate. It never changes keys,
promotes source membership, or treats model-derived membership as admission.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def build(registry: dict, differences: dict, tiered: dict) -> dict:
    if not all(isinstance(value, dict) for value in (registry, differences, tiered)):
        raise ValueError("Structured diagnostic inputs required")
    if (
        registry.get("complete") is not True
        or registry.get("next_links")
        or not isinstance(registry.get("keyed_rows"), list)
        or type(registry.get("keyed_total")) is not int
        or len(registry["keyed_rows"]) != registry["keyed_total"]
    ):
        raise ValueError("complete registry keyed readback required")
    if (
        tiered.get("candidate_only") is not True
        or tiered.get("reviewed_membership") is not False
    ):
        raise ValueError("unpromoted tiered DoRA evidence required")
    rows = registry["keyed_rows"]
    if any(
        not isinstance(row, dict)
        or type(row.get("Id")) is not int
        or row["Id"] <= 0
        or any(
            not isinstance(row.get(field), str)
            or not row[field].strip()
            or row[field] != row[field].strip()
            for field in ("SourceKey", "CanonicalKey")
        )
        for row in rows
    ):
        raise ValueError("Exact registry identities and original DoRA URL required")
    if len({row["Id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate registry item identity")
    by_source = {r["SourceKey"]: r for r in rows}
    if len(by_source) != len(rows):
        raise ValueError("duplicate registry source key")
    by_pmid = defaultdict(list)
    by_dora_source = defaultdict(list)
    if not isinstance(tiered.get("rows"), list):
        raise ValueError("Tiered evidence rows required")  # noqa: TRY004 - retained validator contract
    for r in tiered["rows"]:
        if (
            not isinstance(r, dict)
            or not isinstance(r.get("SourceID"), str)
            or not r["SourceID"].startswith("DORA:")
            or not r["SourceID"][5:].strip()
            or r["SourceID"] != r["SourceID"].strip()
            or not isinstance(r.get("tier"), str)
            or not r["tier"].strip()
        ):
            raise ValueError(
                "Exact tiered DoRA source identity and evidence tier required"
            )
        if r.get("stage_pmid") not in (None, "") and (
            not isinstance(r["stage_pmid"], str)
            or re.fullmatch(r"[1-9][0-9]*", r["stage_pmid"]) is None
        ):
            raise ValueError("Stage PMID must be positive canonical text or absent")
        if r.get("stage_pmid"):
            by_pmid[r["stage_pmid"]].append(r)
        by_dora_source[r["SourceID"]].append(r)
    extra = differences.get("model_additional_membership")
    invalid = differences.get("invalid")
    if not isinstance(extra, list) or not isinstance(invalid, list):
        raise ValueError("provenance difference arrays required")  # noqa: TRY004 - retained validator contract
    legacy = []
    legacy_by_dora_source = defaultdict(list)
    invalid_seen = set()
    for item in invalid:
        if not isinstance(item, dict) or item.get("side") != "registry":
            raise ValueError("unexpected invalid model identity")
        raw_key = item.get("raw_key")
        if not isinstance(raw_key, str) or raw_key in invalid_seen:
            raise ValueError("Unique exact invalid source key required")
        invalid_seen.add(raw_key)
        row = by_source.get(raw_key)
        if row is None:
            raise ValueError(
                "invalid registry source key absent from complete readback"
            )
        if (
            not isinstance(row.get("DORAURL"), str)
            or not row["DORAURL"].strip()
            or row["DORAURL"] != row["DORAURL"].strip()
        ):
            raise ValueError("Legacy invalid registry row needs an exact DoRA URL")
        source_id = "DORA:" + row["DORAURL"]
        candidates = by_dora_source[source_id]
        legacy_by_dora_source[source_id].append(row["Id"])
        legacy.append(
            {
                "registry_id": row["Id"],
                "source_key": row["SourceKey"],
                "canonical_key": row["CanonicalKey"],
                "pmid": row["PMID"],
                "dora_url": row["DORAURL"],
                "review_status": row["ReviewStatus"],
                "candidate_count": len(candidates),
                "candidate_stage_pmids": [r.get("stage_pmid") for r in candidates],
                "candidate_current_pmid_registry_ids": [
                    r.get("registry_pmid_ids") for r in candidates
                ],
                "candidate_tiers": [r["tier"] for r in candidates],
                "disposition": "legacy_identity_conflict_review",
            }
        )
    membership = []
    extra_seen = set()
    for item in extra:
        key = item.get("typed_identity") if isinstance(item, dict) else None
        if (
            not isinstance(key, str)
            or not key.startswith("PMID:")
            or re.fullmatch(r"[1-9][0-9]*", key[5:]) is None
            or key in extra_seen
        ):
            raise ValueError("unexpected model additional identity")
        extra_seen.add(key)
        matches = by_pmid[key[5:]]
        conflict_ids = sorted(
            {
                ident
                for r in matches
                for ident in legacy_by_dora_source.get(r["SourceID"], [])
            }
        )
        membership.append(
            {
                "typed_identity": key,
                "model_membership": item["model_membership"],
                "registry_primary": item["registry_primary"],
                "candidate_count": len(matches),
                "candidate_dora_source_ids": [r["SourceID"] for r in matches],
                "candidate_tiers": [r["tier"] for r in matches],
                "linked_legacy_conflict_registry_ids": conflict_ids,
                "disposition": (
                    "ambiguous_or_missing_evidence"
                    if len(matches) != 1
                    else "legacy_registry_identity_conflict_review"
                    if conflict_ids
                    else "review_candidate_only"
                ),
            }
        )
    counts = Counter(
        r["candidate_tiers"][0] if r["candidate_count"] == 1 else r["disposition"]
        for r in membership
    )
    return copy.deepcopy(
        {
            "kind": "publication_identity_resolution_review_packet_v1",
            "candidate_only": True,
            "registry_write_authorized": False,
            "consumer_accepted": False,
            "identity_merge_authorized": False,
            "review_authority": False,
            "routine_admission_prerequisite": False,
            "original_registry_rows": copy.deepcopy(rows),
            "original_tiered_rows": copy.deepcopy(tiered["rows"]),
            "counts": {
                "model_additional_membership": len(membership),
                "membership_evidence_tiers": dict(sorted(counts.items())),
                "legacy_invalid_registry_identities": len(legacy),
                "membership_candidates_with_legacy_conflicts": sum(
                    bool(r["linked_legacy_conflict_registry_ids"]) for r in membership
                ),
            },
            "rule": "Exact saved PMID and DoRA SourceID joins only. Model co-membership and historical citation evidence are candidates; linked legacy conflicts and PUB keys remain unresolved evidence; no registry admission or routine review requirement follows.",
            "model_additional_membership": membership,
            "legacy_invalid_registry_identities": legacy,
        }
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", required=True, type=Path)
    ap.add_argument("--differences", required=True, type=Path)
    ap.add_argument("--tiered", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    private = (Path(__file__).resolve().parent.parent / "private").resolve()
    if not all(
        path.resolve().is_relative_to(private)
        for path in (args.registry, args.differences, args.tiered, args.output)
    ):
        ap.error("identity details must remain under ignored private/")
    if args.output.resolve() in {
        args.registry.resolve(),
        args.differences.resolve(),
        args.tiered.resolve(),
    }:
        ap.error("output must not replace source evidence")
    raw = {
        key: path.read_bytes()
        for key, path in [
            ("registry", args.registry),
            ("differences", args.differences),
            ("tiered", args.tiered),
        ]
    }
    packet = build(*(json.loads(raw[k]) for k in ("registry", "differences", "tiered")))
    packet["input_sha256"] = {
        key: hashlib.sha256(value).hexdigest() for key, value in raw.items()
    }
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(packet, indent=2) + "\n")
    print(
        json.dumps(
            {
                "kind": packet["kind"],
                "counts": packet["counts"],
                "output": str(args.output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
