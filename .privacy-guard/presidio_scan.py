# Copyright (c) 2026 CareOps contributors.
# SPDX-License-Identifier: Apache-2.0
"""Offline Presidio worker and exact Git-object selection; no matched text is output."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import socket
import subprocess
import sys
from importlib import metadata
from pathlib import Path

OID = re.compile(r"[a-f0-9]{40}")


class Refusal(Exception):
    """A constant diagnostic code, never untrusted content."""


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "--literal-pathspecs", "-C", str(root), *args],
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        raise Refusal("git_read_failed")
    return result.stdout


def selected_text(root: Path, tip: str, bases: list[str], policy: dict) -> list[dict]:
    """Inspect every changed blob and message in outgoing commits, including deletions later."""
    if any(not OID.fullmatch(value) for value in [tip, *bases]):
        raise Refusal("invalid_object_id")
    if git(root, "cat-file", "-t", tip).strip() != b"commit":
        raise Refusal("commit_required")
    commits = (
        git(root, "rev-list", tip, *(["--not", *bases] if bases else []))
        .decode()
        .splitlines()
    )
    if len(commits) > policy["maxCommits"]:
        raise Refusal("commit_limit")
    selected, seen, total = [], set(), 0

    def add(identity: str, blob: bytes) -> None:
        nonlocal total
        if len(blob) > policy["maxBlobBytes"]:
            raise Refusal("blob_limit")
        if b"\0" in blob:
            return  # Existing exact document/binary approval gate still applies.
        try:
            text = blob.decode("utf-8")
        except UnicodeDecodeError:
            return  # Binary/unsupported encoding is covered by the original gate.
        total += len(blob)
        if total > policy["maxTotalBytes"] or len(selected) >= policy["maxBlobs"]:
            raise Refusal("text_scope_limit")
        selected.append(
            {
                "identity": hashlib.sha256(identity.encode()).hexdigest(),
                "blob_sha256": hashlib.sha256(blob).hexdigest(),
                "text": text,
            }
        )

    for commit in commits:
        message = git(root, "show", "-s", "--format=%B", commit)
        add("message:" + hashlib.sha256(message).hexdigest(), message)
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
            entry = git(root, "ls-tree", "-z", commit, "--", name)
            if not entry:
                raise Refusal("missing_changed_object")
            mode, kind, oid = entry.split(b"\t", 1)[0].decode().split()
            if mode == "160000":
                continue  # Each submodule needs its own gate; never recurse silently.
            if kind != "blob" or mode not in {"100644", "100755"}:
                raise Refusal("unsupported_file_mode")
            if (name, oid) in seen:
                continue
            seen.add((name, oid))
            if int(git(root, "cat-file", "-s", oid)) > policy["maxBlobBytes"]:
                raise Refusal("blob_limit")
            add("path:" + name + ":" + oid, raw)
            add(name + ":" + oid, git(root, "cat-file", "blob", oid))
    return selected


def prohibit_network() -> None:
    """No analyzer network calls, even on an empty suffix cache or missing model."""

    def refused(*_args, **_kwargs):
        raise Refusal("analyzer_network_attempt")

    socket.socket.connect = refused
    socket.socket.connect_ex = refused
    socket.create_connection = refused
    socket.getaddrinfo = refused
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"


def load_analyzer(policy: dict):
    """Require the qualified normal model, without downloads or tokenizer fallbacks."""
    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet

    actual_python = ".".join(map(str, sys.version_info[:3]))
    if actual_python != policy["python"] or sys.prefix == sys.base_prefix:
        raise Refusal("runtime_not_qualified")
    for package, version in policy["packages"].items():
        if metadata.version(package) != version:
            raise Refusal("package_not_qualified")
    for distribution in metadata.distributions():
        requires_python = distribution.metadata.get("Requires-Python")
        if requires_python and actual_python not in SpecifierSet(requires_python):
            raise Refusal("unsupported_python_metadata")
        for value in distribution.requires or []:
            required = Requirement(value)
            if required.marker and not required.marker.evaluate({"extra": ""}):
                continue
            if (
                required.specifier
                and metadata.version(required.name) not in required.specifier
            ):
                raise Refusal("incompatible_dependency")
    import spacy

    if policy["model"] != "en_core_web_sm" or not spacy.util.is_package(
        policy["model"]
    ):
        raise Refusal("model_missing")
    model = metadata.distribution("en-core-web-sm")
    digest = hashlib.sha256()
    names = sorted(
        str(name)
        for name in model.files
        if str(name).startswith("en_core_web_sm/") and not str(name).endswith(".pyc")
    )
    for name in names:
        digest.update(
            name.encode()
            + b"\0"
            + hashlib.sha256(model.locate_file(name).read_bytes()).digest()
        )
    if not names or digest.hexdigest() != policy["modelFingerprint"]:
        raise Refusal("model_content_changed")
    import tldextract
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_analyzer.predefined_recognizers import EmailRecognizer

    class OfflineEmailRecognizer(EmailRecognizer):
        """Use Presidio's recognizer with the packaged, network-free suffix list."""

        extractor = tldextract.TLDExtract(suffix_list_urls=())

        def validate_result(self, pattern_text):
            return self.extractor(pattern_text).fqdn != ""

    provider = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": policy["language"], "model_name": policy["model"]}
            ],
        }
    )
    analyzer = AnalyzerEngine(
        nlp_engine=provider.create_engine(), supported_languages=[policy["language"]]
    )
    analyzer.registry.remove_recognizer("EmailRecognizer")
    analyzer.registry.add_recognizer(OfflineEmailRecognizer())
    # Additive labelled identifiers: no claim of checksum or unlabelled coverage.
    for entity, expression in {
        "AU_TFN": r"(?i)\b(?:TFN|tax file number)\s*[:=]?\s*(?:\d[ -]?){8}\d\b",
        "AU_MEDICARE": r"(?i)\bmedicare(?: number)?\s*[:=]?\s*(?:\d[ -]?){9,10}\d\b",
        "DATE_OF_BIRTH": r"(?i)\b(?:DOB|date of birth)\s*[:=]?\s*\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}\b",
    }.items():
        analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity=entity,
                patterns=[Pattern("labelled_identifier", expression, 0.85)],
                supported_language=policy["language"],
            )
        )
    if not set(policy["entities"]).issubset(
        analyzer.get_supported_entities(language=policy["language"])
    ):
        raise Refusal("recognizer_missing")
    return analyzer


def analyze(
    items: list[dict], policy: dict, analyzer, reviews: dict | None = None
) -> dict:
    findings = []
    reviewed = 0
    accepted = (reviews or {}).get("findings", [])
    size, overlap = policy["chunkCharacters"], policy["overlapCharacters"]
    if not 0 < overlap < size:
        raise Refusal("invalid_chunk_policy")
    for item in items:
        matches = {}
        for start in range(0, max(1, len(item["text"])), size - overlap):
            result = analyzer.analyze(
                text=item["text"][start : start + size],
                language=policy["language"],
                entities=policy["entities"],
                score_threshold=policy["threshold"],
            )
            for value in result:
                left, right = start + value.start, start + value.end
                key = (value.entity_type, left, right)
                matches[key] = {
                    "identity": item["identity"],
                    "blob_sha256": item.get(
                        "blob_sha256", hashlib.sha256(item["text"].encode()).hexdigest()
                    ),
                    "entity_index": policy["entities"].index(value.entity_type),
                    "start": left,
                    "end": right,
                    "value_sha256": hashlib.sha256(
                        item["text"][left:right].encode()
                    ).hexdigest(),
                }
        unreviewed = []
        for match in matches.values():
            if any(
                all(approval.get(k) == v for k, v in match.items())
                and approval.get("reason")
                and approval.get("reviewer")
                for approval in accepted
            ):
                reviewed += 1
            else:
                unreviewed.append(match)
        if unreviewed:
            findings.append(
                {
                    "identity": item["identity"],
                    "entities": sorted(
                        {policy["entities"][x["entity_index"]] for x in unreviewed}
                    ),
                    "details": unreviewed,
                }
            )
    return {
        "protocol": 1,
        "checked": len(items),
        "findings": findings,
        "reviewed": reviewed,
    }


def worker() -> int:
    """Parent captures ALL worker output and emits only validated aggregate diagnostics."""
    try:
        payload = json.loads(sys.stdin.buffer.read(25 * 1024 * 1024))
        # Imports and third-party diagnostics must never reach the parent log.
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            if Path(sys.prefix).resolve() != Path(payload["expected_prefix"]).resolve():
                raise Refusal("unexpected_scanner_environment")
            prohibit_network()
            analyzer = load_analyzer(payload["policy"])
            result = analyze(
                payload["items"], payload["policy"], analyzer, payload.get("reviews")
            )
        sys.stdout.write(json.dumps(result))
        return 0
    except Exception:  # noqa: BLE001 -- fail closed without logging third-party input/errors
        sys.stdout.write('{"protocol":1,"error":"scanner_unavailable_or_failed"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(worker())
