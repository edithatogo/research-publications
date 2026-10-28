"""Private create-only capture evidence; local completion is never native admission."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.patch_clinicaltrials_read_retries import strict_json
except ImportError:
    from patch_clinicaltrials_read_retries import strict_json

PRIVATE_ROOT = Path(__file__).resolve().parents[1] / "private/ops"


def json_bytes(value):
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def scope_sha256(scope):
    return hashlib.sha256(
        json.dumps(
            scope,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def private_directory(path):
    path = Path(path)
    root = PRIVATE_ROOT.resolve()
    if path.resolve() == root or not path.resolve().is_relative_to(root):
        raise ValueError("Capture directories must remain below repository private/ops")
    current = path.absolute()
    while current != PRIVATE_ROOT.absolute() and current != current.parent:
        if current.is_symlink():
            raise ValueError("Symlink capture paths are refused")
        current = current.parent
    return path


def create_output(path):
    path = private_directory(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir(mode=0o700, exist_ok=False)
    return path


def _name(name):
    if not isinstance(name, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]+\.(?:json|bin)", name
    ):
        raise ValueError("Safe create-only evidence filename required")
    return name


def write_verified(output, name, raw):
    output = private_directory(output)
    path = output / _name(name)
    if not isinstance(raw, bytes):
        raise ValueError("Serialized evidence bytes required")  # noqa: TRY004 - malformed evidence uses ValueError
    with os.fdopen(
        os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb"
    ) as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    if path.read_bytes() != raw:
        raise OSError("Stored evidence readback mismatch")
    descriptor = os.open(output, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return {"name": name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def commit_generation(output, projection_name, rows, manifest):
    """Serialize both artifacts before either is opened; manifest is committed last."""
    projection = json_bytes(rows)
    result = {
        **manifest,
        "complete": True,
        "accepted": False,
        "projection_sha256": hashlib.sha256(projection).hexdigest(),
    }
    encoded_manifest = json_bytes(result)
    names = set()
    for entry in manifest.get("files", []):
        name = _name(entry.get("name"))
        file = Path(output) / name
        if name in names or file.is_symlink() or not file.is_file():
            raise ValueError("Incomplete or unsafe raw inventory before commit")
        raw = file.read_bytes()
        if (
            type(entry.get("bytes")) is not int
            or len(raw) != entry["bytes"]
            or hashlib.sha256(raw).hexdigest() != entry.get("sha256")
        ):
            raise ValueError("Raw evidence changed before commit")
        names.add(name)
    if {p.name for p in Path(output).iterdir()} != names:
        raise ValueError("Uninventoried capture files before commit")
    for name in (projection_name, "manifest.json", "failed-generation.json"):
        if (Path(output) / name).exists():
            raise FileExistsError("Generation already has final evidence")
    write_verified(output, projection_name, projection)
    write_verified(output, "manifest.json", encoded_manifest)
    return result


def write_failure_receipt(
    output,
    *,
    source,
    scope,
    files,
    completed_ids,
    failed_id,
    error,
    resumed_from=None,
    generation_id=None,
    request_attempts=None,
):
    """Create and verify a durable refusal; any failure marker invalidates completion."""
    output = private_directory(output)
    observed = []
    for path in sorted(output.iterdir()):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Unsafe file in failed generation")
        _name(path.name)
        raw = path.read_bytes()
        observed.append(
            {
                "name": path.name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            }
        )
    requested = scope.get("requested_ids", scope.get("requested_publication_dois"))
    receipt = {
        "format": "rims-source-capture-failure-v1",
        "source": source,
        "generation_id": generation_id or uuid.uuid4().hex,
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "scope_sha256": scope_sha256(scope),
        "complete": False,
        "accepted": False,
        "scope": scope,
        "completed_ids": completed_ids,
        "failed_id": failed_id,
        "files": files,
        "observed_files": observed,
        "requested_count": len(requested) if isinstance(requested, list) else None,
        "completed_count": len(completed_ids),
        "raw_file_count": len(files),
        "error": {"type": type(error).__name__, "message": str(error)[:1000]},
    }
    if resumed_from is not None:
        receipt["resumed_from"] = resumed_from
    if request_attempts is not None:
        receipt["request_attempts"] = request_attempts
    write_verified(output, "failed-generation.json", json_bytes(receipt))
    return receipt


def verified_failure(folder, source, scope, ids):
    """Validate a frozen exact-scope prefix before creating a new generation."""
    folder = private_directory(folder)
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("Existing private failed directory required")
    path = folder / "failed-generation.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("Failed-generation receipt required")
    raw = path.read_bytes()
    receipt = strict_json(raw)
    if not isinstance(receipt, dict) or (
        receipt.get("format"),
        receipt.get("source"),
        receipt.get("complete"),
        receipt.get("accepted"),
    ) != ("rims-source-capture-failure-v1", source, False, False):
        raise ValueError("Failure receipt scope or status mismatch")
    if (
        receipt.get("complete") is not False
        or receipt.get("accepted") is not False
        or receipt.get("scope") != scope
        or receipt.get("scope_sha256") != scope_sha256(scope)
    ):
        raise ValueError("Failure receipt scope or status mismatch")
    completed = receipt.get("completed_ids")
    if (
        not isinstance(completed, list)
        or completed != ids[: len(completed)]
        or len(completed) > len(ids)
    ):
        raise ValueError("Consecutive completed prefix required")
    expected_failed = ids[len(completed)] if len(completed) < len(ids) else None
    if receipt.get("failed_id") != expected_failed:
        raise ValueError("Failure identifier must follow completed prefix")
    files = receipt.get("files")
    if not isinstance(files, list):
        raise ValueError("Raw file inventory required")  # noqa: TRY004 - malformed evidence uses ValueError
    for field, expected in (
        ("requested_count", len(ids)),
        ("completed_count", len(completed)),
        ("raw_file_count", len(files)),
    ):
        if type(receipt.get(field)) is not int or receipt[field] != expected:
            raise ValueError("Exact integer failure receipt counts required")
    inventory = {}
    buffers = {}

    def verified_content(entry):
        name = _name(entry.get("name"))
        if name not in buffers:
            file = folder / name
            if file.is_symlink() or not file.is_file():
                raise ValueError("Missing or unsafe raw evidence")
            content = file.read_bytes()
            buffers[name] = (content, len(content), hashlib.sha256(content).hexdigest())
        content, length, digest = buffers[name]
        if (
            type(entry.get("bytes")) is not int
            or entry["bytes"] != length
            or entry.get("sha256") != digest
        ):
            raise ValueError("Retained raw bytes differ from receipt")
        return content

    for entry in files:
        if not isinstance(entry, dict):
            raise ValueError("Malformed raw file entry")  # noqa: TRY004 - malformed evidence uses ValueError
        name = _name(entry.get("name"))
        if name in inventory:
            raise ValueError("Duplicate raw filename")
        content = verified_content(entry)
        inventory[name] = (entry, content)
    observed = receipt.get("observed_files")
    # Older v1 receipts did not contain observed_files. Require exact inventoried
    # raw files for that legacy shape; newer receipts also bind partial artifacts.
    if observed is None:
        expected_names = set(inventory)
    else:
        if not isinstance(observed, list):
            raise ValueError("Observed failed-file inventory required")
        expected_names = set()
        for entry in observed:
            if not isinstance(entry, dict):
                raise ValueError("Malformed observed file")  # noqa: TRY004 - malformed evidence uses ValueError
            name = _name(entry.get("name"))
            if name in expected_names:
                raise ValueError("Duplicate observed file")
            if name in inventory and any(
                entry.get(key) != inventory[name][0].get(key)
                for key in ("bytes", "sha256")
            ):
                raise ValueError("Conflicting overlapping file inventory assertions")
            verified_content(entry)
            expected_names.add(name)
        if not set(inventory) <= expected_names:
            raise ValueError("Raw inventory missing from observed files")
    if {p.name for p in folder.iterdir()} != expected_names | {
        "failed-generation.json"
    }:
        raise ValueError("Uninventoried failed-generation files")
    return (
        receipt,
        inventory,
        {
            "path": str(path.resolve()),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "completed_ids": completed,
        },
    )


def validate_dois(ids):
    if (
        not isinstance(ids, (list, tuple))
        or not 1 <= len(ids) <= 50_000
        or any(
            not isinstance(value, str)
            or not re.fullmatch(r"10\.[0-9]{4,9}/\S{1,500}", value)
            for value in ids
        )
    ):
        raise ValueError("Bounded exact retained publication DOI identifiers required")
    if len({value.casefold() for value in ids}) != len(ids):
        raise ValueError("Duplicate canonical DOI requests")
    return list(ids)


def reject_failure_envelope(payload):
    """Check governing root fields only; nested source metadata stays untouched."""
    if not isinstance(payload, dict):
        raise ValueError("Provider governing object required")  # noqa: TRY004 - malformed evidence uses ValueError
    if any(key in payload for key in ("error", "errors", "failure")):
        raise ValueError("Provider governing failure envelope contradicts success")
    if any(
        key in payload and payload[key] is not False
        for key in ("partial", "truncated", "incomplete", "failed")
    ):
        raise ValueError("Provider governing partial/failure flag contradicts success")
    if any(
        key in payload and payload[key] is not True for key in ("complete", "success")
    ):
        raise ValueError("Provider governing completion flag contradicts success")
    if isinstance(payload.get("status"), str) and payload["status"].casefold() in (
        "error",
        "errors",
        "failed",
        "failure",
        "partial",
        "incomplete",
    ):
        raise ValueError("Provider governing status contradicts success")


def response_retainer(output, manifest, entry, filename, *, allow_404=False):
    """Bind each available response to its request; keep failed attempt bodies too."""

    def retain(raw, status, date, attempt):
        final = type(status) is int and (status == 200 or (allow_404 and status == 404))
        name = (
            filename
            if final
            else "error-"
            + hashlib.sha256(entry["source_url"].encode()).hexdigest()[:20]
            + "-attempt-"
            + str(attempt)
            + ".bin"
        )
        stored = write_verified(output, name, raw)
        manifest["files"].append(
            {
                **entry,
                **stored,
                "http": status,
                "response_date": date,
                "kind": "response" if final else "http_error",
                "attempt_count": attempt,
                "request_attempts": attempt,
                "transient_failure_count": attempt - 1,
            }
        )

    return retain


def validate_response_entry(entry, url, filename, *, allow_404=False):
    """Check saved request/file/status identity, including retained error bodies."""
    if entry.get("source_url") != url:
        raise ValueError("Retained response request outside exact scope")
    kind = entry.get("kind", "response")
    attempt = entry.get("attempt_count", entry.get("request_attempts", 1))
    status = entry.get("http", 200)
    if type(attempt) is not int or not 1 <= attempt <= 4 or type(status) is not int:
        raise ValueError("Exact retained response status and attempt types required")
    if kind == "response":
        if entry["name"] != filename or status not in (
            (200, 404) if allow_404 else (200,)
        ):
            raise ValueError("Retained response filename/status mismatch")
    elif kind == "http_error":
        expected = (
            "error-"
            + hashlib.sha256(url.encode()).hexdigest()[:20]
            + "-attempt-"
            + str(attempt)
            + ".bin"
        )
        if entry["name"] != expected:
            raise ValueError("Retained error filename/request mismatch")
    else:
        raise ValueError("Unknown retained response kind")
