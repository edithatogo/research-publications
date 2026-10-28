"""Bind per-item live version pagination evidence to a saved stub version export.

The BrowserOS receipt is read-only metadata from each item's versions endpoint
with ``$top=1``. It can prove that the saved single version was the only visible
version at readback, but it does not refresh the saved version contents or
authorize mutation.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

# SPDX-License-Identifier: Apache-2.0
if __package__:
    from scripts.plan_publication_stub_restore import _by_id, _id, count, version_entries, private_output, utc
else:
    from plan_publication_stub_restore import _by_id, _id, count, version_entries, private_output, utc


ROOT = Path(__file__).resolve().parents[1]


def private_path(path: Path) -> Path:
    allowed = (ROOT / "private/ops").resolve()
    resolved = path.resolve()
    if resolved == allowed or allowed not in resolved.parents:
        raise ValueError("Version evidence paths must be under private/ops")
    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p.resolve().is_relative_to(allowed)):
        raise ValueError('Symlink version evidence refused')
    return resolved


def reconcile(export: dict[str, Any], readback: dict[str, Any]) -> dict[str, Any]:
    export, readback = copy.deepcopy((export, readback))
    old = export.get("items")
    live = readback.get("items")
    if (export.get("complete") is not True or export.get("next_links") != []
            or not isinstance(old, list) or not isinstance(live, list)):
        raise ValueError("outer exports are not complete item arrays")
    if readback.get("tenant_mutation_performed") is not False:
        raise ValueError("readback is not a read-only receipt")
    expected = readback.get("expected_item_ids")
    if not isinstance(expected, list) or not expected:
        raise ValueError('Exact nonempty item ID list required')
    for value in expected: _id(value)
    _by_id(export, 'saved versions')
    _by_id(readback, 'version readback')
    count(readback.get('requested_item_count'), len(expected), 'requested count')
    count(readback.get('returned_item_count'), len(expected), 'returned count')
    utc(readback.get('observed_at_utc'))
    if (not isinstance(expected, list) or len(expected) != len(set(expected))
            or set(expected) != {row.get("Id") for row in old}
            or set(expected) != {row.get("id") for row in live}):
        raise ValueError("exact item ID sets do not match")
    if (readback.get("requested_item_count") != len(expected)
            or readback.get("returned_item_count") != len(live)):
        raise ValueError("readback counts disagree")
    by_id = {row["id"]: row for row in live}
    out = []
    for index, row in enumerate(old):
        versions = row.get("versions")
        version_entries(versions)
        observed = by_id[row["Id"]]
        count(observed.get('count'), len(versions), 'version count')
        if (not isinstance(versions, list) or observed.get("status") != 200
                or observed.get("count") != len(versions)
                or observed.get("next") is not None
                or observed.get("labels") != [v.get("VersionLabel") for v in versions]):
            raise ValueError(f"version count, labels or pagination differ for item index {index}")
        out.append({**row, "version_history_complete": True,
                    "version_next_links": []})
    return {**export, "items": out,
            "pagination_evidence_observed_at_utc": readback.get("observed_at_utc"),
            "pagination_evidence_route": readback.get("route")}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--versions", required=True, type=Path)
    p.add_argument("--readback", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    versions_path, readback_path, output_path = map(private_path, (a.versions, a.readback, a.output))
    private_output(a.output, [a.versions, a.readback], root=ROOT)
    if len({versions_path, readback_path, output_path}) != 3 or output_path.exists():
        p.error("Private evidence inputs/output must be distinct and output new")
    result = reconcile(json.loads(versions_path.read_text()), json.loads(readback_path.read_text()))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(f"reconciled {len(result['items'])} item version histories; read-only")


if __name__ == "__main__":
    main()
