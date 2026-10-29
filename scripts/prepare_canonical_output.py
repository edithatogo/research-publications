"""Prepare additive canonical exports from frozen flow definitions, offline only.

Uses the existing Power BI query and SharePoint file operations. This prepares
source; it neither qualifies a connection nor deploys, activates or runs a flow.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime
from urllib.parse import urlsplit
from pathlib import Path

try:
    from scripts.export_publication_register import EXPORT_FIELDS, MONTH, PRECISIONS, SOURCE_SETS
except ImportError:
    from export_publication_register import EXPORT_FIELDS, MONTH, PRECISIONS, SOURCE_SETS


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
    probe = f"trim(replace({value},decodeUriComponent('%EF%BB%BF'),''))"
    controls = [f"startsWith({value},decodeUriComponent('{c}'))" for c in ('%09', '%0D', '%0A', '%EF%BB%BF')]
    formulas = [f"startsWith({probe},'{c}')" for c in ('=', '+', '-', '@')]
    return f"@if(or({','.join(controls + formulas)}),concat(decodeUriComponent('%27'),{value}),{value})"


def valid_month(value):
    if not isinstance(value, str) or not MONTH.fullmatch(value):
        return False
    try:
        datetime.strptime(value, '%Y-%m')
        return True
    except ValueError:
        return False


def immutable_file(target, name, filename, content, previous, save_template, read_template):
    """Read first, create atomically only on404, reconcile uncertain create by read.

    An identical replay performs GETs only. Different content is a conflict;
    an explicit new revision is required. Never use CreateFile's overwrite path.
    """
    params = save_template['inputs']['parameters']
    folder = params['folderPath'].rstrip('/')
    site = params['dataset']
    if not isinstance(folder, str) or not folder.startswith('/') or "@" in folder:
        raise ValueError('Literal existing reporting folder required')
    full_folder = urlsplit(site).path.rstrip('/') + folder
    def literal(value):
        return "'" + value.replace("'", "''") + "'"
    path = f"@concat({literal(folder + '/')},{filename})"
    existing = name + '_Existing'
    read = copy.deepcopy(read_template)
    read.pop('metadata', None)
    read['runAfter'] = {previous: ['Succeeded']}
    read['inputs']['parameters']['path'] = path
    read['inputs']['retryPolicy'] = {'type': 'none'}
    target[existing] = read
    exact = lambda read_name: f"equals(body('{read_name}')?['$content'],base64({content}))"
    create = name + '_Create'
    reread = name + '_Readback'
    create_action = copy.deepcopy(save_template)
    create_action.pop('metadata', None)
    create_action['runAfter'] = {name + '_Require404': ['Succeeded']}
    create_action['inputs']['host']['operationId'] = 'HttpRequest'
    # Server-side overwrite=false retains concurrent/human writes.
    prefix = "_api/web/GetFolderByServerRelativePath(decodedUrl='" + full_folder.replace("'", "''") + "')/Files/Add(url='"
    uri = f"@concat({literal(prefix)},{filename},{literal("',overwrite=false)")})"
    create_action['inputs']['parameters'] = {'dataset': site, 'parameters/method': 'POST',
        'parameters/uri': uri, 'parameters/headers': {'Accept': 'application/json;odata=nometadata',
        'Content-Type': 'text/plain; charset=utf-8'}, 'parameters/body': '@' + content}
    create_action['inputs']['retryPolicy'] = {'type': 'none'}
    after_read = copy.deepcopy(read)
    after_read['runAfter'] = {create: ['Succeeded', 'Failed', 'TimedOut']}
    # A failed/uncertain POST never causes another POST. Exact stored bytes are
    # sufficient to reconcile success; absent/different bytes fail the run.
    target[name] = {'type': 'If', 'expression': f"@equals(actions('{existing}')?['status'],'Succeeded')",
        'runAfter': {existing: ['Succeeded', 'Failed', 'TimedOut']},
        'actions': {name + '_Unchanged': gate(exact(existing), existing, 'CANONICAL_EXISTING_CONTENT_CONFLICT')},
        'else': {'actions': {
            name + '_Require404': gate(f"equals(outputs('{existing}')?['statusCode'],404)", existing, 'CANONICAL_READ_NOT_FOUND_REQUIRED'),
            create: create_action, reread: after_read,
            name + '_Verified': gate(exact(reread), reread, 'CANONICAL_FILE_BYTES_MISMATCH')}}}
    # Branch entry actions have no sibling dependency on an outer scope action.
    target[name]['actions'][name + '_Unchanged']['runAfter'] = {}
    target[name]['else']['actions'][name + '_Require404']['runAfter'] = {}
    return name, path


def build(exporter, writer, *, reporting_month=None, period_policy=None, revision="v1"):
    """Explicit period only: no guessed production period or schedule changes."""
    if (reporting_month is not None) == (period_policy is not None):
        raise ValueError('Select one explicit month or unattended period policy')
    if reporting_month is not None and not valid_month(reporting_month):
        raise ValueError('Valid explicit YYYY-MM required')
    if period_policy not in (None, 'previous-completed-month-brisbane'):
        raise ValueError('Unknown unattended period policy')
    if not isinstance(revision, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,32}', revision):
        raise ValueError('Safe explicit output revision required')
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
    month_filter = 'FILTER(Publication,Publication[PublicationMonth]="__RIMS_PERIOD__")'
    queries = {
        'Rows': full_query,
        'Keys': 'EVALUATE SELECTCOLUMNS(Publication,"CanonicalKey",Publication[CanonicalKey]) ORDER BY [CanonicalKey]',
        'Month_keys': f'EVALUATE SELECTCOLUMNS({month_filter},"CanonicalKey",Publication[CanonicalKey]) ORDER BY [CanonicalKey]',
        'Counts': f'EVALUATE ROW("FullCount",COALESCE(COUNTROWS(Publication),0),"MonthCount",COALESCE(COUNTROWS({month_filter}),0))',
    }
    target['Canonical_Period'] = compose(reporting_month if reporting_month is not None else
        "@subtractFromTime(startOfMonth(convertTimeZone(utcNow(),'UTC','E. Australia Standard Time')),1,'Month','yyyy-MM')", 'Printable_Verify_manifest')
    previous = 'Canonical_Period'
    for label, query in queries.items():
        name = 'Canonical_Query_' + label
        action = copy.deepcopy(query_template)
        action.pop('metadata', None)
        action['runAfter'] = {previous: ['Succeeded']}
        action['inputs']['parameters']['specification/query'] = (
            "@replace('" + query.replace("'", "''") + "','__RIMS_PERIOD__',outputs('Canonical_Period'))"
            if '__RIMS_PERIOD__' in query else query)
        action['inputs']['parameters']['specification/serializerSettings/includeNulls'] = True
        action['inputs']['retryPolicy'] = {'type': 'none'}
        target[name] = action
        check = 'Canonical_Check_' + label
        result = f"first(body('{name}')?['results'])"
        table = f"first({result}?['tables'])"
        target[check] = gate(
            f"and(empty(body('{name}')?['error']),empty(body('{name}')?['errors']),"
            f"equals(coalesce(body('{name}')?['truncated'],false),false),"
            f"equals(coalesce(body('{name}')?['partial'],false),false),"
            f"equals(length(body('{name}')?['results']),1),"
            f"empty({result}?['error']),empty({result}?['errors']),"
            f"equals(coalesce({result}?['truncated'],false),false),"
            f"equals(coalesce({result}?['partial'],false),false),"
            f"equals(length({result}?['tables']),1),"
            f"empty({table}?['error']),empty({table}?['errors']),"
            f"equals(coalesce({table}?['truncated'],false),false),"
            f"equals(coalesce({table}?['partial'],false),false),"
            f"contains(body('{name}'),'firstTableRows'),"
            f"equals(body('{name}')?['firstTableRows'],{table}?['rows']))",
            name, 'CANONICAL_QUERY_ERROR')
        rows = 'Canonical_Raw_' + label
        target[rows] = compose(f"@body('{name}')?['firstTableRows']", check)
        previous = rows
    schema = {'type': 'array', 'items': {'type': 'object',
        'required': ['[' + f + ']' for f in EXPORT_FIELDS],
        'additionalProperties': False,
        'properties': {'[' + f + ']': {'type': ['string', 'null'] if f != 'PublicationYear'
                                     else ['string', 'integer', 'null']} for f in EXPORT_FIELDS}}}
    properties = schema['items']['properties']
    properties['[CanonicalKey]'] = {'type': 'string', 'minLength': 1,
        'pattern': r'^(?!\s)(?!.*\s$)[^\u0000-\u001f\u007f-\u009f\u200b-\u200f\u2028-\u202e\u2060-\u206f\ufeff]+$'}
    properties['[Title]'] = {'type': 'string', 'pattern': r'\S'}
    properties['[SourceSet]'] = {'type': 'string', 'enum': sorted(SOURCE_SETS)}
    properties['[PublicationDatePrecision]'] = {'type': 'string', 'enum': sorted(PRECISIONS)}
    properties['[PublicationMonth]'] = {'type': ['string', 'null'],
        'pattern': r'^(?:|(?!0000)[0-9]{4}-(?:0[1-9]|1[0-2]))$'}
    target['Canonical_Parse_rows'] = {'type': 'ParseJson',
        'inputs': {'content': "@outputs('Canonical_Raw_Rows')", 'schema': schema},
        'runAfter': {previous: ['Succeeded']}}
    target['Canonical_Rows'] = {'type': 'Select', 'inputs': {
        'from': "@body('Canonical_Parse_rows')",
        'select': {f: f"@item()?['[{f}]']" for f in EXPORT_FIELDS}},
        'runAfter': {'Canonical_Parse_rows': ['Succeeded']}}
    # Apply the established export invariants before a date can enter a month.
    month = "string(coalesce(item()?['PublicationMonth'],''))"
    precision = "item()?['PublicationDatePrecision']"
    invalid = (
        "or(not(equals(trim(item()?['CanonicalKey']),item()?['CanonicalKey'])),"
        "empty(trim(item()?['Title'])),startsWith(item()?['CanonicalKey'],'TEST:'),"
        "startsWith(item()?['Title'],'[SYNTHETIC]'),"
        f"if(empty({month}),contains(createArray('day','month'),{precision}),"
        f"or(contains(createArray('year','range','unknown','rss_unverified'),{precision}),"
        f"not(equals(string(item()?['PublicationYear']),substring(concat({month},'0000'),0,4))))))")
    target['Canonical_Invalid_rows'] = {'type': 'Query', 'inputs': {
        'from': "@body('Canonical_Rows')", 'where': '@' + invalid},
        'runAfter': {'Canonical_Rows': ['Succeeded']}}
    target['Canonical_Verify_row_invariants'] = gate("empty(body('Canonical_Invalid_rows'))",
        'Canonical_Invalid_rows', 'CANONICAL_SOURCE_ROW_INVALID')
    target['Canonical_Month'] = {'type': 'Query', 'inputs': {
        'from': "@body('Canonical_Rows')", 'where': "@equals(item()?['PublicationMonth'],outputs('Canonical_Period'))"},
        'runAfter': {'Canonical_Verify_row_invariants': ['Succeeded']}}
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
        raw_csv = csv_name
        csv_name += '_complete'
        header = ','.join(EXPORT_FIELDS)
        target[csv_name] = compose(f"@if(empty(body('{source}')),concat('{header}',decodeUriComponent('%0D%0A')),body('{raw_csv}'))", raw_csv)
        rows_name = 'Canonical_' + label + '_HTML_rows'
        pieces = []
        for field in EXPORT_FIELDS:
            pieces += ["'<dt>" + field + "</dt><dd data-field=\"" + field + "\">'",
                       "replace(" + html(field) + ",decodeUriComponent('%0D'),'&#13;')", "'</dd>'"]
        target[rows_name] = {'type': 'Select', 'inputs': {'from': f"@body('{source}')",
            'select': "@concat('<article><dl>'," + ','.join(pieces) + ",'</dl></article>')"},
            'runAfter': {csv_name: ['Succeeded']}}
        html_name = 'Canonical_' + label + '_HTML'
        heading = 'All observed publications' if label == 'Full' else 'Monthly publications'
        prefix = '<!doctype html><html lang="en-AU"><meta charset="utf-8"><title>' + heading + '</title><style>body{font:16px Georgia;max-width:960px;margin:2rem auto}dd{white-space:pre-wrap;overflow-wrap:anywhere}article{border-top:1px solid;padding:1rem 0}</style><body><h1>' + heading + '</h1><p>Reporting month: '
        target[html_name] = compose(f"@concat('{prefix}',outputs('Canonical_Period'),'</p>',join(body('{rows_name}'),''),'</body></html>')", rows_name)
        previous = html_name
        for extension, content in [('csv', csv_name), ('html', html_name)]:
            name = 'Canonical_Store_' + label + '_' + extension
            filename = f"concat('canonical-',outputs('Canonical_Period'),'-{revision}-{label.lower()}.{extension}')"
            expression = f"outputs('{content}')"
            previous, path = immutable_file(target, name, filename, expression, previous, save_template, read_template)
            verified.append(path)
    target['Canonical_Manifest'] = compose({'kind': 'rims_canonical_outputs_v1',
        'reporting_month': "@outputs('Canonical_Period')", 'revision': revision,
        'source_model': {k: query_template['inputs']['parameters'][k] for k in ('groupid', 'datasetid')},
        'query_contract_sha256': hashlib.sha256(json.dumps(queries, sort_keys=True).encode()).hexdigest(),
        'full_count': "@length(body('Canonical_Rows'))", 'month_count': "@length(body('Canonical_Month'))",
        'keys': "@body('Canonical_Full_keys')", 'month_keys': "@body('Canonical_Month_keys')",
        'readback_verified': True, 'csv_encoding': 'Formula-like and leading control text has one protective apostrophe.',
        'replay_policy': 'Identical period/revision outputs are read-only replays; changed or edited content requires a new explicit revision.',
        'verified_files': verified}, previous)
    filename = f"concat('canonical-',outputs('Canonical_Period'),'-{revision}-complete.json')"
    immutable_file(target, 'Canonical_Store_manifest', filename,
                   "string(outputs('Canonical_Manifest'))", 'Canonical_Manifest', save_template, read_template)

    return candidate


def deployment_plan(exporter, candidate):
    """Pin an additive source delta. This is not a native permission/read receipt."""
    original = unpack(exporter)
    old = original['properties']
    new = candidate['properties']
    reconstructed = copy.deepcopy(candidate)
    reconstruct = reconstructed['properties']
    new_actions = reconstruct['definition']['actions']['Export_Run']['actions']
    added = [k for k in new_actions if k.startswith('Canonical_')]
    if not added:
        raise ValueError('No canonical addition')
    for key in added:
        del new_actions[key]
    old_refs, new_refs = old['connectionReferences'], new['connectionReferences']
    added_refs = sorted(set(new_refs) - set(old_refs))
    if added_refs not in ([], ['shared_powerbi']):
        raise ValueError('Unexpected added connection')
    for key in added_refs:
        del reconstruct['connectionReferences'][key]
    if reconstructed != original:
        raise ValueError('Existing wrapper, action, connection or schedule was changed')
    canonical = lambda obj: json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    raw = exporter.get('clientdata')
    return {'kind': 'canonical_output_additive_deployment_plan',
        'workflowid': exporter.get('workflowid'),
        'expected_clientdata_sha256': hashlib.sha256(raw.encode() if isinstance(raw, str) else canonical(original)).hexdigest(),
        'candidate_normalized_sha256': hashlib.sha256(canonical(candidate)).hexdigest(),
        'added_connection_names': added_refs,
        'connection_reference_sha256': hashlib.sha256(canonical(new_refs)).hexdigest(),
        'added_actions': added, 'required_target_statecode': 0,
        'requires_complete_inactive_run_history': True, 'requires_no_unowned_draft': True,
        'native_preflight_performed': False, 'native_calls': 0,
        'rollback': 'Exact original clientdata; retain target identity, references and original activation state.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exporter', type=Path, required=True)
    parser.add_argument('--writer', type=Path, required=True)
    period = parser.add_mutually_exclusive_group(required=True)
    period.add_argument('--reporting-month')
    period.add_argument('--period-policy', choices=['previous-completed-month-brisbane'])
    parser.add_argument('--revision', default='v1')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    before = args.exporter.read_bytes()
    candidate = build(json.loads(before), json.loads(args.writer.read_bytes()), reporting_month=args.reporting_month, period_policy=args.period_policy, revision=args.revision)
    # Exclusive creation prevents accidental replacement of a reviewed package.
    with args.output.open('x') as handle:
        json.dump({'candidate': candidate, 'plan': deployment_plan(json.loads(before), candidate), 'rollback_clientdata': json.loads(before).get('clientdata', unpack(json.loads(before))), 'exporter_snapshot_sha256': hashlib.sha256(before).hexdigest(),
            'native_calls': 0, 'deployment_ready': False,
            'remaining': ['Fresh stopped target and additive connection qualification',
                          'Native definition and runtime verification deferred']}, handle, indent=2)
        handle.write('\n')


if __name__ == '__main__':
    main()
