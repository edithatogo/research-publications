"""Pure append-only publication retention; no acquisition, commit or tenant call.

Validated native cycle adapters own preparation. The shared PubMed extraction
and archive-seeding CLI remain outside this dependency-closed source slice.
"""

import copy
import hashlib
import json
from datetime import datetime

from scripts.organisation_enrichment import load_reference
from scripts.publication_policy import evaluate, load_policy, validate_policy


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    ).hexdigest()


def utc(value):
    if not isinstance(value, str):
        raise ValueError("Observation time must be UTC text")  # noqa: TRY004 - retained validator ValueError contract
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0:
        raise ValueError("Observation time must be UTC")
    return timestamp


def validate_state(state):
    if (
        not isinstance(state, dict)
        or set(state) != {"kind", "cycles", "versions", "latest"}
        or state.get("kind") != "publication_retained_versions_v1"
        or not isinstance(state["versions"], list)
        or not isinstance(state["latest"], dict)
        or not isinstance(state["cycles"], list)
    ):
        raise ValueError("Malformed retained state")
    latest = {}
    versions_by_cycle = {}
    for index, version in enumerate(state["versions"]):
        if not isinstance(version, dict) or version.get("RecordSHA256") != digest(
            version.get("Record")
        ):
            raise ValueError("Retained record hash mismatch")
        key, generation = version.get("SourceKey"), version.get("Generation")
        if (
            not isinstance(key, str)
            or not key.startswith(("pubmed:", "dora:"))
            or not isinstance(generation, str)
            or not generation.strip()
        ):
            raise ValueError("Retained source identity and generation required")
        observed = version.get("ObservedAtUTC")
        utc(observed)
        source = "PubMed" if key.startswith("pubmed:") else "DORA"
        versions_by_cycle.setdefault((source, generation, observed), []).append(key)
        latest[key] = index
    if latest != state["latest"]:
        raise ValueError(
            "Latest projection lost or rewrote an accepted source identity"
        )
    seen = set()
    for cycle in state["cycles"]:
        if (
            not isinstance(cycle, dict)
            or cycle.get("source") not in ("PubMed", "DORA")
            or not isinstance(cycle.get("generation"), str)
        ):
            raise ValueError("Malformed retained cycle")
        identity = (cycle["source"], cycle["generation"])
        if identity in seen:
            raise ValueError("Duplicate retained source generation")
        seen.add(identity)
        utc(cycle.get("observed_at"))
        keys = cycle.get("keys")
        if (
            not isinstance(keys, list)
            or any(not isinstance(key, str) for key in keys)
            or keys != sorted(set(keys))
        ):
            raise ValueError("Retained cycle keys must be unique ordered text")
        version_keys = versions_by_cycle.pop((*identity, cycle["observed_at"]), [])
        if sorted(version_keys) != keys:
            raise ValueError("Retained cycle lost or reassigned accepted versions")
    if versions_by_cycle:
        raise ValueError("Retained versions lack their accepted cycle")


def latest_projection(state):
    """Show current values and source disappearance without rewriting history."""
    validate_state(state)
    newest = {}
    for cycle in state["cycles"]:
        newest[cycle["source"]] = set(cycle["keys"])
    result = []
    for key, index in sorted(state["latest"].items()):
        row = copy.deepcopy(state["versions"][index])
        source = "PubMed" if key.startswith("pubmed:") else "DORA"
        row["PresentInLatestSourceCycle"] = key in newest.get(source, set())
        result.append(row)
    return result


def retain(state, records, *, generation, observed_at, source, complete, policy=None):
    """Pure append-only acceptance; source-specific batch replay is idempotent."""
    if (
        complete is not True
        or not isinstance(records, list)
        or not isinstance(generation, str)
        or not generation.strip()
        or generation != generation.strip()
        or source not in ("PubMed", "DORA")
    ):
        raise ValueError("Complete validated cycle required")
    time = utc(observed_at)
    policy = load_policy() if policy is None else validate_policy(policy)
    original = (
        state
        if state is not None
        else {
            "kind": "publication_retained_versions_v1",
            "cycles": [],
            "versions": [],
            "latest": {},
        }
    )
    if original.get("kind") != "publication_retained_versions_v1":
        raise ValueError("Unknown retention state")
    validate_state(original)
    reference = load_reference()
    prepared = [
        evaluate(source, source_id, record, policy=policy, reference=reference)
        for source_id, record in records
    ]
    keys = [r["SourceKey"] for r in prepared]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate source identities in a cycle")
    fingerprint = digest(
        {"records": records, "policy": policy, "observed_at": observed_at}
    )
    prior = [c for c in original["cycles"] if c["source"] == source]
    replay = [c for c in prior if c["generation"] == generation]
    if replay:
        if replay[0]["sha256"] != fingerprint:
            raise ValueError("Replayed generation has different content/time/policy")
        return copy.deepcopy(original)
    if prior and time < max(utc(c["observed_at"]) for c in prior):
        raise ValueError("Out-of-order cycle cannot replace latest data")
    result = copy.deepcopy(original)
    for record in prepared:
        record.update(
            Generation=generation,
            ObservedAtUTC=observed_at,
            RecordSHA256=digest(record["Record"]),
        )
        index = len(result["versions"])
        result["versions"].append(record)
        result["latest"][record["SourceKey"]] = index
    result["cycles"].append(
        {
            "source": source,
            "generation": generation,
            "observed_at": observed_at,
            "sha256": fingerprint,
            "keys": sorted(keys),
            "policy_version": policy["version"],
        }
    )
    return result
