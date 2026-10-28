"""Bind typed-identity anomalies to the pending source queue without admitting rows.

Exact source-key joins only. A generated PUB key is durable; PMID=0 is never
converted to a PubMed identity. This packet is evidence for manual review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def build(differences: dict, queue: dict) -> dict:
    if not isinstance(differences, dict) or not isinstance(queue, dict):
        raise ValueError("structured differences and queue required")  # noqa: TRY004 - retained validator ValueError contract
    if (
        queue.get("kind") != "unified_publication_source_review_queue_v1"
        or queue.get("candidate_only") is not True
    ):
        raise ValueError("candidate-only unified review queue required")
    rows = queue.get("rows")
    counts = queue.get("counts")
    total = counts.get("total_pending") if isinstance(counts, dict) else None
    if not isinstance(rows, list) or type(total) is not int or len(rows) != total:
        raise ValueError("review queue count mismatch")
    by_source = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("structured queue row required")  # noqa: TRY004 - retained validator ValueError contract
        source = row.get("source_key")
        if (
            not isinstance(source, str)
            or not source.strip()
            or source != source.strip()
            or source in by_source
        ):
            raise ValueError("missing or duplicate queue source key")
        if (
            not isinstance(row.get("admission"), dict)
            or row["admission"].get("reviewed_admission_proven") is not False
        ):
            raise ValueError("queue contains admitted candidate")
        by_source[source] = row
    invalid = differences.get("invalid")
    if not isinstance(invalid, list):
        raise ValueError("typed-identity differences required")  # noqa: TRY004 - retained validator ValueError contract
    packet_rows = []
    for item in invalid:
        if (
            not isinstance(item, dict)
            or item.get("side") != "registry"
            or not isinstance(item.get("row"), dict)
        ):
            raise ValueError("unexpected invalid identity; inspect typed comparison")
        row = item["row"]
        source, canonical, pmid = (
            row.get("SourceKey"),
            row.get("CanonicalKey"),
            row.get("PMID"),
        )
        if (
            not isinstance(source, str)
            or not source.startswith("dora:")
            or not source[5:].strip()
            or source != source.strip()
        ):
            raise ValueError("unexpected invalid source; inspect typed comparison")
        if (
            not isinstance(canonical, str)
            or not canonical.startswith("PUB:")
            or not canonical[4:].strip()
            or canonical != canonical.strip()
            or not (pmid == "0" or type(pmid) is int and pmid == 0)
        ):
            raise ValueError("unexpected invalid key; inspect typed comparison")
        match = by_source.get(source)
        packet_rows.append(
            {
                "registry_item_id": row.get("Id"),
                "source_key": source,
                "canonical_key": canonical,
                "pmid_raw": pmid,
                "registry_review_status": row.get("ReviewStatus"),
                "typed_identity_failure": item.get("reason"),
                "pending_queue_exact_source_match": match is not None,
                "pending_queue_source_id": match.get("source_id") if match else None,
                "review_required": "Verify the official source, durable key lineage and registry inclusion before any disposition",
                "disposition": None,
                "admission_proven": False,
            }
        )
    if len({r["source_key"] for r in packet_rows}) != len(packet_rows):
        raise ValueError("duplicate anomalous source key")
    return {
        "kind": "publication_identity_review_v1",
        "candidate_only": True,
        "counts": {
            "invalid_registry_identities": len(packet_rows),
            "exact_pending_queue_matches": sum(
                r["pending_queue_exact_source_match"] for r in packet_rows
            ),
            "unmatched_pending_queue_sources": sum(
                not r["pending_queue_exact_source_match"] for r in packet_rows
            ),
        },
        "identity_rule": "Exact SourceKey join only; preserve PUB keys and never infer PMID:0 or DoRA archive membership",
        "rows": packet_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("differences", "queue", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    paths = {
        name: getattr(args, name).resolve()
        for name in ("differences", "queue", "output")
    }
    private = (Path(__file__).resolve().parents[1] / "private/ops").resolve()
    if len(set(paths.values())) != len(paths) or not all(
        path.is_relative_to(private) for path in paths.values()
    ):
        parser.error("distinct inputs and output under ignored private/ops required")
    raw = {name: paths[name].read_bytes() for name in ("differences", "queue")}
    data = {name: json.loads(content) for name, content in raw.items()}
    packet = build(**data)
    packet["input_sha256"] = {
        name: hashlib.sha256(content).hexdigest() for name, content in raw.items()
    }
    with paths["output"].open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(packet, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"counts": packet["counts"], "output": str(paths["output"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
