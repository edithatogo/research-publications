"""Read-only, fail-closed preflight for DEV Publication Registry key constraints.

Consumes a complete native aggregate, keyed-row export and reviewed stub ledger.
It never grants authority to dispose of rows or change a SharePoint field.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

# SPDX-License-Identifier: Apache-2.0
if __package__:
    from scripts.reconcile_generation import keyset
    from scripts.plan_publication_stub_restore import private_output, utc
else:
    from reconcile_generation import keyset
    from plan_publication_stub_restore import private_output, utc


def _key(value: object) -> str:
    return value if isinstance(value, str) and value == value.strip() else ""


def assess(aggregate: dict, keyed: dict, disposition: dict) -> dict:
    blockers: list[str] = []
    rows = keyed.get("keyed_rows")
    stubs = disposition.get("items")
    if not isinstance(rows, list) or not isinstance(stubs, list):
        raise ValueError("keyed_rows and disposition items must be arrays")
    if any(not isinstance(r,dict) for r in rows+stubs):
        raise ValueError('Structured item rows required')
    if type(aggregate.get('http')) is not int or aggregate.get("http") != 200 or aggregate.get("pagination_complete") is not True or keyed.get("complete") is not True or keyed.get('next_links') != []:
        blockers.append("incomplete_native_export")
    count = aggregate.get("items_read")
    if any(type(v) is not int or v < 0 for v in (count,aggregate.get('item_count'),keyed.get('total_rows'))) or count != aggregate.get("item_count") or count != keyed.get("total_rows"):
        blockers.append("total_row_count_mismatch")
    if type(keyed.get('keyed_total')) is not int or keyed.get("keyed_total") != len(rows) or count != len(rows) + len(stubs):
        blockers.append("cohort_count_mismatch")
    if aggregate.get("last_item_modified_utc") != keyed.get("max_modified"):
        blockers.append("observation_watermark_mismatch")
    try:
        utc(aggregate.get('last_item_modified_utc')); utc(keyed.get('max_modified'))
    except (TypeError,ValueError):
        blockers.append('observation_watermark_unavailable')
    ids = [row.get("Id") for row in rows] + [row.get("Id") for row in stubs]
    if any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
        blockers.append("invalid_or_overlapping_item_ids")
    source_values = [_key(row.get("SourceKey")) for row in rows]
    try: keyset([{'key':row.get('SourceKey')} for row in rows], allow_empty=True)
    except ValueError: blockers.append('noncanonical_source_key_identity')
    source_counts = Counter(value.casefold() for value in source_values if value)
    if any(not value for value in source_values) or any(n > 1 for n in source_counts.values()):
        blockers.append("blank_or_case_insensitive_duplicate_SourceKey")
    if type(aggregate.get('duplicate_nonblank_source_keys')) is not int or aggregate.get("duplicate_nonblank_source_keys") != 0:
        blockers.append("native_duplicate_SourceKey")
    # Distinct source rows may legitimately share a canonical publication.
    # CanonicalKey is checked for presence but never made a unique constraint.
    if any(not _key(row.get("CanonicalKey")) for row in rows):
        blockers.append("blank_keyed_CanonicalKey")
    if any(type(aggregate.get(k)) is not int for k in ('blank_source_key','blank_canonical_key')) or aggregate.get("blank_source_key") != len(stubs) or aggregate.get("blank_canonical_key") != len(stubs):
        blockers.append("blank_cohort_mismatch")
    if stubs:
        blockers.append("blank_rows_remain")
    if disposition.get("cross_receipt_evidence_coherent") is not True or type(disposition.get('candidate_count')) is not int or disposition.get("candidate_count") != len(stubs):
        blockers.append("stub_ledger_not_coherent")
    if any(row.get("restore_ready") is not True for row in stubs):
        blockers.append("stub_recovery_not_ready")
    if disposition.get("disposition_decided") is not True or disposition.get("mutation_authorized") is not True:
        blockers.append("stub_disposition_not_authorized")
    fields = aggregate.get("field_constraints", {})
    source = fields.get("SourceKey", {})
    canonical = fields.get("CanonicalKey", {})
    if source.get("internal_name") != "field_1" or canonical.get("internal_name") != "field_2":
        blockers.append("field_mapping_mismatch")
    if source.get("indexed") is not True:
        blockers.append("source_key_index_not_enabled")
    if source.get("unique") is not True:
        blockers.append("source_key_uniqueness_not_enabled")
    if source.get("required") is not True:
        blockers.append("source_key_required_not_enabled")
    # No automatic CanonicalKey uniqueness requirement: canonical identity may
    # be shared across source rows. Its existing index is an independent fact.
    return {
        "schema": "publication-key-migration-preflight/v1",
        "read_only": True,
        "mutation_authorized": False,
        "schema_change_authorized": False,
        "write_payload": None,
        "constraint_preflight_ready": not blockers,
        "native_integrity_accepted": False,
        "blockers": sorted(set(blockers)),
        "counts": {"total": count, "keyed": len(rows), "blank_stubs": len(stubs)},
        "field_internal_names": {"SourceKey": source.get("internal_name"), "CanonicalKey": canonical.get("internal_name")},
        "note": "Historical exports cannot authorize or prove a fresh native migration. Re-export, compare ETags and versions, apply one guarded setting at a time, and read back rejection probes.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--aggregate", required=True, type=Path)
    p.add_argument("--keyed", required=True, type=Path)
    p.add_argument("--disposition", required=True, type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    sources = [args.aggregate, args.keyed, args.disposition]
    if args.output: private_output(args.output, sources)
    payloads = [x.read_bytes() for x in sources]
    result = assess(*(json.loads(x) for x in payloads))
    result["input_sha256"] = {name: hashlib.sha256(data).hexdigest() for name, data in zip(("aggregate", "keyed", "disposition"), payloads)}
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        if args.output.resolve() in {x.resolve() for x in sources}:
            p.error("output must not overwrite input")
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x',encoding='utf-8') as stream: stream.write(text)
    else:
        print(text, end="")
    return 0 if result["constraint_preflight_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
