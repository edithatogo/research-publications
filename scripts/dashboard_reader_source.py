"""Frozen-input guards for local reader builders; no native transport or model edits.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import re
from pathlib import Path
from scripts.prepare_dashboard_overview import literal, projection


def digest(files):
    value = hashlib.sha256()
    for name, raw in sorted(files.items(), key=lambda item: Path(item[0])):
        value.update(name.encode()+b'\0'+len(raw).to_bytes(8, 'big')+raw)
    return value.hexdigest()


def capture(source, expected_sha256):
    source = Path(source)
    if source.is_symlink() or any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('Symbolic source refused')
    files = {p.relative_to(source).as_posix(): p.read_bytes()
             for p in source.rglob('*') if p.is_file()}
    if digest(files) != expected_sha256:
        raise ValueError('Complete report baseline drift')
    if not {'definition.pbir', 'definition/report.json', 'definition/pages/pages.json'} <= files.keys():
        raise ValueError('Complete modern PBIR required')
    order = json.loads(files['definition/pages/pages.json']).get('pageOrder')
    pages = {Path(p).parent.name for p in files
             if p.startswith('definition/pages/') and p.endswith('/page.json') and len(Path(p).parts) == 4}
    if (not isinstance(order, list) or not order or
            any(not isinstance(p, str) or not p or p != p.strip() for p in order) or
            len(order) != len(set(order)) or set(order) != pages):
        raise ValueError('Complete unique page inventory required')
    return files


def model_contract(raw, expected_sha256):
    """Read the frozen complete 61-part/53-table TMDL capture without changing it.

    Field existence/type is a reader dependency, never proof of data completeness,
    keys, processing, relationship admission or human review.
    """
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Frozen complete model hash drift')
    definition = json.loads(raw).get('definition', {})
    parts = definition.get('parts')
    if definition.get('format') != 'TMDL' or not isinstance(parts, list) or len(parts) != 61:
        raise ValueError('Complete frozen 61-part model required')
    files = {}
    for part in parts:
        path = part.get('path')
        if (not isinstance(path, str) or path in files or Path(path).is_absolute() or
                '..' in Path(path).parts or '\\' in path or part.get('payloadType') != 'InlineBase64'):
            raise ValueError('Duplicate or unsafe model part')
        files[path] = base64.b64decode(part['payload'], validate=True).decode('utf-8-sig')
    if 'definition/model.tmdl' not in files:
        raise ValueError('Complete model root required')
    result = {}
    identifier = r"(?:'((?:[^']|'')+)'|([^\n=]+?))"
    for path, text in files.items():
        if not path.startswith('definition/tables/') or not path.endswith('.tmdl'):
            continue
        name = Path(path).stem
        table_declarations = list(re.finditer(r'^table '+identifier+r'\s*$', text, re.M))
        match = table_declarations[0] if len(table_declarations) == 1 else None
        if not match or (match.group(1) or match.group(2)).replace("''", "'") != name or name in result:
            raise ValueError('Model table identity drift')
        fields = {'columns': {}, 'measures': set()}
        declarations = list(re.finditer(r'^\t(column|measure) '+identifier+r'\s*(?:=|$)', text, re.M))
        for index, declaration in enumerate(declarations):
            kind, quoted, bare = declaration.groups()
            field = (quoted or bare).replace("''", "'").strip()
            target = fields['columns'] if kind == 'column' else fields['measures']
            if field in target:
                raise ValueError('Duplicate consumer field')
            if kind == 'measure':
                target.add(field)
            else:
                block = text[declaration.end():declarations[index+1].start() if index+1 < len(declarations) else len(text)]
                dtype = re.search(r'^\t\tdataType: (\w+)\s*$', block, re.M)
                target[field] = dtype.group(1) if dtype else None
        result[name] = fields
    if len(result) != 53:
        raise ValueError('Complete frozen 53-table model required')
    return {'sha256': expected_sha256, 'tables': result}


def dependencies(contract, columns, measures=()):
    """Return exact missing/type dependencies; a missing scalar is never zero."""
    issues = []
    for table, field, types in columns:
        actual = contract['tables'].get(table, {}).get('columns', {}).get(field)
        if actual not in types:
            issues.append({'table': table, 'field': field, 'kind': 'Column',
                           'actual_type': actual, 'required_types': sorted(types)})
    for table, field in measures:
        if field not in contract['tables'].get(table, {}).get('measures', set()):
            issues.append({'table': table, 'field': field, 'kind': 'Measure'})
    return issues


def require(contract, columns, measures=()):
    missing = dependencies(contract, columns, measures)
    if missing:
        raise ValueError('Incomplete consumer contract: '+json.dumps(missing, sort_keys=True))


def require_table_key(doc, table, key, contract):
    """Check exact direct-field consumer identities; do not infer aliases or joins."""
    if doc['visual']['visualType'] != 'tableEx':
        raise ValueError('Expected existing table identity/type')
    selected = []
    for role in doc['visual'].get('query', {}).get('queryState', {}).values():
        for item in role.get('projections', []):
            field = item.get('field', {})
            binding = field.get('Column', {})
            name = binding.get('Property')
            if (set(field) != {'Column'} or binding.get('Expression') != {'SourceRef': {'Entity': table}} or
                    item.get('queryRef') != table+'.'+str(name) or
                    name not in contract['tables'].get(table, {}).get('columns', {})):
                raise ValueError('Existing table consumer binding drift')
            selected.append(name)
    if key not in selected or len(selected) != len(set(selected)):
        raise ValueError('Incomplete or duplicate existing table key')


def words(value):
    return literal("'"+value.replace("'", "''")+"'")


def visual(files, name, kind, rect, title, *, text=None, roles=None):
    """Use only the current visual schema; never inherit queries/filter context."""
    schema = json.loads(files['definition/pages/ReportSection3/visuals/heading/visual.json'])['$schema']
    x, y, width, height = rect
    item = {'$schema': schema, 'name': name,
            'position': {'x': x, 'y': y, 'width': width, 'height': height, 'z': 0, 'tabOrder': 0},
            'visual': {'visualType': kind, 'drillFilterOtherVisuals': True,
                       'visualContainerObjects': {
                           'title': [{'properties': {'show': literal('false' if text is not None else 'true'),
                                                     'text': words(title), 'fontSize': literal('18D')}}],
                           'general': [{'properties': {'altText': words(title)}}],
                           'padding': [{'properties': {side: literal('0D') for side in ('top', 'bottom')}}]}}}
    if roles:
        item['visual']['query'] = {'queryState': {role: {'projections': values} for role, values in roles.items()}}
    if text is not None:
        item['visual']['objects'] = {'general': [{'properties': {'paragraphs': [
            {'textRuns': [{'value': text, 'textStyle': {'fontFamily': 'Segoe UI', 'fontSize': '18px'}}]}]}}]}
    elif kind == 'card':
        item['visual']['objects'] = {'labels': [{'properties': {'fontSize': literal('28D')}}]}
    return item


def direct(table, field, *, measure=False, maximum=False, count=False, label=None):
    if maximum and count:
        raise ValueError('Ambiguous aggregation')
    item = projection(table, field, measure=measure, label=label)
    if maximum or count:
        item['field'] = {'Aggregation': {'Expression': item['field'], 'Function': 4 if maximum else 5}}
        item['queryRef'] = ('Max' if maximum else 'CountNonNull')+'('+table+'.'+field+')'
    return item


def add_page(files, page, title, height, visuals):
    prefix = 'definition/pages/'+page+'/'
    if any(p.startswith(prefix) for p in files):
        raise ValueError('Page already exists; do not replace retained content')
    schema = json.loads(files['definition/pages/ReportSection3/page.json'])['$schema']
    order = json.loads(files['definition/pages/pages.json'])
    if page in order['pageOrder']:
        raise ValueError('Page already in order')
    order['pageOrder'].append(page)
    updates = {'definition/pages/pages.json': order,
               prefix+'page.json': {'$schema': schema, 'name': page, 'displayName': title,
                                    'width': 1920, 'height': height, 'displayOption': 'FitToWidth'}}
    for index, item in enumerate(visuals):
        name = prefix+'visuals/'+item['name']+'/visual.json'
        if name in updates:
            raise ValueError('Duplicate new visual')
        item = copy.deepcopy(item)
        item['position'].update(z=index*100, tabOrder=(len(visuals)-index)*1000)
        updates[name] = item
    return updates


def write_candidate(source, output, files, updates, contract, status, *, missing=()):
    output = Path(output).resolve(); source = Path(source).resolve()
    manifest = output.with_name(output.name+'.manifest.json')
    if output.exists() or manifest.exists() or output == source or source in output.parents:
        raise ValueError('Exclusive output/manifest outside source required')
    encoded = {p: (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode() for p, value in updates.items()}
    for path, raw in encoded.items():
        if (Path(path).is_absolute() or '..' in Path(path).parts or '\\' in path or
                not path.startswith('definition/pages/')):
            raise ValueError('Reader update outside page scope')
    # Validate all new/moved visual rectangles before making an output directory.
    combined = files | encoded
    for path in encoded:
        if not path.endswith('/visual.json'):
            continue
        item = json.loads(combined[path]); pos = item['position']
        page_path = '/'.join(path.split('/')[:3])+'/page.json'
        canvas = json.loads(combined[page_path])
        if (any(type(pos[k]) not in (int, float) or not math.isfinite(pos[k]) for k in ('x', 'y', 'width', 'height')) or
                any(type(canvas[k]) not in (int, float) or not math.isfinite(canvas[k]) or canvas[k] <= 0 for k in ('width', 'height')) or
                min(pos['x'], pos['y']) < 0 or min(pos['width'], pos['height']) <= 0 or
                pos['x']+pos['width'] > canvas['width'] or pos['y']+pos['height'] > canvas['height']):
            raise ValueError('Reader visual outside canvas')
        prefix = '/'.join(path.split('/')[:3])+'/visuals/'
        for other, other_raw in combined.items():
            if other == path or not other.startswith(prefix) or not other.endswith('/visual.json'):
                continue
            neighbor = json.loads(other_raw)['position']
            if (pos['x'] < neighbor['x']+neighbor['width'] and neighbor['x'] < pos['x']+pos['width'] and
                    pos['y'] < neighbor['y']+neighbor['height'] and neighbor['y'] < pos['y']+pos['height']):
                raise ValueError('Reader visual overlaps neighbor')
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in combined.items():
        path = output/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    receipt = {'status': status, 'native_writes': 0, 'model_changed': False,
               'source_sha256': digest(files), 'frozen_model_sha256': contract['sha256'],
               'input': {p: hashlib.sha256(raw).hexdigest() for p, raw in sorted(files.items())},
               'output': {p: hashlib.sha256(raw).hexdigest() for p, raw in sorted(combined.items())},
               'changed_existing': sorted(p for p in encoded if p in files and encoded[p] != files[p]),
               'new_parts': sorted(set(encoded)-set(files)), 'unavailable_dependencies': list(missing),
               'open_gates': ['Exact-version native import compatibility and bounded recovery',
                              'Fresh sole-writer/preimage and native save/readback',
                              'Rendered keyboard/filter/detail/blank/long-label/contrast acceptance']}
    with manifest.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(receipt, indent=2)+'\n')
    return receipt
