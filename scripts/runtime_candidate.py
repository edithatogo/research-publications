"""Select a runnable Python 3.15 candidate and retain honest canary outcomes.

No downloads, environment changes or promotion. SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def version_key(value):
    match = re.fullmatch(r"3\.15\.(0|[1-9][0-9]*)(?:(a|b|rc)([0-9]+))?", value)
    if not match:
        raise ValueError("Exact Python 3.15 release required")
    patch, stage, number = match.groups()
    return int(patch), {"a": 0, "b": 1, "rc": 2, None: 3}[stage], int(number or 0)


def select_python_preview(releases, *, baseline, platform_version):
    """Choose the newest newer release with a matching Linux x64 runner build."""
    baseline_key = version_key(baseline)
    candidates = []
    for release in releases:
        if not isinstance(release, dict) or not isinstance(release.get("version"), str):
            raise ValueError("Malformed runtime manifest release")
        version = release["version"]
        if not re.fullmatch(r"3\.15\.[0-9]+(?:(?:a|b|rc)[0-9]+)?", version):
            continue
        key = version_key(version)
        if key <= baseline_key:
            continue
        files = release.get("files")
        if not isinstance(files, list) or any(not isinstance(row, dict) for row in files):
            raise ValueError("Malformed runtime manifest files")
        if any(row.get("platform") == "linux" and row.get("arch") == "x64"
               and row.get("platform_version") == platform_version for row in files):
            candidates.append((key, version))
    selected = max(candidates)[1] if candidates else None
    return {"baseline": baseline, "candidate": selected, "platformVersion": platform_version,
            "state": "candidate-discovered" if selected else "candidate-unavailable",
            "runtimeTestsExecuted": False, "promoted": False, "nativeWrites": False}


def finalize(receipt, *, discovery_outcome, outcome):
    """A candidate is qualified only when discovery and actual tests succeeded."""
    result = dict(receipt)
    result.update(discoveryOutcome=discovery_outcome, runtimeTestOutcome=outcome,
                  runtimeTestsExecuted=outcome in {"success", "failure"},
                  promoted=False, nativeWrites=False)
    if discovery_outcome != "success":
        result["state"] = "discovery-failed"
    elif not result.get("candidate"):
        result["state"] = "candidate-unavailable"
    elif outcome == "success":
        version_key(result["candidate"])
        result["state"] = "qualified-runtime-candidate"
    elif outcome == "failure":
        result["state"] = "runtime-tests-failed"
    else:
        result["state"] = "runtime-tests-not-executed"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["runtime-finalize"])
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--discovery-outcome", required=True)
    parser.add_argument("--outcome", required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text()) if args.receipt.exists() else {}
    result = finalize(receipt, discovery_outcome=args.discovery_outcome, outcome=args.outcome)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
