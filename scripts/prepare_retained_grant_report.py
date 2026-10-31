"""Add one grant-reference reader page to an unpacked existing PBIR report.

Transport remains with powerbi-report-author; no native calls or rebinding.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import re
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.dashboard_reader_source import digest
from scripts.prepare_dashboard_overview import projection
from scripts.prepare_retained_grant_connection import TABLE, TABLE_PATH
from scripts.plan_publication_stub_restore import private_output
import base64

PAGE = 'RetainedGrantReferences'


def build(files, model_packet, *, expected_report_sha256, expected_model_id):
    if digest(files) != expected_report_sha256:
        raise ValueError('Complete report capture drift')
    binding = json.loads(files['definition.pbir'])['datasetReference']
    connection = binding.get('byConnection', {}).get('connectionString', '')
    ids = re.findall(r'(?:^|;)\s*semanticmodelid\s*=\s*([^;]+)', connection, re.I)
    if ids != [expected_model_id]:
        raise ValueError('Exact existing model binding required; no rebind')
    parts = {p['path']: p for p in model_packet['modelDefinition']['definition']['parts']}
    if TABLE_PATH not in parts:
        raise ValueError('Prepared grant table missing')
    table = base64.b64decode(parts[TABLE_PATH]['payload'], validate=True).decode()
    publication = base64.b64decode(parts['definition/tables/Publication.tmdl']['payload'], validate=True).decode()
    columns = ['PublicationPMID', 'ToLabel', 'ToKey', 'IdentityStatus', 'ReviewState',
               'SourceURL', 'SourceVersion', 'SourcePaths', 'EvidenceKey']
    if any(not re.search(r'^\tcolumn ' + re.escape(c) + r'\s*$', table, re.M) for c in columns):
        raise ValueError('Reader/table field contract drift')
    if any(not re.search(r'^\tcolumn ' + c + r'\s*$', publication, re.M) for c in ['CanonicalKey', 'Title']):
        raise ValueError('Publication reader fields missing')
    order = json.loads(files['definition/pages/pages.json'])
    original_order = order['pageOrder']
    base = 'definition/pages/' + PAGE + '/'
    if PAGE in original_order or any(p.startswith(base) for p in files):
        raise ValueError('Existing reader requires reconciliation')
    templates = {}
    for name, raw in files.items():
        if name.endswith('/visual.json'):
            v = json.loads(raw)
            kind = v.get('visual', {}).get('visualType')
            if kind in ['textbox', 'tableEx', 'slicer']:
                templates.setdefault(kind, v)
    if set(templates) != {'textbox', 'tableEx', 'slicer'}:
        raise ValueError('Accepted connector/visual templates required')
    result = dict(files)
    def emit(path, value):
        result[path] = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    page_template = json.loads(files['definition/pages/' + original_order[0] + '/page.json'])
    page = {k: copy.deepcopy(v) for k, v in page_template.items() if k in ['$schema', 'displayOption']}
    page.update(name=PAGE, displayName='Candidate grant references', width=1920, height=1080)
    emit(base + 'page.json', page)
    def add(name, kind, rect, *, fields=None, words=None):
        v = copy.deepcopy(templates[kind])
        v['name'] = name
        v['position'] = dict(zip(['x', 'y', 'width', 'height'], rect), z=len(result), tabOrder=len(result))
        v.pop('filterConfig', None)
        visual = v['visual']
        for k in ['query', 'objects', 'columnProperties', 'projections', 'prototypeQuery', 'visualContainerObjects']:
            visual.pop(k, None)
        if fields:
            visual['query'] = {'queryState': {'Values': {'projections': fields}}}
        if words is not None:
            visual['objects'] = {'general': [{'properties': {'paragraphs': [
                {'textRuns': [{'value': words, 'textStyle': {'fontFamily': 'Segoe UI', 'fontSize': '16pt'}}]}]}}]}
        emit(base + 'visuals/' + name + '/visual.json', v)
    add('grant-reference-heading', 'textbox', (32, 16, 1856, 56), words='Candidate grant references')
    add('grant-reference-limits', 'textbox', (32, 80, 1856, 112), words=(
        'Source-reported grant references, not confirmed funding relationships. '
        'Select a publication key to inspect identifiers and retained provenance. '
        'Agency labels do not establish award-register identity; human review remains unchanged.'))
    add('publication-selector', 'slicer', (32, 208, 1856, 112),
        fields=[projection('Publication', 'CanonicalKey', label='Publication key')])
    add('grant-reference-evidence', 'tableEx', (32, 344, 1856, 704), fields=[
        projection('Publication', 'Title', label='Publication'),
        *[projection(TABLE, c, label=c) for c in columns]])
    order['pageOrder'] = [*original_order, PAGE]
    emit('definition/pages/pages.json', order)
    if any(result[k] != v for k, v in files.items() if k != 'definition/pages/pages.json'):
        raise ValueError('Protected report content changed')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--model-packet', type=Path, required=True)
    p.add_argument('--report-sha256', required=True)
    p.add_argument('--model-id', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    private_output(a.output, [a.source, a.model_packet])
    files = {f.relative_to(a.source).as_posix(): f.read_bytes() for f in a.source.rglob('*') if f.is_file()}
    result = build(files, json.loads(a.model_packet.read_bytes()),
                   expected_report_sha256=a.report_sha256, expected_model_id=a.model_id)
    a.output.mkdir()
    for name, raw in result.items():
        path = a.output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    print('prepared additive reader page; no native save or rebind')


if __name__ == '__main__':
    main()
