"""Read-only, fail-closed inventory for DEV publication blank-stub recovery.

This consumes saved snapshots only. Optional detailed snapshots use
``{"complete": true, "next_links": [], "items": [{"Id": 123, ...}]}``; item details carry a
``fields`` mapping of all scalar SharePoint internal names and ``ETag``,
``Created`` and ``Modified``. Computed/navigation and attachment fields are
not scalar restore values; attachment files require a separate export. Version
entries must also carry ``version_history_complete: true`` and
``version_next_links: []`` for each item: completeness of the outer item export
does not prove that every version collection was fully paged. Attachment
entries carry ``attachments`` lists. A context snapshot must explicitly record
``list``, ``permissions``, ``retention`` and ``versioning`` sections. Each section
requires ``complete: true``, an observed UTC timestamp, a provenance ``source``
and a nonempty ``data`` object. Missing evidence is reported per item and never
inferred from an empty or absent response.

Retention additionally requires explicit policy applicability for the site and
list: ``data.applicability`` is either ``policy_applies`` or
``no_policy_applies``. It also requires an authoritative policy owner and an
evidence-backed status for site policy, list policy, retention labels, holds,
and record declarations. ``verified_none`` is distinct from ``not_observable``;
the latter keeps the context incomplete. Item metadata alone cannot establish
retention scope.
When a policy applies, its inventory alone does not clear a restore. The
retention section must also carry an explicit ``restore_clearance`` decision
of ``permitted`` with a decision owner and evidence reference.
"""

from __future__ import annotations

import argparse
import copy
import math
import re
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__:
    from scripts.audit_publication_writer_readiness import integer as _integer, utc
else:
    from audit_publication_writer_readiness import integer as _integer, utc

# SPDX-License-Identifier: Apache-2.0


def strict_json_loads(raw: str | bytes) -> Any:
    """Reject ambiguous saved JSON before interpreting or hashing evidence."""
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise ValueError('Duplicate JSON object key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('Nonfinite JSON number')
    def number(value):
        result = float(value)
        if not __import__('math').isfinite(result):
            raise ValueError('Nonfinite JSON number')
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=number)


def _target(snapshot: dict) -> dict | None:
    """Read explicit identity or our emitted binding without upgrading diagnostics."""
    top = snapshot.get('target')
    binding = snapshot.get('target_binding')
    bound = None
    if 'target_binding' in snapshot:
        if not isinstance(binding, dict) or type(binding.get('qualified')) is not bool:
            raise ValueError('Invalid target binding qualification')
        if binding['qualified']:
            bound = binding.get('target')
            if bound is None:
                raise ValueError('Qualified target binding lacks identity')
        elif 'target' in binding or 'target' in snapshot:
            raise ValueError('Unqualified binding cannot carry qualified target identity')
    for value in (top, bound):
        if value is not None and (not isinstance(value, dict) or set(value) != {'site_id', 'list_id'}
                or any(not isinstance(v, str) or not v or v != v.strip() for v in value.values())):
            raise ValueError('Invalid site/list target')
    if 'target' in snapshot and top is None:
        raise ValueError('Invalid site/list target')
    if top is not None and bound is not None and top != bound:
        raise ValueError('Conflicting top-level and bound target identities')
    return top if top is not None else bound


def same_target(*snapshots: dict) -> dict:
    """Require exact scope from explicit targets or validated emitted bindings."""
    targets = [_target(snapshot) for snapshot in snapshots]
    if not targets or any(target is None for target in targets):
        raise ValueError('Explicit site/list target required; receipt unqualified')
    if any(target != targets[0] for target in targets):
        raise ValueError('Evidence target mismatch')
    return copy.deepcopy(targets[0])


def target_qualification(*snapshots: dict) -> dict:
    """Keep origin qualification separate from successful content diagnostics."""
    present = [s for s in snapshots if isinstance(s, dict)]
    targets = [_target(s) for s in present]
    if any(t is not None for t in targets):
        return {'qualified': True, 'target': same_target(*present),
                'evidence_status': 'same_target_bound_diagnostics',
                'success_flags_scope': 'supplied evidence checks only; not native acceptance or authority'}
    return {'qualified': False, 'evidence_status': 'unqualified_diagnostics',
            'success_flags_scope': 'content/ID checks only; native origin unqualified',
            'reason': 'Missing explicit site/list target; ID joins are unqualified diagnostics'}


def _read(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"snapshot must be a JSON object: {path}")
    return value


def count(value: Any, expected: int | None = None, label: str = 'count') -> int:
    result = _integer({label: value}, label)
    if expected is not None and result != expected:
        raise ValueError(label + ' disagrees with exact item set')
    return result


def _id(value: Any) -> int:
    result = count(value, label='item ID')
    if result <= 0:
        raise ValueError('invalid item ID')
    return result


def schema_inventory(schema: dict) -> dict[str, dict]:
    fields = schema.get('fields')
    if not isinstance(fields, list) or not fields:
        raise ValueError('Nonempty schema field inventory required')
    count(schema.get('count'), len(fields), 'schema count')
    names = [f.get('internal_name') if isinstance(f, dict) else None for f in fields]
    if any(not isinstance(n, str) or not n or n != n.strip() for n in names) or len(names) != len(set(names)):
        raise ValueError('Schema has padded, missing or duplicate internal names')
    if any(not isinstance(f.get('type'), str) or not f['type'] or f['type'] != f['type'].strip() for f in fields):
        raise ValueError('Explicit schema field types required')
    return dict(zip(names, fields))


def version_entries(entries: Any) -> list[dict]:
    if not isinstance(entries, list) or not entries or any(not isinstance(v, dict) for v in entries):
        raise ValueError('Nonempty version history required')
    labels = [v.get('VersionLabel') for v in entries]
    if any(not isinstance(v, str) or not re.fullmatch(r'[0-9]+\.[0-9]+',v) for v in labels) or len(labels) != len(set(labels)):
        raise ValueError('Missing, padded or duplicate version labels')
    if any(type(v.get('IsCurrentVersion')) is not bool for v in entries) or sum(v['IsCurrentVersion'] for v in entries) != 1:
        raise ValueError('current and older version markers ambiguous')
    return entries


def private_output(output: Path, inputs: list[Path], *, root: Path | None = None) -> Path:
    allowed = ((root or Path(__file__).resolve().parents[1]) / 'private/ops').resolve()
    paths = [Path(p) for p in [*inputs, output]]
    for path in paths:
        if not path.resolve().is_relative_to(allowed) or path.resolve() == allowed:
            raise ValueError('All evidence inputs/output must remain under ignored private/ops')
        cursor=path
        while True:
            if cursor.is_symlink(): raise ValueError('Symlink evidence paths refused')
            if cursor.resolve()==allowed: break
            if cursor==cursor.parent: raise ValueError('Evidence path has no private root')
            cursor=cursor.parent
    if len({p.resolve() for p in paths}) != len(paths) or output.exists():
        raise ValueError('Distinct inputs and exclusive new output required; cannot overwrite an input')
    return output.resolve()


def governed_policy(policy: Any) -> dict:
    keys = {'policy_id', 'evidence_ref', 'max_age_hours', 'max_skew_hours', 'max_context_skew_hours', 'max_review_age_hours'}
    if not isinstance(policy, dict) or set(policy) != keys:
        raise ValueError('Caller-explicit governed freshness policy required')
    if any(not isinstance(policy[k], str) or not policy[k] or policy[k] != policy[k].strip() for k in ('policy_id','evidence_ref')):
        raise ValueError('Governed policy identity/evidence required')
    if any(type(policy[k]) not in (int,float) or not math.isfinite(policy[k]) or policy[k] < 0 for k in keys-{'policy_id','evidence_ref'}):
        raise ValueError('Governed time limits must be nonnegative finite numbers')
    return copy.deepcopy(policy)


def _by_id(snapshot: dict[str, Any] | None, label: str) -> dict[int, dict[str, Any]]:
    if snapshot is None:
        return {}
    rows = snapshot.get("items")
    if not isinstance(rows, list):
        raise ValueError(f"{label} snapshot requires items array")
    indexed: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{label} item must be an object")
        key = _id(row.get("Id", row.get("id")))
        if 'Id' in row and 'id' in row and _id(row['Id']) != _id(row['id']):
            raise ValueError('Conflicting item ID aliases')
        if key in indexed:
            raise ValueError(f"duplicate {label} item ID {key}")
        indexed[key] = row
    return indexed


def schema_field_inventory_sha256(fields: list[dict[str, Any]]) -> str:
    """Digest the schema field definitions using a deterministic encoding."""
    canonical = json.dumps(
        sorted(fields, key=lambda field: field["internal_name"]),
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _context_section_complete(section: Any, name: str, now: datetime) -> bool:
    if not isinstance(section, dict) or section.get("complete") is not True:
        return False
    if not isinstance(section.get("source"), str) or not section["source"].strip():
        return False
    observed = section.get("observed_at_utc")
    if not isinstance(observed, str) or not observed.strip():
        return False
    try:
        parsed = utc(observed)
    except ValueError:
        return False
    if parsed.tzinfo is None:
        return False
    # A future-dated or malformed-offset observation is not a usable snapshot
    # receipt. Normalize both timestamps to UTC before comparing.
    if parsed.utcoffset() is None:
        return False
    if parsed.astimezone(timezone.utc) > now:
        return False
    data = section.get("data")
    if not isinstance(data, dict) or not data:
        return False
    if any(v is None or (isinstance(v, str) and v.strip().lower() in
           {"", "unknown", "not captured", "not observed"}) for v in data.values()):
        return False
    if name == "retention":
        applicability = data.get("applicability")
        if not isinstance(applicability, str) or applicability not in {"policy_applies", "no_policy_applies"}:
            return False
        if not isinstance(data.get("scope_evidence"), str) or not data["scope_evidence"].strip():
            return False
        if not isinstance(data.get("authoritative_policy_owner"), str) or not data["authoritative_policy_owner"].strip():
            return False
        required_controls = {
            "site_policy", "list_policy", "retention_labels", "holds", "record_declarations",
        }
        controls = data.get("control_inventory")
        if not isinstance(controls, dict) or set(controls) != required_controls:
            return False
        statuses = []
        for control in controls.values():
            if not isinstance(control, dict):
                return False
            status = control.get("status")
            if not isinstance(status, str) or status not in {"verified_none", "present"}:
                return False
            if not isinstance(control.get("evidence_ref"), str) or not control["evidence_ref"].strip():
                return False
            statuses.append(status)
        if applicability == "no_policy_applies" and any(s != "verified_none" for s in statuses):
            return False
        if applicability == "policy_applies" and "present" not in statuses:
            return False
    return True


def _retention_clearance(context: Any, now: datetime) -> str:
    """Keep an observed policy distinct from permission to restore an item."""
    section = context.get("retention") if isinstance(context, dict) else None
    if not _context_section_complete(section, "retention", now):
        return "unknown"
    data = section["data"]
    if data["applicability"] == "no_policy_applies":
        return "no_policy_applies"
    clearance = data.get("restore_clearance")
    if not isinstance(clearance, dict):
        return "pending"
    if clearance.get("decision") == "prohibited":
        return "prohibited"
    if (clearance.get("decision") == "permitted"
            and all(isinstance(clearance.get(name), str) and clearance[name].strip()
                    for name in ("decision_owner", "evidence_ref"))):
        return "permitted"
    return "pending"


def _observed_at(snapshot: Any, *keys: str) -> datetime | None:
    if not isinstance(snapshot, dict):
        return None
    for key in keys:
        value = snapshot.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is not None and parsed.utcoffset() is not None:
            return parsed.astimezone(timezone.utc)
    return None


def _snapshot_freshness(snapshots: dict[str, Any], now: datetime, policy: dict) -> dict[str, Any]:
    """Summarize timestamp coverage, age, and capture skew without source values."""
    observed = {name: _observed_at(snapshot, "observed_at_utc", "date_utc")
                for name, snapshot in snapshots.items() if snapshot is not None}
    missing = sorted(name for name, timestamp in observed.items() if timestamp is None)
    valid = [timestamp for timestamp in observed.values() if timestamp is not None]
    ages = [(now - timestamp).total_seconds() for timestamp in valid]
    future = sorted(name for name, timestamp in observed.items()
                    if timestamp is not None and timestamp > now)
    # Caller-supplied policy is metadata, never authority or a fresh native read.
    stale = sorted(name for name, age in zip(
        (name for name, timestamp in observed.items() if timestamp is not None), ages
    ) if age > policy["max_age_hours"] * 3600)
    skew = (max(valid) - min(valid)).total_seconds() if len(valid) > 1 else 0.0
    gaps = []
    if missing:
        gaps.append("snapshot_observation_time_missing")
    if future:
        gaps.append("snapshot_observation_time_in_future")
    if stale:
        gaps.append("snapshot_evidence_exceeds_governed_age")
    if skew > policy["max_skew_hours"] * 3600:
        gaps.append("snapshot_observation_window_exceeds_governed_skew")
    return {
        "policy_max_age_hours": policy["max_age_hours"],
        "policy_max_skew_hours": policy["max_skew_hours"],
        "observed_snapshot_count": len(observed),
        "timestamped_snapshot_count": len(valid),
        "missing_timestamp_snapshots": missing,
        "future_timestamp_snapshots": future,
        "stale_snapshots": stale,
        "observation_window_seconds": skew,
        "complete": not gaps,
        "gaps": gaps,
    }


def _input_evidence(snapshots: dict[str, Any]) -> dict[str, Any]:
    """Bind a private readiness receipt to inputs without repeating row data."""
    result: dict[str, Any] = {}
    for name, snapshot in snapshots.items():
        if snapshot is None:
            continue
        encoded = json.dumps(snapshot, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")
        rows = snapshot.get("rows", snapshot.get("items", snapshot.get("fields")))
        if isinstance(rows, dict):
            row_count = len(rows)
        elif isinstance(rows, list):
            row_count = len(rows)
        else:
            row_count = None
        result[name] = {
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "entry_count": row_count,
            "complete": snapshot.get("complete") is True,
            "unpaged": snapshot.get("next_links") == [],
            "observed_at_utc": snapshot.get("observed_at_utc") or snapshot.get("date_utc"),
        }
    return result


def _provenance_review(value: Any, now: datetime, policy: dict) -> tuple[bool, str | None]:
    """Require a per-item adjudication before proposing restore eligibility.

    Flow-run/cohort correlation is supporting evidence, not an item-level
    disposition. A review must identify its reviewer, rationale evidence,
    decision and a timezone-aware review timestamp.
    """
    if not isinstance(value, dict) or value.get("status") != "reviewed":
        return False, None
    decision = value.get("decision")
    if decision not in {"remove_and_restore", "retain"}:
        return False, None
    for field in ("reviewer", "evidence_ref", "rationale"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            return False, None
    reviewed_at = value.get("reviewed_at_utc")
    if not isinstance(reviewed_at, str) or not reviewed_at.strip():
        return False, None
    try:
        parsed = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    except ValueError:
        return False, None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return False, None
    age_seconds = (now - parsed.astimezone(timezone.utc)).total_seconds()
    if age_seconds < 0 or age_seconds > policy["max_review_age_hours"] * 3600:
        return False, None
    return True, decision


def plan(
    registry: dict[str, Any], candidates: dict[str, Any], schema: dict[str, Any],
    details: dict[str, Any] | None = None,
    versions: dict[str, Any] | None = None,
    attachments: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    flow_evidence: dict[str, Any] | None = None,
    now: datetime | None = None,
    freshness_policy: dict | None = None,
) -> dict[str, Any]:
    if not isinstance(now, datetime):
        raise ValueError('Caller-explicit aware UTC planning time required')
    planning_now = utc(now.isoformat())
    policy = governed_policy(freshness_policy)
    target_binding = target_qualification(registry, candidates, schema, details, versions, attachments)
    registry, candidates, schema, details, versions, attachments, context, flow_evidence = copy.deepcopy(
        (registry, candidates, schema, details, versions, attachments, context, flow_evidence))
    if registry.get("complete") is not True or registry.get("next_links") != []:
        raise ValueError("registry export is not explicitly complete and unpaged")
    registry_rows = _by_id({"items": registry.get("rows")}, "registry")
    candidate_rows = _by_id(candidates, "candidate")
    if count(candidates.get("candidate_count")) != len(candidate_rows):
        raise ValueError("candidate count disagrees with item set")
    if not candidate_rows:
        raise ValueError("empty candidate set")
    if any('SourceKey' not in row or (row['SourceKey'] is not None and
           (not isinstance(row['SourceKey'], str) or row['SourceKey'] != row['SourceKey'].strip()))
           for row in registry_rows.values()):
        raise ValueError('Missing, padded or non-text SourceKey; do not normalize identities')
    current_blanks = {
        key for key, row in registry_rows.items()
        if not str(row.get("SourceKey") or "").strip()
    }
    if current_blanks != set(candidate_rows):
        raise ValueError("candidate IDs differ from complete current blank-key set")
    schema_inventory(schema)
    fields = schema.get("fields")
    if not isinstance(fields, list) or schema.get("count") != len(fields):
        raise ValueError("schema field inventory is incomplete")
    if any(not isinstance(field, dict) for field in fields):
        raise ValueError("schema field inventory entries must be objects")
    names = [field.get("internal_name") for field in fields]
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("schema has missing or invalid internal names")
    field_names = set(names)
    if len(field_names) != len(fields):
        raise ValueError("schema has missing or duplicate internal names")
    schema_inventory_gaps = []
    if schema.get("inventory_complete") is not True:
        schema_inventory_gaps.append("complete_schema_inventory_not_declared")
    if not isinstance(schema.get("source"), str) or not schema["source"].strip():
        schema_inventory_gaps.append("schema_inventory_provenance_missing")
    expected_inventory_digest = schema_field_inventory_sha256(fields)
    if schema.get("inventory_sha256") != expected_inventory_digest:
        schema_inventory_gaps.append("schema_inventory_digest_missing_or_mismatched")
    schema_inventory_complete = not schema_inventory_gaps
    excluded_fields = sorted(
        {str(f["internal_name"]) for f in fields
         if f.get("type") in {"Computed", "Attachments"}}
    )
    scalar_fields = field_names - set(excluded_fields)
    detail_rows = _by_id(details, "details")
    version_rows = _by_id(versions, "versions")
    attachment_rows = _by_id(attachments, "attachments")
    for label, mapping in (("details", detail_rows), ("versions", version_rows), ("attachments", attachment_rows)):
        if set(mapping) - set(candidate_rows):
            raise ValueError(f"{label} snapshot includes non-candidate IDs")
    all_coverage = {
        label: snap is not None and snap.get("complete") is True
        and snap.get("next_links") == [] and set(mapping) == set(candidate_rows)
        for label, snap, mapping in (("details", details, detail_rows),
                                      ("versions", versions, version_rows),
                                      ("attachments", attachments, attachment_rows))
    }
    context_sections = ("list", "permissions", "retention", "versioning")
    context_section_gaps = [
        section for section in context_sections
        if not isinstance(context, dict) or not _context_section_complete(context.get(section), section, planning_now)
    ]
    context_complete = isinstance(context, dict) and context.get("complete") is True and not context_section_gaps
    policy_clearance = _retention_clearance(context, planning_now)
    freshness_snapshots = {
        "registry": registry,
        "candidates": candidates,
        "schema": schema,
        "details": details,
        "versions": versions,
        "attachments": attachments,
    }
    if isinstance(context, dict):
        freshness_snapshots.update({f"context_{name}": context.get(name)
                                    for name in context_sections})
    freshness = _snapshot_freshness(freshness_snapshots, planning_now, policy)
    input_snapshots = {
        "registry": registry,
        "candidates": candidates,
        "schema": schema,
        "details": details,
        "versions": versions,
        "attachments": attachments,
        "context": context,
        "flow_evidence": flow_evidence,
    }
    candidate_run = (
        flow_evidence.get("candidate_flow_run")
        if isinstance(flow_evidence, dict) else None
    )
    run_id = candidate_run.get("run_id") if isinstance(candidate_run, dict) else None
    direct_id = None
    cohort_start = cohort_end = None
    cohort_hour = None
    if isinstance(candidate_run, dict):
        raw_direct_id = candidate_run.get("first_iteration_created_item_id")
        if raw_direct_id is not None:
            direct_id = _id(raw_direct_id)
        bounds = candidate_run.get("current_contiguous_id_cohort", "")
        # Only consume the deliberately narrow `start-end:` form already
        # recorded in the authenticated readback. Malformed evidence is ignored.
        import re
        match = re.match(r"^(\d+)-(\d+):", str(bounds))
        if match:
            cohort_start, cohort_end = int(match.group(1)), int(match.group(2))
        cohort_hour = candidate_run.get("matching_stub_created_utc_hour")
    # Reject a context bundle assembled from observations taken at materially
    # different times. This is a restore-readiness inventory, so the four
    # control surfaces must describe one coherent snapshot window.
    context_observations = []
    if isinstance(context, dict):
        for section_name in context_sections:
            section = context.get(section_name)
            if isinstance(section, dict) and isinstance(section.get("observed_at_utc"), str):
                try:
                    observed = datetime.fromisoformat(
                        section["observed_at_utc"].replace("Z", "+00:00")
                    )
                    if observed.tzinfo is not None:
                        context_observations.append(observed.astimezone(timezone.utc))
                except ValueError:
                    pass
    context_window_seconds = (
        (max(context_observations) - min(context_observations)).total_seconds()
        if len(context_observations) == len(context_sections) else None
    )
    if context_window_seconds is not None and context_window_seconds > policy["max_context_skew_hours"] * 3600:
        context_complete = False
        context_section_gaps.append("context_observations_exceed_governed_window")
    rows: list[dict[str, Any]] = []
    for key in sorted(candidate_rows):
        current = registry_rows[key]
        item = detail_rows.get(key, {})
        ver = version_rows.get(key, {})
        att = attachment_rows.get(key, {})
        gaps: list[str] = []
        reviews = flow_evidence.get("item_provenance_reviews") if isinstance(flow_evidence, dict) else None
        review = (reviews.get(str(key), reviews.get(key))
                  if isinstance(reviews, dict) else None)
        provenance_reviewed, provenance_decision = _provenance_review(review, planning_now, policy)
        if not provenance_reviewed:
            gaps.append("item_provenance_review_missing_or_invalid")
        elif provenance_decision == "retain":
            gaps.append("item_provenance_review_disposition_retain")
        if not all_coverage["details"]:
            gaps.append("complete_item_detail_export_missing")
        values = item.get("fields")
        missing_fields: list[str] = []
        extra_fields: list[str] = []
        if isinstance(values, dict):
            observed_detail_fields = set(values) - set(excluded_fields)
            missing_fields = sorted(scalar_fields - observed_detail_fields)
            extra_fields = sorted(observed_detail_fields - field_names)
        if not isinstance(values, dict) or missing_fields or extra_fields:
            gaps.append("full_field_values_missing")
            if missing_fields:
                gaps.append("scalar_field_values_missing")
            if extra_fields:
                gaps.append("unrecognized_field_values_present")
        for name in ("GUID", "ETag", "Created", "Modified"):
            if not item.get(name):
                gaps.append(f"{name.lower()}_missing")
            elif name in ('Created', 'Modified'):
                try: utc(item[name])
                except (ValueError, TypeError): gaps.append(name.lower()+'_date_unknown')
        entries = ver.get('versions')
        if isinstance(entries, list) and entries and ver.get('version_history_complete') is True and ver.get('version_next_links') == []:
            version_entries(entries)
        if (not all_coverage["versions"] or not entries or not isinstance(ver.get("versions"), list)
                or ver.get("version_history_complete") is not True
                or ver.get("version_next_links") != []):
            gaps.append("complete_version_history_missing")
        if not all_coverage["attachments"] or not isinstance(att.get("attachments"), list):
            gaps.append("complete_attachment_export_missing")
        if not context_complete:
            # Keep context gaps specific. A missing retention decision must
            # not erase evidence that item values, histories and permissions
            # were successfully exported.
            gaps.extend(f"context_{name}_missing" for name in context_section_gaps)
        if policy_clearance in {"pending", "prohibited"}:
            gaps.append(f"retention_restore_{policy_clearance}")
        if schema_inventory_gaps:
            gaps.extend(f"restore_{name}" for name in schema_inventory_gaps)
        if not freshness["complete"]:
            gaps.extend(f"restore_{name}" for name in freshness["gaps"])
        item_export_gaps = [gap for gap in gaps if gap not in {
            "context_retention_missing",
            "item_provenance_review_missing_or_invalid",
            "item_provenance_review_disposition_retain",
        } and not gap.startswith(("restore_", "retention_restore_"))]
        restore_gaps = list(gaps)
        created = item.get("Created")
        created_hour = created[:13] if isinstance(created, str) and len(created) >= 13 else None
        if run_id and key == direct_id and candidate_run.get("direct_created_item_id_match_proven") is True:
            provenance = {
                "grade": "direct_action_match",
                "flow_run_id": run_id,
                "basis": "saved authenticated run readback records Create returned item ID equal to this item ID",
                "evidence_source": "private/ops/2026-09-24-publication-blank-stub-readback.json",
            }
        elif (run_id and cohort_start is not None and cohort_end is not None
              and cohort_start <= key <= cohort_end and created_hour == cohort_hour):
            provenance = {
                "grade": "cohort_correlation_only",
                "flow_run_id": run_id,
                "basis": "item ID falls in contiguous cohort and Created hour matches; no item-specific Create output",
                "evidence_source": "private/ops/2026-09-24-publication-blank-stub-readback.json",
            }
        else:
            provenance = {
                "grade": "no_individual_flow_correlation",
                "flow_run_id": run_id,
                "basis": "no item-specific flow action evidence; item metadata does not establish origin",
                "evidence_source": None,
            }
        rows.append({
            "Id": key,
            "current_registry_values": current,
            "candidate_metadata": candidate_rows[key],
            "item_detail": item or None,
            "missing_scalar_field_values": missing_fields,
            "extra_detail_field_values": extra_fields,
            "versions": ver.get("versions") if isinstance(ver.get("versions"), list) else None,
            "attachments": att.get("attachments") if isinstance(att.get("attachments"), list) else None,
            "gaps": gaps,
            "item_export_gaps": item_export_gaps,
            "restore_readiness_gaps": restore_gaps,
            "item_export_complete": not item_export_gaps,
            "restore_export_complete": not restore_gaps,
            "policy_clearance": policy_clearance,
            "candidate_evidence_complete": not restore_gaps,
            "restore_ready": False,
            "write_payload": None,
            "provenance_status": "reviewed" if provenance_reviewed else "unresolved",
            "provenance_decision": provenance_decision,
            "provenance_review": review if provenance_reviewed else None,
            "flow_correlation": provenance,
        })
    return {
        "receipt_schema_version": "publication-stub-readiness/v2",
        "generated_at_utc": planning_now.isoformat(),
        "freshness_policy": policy,
        "read_only": True,
        "candidate_count": len(rows),
        "registry_count": len(registry_rows),
        "item_exports_complete": all(row["item_export_complete"] for row in rows),
        "item_export_complete_count": sum(row["item_export_complete"] for row in rows),
        "all_restore_exports_complete": all(row["restore_export_complete"] for row in rows),
        "restore_ready_count": 0,
        "target_binding": target_binding,
        "candidate_evidence_complete_count": sum(row["candidate_evidence_complete"] for row in rows),
        # Compatibility field: this has historically meant the full gated
        # restore package, including policy context. Keep it fail-closed.
        "all_exports_complete": all(row["restore_export_complete"] for row in rows),
        "source_observed_at_utc": registry.get("observed_at_utc"),
        "excluded_non_scalar_fields": excluded_fields,
        "field_coverage_basis": "all schema scalar fields; computed/navigation and attachment fields excluded",
        "schema_inventory_complete": schema_inventory_complete,
        "schema_inventory_gaps": schema_inventory_gaps,
        "input_evidence": _input_evidence(input_snapshots),
        "snapshot_freshness": freshness,
        "context": context,
        "context_section_gaps": context_section_gaps,
        "context_observation_window_seconds": context_window_seconds,
        "flow_evidence_run_id": run_id,
        "irreproducible_by_ordinary_recreation": [
            "original SharePoint item ID", "original creation/modification system metadata",
            "version and audit history", "existing item references or links",
        ],
        "restore_rehearsal": "not_performed",
        "mutation_authorized": False,
        "items": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("registry", "candidates", "schema"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    for name in ("details", "versions", "attachments", "context", "flow_evidence"):
        parser.add_argument(f"--{name.replace('_', '-')}", dest=name, type=Path)
    parser.add_argument('--as-of-utc', required=True)
    parser.add_argument('--freshness-policy', required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    private_output(args.output, [p for p in [getattr(args, name) for name in
        ('registry','candidates','schema','details','versions','attachments','context','flow_evidence','freshness_policy')] if p is not None])
    report = plan(*(_read(getattr(args, name)) for name in
                    ("registry", "candidates", "schema", "details", "versions", "attachments", "context", "flow_evidence")), now=utc(args.as_of_utc), freshness_policy=_read(args.freshness_policy))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"{report['candidate_count']} candidates; complete item exports: "
          f"{report['item_export_complete_count']}; restore-ready: "
          f"{report['restore_ready_count']}; no mutation")


if __name__ == "__main__":
    main()
