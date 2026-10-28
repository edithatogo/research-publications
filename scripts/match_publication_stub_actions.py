"""Read-only item-ID correlation for exported Power Automate Create actions.

The input is a private, normalized action-output export. Each action must
carry its run ID, action/repetition ID, terminal status, and the SharePoint
item ID returned by that action. A timestamp or contiguous ID cohort is not
an accepted substitute for the returned ID. This script never decides whether
an item may be removed or restored.
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
    from scripts.plan_publication_stub_restore import _id, _by_id, count, private_output
else:
    from plan_publication_stub_restore import _id, _by_id, count, private_output


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _item_id(value: Any) -> int:
    return _id(value)


def correlate(candidates: dict[str, Any], actions: dict[str, Any]) -> dict[str, Any]:
    """Correlate only exact returned IDs; reject ambiguous action evidence."""
    rows = candidates.get("items")
    if not isinstance(rows, list) or count(candidates.get("candidate_count")) != len(rows):
        raise ValueError("candidate snapshot count or items missing")
    _by_id(candidates,'action candidates')
    candidate_ids = [_item_id(row.get("Id", row.get("id"))) for row in rows
                     if isinstance(row, dict)]
    if len(candidate_ids) != len(rows) or len(set(candidate_ids)) != len(rows):
        raise ValueError("candidate IDs missing or duplicated")
    if actions.get("schema_version") != "publication-create-action-outputs/v1":
        raise ValueError("unsupported action-output schema")
    outputs = actions.get("actions")
    if not isinstance(outputs, list):
        raise ValueError("actions array missing")
    matches: dict[int, dict[str, str]] = {}
    seen_actions: set[tuple[str, str]] = set()
    seen_created_items: set[int] = set()
    candidate_id_set = set(candidate_ids)
    outside = 0
    for action in outputs:
        if not isinstance(action, dict):
            raise ValueError("action output must be an object")
        run_id = action.get("run_id")
        action_id = action.get("action_id")
        if not all(isinstance(value, str) and value.strip()
                   and value == value.strip()
                   for value in (run_id, action_id)):
            raise ValueError("run and action IDs are required")
        key = (run_id, action_id)
        if key in seen_actions:
            raise ValueError("duplicate run/action output")
        seen_actions.add(key)
        if action.get("status") != "Succeeded":
            raise ValueError("only succeeded Create outputs establish an item match")
        item_id = _item_id(action.get("created_item_id"))
        if item_id in seen_created_items:
            raise ValueError("multiple Create outputs claim one item")
        seen_created_items.add(item_id)
        evidence_ref = action.get("evidence_ref")
        if not isinstance(evidence_ref, str) or not evidence_ref.strip() or evidence_ref != evidence_ref.strip():
            raise ValueError("action requires an item-specific evidence reference")
        if item_id not in candidate_id_set:
            outside += 1
            continue
        matches[item_id] = {"run_id": run_id, "action_id": action_id,
                            "evidence_ref": evidence_ref}
    return {
        "schema_version": "publication-stub-action-correlation/v1",
        "target_binding": target_qualification(candidates, actions),
        "read_only": True,
        "disposition_decided": False,
        "restore_ready": False,
        "candidate_count": len(candidate_ids),
        "action_output_count": len(outputs),
        "exact_match_count": len(matches),
        "unmatched_candidate_count": len(candidate_ids) - len(matches),
        "noncandidate_action_output_count": outside,
        "candidate_snapshot_sha256": _fingerprint(candidates),
        "action_export_sha256": _fingerprint(actions),
        "items": [{"id": item_id, "grade": "direct_action_id_match" if item_id in matches else "unmatched",
                   "action": matches.get(item_id)} for item_id in sorted(candidate_ids)],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--actions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        private_output(args.output, [args.candidates, args.actions])
    except ValueError as error:
        parser.error(str(error))
    private_ops = (Path(__file__).resolve().parent.parent / "private" / "ops").resolve()
    output_path = args.output.resolve()
    if not output_path.is_relative_to(private_ops):
        parser.error("correlation output must be under ignored private/ops")
    if output_path in {args.candidates.resolve(), args.actions.resolve()}:
        parser.error("correlation output cannot overwrite an input")
    result = correlate(strict_json_loads(args.candidates.read_text(encoding="utf-8")),
                       strict_json_loads(args.actions.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(f"{result['exact_match_count']}/{result['candidate_count']} exact item matches; no disposition or mutation")


if __name__ == "__main__":
    main()
