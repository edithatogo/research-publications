"""Prepare the publication slice's immutable technical baseline and as-of projection.

Inputs and generated data stay private. This module performs no service calls,
processing, issuance or report promotion. Existing publication/export measures
remain unchanged. A technical baseline is never an originally issued result.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import base64
import copy
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid
import zlib

try:
    from .prepare_publication_outcome_measures import VERSION as METRIC_VERSION, reference_counts, unwrap
except ImportError:
    from prepare_publication_outcome_measures import VERSION as METRIC_VERSION, reference_counts, unwrap

BASELINE = "PublicationOutcomeBaseline"
FACT = "PublicationOutcomeVersionFact"
VIEW = "PublicationOutcomeView"
MODEL_REVISION = "publication-outcome-projection-2"
REPORT_REVISION = "T18-publications-reader-2"
MODEL_PATH = "definition/model.tmdl"
FIELDS = {
    "SnapshotID": "string", "CanonicalKey": "string", "Title": "string",
    "SourceSet": "string", "AttributionStatus": "string", "PublicationDateRaw": "string",
    "PublicationDatePrecision": "string", "PublicationDate": "dateTime",
    "PublicationMonth": "string", "PublicationYear": "int64",
    "PubMedURL": "string", "DORAURL": "string", "FacilityKeys": "string",
    "OAOpen": "int64", "OAClosed": "int64", "OAUnknown": "int64", "OAHashes": "string",
}
META_FIELDS = {
    "ViewLabel": "string", "CutoffExclusive": "dateTime", "CapturedUTC": "dateTime",
    "MetricVersion": "string", "ModelRevision": "string", "ReportRevision": "string",
    "SourceVersions": "string", "InputSHA256": "string",
}
REQUIRED = set(FIELDS) - {"SnapshotID", "FacilityKeys", "OAOpen", "OAClosed", "OAUnknown", "OAHashes"}


def dax(value):
    return '"' + str(value).replace('"', '""') + '"'


def semantic_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def normalized_publication(row):
    result = {}
    for key, value in row.items():
        match = re.fullmatch(r"Publication\[([^]]+)\]", key)
        name = match[1] if match else key
        if name in result:
            raise ValueError("Duplicate normalized publication field")
        result[name] = value
    if not REQUIRED <= result.keys():
        raise ValueError("Complete publication projection fields required")
    return result


def make_baseline(publications, observations, facilities, metadata):
    """Freeze accepted row/facet/observation inputs without reclassifying identities."""
    required_meta = {"SnapshotID", *META_FIELDS} - {"InputSHA256"}
    if not required_meta <= metadata.keys() or any(not metadata[k] for k in required_meta):
        raise ValueError("Snapshot identity, cutoff, versions and provenance are required")
    if metadata["SnapshotID"] in {"current", "original-unavailable"}:
        raise ValueError("A technical baseline needs its own immutable snapshot ID")
    if metadata["MetricVersion"] != METRIC_VERSION:
        raise ValueError("Baseline metric version differs from the governed definitions")
    if metadata.get("Issued", False) is not False:
        raise ValueError("Technical capture cannot issue or invent an original result")
    if not metadata["ViewLabel"].startswith("Technical baseline") or "not issued" not in metadata["ViewLabel"].lower():
        raise ValueError("Technical baseline must be visibly identified as not issued")
    cutoff = date.fromisoformat(metadata["CutoffExclusive"])
    if cutoff.day != 1:
        raise ValueError("Complete-month cutoff must be the first day of a month")
    captured = datetime.fromisoformat(metadata["CapturedUTC"].replace("Z", "+00:00"))
    if captured.tzinfo is None or captured.utcoffset().total_seconds() != 0:
        raise ValueError("Capture timestamp must be explicitly UTC")
    rows = [normalized_publication(row) for row in publications]
    keys = [r["CanonicalKey"] for r in rows]
    if not rows or any(not isinstance(k, str) or not k for k in keys) or len(set(keys)) != len(keys):
        raise ValueError("Baseline requires complete unique nonempty canonical keys")
    key_set = set(keys)
    facets = {k: set() for k in keys}
    for row in facilities:
        key, facility = row["CanonicalKey"], row["FacilityKey"]
        if key not in key_set or not isinstance(facility, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", facility):
            raise ValueError("Facility bridge must use exact accepted keys and safe typed facility IDs")
        facets[key].add(facility)
    grouped = {}
    for row in observations:
        key = row["CanonicalKey"]
        raw_hash = row.get("RawResponseSHA256")
        if not isinstance(raw_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", raw_hash):
            raise ValueError("Every retained OA observation requires its actual source hash")
        grouped.setdefault(key, []).append(row)
    input_sha = semantic_sha({"publications": publications, "observations": observations,
                              "facilities": facilities, "metadata": metadata})
    frozen = []
    for row in sorted(rows, key=lambda r: r["CanonicalKey"]):
        key = row["CanonicalKey"]
        status = reference_counts([key], grouped.get(key, []))
        record = {name: row[name] for name in FIELDS if name in REQUIRED}
        value = record["PublicationDate"]
        if value is not None:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if "T" in value else datetime.combine(date.fromisoformat(value), datetime.min.time())
            if parsed.time() != datetime.min.time():
                raise ValueError("Publication date must retain the model's date grain")
            record["PublicationDate"] = parsed.date().isoformat()
        record.update(SnapshotID=metadata["SnapshotID"], FacilityKeys="|" + "|".join(sorted(facets[key])) + "|",
                      OAOpen=status["Open"], OAClosed=status["Closed"], OAUnknown=status["Unknown"],
                      OAHashes="|".join(sorted({r["RawResponseSHA256"].lower() for r in grouped.get(key, [])})),
                      **{k: metadata[k] for k in META_FIELDS if k != "InputSHA256"}, InputSHA256=input_sha)
        frozen.append(record)
    return frozen


def _columns(fields, calculated=False):
    result = []
    for name, kind in fields.items():
        text = f"\tcolumn {name}\n\t\tdataType: {kind}\n\t\tsummarizeBy: none\n"
        if name in {"PubMedURL", "DORAURL"}:
            text += "\t\tdataCategory: WebUrl\n"
        if name == "CapturedUTC":
            text += "\t\tformatString: yyyy-MM-dd HH:mm:ss\n"
        elif name in {"PublicationDate", "CutoffExclusive"}:
            text += "\t\tformatString: yyyy-MM-dd\n"
        text += f"\t\tsourceColumn: [{name}]\n" if calculated else f"\t\tsourceColumn: {name}\n"
        result.append(text)
    return "\n".join(result)


def _table(name, columns, expression, calculated=False, measures=""):
    lineage = uuid.uuid5(uuid.NAMESPACE_URL, "rims:T18:publication:" + name)
    return (f"table {name}\n\tlineageTag: {lineage}\n\n" + measures + _columns(columns, calculated)
            + f"\n\tpartition {name} = {'calculated' if calculated else 'm'}\n\t\tmode: import\n\t\tsource =\n\t\t\t"
            + expression.replace("\n", "\n\t\t\t") + "\n")


def baseline_tmdl(rows):
    compressor = zlib.compressobj(level=9, wbits=-15)
    data = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()
    packed = base64.b64encode(compressor.compress(data) + compressor.flush()).decode()
    types = {"string": "type text", "int64": "Int64.Type", "dateTime": "type date"}
    fields = FIELDS | META_FIELDS
    transformations = ','.join('{"' + k + '",' + types[v] + '}' for k, v in fields.items() if k != "CapturedUTC")
    expression = f'''let
    Records = Json.Document(Binary.Decompress(Binary.FromText("{packed}", BinaryEncoding.Base64), Compression.Deflate)),
    Source = Table.FromRecords(Records),
    Dates = Table.TransformColumns(Source, {{
        {{"PublicationDate", each if _ = null then null else Date.FromText(_, "en-AU"), type nullable date}},
        {{"CutoffExclusive", each Date.FromText(_, "en-AU"), type date}},
        {{"CapturedUTC", each DateTimeZone.RemoveZone(DateTimeZone.SwitchZone(DateTimeZone.FromText(_), 0)), type datetime}}
    }}),
    Typed = Table.TransformColumnTypes(Dates, {{{transformations}}})
in Typed'''
    return _table(BASELINE, fields, expression)


def fact_expression():
    direct = [name for name in FIELDS if name not in {"SnapshotID", "FacilityKeys", "OAOpen", "OAClosed", "OAUnknown", "OAHashes"}]
    current = [dax("SnapshotID"), dax("current")]
    for name in direct:
        current += [dax(name), f"Publication[{name}]"]
    for name in ("FacilityKeys", "OAOpen", "OAClosed", "OAUnknown", "OAHashes"):
        current += [dax(name), f"[__{name}]"]
    baseline = ", ".join(item for name in FIELDS for item in (dax(name), f"{BASELINE}[{name}]"))
    # UNION is positional. Keep current and frozen projection columns identical.
    order = ["SnapshotID", *direct, "FacilityKeys", "OAOpen", "OAClosed", "OAUnknown", "OAHashes"]
    baseline = ", ".join(item for name in order for item in (dax(name), f"{BASELINE}[{name}]"))
    return '''VAR CurrentRows = ADDCOLUMNS(Publication,
    "__OAOpen", CALCULATE([K02 Known open publications]),
    "__OAClosed", CALCULATE([K02 Known closed publications]),
    "__OAUnknown", CALCULATE([K02 Unknown OA publications]),
    "__FacilityKeys", VAR WorkKey = Publication[CanonicalKey]
        RETURN "|" & CONCATENATEX(FILTER(ALL(PublicationFacility), PublicationFacility[CanonicalKey] = WorkKey), PublicationFacility[FacilityKey], "|", PublicationFacility[FacilityKey], ASC) & "|",
    "__OAHashes", VAR WorkKey = Publication[CanonicalKey]
        VAR Hashes = DISTINCT(SELECTCOLUMNS(FILTER(ALL(OpenAlexPublicationContext), OpenAlexPublicationContext[CanonicalKey] = WorkKey), "Hash", LOWER(OpenAlexPublicationContext[RawResponseSHA256])))
        RETURN CONCATENATEX(Hashes, [Hash], "|", [Hash], ASC))
RETURN UNION(SELECTCOLUMNS(CurrentRows, ''' + ", ".join(current) + "),\n    SELECTCOLUMNS(" + BASELINE + ", " + baseline + "))"


FILTER_PREFIX = '''VAR SnapshotID = SELECTEDVALUE(PublicationOutcomeView[SnapshotID], "current")
VAR Available = SELECTEDVALUE(PublicationOutcomeView[Available], TRUE())
VAR FacilityScoped = ISCROSSFILTERED(Facility)
VAR Facilities = VALUES(Facility[FacilityKey])
VAR SourceScoped = ISFILTERED(Publication[SourceSet])
VAR Sources = VALUES(Publication[SourceSet])
VAR YearScoped = ISFILTERED(Publication[PublicationYear])
VAR Years = VALUES(Publication[PublicationYear])
VAR DateScoped = ISCROSSFILTERED('Date')
VAR Dates = VALUES('Date'[Date])
VAR WorkRows = FILTER(PublicationOutcomeVersionFact,
    PublicationOutcomeVersionFact[SnapshotID] = SnapshotID
    && (NOT SourceScoped || PublicationOutcomeVersionFact[SourceSet] IN Sources)
    && (NOT YearScoped || PublicationOutcomeVersionFact[PublicationYear] IN Years)
    && (NOT DateScoped || (PublicationOutcomeVersionFact[PublicationDatePrecision] IN {"day", "month"}
        && PublicationOutcomeVersionFact[PublicationDate] IN Dates))
    && (NOT FacilityScoped || VAR Keys = PublicationOutcomeVersionFact[FacilityKeys]
        RETURN COUNTROWS(FILTER(Facilities, CONTAINSSTRING(Keys, "|" & Facility[FacilityKey] & "|"))) > 0))
'''


MEASURES = {
    "V01 Included publications": FILTER_PREFIX + "RETURN IF(Available, COALESCE(COUNTROWS(WorkRows), 0), BLANK())",
    "V01 Open publications": FILTER_PREFIX + "RETURN IF(Available, COALESCE(SUMX(WorkRows, PublicationOutcomeVersionFact[OAOpen]), 0), BLANK())",
    "V01 Closed publications": FILTER_PREFIX + "RETURN IF(Available, COALESCE(SUMX(WorkRows, PublicationOutcomeVersionFact[OAClosed]), 0), BLANK())",
    "V01 Unknown OA publications": FILTER_PREFIX + "RETURN IF(Available, COALESCE(SUMX(WorkRows, PublicationOutcomeVersionFact[OAUnknown]), 0), BLANK())",
    "V01 Assessed publications": "IF(SELECTEDVALUE(PublicationOutcomeView[Available], TRUE()), [V01 Open publications] + [V01 Closed publications], BLANK())",
    "V01 OA rate among assessed": "DIVIDE([V01 Open publications], [V01 Assessed publications])",
    "V01 OA assessment coverage": "DIVIDE([V01 Assessed publications], [V01 Included publications])",
    "V01 Publications without usable month": FILTER_PREFIX + '''RETURN IF(Available, COALESCE(COUNTROWS(FILTER(WorkRows,
        NOT (PublicationOutcomeVersionFact[PublicationDatePrecision] IN {"day", "month"}) || ISBLANK(PublicationOutcomeVersionFact[PublicationMonth]))), 0), BLANK())''',
    "V01 Publications in complete months": FILTER_PREFIX + '''VAR EndExclusive = SELECTEDVALUE(PublicationOutcomeView[CutoffExclusive])
VAR StartInclusive = EDATE(EndExclusive, -24)
RETURN IF(Available && NOT ISBLANK(EndExclusive), COALESCE(COUNTROWS(FILTER(WorkRows,
    PublicationOutcomeVersionFact[PublicationDatePrecision] IN {"day", "month"}
    && PublicationOutcomeVersionFact[PublicationDate] >= StartInclusive
    && PublicationOutcomeVersionFact[PublicationDate] < EndExclusive)), 0), BLANK())''',
    "V01 Original availability": '"Unavailable: no issued T18 publication snapshot is evidenced. A technical baseline is not an issued original."',
    "V01 Reporting month": '''VAR Available = SELECTEDVALUE(PublicationOutcomeView[Available], TRUE())
VAR EndExclusive = SELECTEDVALUE(PublicationOutcomeView[CutoffExclusive])
RETURN IF(Available && NOT ISBLANK(EndExclusive), FORMAT(EDATE(EndExclusive, -1), "mmmm yyyy"), "Unavailable")''',
    "V01 Restatement reason": '''VAR SelectedSnapshot = SELECTEDVALUE(PublicationOutcomeView[SnapshotID], "current")
VAR FrozenID = MAXX(FILTER(ALL(PublicationOutcomeView), PublicationOutcomeView[Available] && PublicationOutcomeView[SnapshotID] <> "current"), PublicationOutcomeView[SnapshotID])
VAR CurrentKeys = CALCULATETABLE(VALUES(PublicationOutcomeVersionFact[CanonicalKey]), REMOVEFILTERS(PublicationOutcomeVersionFact), PublicationOutcomeVersionFact[SnapshotID] = "current")
VAR FrozenKeys = CALCULATETABLE(VALUES(PublicationOutcomeVersionFact[CanonicalKey]), REMOVEFILTERS(PublicationOutcomeVersionFact), PublicationOutcomeVersionFact[SnapshotID] = FrozenID)
RETURN SWITCH(TRUE(), SelectedSnapshot = "original-unavailable", [V01 Original availability],
    SelectedSnapshot <> "current", "Frozen technical baseline; not issued. Source evidence and the metric definition are fixed to this capture.",
    "Current retained evidence versus the technical baseline: " & FORMAT(COALESCE(COUNTROWS(EXCEPT(CurrentKeys, FrozenKeys)), 0), "0") & " added work(s), "
    & FORMAT(COALESCE(COUNTROWS(EXCEPT(FrozenKeys, CurrentKeys)), 0), "0") & " removed work(s). Source date/evidence corrections can restate earlier periods; no issued original is represented.")''',
}


def affected_periods_expression():
    # Compare only fields which can affect this slice's displayed populations,
    # dates or OA counts. A citation-only/raw-hash change is not a K01/K02 change.
    names = ("CanonicalKey", "SourceSet", "AttributionStatus", "FacilityKeys", "PublicationDateRaw", "PublicationDatePrecision",
             "PublicationMonth", "PublicationDate", "OAOpen", "OAClosed", "OAUnknown")
    projection = ", ".join(item for name in names for item in (dax(name), f"{FACT}[{name}]"))
    return '''VAR Available = SELECTEDVALUE(PublicationOutcomeView[Available], TRUE())
VAR FrozenID = MAXX(FILTER(ALL(PublicationOutcomeView), PublicationOutcomeView[Available] && PublicationOutcomeView[SnapshotID] <> "current"), PublicationOutcomeView[SnapshotID])
VAR CurrentRows = SELECTCOLUMNS(FILTER(ALL(PublicationOutcomeVersionFact), PublicationOutcomeVersionFact[SnapshotID] = "current"), ''' + projection + ''')
VAR FrozenRows = SELECTCOLUMNS(FILTER(ALL(PublicationOutcomeVersionFact), PublicationOutcomeVersionFact[SnapshotID] = FrozenID), ''' + projection + ''')
VAR ChangedKeys = DISTINCT(SELECTCOLUMNS(UNION(EXCEPT(CurrentRows, FrozenRows), EXCEPT(FrozenRows, CurrentRows)), "ChangedKey", [CanonicalKey]))
VAR Periods = DISTINCT(SELECTCOLUMNS(FILTER(ALL(PublicationOutcomeVersionFact), PublicationOutcomeVersionFact[CanonicalKey] IN ChangedKeys),
    "Period", COALESCE(PublicationOutcomeVersionFact[PublicationMonth], "Unknown month (precision retained)")))
RETURN IF(NOT Available, "Unavailable", IF(COUNTROWS(ChangedKeys) = 0, "No K01/K02 population, date or OA changes against the technical baseline",
    CONCATENATEX(Periods, [Period], ", ", [Period], ASC)))'''


MEASURES["V01 Affected periods"] = affected_periods_expression()
TEXT_MEASURES = {"V01 Original availability", "V01 Reporting month", "V01 Restatement reason", "V01 Affected periods"}


def measure_tmdl():
    result = []
    for name, expression in MEASURES.items():
        fmt = "0.0%" if name in {"V01 OA rate among assessed", "V01 OA assessment coverage"} else "#,0"
        result.append(f"\t/// Selected retained snapshot; explicit facility/date/source filters. Does not issue a result.\n\tmeasure '{name}' = ```\n\t\t\t"
                      + expression.replace("\n", "\n\t\t\t") + "\n\t\t\t```\n"
                      + (f"\t\tformatString: {fmt}\n" if name not in TEXT_MEASURES else "")
                      + f"\t\tdisplayFolder: T18 publication as-of views\n\t\tannotation RIMSMetricVersion = {METRIC_VERSION}\n")
    return "\n".join(result) + "\n"


def view_tmdl():
    fields = {"SnapshotID": "string", "ViewLabel": "string", "Available": "boolean",
              "ViewOrder": "int64", **META_FIELDS}
    # ViewLabel appears in META_FIELDS; dict union retains one column definition.
    current = {"SnapshotID": dax("current"), "ViewLabel": dax("Current / restated evidence"),
               "Available": "TRUE()", "ViewOrder": "0", "CutoffExclusive": "MAXX(ReportingWindow, ReportingWindow[ReportMonthEndExclusive])",
               "CapturedUTC": "UTCNOW()", "MetricVersion": dax(METRIC_VERSION),
               "ModelRevision": dax(MODEL_REVISION), "ReportRevision": dax(REPORT_REVISION),
               "SourceVersions": 'CONCATENATEX(SUMMARIZE(RetainedHistoryKeys, RetainedHistoryKeys[Source], RetainedHistoryKeys[LastBatchID]), RetainedHistoryKeys[Source] & ":" & RetainedHistoryKeys[LastBatchID], "; ") & "; OpenAlex: retained raw hashes in OA evidence"',
               "InputSHA256": "BLANK()"}
    frozen = {name: f"{BASELINE}[{name}]" for name in fields if name not in {"Available", "ViewOrder"}}
    frozen.update(Available="TRUE()", ViewOrder="1")
    unavailable = {name: "BLANK()" for name in fields}
    unavailable.update(SnapshotID=dax("original-unavailable"), ViewLabel=dax("Originally reported — unavailable"), Available="FALSE()", ViewOrder="2",
                       SourceVersions=dax("No issued original evidence; current data must not approximate it"))
    def row(values):
        return "ROW(" + ", ".join(item for name in fields for item in (dax(name), values[name])) + ")"
    frozen_expression = "DISTINCT(SELECTCOLUMNS(" + BASELINE + ", " + ", ".join(item for name in fields for item in (dax(name), frozen[name])) + "))"
    expression = "UNION(" + row(current) + ",\n    " + frozen_expression + ",\n    " + row(unavailable) + ")"
    result = _table(VIEW, fields, expression, True)
    result = result.replace("\tcolumn ViewLabel\n", "\tcolumn ViewLabel\n\t\tsortByColumn: ViewOrder\n")
    return result


def prepare(preimage: bytes, expected_sha256: str, baseline):
    if hashlib.sha256(preimage).hexdigest() != expected_sha256:
        raise ValueError("Exact native preimage mismatch")
    definition = copy.deepcopy(unwrap(json.loads(preimage)))
    paths = [part["path"] for part in definition["parts"]]
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate native definition parts require reconciliation")
    if any("/roles/" in part["path"] for part in definition["parts"]):
        raise ValueError("Snapshot projection requires explicit RLS/OLS propagation qualification on this target")
    parts = {part["path"]: part for part in definition["parts"]}
    names = (BASELINE, FACT, VIEW)
    if any(f"definition/tables/{name}.tmdl" in parts for name in names):
        raise ValueError("Existing snapshot objects must be reconciled, never overwritten")
    publication = base64.b64decode(parts["definition/tables/Publication.tmdl"]["payload"], validate=True).decode()
    for name in ("K02 Known open publications", "K02 Known closed publications", "K02 Unknown OA publications"):
        if f"measure '{name}'" not in publication or METRIC_VERSION not in publication:
            raise ValueError("Governed native outcome definitions missing or version drift")
    dependencies = {
        "PublicationFacility": ("CanonicalKey", "FacilityKey"),
        "Facility": ("FacilityKey",), "Date": ("Date",),
        "ReportingWindow": ("ReportMonthEndExclusive",),
        "RetainedHistoryKeys": ("Source", "LastBatchID"),
        "OpenAlexPublicationContext": ("CanonicalKey", "RawResponseSHA256"),
    }
    for table, columns in dependencies.items():
        part = parts.get(f"definition/tables/{table}.tmdl")
        if part is None:
            raise ValueError("Required native snapshot dependency missing: " + table)
        text = base64.b64decode(part["payload"], validate=True).decode()
        for column in columns:
            if not re.search(r"(?m)^\tcolumn " + re.escape(column) + r"\s*$", text):
                raise ValueError("Required native snapshot column missing: " + table + "." + column)
    # The retained observation is a UTC instant. Without an explicit format the
    # native card reduces it to a date and hides the available time evidence.
    retained = parts.get("definition/tables/RetainedPubMedPublications.tmdl")
    if retained is not None:
        retained_text = base64.b64decode(retained["payload"], validate=True).decode()
        anchor = "\tcolumn RefreshedAtUTC\n\t\tdataType: dateTime\n"
        if retained_text.count(anchor) != 1:
            raise ValueError("Retained observation UTC column drift")
        tail = retained_text.split(anchor, 1)[1].split("\n\tcolumn ", 1)[0]
        if "formatString:" in tail:
            raise ValueError("Existing retained observation format requires reconciliation")
        retained["payload"] = base64.b64encode(retained_text.replace(
            anchor, anchor + "\t\tformatString: yyyy-MM-dd HH:mm:ss\n", 1).encode()).decode()
    # A date-valued monthly axis lets the web reader space ticks continuously
    # without shrinking fonts or presenting the monthly series as daily counts.
    date_part = parts["definition/tables/Date.tmdl"]
    date_text = base64.b64decode(date_part["payload"], validate=True).decode()
    if re.search(r"(?m)^\tcolumn MonthStart(?:\s|$)", date_text):
        raise ValueError("Existing monthly date axis must be reconciled, never overwritten")
    month_tag = uuid.uuid5(uuid.NAMESPACE_URL, "rims:T18:publication:Date.MonthStart")
    date_text = date_text.rstrip() + (
        "\n\n\tcolumn MonthStart = DATE(YEAR('Date'[Date]), MONTH('Date'[Date]), 1)\n"
        "\t\tdataType: dateTime\n\t\tformatString: MMM yyyy\n"
        f"\t\tlineageTag: {month_tag}\n\t\tsummarizeBy: none\n")
    date_part["payload"] = base64.b64encode(date_text.encode()).decode()
    comparison = parts.get("definition/tables/PublicationComparison.tmdl")
    if comparison is None:
        raise ValueError("Qualified native comparison parameter is required")
    comparison_text = base64.b64decode(comparison["payload"], validate=True).decode()
    reference = "NAMEOF(Publication[SourceSet])"
    if comparison_text.count(reference) != 1:
        raise ValueError("Native comparison source reference drift; reconcile before adoption")
    comparison["payload"] = base64.b64encode(comparison_text.replace(
        reference, f"NAMEOF({FACT}[SourceSet])", 1).encode()).decode()
    if not baseline or any(set(row) != set(FIELDS | META_FIELDS) for row in baseline):
        raise ValueError("Validated complete frozen baseline required")
    keys = [row["CanonicalKey"] for row in baseline]
    if len(set(keys)) != len(keys) or len({row["SnapshotID"] for row in baseline}) != 1:
        raise ValueError("Initial frozen baseline must be one unique canonical snapshot")
    if any(row["SnapshotID"] in {"current", "original-unavailable"}
           or row["MetricVersion"] != METRIC_VERSION
           or not row["ViewLabel"].startswith("Technical baseline")
           or "not issued" not in row["ViewLabel"].lower()
           or not re.fullmatch(r"[0-9a-f]{64}", row["InputSHA256"])
           or any(type(row[k]) is not int or row[k] not in (0, 1) for k in ("OAOpen", "OAClosed", "OAUnknown"))
           or sum(row[k] for k in ("OAOpen", "OAClosed", "OAUnknown")) != 1
           for row in baseline):
        raise ValueError("Frozen snapshot classification, identity or non-issuance contract differs")
    generated = {BASELINE: baseline_tmdl(baseline), FACT: _table(FACT, FIELDS, fact_expression(), True, measure_tmdl()), VIEW: view_tmdl()}
    for name, content in generated.items():
        definition["parts"].append({"path": f"definition/tables/{name}.tmdl", "payloadType": "InlineBase64", "payload": base64.b64encode(content.encode()).decode()})
    model = parts[MODEL_PATH]
    original = base64.b64decode(model["payload"], validate=True).decode()
    if any(re.search(r"(?m)^ref table " + name + r"\s*$", original) for name in names):
        raise ValueError("Unexpected existing snapshot table reference")
    model["payload"] = base64.b64encode((original.rstrip() + "\n\n" + "\n".join("ref table " + name for name in names) + "\n").encode()).decode()
    return definition


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("preimage", type=Path)
    parser.add_argument("inputs", type=Path, help="Private accepted publications/observations/facilities/metadata JSON")
    parser.add_argument("output", type=Path)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    data = json.loads(args.inputs.read_text())
    baseline = make_baseline(**data)
    result = prepare(args.preimage.read_bytes(), args.sha256, baseline)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump({"definition": result}, stream, indent=2)
        stream.write("\n")
