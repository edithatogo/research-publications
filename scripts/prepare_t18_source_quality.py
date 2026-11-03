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
    table['position'].update(y=760, height=144)
    bindings = []
    for suffix in DISPOSITIONS:
        measure = 'T18 Source ' + suffix + ' pairs'
        bindings.append({'field': {'Measure': {'Expression': {'SourceRef': {'Entity': TABLE}},
                                             'Property': measure}},
                         'queryRef': TABLE + '.' + measure})
    decoded = {k: v.decode('utf-8-sig') for k, v in files.items() if k.endswith('.json')}
    chart = visual(decoded, 't18-provider-dispositions', 'barChart', (32, 552, 1856, 192),
                   'Retained work/provider pairs by disposition; not publication totals',
                   roles={'Category': [direct('PublicationSourceEvidence', 'Source')], 'Y': bindings})
    chart['position'].update(z=850, tabOrder=8500)
    containers = chart['visual']['visualContainerObjects']
    containers['title'][0]['properties'].pop('fontSize', None)
    containers.pop('padding', None)
    # Theme-derived colours and native data labels; provider and series names
    # carry meaning independently of colour. Native readability is still required.
    updates = {table_path: table, target: chart}
    result = copy.deepcopy(before)
    indexed = {p['path']: p for p in result['definition']['parts']}
    for path, doc in updates.items():
        payload = base64.b64encode((json.dumps(doc, indent=2) + '\n').encode()).decode()
        if path in indexed:
            indexed[path]['payload'] = payload
        else:
            result['definition']['parts'].append({'path': path, 'payloadType': 'InlineBase64', 'payload': payload})
    return result
