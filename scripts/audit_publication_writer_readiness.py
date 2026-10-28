"""Audit retained CLI query responses without running or authorising a writer.

Storage readiness, materialised projection audits and observed history dates are
separate signals. None proves provider freshness or whole-cycle acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]


def rows(document):
    if not isinstance(document, dict) or "error" in document or document.get("errors"):
        raise ValueError("Query error or malformed response")
    results = document.get("results")
    if not isinstance(results, list) or len(results) != 1:
        raise ValueError("Exactly one query result required")
    result = results[0]
    if not isinstance(result, dict) or "error" in result or result.get("errors"):
        raise ValueError("Query result contains an error")
    tables = result.get("tables")
    if not isinstance(tables, list) or len(tables) != 1:
        raise ValueError("Exactly one result table required")
    table = tables[0]
    if not isinstance(table, dict) or "error" in table or table.get("errors"):
        raise ValueError("Query table contains an error")
    output = table.get("rows")
    if (
        not isinstance(output, list)
        or not output
        or any(not isinstance(x, dict) for x in output)
    ):
        raise ValueError("Nonempty structured query rows required")
    return output


def one(document):
    output = rows(document)
    if len(output) != 1:
        raise ValueError("Exactly one aggregate readiness row required")
    return output[0]


def integer(row, name):
    value = row.get(name)
    if type(value) is not int or value < 0:
        raise ValueError("Nonnegative integer required: " + name)
    return value


def utc(value, *, native=False):
    if not isinstance(value, str) or not value:
        raise ValueError("Recorded UTC timestamp required")
    parsed = datetime.fromisoformat(value)
    # RetainedHistoryKeys native M explicitly removes the zone after SwitchZone(0).
    if native and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("Timestamp must explicitly represent UTC")
    return parsed


def assess(flow, storage_response, projection_response, generation_response, *, as_of):
    now = utc(as_of)
    properties = flow.get("properties", {})
    if properties.get("state") not in ("Started", "Stopped"):
        raise ValueError("Known native flow state required")
    actions = properties.get("definition", {}).get("actions", {})
    bindings = []
    for name in (
        "Run_a_query_against_a_dataset",
        "Run_publication_rows_query",
        "Run_OpenAlex_Context_Query",
    ):
        params = actions.get(name, {}).get("inputs", {}).get("parameters", {})
        try:
            binding = (str(UUID(params["groupid"])), str(UUID(params["datasetid"])))
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise ValueError("Exact query binding required: " + name) from exc
        bindings.append(binding)
    if len(set(bindings)) != 1:
        raise ValueError("Writer query binding mismatch")
    storage = one(storage_response)
    publications = integer(storage, "[PublicationRows]")
    pubmed, dora, history = (
        integer(storage, name)
        for name in ("[RetainedPubMed]", "[RetainedDORA]", "[HistoryRows]")
    )
    storage_ready = (
        storage.get("[SourceReadiness]") == "READY_FOR_STORAGE_VALIDATION"
        and publications > 0
        and pubmed > 0
        and dora > 0
        and history == pubmed + dora
    )
    projection = one(projection_response)
    values = {
        name: integer(projection, "[" + name + "]")
        for name in (
            "FreshAuditRows",
            "FreshAuditFailed",
            "SourceSnapshotRows",
            "FreshPublicationRows",
            "DoraAuditRows",
            "DoraAuditFailed",
        )
    }
    projection_ready = (
        values["FreshAuditRows"] == 9
        and values["FreshAuditFailed"] == 0
        and values["DoraAuditRows"] == 10
        and values["DoraAuditFailed"] == 0
        and values["SourceSnapshotRows"] > 0
        and values["FreshPublicationRows"] > 0
    )
    generations = {"PubMed": [], "DORA": []}
    seen = set()
    for row in rows(generation_response):
        source = row.get("RetainedHistoryKeys[Source]")
        batch = row.get("RetainedHistoryKeys[LastBatchID]")
        if (
            not isinstance(source, str)
            or source not in generations
            or not isinstance(batch, str)
            or not batch.strip()
        ):
            raise ValueError("Scoped source and batch identity required")
        if (source, batch) in seen:
            raise ValueError("Duplicate source-generation aggregate")
        seen.add((source, batch))
        count = integer(row, "[Records]")
        earliest = utc(row.get("[LastObservedMinUTC]"), native=True)
        latest = utc(row.get("[LastObservedMaxUTC]"), native=True)
        if not count or earliest > latest or latest > now:
            raise ValueError("Invalid source-generation count/date evidence")
        generations[source].append((count, earliest, latest))
    if any(not generations[x] for x in generations):
        raise ValueError("Both retained source generations required")
    counts = {
        source: sum(x[0] for x in values) for source, values in generations.items()
    }
    if counts != {"PubMed": pubmed, "DORA": dora}:
        raise ValueError("Retained generation counts differ from readiness query")
    summary = {
        source: {
            "records": counts[source],
            "generation_groups": len(values),
            "last_observed_min_utc": min(x[1] for x in values).isoformat(),
            "last_observed_max_utc": max(x[2] for x in values).isoformat(),
        }
        for source, values in generations.items()
    }
    return {
        "format": "rims-publication-writer-readiness-audit-v1",
        "as_of_utc": now.isoformat(),
        "query_bindings_match": True,
        "storage_validation_ready": storage_ready,
        "routine_projection_ready": projection_ready,
        "publication_rows": publications,
        "retained_history_rows": history,
        "projection_audits": values,
        "retained_observations": summary,
        "flow_state": properties["state"],
        "failure_alerts_enabled": properties.get("flowFailureAlertSubscribed"),
        "source_generation_freshness_accepted": False,
        "whole_cycle_accepted": False,
        "diagnostic_run_permitted": False,
        "limits": "Recorded-response audit only; compare latest accepted archive generation and establish exact lineage before routine writes. No run/refresh/activation authority is created.",
    }


def private_path(path):
    resolved = path.resolve()
    if not resolved.is_relative_to((ROOT / "private/ops").resolve()):
        raise ValueError("Native snapshots and outputs must remain under private/ops")
    return resolved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("flow", "storage", "projection", "generations", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--as-of", required=True, help="Explicit UTC observation time")
    args = parser.parse_args(argv)
    paths = {
        name: private_path(getattr(args, name))
        for name in ("flow", "storage", "projection", "generations", "out")
    }
    if len(set(paths.values())) != 5 or paths["out"].exists():
        raise ValueError("Distinct inputs and a new output path required")
    raw = {name: paths[name].read_bytes() for name in paths if name != "out"}
    report = assess(
        *(
            json.loads(raw[name])
            for name in ("flow", "storage", "projection", "generations")
        ),
        as_of=args.as_of,
    )
    report["acquisition_model_lineage_accepted"] = False
    report["input_sha256"] = {
        name: hashlib.sha256(value).hexdigest() for name, value in raw.items()
    }
    paths["out"].parent.mkdir(parents=True, exist_ok=True)
    with paths["out"].open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                name: report[name]
                for name in (
                    "storage_validation_ready",
                    "routine_projection_ready",
                    "source_generation_freshness_accepted",
                    "diagnostic_run_permitted",
                )
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
