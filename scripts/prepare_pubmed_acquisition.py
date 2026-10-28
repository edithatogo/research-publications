"""Prepare a Microsoft-only full-hedge PubMed raw XML acquisition flow.

The maintained collector configuration is frozen into each manual proposal. Each
explicit run reconciles all selected records, including updates to older IDs.
No model, register, admission, or reporting actions are included.
"""

import copy
import hashlib
import json
from urllib.parse import urlsplit

from scripts.collect_pubmed import BASE, validate_config
from scripts.prepare_qgip_source_collection import build as archive_base
from scripts.prepare_qgip_source_collection import capture_failed_http, compose, gate


def build(site, archive_parent, reference, collector, policy):
    if not isinstance(collector, dict) or not isinstance(policy, dict):
        raise ValueError("Explicit maintained collector/policy required")  # noqa: TRY004 - retained validation ValueError contract
    collector = copy.deepcopy(collector)
    policy = copy.deepcopy(policy)
    pubmed = validate_config(collector)
    if policy.get("source") != "pubmed":
        raise ValueError("Selected PubMed scope required")
    d = archive_base(site, archive_parent, reference)
    p = d["properties"]
    p["displayName"] = "CHHHS RIMS | Data spaces | PubMed source collection"
    definition = p["definition"]
    definition["triggers"]["manual"]["inputs"]["schema"] = {
        "type": "object",
        "properties": {},
    }
    definition["triggers"]["manual"]["runtimeConfiguration"] = {
        "concurrency": {"runs": 1}
    }
    a = definition["actions"] = {}

    def sp(op, params, previous):
        return {
            "type": "OpenApiConnection",
            "runAfter": {previous: ["Succeeded"]},
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

    def save(actions, key, name, content, previous):
        actions["Save_" + key] = sp(
            "CreateFile",
            {
                "folderPath": "@outputs('Run_folder')",
                "name": name,
                "body": "@base64ToBinary(base64(" + content + "))",
            },
            previous,
        )
        ne = name[1:] if name.startswith("@") else "'" + name + "'"
        actions["Read_" + key] = sp(
            "GetFileContentByPath",
            {
                "path": "@concat(outputs('Run_folder'),'/'," + ne + ")",
                "inferContentType": False,
            },
            "Save_" + key,
        )
        actions["Verify_" + key] = gate(
            "equals(base64(" + content + "),body('Read_" + key + "')?['$content'])",
            "Read_" + key,
        )
        return "Verify_" + key

    a["Scope"] = compose(
        {
            "policy": policy,
            "collector_revision": collector.get("facility_query_version"),
            "pubmed": pubmed,
        }
    )
    a["Initialize_acquisition_failure"] = {
        "type": "InitializeVariable",
        "runAfter": {"Scope": ["Succeeded"]},
        "inputs": {
            "variables": [
                {"name": "AcquisitionFailed", "type": "boolean", "value": False}
            ]
        },
    }
    a["Initialize_ids"] = {
        "type": "InitializeVariable",
        "runAfter": {"Initialize_acquisition_failure": ["Succeeded"]},
        "inputs": {"variables": [{"name": "FetchedIds", "type": "array", "value": []}]},
    }
    a["Initialize_files"] = {
        "type": "InitializeVariable",
        "runAfter": {"Initialize_ids": ["Succeeded"]},
        "inputs": {"variables": [{"name": "Files", "type": "array", "value": []}]},
    }
    a["Initialize_own_dois"] = {
        "type": "InitializeVariable",
        "runAfter": {"Initialize_files": ["Succeeded"]},
        "inputs": {
            "variables": [{"name": "OwnPublicationDOIs", "type": "array", "value": []}]
        },
    }
    a["Run_folder"] = compose(
        "@concat('"
        + archive_parent
        + "/pubmed-acquisition-',workflow()?['run']?['name'])",
        "Initialize_own_dois",
    )
    from urllib.parse import urlsplit

    a["Create_folder"] = sp(
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
    a["Guard_folder"] = gate(
        "and(equals(outputs('Create_folder')?['statusCode'],201),equals(int(body('Create_folder')?['ItemCount']),0))",
        "Create_folder",
    )
    last = save(a, "scope", "scope.json", "string(outputs('Scope'))", "Guard_folder")
    for suffix, previous in [("Before", last), ("After", "For_each_batch")]:
        a["Search_" + suffix] = {
            "type": "Http",
            "runAfter": {previous: ["Succeeded"]},
            "inputs": {
                "uri": BASE + "esearch.fcgi",
                "method": "POST",
                "headers": {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                "body": "@concat('db=pubmed&retmode=json&retmax=9999&term=',uriComponent(outputs('Scope')?['pubmed']?['query']))",
                "retryPolicy": {"type": "none"},
            },
        }
        a["Raw_search_" + suffix] = compose(
            "@outputs('Search_" + suffix + "')", "Search_" + suffix
        )
        capture_failed_http(
            a,
            "Search_" + suffix,
            "pubmed",
            "AcquisitionFailed",
            "failure-search-" + suffix.lower() + ".json",
            save,
        )
        lastsearch = save(
            a,
            "search_" + suffix,
            "search-" + suffix.lower() + ".json",
            "string(outputs('Raw_search_" + suffix + "'))",
            "Raw_search_" + suffix,
        )
        a["Guard_search_" + suffix] = gate(
            "and(equals(outputs('Search_"
            + suffix
            + "')?['statusCode'],200),empty(body('Search_"
            + suffix
            + "')?['esearchresult']?['ERROR']),lessOrEquals(int(body('Search_"
            + suffix
            + "')?['esearchresult']?['count']),9999),equals(int(body('Search_"
            + suffix
            + "')?['esearchresult']?['count']),length(body('Search_"
            + suffix
            + "')?['esearchresult']?['idlist'])),equals(length(union(body('Search_"
            + suffix
            + "')?['esearchresult']?['idlist'],body('Search_"
            + suffix
            + "')?['esearchresult']?['idlist'])),length(body('Search_"
            + suffix
            + "')?['esearchresult']?['idlist'])))",
            lastsearch,
        )
    a["ID_batches"] = compose(
        "@chunk(body('Search_Before')?['esearchresult']?['idlist'],100)",
        "Guard_search_Before",
    )
    loop = {}
    loop["Polite_delay"] = {
        "type": "Wait",
        "runAfter": {},
        "inputs": {"interval": {"count": 5, "unit": "Second"}},
    }
    loop["Fetch_xml"] = {
        "type": "Http",
        "runAfter": {"Polite_delay": ["Succeeded"]},
        "inputs": {
            "uri": BASE + "efetch.fcgi",
            "method": "POST",
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/xml",
            },
            "body": "@concat('db=pubmed&retmode=xml&id=',uriComponent(join(items('For_each_batch'),',')))",
            "retryPolicy": {"type": "none"},
        },
    }
    loop["Raw_xml"] = compose("@string(body('Fetch_xml'))", "Fetch_xml")
    capture_failed_http(
        loop,
        "Fetch_xml",
        "pubmed",
        "AcquisitionFailed",
        "@concat('failure-pmid-',first(items('For_each_batch')),'.json')",
        save,
    )
    filename = "@concat('pmid-',first(items('For_each_batch')),'.xml')"
    lastxml = save(loop, "xml", filename, "outputs('Raw_xml')", "Raw_xml")
    loop["XML_for_identity"] = compose(
        "@if(contains(outputs('Raw_xml'),'<!DOCTYPE'),replace(outputs('Raw_xml'),concat('<!DOCTYPE',first(split(last(split(outputs('Raw_xml'),'<!DOCTYPE')),'>')),'>'),''),outputs('Raw_xml'))",
        lastxml,
    )
    loop["Fetched_ids"] = compose(
        "@xpath(xml(outputs('XML_for_identity')),'/PubmedArticleSet/PubmedArticle/MedlineCitation/PMID/text() | /PubmedArticleSet/PubmedBookArticle/BookDocument/PMID/text()')",
        "XML_for_identity",
    )
    loop["Guard_batch"] = gate(
        "and(equals(outputs('Fetch_xml')?['statusCode'],200),equals(length(xpath(xml(outputs('XML_for_identity')),'//ERROR')),0),equals(sort(outputs('Fetched_ids')),sort(items('For_each_batch'))))",
        "Fetched_ids",
    )
    loop["Merged_ids"] = compose(
        "@union(variables('FetchedIds'),outputs('Fetched_ids'))", "Guard_batch"
    )
    loop["Set_ids"] = {
        "type": "SetVariable",
        "runAfter": {"Merged_ids": ["Succeeded"]},
        "inputs": {"name": "FetchedIds", "value": "@outputs('Merged_ids')"},
    }
    loop["Own_doi_values"] = compose(
        "@xpath(xml(outputs('XML_for_identity')),'/PubmedArticleSet/PubmedArticle/PubmedData/ArticleIdList/ArticleId[@IdType=\"doi\"]/text() | /PubmedArticleSet/PubmedBookArticle/PubmedBookData/ArticleIdList/ArticleId[@IdType=\"doi\"]/text()')",
        "Set_ids",
    )
    loop["Normalize_own_dois"] = {
        "type": "Select",
        "runAfter": {"Own_doi_values": ["Succeeded"]},
        "inputs": {
            "from": "@outputs('Own_doi_values')",
            "select": "@toLower(trim(item()))",
        },
    }
    loop["Merged_own_dois"] = compose(
        "@union(variables('OwnPublicationDOIs'),body('Normalize_own_dois'))",
        "Normalize_own_dois",
    )
    loop["Set_own_dois"] = {
        "type": "SetVariable",
        "runAfter": {"Merged_own_dois": ["Succeeded"]},
        "inputs": {
            "name": "OwnPublicationDOIs",
            "value": "@outputs('Merged_own_dois')",
        },
    }
    loop["Record_file"] = {
        "type": "AppendToArrayVariable",
        "runAfter": {"Set_own_dois": ["Succeeded"]},
        "inputs": {
            "name": "Files",
            "value": {
                "file": filename,
                "ids": "@items('For_each_batch')",
                "saved_readback_equal": True,
            },
        },
    }
    a["For_each_batch"] = {
        "type": "Foreach",
        "foreach": "@outputs('ID_batches')",
        "runAfter": {"ID_batches": ["Succeeded"]},
        "runtimeConfiguration": {"concurrency": {"repetitions": 1}},
        "actions": loop,
    }
    a["Guard_complete"] = gate(
        "and(not(variables('AcquisitionFailed')),equals(sort(body('Search_Before')?['esearchresult']?['idlist']),sort(body('Search_After')?['esearchresult']?['idlist'])),equals(sort(variables('FetchedIds')),sort(body('Search_Before')?['esearchresult']?['idlist'])))",
        "Guard_search_After",
    )
    a["Manifest"] = compose(
        {
            "format": "rims-pubmed-full-hedge-commit-v1",
            "source": "pubmed",
            "complete": True,
            "pmids": "@variables('FetchedIds')",
            "count": "@length(variables('FetchedIds'))",
            "files": "@variables('Files')",
            "archive_folder": "@outputs('Run_folder')",
            "run": "@workflow()?['run']?['name']",
            "scope": "@outputs('Scope')",
            "scope_sha256": hashlib.sha256(
                json.dumps(
                    {"collector": collector, "policy": policy},
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
            "downstream_selection_applied": False,
            "fidelity": "complete_HTTP_XML_text; exact_saved_readback; transport_bytes_not_certified",
            "schedule": "manual_only",
            "update_strategy": "full_selected_scope_reconciliation",
            "publication_doi_values": "@variables('OwnPublicationDOIs')",
            "doi_provenance": "Own PubmedData/ArticleIdList and PubmedBookData/ArticleIdList only; cited ReferenceList excluded",
        },
        "Guard_complete",
    )
    verified_manifest = save(
        a, "manifest", "manifest.json", "string(outputs('Manifest'))", "Manifest"
    )
    marker = (
        "@concat('pubmed-acquisition-complete-',workflow()?['run']?['name'],'.json')"
    )
    a["Save_complete_checkpoint"] = sp(
        "CreateFile",
        {
            "folderPath": archive_parent,
            "name": marker,
            "body": "@base64ToBinary(base64(string(outputs('Manifest'))))",
        },
        verified_manifest,
    )
    a["Read_complete_checkpoint"] = sp(
        "GetFileContentByPath",
        {
            "path": "@concat('"
            + archive_parent
            + "/','pubmed-acquisition-complete-',workflow()?['run']?['name'],'.json')",
            "inferContentType": False,
        },
        "Save_complete_checkpoint",
    )
    a["Verify_complete_checkpoint"] = gate(
        "equals(base64(string(outputs('Manifest'))),body('Read_complete_checkpoint')?['$content'])",
        "Read_complete_checkpoint",
    )
    return d


def with_daily_updates(document):
    """Retained API name; this source packet qualifies manual proposals only."""
    raise ValueError("Daily proposal unavailable in the manual-only source packet")


READ_PATHS = (("Search_Before",), ("Search_After",), ("For_each_batch", "Fetch_xml"))


def with_bounded_read_recovery(
    document,
    *,
    expected_definition_sha256,
    selected_paths=None,
    observer_preimage_bytes=None,
    expected_observer_sha256=None,
):
    """Prepare finite retries only for PubMed's three read-only POST leaves.

    ESearch and EFetch use POST to avoid URL limits but have no provider write
    effects. Native retry policy handles transient HTTP faults; failed-generation
    and exact saved-byte guards remain authoritative. No archive/SPO mutation is
    retried, no XML is reused across source generations, and no run is submitted.
    The supplied observer bytes/hash bind existing source identity only. They do
    not certify native storage, deployment or durable failed-generation behavior.
    """
    from scripts.patch_clinicaltrials_read_retries import (
        POLICY,
        definition_sha256,
        strict_json,
    )

    d = copy.deepcopy(document)
    p = d.get("properties", {})
    definition = p.get("definition", {})
    if definition_sha256(definition) != expected_definition_sha256:
        raise ValueError("Definition drift")
    if p.get("state") not in {"Started", "Stopped"}:
        raise ValueError("Existing explicit flow state required")
    a = definition.get("actions", {})
    manifest = a.get("Manifest", {}).get("inputs", {})
    if (
        manifest.get("format") != "rims-pubmed-full-hedge-commit-v1"
        or manifest.get("source") != "pubmed"
    ):
        raise ValueError("Full-hedge PubMed collector required")
    observer = a.get("Observe_failed_generation")
    if (
        not isinstance(observer, dict)
        or observer.get("type") != "Scope"
        or not isinstance(observer.get("actions"), dict)
        or not observer["actions"]
        or not isinstance(observer.get("runAfter"), dict)
        or not observer["runAfter"]
        or any(
            key not in a
            or not isinstance(status, list)
            or not status
            or any(s not in ("Failed", "TimedOut", "Skipped") for s in status)
            for key, status in observer["runAfter"].items()
        )
    ):
        raise ValueError(
            "Existing failed-generation scope required; durability is separately qualified"
        )
    if (
        not isinstance(observer_preimage_bytes, bytes)
        or hashlib.sha256(observer_preimage_bytes).hexdigest()
        != expected_observer_sha256
        or definition_sha256(strict_json(observer_preimage_bytes))
        != definition_sha256(observer)
    ):
        raise ValueError(
            "Explicit supplied observer preimage bytes/hash required; no observer is created"
        )
    if (
        not isinstance(selected_paths, (tuple, list))
        or not selected_paths
        or any(
            not isinstance(path, tuple) or path not in READ_PATHS
            for path in selected_paths
        )
        or len(set(selected_paths)) != len(selected_paths)
    ):
        raise ValueError("Explicit exact read-only PubMed action selection required")
    search_body = "@concat('db=pubmed&retmode=json&retmax=9999&term=',uriComponent(outputs('Scope')?['pubmed']?['query']))"
    fetch_body = "@concat('db=pubmed&retmode=xml&id=',uriComponent(join(items('For_each_batch'),',')))"
    leaves = []
    for path in selected_paths:
        action = (
            a.get(path[0], {})
            if len(path) == 1
            else a.get(path[0], {}).get("actions", {}).get(path[1], {})
        )
        uri = BASE + ("esearch.fcgi" if len(path) == 1 else "efetch.fcgi")
        inputs = action.get("inputs", {})
        parsed = urlsplit(inputs["uri"]) if isinstance(inputs.get("uri"), str) else None
        if (
            action.get("type") != "Http"
            or inputs.get("method") != "POST"
            or inputs.get("uri") != uri
            or not parsed
            or parsed.scheme != "https"
            or parsed.netloc != "eutils.ncbi.nlm.nih.gov"
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
            or inputs.get("retryPolicy") != {"type": "none"}
            or set(inputs) != {"uri", "method", "retryPolicy", "headers", "body"}
            or inputs.get("headers")
            != {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json" if len(path) == 1 else "application/xml",
            }
            or inputs.get("body") != (search_body if len(path) == 1 else fetch_body)
        ):
            raise ValueError("Exact PubMed read-only POST preimage required")
        leaves.append(action)
    for action in leaves:
        action["inputs"]["retryPolicy"] = copy.deepcopy(POLICY)
    return d
