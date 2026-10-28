"""Prepare a manual Microsoft QGIP raw-source collector, initially Stopped.

No service operations. Reuses a qualified Embedded SharePoint reference and an
existing archive parent. Complete native HTTP JSON values are retained before
validation; original transport byte identity is not implied by JSON serialization.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

try:
    from scripts.grants_qld_qgip_api import (
        API_BASE,
        INDEX_RESOURCE_ID,
        PACKAGE_ID,
        PACKAGE_NAME,
        RESOURCE_ID,
        SOURCE_ID,
    )
except ImportError:
    from grants_qld_qgip_api import (
        API_BASE,
        INDEX_RESOURCE_ID,
        PACKAGE_ID,
        PACKAGE_NAME,
        RESOURCE_ID,
        SOURCE_ID,
    )

NAME = "CHHHS RIMS | Data spaces | QGIP source collection"


def compose(value, previous=""):
    return {
        "type": "Compose",
        "inputs": value,
        "runAfter": {previous: ["Succeeded"]} if previous else {},
    }


def gate(expression, previous):
    # A failure stops its dependent chain, including inside Until/Foreach.
    # Native Terminate is not supported inside those loop containers.
    return compose(
        "@if(" + expression + ",true,json('QGIP_SOURCE_GUARD_FAILED'))", previous
    )


def capture_failed_http(actions, stage, source, flag, filename, save):
    """Build a diagnostic branch; no HTTP/storage operation is executed."""
    raw = "Raw_failure_" + stage
    mark = "Mark_failure_" + stage
    actions[raw] = {
        "type": "Compose",
        "runAfter": {stage: ["Failed", "TimedOut"]},
        "inputs": {
            "kind": "rims-source-http-failure-v1",
            "source": source,
            "stage": stage,
            "response": "@outputs('" + stage + "')",
            "body_content": "@outputs('" + stage + "')?['body']",
            "content_state": "@if(equals(outputs('"
            + stage
            + "')?['body'],null),'unavailable','available')",
            "captured_utc": "@utcNow()",
            "accepted": False,
            "source_valid": False,
            "fidelity": "available_native_HTTP_outputs; original_transport_bytes_not_certified",
        },
    }
    actions[mark] = {
        "type": "SetVariable",
        "runAfter": {raw: ["Succeeded"]},
        "inputs": {"name": flag, "value": True},
    }
    return save(
        actions, "failure_" + stage, filename, "string(outputs('" + raw + "'))", mark
    )


def build(site: str, archive_parent: str, reference: dict) -> dict:
    if (
        not isinstance(site, str)
        or not isinstance(archive_parent, str)
        or not isinstance(reference, dict)
    ):
        raise ValueError("Explicit site/archive/reference values required")  # noqa: TRY004 - retained validation ValueError contract
    parsed = urlsplit(site)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".sharepoint.com")
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or site.endswith("/")
        or any(ord(c) < 33 for c in site)
        or parsed.port not in (None, 443)
        or any(c in site for c in "'\\")
        or any(segment in (".", "..") for segment in parsed.path.split("/"))
        or re.search(r"%(?:25|2e|2f|5c)", parsed.path, re.IGNORECASE)
    ):
        raise ValueError("Qualified existing SharePoint site URL required")
    if (
        not archive_parent.startswith("/Documents/")
        or archive_parent.endswith("/")
        or any(c in archive_parent for c in "'?#%\\")
        or any(segment in (".", "..") for segment in archive_parent.split("/"))
        or "//" in archive_parent
        or any(ord(c) < 32 for c in archive_parent)
    ):
        raise ValueError("Qualified existing Documents archive parent required")
    if (
        reference.get("source") != "Embedded"
        or reference.get("id")
        != "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"
        or not isinstance(reference.get("connectionReferenceLogicalName"), str)
        or not re.fullmatch(
            "[A-Za-z0-9_]+", reference["connectionReferenceLogicalName"]
        )
        or not isinstance(reference.get("connectionName"), str)
        or not reference["connectionName"]
        or reference["connectionName"] != reference["connectionName"].strip()
        or any(ord(c) < 32 for c in reference["connectionName"])
    ):
        raise ValueError("Qualified existing Embedded SharePoint reference required")
    # Preserve the supplied reference and source mode, including diagnostic metadata.
    ref = copy.deepcopy(reference)

    def sp(operation, parameters, previous):
        return {
            "type": "OpenApiConnection",
            "runAfter": {previous: ["Succeeded"]},
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

    def save(actions, key, filename, content, previous):
        actions["Save_" + key] = sp(
            "CreateFile",
            {
                "folderPath": "@outputs('Run_folder')",
                "name": filename,
                "body": "@base64ToBinary(base64(" + content + "))",
            },
            previous,
        )
        path = (
            "@concat(outputs('Run_folder'),'/',"
            + (filename[1:] if filename.startswith("@") else "'" + filename + "'")
            + ")"
        )
        actions["Read_" + key] = sp(
            "GetFileContentByPath",
            {"path": path, "inferContentType": False},
            "Save_" + key,
        )
        actions["Verify_" + key] = gate(
            "equals(base64(" + content + "),body('Read_" + key + "')?['$content'])",
            "Read_" + key,
        )
        actions["Record_" + key] = {
            "type": "AppendToArrayVariable",
            "runAfter": {"Verify_" + key: ["Succeeded"]},
            "inputs": {
                "name": "Files",
                "value": {
                    "name": filename,
                    "verification": "exact_base64_stored_content_readback",
                },
            },
        }
        return "Record_" + key

    def capture(actions, key, api_action, queries, previous, filename=None):
        actions["HTTP_" + key] = {
            "type": "Http",
            "runAfter": {previous: ["Succeeded"]},
            "inputs": {
                "uri": API_BASE + api_action,
                "method": "GET",
                "queries": queries,
                "headers": {"Accept": "application/json"},
                "retryPolicy": {"type": "none"},
            },
        }
        actions["Raw_" + key] = {
            "type": "Compose",
            "runAfter": {"HTTP_" + key: ["Succeeded", "Failed", "TimedOut"]},
            "inputs": {
                "request": {
                    "method": "GET",
                    "uri": API_BASE + api_action,
                    "queries": queries,
                },
                "captured_utc": "@utcNow()",
                "response": "@outputs('HTTP_" + key + "')",
                "fidelity": "complete_native_HTTP_JSON_values; original_transport_bytes_not_certified",
            },
        }
        last = save(
            actions,
            key,
            filename or key + ".json",
            "string(outputs('Raw_" + key + "'))",
            "Raw_" + key,
        )
        actions["Guard_" + key] = gate(
            "and(equals(outputs('HTTP_"
            + key
            + "')?['statusCode'],200),equals(body('HTTP_"
            + key
            + "')?['success'],true))",
            last,
        )
        return "Guard_" + key

    a = {}
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
            "where": "@equals(item()?['source_id'],'" + SOURCE_ID + "')",
        },
    }
    a["Guard_source_policy"] = gate(
        "and(equals(length(body('Selected_source_policy')),1),equals(first(body('Selected_source_policy'))?['enabled'],true),equals(first(body('Selected_source_policy'))?['record_kind'],'opportunity_candidate'),equals(first(body('Selected_source_policy'))?['reconciliation']?['admission'],'candidate_only'),equals(first(body('Selected_source_policy'))?['source_resource_id'],'"
        + RESOURCE_ID
        + "'))",
        "Selected_source_policy",
    )
    previous = "Guard_source_policy"
    for name, kind, value in [
        ("Files", "array", []),
        ("Offset", "integer", 0),
        ("Total", "integer", -1),
        ("Records", "array", []),
        ("FirstRecords", "array", []),
    ]:
        key = "Initialize_" + name
        a[key] = {
            "type": "InitializeVariable",
            "runAfter": {previous: ["Succeeded"]},
            "inputs": {"variables": [{"name": name, "type": kind, "value": value}]},
        }
        previous = key
    a["Run_folder"] = compose(
        "@concat('" + archive_parent + "/qgip-source-',workflow()?['run']?['name'])",
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
                + parsed.path
                + "',outputs('Run_folder'))"
            },
        },
        "Run_folder",
    )
    a["Guard_exclusive_folder"] = gate(
        "and(equals(outputs('Create_exclusive_folder')?['statusCode'],201),equals(int(body('Create_exclusive_folder')?['ItemCount']),0))",
        "Create_exclusive_folder",
    )
    metadata = [
        (
            "Index",
            "datastore_search",
            {"resource_id": INDEX_RESOURCE_ID, "limit": 100, "offset": 0},
        ),
        ("Package", "package_show", {"id": PACKAGE_NAME}),
        ("Resource", "resource_show", {"id": RESOURCE_ID}),
        ("Schema", "datastore_info", {"id": RESOURCE_ID}),
    ]
    previous = "Guard_exclusive_folder"
    for name, action, queries in metadata:
        previous = capture(a, name + "_before", action, queries, previous)
    a["QH_index_pointer"] = {
        "type": "Query",
        "runAfter": {previous: ["Succeeded"]},
        "inputs": {
            "from": "@body('HTTP_Index_before')?['result']?['records']",
            "where": "@equals(item()?['Agency'],'QH')",
        },
    }
    a["Parse_source_schema"] = {
        "type": "ParseJson",
        "runAfter": {"QH_index_pointer": ["Succeeded"]},
        "inputs": {
            "content": "@body('HTTP_Schema_before')?['result']?['fields']",
            "schema": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["id", "type"],
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "type": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
    }
    a["Source_schema_keys"] = {
        "type": "Select",
        "runAfter": {"Parse_source_schema": ["Succeeded"]},
        "inputs": {
            "from": "@body('Parse_source_schema')",
            "select": {"id": "@item()?['id']"},
        },
    }
    a["Required_source_schema"] = {
        "type": "Query",
        "runAfter": {"Source_schema_keys": ["Succeeded"]},
        "inputs": {
            "from": "@body('Parse_source_schema')",
            "where": "@and(contains(createArray('Service ID','Status','Assistance type1','Assistance type2','Assistance type3'),item()?['id']),equals(item()?['type'],'text'))",
        },
    }
    a["Guard_source_metadata"] = gate(
        "and(equals(length(body('Required_source_schema')),5),equals(length(union(body('Source_schema_keys'),body('Source_schema_keys'))),length(body('Parse_source_schema'))),equals(body('HTTP_Index_before')?['result']?['total_was_estimated'],false),equals(body('HTTP_Index_before')?['result']?['total'],length(body('HTTP_Index_before')?['result']?['records'])),equals(length(body('QH_index_pointer')),1),equals(first(body('QH_index_pointer'))?['Resource'],'"
        + RESOURCE_ID
        + "'),equals(body('HTTP_Package_before')?['result']?['id'],'"
        + PACKAGE_ID
        + "'),equals(body('HTTP_Package_before')?['result']?['name'],'"
        + PACKAGE_NAME
        + "'),equals(body('HTTP_Package_before')?['result']?['license_id'],'CC-BY-3.0'),equals(body('HTTP_Resource_before')?['result']?['id'],'"
        + RESOURCE_ID
        + "'),equals(body('HTTP_Resource_before')?['result']?['package_id'],'"
        + PACKAGE_ID
        + "'))",
        "Required_source_schema",
    )

    loop = {}
    previous = ""
    for name, value in [("Offset", 0), ("Total", -1), ("Records", [])]:
        key = "Reset_" + name
        loop[key] = {
            "type": "SetVariable",
            "inputs": {"name": name, "value": value},
            "runAfter": {previous: ["Succeeded"]} if previous else {},
        }
        previous = key
    pages = {}
    # Each raw page is stored before parsing/coverage/identity guards.
    last = capture(
        pages,
        "Page",
        "datastore_search",
        {"resource_id": RESOURCE_ID, "limit": 100, "offset": "@variables('Offset')"},
        "",
        filename="@concat('pass-',string(items('Two_complete_reads')),'-offset-',string(variables('Offset')),'.json')",
    )
    # First loop action has no dependency on an action outside its own scope.
    pages["HTTP_Page"]["runAfter"] = {}
    pages["Parse_page"] = {
        "type": "ParseJson",
        "runAfter": {last: ["Succeeded"]},
        "inputs": {
            "content": "@body('HTTP_Page')?['result']",
            "schema": {
                "type": "object",
                "required": ["records", "total", "offset", "total_was_estimated"],
                "properties": {
                    "total": {"type": "integer", "minimum": 0},
                    "offset": {"type": "integer", "minimum": 0},
                    "total_was_estimated": {"enum": [False]},
                    "records": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["Service ID"],
                            "properties": {
                                "Service ID": {"type": "string", "minLength": 1}
                            },
                        },
                    },
                },
            },
        },
    }
    page = "body('Parse_page')"
    pages["Guard_page_coverage"] = gate(
        "and(equals("
        + page
        + "?['offset'],variables('Offset')),lessOrEquals("
        + page
        + "?['total'],1000),or(equals(variables('Total'),-1),equals("
        + page
        + "?['total'],variables('Total'))),equals(length("
        + page
        + "?['records']),min(100,max(0,sub("
        + page
        + "?['total'],variables('Offset'))))))",
        "Parse_page",
    )
    pages["Set_total"] = {
        "type": "SetVariable",
        "runAfter": {"Guard_page_coverage": ["Succeeded"]},
        "inputs": {"name": "Total", "value": "@" + page + "?['total']"},
    }
    pages["Merged_records"] = compose(
        "@union(variables('Records'),body('Parse_page')?['records'])", "Set_total"
    )
    pages["Set_records"] = {
        "type": "SetVariable",
        "runAfter": {"Merged_records": ["Succeeded"]},
        "inputs": {"name": "Records", "value": "@outputs('Merged_records')"},
    }
    pages["Increment_offset"] = {
        "type": "IncrementVariable",
        "runAfter": {"Set_records": ["Succeeded"]},
        "inputs": {"name": "Offset", "value": 100},
    }
    loop["Pages"] = {
        "type": "Until",
        "runAfter": {previous: ["Succeeded"]},
        "expression": "@greaterOrEquals(variables('Offset'),variables('Total'))",
        "limit": {"count": 10, "timeout": "PT10M"},
        "actions": pages,
    }
    loop["Service_keys"] = {
        "type": "Select",
        "runAfter": {"Pages": ["Succeeded"]},
        "inputs": {
            "from": "@variables('Records')",
            "select": {"key": "@item()?['Service ID']"},
        },
    }
    loop["Invalid_keys"] = {
        "type": "Query",
        "runAfter": {"Service_keys": ["Succeeded"]},
        "inputs": {
            "from": "@variables('Records')",
            "where": "@or(equals(trim(item()?['Service ID']),''),not(equals(item()?['Service ID'],trim(item()?['Service ID']))))",
        },
    }
    loop["Guard_complete_keys"] = gate(
        "and(equals(length(variables('Records')),variables('Total')),equals(length(union(body('Service_keys'),body('Service_keys'))),variables('Total')),empty(body('Invalid_keys')))",
        "Invalid_keys",
    )
    loop["Compare_complete_reads"] = {
        "type": "If",
        "runAfter": {"Guard_complete_keys": ["Succeeded"]},
        "expression": "@equals(items('Two_complete_reads'),1)",
        "actions": {
            "Keep_first_records": {
                "type": "SetVariable",
                "runAfter": {},
                "inputs": {"name": "FirstRecords", "value": "@variables('Records')"},
            }
        },
        "else": {
            "actions": {
                "Guard_equal_records": gate(
                    "equals(sort(variables('FirstRecords'),'Service ID'),sort(variables('Records'),'Service ID'))",
                    "",
                )
            }
        },
    }
    a["Two_complete_reads"] = {
        "type": "Foreach",
        "foreach": "@createArray(1,2)",
        "runAfter": {"Guard_source_metadata": ["Succeeded"]},
        "runtimeConfiguration": {"concurrency": {"repetitions": 1}},
        "actions": loop,
    }
    previous = "Two_complete_reads"
    for name, action, queries in metadata:
        previous = capture(a, name + "_after", action, queries, previous)
    # Preserve full bodies regardless; accept only stable source identity/schema.
    a["Guard_stable_metadata"] = gate(
        "and(equals(body('HTTP_Schema_before')?['result']?['fields'],body('HTTP_Schema_after')?['result']?['fields']),equals(body('HTTP_Resource_before')?['result']?['id'],body('HTTP_Resource_after')?['result']?['id']),equals(body('HTTP_Resource_before')?['result']?['package_id'],body('HTTP_Resource_after')?['result']?['package_id']),equals(body('HTTP_Resource_before')?['result']?['last_modified'],body('HTTP_Resource_after')?['result']?['last_modified']),equals(body('HTTP_Resource_before')?['result']?['hash'],body('HTTP_Resource_after')?['result']?['hash']),equals(body('HTTP_Package_before')?['result']?['id'],body('HTTP_Package_after')?['result']?['id']),equals(body('HTTP_Package_before')?['result']?['license_id'],body('HTTP_Package_after')?['result']?['license_id']),equals(body('HTTP_Package_before')?['result']?['resources'],body('HTTP_Package_after')?['result']?['resources']),equals(body('HTTP_Index_before')?['result']?['records'],body('HTTP_Index_after')?['result']?['records']),equals(length(variables('Files')),add(8,mul(2,max(1,div(add(variables('Total'),99),100))))))",
        previous,
    )
    a["Manifest"] = compose(
        {
            "format": "rims-qgip-source-commit-v1",
            "source_id": SOURCE_ID,
            "resource_id": RESOURCE_ID,
            "package_id": PACKAGE_ID,
            "run": "@workflow()?['run']?['name']",
            "committed_utc": "@utcNow()",
            "source_total": "@variables('Total')",
            "complete_reads": 2,
            "files": "@variables('Files')",
            "candidate_filter_applied": False,
            "canonical_admission": False,
            "source_identity_semantics": "observed_snapshot_keys_only",
            "fidelity": "complete_native_HTTP_JSON_values; stored_serialization_readback_exact; original_transport_bytes_not_certified",
            "cryptographic_hashes": "not_computed_in_flow",
            "schedule": "manual_only",
        },
        "Guard_stable_metadata",
    )
    # Commit last, after complete source and every stored file read back exactly.
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
    return {
        "properties": {
            "displayName": NAME,
            "state": "Stopped",
            "connectionReferences": {"shared_sharepointonline": ref},
            "definition": {
                "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
                "contentVersion": "1.0.0.0",
                "parameters": {
                    "$authentication": {"type": "SecureObject", "defaultValue": {}},
                    "$connections": {"type": "Object", "defaultValue": {}},
                },
                "triggers": {
                    "manual": {
                        "type": "Request",
                        "kind": "Button",
                        "inputs": {
                            "schema": {
                                "type": "object",
                                "required": ["CatalogueJson"],
                                "properties": {
                                    "CatalogueJson": {
                                        "type": "string",
                                        "title": "Current source catalogue JSON",
                                        "x-ms-content-hint": "TEXT",
                                    }
                                },
                            }
                        },
                        "runtimeConfiguration": {"concurrency": {"runs": 1}},
                    }
                },
                "actions": a,
            },
        }
    }


def main():
    from scripts.patch_clinicaltrials_read_retries import strict_json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--archive-parent", required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not args.output.resolve().is_relative_to(root / "private/ops"):
        raise ValueError("Tenant-specific output must stay in ignored private/ops")
    candidate = build(
        args.site, args.archive_parent, strict_json(args.reference.read_bytes())
    )
    with args.output.open("x") as stream:
        json.dump(candidate, stream, indent=2)
    print(
        "Prepared Stopped/manual-only QGIP raw collector; native qualification and deployment remain required"
    )


if __name__ == "__main__":
    main()
