"""Archive the established DoRA publication collection in Power Automate.

Complete public collection pages and full metadata HTML are retained; no PDFs,
new repository holdings, record admission, or register/model writes are added.
"""

import copy
import hashlib
import json

from scripts.prepare_qgip_source_collection import build as archive_base
from scripts.prepare_qgip_source_collection import compose, gate

BASE = "https://dora.health.qld.gov.au"
COLLECTION = BASE + "/qldresearchjspui/handle/1/849"


def build(site, parent, reference, policy):
    if not isinstance(policy, dict):
        raise ValueError("Explicit maintained DoRA policy required")  # noqa: TRY004 - retained validation ValueError contract
    policy = copy.deepcopy(policy)
    if policy.get("source") != "dora":
        raise ValueError("Selected DoRA policy required")
    d = archive_base(site, parent, reference)
    p = d["properties"]
    p["displayName"] = "CHHHS RIMS | Data spaces | DoRA publication source collection"
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

    def http(uri, previous):
        return {
            "type": "Http",
            "runAfter": {previous: ["Succeeded"]} if previous else {},
            "inputs": {
                "uri": uri,
                "method": "GET",
                "headers": {"Accept": "text/html"},
                "retryPolicy": {"type": "none"},
            },
        }

    def setvar(name, value, previous):
        return {
            "type": "SetVariable",
            "runAfter": {previous: ["Succeeded"]} if previous else {},
            "inputs": {"name": name, "value": value},
        }

    def save(actions, key, name, expr, previous):
        actions["Save_" + key] = sp(
            "CreateFile",
            {
                "folderPath": "@outputs('Run_folder')",
                "name": name,
                "body": "@base64ToBinary(base64(" + expr + "))",
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
            "equals(base64(" + expr + "),body('Read_" + key + "')?['$content'])",
            "Read_" + key,
        )
        return "Verify_" + key

    a["Scope"] = compose(
        {
            "policy": policy,
            "collection_url": COLLECTION,
            "page_size": 20,
            "scope": "all_public_keys_in_established_collection_only",
            "full_metadata_mode": "full",
        }
    )
    previous = "Scope"
    for name, typ, value in [
        ("Offset", "integer", 0),
        ("Expected", "integer", -1),
        ("Keys", "array", []),
        ("FirstKeys", "array", []),
        ("CollectionFiles", "array", []),
        ("RecordFiles", "array", []),
        ("ScanDone", "boolean", False),
        ("ScanFailed", "boolean", False),
    ]:
        key = "Initialize_" + name
        a[key] = {
            "type": "InitializeVariable",
            "runAfter": {previous: ["Succeeded"]},
            "inputs": {"variables": [{"name": name, "type": typ, "value": value}]},
        }
        previous = key
    a["Run_folder"] = compose(
        "@concat('" + parent + "/dora-publications-',workflow()?['run']?['name'])",
        previous,
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
    initial = save(a, "scope", "scope.json", "string(outputs('Scope'))", "Guard_folder")

    def scan(suffix, previous):
        for name, value in [
            ("Offset", 0),
            ("Expected", -1),
            ("Keys", []),
            ("ScanDone", False),
        ]:
            key = "Reset_" + name + "_" + suffix
            a[key] = setvar(name, value, previous)
            previous = key
        page = {}
        get = "Get_collection_" + suffix
        page[get] = http(
            "@concat('" + COLLECTION + "?offset=',string(variables('Offset')))", ""
        )
        page["Raw_collection_" + suffix] = compose(
            {
                "url": "@concat('"
                + COLLECTION
                + "?offset=',string(variables('Offset')))",
                "response": "@outputs('" + get + "')",
            },
            get,
        )
        name = (
            "@concat('collection-"
            + suffix.lower()
            + "-offset-',string(variables('Offset')),'.json')"
        )
        last = save(
            page,
            "collection_" + suffix,
            name,
            "string(outputs('Raw_collection_" + suffix + "'))",
            "Raw_collection_" + suffix,
        )
        page["Guard_collection_shape_" + suffix] = gate(
            "and(equals(outputs('"
            + get
            + "')?['statusCode'],200),contains(string(body('"
            + get
            + "')),'<div class=\"browse_range\">'),contains(string(body('"
            + get
            + "')),'summary=\"This table browses all dspace content\"'))",
            last,
        )
        page["Range_text_" + suffix] = compose(
            "@first(split(last(split(string(body('"
            + get
            + "')),'<div class=\"browse_range\">')),'</div>'))",
            "Guard_collection_shape_" + suffix,
        )
        page["Page_total_" + suffix] = compose(
            "@int(trim(last(split(outputs('Range_text_" + suffix + "'),' of '))))",
            "Range_text_" + suffix,
        )
        page["Expected_value_" + suffix] = compose(
            "@if(equals(variables('Expected'),-1),outputs('Page_total_"
            + suffix
            + "'),variables('Expected'))",
            "Page_total_" + suffix,
        )
        page["Set_expected_" + suffix] = setvar(
            "Expected",
            "@outputs('Expected_value_" + suffix + "')",
            "Expected_value_" + suffix,
        )
        page["Record_table_" + suffix] = compose(
            "@first(split(last(split(string(body('"
            + get
            + "')),'summary=\"This table browses all dspace content\"')),'</table>'))",
            "Set_expected_" + suffix,
        )
        page["Handle_fragments_" + suffix] = compose(
            "@skip(split(outputs('Record_table_"
            + suffix
            + "'),'href=\"/qldresearchjspui/handle/1/'),1)",
            "Record_table_" + suffix,
        )
        page["Page_keys_" + suffix] = {
            "type": "Select",
            "runAfter": {"Handle_fragments_" + suffix: ["Succeeded"]},
            "inputs": {
                "from": "@outputs('Handle_fragments_" + suffix + "')",
                "select": "@first(split(item(),'\"'))",
            },
        }
        page["Guard_page_" + suffix] = gate(
            "and(equals(outputs('Page_total_"
            + suffix
            + "'),variables('Expected')),greater(variables('Expected'),0),lessOrEquals(variables('Expected'),20000),equals(length(body('Page_keys_"
            + suffix
            + "')),min(20,max(0,sub(variables('Expected'),variables('Offset'))))))",
            "Page_keys_" + suffix,
        )
        page["Merged_keys_" + suffix] = compose(
            "@union(variables('Keys'),body('Page_keys_" + suffix + "'))",
            "Guard_page_" + suffix,
        )
        page["Set_keys_" + suffix] = setvar(
            "Keys", "@outputs('Merged_keys_" + suffix + "')", "Merged_keys_" + suffix
        )
        page["Record_page_" + suffix] = {
            "type": "AppendToArrayVariable",
            "runAfter": {"Set_keys_" + suffix: ["Succeeded"]},
            "inputs": {
                "name": "CollectionFiles",
                "value": {
                    "name": name,
                    "keys": "@body('Page_keys_" + suffix + "')",
                    "saved_readback_equal": True,
                },
            },
        }
        page["Next_offset_" + suffix] = {
            "type": "IncrementVariable",
            "runAfter": {"Record_page_" + suffix: ["Succeeded"]},
            "inputs": {"name": "Offset", "value": 20},
        }
        page["Set_done_" + suffix] = setvar(
            "ScanDone",
            "@greaterOrEquals(variables('Offset'),variables('Expected'))",
            "Next_offset_" + suffix,
        )
        page["Polite_delay_" + suffix] = {
            "type": "Wait",
            "runAfter": {"Set_done_" + suffix: ["Succeeded"]},
            "inputs": {"interval": {"count": 5, "unit": "Second"}},
        }
        page["Mark_failed_" + suffix] = {
            "type": "SetVariable",
            "runAfter": {"Polite_delay_" + suffix: ["Failed", "TimedOut", "Skipped"]},
            "inputs": {"name": "ScanFailed", "value": True},
        }
        page["Stop_failed_" + suffix] = setvar(
            "ScanDone", True, "Mark_failed_" + suffix
        )
        key = "Scan_collection_" + suffix
        a[key] = {
            "type": "Until",
            "runAfter": {previous: ["Succeeded"]},
            "expression": "@equals(variables('ScanDone'),true)",
            "limit": {"count": 1000, "timeout": "P1D"},
            "actions": page,
        }
        guard = "Guard_complete_" + suffix
        a[guard] = gate(
            "and(not(variables('ScanFailed')),equals(length(variables('Keys')),variables('Expected')))",
            key,
        )
        return guard

    before = scan("Before", initial)
    a["Keep_first_keys"] = setvar("FirstKeys", "@variables('Keys')", before)
    loop = {}
    loop["Polite_record_delay"] = {
        "type": "Wait",
        "runAfter": {},
        "inputs": {"interval": {"count": 5, "unit": "Second"}},
    }
    loop["Guard_handle_key"] = gate(
        "and(greater(int(items('For_each_record')),0),equals(string(int(items('For_each_record'))),items('For_each_record')))",
        "Polite_record_delay",
    )
    loop["Get_full_record"] = http(
        "@concat('"
        + BASE
        + "/qldresearchjspui/handle/1/',items('For_each_record'),'?mode=full')",
        "Guard_handle_key",
    )
    loop["Raw_record"] = compose("@string(body('Get_full_record'))", "Get_full_record")
    name = "@concat('handle-1-',items('For_each_record'),'.html')"
    last = save(loop, "record", name, "outputs('Raw_record')", "Raw_record")
    loop["Full_metadata_table"] = compose(
        "@first(split(last(split(outputs('Raw_record'),'itemDisplayTable')),'</table>'))",
        last,
    )
    loop["Identifier_row"] = compose(
        "@replace(replace(replace(first(split(last(split(outputs('Full_metadata_table'),'dc.identifier.uri</td>')),'</tr>')),'&#x2F;','/'),'&#x2f;','/'),'&#47;','/')",
        "Full_metadata_table",
    )
    loop["Guard_record"] = gate(
        "and(equals(outputs('Get_full_record')?['statusCode'],200),contains(outputs('Raw_record'),'itemDisplayTable'),equals(length(split(outputs('Full_metadata_table'),'dc.identifier.uri</td>')),2),or(contains(outputs('Identifier_row'),concat('"
        + BASE
        + "/qldresearchjspui/handle/1/',items('For_each_record'),'<')),contains(outputs('Identifier_row'),concat('http://dora.health.qld.gov.au/qldresearchjspui/handle/1/',items('For_each_record'),'<'))))",
        "Identifier_row",
    )
    loop["Record_file"] = {
        "type": "AppendToArrayVariable",
        "runAfter": {"Guard_record": ["Succeeded"]},
        "inputs": {
            "name": "RecordFiles",
            "value": {
                "name": name,
                "key": "@items('For_each_record')",
                "saved_readback_equal": True,
            },
        },
    }
    a["For_each_record"] = {
        "type": "Foreach",
        "foreach": "@variables('FirstKeys')",
        "runAfter": {"Keep_first_keys": ["Succeeded"]},
        "runtimeConfiguration": {"concurrency": {"repetitions": 1}},
        "actions": loop,
    }
    after = scan("After", "For_each_record")
    a["Guard_collection_stable"] = gate(
        "and(equals(sort(variables('FirstKeys')),sort(variables('Keys'))),equals(length(variables('RecordFiles')),length(variables('FirstKeys'))))",
        after,
    )
    a["Manifest"] = compose(
        {
            "format": "rims-dora-publication-raw-commit-v1",
            "source": "dora",
            "collection_url": COLLECTION,
            "complete": True,
            "keys": "@variables('FirstKeys')",
            "count": "@length(variables('FirstKeys'))",
            "collection_files": "@variables('CollectionFiles')",
            "record_files": "@variables('RecordFiles')",
            "run": "@workflow()?['run']?['name']",
            "archive_folder": "@outputs('Run_folder')",
            "scope": policy,
            "scope_sha256": hashlib.sha256(
                json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "downstream_selection_applied": False,
            "schedule": "manual_only",
            "fidelity": "complete_public_HTML_text; exact_saved_readback; transportbytes_not_certified",
        },
        "Guard_collection_stable",
    )
    save(a, "manifest", "manifest.json", "string(outputs('Manifest'))", "Manifest")
    return d


def with_daily_updates(document):
    """Retained API name; this source packet qualifies manual proposals only."""
    raise ValueError("Daily proposal unavailable in the manual-only source packet")


def with_raw_doi_checkpoint(document, *, expected_definition_sha256=None):
    """Expose explicit own DOI fields after complete raw metadata preservation."""
    d = copy.deepcopy(document)
    p = d["properties"]
    a = p["definition"]["actions"]
    from scripts.patch_clinicaltrials_read_retries import definition_sha256

    if definition_sha256(p["definition"]) != expected_definition_sha256:
        raise ValueError("Definition drift; exact current preimage hash required")
    if (
        p.get("state") != "Stopped"
        or a["Manifest"]["inputs"].get("format")
        != "rims-dora-publication-raw-commit-v1"
    ):
        raise ValueError("Stopped DoRA publication collector required")
    if "Initialize_own_publication_dois" in a:
        raise ValueError("Raw DOI producer already configured")
    top = {
        "Save_complete_checkpoint",
        "Read_complete_checkpoint",
        "Verify_complete_checkpoint",
    }
    loop_names = {
        "Own_doi_fragments",
        "Own_doi_field_html",
        "Own_doi_field_values",
        "Merged_own_dois",
        "Set_own_dois",
    }
    if (
        top.intersection(a)
        or loop_names.intersection(a["For_each_record"]["actions"])
        or any(
            k in a["Manifest"]["inputs"]
            for k in ("publication_doi_values", "doi_provenance")
        )
    ):
        raise ValueError(
            "Existing DOI/checkpoint namespace must be reconciled, not overwritten"
        )
    previous = copy.deepcopy(a["Run_folder"]["runAfter"])
    a["Initialize_own_publication_dois"] = {
        "type": "InitializeVariable",
        "runAfter": previous,
        "inputs": {
            "variables": [{"name": "OwnPublicationDOIs", "type": "array", "value": []}]
        },
    }
    a["Run_folder"]["runAfter"] = {"Initialize_own_publication_dois": ["Succeeded"]}
    loop = a["For_each_record"]["actions"]
    loop["Own_doi_fragments"] = compose(
        "@skip(split(outputs('Full_metadata_table'),'dc.identifier.doi</td>'),1)",
        "Guard_record",
    )
    loop["Own_doi_field_html"] = {
        "type": "Select",
        "runAfter": {"Own_doi_fragments": ["Succeeded"]},
        "inputs": {
            "from": "@outputs('Own_doi_fragments')",
            "select": "@first(split(first(skip(split(item(),'class=\"metadataFieldValue\">'),1)),'</td>'))",
        },
    }
    loop["Own_doi_field_values"] = {
        "type": "Select",
        "runAfter": {"Own_doi_field_html": ["Succeeded"]},
        "inputs": {
            "from": "@body('Own_doi_field_html')",
            "select": "@toLower(trim(xpath(xml(concat('<r>',replace(item(),'&nbsp;','&#160;'),'</r>')),'string(/r)')))",
        },
    }
    loop["Merged_own_dois"] = compose(
        "@union(variables('OwnPublicationDOIs'),body('Own_doi_field_values'))",
        "Own_doi_field_values",
    )
    loop["Set_own_dois"] = {
        "type": "SetVariable",
        "runAfter": {"Merged_own_dois": ["Succeeded"]},
        "inputs": {
            "name": "OwnPublicationDOIs",
            "value": "@outputs('Merged_own_dois')",
        },
    }
    loop["Record_file"]["runAfter"] = {"Set_own_dois": ["Succeeded"]}
    a["Manifest"]["inputs"]["publication_doi_values"] = (
        "@variables('OwnPublicationDOIs')"
    )
    a["Manifest"]["inputs"]["doi_provenance"] = (
        "Explicit own dc.identifier.doi fields from complete full metadata; cited references excluded"
    )
    save = copy.deepcopy(a["Save_manifest"])
    params = save["inputs"]["parameters"]
    folder_expression = a["Run_folder"]["inputs"]
    prefix = "@concat('"
    suffix = "/dora-publications-',workflow()?['run']?['name'])"
    if not folder_expression.startswith(prefix) or not folder_expression.endswith(
        suffix
    ):
        raise ValueError("Qualified existing archive folder expression required")
    parent = folder_expression[len(prefix) : -len(suffix)]
    save["runAfter"] = {"Verify_manifest": ["Succeeded"]}
    params["folderPath"] = parent
    params["name"] = (
        "@concat('dora-publications-complete-',workflow()?['run']?['name'],'.json')"
    )
    a["Save_complete_checkpoint"] = save
    read = copy.deepcopy(a["Read_manifest"])
    read["runAfter"] = {"Save_complete_checkpoint": ["Succeeded"]}
    read["inputs"]["parameters"]["path"] = (
        "@concat('"
        + parent
        + "/dora-publications-complete-',workflow()?['run']?['name'],'.json')"
    )
    a["Read_complete_checkpoint"] = read
    a["Verify_complete_checkpoint"] = gate(
        "equals(base64(string(outputs('Manifest'))),body('Read_complete_checkpoint')?['$content'])",
        "Read_complete_checkpoint",
    )
    return d
