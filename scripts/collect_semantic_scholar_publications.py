# SPDX-License-Identifier: Apache-2.0
"""Checkpoint anonymous exact-identifier Semantic Scholar metadata lookups."""

import argparse
import base64
import hashlib
import json
import time
from collections import Counter
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from enrich_europe_pmc import clean_doi, clean_pmid
from export_publication_register import key_hash
from publication_source_pass import field_paths

FIELDS = "paperId,corpusId,externalIds,url,title,abstract,venue,publicationVenue,year,referenceCount,citationCount,influentialCitationCount,isOpenAccess,openAccessPdf,fieldsOfStudy,s2FieldsOfStudy,publicationTypes,publicationDate,journal,authors"


def save(path, data):
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True).encode()
    if path.exists() and path.read_bytes() == raw:
        return
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(raw)
    temporary.replace(path)


def lookup_id(row):
    doi = clean_doi(row.get("DOI"))
    if doi:
        return "DOI:" + doi.lower()
    pmid = clean_pmid(row.get("PMID"))
    return "PMID:" + pmid if pmid else None


def matches(identifier, paper):
    ids = paper.get("externalIds") or {}
    if identifier.startswith("DOI:"):
        return str(ids.get("DOI", "")).lower() == identifier[4:]
    return str(ids.get("PubMed", "")) == identifier[5:]


def cooldown_seconds(value, fallback):
    """Never retry before a server-provided interval or HTTP date."""
    if value:
        try:
            return max(float(value), fallback)
        except ValueError:
            try:
                return max(
                    parsedate_to_datetime(value).timestamp() - time.time(), fallback
                )
            except (TypeError, ValueError, OverflowError):
                pass
    return fallback


def wait_for_cooldown(seconds):
    deadline = time.monotonic() + seconds
    while (remaining := deadline - time.monotonic()) > 0:
        time.sleep(min(remaining, 60))


def collect(args):
    args.output.mkdir(parents=True, exist_ok=True)
    canonical = json.loads(args.canonical.read_bytes())
    rows = canonical["records"]
    assert (
        len(rows)
        == len({r["CanonicalKey"] for r in rows})
        == canonical["expected_canonical_count"]
    )
    assert key_hash(rows) == canonical["expected_key_sha256"]
    ids = sorted({identifier for row in rows if (identifier := lookup_id(row))})
    observations = {}
    if args.bootstrap:
        paper = json.loads(args.bootstrap.read_bytes())
        doi = clean_doi((paper.get("externalIds") or {}).get("DOI"))
        identifier = "DOI:" + doi.lower() if doi else None
        if not paper.get("paperId") or not identifier or not matches(identifier, paper):
            raise ValueError("Bootstrap requires an exact DOI-matched paper")
        if identifier in ids:
            observations[identifier] = {
                "record": paper,
                "observed": datetime.fromtimestamp(
                    args.bootstrap.stat().st_mtime, UTC
                ).isoformat(),
                "archive": str(args.bootstrap.resolve()),
            }
            ids.remove(identifier)
    no_matches = set()
    stopped = None
    requests = 0
    batch_size = 1 if args.transport == "single" else 50
    next_request = 0
    for start in range(0, len(ids), batch_size):
        batch = ids[start : start + batch_size]
        scope_data = {"ids": batch, "fields": FIELDS}
        if args.transport == "single":
            scope_data["transport"] = "single"
        scope = json.dumps(scope_data, sort_keys=True).encode()
        path = args.output / (hashlib.sha256(scope).hexdigest() + ".json")
        if not path.exists():
            if args.replay_only:
                continue
            endpoint = "batch" if batch_size == 50 else quote(batch[0], safe=":")
            url = (
                "https://api.semanticscholar.org/graph/v1/paper/"
                + endpoint
                + "?"
                + urlencode({"fields": FIELDS})
            )
            request = Request(
                url,
                data=json.dumps({"ids": batch}).encode() if batch_size == 50 else None,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "RIMS-publication-metadata/1.0",
                },
                method="POST" if batch_size == 50 else "GET",
            )
            status = 200
            for attempt in range(args.max_throttle_retries + 1):
                wait_for_cooldown(max(0, next_request - time.monotonic()))
                try:
                    requests += 1
                    with urlopen(request, timeout=45) as response:
                        raw = response.read()
                        status = response.status
                    stopped = None
                    break
                except (HTTPError, OSError) as error:
                    status = getattr(error, "code", None)
                    stopped = {
                        "status": status,
                        "type": type(error).__name__,
                        "batchStart": start,
                    }
                    if isinstance(error, HTTPError):
                        raw = error.read()
                        stopped.update(
                            retryAfter=error.headers.get("Retry-After"),
                            bodyBase64=base64.b64encode(raw).decode(),
                        )
                        if status == 404 and batch_size == 1:
                            body = json.loads(raw)
                            if (
                                isinstance(body, dict)
                                and isinstance(body.get("error"), str)
                                and "not found" in body["error"].lower()
                            ):
                                stopped = None
                                break
                    save(args.output / "stopped.json", stopped)
                    if status != 429 or attempt == args.max_throttle_retries:
                        break
                    delay = cooldown_seconds(
                        stopped.get("retryAfter"), 60 * (2**attempt)
                    )
                    with (args.output / "throttle-events.jsonl").open("a") as log:
                        log.write(
                            json.dumps(
                                {
                                    **stopped,
                                    "delay": delay,
                                    "observed": datetime.now(UTC).isoformat(),
                                }
                            )
                            + "\n"
                        )
                    print(
                        json.dumps(
                            {
                                "throttled": True,
                                "cooldownSeconds": delay,
                                "attempt": attempt + 1,
                            }
                        ),
                        flush=True,
                    )
                    wait_for_cooldown(delay)
                finally:
                    next_request = time.monotonic() + args.interval
            else:
                raise RuntimeError("Unexpected request loop termination")
            if stopped and status != 200:
                break
            stopped = None
            save(
                path,
                {
                    "scope": scope.decode(),
                    "observed": datetime.now(UTC).isoformat(),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "raw": base64.b64encode(raw).decode(),
                    "httpStatus": status,
                },
            )
        receipt = json.loads(path.read_bytes())
        raw = base64.b64decode(receipt["raw"], validate=True)
        assert (
            receipt["scope"] == scope.decode()
            and hashlib.sha256(raw).hexdigest() == receipt["sha256"]
        )
        papers = json.loads(raw)
        if batch_size == 1:
            papers = [None] if receipt.get("httpStatus") == 404 else [papers]
        if not isinstance(papers, list) or len(papers) != len(batch):
            raise ValueError("Incomplete batch response")
        for identifier, paper in zip(batch, papers, strict=True):
            if paper is None:
                no_matches.add(identifier)
            elif isinstance(paper, dict) and paper.get("paperId"):
                observations[identifier] = {
                    "record": paper,
                    "observed": receipt["observed"],
                    "archive": path.name,
                }
            else:
                raise ValueError("Invalid paper response")
        if (start + batch_size) % 25 == 0:
            progress = {
                "completedLookups": len(observations) + len(no_matches),
                "requestsThisRun": requests,
                "totalLookups": len(ids) + bool(args.bootstrap),
            }
            save(args.output / "progress.json", progress)
            print(json.dumps(progress), flush=True)
    manifest = []
    counts = Counter()
    fields = Counter()
    for row in rows:
        identifier = lookup_id(row)
        observation = observations.get(identifier)
        status = "deferred"
        if identifier is None:
            status = "missing identifier"
        elif identifier in no_matches:
            status = "no match"
        elif observation:
            status = (
                "matched" if matches(identifier, observation["record"]) else "ambiguous"
            )
            other_pmid = observation["record"].get("externalIds", {}).get("PubMed")
            if (
                other_pmid
                and clean_pmid(row.get("PMID"))
                and str(other_pmid) != clean_pmid(row["PMID"])
            ):
                status = "ambiguous"
        counts[status] += 1
        if status == "matched":
            fields.update(set(field_paths(observation["record"])))
        manifest.append(
            {
                "key": row["CanonicalKey"],
                "source": "Semantic Scholar",
                "identifier": identifier,
                "status": status,
                "observation": identifier if observation else None,
            }
        )
    result = {
        "canonical": len(rows),
        "canonical_key_sha256": canonical["expected_key_sha256"],
        "requestedFields": FIELDS.split(","),
        "counts": counts,
        "field_presence": fields,
        "manifest": manifest,
        "observations": observations,
        "coverage": "complete for the frozen exact-identifier lookup set"
        if not counts["deferred"]
        else "partial; deferred lookups remain",
        "stopped": stopped,
        "lastProviderStop": json.loads((args.output / "stopped.json").read_bytes())
        if counts["deferred"] and (args.output / "stopped.json").exists()
        else None,
    }
    save(args.output / "coverage.json", result)
    print(
        json.dumps(
            {
                "requestsThisRun": requests,
                "counts": counts,
                "fieldPaths": len(fields),
                "stopped": stopped,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--replay-only", action="store_true")
    parser.add_argument("--transport", choices=["batch", "single"], default="batch")
    parser.add_argument("--interval", type=float, default=2)
    parser.add_argument("--max-throttle-retries", type=int, choices=range(3), default=0)
    parser.add_argument(
        "--bootstrap",
        type=Path,
        help="Previously retained, exact-matched complete paper JSON",
    )
    options = parser.parse_args()
    if options.interval < 2:
        parser.error("Use an interval of at least two seconds")
    collect(options)
