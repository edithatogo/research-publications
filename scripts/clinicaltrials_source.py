"""Private exact-ID trial capture; no native admission or implicit read retries."""

from __future__ import annotations

import argparse
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
        is_retryable_request_error,
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
        is_retryable_request_error,
        read_response,
        validate_attempts,
    )
urlopen = guarded_urlopen

import re

API = "https://clinicaltrials.gov/api/v2/studies/"


def _bounded_display_title(value):
    """At most 255 UTF-16 code units without cutting a supplementary character."""
    units = 0
    for index, char in enumerate(value):
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            raise ValueError("Unpaired surrogate in display title")
        width = 2 if code > 0xFFFF else 1
        if units + width > 255:
            return value[:index]
        units += width
    return value


def register_fields(row, raw_sha256, observed_utc, archive_url):
    """Prepare only source-owned fields; never emit operator-maintained values."""
    nct_id = validate_ids([row["NCTId"]])[0]
    if row["SourceKey"] != "clinicaltrials.gov:" + nct_id:
        raise ValueError("Conflicting trial source key")
    if not re.fullmatch(r"[0-9a-f]{64}", raw_sha256):
        raise ValueError("Full retained payload hash required")
    source_title = row.get("Title")
    if source_title is not None and not isinstance(source_title, str):
        raise ValueError("Source title must be text or null")
    title = _bounded_display_title(source_title or nct_id)
    return {
        "Title": title,
        "SourceKey": row["SourceKey"],
        "NCTId": nct_id,
        "FullStudyTitle": source_title,
        "OfficialTitle": row.get("OfficialTitle") or "",
        "OverallStatus": row.get("OverallStatus") or "",
        "StudyType": row.get("StudyType") or "",
        "LeadSponsor": row.get("LeadSponsor") or "",
        "StartDateSource": json.dumps(
            row.get("StartDate"), ensure_ascii=False, allow_nan=False
        ),
        "CompletionDateSource": json.dumps(
            row.get("CompletionDate"), ensure_ascii=False, allow_nan=False
        ),
        "LastUpdateSource": json.dumps(
            row.get("LastUpdatePosted"), ensure_ascii=False, allow_nan=False
        ),
        "SourceURL": row["SourceURL"],
        "SourcePayloadSHA256": raw_sha256,
        "SourceObservedUTC": observed_utc,
        "ArchiveFileURL": archive_url,
    }


def project(record, expected_id):
    validate_ids([expected_id])
    reject_failure_envelope(record)
    if not isinstance(record, dict) or not isinstance(
        record.get("protocolSection"), dict
    ):
        raise ValueError("Trial protocol object required")  # noqa: TRY004 - malformed evidence uses ValueError
    protocol = record["protocolSection"]
    if not isinstance(protocol.get("identificationModule"), dict):
        raise ValueError("Trial identification object required")  # noqa: TRY004 - malformed evidence uses ValueError
    identity = protocol["identificationModule"]
    if identity["nctId"] != expected_id:
        raise ValueError("Source identity differs from requested NCT ID")
    status = protocol.get("statusModule", {})
    sponsor = protocol.get("sponsorCollaboratorsModule", {})
    design = protocol.get("designModule", {})
    if any(not isinstance(module, dict) for module in (status, sponsor, design)):
        raise ValueError("Trial source modules must be objects")
    lead = sponsor.get("leadSponsor", {})
    if not isinstance(lead, dict):
        raise ValueError("Trial lead sponsor object required")  # noqa: TRY004 - malformed evidence uses ValueError
    for value in (
        identity.get("briefTitle"),
        identity.get("officialTitle"),
        status.get("overallStatus"),
        design.get("studyType"),
        lead.get("name"),
    ):
        if value is not None and not isinstance(value, str):
            raise ValueError("Trial projected text must be string or null")
    for name in ("startDateStruct", "completionDateStruct", "lastUpdatePostDateStruct"):
        if status.get(name) is not None and not isinstance(status[name], dict):
            raise ValueError("Trial dates retain structured objects")
    return {
        "SourceKey": "clinicaltrials.gov:" + expected_id,
        "NCTId": expected_id,
        "Title": identity.get("briefTitle"),
        "OfficialTitle": identity.get("officialTitle"),
        "OverallStatus": status.get("overallStatus"),
        "StudyType": design.get("studyType"),
        "LeadSponsor": lead.get("name"),
        "StartDate": status.get("startDateStruct"),
        "CompletionDate": status.get("completionDateStruct"),
        "LastUpdatePosted": status.get("lastUpdatePostDateStruct"),
        "SourceURL": "https://clinicaltrials.gov/study/" + expected_id,
    }


def validate_ids(values):
    if (
        not isinstance(values, (list, tuple))
        or not 1 <= len(values) <= 50_000
        or any(
            not isinstance(v, str) or not re.fullmatch(r"NCT[0-9]{8}", v)
            for v in values
        )
    ):
        raise ValueError("Bounded nonempty exact NCT identifiers required")
    if len(values) != len(set(values)):
        raise ValueError("Duplicate requested identifiers")
    return sorted(values)


def is_retryable_read_error(error):
    return is_retryable_request_error(error, TRANSIENT_HTTP_STATUSES)


def _verified_failed_prefix(folder, ids):
    scope = {"kind": "exact_retained_publication_nct_ids", "requested_ids": ids}
    receipt, inventory, proof = verified_failure(
        folder, "clinicaltrials.gov", scope, ids
    )
    indexed = {}
    for entry, raw in inventory.values():
        url = entry.get("source_url")
        identity = (
            url[len(API) :] if isinstance(url, str) and url.startswith(API) else None
        )
        if identity not in ids or identity not in receipt["completed_ids"] + [
            receipt["failed_id"]
        ]:
            raise ValueError("Trial raw inventory outside completed/failed scope")
        validate_response_entry(entry, API + identity, identity + ".json")
        if entry.get("kind", "response") == "http_error":
            continue
        if (
            identity not in ids
            or entry["name"] != identity + ".json"
            or entry.get("source_url") != API + identity
            or entry.get("http", 200) != 200
        ):
            raise ValueError("Trial raw inventory differs from exact scope")
        indexed[identity] = (entry, raw)
    prefix = []
    for identity in receipt["completed_ids"]:
        if identity not in indexed:
            raise ValueError("Completed trial prefix lacks raw response")
        entry, raw = indexed[identity]
        row = project(strict_json(raw), identity)
        prefix.append((identity, entry, raw, row))
    return prefix, proof


def capture(ids, output, resume_from=None, *, opener=None, max_attempts=1, sleep=None):
    ids = validate_ids(ids)
    validate_attempts(max_attempts)
    output = Path(output)
    scope = {"kind": "exact_retained_publication_nct_ids", "requested_ids": ids}
    prefix, proof = [], None
    if resume_from is not None:
        if output.resolve().is_relative_to(Path(resume_from).resolve()):
            raise ValueError("Resume input and new output must be separate directories")
        prefix, proof = _verified_failed_prefix(Path(resume_from), ids)
    create_output(output)
    manifest = {
        "source": "clinicaltrials.gov",
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
        for identity, entry, raw, row in prefix:
            current = identity
            stored = write_verified(output, entry["name"], raw)
            manifest["files"].append(
                {**entry, **stored, "reused_from_failure_receipt": proof["sha256"]}
            )
            rows.append(row)
            completed.append(identity)
        for identity in ids[len(completed) :]:
            current = identity
            url = API + identity
            name = identity + ".json"
            raw, _, _, _ = read_response(
                Request(url, headers={"Accept": "application/json"}),
                manifest["request_attempts"],
                opener=opener or urlopen,
                max_attempts=max_attempts,
                sleep=sleep or time.sleep,
                retain=response_retainer(output, manifest, {"source_url": url}, name),
            )
            rows.append(project(strict_json(raw), identity))
            completed.append(identity)
        manifest["count"] = len(rows)
        return commit_generation(output, "studies.json", rows, manifest)
    except Exception as error:
        write_failure_receipt(
            output,
            source="clinicaltrials.gov",
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
    document = strict_json(args.ids_file.read_bytes())
    manifest = capture(
        document["nct_ids"],
        args.output,
        resume_from=args.resume_from,
        max_attempts=args.max_read_attempts,
    )
    print(json.dumps({"complete": manifest["complete"], "count": manifest["count"]}))


if __name__ == "__main__":
    main()
