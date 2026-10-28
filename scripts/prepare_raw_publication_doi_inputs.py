"""Join verified raw publication checkpoints into related-source acquisition.

Preserves the existing legacy DOI input and reads immutable producer receipts;
no publication admission, model refresh, or register writes are introduced.
"""

import argparse
import base64
import copy
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

PRODUCERS = {
    "pubmed": {
        "prefix": "pubmed-acquisition-complete-",
        "format": "rims-pubmed-full-hedge-commit-v1",
        "folder": "pubmed-acquisition-",
    },
    "dora_publications": {
        "prefix": "dora-publications-complete-",
        "format": "rims-dora-publication-raw-commit-v1",
        "folder": "dora-publications-",
    },
}

SHAREPOINT_API = "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"
MANIFEST_FIELDS = frozenset(
    {
        "raw_publication_producer_inputs",
        "invalid_raw_publication_doi_values",
        "related_doi_input_strategy",
        "raw_publication_input_preimage_sha256",
    }
)
SNAPSHOT_FIELDS = frozenset(
    {
        "raw_publication_producer_inputs",
        "invalid_raw_publication_doi_values",
    }
)


def _text(value):
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and not any(ord(c) < 32 for c in value)
    )


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("Duplicate JSON key in pinned evidence")
        out[key] = value
    return out


def _json(raw):
    if not isinstance(raw, bytes):
        raise ValueError("Exact source bytes required")  # noqa: TRY004 - stable frozen-evidence ValueError contract

    def reject_constant(_token):
        raise ValueError("Finite JSON required")

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Valid pinned UTF8 JSON required") from error


def _canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _checkpoint(name, proof, parent):
    if not isinstance(proof, dict):
        raise ValueError("Complete frozen checkpoint proof required")  # noqa: TRY004 - stable frozen-evidence ValueError contract
    raw = proof.get("raw_bytes")
    digest = proof.get("sha256")
    if (
        not isinstance(raw, bytes)
        or not isinstance(digest, str)
        or not re.fullmatch("[a-f0-9]{64}", digest)
        or hashlib.sha256(raw).hexdigest() != digest
        or type(proof.get("length")) is not int
        or len(raw) != proof["length"]
    ):
        raise ValueError("Checkpoint byte/hash/length drift")
    if (
        not isinstance(proof.get("file_id"), str)
        or not re.fullmatch(
            r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}", proof["file_id"]
        )
        or not _text(proof.get("etag"))
        or proof["etag"] == "*"
    ):
        raise ValueError("Exact native file identity/ETag proof required")
    marker = _json(raw)
    config = PRODUCERS[name]
    key = "pmids" if name == "pubmed" else "keys"
    if not isinstance(marker, dict):
        raise ValueError("Structured complete checkpoint required")  # noqa: TRY004 - stable frozen-evidence ValueError contract
    keys = marker.get(key)
    values = marker.get("publication_doi_values")
    run = marker.get("run")
    if (
        marker.get("format") != config["format"]
        or marker.get("source") != ("pubmed" if name == "pubmed" else "dora")
        or marker.get("complete") is not True
        or marker.get("downstream_selection_applied") is not False
        or not isinstance(run, str)
        or not re.fullmatch("[A-Za-z0-9_-]{1,128}", run)
        or not isinstance(keys, list)
        or any(
            not isinstance(k, str) or not re.fullmatch("[1-9][0-9]*", k) for k in keys
        )
        or len(set(keys)) != len(keys)
        or type(marker.get("count")) is not int
        or marker["count"] != len(keys)
        or not isinstance(values, list)
        or any(not isinstance(v, str) or any(ord(c) < 32 for c in v) for v in values)
        or not _text(marker.get("doi_provenance"))
        or not isinstance(marker.get("scope_sha256"), str)
        or not re.fullmatch("[a-f0-9]{64}", marker["scope_sha256"])
        or marker.get("archive_folder") != parent + "/" + config["folder"] + run
        or proof.get("name") != config["prefix"] + run + ".json"
        or any(k in marker for k in ("error", "errors", "partial", "truncated"))
    ):
        raise ValueError(
            "Malformed, incomplete, filtered or identity-mismatched producer checkpoint"
        )
    return marker


def _normalized(value, resolvers):
    result = value.strip().lower()
    if resolvers:
        for prefix in (
            "doi:",
            "http://doi.org/",
            "https://doi.org/",
            "http://dx.doi.org/",
            "https://dx.doi.org/",
        ):
            if result.startswith(prefix):
                return result[len(prefix) :].strip()
    return result


def with_raw_producer_dois(
    document,
    archive_parent,
    producers=("pubmed",),
    *,
    preimage_bytes=None,
    expected_preimage_sha256=None,
    checkpoints=None,
):
    """Prepare a proposal bound to exact current document and frozen marker bytes.

    No latest-marker lookup or service operation. Native adoption must independently
    qualify the generated connector read/byte guards and recheck the preimage.
    """
    if (
        not isinstance(preimage_bytes, bytes)
        or not isinstance(expected_preimage_sha256, str)
        or hashlib.sha256(preimage_bytes).hexdigest() != expected_preimage_sha256
        or _canonical(_json(preimage_bytes)) != _canonical(document)
    ):
        raise ValueError("Exact current preimage bytes/hash required")
    if (
        not isinstance(document, dict)
        or not isinstance(document.get("properties"), dict)
        or not isinstance(document["properties"].get("definition"), dict)
        or not isinstance(document["properties"]["definition"].get("actions"), dict)
    ):
        raise ValueError("Existing native source document required")  # noqa: TRY004 - stable frozen-evidence ValueError contract
    d = copy.deepcopy(document)
    p = d["properties"]
    a = p["definition"]["actions"]
    manifest_node = a.get("Manifest")
    if not isinstance(manifest_node, dict) or not isinstance(
        manifest_node.get("inputs"), dict
    ):
        raise ValueError("Existing manifest preimage required")  # noqa: TRY004 - stable frozen-evidence ValueError contract
    source = manifest_node["inputs"].get("source")
    if (
        p.get("state") != "Stopped"
        or source not in ("crossref", "datacite")
        or any(
            k in a["Manifest"]["inputs"]
            for k in {"recovery", "extension"} | MANIFEST_FIELDS
        )
        or not isinstance(producers, (tuple, list))
        or not producers
        or any(not isinstance(name, str) or name not in PRODUCERS for name in producers)
        or len(set(producers)) != len(producers)
    ):
        raise ValueError(
            "Stopped normal related-source collector and supported raw producers required"
        )
    if (
        not _text(archive_parent)
        or not archive_parent.startswith("/Documents/")
        or archive_parent.endswith("/")
        or any(c in archive_parent for c in "'?#%\\")
        or ".." in archive_parent.split("/")
        or "//" in archive_parent
    ):
        raise ValueError("Qualified existing archive parent required")
    key = "All_dois" if source == "datacite" else "All_DOIs"
    if not isinstance(a.get(key), dict) or not isinstance(a[key].get("runAfter"), dict):
        raise ValueError("Existing DOI union preimage required")  # noqa: TRY004 - stable frozen-evidence ValueError contract
    original = a[key].get("inputs")
    if not isinstance(original, str) or not original.startswith("@union("):
        raise ValueError("Existing legacy DOI union required")
    getter = a.get("Get_publication_dois")
    if (
        not isinstance(getter, dict)
        or not isinstance(getter.get("inputs"), dict)
        or not isinstance(getter["inputs"].get("parameters"), dict)
    ):
        raise ValueError("Existing publication-source preimage required")  # noqa: TRY004 - stable frozen-evidence ValueError contract
    host = getter["inputs"].get("host")
    if not isinstance(host, dict):
        raise ValueError("Existing SharePoint host binding required")  # noqa: TRY004 - stable frozen-evidence ValueError contract
    alias_keys = set(host).intersection({"connectionName", "connectionReferenceName"})
    if len(alias_keys) != 1:
        raise ValueError("Exactly one existing SharePoint connection alias required")
    alias_key = next(iter(alias_keys))
    alias = host[alias_key]
    refs = p.get("connectionReferences")
    reference = (
        refs.get(alias) if isinstance(refs, dict) and isinstance(alias, str) else None
    )
    if (
        getter.get("type") != "OpenApiConnection"
        or set(host) != {"apiId", "operationId", alias_key}
        or host.get("apiId") != SHAREPOINT_API
        or host.get("operationId") != "GetItems"
        or not _text(alias)
        or not isinstance(reference, dict)
        or reference.get("id") != SHAREPOINT_API
        or reference.get("source") not in ("Embedded", "Invoker")
        or not _text(reference.get("connectionName"))
        or (
            "connectionReferenceLogicalName" in reference
            and not _text(reference["connectionReferenceLogicalName"])
        )
        or not _text(getter["inputs"]["parameters"].get("table"))
    ):
        raise ValueError(
            "Exact existing GetItems alias/reference/source binding required"
        )
    site = getter["inputs"]["parameters"].get("dataset")
    if not isinstance(site, str):
        raise ValueError("Exact existing SharePoint site text required")  # noqa: TRY004 - stable frozen-evidence ValueError contract
    parsed = urlsplit(site)
    if (
        not _text(site)
        or parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".sharepoint.com")
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port not in (None, 443)
        or any(c in site for c in "'\\")
        or ".." in parsed.path.split("/")
        or site.endswith("/")
        or re.search("%(?:25|2f|5c|2e)", parsed.path, re.IGNORECASE)
    ):
        raise ValueError("Qualified existing SharePoint source required")
    if not isinstance(checkpoints, dict) or set(checkpoints) != set(producers):
        raise ValueError("Exact complete frozen producer set required")
    markers = {
        name: _checkpoint(name, checkpoints[name], archive_parent) for name in producers
    }
    reserved = {
        "Pinned_valid_raw_publication_dois",
        "Normalize_raw_publication_dois",
        "Canonical_raw_publication_dois",
        "Valid_raw_publication_dois",
        "Invalid_raw_publication_dois",
    }
    reserved.update(
        prefix + name
        for prefix in (
            "Find_raw_",
            "Require_raw_",
            "Read_raw_",
            "Recheck_raw_",
            "Guard_raw_bytes_",
            "Parse_raw_",
            "Guard_raw_",
        )
        for name in producers
    )
    if reserved.intersection(a):
        raise ValueError(
            "Raw input action already present; reconcile rather than replay transformation"
        )
    if "Doi_source_snapshot" in a:
        snapshot = a["Doi_source_snapshot"]
        if (
            not isinstance(snapshot, dict)
            or not isinstance(snapshot.get("inputs"), dict)
            or SNAPSHOT_FIELDS.intersection(snapshot["inputs"])
        ):
            raise ValueError("Existing DOI snapshot preimage drift")

    def sp(op, params, after):
        selected_host = copy.deepcopy(host)
        selected_host["operationId"] = op
        return {
            "type": "OpenApiConnection",
            "runAfter": after,
            "inputs": {
                "host": selected_host,
                "parameters": {"dataset": site, **params},
                "retryPolicy": {"type": "none"},
            },
        }

    def compose(value, after):
        return {"type": "Compose", "runAfter": after, "inputs": value}

    def gate(condition, after):
        return compose(
            "@if(" + condition + ",true,json('RAW_PUBLICATION_CHECKPOINT_REJECTED'))",
            after,
        )

    def literal(value):
        return "'" + str(value).replace("'", "''") + "'"

    previous = copy.deepcopy(a[key]["runAfter"])
    values = []
    snapshots = {}
    for name in producers:
        config = PRODUCERS[name]
        proof = checkpoints[name]
        find = "Find_raw_" + name
        read = "Read_raw_" + name
        parse = "Parse_raw_" + name
        guard = "Guard_raw_" + name
        params = {
            "parameters/method": "GET",
            "parameters/uri": "_api/web/GetFileById('"
            + proof["file_id"]
            + "')?$select=UniqueId,Name,Length,ETag,ServerRelativeUrl",
            "parameters/headers": {"Accept": "application/json;odata=nometadata"},
        }

        def identity(action, proof=proof):
            return (
                "and(equals(toLower(body('"
                + action
                + "')?['UniqueId']),"
                + literal(proof["file_id"].lower())
                + "),equals(body('"
                + action
                + "')?['Name'],"
                + literal(proof["name"])
                + "),equals(int(body('"
                + action
                + "')?['Length']),"
                + str(proof["length"])
                + "),equals(body('"
                + action
                + "')?['ETag'],"
                + literal(proof["etag"])
                + "),equals(body('"
                + action
                + "')?['ServerRelativeUrl'],"
                + literal(parsed.path + archive_parent + "/" + proof["name"])
                + "))"
            )

        a[find] = sp("HttpRequest", copy.deepcopy(params), previous)
        a["Require_raw_" + name] = gate(identity(find), {find: ["Succeeded"]})
        a[read] = sp(
            "GetFileContentByPath",
            {"path": archive_parent + "/" + proof["name"], "inferContentType": False},
            {"Require_raw_" + name: ["Succeeded"]},
        )
        recheck = "Recheck_raw_" + name
        byteguard = "Guard_raw_bytes_" + name
        a[recheck] = sp("HttpRequest", copy.deepcopy(params), {read: ["Succeeded"]})
        a[byteguard] = gate(
            "and("
            + identity(recheck)
            + ",equals(body('"
            + read
            + "')?['$content'],"
            + literal(base64.b64encode(proof["raw_bytes"]).decode())
            + "))",
            {recheck: ["Succeeded"]},
        )
        schema = {
            "type": "object",
            "required": [
                "format",
                "source",
                "complete",
                "run",
                "archive_folder",
                "count",
                "publication_doi_values",
            ],
            "properties": {
                "format": {"enum": [config["format"]]},
                "source": {"enum": ["pubmed" if name == "pubmed" else "dora"]},
                "complete": {"enum": [True]},
                "run": {"type": "string", "minLength": 1},
                "archive_folder": {"type": "string"},
                "count": {"type": "integer", "minimum": 0},
                "publication_doi_values": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        }
        keys = "pmids" if name == "pubmed" else "keys"
        schema["required"].extend([keys, "doi_provenance"])
        schema["properties"][keys] = {"type": "array", "items": {"type": "string"}}
        schema["properties"]["doi_provenance"] = {"type": "string", "minLength": 1}
        a[parse] = {
            "type": "ParseJson",
            "runAfter": {byteguard: ["Succeeded"]},
            "inputs": {
                "content": "@json(base64ToString(body('" + read + "')?['$content']))",
                "schema": schema,
            },
        }
        keys = "pmids" if name == "pubmed" else "keys"
        condition = (
            "and(equals(body('"
            + find
            + "')?['Name'],concat('"
            + config["prefix"]
            + "',body('"
            + parse
            + "')?['run'],'.json')),equals(body('"
            + parse
            + "')?['archive_folder'],concat('"
            + archive_parent
            + "/"
            + config["folder"]
            + "',body('"
            + parse
            + "')?['run'])),equals(body('"
            + parse
            + "')?['count'],length(body('"
            + parse
            + "')?['"
            + keys
            + "'])),equals(length(union(body('"
            + parse
            + "')?['"
            + keys
            + "'],body('"
            + parse
            + "')?['"
            + keys
            + "'])),body('"
            + parse
            + "')?['count']),not(empty(body('"
            + parse
            + "')?['doi_provenance'])))"
        )
        a[guard] = gate(condition, {parse: ["Succeeded"]})
        previous = {guard: ["Succeeded"]}
        values.append("body('" + parse + "')?['publication_doi_values']")
        snapshots[name] = {
            "checkpoint_file": proof["name"],
            "checkpoint_sha256": proof["sha256"],
            "file_id": proof["file_id"],
            "etag": proof["etag"],
            "bytes": proof["length"],
            "checkpoint": "@body('" + parse + "')",
        }
    approved = []
    for marker in markers.values():
        for raw in marker["publication_doi_values"]:
            value = _normalized(raw, "dora_publications" in producers)
            if (
                re.fullmatch(r"10\.[0-9]{4,9}/[^\s\x00-\x1f]+", value)
                and value not in approved
            ):
                approved.append(value)
    a["Pinned_valid_raw_publication_dois"] = compose(approved, previous)
    combined = values[0] if len(values) == 1 else "union(" + ",".join(values) + ")"
    a["Normalize_raw_publication_dois"] = {
        "type": "Select",
        "runAfter": {"Pinned_valid_raw_publication_dois": ["Succeeded"]},
        "inputs": {"from": "@" + combined, "select": "@toLower(trim(item()))"},
    }
    input_action = "Normalize_raw_publication_dois"
    if "dora_publications" in producers:
        canonical = "item()"
        for prefix in (
            "doi:",
            "http://doi.org/",
            "https://doi.org/",
            "http://dx.doi.org/",
            "https://dx.doi.org/",
        ):
            canonical = (
                "if(startsWith(item(),'"
                + prefix
                + "'),trim(substring(item(),"
                + str(len(prefix))
                + ")),"
                + canonical
                + ")"
            )
        input_action = "Canonical_raw_publication_dois"
        a[input_action] = {
            "type": "Select",
            "runAfter": {"Normalize_raw_publication_dois": ["Succeeded"]},
            "inputs": {
                "from": "@body('Normalize_raw_publication_dois')",
                "select": "@" + canonical,
            },
        }
    shape = "contains(outputs('Pinned_valid_raw_publication_dois'),item())"
    a["Valid_raw_publication_dois"] = {
        "type": "Query",
        "runAfter": {input_action: ["Succeeded"]},
        "inputs": {"from": "@body('" + input_action + "')", "where": "@" + shape},
    }
    a["Invalid_raw_publication_dois"] = {
        "type": "Query",
        "runAfter": {"Valid_raw_publication_dois": ["Succeeded"]},
        "inputs": {
            "from": "@body('" + input_action + "')",
            "where": "@and(not(empty(item())),not(" + shape + "))",
        },
    }
    a[key]["inputs"] = "@union(" + original[1:] + ",body('Valid_raw_publication_dois'))"
    a[key]["runAfter"] = {"Invalid_raw_publication_dois": ["Succeeded"]}
    manifest = a["Manifest"]["inputs"]
    manifest["raw_publication_producer_inputs"] = snapshots
    manifest["invalid_raw_publication_doi_values"] = (
        "@body('Invalid_raw_publication_dois')"
    )
    manifest["related_doi_input_strategy"] = (
        "verified_raw_producer_union_with_preserved_legacy_input"
    )
    manifest["raw_publication_input_preimage_sha256"] = expected_preimage_sha256
    if "Doi_source_snapshot" in a:
        a["Doi_source_snapshot"]["inputs"]["raw_publication_producer_inputs"] = (
            snapshots
        )
        a["Doi_source_snapshot"]["inputs"]["invalid_raw_publication_doi_values"] = (
            "@body('Invalid_raw_publication_dois')"
        )
    return d


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("document", "checkpoints", "output"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--preimage-sha256", required=True)
    parser.add_argument("--archive-parent", required=True)
    args = parser.parse_args()
    raw = args.document.read_bytes()
    proofs = _json(args.checkpoints.read_bytes())
    if not isinstance(proofs, dict):
        raise ValueError("Explicit frozen checkpoint set required")  # noqa: TRY004 - stable frozen-evidence ValueError contract
    for proof in proofs.values():
        if not isinstance(proof, dict) or not _text(proof.get("path")):
            raise ValueError("Frozen checkpoint path required")
        proof["raw_bytes"] = Path(proof["path"]).read_bytes()
    proposal = with_raw_producer_dois(
        _json(raw),
        args.archive_parent,
        tuple(proofs),
        preimage_bytes=raw,
        expected_preimage_sha256=args.preimage_sha256,
        checkpoints=proofs,
    )
    result = {
        "format": "rims-raw-publication-input-plan-v1",
        "preimage_path": str(args.document.resolve()),
        "preimage_sha256": args.preimage_sha256,
        "native_acceptance": False,
        "document": proposal,
    }
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print("PREPARED_LOCAL_ONLY; frozen producer proposal; no native operation")


if __name__ == "__main__":
    main()
