"""Prepare additive T18 publication measures from an exact native model preimage.

No service calls or processing occur here. OA assessment describes retained
OpenAlex status observations, not paper availability or institutional coverage.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import re
from pathlib import Path

PATH = "definition/tables/Publication.tmdl"
VERSION = "T18-publications-1"
OPEN = frozenset({"gold", "green", "hybrid", "bronze", "diamond"})
KNOWN = OPEN | {"closed"}


def oa_expression(statuses):
    allowed = ", ".join(json.dumps(s) for s in sorted(statuses))
    return '''VAR AssessedKeys = FILTER(
    ALL(OpenAlexPublicationContext[CanonicalKey]),
    VAR WorkKey = OpenAlexPublicationContext[CanonicalKey]
    VAR Observations = FILTER(ALL(OpenAlexPublicationContext),
        OpenAlexPublicationContext[CanonicalKey] = WorkKey)
    VAR Statuses = DISTINCT(SELECTCOLUMNS(Observations, "StatusValue",
        LOWER(TRIM(OpenAlexPublicationContext[OpenAccessStatus_OpenAlex]))))
    VAR StatusValue = MAXX(Statuses, [StatusValue])
    VAR Undated = COUNTROWS(FILTER(Observations,
        ISBLANK(OpenAlexPublicationContext[OpenAccessStatus_OpenAlex_ObservedUTC])))
    RETURN NOT ISBLANK(WorkKey) && COUNTROWS(Statuses) = 1
        && COALESCE(Undated, 0) = 0 && StatusValue IN {''' + allowed + '''})
RETURN CALCULATE([Publications],
    KEEPFILTERS(TREATAS(AssessedKeys, Publication[CanonicalKey])))'''


MEASURES = {
    "K01 Publications in complete months": 'CALCULATE([Publications Last 24 Complete Months], KEEPFILTERS(Publication[PublicationDatePrecision] IN {"day", "month"}))',
    "K02 OA assessed publications": oa_expression(KNOWN),
    "K02 Known open publications": oa_expression(OPEN),
    "K02 Known closed publications": oa_expression({"closed"}),
    "K02 Unknown OA publications": "[Publications] - [K02 OA assessed publications]",
    "K02 OA rate among assessed": "DIVIDE([K02 Known open publications], [K02 OA assessed publications])",
    "K02 OA assessment coverage": "DIVIDE([K02 OA assessed publications], [Publications])",
}

DESCRIPTIONS = {
    "K01 Publications in complete months": "Included canonical works in the existing last-24-complete-month window with usable day/month precision. Year-only, uncertain and missing months are excluded and remain separately visible; existing export measures are unchanged.",
    "K02 OA assessed publications": "Included canonical works with exactly one recognised, dated retained OpenAlex OA status; conflicting or absent evidence is unknown.",
    "K02 Known open publications": "Included canonical works assessed as gold, green, hybrid, bronze or diamond in retained OpenAlex evidence; not proof of current full-text availability.",
    "K02 Known closed publications": "Included canonical works assessed as closed in dated retained OpenAlex evidence; missing evidence is never closed.",
    "K02 Unknown OA publications": "Included canonical works without one unambiguous recognised dated OA status; includes missing, undated, conflicting and unsupported observations.",
    "K02 OA rate among assessed": "Known open works divided by OA-assessed works in the current canonical/facility/date context; blank when none assessed. Pair with assessment coverage.",
    "K02 OA assessment coverage": "OA-assessed works divided by all included canonical works in the current context; blank when none included. Not a measure of staff or institutional coverage.",
}


def reference_counts(included_keys, observations):
    """Independent set-based reconciliation, retaining contradictory/undated OA."""
    included = set(included_keys)
    if any(not isinstance(k, str) or not k.strip() for k in included):
        raise ValueError("Canonical keys must be nonempty strings")
    groups = {}
    for row in observations:
        key = row["CanonicalKey"]
        if key in included:
            groups.setdefault(key, []).append(row)
    assessed, opened = set(), set()
    for key, rows in groups.items():
        statuses = {str(r.get("Status") or "").strip().lower() for r in rows}
        if (len(statuses) == 1 and statuses <= KNOWN
                and all(r.get("ObservedUTC") for r in rows)):
            assessed.add(key)
            if statuses <= OPEN:
                opened.add(key)
    total, count = len(included), len(assessed)
    return {"Included": total, "Assessed": count, "Open": len(opened),
            "Closed": count - len(opened), "Unknown": total - count,
            "Rate": len(opened) / count if count else None,
            "Coverage": count / total if total else None}


def unwrap(value):
    value = value.get("text", value)
    if isinstance(value, str):
        value = json.loads(value)
    return value.get("definition", value)


COMPARISON_PATH = "definition/tables/PublicationComparison.tmdl"
COMPARISON_TMDL = '''table PublicationComparison

\tcolumn 'Comparison Order'
\t\tdataType: int64
\t\tisHidden
\t\tformatString: 0
\t\tsummarizeBy: sum
\t\tsourceColumn: [Value3]

\tcolumn 'Comparison Fields'
\t\tdataType: string
\t\tisHidden
\t\tsummarizeBy: none
\t\tsourceColumn: [Value2]
\t\tsortByColumn: 'Comparison Order'
\t\textendedProperty ParameterMetadata = {"version":3,"kind":2}

\t/// Choose facility/service or source provenance for the same publication comparison plot; facility totals are non-additive.
\tcolumn Comparison
\t\tdataType: string
\t\tsummarizeBy: none
\t\tsourceColumn: [Value1]
\t\tsortByColumn: 'Comparison Order'
\t\trelatedColumnDetails
\t\t\tgroupByColumn: 'Comparison Fields'

\tpartition PublicationComparison = calculated
\t\tmode: import
\t\tsource =
\t\t\t{("Facility / service", NAMEOF(Facility[FacilityName]), 0),
\t\t\t ("Source provenance", NAMEOF(Publication[SourceSet]), 1)}
'''


def add_comparison_parameter(definition):
    """Add the two-choice field parameter; processing is a separate native gate."""
    result = copy.deepcopy(definition)
    parts = result["parts"]
    if any(p["path"] == COMPARISON_PATH for p in parts):
        raise ValueError("Comparison parameter exists; reconcile rather than duplicate")
    model = next((p for p in parts if p["path"] == "definition/model.tmdl"), None)
    if model is None:
        raise ValueError("Native model declaration missing")
    original = base64.b64decode(model["payload"], validate=True).decode()
    if "PublicationComparison" in original:
        raise ValueError("Existing parameter reference requires reconciliation")
    all_text = "\n".join(base64.b64decode(p["payload"], validate=True).decode()
                         for p in parts if p["path"].endswith(".tmdl"))
    for match in re.finditer(r"(?m)^\s*extendedProperty ParameterMetadata\s*=\s*(\{[^\n]+\})", all_text):
        if json.loads(match[1]).get("kind") == 2:
            raise ValueError("Existing field parameter requires review before adding another")
    for path, column in [(PATH, "SourceSet"), ("definition/tables/Facility.tmdl", "FacilityName")]:
        table = next((p for p in parts if p["path"] == path), None)
        if table is None or not re.search(r"(?m)^\tcolumn " + column + r"\s*$",
                base64.b64decode(table["payload"], validate=True).decode()):
            raise ValueError("Comparison field unavailable: " + column)
    model["payload"] = base64.b64encode((original.rstrip("\n") + "\n\nref table PublicationComparison\n").encode()).decode()
    parts.append({"path": COMPARISON_PATH, "payloadType": "InlineBase64",
                  "payload": base64.b64encode(COMPARISON_TMDL.encode()).decode()})
    return result


def prepare(preimage, expected_sha256, only=None):
    if hashlib.sha256(preimage).hexdigest() != expected_sha256:
        raise ValueError("Native preimage hash mismatch")
    definition = copy.deepcopy(unwrap(json.loads(preimage)))
    selected = list(MEASURES) if only is None else list(only)
    if not selected or len(selected) != len(set(selected)) or any(n not in MEASURES for n in selected):
        raise ValueError("Select a nonempty unique subset of the governed measures")
    parts = definition["parts"]
    paths = [p["path"] for p in parts]
    if len(paths) != len(set(paths)) or PATH not in paths:
        raise ValueError("Missing or duplicate native definition parts")
    table = next(p for p in parts if p["path"] == PATH)
    original = base64.b64decode(table["payload"], validate=True).decode("utf-8")
    dependencies = ["Publications", "Publications Last Complete Month", "Publications Without Usable Month"]
    if "K01 Publications in complete months" in selected:
        dependencies.append("Publications Last 24 Complete Months")
    if not all(re.search(r"(?m)^\tmeasure '?" + re.escape(n) + r"'?(?:\s|=)", original)
               for n in dependencies):
        raise ValueError("Required accepted publication measures are unavailable")
    context_path = "definition/tables/OpenAlexPublicationContext.tmdl"
    context = next((p for p in parts if p["path"] == context_path), None)
    if context is None:
        raise ValueError("Required native OA context missing")
    context_text = base64.b64decode(context["payload"], validate=True).decode("utf-8")
    for name in ("CanonicalKey", "OpenAccessStatus_OpenAlex", "OpenAccessStatus_OpenAlex_ObservedUTC"):
        if not re.search(r"(?m)^\tcolumn " + re.escape(name) + r"\s*$", context_text):
            raise ValueError("Required OA column unavailable: " + name)
    all_text = "\n".join(base64.b64decode(p["payload"], validate=True).decode("utf-8")
                         for p in parts if p["path"].endswith(".tmdl"))
    for name in selected:
        if re.search(r"(?m)^\tmeasure '" + re.escape(name) + r"'\s*=", all_text):
            raise ValueError("Existing outcome measure; reconcile rather than overwrite: " + name)
    additions = []
    for name in selected:
        expression = MEASURES[name]
        fmt = "0.0%" if name in {"K02 OA rate among assessed", "K02 OA assessment coverage"} else "#,0"
        additions.append("\t/// " + DESCRIPTIONS[name] + "\n\tmeasure '" + name + "' = ```\n\t\t\t"
                         + expression.replace("\n", "\n\t\t\t")
                         + "\n\t\t\t```\n\t\tformatString: " + fmt
                         + "\n\t\tdisplayFolder: T18 publication outcomes"
                         + "\n\t\tannotation RIMSMetricVersion = " + VERSION + "\n")
    # Table properties must precede child objects in TMDL. Insert before the
    # first member, never before lineageTag/isHidden or other table metadata.
    member = re.search(r"(?m)^\t(?:///|measure |column |partition |hierarchy )", original)
    if member is None:
        raise ValueError("Native table has no recognised insertion point")
    offset = member.start()
    changed = original[:offset] + "\n".join(additions) + "\n" + original[offset:]
    table["payload"] = base64.b64encode(changed.encode()).decode()
    return definition


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("preimage", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--only", action="append", choices=sorted(MEASURES))
    args = parser.parse_args()
    result = prepare(args.preimage.read_bytes(), args.sha256, args.only)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump({"definition": result}, stream, indent=2)
        stream.write("\n")
