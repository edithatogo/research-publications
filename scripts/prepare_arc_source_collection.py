"""Prepare manual Microsoft ARC full-source capture; no service operations.

Complete native HTTP JSON values precede validation. Two bounded serial reads
must agree page by page and in their global award-ID set. No opportunity admission.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

try:
    from scripts.grants_arc_api import API_BASE, MAX_TOTAL_AWARDS
    from scripts.patch_clinicaltrials_read_retries import definition_sha256, strict_json
    from scripts.prepare_qgip_source_collection import build as qualified_base
    from scripts.prepare_qgip_source_collection import compose, gate
except ImportError:
    from grants_arc_api import API_BASE, MAX_TOTAL_AWARDS
    from patch_clinicaltrials_read_retries import definition_sha256, strict_json
    from prepare_qgip_source_collection import build as qualified_base
    from prepare_qgip_source_collection import compose, gate

NAME = "CHHHS RIMS | Data spaces | ARC award source collection"
PAGE_SIZE = 500
MAX_PAGES = (MAX_TOTAL_AWARDS + PAGE_SIZE - 1) // PAGE_SIZE


def build(site: str, archive_parent: str, reference: dict) -> dict:
    result = qualified_base(site, archive_parent, reference)
    p = result["properties"]
    p["displayName"] = NAME
    definition = p["definition"]
    a = {}
    definition["actions"] = a

    def sp(operation, parameters, previous=""):
        return {
            "type": "OpenApiConnection",
            "runAfter": {previous: ["Succeeded"]} if previous else {},
            "inputs": {
                "host": {
                    "apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
                    "connectionName": "shared_sharepointonline",
                    "operationId": operation,
                },
                "parameters": {"dataset": site, **parameters},
                "retryPolicy": {"type": "none"},
            },
        }

    a["Parse_source_catalogue"] = {
        "type": "ParseJson",
        "runAfter": {},
        "inputs": {
            "content": "@json(triggerBody()?['CatalogueJson'])",
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["source_id", "enabled"],
                    "properties": {
                        "source_id": {"type": "string"},
                        "enabled": {"type": "boolean"},
                    },
                },
            },
        },
    }
    a["Selected_source_policy"] = {
        "type": "Query",
        "runAfter": {"Parse_source_catalogue": ["Succeeded"]},
        "inputs": {
            "from": "@body('Parse_source_catalogue')",
            "where": "@equals(item()?['source_id'],'arc-awards-api')",
        },
    }
    a["Guard_source_policy"] = gate(
        "and(equals(length(body('Selected_source_policy')),1),equals(first(body('Selected_source_policy'))?['enabled'],true),equals(first(body('Selected_source_policy'))?['record_kind'],'awarded_grant_context'),equals(first(body('Selected_source_policy'))?['reconciliation']?['admission'],'context_only'))",
        "Selected_source_policy",
    )
    previous = "Guard_source_policy"
    for name, kind, value in [
        ("Files", "array", []),
        ("Page", "integer", 1),
        ("Total", "integer", -1),
        ("Pages", "integer", -1),
        ("Rows", "integer", 0),
        ("Keys", "array", []),
        ("FirstKeys", "array", []),
        ("PageFailed", "boolean", False),
    ]:
        key = "Initialize_" + name
        a[key] = {
            "type": "InitializeVariable",
            "runAfter": {previous: ["Succeeded"]},
            "inputs": {"variables": [{"name": name, "type": kind, "value": value}]},
        }
        previous = key
    a["Run_folder"] = compose(
        "@concat('" + archive_parent + "/arc-source-',workflow()?['run']?['name'])",
        previous,
    )
    a["Create_exclusive_folder"] = sp(
        "HttpRequest",
        {
            "parameters/method": "POST",
            "parameters/uri": "_api/web/folders",
            "parameters/headers": {
                "Accept": "application/json;odata=nometadata",
                "Content-Type": "application/json;odata=nometadata",
            },
            "parameters/body": {
                "ServerRelativeUrl": "@concat('"
                + urlsplit(site).path
                + "',outputs('Run_folder'))"
            },
        },
        "Run_folder",
    )
    a["Guard_exclusive_folder"] = gate(
        "and(equals(outputs('Create_exclusive_folder')?['statusCode'],201),equals(int(body('Create_exclusive_folder')?['ItemCount']),0))",
        "Create_exclusive_folder",
    )
    loops = {}
    previous = ""
    for name, value in [("Page", 1), ("Rows", 0), ("Keys", [])]:
        key = "Reset_" + name
        loops[key] = {
            "type": "SetVariable",
            "runAfter": {previous: ["Succeeded"]} if previous else {},
            "inputs": {"name": name, "value": value},
        }
        previous = key
    pages = {}
    pages["HTTP_Page"] = {
        "type": "Http",
        "runAfter": {},
        "inputs": {
            "uri": API_BASE,
            "method": "GET",
            "queries": {"page[number]": "@variables('Page')", "page[size]": PAGE_SIZE},
            "headers": {"Accept": "application/json"},
            "retryPolicy": {"type": "none"},
        },
        "limit": {"timeout": "PT30S"},
    }
    pages["Raw_Page"] = {
        "type": "Compose",
        "runAfter": {"HTTP_Page": ["Succeeded", "Failed", "TimedOut"]},
        "inputs": {
            "request": {
                "method": "GET",
                "uri": API_BASE,
                "queries": {
                    "page[number]": "@variables('Page')",
                    "page[size]": PAGE_SIZE,
                },
            },
            "pass": "@items('Two_complete_reads')",
            "captured_utc": "@utcNow()",
            "response": "@outputs('HTTP_Page')",
            "fidelity": "complete_native_HTTP_JSON_values; original_transport_bytes_not_certified",
        },
    }
    filename = "@concat('pass-',string(items('Two_complete_reads')),'-page-',string(variables('Page')),'.json')"
    pages["Save_Page"] = sp(
        "CreateFile",
        {
            "folderPath": "@outputs('Run_folder')",
            "name": filename,
            "body": "@base64ToBinary(base64(string(outputs('Raw_Page'))))",
        },
        "Raw_Page",
    )
    pages["Read_Page"] = sp(
        "GetFileContentByPath",
        {
            "path": "@concat(outputs('Run_folder'),'/'," + filename[1:] + ")",
            "inferContentType": False,
        },
        "Save_Page",
    )
    pages["Verify_Page"] = gate(
        "equals(base64(string(outputs('Raw_Page'))),body('Read_Page')?['$content'])",
        "Read_Page",
    )
    pages["Record_Page"] = {
        "type": "AppendToArrayVariable",
        "runAfter": {"Verify_Page": ["Succeeded"]},
        "inputs": {
            "name": "Files",
            "value": {
                "name": filename,
                "verification": "exact_base64_stored_content_readback",
            },
        },
    }
    pages["Guard_HTTP"] = gate(
        "equals(outputs('HTTP_Page')?['statusCode'],200)", "Record_Page"
    )
    meta_fields = [
        "requested-page-number",
        "requested-page-size",
        "actual-page-size",
        "total-pages",
        "total-size",
    ]
    row_schema = {
        "type": "object",
        "required": ["id", "attributes"],
        "properties": {
            "id": {"type": "string", "minLength": 1},
            "attributes": {
                "type": "object",
                "required": ["code"],
                "properties": {"code": {"type": "string", "minLength": 1}},
            },
        },
    }
    schema = {
        "type": "object",
        "required": ["data", "meta"],
        "properties": {
            "meta": {
                "type": "object",
                "required": meta_fields,
                "properties": {
                    k: {"type": "integer", "minimum": 0} for k in meta_fields
                },
            },
            "data": {"type": "array", "items": row_schema},
        },
    }
    pages["Parse_Page"] = {
        "type": "ParseJson",
        "runAfter": {"Guard_HTTP": ["Succeeded"]},
        "inputs": {"content": "@body('HTTP_Page')", "schema": schema},
    }
    meta = "body('Parse_Page')?['meta']"
    data = "body('Parse_Page')?['data']"
    pages["Guard_exact_page"] = gate(
        "and(equals("
        + meta
        + "?['requested-page-number'],variables('Page')),equals("
        + meta
        + "?['requested-page-size'],500),lessOrEquals("
        + meta
        + "?['total-size'],"
        + str(MAX_TOTAL_AWARDS)
        + "),equals("
        + meta
        + "?['total-pages'],max(1,div(add("
        + meta
        + "?['total-size'],499),500))),lessOrEquals("
        + meta
        + "?['total-pages'],"
        + str(MAX_PAGES)
        + "),equals("
        + meta
        + "?['actual-page-size'],length("
        + data
        + ")),equals(length("
        + data
        + "),min(500,max(0,sub("
        + meta
        + "?['total-size'],mul(sub(variables('Page'),1),500))))),or(equals(variables('Total'),-1),and(equals("
        + meta
        + "?['total-size'],variables('Total')),equals("
        + meta
        + "?['total-pages'],variables('Pages')))))",
        "Parse_Page",
    )
    pages["Set_total"] = {
        "type": "SetVariable",
        "runAfter": {"Guard_exact_page": ["Succeeded"]},
        "inputs": {"name": "Total", "value": "@" + meta + "?['total-size']"},
    }
    pages["Set_pages"] = {
        "type": "SetVariable",
        "runAfter": {"Set_total": ["Succeeded"]},
        "inputs": {"name": "Pages", "value": "@" + meta + "?['total-pages']"},
    }
    pages["Invalid_keys"] = {
        "type": "Query",
        "runAfter": {"Set_pages": ["Succeeded"]},
        "inputs": {
            "from": "@" + data,
            "where": "@or(empty(trim(item()?['id'])),not(equals(item()?['id'],trim(item()?['id']))),empty(trim(item()?['attributes']?['code'])),not(equals(item()?['attributes']?['code'],trim(item()?['attributes']?['code']))))",
        },
    }
    pages["Guard_keys"] = gate("empty(body('Invalid_keys'))", "Invalid_keys")
    pages["Page_keys"] = {
        "type": "Select",
        "runAfter": {"Guard_keys": ["Succeeded"]},
        "inputs": {"from": "@" + data, "select": {"id": "@item()?['id']"}},
    }
    pages["Merged_keys"] = compose(
        "@union(variables('Keys'),body('Page_keys'))", "Page_keys"
    )
    pages["Guard_no_duplicate_keys"] = gate(
        "equals(length(outputs('Merged_keys')),add(length(variables('Keys')),length(body('Page_keys'))))",
        "Merged_keys",
    )
    pages["Set_keys"] = {
        "type": "SetVariable",
        "runAfter": {"Guard_no_duplicate_keys": ["Succeeded"]},
        "inputs": {"name": "Keys", "value": "@outputs('Merged_keys')"},
    }
    pages["Increment_rows"] = {
        "type": "IncrementVariable",
        "runAfter": {"Set_keys": ["Succeeded"]},
        "inputs": {"name": "Rows", "value": "@length(" + data + ")"},
    }
    first = {}
    first["Read_first_pass_page"] = sp(
        "GetFileContentByPath",
        {
            "path": "@concat(outputs('Run_folder'),'/pass-1-page-',string(variables('Page')),'.json')",
            "inferContentType": False,
        },
    )
    first["First_page"] = compose(
        "@json(base64ToString(body('Read_first_pass_page')?['$content']))",
        "Read_first_pass_page",
    )
    first["Guard_full_page_replay"] = gate(
        "and(equals(outputs('First_page')?['response']?['statusCode'],200),equals(sort(outputs('First_page')?['response']?['body']?['data'],'id'),sort(body('Parse_Page')?['data'],'id')))",
        "First_page",
    )
    pages["Compare_passes"] = {
        "type": "If",
        "runAfter": {"Increment_rows": ["Succeeded"]},
        "expression": "@equals(items('Two_complete_reads'),2)",
        "actions": first,
        "else": {"actions": {}},
    }
    pages["Increment_page"] = {
        "type": "IncrementVariable",
        "runAfter": {"Compare_passes": ["Succeeded"]},
        "inputs": {"name": "Page", "value": 1},
    }
    pages["Latch_http_failure"] = {
        "type": "SetVariable",
        "runAfter": {"HTTP_Page": ["Failed", "TimedOut", "Skipped"]},
        "inputs": {"name": "PageFailed", "value": True},
    }
    pages["Latch_page_failure"] = {
        "type": "SetVariable",
        "runAfter": {"Increment_page": ["Failed", "TimedOut", "Skipped"]},
        "inputs": {"name": "PageFailed", "value": True},
    }
    loops["Guard_page_entry"] = gate("not(variables('PageFailed'))", previous)
    loops["Read_pages"] = {
        "type": "Until",
        "runAfter": {"Guard_page_entry": ["Succeeded"]},
        "expression": "@or(variables('PageFailed'),greater(variables('Page'),variables('Pages')))",
        "limit": {"count": MAX_PAGES, "timeout": "PT1H"},
        "actions": pages,
    }
    loops["Guard_complete_set"] = gate(
        "and(not(variables('PageFailed')),equals(variables('Rows'),variables('Total')),equals(length(variables('Keys')),variables('Total')))",
        "Read_pages",
    )
    loops["Compare_key_sets"] = {
        "type": "If",
        "runAfter": {"Guard_complete_set": ["Succeeded"]},
        "expression": "@equals(items('Two_complete_reads'),1)",
        "actions": {
            "Keep_first_keys": {
                "type": "SetVariable",
                "runAfter": {},
                "inputs": {"name": "FirstKeys", "value": "@variables('Keys')"},
            }
        },
        "else": {
            "actions": {
                "Guard_equal_keys": gate(
                    "equals(sort(variables('FirstKeys'),'id'),sort(variables('Keys'),'id'))",
                    "",
                )
            }
        },
    }
    loops["Latch_set_failure"] = {
        "type": "SetVariable",
        "runAfter": {"Compare_key_sets": ["Failed", "TimedOut", "Skipped"]},
        "inputs": {"name": "PageFailed", "value": True},
    }
    a["Two_complete_reads"] = {
        "type": "Foreach",
        "foreach": "@createArray(1,2)",
        "runAfter": {"Guard_exclusive_folder": ["Succeeded"]},
        "runtimeConfiguration": {"concurrency": {"repetitions": 1}},
        "actions": loops,
    }
    a["Guard_manifest_coverage"] = gate(
        "and(not(variables('PageFailed')),equals(length(variables('Files')),mul(2,variables('Pages'))))",
        "Two_complete_reads",
    )
    a["Manifest"] = compose(
        {
            "format": "rims-arc-source-commit-v1",
            "source_id": "arc-awards-api",
            "record_kind": "awards_only",
            "source_api": API_BASE,
            "run": "@workflow()?['run']?['name']",
            "committed_utc": "@utcNow()",
            "source_total": "@variables('Total')",
            "page_size": PAGE_SIZE,
            "page_count": "@variables('Pages')",
            "complete_reads": 2,
            "files": "@variables('Files')",
            "canonical_opportunity_admission": False,
            "candidate_filter_applied": False,
            "source_identity_semantics": "observed_award_keys_only; lifecycle_not_proven",
            "replay_scope": "full data rows per page, sorted by id, and complete global id set; page membership drift rejects commit",
            "fidelity": "complete_native_HTTP_JSON_values; stored_serialization_readback_exact; original_transport_bytes_not_certified",
            "schedule": "manual_only",
        },
        "Guard_manifest_coverage",
    )
    a["Commit_manifest"] = sp(
        "CreateFile",
        {
            "folderPath": "@outputs('Run_folder')",
            "name": "manifest.json",
            "body": "@base64ToBinary(base64(string(outputs('Manifest'))))",
        },
        "Manifest",
    )
    a["Read_manifest"] = sp(
        "GetFileContentByPath",
        {
            "path": "@concat(outputs('Run_folder'),'/manifest.json')",
            "inferContentType": False,
        },
        "Commit_manifest",
    )
    a["Verify_manifest"] = gate(
        "equals(base64(string(outputs('Manifest'))),body('Read_manifest')?['$content'])",
        "Read_manifest",
    )
    return result


def with_configured_catalogue(document, catalogue, *, expected_definition_sha256=None):
    """Bind maintained ARC configuration for input-free operator runs."""
    if not isinstance(catalogue, list) or any(
        not isinstance(row, dict) for row in catalogue
    ):
        raise ValueError("Explicit catalogue rows required")
    if (
        definition_sha256(document["properties"]["definition"])
        != expected_definition_sha256
    ):
        raise ValueError("Definition drift; exact current preimage required")
    selected = [row for row in catalogue if row.get("source_id") == "arc-awards-api"]
    if len(selected) != 1:
        raise ValueError("Exactly one maintained ARC source configuration required")
    record = selected[0]
    endpoint = urlsplit(record.get("api_url", ""))
    result = copy.deepcopy(document)
    p = result["properties"]
    a = p["definition"]["actions"]
    if (
        p.get("state") != "Stopped"
        or p.get("isManaged") is True
        or record.get("enabled") is not True
        or record.get("record_kind") != "awarded_grant_context"
        or record.get("reconciliation", {}).get("admission") != "context_only"
        or endpoint.scheme != "https"
        or endpoint.hostname != "dataportal.arc.gov.au"
        or endpoint.path != "/NCGP/API/grants"
        or endpoint.username
        or endpoint.password
        or endpoint.port is not None
        or endpoint.fragment
        or a.get("Manifest", {}).get("inputs", {}).get("source_id") != "arc-awards-api"
        or any(
            k in a.get("Manifest", {}).get("inputs", {})
            for k in ("source_policy_sha256", "source_policy_snapshot")
        )
        or a.get("Parse_source_catalogue", {}).get("inputs", {}).get("content")
        != "@json(triggerBody()?['CatalogueJson'])"
        or "manual" not in p["definition"]["triggers"]
    ):
        raise ValueError(
            "Stopped accepted ARC operator graph and enabled qualified source required"
        )
    a["Parse_source_catalogue"]["inputs"]["content"] = [copy.deepcopy(record)]
    p["definition"]["triggers"]["manual"]["inputs"]["schema"] = {
        "type": "object",
        "properties": {},
    }
    a["Manifest"]["inputs"]["source_policy_sha256"] = hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    a["Manifest"]["inputs"]["source_policy_snapshot"] = (
        "@first(body('Selected_source_policy'))"
    )
    return result


def with_weekly_updates(document, catalogue):
    """Retained name; no recurrence proposal is qualified by this packet."""
    raise ValueError("Weekly proposal unavailable in this manual-only source packet")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ["site", "archive-parent"]:
        parser.add_argument("--" + arg, required=True)
    for arg in ["reference", "output"]:
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "private/ops"
    if not args.output.resolve().is_relative_to(root.resolve()):
        raise ValueError("Private output required")
    candidate = build(
        args.site, args.archive_parent, strict_json(args.reference.read_bytes())
    )
    serialized = json.dumps(candidate, indent=2, allow_nan=False)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(serialized)
    print(
        "Prepared Stopped manual ARC full-source collector; native qualification required"
    )


if __name__ == "__main__":
    main()
