"""Private complete related-DOI queries; source assertions are not output counts."""

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


from urllib.parse import urlencode

API = "https://api.datacite.org/dois"
PAGE_SIZE = 25


def _query_url(doi, page):
    escaped = doi.replace("\\", "\\\\").replace('"', '\\"')
    return (
        API
        + "?"
        + urlencode(
            {
                "query": 'relatedIdentifiers.relatedIdentifier:"' + escaped + '"',
                "page[size]": PAGE_SIZE,
                "page[number]": page,
            }
        )
    )


def _page_name(doi, page):
    return (
        "query-"
        + hashlib.sha256(doi.casefold().encode()).hexdigest()[:20]
        + "-page-"
        + str(page)
        + ".json"
    )


def project(record, publication_doi):
    if not isinstance(record, dict) or not isinstance(record.get("attributes"), dict):
        raise ValueError("DataCite record/attributes required")  # noqa: TRY004 - malformed evidence uses ValueError
    attrs = record["attributes"]
    doi = attrs.get("doi")
    identity = record.get("id")
    validate_dois([doi])
    validate_dois([identity])
    if doi.casefold() != identity.casefold():
        raise ValueError("DataCite record identity conflict")
    related = attrs.get("relatedIdentifiers", [])
    if not isinstance(related, list) or any(not isinstance(r, dict) for r in related):
        raise ValueError("DataCite related identifier array required")
    matching = [
        r
        for r in related
        if r.get("relatedIdentifierType") == "DOI"
        and isinstance(r.get("relatedIdentifier"), str)
        and r["relatedIdentifier"].casefold() == publication_doi.casefold()
    ]
    if not matching:
        return None
    return {
        "SourceKey": "datacite:"
        + doi.lower()
        + "|publication:"
        + publication_doi.lower(),
        "DOI": doi.lower(),
        "RelatedPublicationDOI": publication_doi.lower(),
        "Titles": attrs.get("titles"),
        "ResourceTypes": attrs.get("types"),
        "RelationshipsToPublication": matching,
        "AllRelatedIdentifiers": attrs.get("relatedIdentifiers"),
        "Version": attrs.get("version"),
        "Publisher": attrs.get("publisher"),
        "Published": attrs.get("published"),
        "Updated": attrs.get("updated"),
        "SourceURL": attrs.get("url"),
        "Interpretation": "source_assertions; conceptual_output_count_not_inferred",
    }


def _validated_page(raw, doi, page, expected_total=None):
    payload = strict_json(raw)
    reject_failure_envelope(payload)
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("meta"), dict)
        or not isinstance(payload.get("data"), list)
    ):
        raise ValueError("DataCite page/meta/data required")  # noqa: TRY004 - malformed evidence uses ValueError
    meta = payload["meta"]
    data = payload["data"]
    total = meta.get("total")
    if (
        type(page) is not int
        or not 1 <= page <= 100
        or type(total) is not int
        or not 0 <= total <= 2500
        or (expected_total is not None and total != expected_total)
        or type(meta.get("page")) is not int
        or meta["page"] != page
    ):
        raise ValueError("DataCite source count/scope changed during pagination")
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if (
        type(meta.get("totalPages")) is not int
        or meta["totalPages"] not in ({0, 1} if total == 0 else {pages})
        or page > pages
    ):
        raise ValueError("Unexpected DataCite page coverage")
    if len(data) != min(PAGE_SIZE, max(0, total - (page - 1) * PAGE_SIZE)):
        raise ValueError("DataCite page row count differs from declared total")
    links = payload.get("links")
    if links is not None and not isinstance(links, dict):
        raise ValueError("DataCite governing links must be an object")
    if page == pages and links is not None and links.get("next") is not None:
        raise ValueError("DataCite terminal page advertises continuation")
    keys = []
    rows = []
    for record in data:
        projected = project(record, doi)
        key = record["id"].casefold()
        if key in keys:
            raise ValueError("Repeated DataCite ID within source page")
        keys.append(key)
        if projected is not None:
            rows.append(projected)
    return total, pages, keys, rows


def _verified_resume(folder, ids):
    scope = {
        "kind": "complete_related_identifier_queries_for_exact_publication_dois",
        "requested_publication_dois": ids,
    }
    receipt, inventory, proof = verified_failure(folder, "datacite", scope, ids)
    completed = receipt["completed_ids"]
    failed = receipt["failed_id"]
    indexed = {}
    failed_pages = set()
    for entry, raw in inventory.values():
        doi = entry.get("publication_doi")
        page = entry.get("page")
        if (
            doi not in ids
            or doi not in completed + [failed]
            or type(page) is not int
            or not 1 <= page <= 100
            or entry.get("source_url") != _query_url(doi, page)
        ):
            raise ValueError("DataCite failed receipt page identity invalid")
        validate_response_entry(entry, _query_url(doi, page), _page_name(doi, page))
        if doi == failed:
            failed_pages.add(page)
        if entry.get("kind", "response") == "http_error":
            continue
        if (
            entry["name"] != _page_name(doi, page)
            or (doi, page) in indexed
            or type(entry.get("http", 200)) is not int
            or entry.get("http", 200) != 200
        ):
            raise ValueError("DataCite raw response identity invalid")
        indexed[(doi, page)] = (entry, raw)
    if failed_pages and sorted(failed_pages) != list(range(1, max(failed_pages) + 1)):
        raise ValueError("Failed DataCite query has a page gap")
    prefix = []
    for doi in completed:
        numbers = sorted(page for key, page in indexed if key == doi)
        if not numbers or numbers != list(range(1, max(numbers) + 1)):
            raise ValueError("Completed DataCite query has a page gap")
        total = None
        keys = set()
        pages = None
        records = []
        files = []
        for page in numbers:
            entry, raw = indexed[(doi, page)]
            total, pages, page_ids, rows = _validated_page(raw, doi, page, total)
            if keys.intersection(page_ids):
                raise ValueError("Repeated DataCite ID across source pages")
            keys.update(page_ids)
            records.extend(rows)
            files.append((entry, raw))
        if numbers != list(range(1, pages + 1)) or len(keys) != total:
            raise ValueError("Completed DataCite query not fully covered")
        prefix.append(
            (
                doi,
                files,
                records,
                {"publication_doi": doi, "returned_records": total, "pages": pages},
            )
        )
    return prefix, proof


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
    scope = {
        "kind": "complete_related_identifier_queries_for_exact_publication_dois",
        "requested_publication_dois": ids,
    }
    prefix, proof = [], None
    if resume_from is not None:
        if output.resolve().is_relative_to(Path(resume_from).resolve()):
            raise ValueError("Resume input and new output must be separate directories")
        prefix, proof = _verified_resume(Path(resume_from), ids)
    create_output(output)
    manifest = {
        "source": "datacite",
        "scope": scope["kind"],
        "scope_sha256": scope_sha256(scope),
        "generation_id": uuid.uuid4().hex,
        "requested_publication_dois": ids,
        "captured_utc": datetime.now(UTC).isoformat(),
        "files": [],
        "queries": [],
        "request_attempts": [],
        "max_read_attempts": max_attempts,
    }
    if proof is not None:
        manifest["resumed_from"] = proof
    rows = []
    completed = []
    current = None
    try:
        for doi, files, records, query in prefix:
            current = doi
            for entry, raw in files:
                stored = write_verified(output, entry["name"], raw)
                manifest["files"].append(
                    {**entry, **stored, "reused_from_failure_receipt": proof["sha256"]}
                )
            rows.extend(records)
            manifest["queries"].append(query)
            completed.append(doi)
        for doi in ids[len(completed) :]:
            current = doi
            page = 1
            total = None
            keys = set()
            while True:
                url = _query_url(doi, page)
                raw, _, _, _ = read_response(
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
                    retain=response_retainer(
                        output,
                        manifest,
                        {"publication_doi": doi, "page": page, "source_url": url},
                        _page_name(doi, page),
                    ),
                )
                total, pages, page_ids, page_rows = _validated_page(
                    raw, doi, page, total
                )
                if keys.intersection(page_ids):
                    raise ValueError("Repeated DataCite ID across source pages")
                keys.update(page_ids)
                rows.extend(page_rows)
                if page == pages:
                    break
                page += 1
            if len(keys) != total:
                raise ValueError("Incomplete DataCite query result set")
            manifest["queries"].append(
                {"publication_doi": doi, "returned_records": total, "pages": page}
            )
            completed.append(doi)
        manifest["relationship_assertions"] = len(rows)
        return commit_generation(output, "related-outputs.json", rows, manifest)
    except Exception as error:
        write_failure_receipt(
            output,
            source="datacite",
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
    print(
        json.dumps(
            {
                "complete": result["complete"],
                "relationship_assertions": result["relationship_assertions"],
            }
        )
    )


if __name__ == "__main__":
    main()
