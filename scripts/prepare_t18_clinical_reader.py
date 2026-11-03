"""Repair Clinical Analytics against a complete, fingerprinted native definition.

Prepare only: deployment, processing and rendering have separate acceptance gates.
Preserves all existing binding and visual identities and every unrelated part.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import base64
import copy
import json
from pathlib import Path

from scripts.deploy_report_definition import fingerprint, parts

PAGE = 'definition/pages/ReportSection4/'
TITLES = {
    'oa-rate': ('Open access compliance rate', 'Open access among assessed publications'),
    'oa-papers': ('Open access publications', 'Known open publications'),
    'trials-count': ('Clinical trial linked papers', 'PubMed clinical-trial-type publications'),
    'funded-papers': ('Grant-funded publications', 'Publications with reviewed funding links'),
    'specialty-distribution': ('Publications by clinical directorate and specialty', 'Publications by facility/service'),
    'for-division': ('ANZSRC 2020 Field of Research (FoR) division', 'Provider-reported research field'),
    'study-design-breakdown': ('Evidence hierarchy and study designs', 'Registered study design'),
    'oa-distribution': ('Open access distribution (Gold / Green / Hybrid / Closed)', 'Retained OA status; blank is unknown'),
}
TEXT = {
    'caption': ('Clinical directorate specialty mapping,',
                'Source-qualified publication characteristics. OA share describes assessed works; coverage describes all included works. Research fields retain provider classifications.'),
    'footer': ('Field of Research mapped using ANZSRC',
               'OA is dated retained provider evidence, not policy compliance. Study design retains register assertions; trial-type papers are not unique trials. Reviewed funding links are not award amounts. Facility totals overlap; no clinical impact or ANZSRC crosswalk is inferred.'),
}


def literal(value):
    return "'" + value.replace("'", "''") + "'"


def prepare(before, *, expected_sha256):
    if fingerprint(before) != expected_sha256:
        raise ValueError('Complete report preimage drift')
    source = parts(before)
    page = json.loads(source[PAGE + 'page.json'])
    if page.get('displayName') != 'Clinical Analytics':
        raise ValueError('Clinical page identity drift')
    result = copy.deepcopy(before)
    updates = {}
    for name, (old, new) in TITLES.items():
        path = PAGE + 'visuals/' + name + '/visual.json'
        doc = json.loads(source[path])
        titles = doc['visual']['visualContainerObjects']['title']
        if len(titles) != 1 or titles[0]['properties']['text']['expr']['Literal']['Value'] != literal(old):
            raise ValueError('Visual title preimage drift: ' + name)
        titles[0]['properties']['text']['expr']['Literal']['Value'] = literal(new)
        updates[path] = doc
    for name, (prefix, replacement) in TEXT.items():
        path = PAGE + 'visuals/' + name + '/visual.json'
        doc = json.loads(source[path])
        runs = [r for g in doc['visual']['objects']['general']
                for p in g['properties']['paragraphs'] for r in p['textRuns']]
        if len(runs) != 1 or not runs[0]['value'].startswith(prefix):
            raise ValueError('Text preimage drift: ' + name)
        runs[0]['value'] = replacement
        if name == 'footer':
            position = doc.get('position', {})
            if position.get('y') == 960 and position.get('height') == 40:
                position['height'] = 56
        updates[path] = doc
    cards = ['oa-rate', 'oa-papers', 'oa-assessed', 'oa-coverage', 'trials-count', 'funded-papers']
    template = json.loads(source[PAGE + 'visuals/oa-rate/visual.json'])
    for name, label, measure in [
        ('oa-assessed', 'OA-assessed publications', 'K02 OA assessed publications'),
        ('oa-coverage', 'OA assessment coverage', 'K02 OA assessment coverage'),
    ]:
        path = PAGE + 'visuals/' + name + '/visual.json'
        if path in source:
            raise ValueError('New visual identity already exists')
        # Rewrite only the known explicit measure binding; preserve native query shape.
        def replace(value):
            if isinstance(value, dict):
                return {k: replace(v) for k, v in value.items()}
            if isinstance(value, list):
                return [replace(v) for v in value]
            if isinstance(value, str):
                return value.replace('Open Access Rate', measure)
            return value
        doc = replace(copy.deepcopy(template))
        doc['name'] = name
        doc['visual']['visualContainerObjects']['title'][0]['properties']['text']['expr']['Literal']['Value'] = literal(label)
        updates[path] = doc
    for index, name in enumerate(cards):
        path = PAGE + 'visuals/' + name + '/visual.json'
        updates[path]['position'].update(x=32 + index * 312,
                                         y=112, width=296, height=128,
                                         tabOrder=2000 + index * 1000)
        updates[path]['visual']['visualContainerObjects']['title'][0]['properties']['fontSize'] = {
            'expr': {'Literal': {'Value': '14D'}}}
    # Retain the native activity detail and all slicers on the specified 1080 canvas.
    # The table remains a scrollable, keyboard-addressable native table.
    if page.get('height') == 1296 and page.get('width') == 1920:
        page['height'] = 1080
        updates[PAGE + 'page.json'] = page
        for name in ['facility-filter', 'year-filter', 'oa-filter', 'study-filter']:
            path = PAGE + 'visuals/' + name + '/visual.json'
            doc = json.loads(source[path])
            doc['position'].update(y=256, height=96)
            updates[path] = doc
        for name, y, height in [('specialty-distribution', 368, 224), ('for-division', 368, 224),
                                ('oa-distribution', 608, 208), ('study-design-breakdown', 608, 208)]:
            path = PAGE + 'visuals/' + name + '/visual.json'
            updates[path]['position'].update(y=y, height=height)
            updates[path]['visual']['visualContainerObjects']['subTitle'] = [
                {'properties': {'show': {'expr': {'Literal': {'Value': 'false'}}}}}]
        path = PAGE + 'visuals/49abdc3e306c680aa070/visual.json'
        doc = json.loads(source[path])
        doc['position'].update(y=832, height=160, tabOrder=14000)
        updates[path] = doc
        updates[PAGE + 'visuals/footer/visual.json']['position'].update(y=1008, height=56,
                                                                     tabOrder=15000)
    for path, doc in updates.items():
        if 'visual' not in doc:
            continue
        containers = doc['visual'].setdefault('visualContainerObjects', {})
        titles = containers.get('title', [])
        value = titles[0]['properties']['text']['expr']['Literal']['Value'] if titles else "''"
        label = value[1:-1].replace("''", "'") if value.startswith("'") and value.endswith("'") else ''
        if label:
            general = containers.setdefault('general', [])
            if not general:
                general.append({})
            general[0].setdefault('properties', {})['altText'] = {'expr': {'Literal': {'Value': literal(label)}}}
    indexed = {p['path']: p for p in result['definition']['parts']}
    for path, doc in updates.items():
        payload = base64.b64encode((json.dumps(doc, indent=2) + '\n').encode()).decode()
        if path in indexed:
            indexed[path]['payload'] = payload
        else:
            result['definition']['parts'].append({'path': path, 'payload': payload, 'payloadType': 'InlineBase64'})
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('preimage', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--expected-sha256', required=True)
    a = p.parse_args()
    result = prepare(json.loads(a.preimage.read_bytes()), expected_sha256=a.expected_sha256)
    with a.output.open('x') as f:
        json.dump(result, f, indent=2)


if __name__ == '__main__':
    main()
