"""Recover only the publication's own identifiers from retained PubMed chunks.

No network or native writes. Reference-list identifiers are deliberately excluded;
a PMCID identifies a retrieval candidate, not permission to archive its contents.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from scripts.publication_source_metadata_contract import reconstruct_metadata_rows


def normalize_doi(value):
    """Retained OA contract: resolver removal only; no DOI: or percent decoding."""
    if not isinstance(value, str):
        raise ValueError("DOI required")  # noqa: TRY004 - stable frozen-evidence ValueError contract
    value = re.sub(
        r"^https?://(?:dx\.)?doi\.org/", "", value.strip(), flags=re.IGNORECASE
    )
    if not re.fullmatch(r"10\.\d{4,9}/[^\s]+", value):
        raise ValueError("Invalid DOI")
    return value.lower()


def _node_list(value, label):
    if not isinstance(value, list) or any(
        not isinstance(node, dict) or not isinstance(node.get("Name"), str)
        for node in value
    ):
        raise ValueError("Malformed retained " + label)
    return value


def _unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate retained JSON key")
        result[key] = value
    return result


def identifiers(rows, pmid):
    """Read own ArticleIdList only, using the canonical strict chunk reader."""
    if not isinstance(pmid, str) or re.fullmatch(r"[1-9][0-9]*", pmid) is None:
        raise ValueError("Positive ASCII PMID text required")
    if not isinstance(rows, list) or any(
        not isinstance(row, dict)
        or not isinstance(row.get("[PMID]"), str)
        or re.fullmatch(r"[1-9][0-9]*", row["[PMID]"]) is None
        for row in rows
    ):
        raise ValueError("Exact retained PMID identities required")
    selected = [row for row in rows if row["[PMID]"] == pmid]
    if not selected:
        raise ValueError("Retained PMID missing")
    documents, entries, _ = reconstruct_metadata_rows(selected, "PMID")
    tree = _node_list(
        json.loads(documents[pmid], object_pairs_hook=_unique_json), "tree"
    )
    data = [node for node in tree if node["Name"] == "PubmedData"]
    if len(data) != 1:
        raise ValueError(
            "Exact PubmedData required; book/foreign adapters are not qualified"
        )
    children = _node_list(data[0].get("Value"), "PubmedData")
    lists = [node for node in children if node["Name"] == "ArticleIdList"]
    if len(lists) != 1:
        raise ValueError("Exact publication ArticleIdList required")
    values = {}
    for node in _node_list(lists[0].get("Value"), "ArticleIdList"):
        if node["Name"] != "ArticleId":
            continue
        attributes = _node_list(node.get("Attributes"), "ArticleId attributes")
        types = [
            attribute.get("Value")
            for attribute in attributes
            if attribute["Name"] == "IdType"
        ]
        value = node.get("Value")
        if (
            len(types) != 1
            or not isinstance(types[0], str)
            or not types[0]
            or types[0] != types[0].strip()
            or not isinstance(value, str)
            or not value
        ):
            raise ValueError("Ambiguous or malformed own ArticleId")
        values.setdefault(types[0], set()).add(value)
    if values.get("pubmed") != {pmid}:
        raise ValueError("Publication PMID mismatch")
    for kind in ("doi", "pmc"):
        if len(values.get(kind, set())) > 1:
            raise ValueError("Ambiguous publication identifier")
    doi = next(iter(values.get("doi", [])), None)
    pmcid = next(iter(values.get("pmc", [])), None)
    if pmcid is not None and re.fullmatch(r"PMC[1-9][0-9]*", pmcid) is None:
        raise ValueError("Invalid PMCID")
    return {
        "PMID": pmid,
        "DOI": normalize_doi(doi) if doi is not None else None,
        "PMCID": pmcid,
        "source_metadata_sha256": entries[0][1],
        "archiving_eligibility": "not_evaluated",
        "native_projection_applied": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--pmid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.rows.read_bytes()
    result = identifiers(json.loads(raw), args.pmid)
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print("PREPARED_LOCAL_ONLY; archive eligibility not evaluated")


if __name__ == "__main__":
    main()
