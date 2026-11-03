# SPDX-License-Identifier: Apache-2.0
"""Reconcile the accepted bibliography with exact Europe PMC and retained OpenAlex records."""

import argparse
import base64
import hashlib
import json
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from enrich_europe_pmc import EUROPE_PMC_BASE_URL, clean_doi, clean_pmid
from export_publication_register import key_hash


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    if path.exists() and path.read_bytes() == data:
        return
    temp = path.with_suffix(".tmp")
    temp.write_bytes(data)
    temp.replace(path)


def doi(value):
    return (clean_doi(value) or "").lower()


def openalex(paths):
    works = defaultdict(dict)
    chunks = defaultdict(list)
    for path in paths:
        for row in json.loads(path.read_bytes()):
            chunks[
                path.parent, row["[RequestedDOI]"], row["[RawResponseIndex]"]
            ].append(row)
    for (_, identifier, _), rows in chunks.items():
        rows.sort(key=lambda r: r["[RawChunkIndex]"])
        if rows[0]["[RawHTTPStatus]"] != 200:
            continue
        if [r["[RawChunkIndex]"] for r in rows] != list(
            range(rows[0]["[RawChunkCount]"])
        ):
            raise ValueError("Incomplete retained OpenAlex chunks")
        raw = base64.b64decode("".join(r["[RawPayloadBase64]"] for r in rows))
        if len(raw) != rows[0]["[RawByteCount]"]:
            raise ValueError("Retained OpenAlex byte-count mismatch")
        work = json.loads(raw)
        if doi(identifier) and doi(work.get("doi")) == doi(identifier):
            works[doi(identifier)][digest(raw)] = {
                "record": work,
                "observed": rows[0]["[RawAcquiredUTC]"],
                "sha256": digest(raw),
            }
    return works


def collect_openalex(rows, retained, directory, replay_only=False):
    """Anonymous exact-DOI filters, checkpointed in batches under the free allowance."""
    outcomes = {}
    identifiers = sorted({doi(r["DOI"]) for r in rows} - set(retained) - {""})
    for start in range(0, len(identifiers), 25):
        batch = identifiers[start : start + 25]
        # Filter delimiters in a DOI require individual resolution.
        safe = [d for d in batch if not any(c in d for c in "|,:")]
        if not safe:
            continue
        query = urlencode({"filter": "doi:" + "|".join(safe), "per_page": 100})
        path = directory / ("alex-" + digest(query.encode()) + ".json")
        cached = path.exists()
        if not cached and replay_only:
            continue
        if not cached:
            try:
                with urlopen(
                    "https://api.openalex.org/works?" + query, timeout=35
                ) as response:
                    raw = response.read()
                    budget = {
                        k.lower(): v
                        for k, v in response.headers.items()
                        if k.lower().startswith("x-ratelimit-")
                    }
                receipt = {
                    "query": query,
                    "raw": base64.b64encode(raw).decode(),
                    "sha256": digest(raw),
                    "observed": datetime.now(UTC).isoformat(),
                    "budget": budget,
                }
                save(path, receipt)
                time.sleep(0.2)
            except (HTTPError, OSError) as error:
                outcomes.update(
                    dict.fromkeys(
                        safe,
                        "deferred"
                        if getattr(error, "code", 0) in (401, 403, 429)
                        else "failed",
                    )
                )
                break
        receipt = json.loads(path.read_bytes())
        raw = base64.b64decode(receipt["raw"], validate=True)
        if receipt["query"] != query or digest(raw) != receipt["sha256"]:
            raise ValueError("OpenAlex checkpoint mismatch")
        data = json.loads(raw)
        works = data["results"]
        if len(works) != data["meta"]["count"] or any(
            doi(w.get("doi")) not in safe for w in works
        ):
            outcomes.update(dict.fromkeys(safe, "failed"))
            break
        for identifier in safe:
            outcomes[identifier] = "no match"
        for work in works:
            identifier = doi(work["doi"])
            retained[identifier][work["id"]] = {
                "record": work,
                "observed": receipt["observed"],
                "archive": path.name,
            }
            outcomes[identifier] = "fresh"
        if (
            not cached
            and float(receipt["budget"].get("x-ratelimit-remaining-usd", 0)) < 0.001
        ):
            break
    return outcomes


def field_paths(value, prefix=""):
    """Count each nested provider field once per publication, including array children."""
    if isinstance(value, dict):
        for key, child in value.items():
            name = prefix + "." + key if prefix else key
            if child not in (None, "", [], {}):
                yield name
            # OpenAlex encodes every abstract word as a dynamic dictionary key.
            if key != "abstract_inverted_index":
                yield from field_paths(child, name)
    elif isinstance(value, list):
        for member in value:
            yield from field_paths(member, prefix + "[]")


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    envelope = json.loads(args.canonical.read_bytes())
    rows = envelope["records"]
    keys = {r["CanonicalKey"] for r in rows}
    if (
        len(rows) != envelope["expected_canonical_count"]
        or len(keys) != len(rows)
        or key_hash(rows) != envelope["expected_key_sha256"]
    ):
        raise ValueError("Canonical identity mismatch")
    monthly = json.loads(args.monthly.read_bytes())
    if (
        not {r["CanonicalKey"] for r in monthly["records"]} <= keys
        or key_hash(monthly["records"]) != monthly["expected_key_sha256"]
    ):
        raise ValueError("Monthly identity mismatch")
    alex = openalex(args.openalex)
    alex_outcomes = collect_openalex(rows, alex, args.output, args.replay_only)
    pmids = sorted({p for r in rows if (p := clean_pmid(r["PMID"]))})
    epmc = {}
    failures = {}
    for start in range(0, len(pmids), 50):
        batch = pmids[start : start + 50]
        query = "SRC:MED AND (" + " OR ".join("EXT_ID:" + p for p in batch) + ")"
        path = args.output / (digest(query.encode()) + ".json")
        try:
            if args.replay_only and not path.exists():
                continue
            if not path.exists():
                url = (
                    EUROPE_PMC_BASE_URL
                    + "?"
                    + urlencode(
                        {
                            "query": query,
                            "format": "json",
                            "resultType": "core",
                            "pageSize": 100,
                        }
                    )
                )
                with urlopen(url, timeout=35) as response:
                    raw = response.read()
                parsed = json.loads(raw)
                if "resultList" not in parsed:
                    raise ValueError("Missing result list")
                save(
                    path,
                    {
                        "observed": datetime.now(UTC).isoformat(),
                        "query": query,
                        "sha256": digest(raw),
                        "raw": base64.b64encode(raw).decode(),
                    },
                )
                time.sleep(0.2)
            receipt = json.loads(path.read_bytes())
            raw = base64.b64decode(receipt["raw"])
            if receipt["query"] != query or digest(raw) != receipt["sha256"]:
                raise ValueError("Checkpoint mismatch")
            parsed = json.loads(raw)
            found = parsed["resultList"]["result"]
            if parsed["hitCount"] != len(found) or any(
                w.get("source") != "MED" or w.get("pmid") not in batch for w in found
            ):
                raise ValueError("Incomplete or unrelated results")
            for p in batch:
                epmc[p] = [
                    {"record": w, "observed": receipt["observed"], "archive": path.name}
                    for w in found
                    if w["pmid"] == p
                ]
        except (OSError, ValueError, KeyError) as error:
            failures.update(dict.fromkeys(batch, str(error)))
            break
    pubmed = json.loads(args.pubmed.read_bytes())["metadata_payloads"]
    observations = {}
    manifest = []
    counts = defaultdict(Counter)
    fields = defaultdict(Counter)
    for row in rows:
        p, d = clean_pmid(row["PMID"]), doi(row["DOI"])
        pubmed_ref = None
        if p in pubmed:
            payload = json.loads(pubmed[p])
            if any(
                part.get("Name") == "MedlineCitation"
                and any(
                    field.get("Name") == "PMID" and field.get("Value") == p
                    for field in part["Value"]
                )
                for part in payload
            ):
                pubmed_ref = "PubMed/" + p
                observations[pubmed_ref] = payload
        for source, identifier, versions in [
            ("Europe PMC", p, epmc.get(p, [])),
            ("OpenAlex", d, list(alex.get(d, {}).values())),
        ]:
            status = (
                alex_outcomes.get(identifier, "deferred")
                if source == "OpenAlex"
                else "deferred"
            )
            if not identifier:
                status = "missing identifier"
            elif source == "Europe PMC" and p in failures:
                status = "failed"
            elif versions:
                ids = {v["record"].get("id") for v in versions}
                conflict = any(
                    d and doi(v["record"].get("doi")) and doi(v["record"]["doi"]) != d
                    for v in versions
                )
                if source == "OpenAlex" and p:
                    for version in versions:
                        supplied = version["record"].get("ids", {}).get("pmid")
                        if supplied and supplied.rstrip("/").rsplit("/", 1)[-1] != p:
                            conflict = True
                conflict |= source == "Europe PMC" and len(versions) != 1
                status = (
                    "ambiguous"
                    if None in ids or len(ids) != 1 or conflict
                    else "matched"
                )
            elif source == "Europe PMC" and p in epmc:
                status = "no match"
            ref = source + "/" + str(identifier) if versions else None
            if ref:
                observations[ref] = versions
            if status == "matched":
                for field in {k for v in versions for k in field_paths(v["record"])}:
                    fields[source][field] += 1
            counts[source][status] += 1
            manifest.append(
                {
                    "key": row["CanonicalKey"],
                    "source": source,
                    "identifier": identifier,
                    "status": status,
                    "observation": ref,
                    "evidence_origin": (
                        "retained archive"
                        if source == "OpenAlex"
                        and versions
                        and identifier not in alex_outcomes
                        else "provider capture"
                    )
                    if versions
                    else None,
                    "retained_pubmed": pubmed_ref,
                }
            )
    save(
        args.output / "coverage.json",
        {
            "native_delivery": "pending guarded SharePoint read, flow run and isolated-model readback",
            "conditional_sources": {
                "Semantic Scholar": "source use, retention and display unqualified",
                "Lens": "access and terms unqualified",
                "Scopus": "institutional API entitlement unverified",
                "Dimensions": "organisational API entitlement unverified",
                "Web of Science": "institutional API entitlement unverified",
            },
            "canonical": len(rows),
            "monthly": len(monthly["records"]),
            "canonical_sha256": digest(args.canonical.read_bytes()),
            "monthly_sha256": digest(args.monthly.read_bytes()),
            "counts": counts,
            "field_presence": fields,
            "failures": failures,
            "manifest": manifest,
            "observations": observations,
        },
    )
    print(dict(counts))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("canonical", "monthly", "pubmed", "output"):
        parser.add_argument("--" + arg, required=True, type=Path)
    parser.add_argument("--openalex", nargs="*", type=Path, default=[])
    parser.add_argument(
        "--replay-only",
        action="store_true",
        help="Use verified checkpoints without provider requests",
    )
    run(parser.parse_args())
