# Copyright (c) 2026 Repository contributors.
# SPDX-License-Identifier: Apache-2.0
"""Pre-transfer private-destination and Presidio gate; diagnostics contain no raw data."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "careops_presidio_scan", HERE / "presidio_scan.py"
)
SCAN = importlib.util.module_from_spec(SPEC)
try:
    SPEC.loader.exec_module(SCAN)
except Exception:  # noqa: BLE001 -- unavailable helper must not disclose a traceback
    print("Repository push blocked: trusted scanner unavailable.", file=sys.stderr)
    raise SystemExit(1)
OID, Refusal, git, selected_text = SCAN.OID, SCAN.Refusal, SCAN.git, SCAN.selected_text
ZERO = "0" * 40


def run(command: list[str], *, data: bytes | None = None, timeout: int = 60) -> bytes:
    result = subprocess.run(
        command, input=data, capture_output=True, check=False, timeout=timeout
    )
    if result.returncode:
        raise Refusal("required_command_failed")
    return result.stdout


def destination(url: str, policy: dict, command=run, *, advertise=True) -> list[str]:
    """Only the approved repository; no credentials, query, fragments or alternate host."""
    repo = policy["repository"]
    permitted = {
        f"https://github.com/{repo}",
        f"https://github.com/{repo}.git",
        f"git@github.com:{repo}",
        f"git@github.com:{repo}.git",
    }
    if (
        policy["host"] != "github.com"
        or policy["requiredVisibility"] not in {"PRIVATE", "PUBLIC"}
        or url not in permitted
    ):
        raise Refusal("destination_not_approved")
    state = json.loads(
        command(["gh", "api", "--hostname", "github.com", "repos/" + repo])
    )
    if (
        state.get("full_name", "").lower() != repo.lower()
        or state.get("private") is not (policy["requiredVisibility"] == "PRIVATE")
        or state.get("visibility") != policy["requiredVisibility"].lower()
    ):
        raise Refusal("private_visibility_not_verified")
    if not advertise:
        return []  # CI uses its explicit fetched range, without Git transport credentials.
    refs = command(["git", "ls-remote", "--heads", url])
    if len(refs) > 2 * 1024 * 1024:
        raise Refusal("remote_scope_limit")
    tips = []
    for line in refs.decode().splitlines():
        parts = line.split()
        if (
            len(parts) != 2
            or not OID.fullmatch(parts[0])
            or not parts[1].startswith("refs/heads/")
        ):
            raise Refusal("invalid_remote_metadata")
        tips.append(parts[0])
    return sorted(set(tips))


def push_rows(payload: bytes) -> list[tuple[str, str]]:
    if len(payload) > 1024 * 1024:
        raise Refusal("push_scope_limit")
    rows = []
    for line in payload.decode().splitlines():
        fields = line.split()
        if len(fields) != 4 or any(
            not OID.fullmatch(v) for v in [fields[1], fields[3]]
        ):
            raise Refusal("invalid_push_metadata")
        if not fields[2].startswith("refs/heads/"):
            raise Refusal("non_branch_push_requires_review")
        if fields[1] != ZERO:
            rows.append((fields[1], fields[3]))
    return rows


def review_control_number(item: dict, finding: dict, policy: dict) -> bool:
    """Only typed offset/rank tokens in the exact review control path, never free text."""
    if policy["entities"][finding["entity_index"]] != "PHONE_NUMBER":
        return False
    raw = item["text"].encode()
    oid = hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False
    ).hexdigest()
    expected = hashlib.sha256(
        (".privacy-guard/presidio-reviewed-findings.json:" + oid).encode()
    ).hexdigest()
    if item["identity"] != expected:
        return False

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_metadata")
            result[key] = value
        return result

    try:
        value = json.loads(item["text"], object_pairs_hook=unique)
        if (
            set(value) != {"schemaVersion", "policy_sha256", "findings"}
            or type(value["schemaVersion"]) is not int
            or value["schemaVersion"] != 1
        ):
            return False
        if (
            value["policy_sha256"]
            != hashlib.sha256((HERE / "presidio-policy.json").read_bytes()).hexdigest()
        ):
            return False
        fields = {
            "identity",
            "blob_sha256",
            "entity_index",
            "start",
            "end",
            "value_sha256",
            "reason",
            "reviewer",
        }
        if not isinstance(value["findings"], list):
            return False
        for row in value["findings"]:
            if set(row) != fields:
                return False
            if any(
                not isinstance(row[k], str) or not re.fullmatch("[a-f0-9]{64}", row[k])
                for k in ["identity", "blob_sha256", "value_sha256"]
            ):
                return False
            if any(type(row[k]) is not int for k in ["start", "end", "entity_index"]):
                return False
            if not 0 <= row["start"] <= row["end"] <= policy["maxBlobBytes"]:
                return False
            if not 0 <= row["entity_index"] < len(policy["entities"]):
                return False
            if any(
                not isinstance(row[k], str) or not row[k]
                for k in ["reason", "reviewer"]
            ):
                return False
        for token in re.finditer(
            r'(?<!\\)"(?:start|end|entity_index)"\s*:\s*(0|[1-9][0-9]*)', item["text"]
        ):
            if token.start(1) == finding["start"] and token.end(1) == finding["end"]:
                return True
    except (ValueError, TypeError, KeyError):
        return False
    return False


def scanner(root: Path, items: list[dict], policy: dict, command=run) -> None:
    python = root / ".venv-privacy-presidio/bin/python"
    if not python.is_file() or python.parent.parent.is_symlink():
        raise Refusal("presidio_runtime_missing")
    reviews = json.loads((HERE / "presidio-reviewed-findings.json").read_text())
    policy_hash = hashlib.sha256(
        (HERE / "presidio-policy.json").read_bytes()
    ).hexdigest()
    if (
        reviews.get("schemaVersion") != 1
        or reviews.get("policy_sha256") != policy_hash
        or not isinstance(reviews.get("findings"), list)
    ):
        raise Refusal("text_review_policy_changed")
    payload = json.dumps(
        {
            "policy": policy,
            "items": items,
            "reviews": reviews,
            "expected_prefix": str(python.parent.parent),
        }
    ).encode()
    result = json.loads(
        command(
            [str(python), "-I", str(HERE / "presidio_scan.py")],
            data=payload,
            timeout=300,
        )
    )
    if (
        result.get("protocol") != 1
        or result.get("error")
        or result.get("checked") != len(items)
        or not isinstance(result.get("findings"), list)
    ):
        raise Refusal("presidio_scan_not_verified")
    selected = {item["identity"]: item for item in items}
    for group in result["findings"]:
        if not isinstance(group.get("details"), list) or not group["details"]:
            raise Refusal("invalid_scanner_findings")
        item = selected[group["identity"]]
        if any(
            not review_control_number(item, finding, policy)
            for finding in group["details"]
        ):
            raise Refusal("presidio_personal_details_detected")


def documents(root: Path, tip: str, bases: list[str], policy: dict) -> None:
    """New documents/binary bytes require an exact independent content approval."""
    approvals = json.loads((HERE / "document-approvals.json").read_text())
    if approvals.get("schemaVersion") != 1 or not isinstance(
        approvals.get("approvals"), list
    ):
        raise Refusal("document_policy")
    commits = (
        git(root, "rev-list", tip, *(["--not", *bases] if bases else []))
        .decode()
        .splitlines()
    )
    if len(commits) > policy["maxCommits"]:
        raise Refusal("document_scope")
    seen = set()
    total = 0
    suffixes = {
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".zip",
        ".gz",
        ".tar",
        ".7z",
        ".pbix",
        ".pbit",
        ".ipynb",
    }
    for commit in commits:
        paths = git(
            root,
            "diff-tree",
            "--root",
            "--no-commit-id",
            "-r",
            "-m",
            "--no-renames",
            "--diff-filter=ACMT",
            "--name-only",
            "-z",
            commit,
        )
        for raw in paths.split(b"\0"):
            if not raw:
                continue
            name = raw.decode("utf-8")
            mode, kind, oid = (
                git(root, "ls-tree", "-z", commit, "--", name)
                .split(b"\t", 1)[0]
                .decode()
                .split()
            )
            if mode == "160000":
                continue
            if kind != "blob" or mode not in {"100644", "100755"}:
                raise Refusal("document_mode")
            if (name, oid) in seen:
                continue
            seen.add((name, oid))
            if (
                len(seen) > policy["maxBlobs"]
                or int(git(root, "cat-file", "-s", oid)) > policy["maxBlobBytes"]
            ):
                raise Refusal("document_scope")
            data = git(root, "cat-file", "blob", oid)
            total += len(data)
            if total > policy["maxTotalBytes"]:
                raise Refusal("document_scope")
            binary = b"\0" in data
            try:
                data.decode("utf-8")
            except UnicodeDecodeError:
                binary = True
            if binary or Path(name).suffix.lower() in suffixes:
                digest = hashlib.sha256(data).hexdigest()
                if not any(
                    a.get("path") == name
                    and a.get("sha256") == digest
                    and a.get("reason")
                    and a.get("reviewer")
                    for a in approvals["approvals"]
                ):
                    raise Refusal("unapproved_document")


def secrets(root: Path, tip: str, bases: list[str]) -> None:
    selection = " ".join([tip, "--not", *bases]) if bases else tip
    run(
        [
            "gitleaks",
            "git",
            str(root),
            "--log-opts=" + selection,
            "--gitleaks-ignore-path",
            "/dev/null",
            "--ignore-gitleaks-allow",
            "--redact",
            "--no-banner",
        ],
        timeout=300,
    )


def notify() -> None:
    """Generic local owner notification only. Its success never controls permission to push."""
    if (
        sys.platform == "darwin"
        and not os.environ.get("CI")
        and not os.environ.get("CAREOPS_NOTIFICATION_WRAPPED")
    ):
        try:
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'display notification "Push blocked. Review the local privacy gate." with title "Repository privacy"',
                ],
                capture_output=True,
                check=False,
                timeout=3,
            )
        except (OSError, subprocess.SubprocessError):
            print(
                "Local notification unavailable; push remains blocked.", file=sys.stderr
            )


def main() -> int:
    class SilentParser(argparse.ArgumentParser):
        def error(self, _message):
            raise Refusal("invalid_gate_arguments")

    parser = SilentParser(description=__doc__)
    parser.add_argument("remote", nargs="?")
    parser.add_argument("url", nargs="?")
    parser.add_argument(
        "--legacy", help="Installed managed dispatcher retained verbatim"
    )
    parser.add_argument("--ci-base")
    parser.add_argument("--ci-tip")
    args = parser.parse_args()
    try:
        policy = json.loads((HERE / "presidio-policy.json").read_text())
        root = Path(
            run(["git", "rev-parse", "--show-toplevel"]).decode().strip()
        ).resolve()
        if git(root, "rev-parse", "--is-shallow-repository").strip() != b"false":
            raise Refusal("complete_history_required")
        # Network metadata preflight precedes analysis. No source text leaves this process tree.
        if args.ci_tip:
            if os.environ.get("GITHUB_REPOSITORY") != policy["repository"]:
                raise Refusal("ci_repository_not_approved")
            destination(
                "https://github.com/" + policy["repository"] + ".git",
                policy,
                advertise=False,
            )
            if (
                not args.ci_base
                or not OID.fullmatch(args.ci_base)
                or not OID.fullmatch(args.ci_tip)
            ):
                raise Refusal("explicit_ci_range_required")
            rows, known, payload = [(args.ci_tip, args.ci_base)], [args.ci_base], b""
        else:
            if not args.remote or not args.url:
                raise Refusal("explicit_destination_required")
            # URL rewriting can route a seemingly approved URL to another server.
            rewrite = subprocess.run(
                [
                    "git",
                    "config",
                    "--get-regexp",
                    r"^url\..*\.(insteadof|pushinsteadof)$",
                ],
                capture_output=True,
                check=False,
            )
            if rewrite.returncode != 1:
                raise Refusal("unreviewed_transport_rewrite")
            known = destination(args.url, policy)
            payload = sys.stdin.buffer.read(1024 * 1024 + 1)
            rows = push_rows(payload)
        bases = []
        for oid in known:
            try:
                if git(root, "cat-file", "-t", oid).strip() == b"commit":
                    bases.append(oid)
            except Refusal:
                pass  # Never exclude an unknown object; conservative full scan instead.
        items, identities, total = [], set(), 0
        for tip, _old in rows:
            for item in selected_text(root, tip, bases, policy):
                if item["identity"] in identities:
                    continue
                identities.add(item["identity"])
                total += len(item["text"].encode())
                if total > policy["maxTotalBytes"] or len(items) >= policy["maxBlobs"]:
                    raise Refusal("combined_text_scope_limit")
                items.append(item)
        if run(["gitleaks", "version"]).strip() != b"8.30.1":
            raise Refusal("secret_scanner_version")
        # Even a clean/deletion-only push must prove scanner and model availability.
        scanner(root, items, policy)
        for tip, _old in rows:
            documents(root, tip, bases, policy)
            secrets(root, tip, bases)
        if args.legacy:
            run([args.legacy, args.remote, args.url], data=payload, timeout=600)
        print("Repository approved destination and offline Presidio gate passed.")
        return 0
    except Exception:  # noqa: BLE001 -- privacy boundary; arbitrary raw errors must not escape
        # No exception, filename, URL, subprocess stderr, match or snippet is echoed.
        print(
            "Repository push blocked: approved destination or complete privacy scan not verified.",
            file=sys.stderr,
        )
        notify()
        return 1


if __name__ == "__main__":
    try:
        code = main()
    except Exception:  # noqa: BLE001 -- startup failure is a refusal, never a bypass
        print("Repository push blocked: privacy gate could not start.", file=sys.stderr)
        notify()
        code = 1
    raise SystemExit(code)
