"""Offline field-evidence diff for blank publication stubs; never emits writes.

The rehearsal only considers older, explicitly non-current SharePoint versions.
Create-action correlation establishes origin, not the original field values.
All output is field names and counts; source values remain in private inputs.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

# SPDX-License-Identifier: Apache-2.0
if __package__:
    from scripts.plan_publication_stub_restore import count, schema_inventory, schema_field_inventory_sha256, version_entries, private_output
else:
    from plan_publication_stub_restore import count, schema_inventory, schema_field_inventory_sha256, version_entries, private_output


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("input must be an object")
    return value


def _rows(snapshot: dict[str, Any], label: str) -> dict[int, dict[str, Any]]:
    if snapshot.get("complete") is not True or snapshot.get("next_links") != []:
        raise ValueError(f"{label} export is not complete and unpaged")
    result = {}
    for row in snapshot.get("items", []):
        if not isinstance(row, dict):
            raise ValueError(f"{label} item invalid")
        ident = row.get("Id")
        if isinstance(ident, bool) or not isinstance(ident, int) or ident < 1 or ident in result:
            raise ValueError(f"{label} ID invalid or duplicated")
        result[ident] = row
    return result


def _filled(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _older_versions(entries: list[dict[str, Any]], item_id: int) -> list[dict[str, Any]]:
    """Distinguish a confirmed first version from ambiguous history."""
    if not entries or any(not isinstance(entry, dict) for entry in entries):
        raise ValueError(f"version history invalid for {item_id}")
    version_entries(entries)
    markers = [entry.get("IsCurrentVersion") for entry in entries]
    if any(type(marker) is not bool for marker in markers) or markers.count(True) != 1:
        raise ValueError(f"current and older version markers ambiguous for {item_id}")
    return [entry for entry in entries if entry["IsCurrentVersion"] is False]


def rehearse(details: dict[str, Any], versions: dict[str, Any],
             correlation: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    details, versions, correlation, schema = copy.deepcopy((details, versions, correlation, schema))
    current = _rows(details, "details")
    histories = _rows(versions, "versions")
    if not current or set(current) != set(histories):
        raise ValueError("detail and version candidate sets differ")
    schema_inventory(schema)
    if (schema.get("inventory_complete") is not True or
            schema.get('inventory_sha256') != schema_field_inventory_sha256(schema['fields']) or
            not isinstance(schema.get('source'), str) or not schema['source'].strip()):
        raise ValueError("complete schema inventory required")
    fields = {f["internal_name"] for f in schema["fields"]
              if f.get("type") not in {"Computed", "Attachments"}}
    if len(fields) == 0:
        raise ValueError("no scalar fields")
    if correlation.get("read_only") is not True or count(correlation.get("candidate_count")) != len(current):
        raise ValueError("correlation candidate set incomplete")
    actions = correlation.get("items")
    if not isinstance(actions, list) or len(actions) != len(current):
        raise ValueError("correlation rows incomplete")
    by_id = {}
    for action in actions:
        ident = action.get("id")
        if isinstance(ident, bool) or not isinstance(ident, int) or ident in by_id:
            raise ValueError("correlation ID invalid or duplicated")
        by_id[ident] = action
    if set(by_id) != set(current):
        raise ValueError("correlation candidate IDs differ")
    items = []
    for ident in sorted(current):
        detail = current[ident]
        history = histories[ident]
        if history.get("version_history_complete") is not True or history.get("version_next_links") != []:
            raise ValueError(f"version pagination incomplete for {ident}")
        if not isinstance(detail.get("fields"), dict) or not isinstance(history.get("versions"), list):
            raise ValueError(f"field or version data missing for {ident}")
        prior = _older_versions(history["versions"], ident)
        if not fields <= detail['fields'].keys():
            raise ValueError('Incomplete current scalar field coverage')
        current_version = next(v for v in history['versions'] if v['IsCurrentVersion'] is True)
        if any(field not in current_version or json.dumps(current_version[field],sort_keys=True,allow_nan=False) != json.dumps(detail['fields'][field],sort_keys=True,allow_nan=False) for field in fields):
            raise ValueError('Current version values do not match saved detail')
        # A historical field must be unambiguous across older versions. A
        # current-version value cannot serve as pre-incident evidence.
        recoverable = []
        conflicting = []
        incomplete = []
        for field in sorted(fields):
            if _filled(detail["fields"].get(field)):
                continue
            if any(field not in v for v in prior):
                incomplete.append(field); continue
            values = [v[field] for v in prior]
            unique = {json.dumps(value, sort_keys=True, ensure_ascii=False) for value in values}
            if len(unique) == 1 and _filled(values[0]):
                recoverable.append(field)
            elif len(unique) > 1 and any(_filled(value) for value in values):
                conflicting.append(field)
        missing = sorted(field for field in fields
                         if not _filled(detail["fields"].get(field))
                         and field not in recoverable and field not in conflicting)
        items.append({
            "Id": ident,
            "flow_correlation_grade": by_id[ident].get("grade", "unmatched"),
            "older_version_count": len(prior),
            "historical_value_field_names": recoverable,
            "conflicting_history_field_names": conflicting,
            "incomplete_history_field_names": incomplete,
            "fields_without_historical_value": missing,
            "restoration_authorized": False,
            "write_payload": None,
        })
    return {
        "receipt_schema_version": "publication-stub-offline-rehearsal/v1",
        "read_only": True,
        "mutation_authorized": False,
        "write_payload": None,
        "restore_ready_count": 0,
        "reason": "field evidence only; retention, item review, approval and fresh readback remain separate gates",
        "candidate_count": len(items),
        "historical_value_item_count": sum(bool(i["historical_value_field_names"]) for i in items),
        "input_sha256": {
            name: hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                           separators=(",", ":")).encode()).hexdigest()
            for name, value in (("details", details), ("versions", versions),
                                ("correlation", correlation), ("schema", schema))
        },
        "items": items,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("details", "versions", "correlation", "schema"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    private_output(args.output, [getattr(args, n) for n in ('details','versions','correlation','schema')])
    result = rehearse(*(_load(getattr(args, name)) for name in
                        ("details", "versions", "correlation", "schema")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(f"{result['candidate_count']} candidates; "
          f"{result['historical_value_item_count']} with historical values; "
          "0 restore-ready; no mutation")


if __name__ == "__main__":
    main()
