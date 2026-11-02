"""Add retained GrantConnect history to existing complete model/report captures.

No acquisition, source refresh, relationship inference or native invocation.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
import argparse
import json
import re
from pathlib import Path
from uuid import UUID

from scripts.deploy_report_definition import fingerprint, parts
from scripts.prepare_outcome_reader import emit
from scripts.prepare_dashboard_overview import SCHEMA, projection

TABLES = {'awards': 'GrantConnectAwardHistory',
          'closed': 'GrantConnectClosedHistory', 'links': 'GrantConnectAwardOpportunity'}
FIELDS = ('HistoryKey', 'Title', 'GAID', 'GOID', 'EvidenceHash')


def replace_part(document, path, content):
    original = [p for p in document['definition']['parts'] if p['path'] == path]
    if len(original) != 1:
        raise ValueError('Exact existing part required')
    document['definition']['parts'].remove(original[0])
    emit(document, path, content)


def prepare(model, report, *, model_sha256, report_sha256, site, lists):
    """Preserve every existing part; expose distinct entities without guessed joins."""
    if fingerprint(model) != model_sha256 or fingerprint(report) != report_sha256:
        raise ValueError('Complete exact model/report preimages required')
    mp, rp = parts(model), parts(report)
    if set(lists) != set(TABLES) or len(set(lists.values())) != 3:
        raise ValueError('Three distinct history list bindings required')
    if not re.fullmatch(r'https://[a-z0-9-]+(?:-my)?\.sharepoint\.com/[A-Za-z0-9_/-]+', site):
        raise ValueError('Exact existing HTTPS SharePoint site required')
    if not any(('SharePoint.Tables(' + json.dumps(site)).encode() in raw
               for path, raw in mp.items() if path.startswith('definition/tables/')):
        raise ValueError('History must reuse an existing model SharePoint source')
    for value in lists.values():
        UUID(value)
    model_root = mp['definition/model.tmdl'].decode()
    result_model, result_report = copy.deepcopy(model), copy.deepcopy(report)
    order_path = 'definition/pages/pages.json'
    order = json.loads(rp[order_path])
    prefix = 'definition/pages/GrantConnectHistory/'
    if 'GrantConnectHistory' in order['pageOrder'] or any(p.startswith(prefix) for p in rp):
        raise ValueError('Existing history page needs an explicit update')
    for entity, name in TABLES.items():
        path = f'definition/tables/{name}.tmdl'
        if path in mp or re.search(r'(?m)^\s*ref table ' + name + r'\s*$', model_root):
            raise ValueError('Existing history table must be preserved')
        lines = ['table ' + name]
        for field in FIELDS:
            lines += ['\tcolumn ' + field, '\t\tdataType: string',
                      '\t\tsummarizeBy: none', '\t\tsourceColumn: ' + field]
        selected = '{' + ', '.join(json.dumps(f) for f in FIELDS) + '}'
        typed = '{' + ', '.join('{' + json.dumps(f) + ', type text}' for f in FIELDS) + '}'
        lines += ['\tpartition ' + name + ' = m', '\t\tmode: import', '\t\tsource =',
                  '\t\t\tlet', '\t\t\t Source = SharePoint.Tables(' + json.dumps(site) + ', [Implementation = "2.0", ViewMode = "All"]),',
                  '\t\t\t Rows = Source{[Id = ' + json.dumps(str(UUID(lists[entity]))) + ']}[Items],',
                  '\t\t\t Selected = Table.SelectColumns(Rows, ' + selected + ', MissingField.Error),',
                  '\t\t\t Typed = Table.TransformColumnTypes(Selected, ' + typed + ')',
                  '\t\t\tin Typed']
        emit(result_model, path, '\n'.join(lines) + '\n')
        model_root += '\nref table ' + name + '\n'
    replace_part(result_model, 'definition/model.tmdl', model_root)
    emit(result_report, prefix + 'page.json', json.dumps({
        '$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json',
        'name': 'GrantConnectHistory', 'displayName': 'GrantConnect history',
        'displayOption': 'FitToPage', 'height': 1320, 'width': 1920}))
    heading = {'$schema': SCHEMA, 'name': 'history-heading',
        'position': {'x': 32, 'y': 16, 'z': 0, 'height': 104, 'width': 1856, 'tabOrder': 0},
        'visual': {'visualType': 'textbox', 'objects': {'general': [{'properties': {
            'paragraphs': [{'textRuns': [{'value': 'GrantConnect history — last processed list snapshot; may be partial while historical import continues. Award versions, closed opportunities and confirmed GA/GO pairs remain separate. These source records do not establish institutional applications or publication funding. Award-version counts are not distinct-grant counts.',
                'textStyle': {'fontFamily': 'Segoe UI', 'fontSize': '16pt'}}]}]}}]}}}
    emit(result_report, prefix + 'visuals/history-heading/visual.json', json.dumps(heading))
    titles = {'awards': 'Award versions', 'closed': 'Closed or archived opportunities',
              'links': 'Confirmed award-version / opportunity identifiers'}
    for index, (entity, table) in enumerate(TABLES.items()):
        visual = {'$schema': SCHEMA, 'name': 'history-' + entity,
            'position': {'x': 32, 'y': 136 + index * 384, 'z': index + 1,
                         'height': 352, 'width': 1856, 'tabOrder': index + 1},
            'visual': {'visualType': 'tableEx', 'visualContainerObjects': {
                'title': [{'properties': {'show': {'expr': {'Literal': {'Value': 'true'}}},
                    'text': {'expr': {'Literal': {'Value': "'" + titles[entity] + "'"}}}}}]},
                'query': {'queryState': {
                'Values': {'projections': [projection(table, f) for f in FIELDS]}}}}}
        emit(result_report, prefix + f'visuals/history-{entity}/visual.json', json.dumps(visual))
    order['pageOrder'].append('GrantConnectHistory')
    replace_part(result_report, order_path, json.dumps(order))
    if any(parts(result_model)[p] != raw for p, raw in mp.items() if p != 'definition/model.tmdl'):
        raise ValueError('Protected model content changed')
    if any(parts(result_report)[p] != raw for p, raw in rp.items() if p != order_path):
        raise ValueError('Protected report content changed')
    return {'model': result_model, 'report': result_report,
            'process_tables': list(TABLES.values()), 'native_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('model', 'report', 'binding', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    private = Path(__file__).resolve().parents[1] / 'private/ops'
    if not args.output.resolve().is_relative_to(private.resolve()):
        raise ValueError('Private candidate output required')
    model, report, binding = (json.loads(p.read_bytes()) for p in
                              (args.model, args.report, args.binding))
    packet = prepare(model, report, model_sha256=fingerprint(model),
                     report_sha256=fingerprint(report), site=binding['site'], lists=binding['lists'])
    args.output.mkdir(parents=True, exist_ok=False)
    for name in ('model', 'report'):
        (args.output / (name + '-candidate.json')).write_text(json.dumps(packet[name]))
        (args.output / (name + '-inverse.json')).write_text(json.dumps(locals()[name]))
    (args.output / 'processing-scope.json').write_text(json.dumps({
        'type': 'full', 'commitMode': 'transactional', 'retryCount': 0,
        'objects': [{'table': t} for t in packet['process_tables']], 'applyRefreshPolicy': False}))
    (args.output / 'status.json').write_text(json.dumps({
        'source': 'retained SharePoint history; no provider acquisition',
        'model_before_sha256': fingerprint(model), 'report_before_sha256': fingerprint(report),
        'native_verified': False, 'processing_submitted': False}))


if __name__ == '__main__':
    main()
