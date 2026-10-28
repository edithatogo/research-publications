"""Prepare revision-bound metadata exceptions for the existing human review route.

Local preparation only. Never mutates source, registry, author identities or
review decisions. Native review-flow generation is outside this source slice.
"""

from __future__ import annotations

from collections import defaultdict

from .publication_reconciliation import build_case

METADATA_FIELDS = frozenset(
    {
        "Title",
        "Authors",
        "Journal",
        "PublicationYear",
        "PublicationMonth",
        "PublicationDateRaw",
        "PublicationDatePrecision",
        "CHHHSAffiliatedAuthors",
        "MatchedFacilities",
    }
)
RULE_VERSION = "source-registry-metadata-conflict-v2"


def metadata_difference_kind(field, retained, source):
    """Classify selected literal values without editing them or matching people.

    Two bounded HTML entity decodes cover nested publisher encodings. Literal
    affiliated-name segment equality is not author identity/order evidence.
    Numeric zero is not globally missing; date-range repair has its own guard.
    """
    import html
    import re

    if field not in METADATA_FIELDS:
        raise ValueError("Qualified metadata field required")
    if retained == source:
        return "exact"
    if source is None or isinstance(source, str) and not source.strip():
        return "source_unknown_retained"
    if retained is None or isinstance(retained, str) and not retained.strip():
        return "missing_destination"
    if isinstance(retained, str) and isinstance(source, str):

        def text(value):
            for _ in range(2):
                value = html.unescape(value)
            return re.sub(r"</?(?:i|b|em|strong|sub|sup)>", "", value)

        a, b = text(retained), text(source)
        if a == b:
            return "text_representation_equivalent"
        if a.casefold() == b.casefold():
            return "case_representation_equivalent"
        if field == "CHHHSAffiliatedAuthors":
            segments = lambda v: {t.strip() for t in re.split("[;,]", v) if t.strip()}
            if segments(retained) == segments(source):
                return "equal_literal_segments_not_author_identity"
    return "populated_semantic_difference_preserved"


def cases_from_metadata_differences(
    differences, registry_rows, *, source_revision, registry_revision, complete
):
    """Group selected differences by stable item, preserving both exact values.

    Revision denotes each input snapshot, not a inferred modification date.
    No equivalence, correction or author matching is inferred here. Unknown
    fields, duplicate fields/items, changed registry values and lost evidence
    stop preparation. All selected cases are returned, without truncation.
    """
    if (
        complete is not True
        or not isinstance(differences, list)
        or not isinstance(registry_rows, list)
    ):
        raise ValueError("Complete source and registry snapshots required")
    if any(
        not isinstance(x, str) or not x.strip() or x != x.strip()
        for x in (source_revision, registry_revision)
    ):
        raise ValueError("Exact source and registry revisions required")
    indexed = {}
    for row in registry_rows:
        if not isinstance(row, dict) or set(row) != {
            "item_id",
            "source_key",
            "values",
            "evidence",
        }:
            raise ValueError("Registry input needs item_id/source_key/values/evidence")
        ident = row["item_id"]
        if type(ident) is not int or ident <= 0 or ident in indexed:
            raise ValueError("Unique positive registry item ID required")
        if not isinstance(row["values"], dict):
            raise ValueError("Registry values must be an object")  # noqa: TRY004 - retained validator ValueError contract
        indexed[ident] = row
    grouped = defaultdict(dict)
    for diff in differences:
        if not isinstance(diff, dict) or set(diff) != {
            "id",
            "field",
            "registry",
            "canonical",
        }:
            raise ValueError("Exact difference shape required")
        ident, field = diff["id"], diff["field"]
        if (
            type(ident) is not int
            or ident not in indexed
            or field not in METADATA_FIELDS
        ):
            raise ValueError(
                "Difference must bind an existing item and qualified metadata field"
            )
        if field in grouped[ident] or field not in indexed[ident]["values"]:
            raise ValueError("No duplicate or absent registry field")
        if (
            diff["registry"] != indexed[ident]["values"][field]
            or diff["registry"] == diff["canonical"]
        ):
            raise ValueError("Stale registry difference or equal values")
        grouped[ident][field] = diff["canonical"]
    cases = []
    for ident, changed in grouped.items():
        row = indexed[ident]
        key = row["source_key"]
        original = dict(row["values"])
        candidate = dict(changed)
        # Record roles are explicit; neither panel is labelled an approved correction.
        original.update(
            ValueRole="Retained registry values; correction provenance unresolved",
            RegistryItemID=ident,
            SnapshotRevision=registry_revision,
        )
        candidate.update(
            ValueRole="Canonical source values for disputed fields; proposal only; context title from registry",
            ContextTitle=row["values"].get("Title"),
            RegistryItemID=ident,
            SnapshotRevision=source_revision,
        )
        for link in ("PubMedURL", "DORAURL"):
            if link in row["values"]:
                candidate[link] = row["values"][link]
        evidence = row["evidence"]
        if not isinstance(evidence, list):
            raise ValueError("Evidence must be an array")  # noqa: TRY004 - retained validator ValueError contract
        canonical_evidence = [
            dict(e, evidence_id="canonical:" + e["evidence_id"]) for e in evidence
        ]
        records = [
            {
                "record_id": f"registry:{ident}",
                "source_key": key,
                "values": original,
                "evidence": evidence,
            },
            {
                "record_id": f"canonical-for:{ident}",
                "source_key": key,
                "values": candidate,
                "evidence": canonical_evidence,
            },
        ]
        cases.append(
            build_case(
                records,
                "metadata_conflict",
                RULE_VERSION,
                source_revision + "|registry:" + registry_revision,
            )
        )
    return tuple(sorted(cases, key=lambda x: x.case_id))


def review_page(cases, page_index, page_size=20):
    """Explicit pages for the existing bounded reviewer; never silently truncates."""
    if (
        type(page_index) is not int
        or page_index < 0
        or type(page_size) is not int
        or not 1 <= page_size <= 20
    ):
        raise ValueError("Qualified zero-based page and size1..20 required")
    cases = tuple(cases)
    if len({c.case_id for c in cases}) != len(cases):
        raise ValueError("Unique cases required")
    pages = (len(cases) + page_size - 1) // page_size
    if page_index >= pages:
        raise ValueError("Page outside complete case set")
    return {
        "cases": cases[page_index * page_size : (page_index + 1) * page_size],
        "page_index": page_index,
        "page_count": pages,
        "total_cases": len(cases),
        "remaining_after_page": max(0, len(cases) - (page_index + 1) * page_size),
    }


def build_metadata_review_slice(
    definition,
    cases,
    *,
    canonical_query,
    canonical_rows,
    dataset,
    list_id,
    registry_items,
    sharepoint_host,
    total_cases=None,
):
    """Bounded existing-flow slice; drift guards precede review/cache effects.

    The original identity acquisition/cache/AI graph is retained. Native source
    and registry reads must match the supplied snapshots before frozen cases are
    rendered. Local code prepares the definition; Microsoft executes it.
    """
    import copy
    import re

    from .prepare_reconciliation_review_flow import (
        update_review_renderer,
        workflow_data_text,
    )

    if not isinstance(cases, list) or not 1 <= len(cases) <= 20:
        raise ValueError("One complete selected page of1..20 cases required")
    if total_cases is None:
        total_cases = len(cases)
    if type(total_cases) is not int or total_cases < len(cases):
        raise ValueError("Honest complete case count required")
    ids = set()
    for c in cases:
        rebuilt = build_case(
            c.get("records"),
            c.get("issue"),
            c.get("rule_version"),
            c.get("source_revision"),
        )
        if (
            c.get("case_id") != rebuilt.case_id
            or c.get("source_fingerprint") != rebuilt.source_fingerprint
            or rebuilt.issue != "metadata_conflict"
        ):
            raise ValueError("Exact metadata case revision required")
        pairs = {r["record_id"]: r for r in c["records"]}
        regs = [r for key, r in pairs.items() if key.startswith("registry:")]
        if len(regs) != 1:
            raise ValueError("Exactly one retained registry record per case")
        ident = int(regs[0]["record_id"].split(":")[1])
        ids.add(ident)
    if (
        len(ids) != len(cases)
        or {r["Id"] for r in registry_items} != ids
        or len(registry_items) != len(ids)
    ):
        raise ValueError("Complete unique selected registry snapshot required")
    if (
        len(canonical_rows) != len(cases)
        or not isinstance(canonical_query, str)
        or not canonical_query.startswith("EVALUATE SELECTCOLUMNS(")
    ):
        raise ValueError("Exact complete canonical projection required")
    canonical_by_pmid = {r["[PMID]"]: r for r in canonical_rows}
    if len(canonical_by_pmid) != len(canonical_rows):
        raise ValueError("Unique canonical PMID source required")
    registry_by_id = {r["Id"]: r for r in registry_items}
    fields = {
        "Title": "Title",
        "Authors": "field_3",
        "Journal": "field_4",
        "PublicationYear": "field_5",
        "PublicationMonth": "field_6",
        "PublicationDateRaw": "field_7",
        "PublicationDatePrecision": "field_8",
        "CHHHSAffiliatedAuthors": "field_15",
        "MatchedFacilities": "field_14",
    }
    for c in cases:
        original = next(
            r for r in c["records"] if r["record_id"].startswith("registry:")
        )
        ident = int(original["record_id"].split(":")[1])
        key = original["source_key"]
        if not key.startswith("pubmed:") or registry_by_id[ident]["field_1"] != key:
            raise ValueError("Qualified exact PubMed registry source identity required")
        canonical = next(
            (r for r in c["records"] if r["record_id"] == f"canonical-for:{ident}"),
            None,
        )
        if (
            canonical is None
            or canonical["source_key"] != key
            or key.split(":")[1] not in canonical_by_pmid
        ):
            raise ValueError("Source pair must bind the exact canonical PMID")
        for field, internal in fields.items():
            if field in original["values"] and original["values"][
                field
            ] != registry_by_id[ident].get(internal):
                raise ValueError("Original case differs from native registry snapshot")
            if field in canonical["values"] and canonical["values"][
                field
            ] != canonical_by_pmid[key.split(":")[1]].get("[" + field + "]"):
                raise ValueError(
                    "Candidate case differs from canonical source snapshot"
                )
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", list_id) or not dataset.startswith(
        "https://"
    ):
        raise ValueError("Qualified existing native dataset/list required")
    d = copy.deepcopy(definition)
    actions = d["actions"]
    if (
        d["parameters"].get("reconciliationNewPredictionLimit", {}).get("defaultValue")
        != 0
    ):
        raise ValueError("Metadata human fallback must retain zero new AI calls")
    if any(k.startswith("Metadata_") for k in actions):
        raise ValueError("Do not overwrite existing metadata slice")

    def walk(nodes):
        for name, node in nodes.items():
            yield name, node
            yield from walk(node.get("actions", {}))
            yield from walk(node.get("else", {}).get("actions", {}))

    update_review_renderer(d)
    for name, node in walk(actions):
        if name == "Review_HTML":
            old = "Identity exceptions selected from the revision-bound canonical source; configured AI text is advisory."
            if old not in node["inputs"]:
                raise ValueError("Qualified original canonical review heading required")
            node["inputs"] = node["inputs"].replace(
                old,
                f"Selected {len(cases)} of {total_cases} retained metadata cases. All other cases remain preserved. "
                "AI calls are disabled for this slice; proposed source values are not approved corrections.",
            )
    query = copy.deepcopy(actions["Read_canonical_exceptions"])
    query["inputs"]["parameters"]["specification/query"] = canonical_query
    query["runAfter"] = {"Select_runtime_cases": ["Succeeded"]}
    actions["Metadata_Read_Source"] = query
    cols = [
        "Id",
        "field_1",
        "Title",
        "field_3",
        "field_4",
        "field_5",
        "field_6",
        "field_7",
        "field_8",
        "field_12",
        "field_13",
        "field_14",
        "field_15",
        "field_17",
        "field_18",
    ]
    uri = (
        "_api/web/lists(guid'"
        + list_id
        + "')/items?$select="
        + ",".join(cols)
        + "&$filter="
        + " or ".join("Id eq " + str(i) for i in sorted(ids))
        + "&$orderby=Id asc&$top=21"
    )
    host = copy.deepcopy(sharepoint_host)
    host["operationId"] = "HttpRequest"
    actions["Metadata_Read_Registry"] = {
        "type": "OpenApiConnection",
        "inputs": {
            "host": host,
            "parameters": {
                "dataset": dataset,
                "parameters/method": "GET",
                "parameters/uri": uri,
                "parameters/headers": {"Accept": "application/json;odata=verbose"},
            },
        },
        "runAfter": {"Metadata_Read_Source": ["Succeeded"]},
    }
    actual = "body('Metadata_Read_Registry')?['d']?['results']"
    projection = {c: "@item()?['" + c + "']" for c in cols}
    projection["field_5"] = (
        "@if(equals(item()?['field_5'],null),null,int(item()?['field_5']))"
    )
    for link in ("field_12", "field_13"):
        projection[link] = "@item()?['" + link + "']?['Url']"
    actions["Metadata_Select_Registry"] = {
        "type": "Select",
        "inputs": {"from": "@" + actual, "select": projection},
        "runAfter": {"Metadata_Read_Registry": ["Succeeded"]},
    }
    expected = [
        {c: r.get(c) for c in cols}
        for r in sorted(registry_items, key=lambda x: x["Id"])
    ]
    for row in expected:
        if row["field_5"] is not None:
            row["field_5"] = int(row["field_5"])
        for link in ("field_12", "field_13"):
            if isinstance(row[link], dict):
                row[link] = row[link].get("Url")
    rows = "body('Metadata_Read_Source')?['results'][0]?['tables'][0]?['rows']"
    # Static data has a nonexpression prefix; embedded source text cannot become
    # a workflow expression. Short comparisons avoid the native8192 limit.
    actions["Metadata_Expected_Snapshots"] = {
        "type": "Compose",
        "inputs": workflow_data_text(
            {"registry": expected, "canonical": canonical_rows}
        ),
        "runAfter": {"Metadata_Select_Registry": ["Succeeded"]},
    }
    expected_ref = "json(substring(outputs('Metadata_Expected_Snapshots'),5))"
    expression = (
        "@and(equals(length("
        + actual
        + "),"
        + str(len(ids))
        + "),equals(string(body('Metadata_Select_Registry')),string("
        + expected_ref
        + "?['registry'])),equals(string("
        + rows
        + "),string("
        + expected_ref
        + "?['canonical'])))"
    )
    actions["Metadata_Guard_Snapshots"] = {
        "type": "If",
        "expression": expression,
        "actions": {},
        "else": {
            "actions": {
                "Metadata_Stop_Drift": {
                    "type": "Terminate",
                    "inputs": {
                        "runStatus": "Failed",
                        "runError": {
                            "code": "METADATA_REVIEW_SNAPSHOT_DRIFT",
                            "message": "Source/registry no longer matches the selected review snapshot. No review or correction was produced.",
                        },
                    },
                }
            }
        },
        "runAfter": {"Metadata_Expected_Snapshots": ["Succeeded"]},
    }
    actions["Metadata_Frozen_Cases_Text"] = {
        "type": "Compose",
        "inputs": workflow_data_text(cases),
        "runAfter": {"Metadata_Guard_Snapshots": ["Succeeded"]},
    }
    actions["Frozen_cases"]["inputs"] = (
        "@json(substring(outputs('Metadata_Frozen_Cases_Text'),5))"
    )
    actions["Frozen_cases"]["runAfter"] = {"Metadata_Frozen_Cases_Text": ["Succeeded"]}
    return d
