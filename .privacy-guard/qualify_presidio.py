# Copyright (c) 2026 CareOps contributors.
# SPDX-License-Identifier: Apache-2.0
"""Real, offline model qualification with synthetic values and redacted output."""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    policy = json.loads((HERE / "presidio-policy.json").read_text())
    # Construct fictional values; no real person's details or genuine identifier is used.
    person = "".join(map(chr, [74, 97, 110, 101, 32, 68, 111, 101]))
    mail = "synthetic" + chr(64) + "example.com"
    items = [
        {"identity": "a" * 64, "text": "Patient " + person + "; email " + mail},
        {"identity": "b" * 64, "text": "repeatable source validation"},
    ]
    result = subprocess.run(
        [sys.executable, "-I", str(HERE / "presidio_scan.py")],
        input=json.dumps(
            {"policy": policy, "items": items, "expected_prefix": sys.prefix}
        ).encode(),
        capture_output=True,
        check=False,
        timeout=90,
    )
    try:
        data = json.loads(result.stdout)
        detected = {entity for row in data["findings"] for entity in row["entities"]}
        if (
            result.returncode
            or data["checked"] != 2
            or not {"PERSON", "EMAIL_ADDRESS"}.issubset(detected)
        ):
            raise ValueError
        for bad_policy in [
            {**policy, "model": "missing_model"},
            {**policy, "modelFingerprint": "0" * 64},
        ]:
            failed = subprocess.run(
                [sys.executable, "-I", str(HERE / "presidio_scan.py")],
                input=json.dumps(
                    {
                        "policy": bad_policy,
                        "items": items,
                        "expected_prefix": sys.prefix,
                    }
                ).encode(),
                capture_output=True,
                check=False,
                timeout=90,
            )
            if (
                failed.returncode == 0
                or person.encode() in failed.stdout + failed.stderr
            ):
                raise ValueError
        spec = importlib.util.spec_from_file_location(
            "qualified_scan", HERE / "presidio_scan.py"
        )
        scan = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scan)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scan.git(root, "init", "-q")
            scan.git(root, "config", "user.name", "synthetic")
            scan.git(root, "config", "user.email", "synthetic@example.invalid")

            def commit(text):
                (root / "sample.txt").write_text(text)
                scan.git(root, "add", "sample.txt")
                scan.git(root, "commit", "-qm", "source fixture")
                return scan.git(root, "rev-parse", "HEAD").decode().strip()

            base = commit("ordinary source")
            commit("Patient " + person)
            tip = commit("ordinary source")
            selected = scan.selected_text(root, tip, [base], policy)
            target = next(
                item["identity"]
                for item in selected
                if item["text"] == "Patient " + person
            )
            intermediate = subprocess.run(
                [sys.executable, "-I", str(HERE / "presidio_scan.py")],
                input=json.dumps(
                    {"policy": policy, "items": selected, "expected_prefix": sys.prefix}
                ).encode(),
                capture_output=True,
                check=False,
                timeout=90,
            )
            observed = json.loads(intermediate.stdout)
            if intermediate.returncode or not any(
                row["identity"] == target and "PERSON" in row["entities"]
                for row in observed["findings"]
            ):
                raise ValueError
        print(
            "Qualified Python, dependency metadata, normal model fingerprint and offline synthetic detection."
        )
        return 0
    except Exception:  # noqa: BLE001 -- withhold synthetic/third-party errors as for real input
        print("Presidio qualification failed; diagnostics withheld.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
