"""Build and verify a reproducible source-only release archive.

Tenant snapshots, private configuration, Git history and native recovery
packages are intentionally excluded. They require a separate private backup
route and are never implied by this source release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

try:
    from project_utils import ROOT
except ModuleNotFoundError:  # import through the repository package during tests
    from scripts.project_utils import ROOT

VERSION_RE = re.compile(
    r"^(?P<major>0|[1-9][0-9]*)\.(?P<minor>0|[1-9][0-9]*)\."
    r"(?P<patch>0|[1-9][0-9]*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
EXCLUDED_PREFIXES = ("private/", ".private/", ".flowagent/", "downloads/canonical_live_artifacts/")
# Native Power Platform recovery/deployment files are not source archives.
# In particular, PBIX/PBIT can contain cached records, credentials and model
# state even when checked into an otherwise source-only repository.
EXCLUDED_SUFFIXES = (".zip", ".bundle", ".pbix", ".pbit", ".msapp", ".msflow")
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
WINDOWS_RESERVED_NAMES = {
    "con", "prn", "aux", "nul", "conin$", "conout$",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


def run(args: list[str], cwd: Path = ROOT) -> str:
    process = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if process.returncode:
        raise RuntimeError(f"Command failed ({process.returncode}): {args}\n{process.stdout}\n{process.stderr}")
    return (process.stdout + process.stderr).strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_stable_entry(target: zipfile.ZipFile, name: str, content: bytes) -> None:
    """Write a deterministic ZIP member independent of the current clock."""
    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    target.writestr(info, content)


def write_release_receipt(path: Path, receipt: dict) -> None:
    """Create the versioned receipt without replacing evidence from another run."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def validate_extraction(extracted: Path) -> None:
    """Run the repository's required full harness from the fresh extraction."""
    run([str(extracted / '.venv' / 'bin' / 'python'), "scripts/agent_harness.py", "check", "--task", "all"], extracted)


def prepare_extraction_test_environment(extracted: Path) -> None:
    """Configure a disposable checkout fixture after archive integrity verification.

    Git-dependent guards must see a real ignore policy. This fixture has no
    source history, credentials or native bindings and is never archived.
    """
    if (extracted / ".git").exists() or (extracted / ".venv").exists():
        raise RuntimeError("fresh extraction unexpectedly contains local state")
    run(["git", "init", "--quiet"], extracted)
    (extracted / "private" / "ops").mkdir(parents=True)
    for path in ("private/ops/probe", ".venv/probe"):
        run(["git", "check-ignore", "-q", path], extracted)
    run([sys.executable, "-m", "venv", ".venv"], extracted)
    version = run([str(extracted / ".venv" / "bin" / "python"), "--version"], extracted)
    if version != "Python 3.15.1":
        raise RuntimeError(f"unexpected extraction test interpreter: {version}")
    run(["uv", "pip", "sync", "--require-hashes", "--python", str(extracted / ".venv" / "bin" / "python"),
         "requirements-dev.txt"], extracted)


def validate_version(version: str) -> str:
    match = VERSION_RE.fullmatch(version) if isinstance(version, str) else None
    if match is None:
        raise ValueError("version must use MAJOR.MINOR.PATCH with an optional preview suffix")
    prerelease = match.group("prerelease")
    if prerelease and any(
        identifier.isdigit() and len(identifier) > 1 and identifier.startswith("0")
        for identifier in prerelease.split(".")
    ):
        raise ValueError("numeric prerelease identifiers must not contain leading zeroes")
    return version


def validate_identity(value: str, field: str) -> str:
    """Require a nonempty identity without silently trimming caller input."""
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be a nonempty, unpadded string")
    return value


def portable_path_key(relative: str) -> str:
    """Validate a ZIP member path and return its case/normalization-safe key."""
    if not isinstance(relative, str) or not relative:
        raise ValueError("path is not portable")
    if "\\" in relative:
        raise ValueError("path is not normalized because it contains a backslash")
    if "\x00" in relative:
        raise ValueError("path is not portable because it contains NUL")
    parts = relative.split("/")
    if any(not part or part in {".", ".."} for part in parts):
        raise ValueError("path is not normalized")
    for part in parts:
        device_name = part.split(".", 1)[0].rstrip(" .").casefold()
        if (":" in part or part.endswith((".", " ")) or any(ord(char) < 32 for char in part)
                or device_name in WINDOWS_RESERVED_NAMES):
            raise ValueError("path is not portable to Windows")
    return "/".join(unicodedata.normalize("NFC", part).casefold() for part in parts)


def register_portable_file(key: str, files: set[str], directories: set[str]) -> None:
    """Reject file/directory conflicts after portable case normalization."""
    parts = key.split("/")
    if (key in files or key in directories
            or any("/".join(parts[:index]) in files for index in range(1, len(parts)))):
        raise ValueError("file and directory paths collide on a case-insensitive filesystem")
    directories.update("/".join(parts[:index]) for index in range(1, len(parts)))
    files.add(key)


def source_paths(root: Path = ROOT) -> list[Path]:
    """Return tracked source files eligible for a source archive."""
    base = root.resolve()
    try:
        names = run(["git", "ls-files", "-z"], root).split("\0")
    except RuntimeError:
        # A source archive intentionally has no .git directory.  Walk the
        # extracted tree so its local validation can still be self-contained.
        names = [path.relative_to(root).as_posix() for path in root.rglob("*")
                 if path.is_file() and not (set(path.relative_to(root).parts) & EXCLUDED_DIRS)
                 and ".git" not in path.parts]
    paths = []
    portable_files: set[str] = set()
    portable_directories: set[str] = set()
    for name in names:
        if not name:
            continue
        normalised = name
        folded = normalised.casefold()
        if folded == "release-manifest.json" or folded.startswith(EXCLUDED_PREFIXES):
            continue
        filename = normalised.rsplit("/", 1)[-1].casefold()
        if filename.startswith(".env") or filename.endswith(".env"):
            continue
        if folded.endswith(EXCLUDED_SUFFIXES):
            continue
        # Validate only paths eligible for the archive. Excluded private paths
        # may legitimately differ in case on a POSIX authoring filesystem.
        try:
            portable_name = portable_path_key(name)
        except ValueError as exc:
            raise RuntimeError(f"source path is not portable for release packaging: {name!r}") from exc
        try:
            register_portable_file(portable_name, portable_files, portable_directories)
        except ValueError as exc:
            raise RuntimeError(f"source paths collide on a case-insensitive filesystem: {name!r}") from exc
        relative = Path(normalised)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"source path is unsafe for release packaging: {name}")
        path = root / relative
        # A tracked symlink can expose private material outside the checkout
        # while still appearing to be an ordinary allowlisted source path.
        # Internal aliases remain supported for the pinned Conductor skill.
        resolved = path.resolve()
        if not resolved.is_relative_to(base):
            raise RuntimeError(f"source path escapes repository root: {name}")
        resolved_name = resolved.relative_to(base).as_posix().casefold()
        if (resolved_name.startswith(EXCLUDED_PREFIXES)
                or resolved.name.casefold().startswith(".env")
                or resolved.name.casefold().endswith((".env", *EXCLUDED_SUFFIXES))):
            raise RuntimeError(f"source path resolves to excluded private/runtime material: {name}")
        if path.is_file():
            paths.append(path)
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def build_manifest(paths: list[Path], version: str, schema_version: str, batch_id: str,
                   root: Path = ROOT) -> dict:
    validate_version(version)
    validate_identity(schema_version, "SchemaVersion")
    validate_identity(batch_id, "AcceptedBatchID")
    try:
        head = run(["git", "rev-parse", "HEAD"], root)
        dirty = bool(run(["git", "status", "--porcelain"], root))
    except RuntimeError:
        head = "source-archive"
        dirty = False
    return {
        "SoftwareVersion": version,
        "SchemaVersion": schema_version,
        "AcceptedBatchID": batch_id,
        "SourceCommit": head,
        "DirtyBuild": dirty,
        "NativeAcceptance": False,
        "Files": [
            {"path": path.relative_to(root).as_posix(), "sha256": digest(path), "bytes": path.stat().st_size}
            for path in paths
        ],
    }


def verify_manifest(root: Path, manifest: dict) -> None:
    """Verify every source entry recorded in a release manifest.

    This is deliberately scoped to the existing release manifest rather than
    introducing a second receipt format. Reject unsafe or duplicate paths so a
    malformed manifest cannot escape the extracted release directory.
    """
    if not isinstance(manifest, dict):
        raise ValueError("release manifest must be an object")
    try:
        validate_version(manifest.get("SoftwareVersion"))
    except (TypeError, ValueError) as exc:
        raise ValueError("release manifest has invalid SoftwareVersion") from exc
    for field in ("SchemaVersion", "AcceptedBatchID"):
        try:
            validate_identity(manifest.get(field), field)
        except ValueError as exc:
            raise ValueError(f"release manifest has invalid {field}") from exc
    source_commit = manifest.get("SourceCommit")
    if not isinstance(source_commit, str) or not re.fullmatch(r"(?:source-archive|[0-9a-f]{40}|[0-9a-f]{64})", source_commit):
        raise ValueError("release manifest has invalid SourceCommit")
    if not isinstance(manifest.get("DirtyBuild"), bool):
        raise ValueError("release manifest has invalid DirtyBuild")
    if manifest.get("NativeAcceptance") is not False:
        raise ValueError("source release manifest must not claim NativeAcceptance")

    files = manifest.get("Files")
    if not isinstance(files, list):
        raise ValueError("release manifest Files must be a list")
    seen: set[str] = set()
    portable_files: set[str] = set()
    portable_directories: set[str] = set()
    expected_paths: set[str] = set()
    base = root.resolve()
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("release manifest contains an invalid file entry")
        relative = entry["path"]
        candidate = (base / relative).resolve()
        if candidate == base or not candidate.is_relative_to(base):
            raise ValueError(f"release manifest path escapes extraction root: {relative}")
        canonical = candidate.relative_to(base).as_posix()
        if canonical != relative:
            raise ValueError(f"release manifest path is not normalized: {relative}")
        if canonical in seen:
            raise ValueError(f"release manifest contains duplicate path: {relative}")
        try:
            portable_name = portable_path_key(relative)
        except ValueError as exc:
            raise ValueError(f"release manifest {exc}: {relative!r}") from exc
        try:
            register_portable_file(portable_name, portable_files, portable_directories)
        except ValueError as exc:
            raise ValueError(f"release manifest contains platform-colliding path: {relative}") from exc
        seen.add(canonical)
        expected_paths.add(canonical)
        if not candidate.is_file():
            raise ValueError(f"release file is missing: {relative}")
        expected_hash = entry.get("sha256")
        expected_bytes = entry.get("bytes")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError(f"release manifest has invalid SHA-256 for: {relative}")
        if not isinstance(expected_bytes, int) or isinstance(expected_bytes, bool) or expected_bytes < 0:
            raise ValueError(f"release manifest has invalid byte length for: {relative}")
        if candidate.stat().st_size != expected_bytes:
            raise ValueError(f"release file length differs from manifest: {relative}")
        if digest(candidate) != expected_hash:
            raise ValueError(f"release file hash differs from manifest: {relative}")

    actual_paths = {
        path.relative_to(base).as_posix()
        for path in base.rglob("*")
        if path.is_file() and path != base / "RELEASE-MANIFEST.json"
    }
    unexpected = sorted(actual_paths - expected_paths)
    if unexpected:
        raise ValueError(f"release extraction contains unmanifested files: {', '.join(unexpected[:5])}")


def package(output: Path, version: str = "0.3.0-rc1", schema_version: str = "publication-platform-v1",
            accepted_batch_id: str = "local-source", root: Path = ROOT) -> dict:
    """Create a clean-tree source archive and verify a fresh extraction."""
    output.mkdir(parents=True, exist_ok=True)
    version = validate_version(version)
    archive = output / f"CHHHS-Research-Publications-v{version}-Source.zip"
    receipt_path = output / f"CHHHS-Research-Publications-v{version}-Source-receipt.json"
    if archive.exists() or receipt_path.exists():
        raise FileExistsError("refusing to replace an existing release archive or receipt")
    if run(["git", "status", "--porcelain"], root):
        raise RuntimeError("Commit or isolate changes before making a reproducible release")
    paths = source_paths(root)
    manifest = build_manifest(paths, version, schema_version, accepted_batch_id, root)
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for path in paths:
            write_stable_entry(
                target,
                "chhhs-research-publications/" + path.relative_to(root).as_posix(),
                path.read_bytes(),
            )
        write_stable_entry(
            target,
            "chhhs-research-publications/RELEASE-MANIFEST.json",
            (json.dumps(manifest, indent=2) + "\n").encode("utf-8"),
        )

    with tempfile.TemporaryDirectory(prefix="chhhs-release-") as temporary:
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(temporary)
            names = {name.replace("\\", "/") for name in zipped.namelist()}
        extracted = Path(temporary) / "chhhs-research-publications"
        if any(name.endswith("/.git") or "/.git/" in name for name in names):
            raise RuntimeError("source archive must not contain .git")
        if any(name.startswith("chhhs-research-publications/private/") or
               name.startswith("chhhs-research-publications/downloads/canonical_live_artifacts/")
               for name in names):
            raise RuntimeError("source archive contains private/runtime artefacts")
        extracted_manifest = json.loads((extracted / "RELEASE-MANIFEST.json").read_text(encoding="utf-8"))
        if extracted_manifest != manifest:
            raise RuntimeError("fresh extraction manifest differs")
        verify_manifest(extracted, extracted_manifest)
        prepare_extraction_test_environment(extracted)
        validate_extraction(extracted)

    receipt = {
        **manifest,
        "Archive": {"path": archive.name, "sha256": digest(archive), "bytes": archive.stat().st_size},
        "FreshExtractionVerified": True,
        "ExtractionTestSetup": "disposable empty Git repository, ignored private directory, and Python 3.15.1 environment synced from the dev lock; no native bindings",
        "ContainsGitHistory": False,
        "ContainsPrivateRuntime": False,
    }
    write_release_receipt(receipt_path, receipt)
    print(json.dumps(receipt, indent=2))
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT.parent)
    parser.add_argument("--version", default="0.3.0-rc1")
    parser.add_argument("--schema-version", default="publication-platform-v1")
    parser.add_argument("--accepted-batch-id", default="local-source")
    args = parser.parse_args()
    package(args.output_dir, args.version, args.schema_version, args.accepted_batch_id)
