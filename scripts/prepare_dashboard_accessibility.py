"""Prepare bounded accessibility fixes from an exact native PBIR preimage.

Local artifact preparation only. Preserves report/model identity, queries,
filters, visible text and all visual identities. Geometry changes fix five textboxes
and two pre-existing metadata tables that obscure content. Native keyboard,
zoom and rendering verification is required before promotion.

SPDX-License-Identifier: Apache-2.0
"""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path

METADATA_TABLES = {'ReportSection2': ('bc5eb9d737e586c0cd91', 1080, 1240),
                   'ReportSection4': ('49abdc3e306c680aa070', 1024, 1184)}

HEIGHTS = {
    ('ReportSection', 'heading'): 56,
    ('ReportSection', 'footer'): 40,
    ('ReportSection2', 'heading'): 56,
    ('ReportSection2', 'footer'): 40,
    ('ReportSection4', 'heading'): 56,
}


def contrast(foreground, background='#FFFFFF'):
    def luminance(value):
        channels = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
        return sum(c * w for c, w in zip(linear, (.2126, .7152, .0722)))
    a, b = sorted((luminance(foreground), luminance(background)))
    return (b + .05) / (a + .05)


def literal_text(value):
    raw = value.get('expr', {}).get('Literal', {}).get('Value', '')
    return raw[1:-1].replace("''", "'") if raw.startswith("'") and raw.endswith("'") else ''


def description(item, page_name):
    visual = item['visual']
    if visual['visualType'] == 'textbox':
        paragraphs = visual.get('objects', {}).get('general', [])
        words = ' '.join(run['value'] for obj in paragraphs
                         for paragraph in obj.get('properties', {}).get('paragraphs', [])
                         for run in paragraph.get('textRuns', []) if isinstance(run.get('value'), str))
    else:
        titles = visual.get('visualContainerObjects', {}).get('title', [])
        words = next((literal_text(t.get('properties', {}).get('text', {})) for t in titles
                      if literal_text(t.get('properties', {}).get('text', {}))), '')
        if not words:
            fields = [p.get('displayName') or p.get('nativeQueryRef') or p.get('queryRef', '')
                      for role in visual.get('query', {}).get('queryState', {}).values()
                      for p in role.get('projections', [])]
            words = ', '.join(dict.fromkeys(fields))
        if visual['visualType'] == 'slicer':
            words = 'Filter: ' + words
    if not words.strip():
        raise ValueError(f'No source-backed accessible description: {page_name}/{item["name"]}')
    # Do not freeze changing counts or infer identities/relationships in alt text.
    return (page_name + '. ' + words.strip())[:1000]


def prepare(document):
    result = copy.deepcopy(document)
    definition = result['definition']
    if definition.get('format') != 'PBIR':
        raise ValueError('Current native PBIR required')
    files = {}
    for part in definition['parts']:
        path = part['path']
        if path in files or Path(path).is_absolute() or '..' in Path(path).parts or '\\' in path:
            raise ValueError('Duplicate or unsafe definition path')
        files[path] = part

    def read(path):
        return json.loads(base64.b64decode(files[path]['payload'], validate=True))

    def write(path, value):
        if path not in files:
            files[path] = {'path': path, 'payloadType': 'InlineBase64'}
            definition['parts'].append(files[path])
        files[path]['payload'] = base64.b64encode(json.dumps(value, ensure_ascii=False, indent=2).encode()).decode()

    order = read('definition/pages/pages.json')['pageOrder']
    if len(order) != 9:
        raise ValueError('Expected current nine-page report')
    changed_heights = set()
    for page in order:
        page_info = read(f'definition/pages/{page}/page.json')
        paths = [p for p in files if p.startswith(f'definition/pages/{page}/visuals/') and p.endswith('/visual.json')]
        visuals = [(p, read(p)) for p in paths]
        if page in METADATA_TABLES:
            name, y, canvas = METADATA_TABLES[page]
            table = next((item for _, item in visuals if item['name'] == name), None)
            if table is None:
                raise ValueError('Expected metadata table identity missing')
            table['position'].update(x=32, y=y, width=1856, height=128)
            page_info['height'] = canvas
            write(f'definition/pages/{page}/page.json', page_info)
        # Tab order follows actual visual placement, not original creation time.
        visuals.sort(key=lambda pair: (pair[1]['position']['y'], pair[1]['position']['x'], pair[1]['name']))
        for index, (path, item) in enumerate(visuals):
            key = (page, item['name'])
            if key in HEIGHTS:
                item['position']['height'] = HEIGHTS[key]
                if key[1] == 'heading':
                    item['position']['y'] = 8
                changed_heights.add(key)
            position = item['position']
            if position['y'] + position['height'] > page_info['height']:
                raise ValueError('Visual extends beyond canvas')
            # Native reading-mode traversal visits descending tabOrder values.
            position['tabOrder'] = (len(visuals) - index - 1) * 1000
            vco = item['visual'].setdefault('visualContainerObjects', {})
            general = vco.setdefault('general', [{'properties': {}}])
            general[0].setdefault('properties', {})['altText'] = {
                'expr': {'Literal': {'Value': "'" + description(item, page_info['displayName']).replace("'", "''") + "'"}}}
            write(path, item)
    if changed_heights != set(HEIGHTS):
        raise ValueError('Expected five source textbox identities missing')
    # Keep the palette hues; darken only marks below 3:1 against the white canvas.
    report = read('definition/report.json')
    theme = report['themeCollection']['baseTheme']
    resource = next(p for p in report['resourcePackages'] if p['name'] == theme['type'])
    entry = next(i for i in resource['items'] if i['name'] == theme['name'])
    path = f"StaticResources/{resource['name']}/{entry['path']}"
    colors = read(path)
    for index, color in enumerate(colors['dataColors']):
        rgb = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
        while contrast(color) < 3:
            rgb = [max(0, channel - 1) for channel in rgb]
            color = '#' + ''.join(f'{channel:02X}' for channel in rgb)
        colors['dataColors'][index] = color
    palette = colors['dataColors']
    suffix = hashlib.sha256(json.dumps(palette).encode()).hexdigest()[:12]
    name = f'RIMSAccessible-{suffix}.json'
    custom = report['themeCollection'].get('customTheme')
    if custom and custom['name'] != name:
        raise ValueError('Existing custom theme requires explicit reconciliation')
    # SharedResources base themes are regenerated by the service; use a supported
    # registered custom theme containing only the bounded palette override.
    theme_path = f'StaticResources/RegisteredResources/{name}'
    write(theme_path, {'$schema': 'https://raw.githubusercontent.com/microsoft/powerbi-desktop-samples/main/Report%20Theme%20JSON%20Schema/reportThemeSchema-2.159.json',
                       'name': name, 'dataColors': palette})
    report['themeCollection']['customTheme'] = {'name': name, 'type': 'RegisteredResources',
        'reportVersionAtImport': theme.get('reportVersionAtImport', {'visual': '2.12.0', 'report': '3.4.0', 'page': '2.3.1'})}
    registered = next((r for r in report['resourcePackages'] if r['name'] == 'RegisteredResources'), None)
    if registered is None:
        registered = {'name': 'RegisteredResources', 'type': 'RegisteredResources', 'items': []}
        report['resourcePackages'].append(registered)
    if not any(i['name'] == name for i in registered['items']):
        registered['items'].append({'name': name, 'path': name, 'type': 'CustomTheme'})
    write('definition/report.json', report)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--definition', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.definition.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.expected_sha256:
        raise ValueError('Native preimage hash mismatch')
    result = prepare(json.loads(raw))
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
    print('Prepared five heights, spatial tab order, source-backed alt text and contrast-safe marks; native checks pending')


if __name__ == '__main__':
    main()
