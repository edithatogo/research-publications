"""Plan, but never apply, organisation enrichment for a private DEV list readback.

Input and output contain tenant row identifiers and belong under ignored private/ops/.
The plan reuses the tested affiliation matcher and changes only the eight additive
logical organisation fields; the missing native schema remains unqualified.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.organisation_enrichment import load_reference
from scripts.publication_policy import (
    ATTRIBUTION_FIELDS,
)
from scripts.publication_policy import (
    _enrich_policy_evidence as enrich_record,
)

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_OPS = (ROOT / "private" / "ops").resolve()
FIELD_SCHEMA = ROOT / "config" / "publication-organisation-fields.schema.json"


def private_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to(PRIVATE_OPS):
        raise ValueError("tenant row data must stay under ignored private/ops/")
    return path


def build_plan(paths: list[Path]) -> dict:
    if not paths:
        raise ValueError("at least one private readback part is required")
    raw_parts = [path.read_bytes() for path in paths]
    parts = [json.loads(value) for value in raw_parts]
    if any(not isinstance(part, dict) for part in parts):
        raise ValueError("readback parts must be objects")
    if any(type(part.get("part")) is not int for part in parts) or [
        part["part"] for part in parts
    ] != list(range(len(parts))):
        raise ValueError("readback parts must be consecutive and ordered")
    if any(
        not isinstance(part.get("surface"), str)
        or not part["surface"].strip()
        or part["surface"] != part["surface"].strip()
        for part in parts
    ):
        raise ValueError("unexpected readback surface")
    if any(
        "error" in part
        or part.get("errors")
        or part.get("next_links")
        or ("partial" in part and part["partial"] is not False)
        for part in parts
    ):
        raise ValueError("Readback error or incomplete part")
    for part in parts:
        total = part.get("total")
        eligible = part.get("eligible")
        list_name = part.get("list")
        if (
            type(total) is not int
            or total < 0
            or type(eligible) is not int
            or eligible < 0
            or eligible > total
            or not isinstance(list_name, str)
            or not list_name.strip()
        ):
            raise ValueError("readback part is missing valid list/count provenance")
        if not isinstance(part.get("rows"), list):
            raise ValueError("readback part rows must be a list")  # noqa: TRY004 - retained validator contract
    totals = {(part["total"], part["eligible"], part["list"]) for part in parts}
    if len(totals) != 1:
        raise ValueError("readback part totals or list target differ")
    rows = [row for part in parts for row in part["rows"]]
    if len(rows) != parts[0]["eligible"]:
        raise ValueError("readback parts do not cover every eligible affiliation")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("readback rows must be objects")  # noqa: TRY004 - retained validator contract
        row_id = row.get("Id")
        source_key = row.get("SourceKey")
        canonical_key = row.get("CanonicalKey")
        affiliation = row.get("AffiliationsRaw")
        if type(row_id) is not int or row_id <= 0:
            raise ValueError("readback row requires a positive integer registry ID")
        if (
            not isinstance(source_key, str)
            or not source_key.strip()
            or not isinstance(canonical_key, str)
            or not canonical_key.strip()
            or source_key != source_key.strip()
            or canonical_key != canonical_key.strip()
        ):
            raise ValueError(
                "readback row requires nonblank SourceKey and CanonicalKey identity"
            )
        if not isinstance(affiliation, str) or not affiliation.strip():
            raise ValueError("readback row requires explicit affiliation text")
        if any(row.get(field) not in (None, "") for field in ATTRIBUTION_FIELDS):
            raise ValueError(
                "organisation field already populated or has an invalid value"
            )
    ids = [row["Id"] for row in rows]
    sources = [row["SourceKey"] for row in rows]
    canonicals = [row["CanonicalKey"] for row in rows]
    if (
        len(set(ids)) != len(rows)
        or len(set(sources)) != len(rows)
        or len(set(canonicals)) != len(rows)
    ):
        raise ValueError("duplicate registry ID or publication key in readback")
    # Logical evidence fields match the retained source contract. The native
    # schema is absent in this checkout; no native mapping qualification follows.
    fields = ATTRIBUTION_FIELDS
    reference = load_reference()
    updates = []
    methods = Counter()
    keysets = Counter()
    for row in rows:
        enriched = enrich_record(
            {
                "AffiliationsRaw": row["AffiliationsRaw"],
                "PublicationDateRaw": row.get("PublicationDateRaw"),
                "PublicationDatePrecision": row.get("PublicationDatePrecision"),
            },
            reference,
        )
        methods[enriched["OrganisationMatchMethod"]] += 1
        if not enriched["OrganisationKeys"]:
            continue
        values = {field: enriched[field] for field in fields}
        keysets[values["OrganisationKeys"]] += 1
        updates.append(
            {
                "Id": row["Id"],
                "SourceKey": row["SourceKey"],
                "CanonicalKey": row["CanonicalKey"],
                "fields": values,
            }
        )
    fingerprint = hashlib.sha256(
        json.dumps(
            sorted(rows, key=lambda row: row["Id"]),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return {
        "mode": "DRY_RUN_ONLY",
        "source": "declared frozen publication affiliation readback; native provenance unqualified",
        "declared_readback_surfaces": sorted({part["surface"] for part in parts}),
        "candidate_only": True,
        "write_authorized": False,
        "consumer_accepted": False,
        "review_authority": False,
        "routine_admission_prerequisite": False,
        "native_field_contract_qualified": False,
        "native_field_contract_dependency": str(FIELD_SCHEMA.relative_to(ROOT)),
        "input_part_sha256": [hashlib.sha256(value).hexdigest() for value in raw_parts],
        "original_rows": copy.deepcopy(rows),
        "input_sha256": fingerprint,
        "list_item_count": parts[0]["total"],
        "eligible_affiliation_count": len(rows),
        "candidate_update_count": len(updates),
        "unmatched_count": methods["unmatched"],
        "method_counts": dict(sorted(methods.items())),
        "organisation_keysets": dict(sorted(keysets.items())),
        "candidate_updates": updates,
        "boundary": "No list writes. Re-read exact row/key/affiliation before any controlled apply; preserve all existing fields and unknown dates.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    paths = [private_path(value) for value in args.input]
    output = private_path(args.output)
    if output.exists():
        raise FileExistsError(output)
    plan = build_plan(paths)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(plan, indent=2) + "\n")
    print(
        f"DRY_RUN_ONLY: {plan['candidate_update_count']} matched, {plan['unmatched_count']} unmatched of {plan['eligible_affiliation_count']} eligible affiliations"
    )


if __name__ == "__main__":
    main()
