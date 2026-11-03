"""Prepare three-provider dispositions on the existing source-quality page.

Local candidate only. Requires accepted T18 source-pair measures before deployment.
All existing queries/navigation remain; the retained detail table stays scrollable.
SPDX-License-Identifier: Apache-2.0
"""
import base64
import copy
import json

from scripts.deploy_report_definition import fingerprint, parts
from scripts.dashboard_reader_source import visual, direct
from scripts.prepare_t18_indicator_model import DISPOSITIONS, TABLE

PAGE = 'definition/pages/ReportSection/'


def prepare(before, *, expected_sha256):
    if fingerprint(before) != expected_sha256:
        raise ValueError('Complete report preimage drift')
    files = parts(before)
    if json.loads(files[PAGE + 'page.json']).get('displayName') != 'Publication Sources & Quality':
        raise ValueError('Source-quality page identity drift')
    target = PAGE + 'visuals/t18-provider-dispositions/visual.json'
    if target in files:
        raise ValueError('Provider visual already exists')
    table_path = PAGE + 'visuals/reconciliation-register/visual.json'
    table = json.loads(files[table_path])
    if table['position']['y'] != 552 or table['position']['height'] != 352:
        raise ValueError('Source detail layout drift')
    table['position'].update(y=712, height=192)
    bindings = []
    for suffix in DISPOSITIONS:
        measure = 'T18 Source ' + suffix + ' pairs'
        bindings.append({'field': {'Measure': {'Expression': {'SourceRef': {'Entity': TABLE}},
                                             'Property': measure}},
                         'queryRef': TABLE + '.' + measure,
                         'displayName': suffix.capitalize()})
    decoded = {k: v.decode('utf-8-sig') for k, v in files.items() if k.endswith('.json')}
    chart = visual(decoded, 't18-provider-dispositions', 'tableEx', (32, 504, 1856, 192),
                   'Retained work/provider pairs by disposition; not publication totals',
                   roles={'Values': [direct('PublicationSourceEvidence', 'Source')] + bindings})
    chart['position'].update(z=850, tabOrder=8500)
    containers = chart['visual']['visualContainerObjects']
    containers['title'][0]['properties'].pop('fontSize', None)
    containers.pop('padding', None)
    containers['subTitle'] = [{'properties': {'show': {'expr': {'Literal': {'Value': 'false'}}}}}]
    containers['padding'] = [{'properties': {
        side: {'expr': {'Literal': {'Value': str(value) + 'D'}}}
        for side, value in [('top', 4), ('bottom', 4), ('left', 8), ('right', 8)]}}]
    containers['spacing'] = [{'properties': {
        key: {'expr': {'Literal': {'Value': value}}} for key, value in [
            ('customizeSpacing', 'true'), ('spaceAbovePlotArea', '0D'),
            ('spaceBelowSubTitle', '0D'), ('spaceAboveDivider', '0D'), ('verticalSpacing', '0D')]}}]
    chart['visual']['objects'] = {
        'columnHeaders': [{'properties': {
            'fontSize': {'expr': {'Literal': {'Value': '14D'}}},
            'autoSizeColumnWidth': {'expr': {'Literal': {'Value': 'true'}}},
            'columnAdjustment': {'expr': {'Literal': {'Value': "'growToFit'"}}}}}],
        'values': [{'properties': {'fontSize': {'expr': {'Literal': {'Value': '16D'}}}}}],
        'grid': [{'properties': {'rowPadding': {'expr': {'Literal': {'Value': '0D'}}}}}],
        'total': [{'properties': {'show': {'expr': {'Literal': {'Value': 'false'}}}}}],
    }
    # A native table exposes all three providers and exact counts without relying
    # on colour or a category scrollbar. Native readability is still required.
    updates = {table_path: table, target: chart}
    for name in ['source-overlap', 'dedup-method', 'facility-contributions']:
        path = PAGE + 'visuals/' + name + '/visual.json'
        if path in files:
            doc = json.loads(files[path])
            if doc['position'].get('y') != 224 or doc['position'].get('height') != 312:
                raise ValueError('Source overview layout drift: ' + name)
            doc['position']['height'] = 264
            updates[path] = doc
    result = copy.deepcopy(before)
    indexed = {p['path']: p for p in result['definition']['parts']}
    for path, doc in updates.items():
        payload = base64.b64encode((json.dumps(doc, indent=2) + '\n').encode()).decode()
        if path in indexed:
            indexed[path]['payload'] = payload
        else:
            result['definition']['parts'].append({'path': path, 'payloadType': 'InlineBase64', 'payload': payload})
    return result
