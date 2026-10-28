"""Prepare a manual Microsoft ARC award export from a retained source commit.

No network effects. Bounded page JSON/CSV outputs avoid a single oversized action;
all pages are committed as one export only after complete validation/readback.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

try:
    from scripts.grants_arc_api import API_BASE
    from scripts.patch_clinicaltrials_read_retries import strict_json
    from scripts.prepare_arc_source_collection import build as source_build
    from scripts.prepare_arc_source_collection import compose, gate
    from scripts.prepare_qgip_candidate_export import build as candidate_build
except ImportError:
    from grants_arc_api import API_BASE
    from patch_clinicaltrials_read_retries import strict_json
    from prepare_arc_source_collection import build as source_build
    from prepare_arc_source_collection import compose, gate
    from prepare_qgip_candidate_export import build as candidate_build

NAME = "CHHHS RIMS | Funding | ARC award context export"
FIELDS = [
    "RecordKind",
    "Source",
    "SourceID",
    "AwardCode",
    "Title",
    "Funder",
    "URL",
    "Description",
    "Amount",
    "Status",
    "RetrievedUTC",
    "EvidenceHash",
]


def build(site, archive_parent, reference):
    result = source_build(site, archive_parent, reference)
    p = result["properties"]
    p["displayName"] = NAME
    definition = p["definition"]
    a = definition["actions"]
    trigger = definition["triggers"]["manual"]["inputs"]["schema"]
    trigger["required"].append("SourceRun")
    trigger["properties"]["SourceRun"] = {
        "type": "string",
        "minLength": 1,
        "maxLength": 128,
        "title": "Existing committed ARC source run",
        "x-ms-content-hint": "TEXT",
    }

    def sp(op, params, previous=""):
        return {
            "type": "OpenApiConnection",
            "runAfter": {previous: ["Succeeded"]} if previous else {},
            "inputs": {
                "host": {
                    "apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
                    "connectionName": "shared_sharepointonline",
                    "operationId": op,
                },
                "parameters": {"dataset": site, **params},
                "retryPolicy": {"type": "none"},
            },
        }

    # Reuse the accepted source-folder traversal guard, with this source policy.
    guard = copy.deepcopy(
        candidate_build(site, archive_parent, reference)["properties"]["definition"][
            "actions"
        ]["Guard_source_run"]
    )
    a["Guard_source_run"] = guard
    a["Initialize_Files"]["runAfter"] = {"Guard_source_run": ["Succeeded"]}
    a["Initialize_OutputFiles"] = {
        "type": "InitializeVariable",
        "runAfter": {"Initialize_PageFailed": ["Succeeded"]},
        "inputs": {
            "variables": [{"name": "OutputFiles", "type": "array", "value": []}]
        },
    }
    a["Run_folder"]["runAfter"] = {"Initialize_OutputFiles": ["Succeeded"]}
    a["Run_folder"]["inputs"] = (
        "@concat('" + archive_parent + "/arc-source-',triggerBody()?['SourceRun'])"
    )
    a["Create_exclusive_folder"] = sp(
        "GetFileContentByPath",
        {
            "path": "@concat(outputs('Run_folder'),'/manifest.json')",
            "inferContentType": False,
        },
        "Run_folder",
    )
    a["Source_manifest"] = {
        "type": "ParseJson",
        "runAfter": {"Create_exclusive_folder": ["Succeeded"]},
        "inputs": {
            "content": "@json(base64ToString(body('Create_exclusive_folder')?['$content']))",
            "schema": {
                "type": "object",
                "required": [
                    "format",
                    "source_id",
                    "record_kind",
                    "source_api",
                    "run",
                    "committed_utc",
                    "source_total",
                    "page_count",
                    "page_size",
                    "complete_reads",
                    "files",
                    "canonical_opportunity_admission",
                    "candidate_filter_applied",
                    "schedule",
                ],
                "properties": {
                    "source_total": {"type": "integer", "minimum": 0, "maximum": 50000},
                    "page_count": {"type": "integer", "minimum": 1, "maximum": 100},
                    "page_size": {"type": "integer"},
                    "files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "verification"],
                            "properties": {
                                "name": {"type": "string"},
                                "verification": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    }
    a["Guard_exclusive_folder"] = gate(
        "and(equals(body('Source_manifest')?['format'],'rims-arc-source-commit-v1'),equals(body('Source_manifest')?['source_id'],'arc-awards-api'),equals(body('Source_manifest')?['record_kind'],'awards_only'),equals(body('Source_manifest')?['source_api'],'"
        + API_BASE
        + "'),equals(body('Source_manifest')?['run'],triggerBody()?['SourceRun']),equals(body('Source_manifest')?['complete_reads'],2),equals(body('Source_manifest')?['page_size'],500),equals(body('Source_manifest')?['page_count'],max(1,div(add(body('Source_manifest')?['source_total'],499),500))),equals(body('Source_manifest')?['canonical_opportunity_admission'],false),equals(body('Source_manifest')?['candidate_filter_applied'],false),equals(body('Source_manifest')?['schedule'],'manual_only'))",
        "Source_manifest",
    )
    a["Output_folder"] = compose(
        "@concat('" + archive_parent + "/arc-awards-',workflow()?['run']?['name'])",
        "Guard_exclusive_folder",
    )
    a["Create_output_folder"] = sp(
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
                + "',outputs('Output_folder'))"
            },
        },
        "Output_folder",
    )
    a["Guard_output_folder"] = gate(
        "and(equals(outputs('Create_output_folder')?['statusCode'],201),equals(int(body('Create_output_folder')?['ItemCount']),0))",
        "Create_output_folder",
    )
    a["Two_complete_reads"]["runAfter"] = {"Guard_output_folder": ["Succeeded"]}
    pages = a["Two_complete_reads"]["actions"]["Read_pages"]["actions"]
    for key in ["HTTP_Page", "Raw_Page", "Save_Page", "Read_Page", "Verify_Page"]:
        del pages[key]
    filename = "@concat('pass-',string(items('Two_complete_reads')),'-page-',string(variables('Page')),'.json')"
    pages["Read_Page"] = sp(
        "GetFileContentByPath",
        {
            "path": "@concat(outputs('Run_folder'),'/'," + filename[1:] + ")",
            "inferContentType": False,
        },
    )
    pages["Raw_Page"] = compose(
        "@json(base64ToString(body('Read_Page')?['$content']))", "Read_Page"
    )
    pages["HTTP_Page"] = compose("@outputs('Raw_Page')?['response']", "Raw_Page")
    pages["Verify_Page"] = gate(
        "and(equals(outputs('Raw_Page')?['request']?['method'],'GET'),equals(outputs('Raw_Page')?['request']?['uri'],'"
        + API_BASE
        + "'),equals(outputs('Raw_Page')?['request']?['queries']?['page[number]'],variables('Page')),equals(outputs('Raw_Page')?['request']?['queries']?['page[size]'],500),equals(outputs('Raw_Page')?['pass'],items('Two_complete_reads')),lessOrEquals(ticks(outputs('Raw_Page')?['captured_utc']),ticks(body('Source_manifest')?['committed_utc'])) )",
        "HTTP_Page",
    )
    pages["Guard_HTTP"]["inputs"] = (
        "@if(equals(outputs('HTTP_Page')?['statusCode'],200),true,int('GUARD_FAILED'))"
    )
    pages["Parse_Page"]["inputs"]["content"] = "@outputs('HTTP_Page')?['body']"
    row = pages["Parse_Page"]["inputs"]["schema"]["properties"]["data"]["items"]
    row["required"].append("links")
    row["properties"]["links"] = {
        "type": "object",
        "required": ["self"],
        "properties": {"self": {"type": "string"}},
    }
    row["properties"]["attributes"]["properties"].update(
        {
            k: {"type": ["string", "null"]}
            for k in ["grant-summary", "scheme-name", "grant-status"]
        }
    )
    row["properties"]["attributes"]["properties"]["current-funding-amount"] = {
        "type": ["string", "number", "null"]
    }
    pages["Guard_exact_page"]["inputs"] = pages["Guard_exact_page"]["inputs"].replace(
        "or(equals(variables('Total'),-1)",
        "and(equals(body('Parse_Page')?['meta']?['total-size'],body('Source_manifest')?['source_total']),equals(body('Parse_Page')?['meta']?['total-pages'],body('Source_manifest')?['page_count'])),or(equals(variables('Total'),-1)",
    )
    comparison = pages["Compare_passes"]["actions"]
    comparison["Guard_full_page_replay"]["inputs"] = comparison[
        "Guard_full_page_replay"
    ]["inputs"].replace("body('Parse_Page')", "body('Parse_Page')")
    aexpr = "item()?['attributes']?"
    summary = aexpr + "['grant-summary']"
    scheme = aexpr + "['scheme-name']"
    status = aexpr + "['grant-status']"
    amount = aexpr + "['current-funding-amount']"
    comparison["Invalid_award_links"] = {
        "type": "Query",
        "runAfter": {"Guard_full_page_replay": ["Succeeded"]},
        "inputs": {
            "from": "@body('Parse_Page')?['data']",
            "where": "@not(or(equals(replace(item()?['links']?['self'],'http://','https://'),concat('"
            + API_BASE
            + "/',item()?['id'])),equals(replace(item()?['links']?['self'],'http://','https://'),concat('"
            + API_BASE
            + "/',item()?['attributes']?['code']))))",
        },
    }
    comparison["Guard_award_links"] = gate(
        "empty(body('Invalid_award_links'))", "Invalid_award_links"
    )
    comparison["Award_page"] = {
        "type": "Select",
        "runAfter": {"Guard_award_links": ["Succeeded"]},
        "inputs": {
            "from": "@body('Parse_Page')?['data']",
            "select": {
                "RecordKind": "Award",
                "Source": "arc",
                "SourceID": "@item()?['id']",
                "AwardCode": "@item()?['attributes']?['code']",
                "Title": "@trim(if(empty("
                + summary
                + "),coalesce("
                + scheme
                + ",''),"
                + summary
                + "))",
                "Funder": "Australian Research Council",
                "URL": "@replace(item()?['links']?['self'],'http://','https://')",
                "Description": "@trim(coalesce(" + summary + ",''))",
                "Amount": "@if(equals("
                + amount
                + ",null),'',trim(string("
                + amount
                + ")))",
                "Status": "@trim(if(empty(" + status + "),'Unknown'," + status + "))",
                "RetrievedUTC": "@string(body('Source_manifest')?['committed_utc'])",
                "EvidenceHash": "",
            },
        },
    }
    comparison["Award_CSV"] = {
        "type": "Table",
        "runAfter": {"Award_page": ["Succeeded"]},
        "inputs": {"from": "@body('Award_page')", "format": "CSV"},
    }
    previous = "Award_CSV"
    for kind, content in [
        ("json", "string(body('Award_page'))"),
        ("csv", "body('Award_CSV')"),
    ]:
        name = "@concat('awards-page-',string(variables('Page')),'." + kind + "')"
        label = kind.upper()
        comparison["Save_" + label] = sp(
            "CreateFile",
            {
                "folderPath": "@outputs('Output_folder')",
                "name": name,
                "body": "@base64ToBinary(base64(" + content + "))",
            },
            previous,
        )
        comparison["Read_" + label] = sp(
            "GetFileContentByPath",
            {
                "path": "@concat(outputs('Output_folder'),'/'," + name[1:] + ")",
                "inferContentType": False,
            },
            "Save_" + label,
        )
        comparison["Verify_" + label] = gate(
            "equals(base64(" + content + "),body('Read_" + label + "')?['$content'])",
            "Read_" + label,
        )
        comparison["Record_" + label] = {
            "type": "AppendToArrayVariable",
            "runAfter": {"Verify_" + label: ["Succeeded"]},
            "inputs": {
                "name": "OutputFiles",
                "value": {
                    "name": name,
                    "rows": "@length(body('Award_page'))",
                    "verification": "exact_base64_stored_content_readback",
                },
            },
        }
        previous = "Record_" + label
    a["Guard_manifest_coverage"]["inputs"] = (
        "@if(and(not(variables('PageFailed')),equals(length(variables('Files')),mul(2,variables('Pages'))),equals(sort(variables('Files'),'name'),sort(body('Source_manifest')?['files'],'name')),equals(length(variables('OutputFiles')),mul(2,variables('Pages')))),true,int('GUARD_FAILED'))"
    )
    a["Read_source_manifest_again"] = sp(
        "GetFileContentByPath",
        {
            "path": "@concat(outputs('Run_folder'),'/manifest.json')",
            "inferContentType": False,
        },
        "Guard_manifest_coverage",
    )
    a["Guard_manifest_unchanged"] = gate(
        "equals(body('Read_source_manifest_again')?['$content'],body('Create_exclusive_folder')?['$content'])",
        "Read_source_manifest_again",
    )
    a["Manifest"] = compose(
        {
            "format": "rims-arc-award-export-v1",
            "source_run": "@triggerBody()?['SourceRun']",
            "source_total": "@variables('Total')",
            "page_count": "@variables('Pages')",
            "rows_per_page": 500,
            "fields": copy.deepcopy(FIELDS),
            "record_kind": "awards_only",
            "canonical_opportunity_admission": False,
            "lifecycle_semantics_proven": False,
            "files": "@variables('OutputFiles')",
            "source_manifest_base64": "@body('Read_source_manifest_again')?['$content']",
            "run": "@workflow()?['run']?['name']",
            "created_utc": "@utcNow()",
        },
        "Guard_manifest_unchanged",
    )
    a["Commit_manifest"]["inputs"]["parameters"]["folderPath"] = (
        "@outputs('Output_folder')"
    )
    a["Read_manifest"]["inputs"]["parameters"]["path"] = (
        "@concat(outputs('Output_folder'),'/manifest.json')"
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["site", "archive-parent"]:
        parser.add_argument("--" + name, required=True)
    for name in ["reference", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "private/ops"
    if not args.output.resolve().is_relative_to(root.resolve()):
        raise ValueError("Private output required")
    result = build(
        args.site, args.archive_parent, strict_json(args.reference.read_bytes())
    )
    serialized = json.dumps(result, indent=2, allow_nan=False)
    with os.fdopen(
        os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w"
    ) as stream:
        stream.write(serialized)
    print(
        "Prepared Stopped manual ARC award-context export; native qualification required"
    )


if __name__ == "__main__":
    main()
