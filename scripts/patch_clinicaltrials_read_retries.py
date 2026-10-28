"""Prepare a fingerprint-bound retry patch for the existing ClinicalTrials flow.

No service effects. The caller must separately prove exact native identity,
current definition, ownership, bindings and runtime adoption before deployment.
Retries continue the same GET; they do not resume a failed run or commit partial
pages. Native HTTP retries cover transient failures, not permission repair.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

POLICY = {
    "type": "exponential",
    "count": 3,
    "interval": "PT10S",
    "minimumInterval": "PT10S",
    "maximumInterval": "PT1M",
}
PATHS = (
    ("Two_discovery_reads", "Discovery_pages", "Get_discovery_page"),
    ("For_each_trial", "Get_trial"),
)
DISCOVERY = "@concat('https://clinicaltrials.gov/api/v2/studies?format=json&countTotal=true&pageSize=100&query.term=',uriComponent(outputs('Acquisition_scope')?['query_term']),if(empty(variables('DiscoveryToken')),'',concat('&pageToken=',uriComponent(variables('DiscoveryToken')))))"
DETAIL = "@concat('https://clinicaltrials.gov/api/v2/studies/',items('For_each_trial'))"


def _expression(value, expected, path):
    if not isinstance(value, str) or value != expected:
        raise ValueError("Exact provider expression allowlist required")
    prefix = re.match(r"@concat\('([^']*)',", value)
    parsed = urlsplit(prefix[1]) if prefix else None
    if (
        not parsed
        or parsed.scheme != "https"
        or parsed.netloc != "clinicaltrials.gov"
        or parsed.path != path
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ValueError("Exact parsed provider URI required")


def definition_sha256(definition):
    return hashlib.sha256(
        json.dumps(
            definition,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def prepare(document, *, expected_definition_sha256, selected_paths=None):
    """Change exactly two qualified read retry policies, preserving all else."""
    if not isinstance(expected_definition_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", expected_definition_sha256
    ):
        raise ValueError("Explicit expected native-definition SHA256 required")
    candidate = copy.deepcopy(document)
    try:
        properties = candidate["properties"]
        definition = properties["definition"]
        if definition_sha256(definition) != expected_definition_sha256:
            raise ValueError("Definition drift: reconcile before preparing an update")
        if properties.get("state") not in {"Started", "Stopped"}:
            raise ValueError("Explicit existing flow state required")
        manifest = definition["actions"]["Manifest"]["inputs"]
        if (
            manifest.get("format") != "rims-ctgov-discovery-commit-v1"
            or manifest.get("source") != "clinicaltrials.gov"
            or manifest.get("discovery_complete_reads") != 2
        ):
            raise ValueError(
                "Qualified complete ClinicalTrials discovery collector required"
            )
        if (
            not isinstance(selected_paths, (tuple, list))
            or not selected_paths
            or any(
                not isinstance(path, tuple) or path not in PATHS
                for path in selected_paths
            )
            or len(set(selected_paths)) != len(selected_paths)
        ):
            raise ValueError("Explicit exact read-only action paths required")
        changed = []
        for path in selected_paths:
            actions = definition["actions"]
            for container in path[:-1]:
                actions = actions[container]["actions"]
            action = actions[path[-1]]
            inputs = action["inputs"]
            uri = inputs.get("uri", "")
            if (
                action.get("type") != "Http"
                or inputs.get("method") != "GET"
                or not isinstance(uri, str)
            ):
                raise ValueError(
                    "Only the existing HTTP GET actions may receive retries"
                )
            if set(inputs) != {"uri", "method", "headers", "retryPolicy"} or inputs.get(
                "headers"
            ) != {"Accept": "application/json"}:
                raise ValueError(
                    "Exact anonymous read input shape required; no body or auth added"
                )
            if path[-1] == "Get_discovery_page":
                expected_uri = "@outputs('Discovery_uri')"
                discovery = actions["Discovery_uri"]["inputs"]
                if (
                    uri != expected_uri
                    or actions["Discovery_uri"].get("type") != "Compose"
                ):
                    raise ValueError("Discovery read source changed")
                _expression(discovery, DISCOVERY, "/api/v2/studies")
            else:
                _expression(uri, DETAIL, "/api/v2/studies/")
            if inputs.get("retryPolicy") not in ({"type": "none"}, POLICY):
                raise ValueError("Existing custom retry policy requires reconciliation")
            if inputs.get("retryPolicy") != POLICY:
                changed.append(".".join(path))
                inputs["retryPolicy"] = copy.deepcopy(POLICY)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError(
            "Incomplete or unexpected native collector definition"
        ) from error
    return candidate, {
        "status": "PREPARED_LOCAL_ONLY" if changed else "UNCHANGED_LOCAL_ONLY",
        "definition_before_sha256": expected_definition_sha256,
        "definition_after_sha256": definition_sha256(definition),
        "changed_action_paths": changed,
        "native_saved": False,
        "native_retry_execution_proved": False,
        "cross_run_resume_proved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--expected-definition-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--action", choices=["discovery", "detail"], action="append", required=True
    )
    args = parser.parse_args()
    candidate, receipt = prepare(
        json.loads(args.source.read_text()),
        expected_definition_sha256=args.expected_definition_sha256,
        selected_paths=tuple(
            PATHS[0 if name == "discovery" else 1] for name in args.action
        ),
    )
    with args.output.open("x") as stream:
        json.dump({"candidate": candidate, "receipt": receipt}, stream, indent=2)
        stream.write("\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
