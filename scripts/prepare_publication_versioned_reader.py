"""Upgrade the accepted publication reader to retained as-of views, without I/O effects.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil

try:
    from .prepare_publication_outcome_reader import (
        MAIN, button, fingerprint, inherited, label, literal, position, projection, read, text, write,
    )
    from .prepare_publication_reporting_snapshot import FACT, VIEW, FIELDS
except ImportError:
    from prepare_publication_outcome_reader import (
        MAIN, button, fingerprint, inherited, label, literal, position, projection, read, text, write,
    )
    from prepare_publication_reporting_snapshot import FACT, VIEW, FIELDS

EVIDENCE = "PublicationVersionEvidence"
MEASURE_MAP = {
    "Publications": "V01 Included publications",
    "K01 Publications in complete months": "V01 Publications in complete months",
    "K02 OA rate among assessed": "V01 OA rate among assessed",
    "K02 OA assessment coverage": "V01 OA assessment coverage",
    "K02 Known open publications": "V01 Open publications",
    "K02 Known closed publications": "V01 Closed publications",
    "K02 Unknown OA publications": "V01 Unknown OA publications",
    "Publications Without Usable Month": "V01 Publications without usable month",
    "Reporting Month": "V01 Reporting month",
}


def version_bindings(value):
    """Translate every primary query/filter/sort reference, including SQ aliases."""
    if isinstance(value, list):
        return [version_bindings(x) for x in value]
    if not isinstance(value, dict):
        if isinstance(value, str):
            for old, new in MEASURE_MAP.items():
                if value == "Publication." + old:
                    return FACT + "." + new
            for field in FIELDS:
                if value == "Publication." + field:
                    return FACT + "." + field
        return value
    result = copy.deepcopy(value)
    for kind in ("Column", "Measure"):
        expression = result.get(kind)
        if expression:
            ref = expression.get("Expression", {}).get("SourceRef", {})
            if ref.get("Entity") == "Publication":
                field = expression["Property"]
                if kind == "Measure":
                    if field not in MEASURE_MAP:
                        raise ValueError("Unmapped publication metric: " + field)
                    ref["Entity"], expression["Property"] = FACT, MEASURE_MAP[field]
                else:
                    if field not in FIELDS:
                        raise ValueError("Unretained publication field: " + field)
                    ref["Entity"] = FACT
            # The existing positive-work filter uses a From alias.
            elif ref.get("Source") == "p" and kind == "Measure":
                if expression["Property"] != "Publications":
                    raise ValueError("Unexpected aliased publication filter")
                expression["Property"] = MEASURE_MAP["Publications"]
    if result.get("Entity") == "Publication" and result.get("Name") == "p":
        result["Entity"] = FACT
    return {k: version_bindings(v) for k, v in result.items()}


def positive_filter():
    return {"name": "t18-version-visible-work", "type": "Advanced",
        "field": projection(FACT, "V01 Included publications", True)["field"],
        "filter": {"Version": 2, "From": [{"Name": "v", "Entity": FACT, "Type": 0}],
            "Where": [{"Condition": {"Comparison": {"ComparisonKind": 1,
                "Left": {"Measure": {"Expression": {"SourceRef": {"Source": "v"}},
                    "Property": "V01 Included publications"}},
                "Right": {"Literal": {"Value": "0L"}}}}}]}}


def prepare(source, output, expected_sha256):
    source, output = Path(source), Path(output)
    if fingerprint(source) != expected_sha256:
        raise ValueError("Exact reader preimage mismatch")
    if output.exists():
        raise FileExistsError("Refusing to overwrite a versioned reader candidate")
    pages = source / "definition/pages"
    if (pages / EVIDENCE).exists():
        raise ValueError("Versioned evidence already exists; reconcile rather than duplicate")
    before = {p.relative_to(source).as_posix(): p.read_bytes()
              for p in source.rglob("*") if p.is_file()}
    shutil.copytree(source, output)
    main = output / "definition/pages" / MAIN
    for path in (main / "visuals").glob("*/visual.json"):
        write(path, version_bindings(read(path)))

    trend_path = main / "visuals/annual-trajectory/visual.json"
    trend = read(trend_path)
    trend["visual"]["query"]["queryState"]["Category"] = {
        "projections": [projection("Date", "MonthStart", label="Month")]}
    trend["visual"]["query"]["sortDefinition"] = {"sort": [{
        "field": projection("Date", "MonthStart")["field"], "direction": "Ascending"}],
        "isDefaultSort": True}
    # A continuous axis reduces label collisions while the measure still counts
    # complete months only; no daily interpolation or shorter reporting window.
    axes = trend["visual"].setdefault("objects", {}).setdefault("categoryAxis", [])
    for entry in axes:
        entry.get("properties", {}).pop("axisType", None)
    axes.append({"properties": {"axisType": text("Scalar")}})
    write(trend_path, trend)

    def put(folder, visual):
        write(folder / "visuals" / visual["name"] / "visual.json", visual)

    period = read(main / "visuals/t18-reporting-period/visual.json")
    put(main, position(period, 32, 944, 352, 128, 13000))
    selector = inherited(read(main / "visuals/source-filter/visual.json"))
    selector["name"] = "t18-version"
    selector["visual"]["query"] = {"queryState": {"Values": {
        "projections": [projection(VIEW, "ViewLabel")]}}}
    selector.pop("filterConfig", None)
    selector["visual"]["objects"] = {
        "selection": [{"properties": {"strictSingleSelect": literal("true"), "singleSelect": literal("true")}}],
        "data": [{"properties": {"mode": text("Dropdown")}}],
        "general": [{"properties": {"filter": {"filter": {
            "Version": 2, "From": [{"Name": "v", "Entity": VIEW, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "v"}}, "Property": "ViewLabel"}}],
                "Values": [[{"Literal": {"Value": "'Current / restated evidence'"}}]]}}}]}}}}]}
    put(main, position(label(selector, "Evidence version"), 400, 944, 592, 128, 14000))
    definitions = read(main / "visuals/t18-definitions/visual.json")
    put(main, position(definitions, 1008, 960, 424, 96, 15000))
    drill = read(main / "visuals/t18-drill/visual.json")
    drill["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]["drillthroughSection"] = text(EVIDENCE)
    put(main, position(drill, 1448, 960, 440, 96, 16000))

    detail = output / "definition/pages" / EVIDENCE
    page = copy.deepcopy(read(main / "page.json"))
    page.update(name=EVIDENCE, displayName="Publication version evidence")
    filters = [("Facility", "FacilityName"), (VIEW, "ViewLabel"),
               (FACT, "SourceSet"), (FACT, "PublicationYear"), (FACT, "AttributionStatus")]
    page["pageBinding"] = {"name": "T18PublicationVersionEvidence", "type": "Drillthrough",
        "acceptsFilterContext": "Default", "parameters": [
            {"name": "VersionEvidence" + str(i), "boundFilter": "t18-version-drill-" + str(i),
             "asAggregation": False, "fieldExpr": projection(table, field)["field"]}
            for i, (table, field) in enumerate(filters)]}
    page["filterConfig"] = {"filters": [
        {"name": "t18-version-drill-" + str(i), "type": "Categorical", "howCreated": "Drillthrough",
         "field": projection(table, field)["field"]} for i, (table, field) in enumerate(filters)]}
    write(detail / "page.json", page)
    schema = trend["$schema"]
    put(detail, position(button(schema, "t18-version-back", "Back to publications", "Back"), 1448, 16, 440, 80, 1000))

    def table(name, title, projections, pos, filtered=False):
        visual = {"$schema": schema, "name": name, "visual": {
            "visualType": "tableEx", "query": {"queryState": {"Values": {"projections": projections}}},
            "objects": {"columnHeaders": [{"properties": {"wordWrap": literal("true")}}],
                "values": [{"properties": {"wordWrap": literal("true"), "urlIcon": literal("true")}}]}}}
        for p in projections:
            p["active"] = True
            if p.get("field", {}).get("Column", {}).get("Property") in {"PubMedURL", "DORAURL"}:
                visual["visual"]["objects"].setdefault("columnFormatting", []).append({
                    "selector": {"metadata": p["queryRef"]}, "properties": {"backColor": {
                        "solid": {"color": {"expr": {"ThemeDataColor": {"ColorId": 2, "Percent": 0.9}}}}}}})
        if filtered:
            visual["filterConfig"] = {"filters": [positive_filter()]}
        put(detail, position(label(visual, title), *pos))

    table("t18-version-metadata", "Selected evidence — technical baselines are not issued originals", [
        projection(VIEW, field, label=caption) for field, caption in (
            ("ViewLabel", "Evidence version"), ("CutoffExclusive", "Cutoff exclusive"),
            ("CapturedUTC", "Captured UTC"), ("MetricVersion", "Metric version"),
            ("ModelRevision", "Model revision"), ("ReportRevision", "Report revision"))],
        (32, 112, 1856, 176, 2000))
    table("t18-version-source", "Source batches and retained input identity", [
        projection(VIEW, "SourceVersions", label="Retained source batches"),
        projection(VIEW, "InputSHA256", label="Frozen input SHA-256")], (32, 304, 1856, 144, 3000))
    table("t18-version-change", "Restatement and unavailable-original explanation", [
        projection(FACT, metric, True, caption) for metric, caption in (
            ("V01 Restatement reason", "Reason"), ("V01 Affected periods", "Affected periods"))],
        (32, 464, 1856, 144, 4000))
    table("t18-version-works", "Selected version — publication evidence", [
        projection(FACT, field, label=caption) for field, caption in (
            ("CanonicalKey", "Canonical key"), ("Title", "Publication"), ("SourceSet", "Provenance"),
            ("PublicationDateRaw", "Date"), ("PublicationDatePrecision", "Precision"))] + [
        projection(FACT, metric, True, caption) for metric, caption in (
            ("V01 Open publications", "Open"), ("V01 Closed publications", "Closed"),
            ("V01 Unknown OA publications", "Unknown"))] + [
        projection(FACT, field, label=caption) for field, caption in (
            ("PubMedURL", "PubMed"), ("DORAURL", "DORA"), ("OAHashes", "Retained OA input hashes"))],
        (32, 624, 1856, 432, 5000), True)
    order_path = output / "definition/pages/pages.json"
    order = read(order_path)
    order["pageOrder"].insert(order["pageOrder"].index(MAIN) + 1, EVIDENCE)
    # This selected reader opens on its graphical overview, independently of
    # the preserved source report's legacy monthly landing page.
    order["activePageName"] = MAIN
    order["landingPageName"] = MAIN
    write(order_path, order)
    unchanged = [name for name in before if not name.startswith("definition/pages/" + MAIN + "/")
                 and name != "definition/pages/pages.json"]
    for name in unchanged:
        if (output / name).read_bytes() != before[name]:
            raise ValueError("Unrelated reader part changed: " + name)
    return {"sourceSHA256": expected_sha256, "unaffectedPartsExact": len(unchanged),
            "evidencePage": EVIDENCE, "nativeSaveSubmitted": False,
            "requiresQualifiedModel": {"tables": [FACT, VIEW], "column": "Date.MonthStart",
                                       "measures": sorted(set(MEASURE_MAP.values()))}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output, args.sha256), indent=2))
