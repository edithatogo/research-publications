"""Join private blank-stub receipts without turning provenance into authority.

All inputs must describe the exact same candidate set. The output is a
read-only evidence matrix; it never proposes a SharePoint write.
"""

from __future__ import annotations

import argparse

if __package__:
    from scripts.plan_publication_stub_restore import strict_json_loads, same_target, target_qualification
else:
    from plan_publication_stub_restore import strict_json_loads, same_target, target_qualification
import hashlib
import json
from pathlib import Path
from typing import Any

# SPDX-License-Identifier: Apache-2.0
if __package__:
    from scripts.plan_publication_stub_restore import count, private_output
else:
    from plan_publication_stub_restore import count, private_output


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def _indexed(value: Any, field: str, label: str) -> dict[int, dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{label} items missing")
    result = {}
    for row in value:
        if not isinstance(row, dict):
            raise ValueError(f"{label} row invalid")
        ident = row.get(field)
        if isinstance(ident, bool) or not isinstance(ident, int) or ident < 1 or ident in result:
            raise ValueError(f"{label} ID invalid or duplicated")
        result[ident] = row
    return result


def reconcile(candidates: dict[str, Any], correlation: dict[str, Any],
              rehearsal: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    source = _indexed(candidates.get("items"), "id", "candidate")
    matched = _indexed(correlation.get("items"), "id", "correlation")
    history = _indexed(rehearsal.get("items"), "Id", "rehearsal")
    planned = _indexed(readiness.get("items"), "Id", "readiness")
    ids = set(source)
    if not ids or any(set(rows) != ids for rows in (matched, history, planned)):
        raise ValueError("candidate sets differ")
    if any(count(receipt.get("candidate_count")) != len(ids) for receipt in
           (candidates, correlation, rehearsal, readiness)):
        raise ValueError("candidate counts differ")
    if correlation.get("candidate_snapshot_sha256") != _digest(candidates):
        raise ValueError("correlation is not bound to candidate snapshot")
    if correlation.get("read_only") is not True or correlation.get("disposition_decided") is not False:
        raise ValueError("correlation must be read-only and undecided")
    if rehearsal.get("read_only") is not True or rehearsal.get("mutation_authorized") is not False:
        raise ValueError("rehearsal must be read-only and unauthorized")
    if readiness.get("read_only") is not True or readiness.get("mutation_authorized") is not False:
        raise ValueError("readiness must be read-only and unauthorized")
    evidence = readiness.get("input_evidence", {})
    if not isinstance(evidence, dict) or evidence.get("candidates", {}).get("sha256") != _digest(candidates):
        raise ValueError("readiness is not bound to candidate snapshot")
    rehearsal_inputs = rehearsal.get("input_sha256", {})
    if not isinstance(rehearsal_inputs, dict) or rehearsal_inputs.get("correlation") != _digest(correlation):
        raise ValueError("rehearsal is not bound to action correlation")
    cross_receipt_mismatches = [
        name for name in ("details", "versions", "schema")
        if rehearsal_inputs.get(name) != evidence.get(name, {}).get("sha256")
    ]
    counts = {"exact_create_match": 0, "unmatched_create": 0,
              "older_values_available": 0, "item_export_complete": 0,
              "restore_ready": 0}
    rows = []
    unmatched_ids = []
    for ident in sorted(ids):
        action = matched[ident]
        older = history[ident]
        plan = planned[ident]
        grade = action.get("grade")
        if grade not in {"direct_action_id_match", "unmatched"}:
            raise ValueError("unsupported action correlation grade")
        if grade == "direct_action_id_match" and not isinstance(action.get("action"), dict):
            raise ValueError("exact action evidence missing")
        if grade == "unmatched" and action.get("action") is not None:
            raise ValueError("unmatched action carries evidence")
        counts["exact_create_match" if grade == "direct_action_id_match" else "unmatched_create"] += 1
        if grade == "unmatched":
            unmatched_ids.append(ident)
        available = older.get("historical_value_field_names")
        if not isinstance(available, list):
            raise ValueError("historical field evidence missing")
        counts["older_values_available"] += bool(available)
        counts["item_export_complete"] += plan.get("item_export_complete") is True
        # A supplied legacy claim is diagnostic input, never restore authority.
        gaps = []
        if grade == "unmatched":
            gaps.append("item_specific_create_output_not_reconciled")
        if not available:
            gaps.append("older_field_values_not_recovered")
        if plan.get("provenance_status") != "reviewed" or plan.get("provenance_decision") != "remove_and_restore":
            gaps.append("reviewed_item_disposition_not_proven")
        rows.append({"Id": ident, "create_match": grade == "direct_action_id_match",
                     "older_value_field_count": len(available),
                     "item_export_complete": plan.get("item_export_complete") is True,
                     "restore_ready": False,
                     "legacy_restore_ready_claim": plan.get("restore_ready") is True,
                     "evidence_gaps": gaps})
    if counts["exact_create_match"] != count(correlation.get("exact_match_count")):
        raise ValueError("correlation aggregate disagrees with rows")
    if counts["unmatched_create"] != count(correlation.get("unmatched_candidate_count")):
        raise ValueError("unmatched correlation aggregate disagrees with rows")
    if counts["older_values_available"] != count(rehearsal.get("historical_value_item_count")):
        raise ValueError("rehearsal aggregate disagrees with rows")
    if not cross_receipt_mismatches and sum(p.get('restore_ready') is True for p in planned.values()) != count(readiness.get("restore_ready_count")):
        raise ValueError("readiness aggregate disagrees with rows")
    if counts["item_export_complete"] != count(readiness.get("item_export_complete_count")):
        raise ValueError("item export aggregate disagrees with rows")
    return {"receipt_schema_version": "publication-stub-disposition-evidence/v1",
            "read_only": True, "mutation_authorized": False,
            "target_binding": target_qualification(candidates, correlation, rehearsal, readiness),
            "disposition_decided": False, "candidate_count": len(ids),
            "cross_receipt_evidence_coherent": not cross_receipt_mismatches,
            "cross_receipt_mismatches": cross_receipt_mismatches,
            "counts": counts,
            "unmatched_action_item_ids": unmatched_ids,
            "unmatched_action_next_evidence": "Read back the exact Create action output for each unmatched item ID, or document an independent item-level provenance adjudication. An ID cohort or timestamp is not action evidence; no restoration follows from this receipt.",
            "input_sha256": {name: _digest(value) for name, value in
                             (("candidates", candidates), ("correlation", correlation),
                              ("rehearsal", rehearsal), ("readiness", readiness))},
            "items": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidates", "correlation", "rehearsal", "readiness", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    private_output(args.output, [getattr(args, n) for n in ('candidates','correlation','rehearsal','readiness')])
    private_ops = (Path(__file__).resolve().parent.parent / "private" / "ops").resolve()
    if not args.output.resolve().is_relative_to(private_ops):
        parser.error("output must be under ignored private/ops")
    inputs = [getattr(args, name) for name in ("candidates", "correlation", "rehearsal", "readiness")]
    if args.output.resolve() in {path.resolve() for path in inputs}:
        parser.error("output cannot overwrite an input")
    result = reconcile(*(strict_json_loads(path.read_text(encoding="utf-8")) for path in inputs))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(f"{result['candidate_count']} candidates; {result['counts']['exact_create_match']} exact Create matches; "
          f"{result['counts']['restore_ready']} restore-ready; no disposition or mutation")


if __name__ == "__main__":
    main()
