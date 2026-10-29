"""Prepare additive canonical exports from frozen flow definitions, offline only.

Uses the existing Power BI query and SharePoint file operations. This prepares
source; it neither qualifies a connection nor deploys, activates or runs a flow.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from scripts.export_publication_register import EXPORT_FIELDS, MONTH


def unpack(record):
    value = record.get('clientdata', record)
    return json.loads(value) if isinstance(value, str) else copy.deepcopy(value)


def find_query(node):
    found = []
    def visit(value):
        if isinstance(value, dict):
            if (value.get('type') == 'OpenApiConnection'
                    and value.get('inputs', {}).get('host', {}).get('operationId') == 'ExecuteDatasetQuery'):
                found.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(node)
    if not found:
        raise ValueError('Existing ExecuteDatasetQuery binding required')
    bindings = [dict(host=v['inputs']['host'], groupid=v['inputs']['parameters']['groupid'],
                     datasetid=v['inputs']['parameters']['datasetid']) for v in found]
    if any(binding != bindings[0] for binding in bindings):
        raise ValueError('Ambiguous existing model bindings')
    return copy.deepcopy(found[0])


def compose(value, previous):
    return {'type': 'Compose', 'inputs': value, 'runAfter': {previous: ['Succeeded']}}


def gate(condition, previous, code):
    return compose(f"@if({condition},true,int('{code}'))", previous)


def text(field):
    return f"string(coalesce(item()?['{field}'],''))"


def html(field):
    value = text(field)
    for old, new in [('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;'), ('"', '&quot;')]:
        value = f"replace({value},'{old}','{new}')"
    return value


def csv_cell(field):
    value = text(field)
    # Prefix every nonempty cell. This reversible CSV convention avoids formula
    # interpretation even with leading Unicode whitespace or control characters.
    return f"@if(empty({value}),'',concat(decodeUriComponent('%27'),{value}))"


def build(exporter, writer, *, reporting_month):
    """Explicit period only: no guessed production period or schedule changes."""
    if not isinstance(reporting_month, str) or not MONTH.fullmatch(reporting_month):
        raise ValueError('Explicit YYYY-MM required; frozen cases are not production defaults')
    original, donor = unpack(exporter), unpack(writer)
    candidate = copy.deepcopy(original)
    props = candidate['properties']
    actions = props['definition']['actions']
    if not {'Export_Run', 'Monitor_Success_receipt', 'Monitor_Retain_failed_status'} <= actions.keys():
        raise ValueError('Existing monitored exporter required')
    target = actions['Export_Run']['actions']
    if any(k.startswith('Canonical_') for k in target):
        raise ValueError('Canonical scope already present; reconcile rather than overwrite')
    if 'Printable_Verify_manifest' not in target:
        raise ValueError('Existing final registry readback required')
    query_template = find_query(donor)
    host = query_template['inputs']['host']
    if host.get('apiId') != '/providers/Microsoft.PowerApps/apis/shared_powerbi':
        raise ValueError('Unexpected query connector')
    ref = host['connectionName']
    donor_refs = donor['properties']['connectionReferences']
    refs = props['connectionReferences']
    if donor_refs.get('shared_sharepointonline') != refs.get('shared_sharepointonline'):
        raise ValueError('Writer and exporter SharePoint bindings differ')
    if ref not in donor_refs or (ref in refs and refs[ref] != donor_refs[ref]):
        raise ValueError('Missing or conflicting pinned Power BI connection')
    refs[ref] = copy.deepcopy(donor_refs[ref])
    save_template = target['Save_Registered_Publications_CSV']
    read_template = target['Printable_Read_manifest']
    if (save_template['inputs']['host']['operationId'] != 'CreateFile'
            or read_template['inputs']['host']['operationId'] != 'GetFileContentByPath'):
        raise ValueError('Existing file operation contracts required')
    full_query = 'EVALUATE SELECTCOLUMNS(Publication,' + ','.join(
        f'"{f}",Publication[{f}]' for f in EXPORT_FIELDS) + ') ORDER BY [CanonicalKey]'
    month_filter = f'FILTER(Publication,Publication[PublicationMonth]="{reporting_month}")'
    queries = {
        'Rows': full_query,
        'Keys': 'EVALUATE SELECTCOLUMNS(Publication,"CanonicalKey",Publication[CanonicalKey]) ORDER BY [CanonicalKey]',
        'Month_keys': f'EVALUATE SELECTCOLUMNS({month_filter},"CanonicalKey",Publication[CanonicalKey]) ORDER BY [CanonicalKey]',
        'Counts': f'EVALUATE ROW("FullCount",COALESCE(COUNTROWS(Publication),0),"MonthCount",COALESCE(COUNTROWS({month_filter}),0))',
    }
    previous = 'Printable_Verify_manifest'
    for label, query in queries.items():
        name = 'Canonical_Query_' + label
        action = copy.deepcopy(query_template)
        action.pop('metadata', None)
        action['runAfter'] = {previous: ['Succeeded']}
        action['inputs']['parameters']['specification/query'] = query
        action['inputs']['parameters']['specification/serializerSettings/includeNulls'] = True
        action['inputs']['retryPolicy'] = {'type': 'none'}
        target[name] = action
        check = 'Canonical_Check_' + label
        target[check] = gate(
            f"and(empty(body('{name}')?['error']),empty(body('{name}')?['errors']),"
            f"equals(coalesce(body('{name}')?['truncated'],false),false),"
            f"equals(coalesce(body('{name}')?['partial'],false),false),"
            f"contains(body('{name}'),'firstTableRows'))", name, 'CANONICAL_QUERY_ERROR')
        rows = 'Canonical_Raw_' + label
        target[rows] = compose(f"@body('{name}')?['firstTableRows']", check)
        previous = rows
    schema = {'type': 'array', 'items': {'type': 'object',
        'required': ['[' + f + ']' for f in EXPORT_FIELDS],
        'additionalProperties': False,
        'properties': {'[' + f + ']': {'type': ['string', 'null'] if f != 'PublicationYear'
                                     else ['string', 'integer', 'null']} for f in EXPORT_FIELDS}}}
    schema['items']['properties']['[CanonicalKey]'] = {'type': 'string', 'minLength': 1}
    target['Canonical_Parse_rows'] = {'type': 'ParseJson',
        'inputs': {'content': "@outputs('Canonical_Raw_Rows')", 'schema': schema},
        'runAfter': {previous: ['Succeeded']}}
    target['Canonical_Rows'] = {'type': 'Select', 'inputs': {
        'from': "@body('Canonical_Parse_rows')",
        'select': {f: f"@item()?['[{f}]']" for f in EXPORT_FIELDS}},
        'runAfter': {'Canonical_Parse_rows': ['Succeeded']}}
    target['Canonical_Month'] = {'type': 'Query', 'inputs': {
        'from': "@body('Canonical_Rows')", 'where': f"@equals(item()?['PublicationMonth'],'{reporting_month}')"},
        'runAfter': {'Canonical_Rows': ['Succeeded']}}
    previous = 'Canonical_Month'
    for label, source in [('Full', 'Canonical_Rows'), ('Month', 'Canonical_Month')]:
        name = 'Canonical_' + label + '_keys'
        target[name] = {'type': 'Select', 'inputs': {'from': f"@body('{source}')",
            'select': {'[CanonicalKey]': "@item()?['CanonicalKey']"}},
            'runAfter': {previous: ['Succeeded']}}
        previous = name
    conditions = ["equals(length(outputs('Canonical_Raw_Counts')),1)"]
    for label, raw in [('Full', 'Keys'), ('Month', 'Month_keys')]:
        keys = f"body('Canonical_{label}_keys')"
        expected = f"outputs('Canonical_Raw_{raw}')"
        conditions += [f"equals({keys},{expected})",
            f"equals(length(union({keys},{keys})),length({keys}))",
            f"equals(length({keys}),first(outputs('Canonical_Raw_Counts'))?['[{label}Count]'])"]
    target['Canonical_Verify_keys'] = gate('and(' + ','.join(conditions) + ')', previous, 'CANONICAL_KEYS_INCOMPLETE')
    previous = 'Canonical_Verify_keys'
    verified = []
    for label, source in [('Full', 'Canonical_Rows'), ('Month', 'Canonical_Month')]:
        safe = 'Canonical_' + label + '_safe_cells'
        target[safe] = {'type': 'Select', 'inputs': {'from': f"@body('{source}')",
            'select': {f: csv_cell(f) for f in EXPORT_FIELDS}}, 'runAfter': {previous: ['Succeeded']}}
        csv_name = 'Canonical_' + label + '_CSV'
        target[csv_name] = {'type': 'Table', 'inputs': {'from': f"@body('{safe}')", 'format': 'CSV',
            'columns': [{'header': f, 'value': f"@item()?['{f}']"} for f in EXPORT_FIELDS]},
            'runAfter': {safe: ['Succeeded']}}
        rows_name = 'Canonical_' + label + '_HTML_rows'
        cells = ",'</td><td>',".join(html(f) for f in EXPORT_FIELDS)
        target[rows_name] = {'type': 'Select', 'inputs': {'from': f"@body('{source}')",
            'select': "@concat('<tr><td>'," + cells + ",'</td></tr>')"},
            'runAfter': {csv_name: ['Succeeded']}}
        html_name = 'Canonical_' + label + '_HTML'
        heading = 'All observed publications' if label == 'Full' else 'Publications: ' + reporting_month
        prefix = '<!doctype html><html><head><meta charset="utf-8"><title>' + heading + '</title></head><body><h1>' + heading + '</h1><table><thead><tr>'
        prefix += ''.join('<th>' + f + '</th>' for f in EXPORT_FIELDS) + '</tr></thead><tbody>'
        target[html_name] = compose(f"@concat('{prefix}',join(body('{rows_name}'),''),'</tbody></table></body></html>')", rows_name)
        previous = html_name
        for extension, content in [('csv', csv_name), ('html', html_name)]:
            name = 'Canonical_Save_' + label + '_' + extension
            action = copy.deepcopy(save_template)
            action['runAfter'] = {previous: ['Succeeded']}
            action['inputs']['parameters']['name'] = f"@concat('canonical-{reporting_month}-{label.lower()}-',workflow()?['run']?['name'],'.{extension}')"
            action['inputs']['parameters']['body'] = f"@{'body' if extension == 'csv' else 'outputs'}('{content}')"
            action['inputs']['retryPolicy'] = {'type': 'none'}
            target[name] = action
            read = name.replace('Save', 'Read')
            target[read] = copy.deepcopy(read_template)
            target[read]['runAfter'] = {name: ['Succeeded']}
            target[read]['inputs']['parameters']['path'] = f"@body('{name}')?['Path']"
            verify = name.replace('Save', 'Verify')
            expr = action['inputs']['parameters']['body'][1:]
            target[verify] = gate(f"equals(body('{read}')?['$content'],base64({expr}))", read, 'CANONICAL_FILE_BYTES_MISMATCH')
            verified.append(verify)
            previous = verify
    target['Canonical_Manifest'] = compose({'kind': 'rims_canonical_outputs_v1',
        'reporting_month': reporting_month, 'run_id': "@workflow()?['run']?['name']",
        'full_count': "@length(body('Canonical_Rows'))", 'month_count': "@length(body('Canonical_Month'))",
        'csv_encoding': 'Each nonempty value has one leading apostrophe; remove exactly one to recover the source value.',
        'replay_policy': 'Immutable per-run outputs; later runs create a new generation. No last-good file is overwritten.',
        'verified_files': [f"@body('{name.replace('Verify', 'Save')}')?['Path']" for name in verified]}, previous)
    target['Canonical_Save_manifest'] = copy.deepcopy(save_template)
    save = target['Canonical_Save_manifest']
    save['runAfter'] = {'Canonical_Manifest': ['Succeeded']}
    save['inputs']['parameters'].update(name="@concat('canonical-',workflow()?['run']?['name'],'-complete.json')", body="@string(outputs('Canonical_Manifest'))")
    save['inputs']['retryPolicy'] = {'type': 'none'}
    target['Canonical_Read_manifest'] = copy.deepcopy(read_template)
    target['Canonical_Read_manifest']['runAfter'] = {'Canonical_Save_manifest': ['Succeeded']}
    target['Canonical_Read_manifest']['inputs']['parameters']['path'] = "@body('Canonical_Save_manifest')?['Path']"
    target['Canonical_Verify_manifest'] = gate("equals(body('Canonical_Read_manifest')?['$content'],base64(string(outputs('Canonical_Manifest'))))", 'Canonical_Read_manifest', 'CANONICAL_MANIFEST_BYTES_MISMATCH')
    return candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exporter', type=Path, required=True)
    parser.add_argument('--writer', type=Path, required=True)
    parser.add_argument('--reporting-month', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    before = args.exporter.read_bytes()
    candidate = build(json.loads(before), json.loads(args.writer.read_bytes()), reporting_month=args.reporting_month)
    # Exclusive creation prevents accidental replacement of a reviewed package.
    with args.output.open('x') as handle:
        json.dump({'candidate': candidate, 'exporter_snapshot_sha256': hashlib.sha256(before).hexdigest(),
            'native_calls': 0, 'deployment_ready': False,
            'remaining': ['Period automation binding', 'CSV parity and replay policy review',
                          'Fresh stopped target and additive connection qualification',
                          'Native definition and runtime verification deferred']}, handle, indent=2)
        handle.write('\n')


if __name__ == '__main__':
    main()
