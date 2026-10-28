"""Prepare a Microsoft manual candidate export from an existing QGIP commit.

No service operations. Reuse complete-source validation; no external acquisition
or canonical registry writes. Source envelopes remain in their original folder.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

try:
    from scripts.grants_qld_qgip_api import PACKAGE_ID, RESOURCE_ID, SOURCE_ID
    from scripts.patch_clinicaltrials_read_retries import strict_json
    from scripts.prepare_qgip_source_collection import build as source_build
    from scripts.prepare_qgip_source_collection import compose, gate
except ImportError:
    from grants_qld_qgip_api import PACKAGE_ID, RESOURCE_ID, SOURCE_ID
    from patch_clinicaltrials_read_retries import strict_json
    from prepare_qgip_source_collection import build as source_build
    from prepare_qgip_source_collection import compose, gate

NAME = "CHHHS RIMS | Funding | QGIP candidate export"


def build(site: str, archive_parent: str, reference: dict) -> dict:
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
        "title": "Existing committed QGIP source run",
        "x-ms-content-hint": "TEXT",
    }

    def sp(operation, params, previous):
        return {
            "type": "OpenApiConnection",
            "runAfter": {previous: ["Succeeded"]} if previous else {},
            "inputs": {
                "host": {
                    "apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
                    "connectionName": "shared_sharepointonline",
                    "operationId": operation,
                },
                "parameters": {"dataset": site, **params},
                "retryPolicy": {"type": "none"},
            },
        }

    a["Guard_source_run"] = gate(
        "and(not(empty(triggerBody()?['SourceRun'])),lessOrEquals(length(triggerBody()?['SourceRun']),128),equals(triggerBody()?['SourceRun'],trim(triggerBody()?['SourceRun'])),not(contains(triggerBody()?['SourceRun'],'/')),not(contains(triggerBody()?['SourceRun'],'\\')),not(contains(triggerBody()?['SourceRun'],'..')),not(contains(triggerBody()?['SourceRun'],decodeUriComponent('%27'))),not(contains(triggerBody()?['SourceRun'],'?')),not(contains(triggerBody()?['SourceRun'],'#')))",
        "Guard_source_policy",
    )
    a["Guard_source_run"]["inputs"] = a["Guard_source_run"]["inputs"].replace(
        "and(",
        "and(equals(uriComponent(triggerBody()?['SourceRun']),triggerBody()?['SourceRun']),",
        1,
    )
    a["Initialize_Files"]["runAfter"] = {"Guard_source_run": ["Succeeded"]}
    a["Run_folder"]["inputs"] = (
        "@concat('" + archive_parent + "/qgip-source-',triggerBody()?['SourceRun'])"
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
                    "resource_id",
                    "package_id",
                    "run",
                    "committed_utc",
                    "source_total",
                    "complete_reads",
                    "files",
                    "candidate_filter_applied",
                    "canonical_admission",
                    "schedule",
                ],
                "properties": {
                    "source_total": {"type": "integer", "minimum": 0, "maximum": 1000},
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
        "and(equals(body('Source_manifest')?['format'],'rims-qgip-source-commit-v1'),equals(body('Source_manifest')?['source_id'],'"
        + SOURCE_ID
        + "'),equals(body('Source_manifest')?['resource_id'],'"
        + RESOURCE_ID
        + "'),equals(body('Source_manifest')?['package_id'],'"
        + PACKAGE_ID
        + "'),equals(body('Source_manifest')?['run'],triggerBody()?['SourceRun']),equals(body('Source_manifest')?['complete_reads'],2),equals(body('Source_manifest')?['candidate_filter_applied'],false),equals(body('Source_manifest')?['canonical_admission'],false),equals(body('Source_manifest')?['schedule'],'manual_only'))",
        "Source_manifest",
    )

    def convert(actions):
        for key in list(actions):
            action = actions.get(key)
            if action is None:
                continue
            if key.startswith("HTTP_"):
                tag = key[5:]
                request = copy.deepcopy(action["inputs"])
                filename = actions["Record_" + tag]["inputs"]["value"]["name"]
                path = (
                    "@concat(outputs('Run_folder'),'/',"
                    + (
                        filename[1:]
                        if filename.startswith("@")
                        else "'" + filename + "'"
                    )
                    + ")"
                )
                actions["Load_" + tag] = sp(
                    "GetFileContentByPath",
                    {"path": path, "inferContentType": False},
                    "",
                )
                actions["Load_" + tag]["runAfter"] = action["runAfter"]
                actions["Raw_" + tag] = compose(
                    "@json(base64ToString(body('Load_" + tag + "')?['$content']))",
                    "Load_" + tag,
                )
                query_guard = (
                    "equals(outputs('Raw_"
                    + tag
                    + "')?['request']?['queries'],json('"
                    + json.dumps(request["queries"], separators=(",", ":")).replace(
                        "'", "''"
                    )
                    + "'))"
                )
                if tag == "Page":
                    query_guard = (
                        "equals(outputs('Raw_Page')?['request']?['queries'],setProperty(json('{\"resource_id\":\""
                        + RESOURCE_ID
                        + "\",\"limit\":100}'),'offset',variables('Offset')))"
                    )
                actions["Bind_" + tag] = gate(
                    "and(equals(outputs('Raw_"
                    + tag
                    + "')?['request']?['method'],'GET'),equals(outputs('Raw_"
                    + tag
                    + "')?['request']?['uri'],'"
                    + request["uri"]
                    + "'),"
                    + query_guard
                    + ",lessOrEquals(ticks(outputs('Raw_"
                    + tag
                    + "')?['captured_utc']),ticks(body('Source_manifest')?['committed_utc'])))",
                    "Raw_" + tag,
                )
                actions[key] = compose(
                    "@outputs('Raw_" + tag + "')?['response']", "Bind_" + tag
                )
                for prefix in ["Save_", "Read_", "Verify_"]:
                    del actions[prefix + tag]
                actions["Record_" + tag]["runAfter"] = {key: ["Succeeded"]}
            for child in ["actions"]:
                if child in action:
                    convert(action[child])
            if "else" in action:
                convert(action["else"]["actions"])

    convert(a)
    a["Two_complete_reads"]["actions"]["Latch_consumer_set_failure"] = {
        "type": "SetVariable",
        "runAfter": {"Compare_complete_reads": ["Failed", "TimedOut", "Skipped"]},
        "inputs": {"name": "PageFailed", "value": True},
    }

    # Compose response objects are addressed explicitly rather than through body().
    def rewrite(value):
        if isinstance(value, dict):
            return {k: rewrite(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rewrite(v) for v in value]
        if isinstance(value, str):
            import re

            return re.sub(r"body\('(HTTP_[^']+)'\)", r"outputs('\1')?['body']", value)
        return value

    a = rewrite(a)
    definition["actions"] = a
    for key in ["Manifest", "Commit_manifest", "Read_manifest", "Verify_manifest"]:
        del a[key]
    a["Guard_manifest_files"] = gate(
        "and(not(variables('PageFailed')),equals(variables('Total'),body('Source_manifest')?['source_total']),equals(sort(variables('Files'),'name'),sort(body('Source_manifest')?['files'],'name')))",
        "Guard_stable_metadata",
    )
    a["Read_source_manifest_again"] = sp(
        "GetFileContentByPath",
        {
            "path": "@concat(outputs('Run_folder'),'/manifest.json')",
            "inferContentType": False,
        },
        "Guard_manifest_files",
    )
    a["Guard_manifest_unchanged"] = gate(
        "equals(body('Read_source_manifest_again')?['$content'],body('Create_exclusive_folder')?['$content'])",
        "Read_source_manifest_again",
    )
    fields = ["Status", "Assistance type1", "Assistance type2", "Assistance type3"]
    a["Parse_classifiers"] = {
        "type": "ParseJson",
        "runAfter": {"Guard_manifest_unchanged": ["Succeeded"]},
        "inputs": {
            "content": "@variables('Records')",
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {f: {"type": ["string", "null"]} for f in fields},
                },
            },
        },
    }
    a["Candidate_rows"] = {
        "type": "Query",
        "runAfter": {"Parse_classifiers": ["Succeeded"]},
        "inputs": {
            "from": "@body('Parse_classifiers')",
            "where": "@and(equals(toLower(trim(coalesce(item()?['Status'],''))),'open'),or("
            + ",".join(
                "equals(toLower(trim(coalesce(item()?['Assistance type"
                + str(i)
                + "'],''))),'grant')"
                for i in range(1, 4)
            )
            + "))",
        },
    }
    a["Candidate_export"] = {
        "type": "Select",
        "runAfter": {"Candidate_rows": ["Succeeded"]},
        "inputs": {
            "from": "@body('Candidate_rows')",
            "select": {
                "RecordKind": "OpportunityCandidate",
                "Source": "qld-qgip",
                "SourceID": "@item()?['Service ID']",
                "ProgramTitleSource": "@item()?['Program title']",
                "SubprogramTitleSource": "@item()?['Sub-program title']",
                "Status": "Needs Review",
                "SourceStatus": "@item()?['Status']",
                "IdentityStatus": "CandidateUnproven",
                "FreshnessStatus": "Needs Review",
                "CanonicalAdmission": False,
                "ClosingDateSource": "@item()?['Closing date (date format)']",
                "ClosingTextSource": "@item()?['Closing date (text)']",
                "URLSource": "@item()?['Website']",
                "EligibilitySource": "@item()?['Eligibility']",
                "SourceUpdatedUTC": "@outputs('HTTP_Resource_before')?['body']?['result']?['last_modified']",
                "SourceRun": "@triggerBody()?['SourceRun']",
                "SourceCommittedUTC": "@body('Source_manifest')?['committed_utc']",
            },
        },
    }
    a["Candidate_CSV"] = {
        "type": "Table",
        "runAfter": {"Candidate_export": ["Succeeded"]},
        "inputs": {"from": "@body('Candidate_export')", "format": "CSV"},
    }
    a["Output_folder"] = compose(
        "@concat('"
        + archive_parent
        + "/qgip-candidates-',workflow()?['run']?['name'])",
        "Candidate_CSV",
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
    previous = "Guard_output_folder"
    for label, name, content in [
        ("JSON", "candidates.json", "string(body('Candidate_export'))"),
        ("CSV", "candidates.csv", "body('Candidate_CSV')"),
    ]:
        a["Save_" + label] = sp(
            "CreateFile",
            {
                "folderPath": "@outputs('Output_folder')",
                "name": name,
                "body": "@base64ToBinary(base64(" + content + "))",
            },
            previous,
        )
        a["Read_" + label] = sp(
            "GetFileContentByPath",
            {
                "path": "@concat(outputs('Output_folder'),'/" + name + "')",
                "inferContentType": False,
            },
            "Save_" + label,
        )
        a["Verify_" + label] = gate(
            "equals(base64(" + content + "),body('Read_" + label + "')?['$content'])",
            "Read_" + label,
        )
        previous = "Verify_" + label
    a["Candidate_manifest"] = compose(
        {
            "format": "rims-qgip-candidate-export-v1",
            "source_run": "@triggerBody()?['SourceRun']",
            "source_total": "@variables('Total')",
            "candidate_count": "@length(body('Candidate_rows'))",
            "canonical_admission": False,
            "identity_status": "CandidateUnproven",
            "files": ["candidates.json", "candidates.csv"],
            "run": "@workflow()?['run']?['name']",
            "created_utc": "@utcNow()",
            "source_manifest_base64": "@body('Read_source_manifest_again')?['$content']",
        },
        previous,
    )
    a["Commit_candidate_manifest"] = sp(
        "CreateFile",
        {
            "folderPath": "@outputs('Output_folder')",
            "name": "manifest.json",
            "body": "@base64ToBinary(base64(string(outputs('Candidate_manifest'))))",
        },
        "Candidate_manifest",
    )
    a["Read_candidate_manifest"] = sp(
        "GetFileContentByPath",
        {
            "path": "@concat(outputs('Output_folder'),'/manifest.json')",
            "inferContentType": False,
        },
        "Commit_candidate_manifest",
    )
    a["Verify_candidate_manifest"] = gate(
        "equals(base64(string(outputs('Candidate_manifest'))),body('Read_candidate_manifest')?['$content'])",
        "Read_candidate_manifest",
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--archive-parent", required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
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
        "Prepared Stopped manual QGIP candidate export; native deployment/readback required"
    )


if __name__ == "__main__":
    main()
