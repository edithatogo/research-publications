# SPDX-License-Identifier: Apache-2.0
"""Checkpoint anonymous exact-identifier Semantic Scholar metadata lookups."""

import argparse
import base64
import hashlib
import json
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
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
    for start in range(0, len(ids), 50):
        batch = ids[start : start + 50]
        scope = json.dumps({"ids": batch, "fields": FIELDS}, sort_keys=True).encode()
        path = args.output / (hashlib.sha256(scope).hexdigest() + ".json")
        if not path.exists():
            if args.replay_only:
                continue
            url = "https://api.semanticscholar.org/graph/v1/paper/batch?" + urlencode(
                {"fields": FIELDS}
            )
            request = Request(
                url,
                data=json.dumps({"ids": batch}).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "RIMS-publication-metadata/1.0",
                },
                method="POST",
            )
            try:
                requests += 1
                with urlopen(request, timeout=45) as response:
                    raw = response.read()
            except (HTTPError, OSError) as error:
                stopped = {
                    "status": getattr(error, "code", None),
                    "type": type(error).__name__,
                    "batchStart": start,
                }
                if isinstance(error, HTTPError):
                    stopped["retryAfter"] = error.headers.get("Retry-After")
                    stopped["bodyBase64"] = base64.b64encode(error.read()).decode()
                save(args.output / "stopped.json", stopped)
                break
            save(
                path,
                {
                    "scope": scope.decode(),
                    "observed": datetime.now(UTC).isoformat(),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "raw": base64.b64encode(raw).decode(),
                },
            )
            time.sleep(2)
        receipt = json.loads(path.read_bytes())
        raw = base64.b64decode(receipt["raw"], validate=True)
        assert (
            receipt["scope"] == scope.decode()
            and hashlib.sha256(raw).hexdigest() == receipt["sha256"]
        )
        papers = json.loads(raw)
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
    parser.add_argument(
        "--bootstrap",
        type=Path,
        help="Previously retained, exact-matched complete paper JSON",
    )
    collect(parser.parse_args())
