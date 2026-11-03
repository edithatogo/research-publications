# Copyright (c) 2026 CareOps contributors.
# SPDX-License-Identifier: Apache-2.0
"""Install a frozen reviewed guard into this independent clone's real hooks."""

import fcntl
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

FILES = (
    "pre_push.py",
    "presidio_scan.py",
    "presidio-policy.json",
    "presidio-reviewed-findings.json",
    "document-approvals.json",
)


def atomic(path, data):
    fd, name = tempfile.mkstemp(prefix=".privacy-install-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, 0o700)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    root = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    ).resolve()
    common = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            text=True,
        ).strip()
    ).resolve()
    if (
        sys.version_info[:3] != (3, 15, 1)
        or Path(sys.prefix).resolve() != root / ".venv-privacy-hooks"
    ):
        raise ValueError("runtime")
    configured = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        capture_output=True,
        text=True,
        check=False,
    )
    if configured.returncode not in {0, 1} or configured.stdout.strip() not in {
        "",
        str(common / "hooks"),
    }:
        raise ValueError("existing_configuration_requires_qualified_chain")
    bundle, hooks = common / "privacy-hooks-v1", common / "hooks"
    if any(
        p.is_symlink()
        for p in [bundle, hooks, bundle / "installation.json", bundle / "install.lock"]
    ):
        raise ValueError("linked_owner")
    bundle.mkdir(mode=0o700, exist_ok=True)
    hooks.mkdir(exist_ok=True)
    with (bundle / "install.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipt_file = bundle / "installation.json"
        prior = json.loads(receipt_file.read_text()) if receipt_file.exists() else None
        before = {
            event: (hooks / event).read_bytes() if (hooks / event).exists() else None
            for event in ["pre-commit", "pre-push"]
        }
        if any((hooks / event).is_symlink() for event in before):
            raise ValueError("linked_hook")
        if prior:
            for event, data in before.items():
                if (
                    data is None
                    or hashlib.sha256(data).hexdigest()
                    != prior["installedHookHashes"][event]
                ):
                    raise ValueError("changed_owner")
        else:
            for event, data in before.items():
                if data is not None:
                    if not os.access(hooks / event, os.X_OK):
                        raise ValueError("non_executable_legacy")
                    saved = bundle / (event + ".legacy")
                    saved.write_bytes(data)
                    saved.chmod(0o700)
        payload = {
            name: (root / ".privacy-guard" / name).read_bytes() for name in FILES
        }
        if any((root / ".privacy-guard" / name).is_symlink() for name in FILES):
            raise ValueError("linked_source")
        identity = hashlib.sha256(
            b"".join(name.encode() + b"\0" + data for name, data in payload.items())
        ).hexdigest()
        snapshots = bundle / "snapshots"
        snapshots.mkdir(mode=0o700, exist_ok=True)
        target = snapshots / identity
        if target.is_symlink():
            raise ValueError("snapshot")
        target.mkdir(mode=0o700, exist_ok=True)
        for name, data in payload.items():
            path = target / name
            if path.is_symlink() or (path.exists() and path.read_bytes() != data):
                raise ValueError("snapshot")
            if not path.exists():
                path.write_bytes(data)
        header = "#!/bin/sh\nset -eu\ncheckout_root=$(git rev-parse --show-toplevel)\n"
        driver = '"$checkout_root/.venv-privacy-hooks/bin/python" -I ' + shlex.quote(
            str(target / "pre_push.py")
        )
        legacy_push = bundle / "pre-push.legacy"
        if legacy_push.exists():
            driver += " --legacy " + shlex.quote(str(legacy_push))
        push = (
            header
            + "if CAREOPS_NOTIFICATION_WRAPPED=1 "
            + driver
            + ' "$@" >/dev/null 2>&1; then\n echo "Repository privacy guards passed."\n exit 0\nfi\necho "Push blocked; diagnostic content withheld." >&2\nif [ -z "${CI:-}" ] && [ "$(uname -s)" = Darwin ]; then\n osascript -e \'display notification "Push blocked. Review the local privacy gate." with title "Repository privacy"\' >/dev/null 2>&1 || true\nfi\nexit 1\n'
        )
        legacy_commit = bundle / "pre-commit.legacy"
        commit = header
        if legacy_commit.exists():
            commit += (
                "if ! "
                + shlex.quote(str(legacy_commit))
                + ' "$@" >/dev/null 2>&1; then echo "Commit blocked by retained guard; diagnostics withheld." >&2; exit 1; fi\n'
            )
        commit += 'cd "$checkout_root"\nif [ "$(gitleaks version 2>/dev/null)" != "8.30.1" ]; then echo "Commit blocked: required secret scanner unavailable." >&2; exit 1; fi\nif ! git diff --cached --check >/dev/null 2>&1 || ! gitleaks git . --pre-commit --staged --gitleaks-ignore-path /dev/null --ignore-gitleaks-allow --redact --no-banner >/dev/null 2>&1; then echo "Commit blocked; diagnostics withheld." >&2; exit 1; fi\n'
        texts = {"pre-push": push.encode(), "pre-commit": commit.encode()}
        replaced = []
        try:
            for event, data in texts.items():
                path = hooks / event
                current = path.read_bytes() if path.exists() else None
                if path.is_symlink() or current != before[event]:
                    raise ValueError("concurrent_change")
                atomic(path, data)
                replaced.append(event)
                if path.read_bytes() != data:
                    raise ValueError("readback")
        except Exception:
            for event in reversed(replaced):
                path = hooks / event
                if not path.is_symlink() and path.read_bytes() == texts[event]:
                    if before[event] is None:
                        path.unlink()
                    else:
                        atomic(path, before[event])
            raise
        receipt = {
            "sourceFingerprint": identity,
            "snapshot": str(target),
            "installedHookHashes": {
                k: hashlib.sha256(v).hexdigest() for k, v in texts.items()
            },
            "previousHookPresence": {
                k: (bundle / (k + ".legacy")).exists() for k in before
            },
            "root": str(root),
            "originalConfigurationPreserved": True,
        }
        atomic(receipt_file, (json.dumps(receipt, indent=2) + "\n").encode())
    print(
        "Installed hooks read back; existing chain retained; missing scanner blocks pushes."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 -- fail closed without exposing paths or source
        print(
            "Hook installation refused; diagnostic content withheld.", file=sys.stderr
        )
        raise SystemExit(1)
