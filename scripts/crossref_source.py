"""Private exact-DOI registered metadata capture; no native admission."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request

try:
    from scripts.source_capture_receipt import (
        commit_generation,
        create_output,
        reject_failure_envelope,
        response_retainer,
        scope_sha256,
        strict_json,
        validate_dois,
        validate_response_entry,
        verified_failure,
        write_failure_receipt,
        write_verified,
    )
    from scripts.source_http_retry import (
        MAX_READ_ATTEMPTS as MAX_READ_ATTEMPTS,  # noqa: PLC0414 - preserve public policy constants
    )
    from scripts.source_http_retry import (
        TRANSIENT_HTTP_STATUSES as TRANSIENT_HTTP_STATUSES,  # noqa: PLC0414 - preserve public policy constants
    )
    from scripts.source_http_retry import (
        guarded_urlopen,
        read_response,
        validate_attempts,
    )
except ImportError:
    from source_capture_receipt import (
        commit_generation,
        create_output,
        reject_failure_envelope,
        response_retainer,
        scope_sha256,
        strict_json,
        validate_dois,
        validate_response_entry,
        verified_failure,
        write_failure_receipt,
        write_verified,
    )
    from source_http_retry import (
        MAX_READ_ATTEMPTS as MAX_READ_ATTEMPTS,  # noqa: PLC0414 - preserve public policy constants
    )
    from source_http_retry import (
        TRANSIENT_HTTP_STATUSES as TRANSIENT_HTTP_STATUSES,  # noqa: PLC0414 - preserve public policy constants
    )
    from source_http_retry import (
        guarded_urlopen,
        read_response,
        validate_attempts,
    )
urlopen = guarded_urlopen

from urllib.parse import quote

API = "https://api.crossref.org/works/"


def project(payload, doi, http=200):
    validate_dois([doi])
    if type(http) is not int or http not in (200, 404):
        raise ValueError("Exact Crossref outcome status required")
    base = {
        "SourceKey": "crossref:" + doi.lower(),
        "DOI": doi.lower(),
        "SourceURL": "https://doi.org/" + doi,
        "Coverage": "registered_metadata_only",
    }
    if http == 404:
        return {
            **base,
            "LookupStatus": "not_found",
            "Title": None,
            "UpdateTo": None,
            "Relation": None,
            "Assertions": None,
        }
    reject_failure_envelope(payload)
    if not isinstance(payload, dict) or not isinstance(payload.get("message"), dict):
        raise ValueError("Crossref message object required")  # noqa: TRY004 - malformed evidence uses ValueError
    message = payload["message"]
    if not isinstance(message.get("DOI"), str):
        raise ValueError("Crossref DOI string required")  # noqa: TRY004 - malformed evidence uses ValueError
    if message.get("title") is not None and (
        not isinstance(message["title"], list)
        or any(not isinstance(value, str) for value in message["title"])
    ):
        raise ValueError("Crossref source title array required")
    if payload.get("status") != "ok" or message["DOI"].casefold() != doi.casefold():
        raise ValueError("Crossref status or registered DOI differs from request")
    return {
        **base,
        "LookupStatus": "found",
        "Title": message.get("title"),
        "Type": message.get("type"),
        "UpdateTo": message.get("update-to"),
        "Relation": message.get("relation"),
        "Assertions": message.get("assertion"),
        "Indexed": message.get("indexed"),
        "Deposited": message.get("deposited"),
    }


def _filename(doi):
    return "doi-" + hashlib.sha256(doi.casefold().encode()).hexdigest()[:20] + ".json"


def _url(doi):
    return API + quote(doi, safe="")


def _verified_resume(folder, ids):
    scope = {"kind": "exact_retained_publication_dois", "requested_ids": ids}
    receipt, inventory, proof = verified_failure(folder, "crossref", scope, ids)
    indexed = {}
    for entry, raw in inventory.values():
        doi = entry.get("doi")
        if (
            doi not in ids
            or doi not in receipt["completed_ids"] + [receipt["failed_id"]]
            or entry.get("source_url") != _url(doi)
        ):
            raise ValueError("Crossref retained request outside exact scope")
        validate_response_entry(entry, _url(doi), _filename(doi), allow_404=True)
        if entry.get("kind", "response") == "http_error":
            continue
        if (
            entry["name"] != _filename(doi)
            or type(entry.get("http")) is not int
            or entry["http"] not in (200, 404)
            or doi in indexed
        ):
            raise ValueError("Crossref retained file identity invalid")
        indexed[doi] = (entry, raw)
    reused = []
    for doi in receipt["completed_ids"]:
        if doi not in indexed:
            raise ValueError("Completed Crossref prefix lacks raw response")
        entry, raw = indexed[doi]
        row = project(
            strict_json(raw) if entry["http"] == 200 else {}, doi, entry["http"]
        )
        reused.append((doi, entry, raw, row))
    return reused, proof


def capture(
    ids,
    output: Path,
    resume_from: Path | None = None,
    *,
    opener=None,
    max_attempts=1,
    sleep=None,
):
    ids = validate_dois(ids)
    validate_attempts(max_attempts)
    output = Path(output)
    scope = {"kind": "exact_retained_publication_dois", "requested_ids": ids}
    prefix, proof = [], None
    if resume_from is not None:
        if output.resolve().is_relative_to(Path(resume_from).resolve()):
            raise ValueError("Resume input and new output must be separate directories")
        prefix, proof = _verified_resume(Path(resume_from), ids)
    create_output(output)
    manifest = {
        "source": "crossref",
        "scope": scope["kind"],
        "scope_sha256": scope_sha256(scope),
        "generation_id": uuid.uuid4().hex,
        "requested_ids": ids,
        "captured_utc": datetime.now(UTC).isoformat(),
        "files": [],
        "request_attempts": [],
        "max_read_attempts": max_attempts,
    }
    if proof is not None:
        manifest["resumed_from"] = proof
    rows = []
    completed = []
    current = None
    try:
        for doi, entry, raw, row in prefix:
            current = doi
            stored = write_verified(output, entry["name"], raw)
            manifest["files"].append(
                {**entry, **stored, "reused_from_failure_receipt": proof["sha256"]}
            )
            rows.append(row)
            completed.append(doi)
        for doi in ids[len(completed) :]:
            current = doi
            url = _url(doi)
            raw, status, _, _ = read_response(
                Request(
                    url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "RIMS-source-retention/1.0",
                    },
                ),
                manifest["request_attempts"],
                opener=opener or urlopen,
                max_attempts=max_attempts,
                sleep=sleep or time.sleep,
                allow_404=True,
                retain=response_retainer(
                    output,
                    manifest,
                    {"doi": doi, "source_url": url},
                    _filename(doi),
                    allow_404=True,
                ),
            )
            rows.append(project(strict_json(raw) if status == 200 else {}, doi, status))
            completed.append(doi)
        manifest["count"] = len(rows)
        return commit_generation(output, "publication-notices.json", rows, manifest)
    except Exception as error:
        write_failure_receipt(
            output,
            source="crossref",
            scope=scope,
            files=manifest["files"],
            completed_ids=completed,
            failed_id=current if len(completed) < len(ids) else None,
            error=error,
            resumed_from=proof,
            generation_id=manifest["generation_id"],
            request_attempts=manifest["request_attempts"],
        )
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--max-read-attempts", type=int, choices=range(1, 5), default=1)
    args = parser.parse_args()
    result = capture(
        strict_json(args.ids_file.read_bytes())["doi_ids"],
        args.output,
        resume_from=args.resume_from,
        max_attempts=args.max_read_attempts,
    )
    print(json.dumps({"complete": result["complete"], "records": result["count"]}))


if __name__ == "__main__":
    main()
