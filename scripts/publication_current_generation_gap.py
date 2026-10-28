"""Reconcile retained PubMed XML coverage to a consumed typed commit offline.

No source acquisition or admission occurs. A key match does not certify metadata
parity on overlapping records, provider freshness, affiliation or native storage.
"""

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def _keys(values):
    if (
        not isinstance(values, list)
        or any(
            not isinstance(value, str) or re.fullmatch(r"[1-9][0-9]*", value) is None
            for value in values
        )
        or len(set(values)) != len(values)
    ):
        raise ValueError("Unique positive ASCII PMID strings required")
    return set(values)


def reconcile(manifest, readback, typed_commit, documents):
    """Validate complete raw bytes/identities before reporting missing typed keys."""
    if not all(
        isinstance(value, dict)
        for value in (manifest, readback, typed_commit, documents)
    ):
        raise ValueError("Structured frozen evidence required")
    if (
        manifest.get("format") != "rims-pubmed-full-hedge-commit-v1"
        or manifest.get("source") != "pubmed"
        or manifest.get("complete") is not True
    ):
        raise ValueError("Complete current PubMed raw manifest required")
    current = _keys(manifest.get("pmids"))
    if not current:
        raise ValueError("Nonempty retained PubMed generation required")
    if type(manifest.get("count")) is not int or manifest["count"] != len(current):
        raise ValueError("Current raw manifest count mismatch")
    if readback.get("status") != "PASS_CACHED_PUBMED_XML_IDENTITIES" or readback.get(
        "records"
    ) != len(current):
        raise ValueError("Complete retained raw readback required")
    files, proofs = manifest.get("files"), readback.get("files")
    if not isinstance(files, list) or not isinstance(proofs, list) or not files:
        raise ValueError("Nonempty raw file inventory required")
    indexed = {}
    for proof in proofs:
        if (
            not isinstance(proof, dict)
            or not isinstance(proof.get("file"), str)
            or proof["file"] != Path(proof["file"]).name
            or proof["file"] in indexed
        ):
            raise ValueError("Unique retained file readback required")
        indexed[proof["file"]] = proof
    observed, consumed_names = [], set()
    for entry in files:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("file"), str)
            or entry.get("saved_readback_equal") is not True
        ):
            raise ValueError("Exact retained raw file entry required")
        name = Path(entry["file"]).name
        if name in consumed_names or name not in documents or name not in indexed:
            raise ValueError("Raw file missing or duplicated")
        consumed_names.add(name)
        content, proof = documents[name], indexed[name]
        if (
            not isinstance(content, bytes)
            or type(proof.get("bytes")) is not int
            or proof["bytes"] != len(content)
            or hashlib.sha256(content).hexdigest() != proof.get("sha256")
        ):
            raise ValueError("Retained XML byte proof mismatch")
        root = ET.fromstring(content)
        records = root.findall("PubmedArticle") + root.findall("PubmedBookArticle")
        ids = []
        for record in records:
            node = (
                record.find("MedlineCitation/PMID")
                if record.tag == "PubmedArticle"
                else record.find("BookDocument/PMID")
            )
            ids.append(node.text if node is not None else None)
        _keys(ids)
        if (
            ids != entry.get("ids")
            or type(proof.get("records")) is not int
            or len(ids) != proof["records"]
        ):
            raise ValueError("Exact raw XML file identity/order proof mismatch")
        observed.extend(ids)
    if (
        consumed_names != set(documents)
        or consumed_names != set(indexed)
        or _keys(observed) != current
    ):
        raise ValueError("Complete raw file coverage mismatch")
    if (
        type(typed_commit.get("SchemaVersion")) is not int
        or typed_commit.get("SchemaVersion") != 1
        or typed_commit.get("Status") != "committed"
    ):
        raise ValueError("Consumed committed typed manifest required")
    sources = typed_commit.get("Sources")
    selected = (
        [
            source
            for source in sources
            if isinstance(source, dict) and source.get("Source") == "PubMed"
        ]
        if isinstance(sources, list)
        else []
    )
    if len(selected) != 1:
        raise ValueError("Exactly one consumed typed PubMed source required")
    typed = _keys(selected[0].get("ExpectedKeys"))
    if type(selected[0].get("ExpectedRecords")) is not int or selected[0][
        "ExpectedRecords"
    ] != len(typed):
        raise ValueError("Consumed typed source count mismatch")
    return {
        "kind": "publication_current_generation_metadata_gap_v1",
        "status": "PASS_FROZEN_COVERAGE_ONLY",
        "raw_records": len(current),
        "raw_files_verified": len(consumed_names),
        "consumed_typed_records": len(typed),
        "current_keys_missing_from_typed_generation": sorted(current - typed),
        "typed_keys_absent_from_current_raw": sorted(typed - current),
        "overlapping_records": len(current & typed),
        "overlapping_metadata_parity_accepted": False,
        "typed_metadata_for_new_keys_accepted": False,
        "new_provider_requests": 0,
        "native_writes": 0,
        "input_value_sha256": {
            name: hashlib.sha256(
                json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            for name, value in [
                ("manifest", manifest),
                ("readback", readback),
                ("typed_commit", typed_commit),
            ]
        },
    }
