"""Derive award context from a downloaded Microsoft ARC full-source commit.

Offline only. Full unknown fields remain in the downloaded source files, bound
by stored-file hashes. No network, canonical opportunity admission or lifecycle
inference. Retain the downloaded folder alongside the derived award view.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

try:
    from scripts import grants_arc_api as arc
    from scripts.grants_sources import require_enabled_source
    from scripts.patch_clinicaltrials_read_retries import strict_json
except ImportError:
    import grants_arc_api as arc
    from grants_sources import require_enabled_source
    from patch_clinicaltrials_read_retries import strict_json


def _aware(value):
    if not isinstance(value, str):
        raise ValueError("Source timestamp required")  # noqa: TRY004 - malformed evidence uses ValueError
    date = dt.datetime.fromisoformat(value)
    if date.tzinfo is None or date.utcoffset() is None:
        raise ValueError("Source timestamp must be timezone-aware")
    return date


def _load(path, root):
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Source path escapes downloaded commit")
    if not path.is_file() or path.stat().st_size > 4_000_000:
        raise ValueError("Source file missing or beyond bounded size")
    raw = path.read_bytes()
    data = strict_json(raw)
    if not isinstance(data, dict):
        raise ValueError("Source file must contain an object")  # noqa: TRY004 - malformed evidence uses ValueError
    return data, raw


def read_commit(
    folder: Path,
    *,
    catalogue_path=arc.DEFAULT_CATALOGUE,
    expected_schedule="manual_only",
):
    """Replay a saved commit; schedule matching never proves trigger origin."""
    if not isinstance(expected_schedule, str) or expected_schedule not in (
        "manual_only",
        "weekly",
    ):
        raise ValueError("Expected schedule must be manual_only or weekly")
    require_enabled_source(catalogue_path, "arc-awards-api")
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Downloaded commit directory required")
    manifest, mb = _load(folder / "manifest.json", folder)
    fixed = {
        "format": "rims-arc-source-commit-v1",
        "source_id": "arc-awards-api",
        "record_kind": "awards_only",
        "source_api": arc.API_BASE,
        "complete_reads": 2,
        "canonical_opportunity_admission": False,
        "candidate_filter_applied": False,
        "schedule": expected_schedule,
        "page_size": 500,
    }
    if any(
        type(manifest.get(k)) is not type(v) or manifest.get(k) != v
        for k, v in fixed.items()
    ):
        raise ValueError("ARC commit source or award-only boundary changed")
    total = manifest.get("source_total")
    pages = manifest.get("page_count")
    if type(total) is not int or not 0 <= total <= arc.MAX_TOTAL_AWARDS:
        raise ValueError("Bounded exact source total required")
    if type(pages) is not int or pages != max(1, (total + 499) // 500):
        raise ValueError("Exact page coverage required")
    if not isinstance(manifest.get("run"), str) or not manifest["run"].strip():
        raise ValueError("Native run identity required")
    committed = _aware(manifest.get("committed_utc"))
    names = {
        f"pass-{read}-page-{page}.json"
        for read in (1, 2)
        for page in range(1, pages + 1)
    }
    declared = manifest.get("files")
    if (
        not isinstance(declared, list)
        or len(declared) != len(names)
        or any(
            not isinstance(f, dict)
            or f.get("name") not in names
            or f.get("verification") != "exact_base64_stored_content_readback"
            for f in declared
        )
        or {f["name"] for f in declared} != names
    ):
        raise ValueError("Manifest file coverage incomplete or duplicated")
    if {p.name for p in folder.iterdir()} != names | {"manifest.json"}:
        raise ValueError("Missing or unmanifested source file")
    hashes = {}
    passes = []
    awards = []
    all_attribute_fields = set()
    for read in (1, 2):
        row_hashes = {}
        records = []
        for page in range(1, pages + 1):
            name = f"pass-{read}-page-{page}.json"
            envelope, raw = _load(folder / name, folder)
            expected_request = {
                "method": "GET",
                "uri": arc.API_BASE,
                "queries": {"page[number]": page, "page[size]": 500},
            }
            if (
                json.dumps(envelope.get("request"), sort_keys=True, allow_nan=False)
                != json.dumps(expected_request, sort_keys=True, allow_nan=False)
                or type(envelope.get("pass")) is not int
                or envelope["pass"] != read
            ):
                raise ValueError("Envelope request differs from declared source page")
            if _aware(envelope.get("captured_utc")) > committed:
                raise ValueError("Capture occurred after declared commit")
            response = envelope.get("response")
            if (
                not isinstance(response, dict)
                or type(response.get("statusCode")) is not int
                or response["statusCode"] != 200
            ):
                raise ValueError("Source response did not succeed")
            payload = response.get("body")
            if not isinstance(payload, dict) or not isinstance(
                payload.get("data"), list
            ):
                raise ValueError("Source data list required")  # noqa: TRY004 - malformed evidence uses ValueError
            if arc._exact_meta(payload, page, 500) != (total, pages):
                raise ValueError("Retained pagination differs from manifest")
            typed = arc.parse_award_page(
                payload, retrieved_at=manifest["committed_utc"]
            )
            for source, record in zip(payload["data"], typed):
                source_id = record["SourceID"]
                if source_id in row_hashes:
                    raise ValueError("Repeated source award ID across pages")
                all_attribute_fields.update(source["attributes"])
                row_hashes[source_id] = hashlib.sha256(
                    json.dumps(
                        source,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest()
            hashes[name] = hashlib.sha256(raw).hexdigest()
            records.extend(typed)
        if len(row_hashes) != total:
            raise ValueError("Retained rows do not cover declared source total")
        passes.append(row_hashes)
        awards = records
    if passes[0] != passes[1]:
        raise ValueError("Full source award content changed across reads")
    return {
        "source": "arc",
        "record_kind": "awards_only",
        "source_total": total,
        "page_count": pages,
        "page_size": 500,
        "complete_reads": 2,
        "snapshot_complete": True,
        "retrieved_utc": manifest["committed_utc"],
        "canonical_opportunity_admission": False,
        "authoritative_lifecycle_semantics_proven": False,
        "source_attribute_fields": sorted(all_attribute_fields),
        "source_row_hashes": passes[1],
        "records": awards,
        "raw_source": {
            "native_manifest": manifest,
            "manifest_sha256": hashlib.sha256(mb).hexdigest(),
            "stored_file_sha256": hashes,
            "native_run": manifest["run"],
            "retention": "Complete response JSON values remain in the downloaded commit files; keep folder with this derived view",
            "qualification": "offline downloaded commit validation; fresh native readback separate",
            "original_transport_bytes_certified": False,
        },
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--catalogue", type=Path, default=arc.DEFAULT_CATALOGUE)
    p.add_argument(
        "--expected-schedule",
        choices=("manual_only", "weekly"),
        default="manual_only",
        help="Match retained manifest cadence; does not certify natural recurrence or authorise acquisition",
    )
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1] / "private/ops"
    if not args.output.resolve().is_relative_to(root.resolve()):
        raise ValueError("Derived output must remain in private/ops")
    if args.output.exists():
        raise ValueError("Refuse to overwrite existing evidence")
    result = read_commit(
        args.folder,
        catalogue_path=args.catalogue,
        expected_schedule=args.expected_schedule,
    )
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(serialized)
    print(
        f"Verified {result['source_total']} award rows across two reads; no canonical opportunity admission"
    )


if __name__ == "__main__":
    main()
