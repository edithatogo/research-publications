"""Add the approved indicator dictionary and missing source-quality calculations.

Existing measure identities remain authoritative. Unavailable outcomes have reasons,
not invented zero-valued measures. No native operation is performed.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import base64
import copy
import json
import re

from scripts.deploy_report_definition import fingerprint, parts

TABLE = 'T18 Indicator Definition'
PATH = 'definition/tables/' + TABLE + '.tmdl'
DISPOSITIONS = {'matched': 'matched', 'deferred': 'deferred', 'ambiguous': 'ambiguous',
                'missing identifier': 'missing identifier', 'no match': 'no match', 'other': None}


def dictionary_rows(contract):
    rows = []
    seen = set()
    for metric in contract['metrics']:
        if metric['id'] in seen:
            raise ValueError('Duplicate indicator identity')
        seen.add(metric['id'])
        if not metric.get('unavailable_reason') or not metric.get('eligibility'):
            raise ValueError('Eligibility and unavailable reason required')
        if metric.get('readiness') == 'existing-measure' and not metric.get('measure'):
            raise ValueError('Existing measure reference required')
        if any(metric.get(k) is not None for k in ('owner', 'target', 'threshold')):
            raise ValueError('Authority-bound targets/owners require separate review')
        rows.append({k: str(metric.get(v) or '') for k, v in {
            'IndicatorID': 'id', 'DefinitionVersion': 'version', 'Label': 'label',
            'Grain': 'grain', 'SourceTable': 'source_table', 'MeasureName': 'measure',
            'Numerator': 'numerator', 'Denominator': 'denominator', 'DateRole': 'date_role',
            'Eligibility': 'eligibility', 'Unit': 'unit', 'Aggregation': 'aggregation',
            'NullPolicy': 'null_policy', 'Readiness': 'readiness',
            'UnavailableReason': 'unavailable_reason', 'CustodianStatus': 'owner_status',
            'Purpose': 'purpose', 'FrameworkDomain': 'framework_domain', 'Direction': 'direction',
            'Population': 'population', 'EvidenceStatus': 'evidence_status',
            'RefreshExpectation': 'refresh_expectation', 'Comparison': 'comparison',
        }.items()})
        rows[-1]['SourceLineage'] = json.dumps(metric.get('source_lineage', {}), sort_keys=True)
    return rows


def prepare(before, contract, *, expected_sha256):
    if fingerprint(before) != expected_sha256:
        raise ValueError('Complete model preimage drift')
    files = parts(before)
    if PATH in files:
        raise ValueError('Indicator table exists; reconcile its revision')
    for metric in contract['metrics']:
        if metric.get('measure'):
            path = 'definition/tables/' + metric['source_table'] + '.tmdl'
            text = files.get(path, b'').decode()
            name = metric['measure']
            if not re.search(r'^\tmeasure (?:' + re.escape(name) + "|'" + re.escape(name.replace("'", "''")) + "')\\s*=", text, re.M):
                raise ValueError('Existing measure missing: ' + name)
    rows = dictionary_rows(contract)
    if not rows:
        raise ValueError('Nonempty approved dictionary required')
    encoded = base64.b64encode(json.dumps(rows, separators=(',', ':')).encode()).decode()
    columns = ''.join('\tcolumn ' + name + '\n\t\tdataType: string\n\t\tsummarizeBy: none\n\t\tsourceColumn: ' + name + '\n\n' for name in rows[0])
    measures = []
    for suffix, disposition in DISPOSITIONS.items():
        predicate = ('PublicationSourceEvidence[Disposition] = "' + disposition + '"'
                     if disposition is not None else
                     'NOT(PublicationSourceEvidence[Disposition] IN {'
                     + ', '.join(json.dumps(v) for v in DISPOSITIONS.values() if v is not None) + '})')
        expression = '''VAR FacilityFiltered = ISFILTERED(Facility) || ISFILTERED(PublicationFacility)
VAR MatchedKeys = VALUES(PublicationFacility[CanonicalKey])
VAR Keys = FILTER(VALUES(Publication[CanonicalKey]),
    NOT FacilityFiltered || Publication[CanonicalKey] IN MatchedKeys)
RETURN CALCULATE(COUNTROWS(SUMMARIZE(PublicationSourceEvidence,
    PublicationSourceEvidence[CanonicalKey], PublicationSourceEvidence[Source])),
    KEEPFILTERS(TREATAS(Keys, PublicationSourceEvidence[CanonicalKey])),
    KEEPFILTERS(''' + predicate + '''))'''
        measures.append('\t/// Distinct canonical work/provider pairs in the current publication cohort; provider categories are not publications.\n'
                        + "\tmeasure 'T18 Source " + suffix + " pairs' =\n\t\t\t" + expression.replace('\n', '\n\t\t\t')
                        + '\n\t\tformatString: #,0\n\t\tdisplayFolder: T18 source reliability\n\n')
    text = "table '" + TABLE + "'\n\n" + ''.join(measures) + columns
    text += "\tpartition '" + TABLE + "' = m\n\t\tmode: import\n\t\tsource =\n\t\t\tlet\n\t\t\t    Rows = Json.Document(Binary.FromText(\"" + encoded + "\", BinaryEncoding.Base64)),\n\t\t\t    Result = Table.FromRecords(Rows)\n\t\t\tin Table.TransformColumnTypes(Result, List.Transform(Table.ColumnNames(Result), each {_, type text}))\n"
    result = copy.deepcopy(before)
    model = next(p for p in result['definition']['parts'] if p['path'] == 'definition/model.tmdl')
    root = files['definition/model.tmdl'].decode()
    if not re.search(r'^ref table ', root, re.M):
        raise ValueError('Native table reference declarations required')
    root += "\nref table '" + TABLE + "'\n"
    model['payload'] = base64.b64encode(root.encode()).decode()
    result['definition']['parts'].append({'path': PATH, 'payloadType': 'InlineBase64',
                                        'payload': base64.b64encode(text.encode()).decode()})
    return result
