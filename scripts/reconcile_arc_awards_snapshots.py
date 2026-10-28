"""Compare two complete, locally saved ARC award snapshots by source ID.

The comparison is descriptive only. ARC records are award context and this
tool does not infer open-opportunity lifecycle or admission decisions.
"""
from __future__ import annotations

import argparse
import base64
import os
import re
import tempfile
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


# SPDX-License-Identifier: Apache-2.0
if __package__:
    from scripts.plan_publication_stub_restore import strict_json_loads, private_output
else:
    from plan_publication_stub_restore import strict_json_loads, private_output


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def digest(raw, expected):
    if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('Caller-pinned SHA256 required')
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Captured bytes differ from caller-pinned SHA256')


def preimage(document, expected_sha256, expected_parts):
    if fingerprint(document) != expected_sha256:
        raise ValueError('Complete preimage digest mismatch')
    parts = document.get('parts')
    if not isinstance(parts, list) or not parts:
        raise ValueError('Complete inline preimage required')
    if (not isinstance(expected_parts, list) or not expected_parts
            or len(expected_parts) != len(set(expected_parts))):
        raise ValueError('Explicit complete part inventory required')
    paths = []
    for part in parts:
        if not isinstance(part, dict): raise ValueError('Invalid preimage part')
        path = part.get('path')
        if (not isinstance(path, str) or not path or path != path.strip()
                or path.startswith('/') or '\\' in path or any(x in ('','.','..') for x in path.split('/'))):
            raise ValueError('Invalid preimage path')
        if part.get('payloadType') != 'InlineBase64': raise ValueError('Inline preimage required')
        base64.b64decode(part.get('payload',''), validate=True)
        paths.append(path)
    if len(paths) != len(set(paths)) or set(paths) != set(expected_parts):
        raise ValueError('Complete preimage part inventory mismatch')


def write_new(path, value, inputs):
    """Validate/serialize first, then install exclusively without partial outputs."""
    private_output(path, inputs)
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.arc-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, path)
    finally:
        os.unlink(temp)


IGNORED_FIELDS = {"RetrievedUTC", "EvidenceHash"}


def private_output_path(path: Path) -> Path:
    private_root = (Path(__file__).resolve().parent.parent / "private/ops").resolve()
    resolved = path.resolve()
    if resolved == private_root or private_root not in resolved.parents:
        raise ValueError("Detailed reconciliation output must be under private/ops")
    if resolved.exists():
        raise ValueError("Refusing to overwrite an existing private reconciliation")
    return resolved


def _load_snapshot(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str, dict[str, str]]:
    raw = path.read_bytes()
    digest(raw, expected_sha256)
    snapshot = strict_json_loads(raw)
    if not isinstance(snapshot, dict):
        raise ValueError(f"{path}: snapshot must be an object")
    if 'error' in snapshot or 'errors' in snapshot:
        raise ValueError('Failure envelope is not a complete snapshot')
    if snapshot.get("source") != "arc" or snapshot.get("record_kind") != "awards_only":
        raise ValueError(f"{path}: expected an ARC awards-only snapshot")
    records = snapshot.get("records")
    if snapshot.get("snapshot_complete") is not True or not isinstance(records, list):
        raise ValueError(f"{path}: snapshot must be complete and contain records")
    if snapshot.get('next_links') != []:
        raise ValueError('Complete unpaged snapshot required')
    if snapshot.get('snapshot_hash') != fingerprint(records):
        raise ValueError('Snapshot record digest mismatch')
    expected_total = snapshot.get("source_total")
    if type(expected_total) is not int or expected_total != len(records):
        raise ValueError(f"{path}: source_total must equal record count")
    keyed: dict[str, dict[str, Any]] = {}
    source_to_code: dict[str, str] = {}
    codes: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"{path}: each record must be an object")
        if record.get('Amount') is not None and not isinstance(record.get('Amount'), str):
            raise ValueError('Amount must remain raw source text or unknown')
        if ('Source' in record and record['Source'] != 'arc') or ('RecordKind' in record and record['RecordKind'] != 'Award'):
            raise ValueError('Conflicting award source identity')
        if 'error' in record or 'errors' in record:
            raise ValueError('Failure envelope is not an award record')
        source_id = record.get("SourceID")
        if not isinstance(source_id, str) or not source_id or source_id != source_id.strip():
            raise ValueError(f"{path}: record SourceID must be nonblank and unpadded")
        if source_id in keyed:
            raise ValueError(f"{path}: duplicate SourceID")
        award_code = record.get("AwardCode")
        if not isinstance(award_code, str) or not award_code or award_code != award_code.strip():
            raise ValueError(f"{path}: record AwardCode must be nonblank and unpadded")
        if award_code in codes:
            raise ValueError(f"{path}: duplicate AwardCode")
        keyed[source_id] = record
        source_to_code[source_id] = award_code
        codes.add(award_code)
    snapshot["_records_by_id"] = keyed
    return snapshot, hashlib.sha256(raw).hexdigest(), source_to_code


def reconcile(baseline_path: Path, current_path: Path, *, baseline_sha256: str, current_sha256: str) -> dict[str, Any]:
    baseline, baseline_file_hash, old_mapping = _load_snapshot(baseline_path, baseline_sha256)
    current, current_file_hash, new_mapping = _load_snapshot(current_path, current_sha256)
    old = baseline.pop("_records_by_id")
    new = current.pop("_records_by_id")
    old_ids, new_ids = set(old), set(new)
    old_codes, new_codes = set(old_mapping.values()), set(new_mapping.values())
    def mapping_fingerprint(mapping: dict[str, str]) -> str:
        encoded = json.dumps(sorted(mapping.items()), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
    added, removed = sorted(new_ids - old_ids), sorted(old_ids - new_ids)
    changed: list[dict[str, Any]] = []
    field_counts: Counter[str] = Counter()
    amount_transitions: Counter[str] = Counter()
    for source_id in sorted(old_ids & new_ids):
        before, after = old[source_id], new[source_id]
        fields = sorted(
            field for field in (set(before) | set(after)) - IGNORED_FIELDS
            if fingerprint([field in before, before.get(field)]) != fingerprint([field in after, after.get(field)])
        )
        if not fields:
            continue
        field_counts.update(fields)
        entry: dict[str, Any] = {"source_id": source_id, "changed_fields": fields}
        if "Amount" in fields:
            old_amount, new_amount = before.get("Amount"), after.get("Amount")
            transition = ("blank_to_zero" if old_amount in (None, "") and new_amount in (0, 0.0, "0", "0.0")
                          else "zero_to_blank" if old_amount in (0, 0.0, "0", "0.0") and new_amount in (None, "")
                          else "other")
            amount_transitions[transition] += 1
            entry["amount_before"] = old_amount
            entry["amount_after"] = new_amount
        changed.append(entry)
    return {
        "schema": "arc-awards-row-reconciliation/v1",
        "mutation_authorized": False,
        "native_acceptance": False,
        "baseline": {
            "snapshot_file": str(baseline_path),
            "file_sha256": baseline_file_hash,
            "retrieved_utc": baseline.get("retrieved_utc"),
            "snapshot_hash": baseline.get("snapshot_hash"),
            "record_count": len(old),
        },
        "current": {
            "snapshot_file": str(current_path),
            "file_sha256": current_file_hash,
            "retrieved_utc": current.get("retrieved_utc"),
            "snapshot_hash": current.get("snapshot_hash"),
            "record_count": len(new),
        },
        "award_code_mapping": {
            "baseline_source_id_count": len(old_mapping),
            "baseline_unique_award_code_count": len(old_codes),
            "baseline_pairing_sha256": mapping_fingerprint(old_mapping),
            "current_source_id_count": len(new_mapping),
            "current_unique_award_code_count": len(new_codes),
            "current_pairing_sha256": mapping_fingerprint(new_mapping),
            "same_source_id_set": old_ids == new_ids,
            "same_award_code_set": old_codes == new_codes,
            "same_one_to_one_sourceid_awardcode_mapping": old_mapping == new_mapping,
            "identity_or_lifecycle_semantics_proven": False,
        },
        "added_source_ids": added,
        "removed_source_ids": removed,
        "changed_record_count": len(changed),
        "changed_field_counts": dict(sorted(field_counts.items())),
        "amount_transition_counts": dict(sorted(amount_transitions.items())),
        "changed_records": changed,
        "authoritative_lifecycle_semantics_proven": False,
        "canonical_opportunity_admission": False,
        "interpretation": "Observed normalized-field differences only; ARC remains award context.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-sha256", required=True)
    parser.add_argument("--current-sha256", required=True)
    args = parser.parse_args()
    private_output(args.output, [args.baseline,args.current])
    result = reconcile(args.baseline, args.current, baseline_sha256=args.baseline_sha256, current_sha256=args.current_sha256)
    output = private_output_path(args.output)
    write_new(output,result,[args.baseline,args.current])
    print(json.dumps({
        "baseline_count": result["baseline"]["record_count"],
        "current_count": result["current"]["record_count"],
        "added": len(result["added_source_ids"]),
        "removed": len(result["removed_source_ids"]),
        "changed_records": result["changed_record_count"],
        "changed_field_counts": result["changed_field_counts"],
        "amount_transition_counts": result["amount_transition_counts"],
        "award_code_mapping": result["award_code_mapping"],
        "output": str(output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
