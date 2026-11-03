"""Author a portable A4 RDL candidate using governed semantic measure identities.

The connection placeholder is bound privately only after model acceptance. XML
construction is local evidence; native RDL import and PDF rendering remain gates.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

NS = 'http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition'
ET.register_namespace('', NS)


def node(parent, name, text=None, **attrs):
    child = ET.SubElement(parent, '{' + NS + '}' + name, attrs)
    if text is not None:
        child.text = text
    return child


def dax_string(value):
    return '"' + value.replace('"', '""') + '"'


def query(contract):
    rows = []
    for index, m in enumerate(contract['metrics']):
        domain = m['id'][0]
        group = ('Knowledge and reach' if domain == 'K' else
                 'Capacity and partnerships' if domain in 'CP' else
                 'Translation and community benefit' if domain in 'THESQ' else
                 'Stewardship and reliability')
        value = 'BLANK()'
        evidence = m['unavailable_reason']
        if m.get('readiness') == 'existing-measure':
            measure = "'" + m['source_table'].replace("'", "''") + "'[" + m['measure'].replace(']', ']]') + ']'
            if m['source_table'] == 'Publication':
                value = 'CALCULATE(' + measure + ', REMOVEFILTERS(\'Date\'), PeriodDates, KEEPFILTERS(Publication[PublicationDatePrecision] IN {"day", "month"}))'
                if m['id'] == 'K01':
                    value = 'CALCULATE([Selected Month Publications], REMOVEFILTERS(\'Date\'), PeriodDates, TREATAS({@ReportMonth}, \'Date\'[YearMonth]))'
                evidence = 'Retained publication cohort; ' + m['eligibility']
            elif m['id'] == 'C01.study':
                value = measure
                evidence = 'Source snapshot count; not a monthly active-project or leadership measure. ' + m['eligibility']
            elif m['id'] == 'P01.links':
                value = measure
                evidence = 'Current reviewed-link snapshot; not a monthly partnership rate. ' + m['eligibility']
        fields = {'Order': str(index), 'GroupName': dax_string(group), 'MetricID': dax_string(m['id']),
                  'Label': dax_string(m['label']), 'Value': value, 'Unit': dax_string(m['unit']),
                  'Evidence': dax_string(evidence), 'Period': '@ReportMonth',
                  'Numerator': 'BLANK()', 'Denominator': 'BLANK()', 'UnknownCount': 'BLANK()'}
        if m['id'].startswith('K02.'):
            for field, measure_name in {
                'Numerator': 'K02 Known open publications' if m['id'] == 'K02.rate' else 'K02 OA assessed publications',
                'Denominator': 'K02 OA assessed publications' if m['id'] == 'K02.rate' else 'Publications',
                'UnknownCount': 'K02 Unknown OA publications',
            }.items():
                fields[field] = "CALCULATE([" + measure_name + "], REMOVEFILTERS('Date'), PeriodDates, KEEPFILTERS(Publication[PublicationDatePrecision] IN {\"day\", \"month\"}))"
        rows.append('ROW(' + ', '.join(dax_string(k) + ', ' + v for k, v in fields.items()) + ')')
    return '''DEFINE
VAR PeriodStart = DATE(VALUE(LEFT(@ReportMonth, 4)), VALUE(RIGHT(@ReportMonth, 2)), 1)
VAR PeriodEnd = EDATE(PeriodStart, 1)
VAR GuardedStart = IF(FORMAT(PeriodStart, "yyyy-MM") = @ReportMonth
    && PeriodEnd <= MAX(ReportingWindow[ReportMonthEndExclusive]), PeriodStart,
    ERROR("Select a complete yyyy-MM publication month within the accepted reporting window"))
VAR PeriodDates = DATESBETWEEN('Date'[Date], GuardedStart, PeriodEnd - 1)
EVALUATE UNION(
''' + ',\n'.join(rows) + ')\nORDER BY [Order]'


def textbox(items, name, text, top, *, height='0.7cm', size='10pt', bold=False):
    box = node(items, 'Textbox', Name=name)
    node(box, 'CanGrow', 'true')
    paragraphs = node(box, 'Paragraphs')
    para = node(paragraphs, 'Paragraph')
    runs = node(para, 'TextRuns')
    run = node(runs, 'TextRun')
    node(run, 'Value', text)
    style = node(run, 'Style')
    node(style, 'FontFamily', 'Segoe UI')
    node(style, 'FontSize', size)
    if bold:
        node(style, 'FontWeight', 'Bold')
    node(box, 'Top', top)
    node(box, 'Left', '0cm')
    node(box, 'Height', height)
    node(box, 'Width', '18cm')
    style = node(box, 'Style')
    for side in ['Left', 'Right', 'Top', 'Bottom']:
        node(style, 'Padding' + side, '2pt')
    return box


def build(contract):
    report = ET.Element('{' + NS + '}Report')
    node(report, 'Description', 'T18 A4 candidate; native import, populated/empty PDF and cross-consumer parity unverified.')
    sources = node(report, 'DataSources')
    source = node(sources, 'DataSource', Name='AcceptedRIMSModel')
    connection = node(source, 'ConnectionProperties')
    node(connection, 'DataProvider', 'PBIDATASET')
    node(connection, 'ConnectString', 'Data Source=pbiazure://api.powerbi.com/;Initial Catalog=sobe_wowvirtualserver-__ACCEPTED_MODEL_ID__;Integrated Security=ClaimsToken')
    datasets = node(report, 'DataSets')
    data = node(datasets, 'DataSet', Name='Indicators')
    q = node(data, 'Query')
    node(q, 'DataSourceName', 'AcceptedRIMSModel')
    parameters = node(q, 'QueryParameters')
    node(node(parameters, 'QueryParameter', Name='@ReportMonth'), 'Value', '=Parameters!ReportMonth.Value')
    node(q, 'CommandText', query(contract))
    fields = node(data, 'Fields')
    for name in ['Order', 'GroupName', 'MetricID', 'Label', 'Value', 'Unit', 'Evidence', 'Period', 'Numerator', 'Denominator', 'UnknownCount']:
        node(node(fields, 'Field', Name=name), 'DataField', '[' + name + ']')
    parameters = node(report, 'ReportParameters')
    month = node(parameters, 'ReportParameter', Name='ReportMonth')
    node(month, 'DataType', 'String')
    default = node(node(month, 'DefaultValue'), 'Values')
    node(default, 'Value', '=Format(DateAdd("m", -1, DateSerial(Year(DateAdd("h", 10, DateTime.UtcNow)), Month(DateAdd("h", 10, DateTime.UtcNow)), 1)), "yyyy-MM")')
    node(month, 'Prompt', 'Complete publication month (yyyy-MM); other domains retain their source snapshot period')
    revision = node(parameters, 'ReportParameter', Name='AcceptedModelRevision')
    node(revision, 'DataType', 'String')
    node(node(node(revision, 'DefaultValue'), 'Values'), 'Value', '__UNACCEPTED_MODEL_REVISION__')
    node(revision, 'Hidden', 'true')
    sections = node(report, 'ReportSections')
    section = node(sections, 'ReportSection')
    body = node(section, 'Body')
    allitems = node(body, 'ReportItems')
    summary = node(allitems, 'Rectangle', Name='SummaryPage')
    items = node(summary, 'ReportItems')
    textbox(items, 'Title', 'CHHHS research outcomes and evidence', '0cm', size='20pt', height='1cm', bold=True)
    textbox(items, 'Period', '= "Publication month: " & Parameters!ReportMonth.Value', '1.1cm')
    textbox(items, 'Limits', 'Retained evidence, not a complete institutional census. Unavailable is not zero impact. Snapshot counts and monthly publication cohorts are identified separately. No targets or owners are inferred.', '1.9cm', height='1.5cm')
    textbox(items, 'PublicationSummary', '= "Publication outputs: " & Format(Lookup("K01", Fields!MetricID.Value, Fields!Value.Value, "Indicators"), "#,0")', '3.8cm', size='16pt', height='1cm', bold=True)
    textbox(items, 'OASummary', '= "OA among assessed: " & IIF(IsNothing(Lookup("K02.rate", Fields!MetricID.Value, Fields!Value.Value, "Indicators")), "Unavailable", Format(Lookup("K02.rate", Fields!MetricID.Value, Fields!Value.Value, "Indicators"), "0.0%")) & " | Assessment coverage: " & IIF(IsNothing(Lookup("K02.coverage", Fields!MetricID.Value, Fields!Value.Value, "Indicators")), "Unavailable", Format(Lookup("K02.coverage", Fields!MetricID.Value, Fields!Value.Value, "Indicators"), "0.0%"))', '5cm', height='1.2cm')
    textbox(items, 'KnowledgeSummary', 'KNOWLEDGE AND REACH | Counts describe retained publication outputs. OA numerator, eligible denominator and unknown work counts appear in the evidence appendix. Citation comparisons require compatible field, year, type and observation windows.', '6.5cm', height='2.1cm')
    textbox(items, 'CapacitySummary', '= "CAPACITY AND PARTNERSHIPS | Source-qualified study snapshot records: " & Format(Lookup("C01.study", Fields!MetricID.Value, Fields!Value.Value, "Indicators"), "#,0") & ". Study records are not active or led projects. Workforce time and partnership rates require qualified identities, roles, dates and eligible denominators."', '9cm', height='2.1cm')
    textbox(items, 'TranslationSummary', 'TRANSLATION AND COMMUNITY BENEFIT | No real governed adoption, aggregate health, economic or community-benefit result is inferred from publication activity or technical intake fixtures. Unavailable domains retain their specific evidence dependencies.', '11.5cm', height='2.1cm')
    textbox(items, 'StewardshipSummary', 'STEWARDSHIP AND RELIABILITY | Opportunities, confirmed closings, held deadlines and historical coverage are separate. Award amounts need currency/cohort meaning. Source observation, acquisition, model processing and scheduled delivery are separate events.', '14cm', height='2.1cm')
    textbox(items, 'ModelRevision', '= "Model revision: " & Parameters!AcceptedModelRevision.Value', '17cm', height='1.2cm', size='9pt')
    textbox(items, 'AppendixNotice', 'Vertical indicator sections and evidence appendix follow. Values retain their defined cohort or snapshot period, measure identity, coverage and unavailable reason. This report does not assign performance ratings.', '19cm', height='2.1cm')
    node(node(summary, 'PageBreak'), 'BreakLocation', 'End')
    node(summary, 'KeepTogether', 'true')
    node(summary, 'Top', '0cm')
    node(summary, 'Left', '0cm')
    node(summary, 'Height', '24cm')
    node(summary, 'Width', '18cm')
    # A detail list gives every vertical a growing evidence block and a stable
    # per-row pagination boundary. No image or local calculation substitutes for DAX.
    tablix = node(allitems, 'Tablix', Name='IndicatorEvidence')
    tb = node(tablix, 'TablixBody')
    cols = node(tb, 'TablixColumns')
    node(node(cols, 'TablixColumn'), 'Width', '18cm')
    rows = node(tb, 'TablixRows')
    row = node(rows, 'TablixRow')
    node(row, 'Height', '4cm')
    cells = node(row, 'TablixCells')
    content = node(node(cells, 'TablixCell'), 'CellContents')
    rect = node(content, 'Rectangle', Name='EvidenceBlock')
    ri = node(rect, 'ReportItems')
    textbox(ri, 'GroupLabel', '=Fields!GroupName.Value & " | " & Fields!MetricID.Value', '0cm', bold=True)
    textbox(ri, 'MetricLabel', '=Fields!Label.Value', '0.7cm', bold=True)
    textbox(ri, 'MetricValue', '=IIF(IsNothing(Fields!Value.Value), "Unavailable", Format(Fields!Value.Value, IIF(Fields!Unit.Value = "ratio", "0.0%", "#,0"))) & " | " & Fields!Unit.Value', '1.4cm')
    textbox(ri, 'MetricContext', '=IIF(IsNothing(Fields!Denominator.Value), "Source/snapshot eligibility is stated below", "Numerator: " & Fields!Numerator.Value & " | Eligible denominator: " & Fields!Denominator.Value & " | Unknown OA works: " & Fields!UnknownCount.Value)', '2.1cm', size='9pt')
    textbox(ri, 'EvidenceReason', '=Fields!Evidence.Value', '2.8cm', height='1.2cm', size='9pt')
    node(rect, 'KeepTogether', 'true')
    hierarchy = node(tablix, 'TablixColumnHierarchy')
    node(node(hierarchy, 'TablixMembers'), 'TablixMember')
    hierarchy = node(tablix, 'TablixRowHierarchy')
    member = node(node(hierarchy, 'TablixMembers'), 'TablixMember')
    node(member, 'Group', Name='Details')
    node(member, 'KeepTogether', 'true')
    node(tablix, 'DataSetName', 'Indicators')
    node(tablix, 'Top', '24cm')
    node(tablix, 'Left', '0cm')
    node(tablix, 'Height', '4cm')
    node(tablix, 'Width', '18cm')
    node(tablix, 'NoRowsMessage', 'No source-qualified indicators for this selection; no zero-impact inference.')
    node(body, 'Height', '28cm')
    node(section, 'Width', '18cm')
    page = node(section, 'Page')
    header = node(page, 'PageHeader')
    node(header, 'Height', '1.2cm')
    node(header, 'PrintOnFirstPage', 'true')
    node(header, 'PrintOnLastPage', 'true')
    textbox(node(header, 'ReportItems'), 'RepeatingTitle',
            '= "CHHHS research outcomes | " & Parameters!ReportMonth.Value',
            '0cm', bold=True)
    footer = node(page, 'PageFooter')
    node(footer, 'Height', '0.8cm')
    node(footer, 'PrintOnFirstPage', 'true')
    node(footer, 'PrintOnLastPage', 'true')
    textbox(node(footer, 'ReportItems'), 'PageNumber', '= "T18-outcomes-20261103.1 | " & Parameters!ReportMonth.Value & " | Page " & Globals!PageNumber & " of " & Globals!TotalPages', '0cm', size='8pt')
    for name, value in [('PageHeight', '29.7cm'), ('PageWidth', '21cm'), ('LeftMargin', '1.5cm'), ('RightMargin', '1.5cm'), ('TopMargin', '1.5cm'), ('BottomMargin', '1.5cm')]:
        node(page, name, value)
    node(report, 'Language', 'en-AU')
    node(report, 'ConsumeContainerWhitespace', 'true')
    ET.indent(report)
    return ET.tostring(report, encoding='utf-8', xml_declaration=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract', type=Path, default=Path('contracts/t18-outcome-indicators.json'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    with a.output.open('xb') as f:
        f.write(build(json.loads(a.contract.read_text())))


if __name__ == '__main__':
    main()
