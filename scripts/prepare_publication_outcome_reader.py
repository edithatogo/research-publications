"""Prepare the T18 publication reader without service calls or lost visual IDs.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = "ReportSection3"
DETAIL = "PublicationOutcomeDetails"
KEEP = {"all-papers", "annual-trajectory", "facility-breakdown", "attribution-breakdown",
        "facility-filter", "year-filter", "source-filter", "overview-unknown-month"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fingerprint(folder):
    h = hashlib.sha256()
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        h.update(path.relative_to(folder).as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return h.hexdigest()


def correct_window_captions(folder):
    """Relabel the existing window measure without implying source freshness."""
    changed = []
    for relative, expected in (
        ("ReportSection/visuals/refresh-time/visual.json", "Last model refresh (UTC)"),
        ("ReportSection2/visuals/bc5eb9d737e586c0cd91/visual.json", "Publication data refreshed · UTC"),
    ):
        path = Path(folder) / "definition/pages" / relative
        if not (Path(folder) / "definition/pages" / relative.split("/")[0]).exists():
            continue
        value = read(path)
        visual = value["visual"]
        if "Refresh Timestamp UTC" not in json.dumps(visual["query"]):
            raise ValueError("Window measure drift: " + relative)
        objects = visual["visualContainerObjects"]
        title = objects["title"][0]["properties"]["text"]
        if title != text(expected):
            raise ValueError("Window caption drift: " + relative)
        title.update(text("Window evaluated (UTC)"))
        objects["general"][0]["properties"]["altText"] = text("Reporting window evaluation time in UTC")
        for item in visual["query"]["queryState"].get("Values", {}).get("projections", []):
            item["nativeQueryRef"] = item["displayName"] = "Window evaluated (UTC)"
        write(path, value)
        changed.append("definition/pages/" + relative)
    return changed


def repair_reconciliation_controls(folder):
    """Give the existing web dropdowns room without changing their cohorts."""
    page = Path(folder) / "definition/pages/ReportSection"
    if not page.exists():
        return []
    changed = []
    layouts = {
        "reader-year": ((32, 448, 300, 88), (32, 544, 440, 112)),
        "reader-source": ((348, 448, 620, 88), (488, 544, 680, 112)),
        "reader-precision": ((984, 448, 904, 88), (1184, 544, 704, 112)),
        "reconciliation-register": ((32, 552, 1856, 352), (32, 672, 1856, 232)),
        "source-overlap": ((32, 224, 736, 208), (32, 224, 736, 304)),
        "dedup-method": ((792, 224, 528, 208), (792, 224, 528, 304)),
        "facility-contributions": ((1344, 224, 544, 208), (1344, 224, 544, 304)),
    }
    for name, (expected, target) in layouts.items():
        path = page / "visuals" / name / "visual.json"
        value = read(path)
        actual = tuple(value["position"][k] for k in ("x", "y", "width", "height"))
        if actual != expected:
            raise ValueError("Reconciliation layout drift: " + name)
        value["position"].update(zip(("x", "y", "width", "height"), target))
        if name.startswith("reader-"):
            value["visual"].setdefault("visualContainerObjects", {})["visualHeader"] = [
                {"properties": {"show": literal("false")}}]
        write(path, value)
        changed.append(path.relative_to(folder).as_posix())
    return changed


def repair_reconciliation_charts(folder):
    """Render the existing source/method counts without clipped donut labels."""
    page = Path(folder) / "definition/pages/ReportSection"
    if not page.exists():
        return []
    changed = []
    for name, expected_type in (("source-overlap", "donutChart"), ("dedup-method", "barChart")):
        path = page / "visuals" / name / "visual.json"
        value = read(path)
        visual = value["visual"]
        if visual["visualType"] != expected_type:
            raise ValueError("Reconciliation chart drift: " + name)
        if "Publication.Publications" not in json.dumps(visual["query"]):
            raise ValueError("Reconciliation count binding drift: " + name)
        visual["visualType"] = "clusteredColumnChart"
        visual["objects"] = {
            "general": [{"properties": {"responsive": literal("false")}}],
            "valueAxis": [{"properties": {"show": literal("false")}}],
            "labels": [{"properties": {"show": literal("true"), "labelDisplayUnits": literal("1D"),
                                        "labelPrecision": literal("0D")}}],
        }
        visual.setdefault("visualContainerObjects", {})["subTitle"] = [
            {"properties": {"show": literal("false")}}]
        if name == "dedup-method":
            visual["visualContainerObjects"]["general"] = [{"properties": {"altText": text(
                "Publication counts by retained reconciliation method. Long labels include "
                "invalid-identifiers-needs-review and possible-title+year-needs-review. "
                "Full source values remain in the register's DedupMethod column.")}}]
        filters = value.setdefault("filterConfig", {}).setdefault("filters", [])
        filters.append(positive_publication_filter("t18-reconciliation-positive-" + name))
        write(path, value)
        changed.append(path.relative_to(folder).as_posix())
    return changed


def inherit_neutral_text_colors(folder):
    """Let themes own fixed neutral text; preserve data/conditional colours."""
    neutrals = {"#172B4D", "#475569", "#0F172A", "#17354A", "#243746", "#64748B"}

    def fixed_color(value):
        if isinstance(value, str):
            return value.upper()
        if isinstance(value, dict):
            color = value.get("solid", {}).get("color", {})
            if isinstance(color, str):
                return color.upper()
            return color.get("expr", {}).get("Literal", {}).get("Value", "").strip("'").upper()
        return ""

    def clean(value):
        if isinstance(value, list):
            return [clean(x) for x in value]
        if not isinstance(value, dict):
            return value
        result = {}
        for key, child in value.items():
            if key == "fontColor" and fixed_color(child) in neutrals:
                continue
            if key == "textStyle" and isinstance(child, dict):
                child = dict(child)
                if fixed_color(child.get("color")) in neutrals:
                    child.pop("color")
            result[key] = clean(child)
        return result

    changed = []
    for path in (Path(folder) / "definition/pages").glob("*/visuals/*/visual.json"):
        before = read(path)
        after = copy.deepcopy(before)
        # Never transform query/filter expressions, including colour expressions
        # supplied by data. Only fixed presentation properties are eligible.
        visual = after["visual"]
        for section in ("objects", "visualContainerObjects"):
            if section in visual:
                visual[section] = clean(visual[section])
        for role in ("labels", "categoryLabels", "categoryAxis", "valueAxis", "legend"):
            for entry in visual.get("objects", {}).get(role, []):
                props = entry.get("properties", {})
                for key in ("color", "labelColor", "titleColor"):
                    if fixed_color(props.get(key)) in neutrals:
                        props.pop(key)
        for entry in visual.get("visualContainerObjects", {}).get("background", []):
            props = entry.get("properties", {})
            if fixed_color(props.get("color")) in {"#E9F2F8", "#D8EAF5"}:
                props.pop("color")
        if after != before:
            write(path, after)
            changed.append(path.relative_to(folder).as_posix())
    return changed


def repair_publication_evidence_styles(folder):
    """Keep source groups and source links legible in either report theme."""
    changed = []
    detail = Path(folder) / "definition/pages" / DETAIL
    chart_path = detail / "visuals/provenance-breakdown/visual.json"
    if chart_path.exists():
        chart = read(chart_path)
        if chart["visual"]["visualType"] != "donutChart":
            raise ValueError("Evidence provenance chart drift")
        chart["visual"]["visualType"] = "clusteredColumnChart"
        chart["visual"]["objects"] = {
            "general": [{"properties": {"responsive": literal("false")}}],
            "labels": [{"properties": {"show": literal("true"), "labelDisplayUnits": literal("1D"), "labelPrecision": literal("0D")}}]}
        chart["visual"].setdefault("visualContainerObjects", {})["subTitle"] = [{"properties": {"show": literal("false")}}]
        chart.setdefault("filterConfig", {}).setdefault("filters", []).append(positive_publication_filter("t18-evidence-source-positive"))
        chart["position"]["width"] = 736
        write(chart_path, chart)
        changed.append(chart_path.relative_to(folder).as_posix())
        for name in ("overview-coverage", "overview-scope"):
            path = detail / "visuals" / name / "visual.json"
            value = read(path)
            value["position"].update(x=784, width=1104)
            write(path, value)
            changed.append(path.relative_to(folder).as_posix())
    for path in (Path(folder) / "definition/pages").glob("*/visuals/*/visual.json"):
        value = read(path)
        visual = value["visual"]
        if visual.get("visualType") != "tableEx":
            continue
        fields = [p for p in visual.get("query", {}).get("queryState", {}).get("Values", {}).get("projections", [])
                  if p.get("field", {}).get("Column", {}).get("Property") in {"PubMedURL", "DORAURL"}]
        if not fields:
            continue
        formats = visual.setdefault("objects", {}).setdefault("columnFormatting", [])
        for field in fields:
            metadata = field["queryRef"]
            item = next((x for x in formats if x.get("selector", {}).get("metadata") == metadata), None)
            if item is None:
                item = {"selector": {"metadata": metadata}, "properties": {}}
                formats.append(item)
            if "backColor" in item["properties"]:
                raise ValueError("Preserve existing publication-link background rule: " + metadata)
            # The native URL glyph ignores column font colour. A light tint
            # of the theme accent preserves contrast for its fixed blue glyph.
            item["properties"]["backColor"] = {"solid": {"color": {"expr": {
                "ThemeDataColor": {"ColorId": 2, "Percent": 0.9}}}}}
        write(path, value)
        changed.append(path.relative_to(folder).as_posix())
    return changed


def repair_declared_evidence_links(folder):
    """Tint native WebUrl cells whose fixed blue glyph ignores foreground colour.

    These exact table/column pairs are declared WebUrl in the accepted native
    model definition. Ordinary identifier or source-text columns stay untouched.
    """
    declared = {
        "Publication": {"PubMedURL", "DORAURL"},
        "ResearcherPublicationMentions": {"PubMedURL", "DORAURL"},
        "ARCAwardContext": {"URL"},
        "Funding Relationship Context": {"EvidenceURL", "NativeSourceURL", "PublicationURL", "SourceAwardURL"},
        "Study register": {"SourceURL", "ArchiveFileURL"}}
    tint = {"solid": {"color": {"expr": {"ThemeDataColor": {"ColorId": 2, "Percent": 0.9}}}}}
    edits = []
    for path in (Path(folder) / "definition/pages").glob("*/visuals/*/visual.json"):
        value = read(path)
        visual = value["visual"]
        if visual.get("visualType") != "tableEx":
            continue
        before = json.dumps(value, sort_keys=True)
        projections = visual.get("query", {}).get("queryState", {}).get("Values", {}).get("projections", [])
        for projection_value in projections:
            field = projection_value.get("field", {})
            field = field.get("Aggregation", {}).get("Expression", field)
            column = field.get("Column", {})
            entity = column.get("Expression", {}).get("SourceRef", {}).get("Entity")
            if column.get("Property") not in declared.get(entity, set()):
                continue
            metadata = projection_value["queryRef"]
            formats = visual.setdefault("objects", {}).setdefault("columnFormatting", [])
            item = next((x for x in formats if x.get("selector", {}).get("metadata") == metadata), None)
            if item is None:
                item = {"selector": {"metadata": metadata}, "properties": {}}
                formats.append(item)
            props = item["properties"]
            if "backColor" in props and props["backColor"] != tint:
                raise ValueError("Preserve existing evidence-link background rule: " + metadata)
            props["backColor"] = tint
        if json.dumps(value, sort_keys=True) != before:
            edits.append((path, value))
    for path, value in edits:
        write(path, value)
    return [path.relative_to(folder).as_posix() for path, _ in edits]


def repair_evidence_control_space(folder):
    """Provide room for inherited readable dropdown text without changing queries."""
    root = Path(folder) / "definition/pages"
    edits = []
    targets = {
        "ResearcherEvidence": {
            "researcher-label": (160, 90, 160, 112),
            "researcher-year": (160, 90, 160, 112),
            "researcher-source": (160, 90, 160, 112),
            "researcher-groups": (268, 660, 288, 640),
            "researcher-publications": (268, 660, 288, 640)},
        "ARCAwardContextReader": {
            "funding-state": (1030, 80, 1030, 128),
            "funding-candidates": (1030, 80, 1030, 128),
            "funding-confirmed": (1030, 80, 1030, 128),
            "funding-unclassified": (1030, 80, 1030, 128),
            "funding-note": (1030, 80, 1030, 128),
            "funding-records": (1126, 260, 1174, 260),
            "arc-footer": (1402, 84, 1450, 84)}}
    for page, visuals in targets.items():
        for name, (old_y, old_h, y, height) in visuals.items():
            path = root / page / "visuals" / name / "visual.json"
            if not path.exists():
                continue
            value = read(path)
            if (value["position"]["y"], value["position"]["height"]) != (old_y, old_h):
                raise ValueError("Evidence control layout drift: " + page + "/" + name)
            value["position"].update(y=y, height=height)
            edits.append((path, value))
    page_path = root / "ARCAwardContextReader/page.json"
    if page_path.exists():
        page = read(page_path)
        page["height"] = max(page["height"], 1560)
        edits.append((page_path, page))
    for path, value in edits:
        write(path, value)
    return [path.relative_to(folder).as_posix() for path, _ in edits]


def repair_retained_pubmed_observation(folder):
    """Show the accepted retained observation, independent of unready Fresh tables."""
    page = Path(folder) / "definition/pages/SourceFreshness/visuals"
    path = page / "observed-0/visual.json"
    if not path.exists():
        return []
    value = read(path)
    projection_value = value["visual"]["query"]["queryState"]["Data"]["projections"][0]
    aggregate = projection_value["field"]["Aggregation"]
    column = aggregate["Expression"]["Column"]
    if (aggregate["Function"] != 4 or column["Property"] != "RefreshedAtUTC"
            or column["Expression"]["SourceRef"]["Entity"] != "FreshSearchAudit"):
        raise ValueError("PubMed observation binding drift; preserve the exact qualified event")
    column["Expression"]["SourceRef"]["Entity"] = "RetainedPubMedPublications"
    projection_value["queryRef"] = "Max(RetainedPubMedPublications.RefreshedAtUTC)"
    caption = "PubMed — retained observation UTC"
    projection_value["nativeQueryRef"] = projection_value["displayName"] = caption
    objects = value["visual"]["visualContainerObjects"]
    objects["general"][0]["properties"]["altText"] = text(caption)
    objects["title"][0]["properties"]["text"] = text(caption)
    objects["visualHeaderTooltip"][0]["properties"]["text"] = text(caption)
    note_path = page / "source-0/visual.json"
    note = json.dumps(read(note_path), ensure_ascii=False)
    old = "Search execution observation; not publication or provider update."
    if note.count(old) != 3:
        raise ValueError("PubMed observation explanation drift")
    note = note.replace(old, "Observation stamp in accepted retained PubMed rows; not provider update or complete coverage.")
    # Validate both qualified preimages before changing either local part.
    write(path, value)
    write(note_path, json.loads(note))
    return [p.relative_to(folder).as_posix() for p in (path, note_path)]


def literal(value):
    return {"expr": {"Literal": {"Value": value}}}


def text(value):
    return literal("'" + value.replace("'", "''") + "'")


def projection(table, name, measure=False, label=None):
    field = {"Measure" if measure else "Column": {
        "Expression": {"SourceRef": {"Entity": table}}, "Property": name}}
    result = {"field": field, "queryRef": table + "." + name,
              "nativeQueryRef": label or name, "displayName": label or name}
    if not measure:
        result["active"] = True
    return result


def inherited(value):
    """New/modified primary visuals inherit all colour/font literals from theme."""
    if isinstance(value, dict):
        return {key: inherited(child) for key, child in value.items()
                if key not in {"fontSize", "fontFamily", "fontFace", "fontColor", "color"}}
    if isinstance(value, list):
        return [inherited(child) for child in value]
    return value


def position(v, x, y, width, height, order):
    v["position"] = {"x": x, "y": y, "width": width, "height": height,
                     "z": order, "tabOrder": order}
    return v


def label(v, title):
    objects = v["visual"].setdefault("visualContainerObjects", {})
    objects["title"] = [{"properties": {"show": literal("true"), "text": text(title)}}]
    objects["general"] = [{"properties": {"altText": text(title)}}]
    return v


def positive_publication_filter(name):
    return {"name": name, "type": "Advanced",
        "field": projection("Publication", "Publications", True)["field"],
        "filter": {"Version": 2, "From": [{"Name": "p", "Entity": "Publication", "Type": 0}],
            "Where": [{"Condition": {"Comparison": {"ComparisonKind": 1,
                "Left": {"Measure": {"Expression": {"SourceRef": {"Source": "p"}}, "Property": "Publications"}},
                "Right": {"Literal": {"Value": "0L"}}}}}]}}


def button(schema, name, title, action, target=None):
    link = {"show": literal("true"), "type": text(action)}
    if target:
        link["drillthroughSection" if action == "Drillthrough" else "navigationSection"] = text(target)
    return {"$schema": schema, "name": name, "visual": {
        "visualType": "actionButton", "objects": {
            "text": [{"properties": {"show": literal("true")}},
                     {"selector": {"id": "default"}, "properties": {"text": text(title)}}],
            "outline": [{"properties": {"show": literal("true")}}]},
        "visualContainerObjects": {"visualLink": [{"properties": link}],
            "padding": [{"properties": {k: literal("0D") for k in ("top", "bottom", "left", "right")}}],
            "general": [{"properties": {"altText": text(title)}}]}}}


def theme(variant):
    base = read(ROOT / "config/publication-outcomes-theme.base.json")
    base.update(read(ROOT / ("config/publication-outcomes-theme." + variant + ".json")))
    # Text classes require literal theme colours; visual fill properties also
    # support semantic names. Resolve here, keeping colour ownership in themes.
    for item in base["textClasses"].values():
        item["color"] = base["foreground"]
    return base


def prepare(source, output, expected_sha256, variant="light", monthly_date_axis=False):
    if fingerprint(source) != expected_sha256:
        raise ValueError("Exact report preimage mismatch")
    if output.exists():
        raise FileExistsError("Refusing to overwrite a reader candidate")
    before = {p.relative_to(source).as_posix(): p.read_bytes()
              for p in source.rglob("*") if p.is_file()}
    main = source / "definition/pages" / MAIN
    if (source / "definition/pages" / DETAIL).exists():
        raise ValueError("Outcome detail page already exists; reconcile instead of duplicating")
    visuals = {p.parent.name: read(p) for p in (main / "visuals").glob("*/visual.json")}
    if not KEEP <= visuals.keys():
        raise ValueError("Required existing overview visuals missing")
    card = inherited(copy.deepcopy(visuals["overview-unknown-month"]))
    schema = card["$schema"]
    shutil.copytree(source, output)
    main = output / "definition/pages" / MAIN
    detail = output / "definition/pages" / DETAIL
    page = read(main / "page.json")
    page.update(width=1920, height=1080)
    write(main / "page.json", page)
    detail_page = copy.deepcopy(page)
    detail_page.update(name=DETAIL, displayName="Publication definitions and evidence")
    detail_page["pageBinding"] = {"name": "T18PublicationEvidence", "type": "Drillthrough",
        "acceptsFilterContext": "Default", "parameters": [{"name": "FacilityEvidence",
            "boundFilter": "t18-facility-drill", "asAggregation": False,
            "fieldExpr": projection("Facility", "FacilityName")["field"]}]}
    detail_page["filterConfig"] = {"filters": [{"name": "t18-facility-drill", "type": "Categorical", "howCreated": "Drillthrough",
        "field": projection("Facility", "FacilityName")["field"]}]}
    write(detail / "page.json", detail_page)
    for name in sorted(set(visuals) - KEEP):
        shutil.move(str(main / "visuals" / name), str(detail / "visuals" / name))

    def put(page_folder, v):
        write(page_folder / "visuals" / v["name"] / "visual.json", v)

    # Existing primary controls/plots keep stable identities and effective fields.
    for name, pos in {
        "facility-filter": (32, 16, 496, 128, 1000),
        "source-filter": (544, 16, 496, 128, 2000),
        "year-filter": (1056, 16, 416, 128, 3000),
        "annual-trajectory": (32, 288, 912, 304, 9000),
        "facility-breakdown": (32, 608, 912, 320, 11000),
        "attribution-breakdown": (960, 608, 928, 320, 12000),
        "overview-unknown-month": (1448, 160, 440, 112, 8000),
    }.items():
        put(main, position(inherited(copy.deepcopy(visuals[name])), *pos))
    # Preserve the accepted dropdown controls; short list slicers clipped options in web use.
    # Native floating headers obscured the compact dropdown hit target on hover.
    # These controls need their accessible dropdowns, not pin/export toolbars.
    for name in ("facility-filter", "source-filter", "year-filter"):
        control = read(main / "visuals" / name / "visual.json")
        control["visual"].setdefault("visualContainerObjects", {})["visualHeader"] = [
            {"properties": {"show": literal("false")}}]
        put(main, control)
    trend = read(main / "visuals/annual-trajectory/visual.json")
    trend["visual"]["query"] = {"queryState": {
        "Category": {"projections": [projection("Date", "MonthStart" if monthly_date_axis else "YearMonth")]},
        "Y": {"projections": [projection("Publication", "K01 Publications in complete months", True, "Included publications")]}}}
    if monthly_date_axis:
        # Enable only after the saved model's Date.MonthStart column is qualified.
        trend["visual"].setdefault("objects", {}).setdefault("categoryAxis", []).append({
            "properties": {"axisType": text("Scalar")}})
    put(main, label(trend, "Publications — last 24 complete months"))

    def make_card(name, measure, title, pos, precision=0):
        v = copy.deepcopy(card)
        v["name"] = name
        v["visual"]["query"] = {"queryState": {"Data": {"projections": [projection("Publication", measure, True, title)]}}}
        v["visual"].setdefault("objects", {})["value"] = [{"selector": {"id": "default"},
            "properties": {"labelDisplayUnits": literal("1D"), "labelPrecision": literal(str(precision) + "D")}}]
        label(v, title)
        # The card already displays its category; a second container title
        # clipped the callout in the native laptop reader.
        v["visual"]["visualContainerObjects"]["title"][0]["properties"]["show"] = literal("false")
        put(main, position(v, *pos))

    make_card("all-papers", "Publications", "Included publications", (32, 160, 440, 112, 5000))
    make_card("t18-oa-rate", "K02 OA rate among assessed", "Open among OA-assessed", (504, 160, 440, 112, 6000), 1)
    make_card("t18-oa-coverage", "K02 OA assessment coverage", "OA assessment coverage", (976, 160, 440, 112, 7000), 1)
    oa = copy.deepcopy(trend)
    oa["name"] = "t18-oa-status"
    oa["visual"]["visualType"] = "hundredPercentStackedColumnChart"
    for axis in oa["visual"].get("objects", {}).get("categoryAxis", []):
        axis.get("properties", {}).pop("axisType", None)
    oa["visual"]["query"] = {"queryState": {
        "Category": {"projections": [projection("Publication", "SourceSet", label="Source provenance")]},
        "Y": {"projections": [projection("Publication", m, True, title) for m, title in [
            ("K02 Known open publications", "Open"), ("K02 Known closed publications", "Closed"),
            ("K02 Unknown OA publications", "Unknown")]]}}}
    put(main, position(label(oa, "OA evidence — open, closed and unknown"), 960, 288, 928, 304, 10000))
    make_card("t18-reporting-period", "Reporting Month", "Selected reporting month", (32, 944, 640, 128, 13000))
    comparison = inherited(copy.deepcopy(visuals["facility-filter"]))
    comparison["name"] = "t18-comparison"
    comparison["visual"]["visualType"] = "slicer"
    comparison["visual"].pop("drillFilterOtherVisuals", None)
    comparison["visual"]["query"] = {"queryState": {"Values": {
        "projections": [projection("PublicationComparison", "Comparison")]}}}
    # Native web save: default selection must not hide the other option.
    selection_filter = read(ROOT / "config/publication-comparison-selection.json")
    comparison["visual"]["objects"] = {
        "selection": [{"properties": {"strictSingleSelect": literal("true"), "singleSelect": literal("true")}}],
        # Native button-slicer layouts clipped labels at fitted laptop scale.
        # Keep the same field parameter in the qualified native dropdown.
        "data": [{"properties": {"mode": text("Dropdown")}}],
        "header": [{"properties": {"show": literal("false")}}],
        "general": [{"properties": {"filter": {"filter": selection_filter}}}]}
    comparison.pop("filterConfig", None)
    comparison["visual"].setdefault("visualContainerObjects", {})["visualHeader"] = [{"properties": {"show": literal("false")}}]
    put(main, position(label(comparison, "Compare publications by"), 1504, 16, 384, 128, 4000))
    bar = read(main / "visuals/facility-breakdown/visual.json")
    bar["visual"]["query"]["queryState"]["Category"] = {
        "projections": [projection("Facility", "FacilityName"), projection("Publication", "SourceSet")],
        "fieldParameters": [{"parameterExpr": projection("PublicationComparison", "Comparison")["field"],
                             "index": 0, "length": 2}]}
    put(main, label(bar, "Publications by comparison — facility groups may overlap"))
    # The native responsive layout shrank themed 20pt axes to 9pt on these
    # fixed laptop charts. Keep the theme fonts and the explicit canvas layout.
    for name in ("annual-trajectory", "t18-oa-status", "facility-breakdown", "attribution-breakdown"):
        chart = read(main / "visuals" / name / "visual.json")
        entries = chart["visual"].setdefault("objects", {}).setdefault("general", [])
        static = next((entry for entry in entries if not entry.get("selector")), None)
        if static is None:
            static = {"properties": {}}
            entries.append(static)
        static.setdefault("properties", {})["responsive"] = literal("false")
        if name != "annual-trajectory":
            # Zero-valued measures otherwise retain unrelated dimension groups
            # under a facility selection. The trend intentionally retains zeros.
            chart.setdefault("filterConfig", {}).setdefault("filters", []).append(
                positive_publication_filter("t18-positive-" + name))
        if name in ("facility-breakdown", "attribution-breakdown"):
            axis_entries = chart["visual"]["objects"].setdefault("categoryAxis", [])
            axis = next((entry for entry in axis_entries if not entry.get("selector")), None)
            if axis is None:
                axis = {"properties": {}}
                axis_entries.append(axis)
            axis.setdefault("properties", {})["preferredCategoryWidth"] = literal("40D")
        put(main, chart)
    for name, title, action, pos in [
        ("t18-definitions", "Definitions and evidence", "PageNavigation", (704, 960, 568, 96, 14000)),
        ("t18-drill", "Selected facility evidence", "Drillthrough", (1288, 960, 600, 96, 15000)),
    ]:
        put(main, position(button(schema, name, title, action, DETAIL), *pos))

    # Retain every old detail visual and its data; only repair the observed caption.
    detail_positions = {
        "heading": (32, 8, 1536, 56, 1000), "caption": (32, 80, 1856, 64, 3000),
        "review-filter": (32, 160, 600, 96, 4000), "pubmed": (648, 160, 296, 96, 5000),
        "dora": (960, 160, 296, 96, 6000), "overlap": (1272, 160, 296, 96, 7000),
        "footer": (1584, 160, 304, 96, 8000),
        "overview-activities": (32, 272, 440, 96, 9000), "overview-arc": (504, 272, 440, 96, 10000),
        "overview-confirmed": (976, 272, 440, 96, 11000), "overview-candidates": (1448, 272, 440, 96, 12000),
        "provenance-breakdown": (32, 384, 544, 272, 13000),
        "overview-coverage": (592, 384, 1296, 128, 14000),
        "overview-scope": (592, 528, 1296, 128, 15000),
    }
    if set(detail_positions) != set(visuals) - KEEP:
        raise ValueError("Unmapped existing detail visual; preserve and explicitly place it")
    for name, pos in detail_positions.items():
        v = copy.deepcopy(visuals[name])
        if name == "footer":
            title = v["visual"]["visualContainerObjects"]["title"][0]["properties"]["text"]
            if title != text("Last model refresh (UTC)"):
                raise ValueError("Window-evaluation caption drift; reconcile the exact preimage")
            title.update(text("Window evaluated (UTC)"))
            general = v["visual"]["visualContainerObjects"].setdefault("general", [])
            if not general:
                general.append({"properties": {}})
            general[0].setdefault("properties", {})["altText"] = text("Reporting window evaluation time in UTC")
            for item in v["visual"]["query"]["queryState"].get("Values", {}).get("projections", []):
                item["nativeQueryRef"] = item["displayName"] = "Window evaluated (UTC)"
        if name == "overview-coverage":
            old = "Studies and NHMRC/MRFF award registers are not connected to this model."
            value = json.dumps(v)
            if old not in value:
                raise ValueError("Coverage caption drift; reconcile the exact preimage")
            v = json.loads(value.replace(old, "Study and NHMRC/MRFF award registers are retained separately; their populations are not publication counts."))
        put(detail, position(v, *pos))
    put(detail, position(button(schema, "t18-back", "Back to publications", "Back"), 1600, 8, 288, 64, 2000))
    table = {"$schema": schema, "name": "t18-work-evidence", "visual": {
        "visualType": "tableEx", "query": {"queryState": {"Values": {"projections": [
            projection("Publication", n, label=title) for n, title in [
                ("Title", "Publication"), ("SourceSet", "Provenance"),
                ("PublicationDateRaw", "Date"), ("PublicationDatePrecision", "Precision")]
        ] + [projection("Publication", n, True, title) for n, title in [
            ("K02 Known open publications", "Open"), ("K02 Known closed publications", "Closed"),
            ("K02 Unknown OA publications", "Unknown")]] + [projection("Publication", n, label=title) for n, title in [
                ("PubMedURL", "PubMed"), ("DORAURL", "DORA"), ("CanonicalKey", "Canonical key")]]}}},
        "objects": {
            "columnHeaders": [{"properties": {"autoSizeColumnWidth": literal("false"), "wordWrap": literal("true")}}],
            "values": [{"properties": {"wordWrap": literal("true"), "urlIcon": literal("true")}}],
            "columnWidth": [{"selector": {"metadata": "Publication." + name},
                             "properties": {"value": literal(str(width) + "D")}} for name, width in [
                ("Title", 480), ("SourceSet", 160), ("PublicationDateRaw", 120), ("PublicationDatePrecision", 110),
                ("K02 Known open publications", 95), ("K02 Known closed publications", 95),
                ("K02 Unknown OA publications", 95), ("PubMedURL", 160), ("DORAURL", 120), ("CanonicalKey", 240)]]},
        "drillFilterOtherVisuals": True}}
    # Values is a mixed grouping/measure role: absent active flags became false
    # for measures in native saved readback, silently hiding OA columns.
    for item in table["visual"]["query"]["queryState"]["Values"]["projections"]:
        item["active"] = True
    # The existing facility-aware measure is essential: Facility filters the
    # bridge, not Publication directly, and zero-valued OA measures retain rows.
    table["filterConfig"] = {"filters": [positive_publication_filter("t18-visible-work")]}
    put(detail, position(label(table, "Publication evidence — OA counts per work"), 32, 688, 1856, 360, 16000))

    order_path = output / "definition/pages/pages.json"
    order = read(order_path)
    order["pageOrder"].insert(order["pageOrder"].index(MAIN) + 1, DETAIL)
    write(order_path, order)
    report_path = output / "definition/report.json"
    report = read(report_path)
    packages = [p for p in report["resourcePackages"] if p["name"] == "RegisteredResources"]
    if len(packages) != 1:
        raise ValueError("Native registered-resource package is ambiguous")
    for mode in ("light", "dark"):
        resource = theme(mode)
        write(output / "StaticResources/RegisteredResources" / resource["name"], resource)
        packages[0]["items"].append({"name": resource["name"], "path": resource["name"], "type": "CustomTheme"})
    report["themeCollection"]["customTheme"]["name"] = theme(variant)["name"]
    write(report_path, report)
    # All other pages, bindings, resources and existing starting-page selection survive.
    unaffected = [name for name in before if not name.startswith("definition/pages/" + MAIN + "/")
                  and name not in {"definition/report.json", "definition/pages/pages.json"}]
    for name in unaffected:
        if (output / name).read_bytes() != before[name]:
            raise ValueError("Unrelated report part changed: " + name)
    explicit_changes = (correct_window_captions(output) + repair_reconciliation_controls(output)
                        + repair_reconciliation_charts(output) + inherit_neutral_text_colors(output)
                        + repair_publication_evidence_styles(output) + repair_retained_pubmed_observation(output)
                        + repair_evidence_control_space(output) + repair_declared_evidence_links(output))
    unaffected = [name for name in unaffected if name not in explicit_changes]
    old_ids = {(p.parents[2].name, read(p)["name"])
               for p in (source / "definition/pages").glob("*/visuals/*/visual.json")}
    new_ids = {(p.parents[2].name, read(p)["name"])
               for p in (output / "definition/pages").glob("*/visuals/*/visual.json")}
    retained = {(DETAIL if page == MAIN and name not in KEEP else page, name) for page, name in old_ids}
    if not retained <= new_ids:
        raise ValueError("Existing visual identity lost")
    return {"sourceSHA256": expected_sha256, "unaffectedPartsExact": len(unaffected),
            "originalVisualIDsPreserved": len(old_ids), "newVisualIDs": sorted(new_ids - retained),
            "mainPage": MAIN, "detailPage": DETAIL, "themeVariant": variant,
            "monthlyDateAxis": monthly_date_axis, "nativeSaveSubmitted": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--variant", choices=("light", "dark"), default="light")
    parser.add_argument("--monthly-date-axis", action="store_true",
                        help="Requires the qualified native Date.MonthStart column")
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output, args.sha256, args.variant, args.monthly_date_axis), indent=2))
