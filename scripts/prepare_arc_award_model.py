"""Prepare one additive ARC award table; no native writes or opportunity admission."""
from __future__ import annotations
import argparse
import base64
import copy
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, unquote
import uuid

# SPDX-License-Identifier: Apache-2.0
if __package__:
    from scripts.reconcile_arc_awards_snapshots import fingerprint, preimage, write_new, strict_json_loads, _load_snapshot
else:
    from reconcile_arc_awards_snapshots import fingerprint, preimage, write_new, strict_json_loads, _load_snapshot

ROOT = Path(__file__).resolve().parents[1]
NAME = 'ARCAwardContext'
FIELDS = ('RecordKind', 'Source', 'SourceID', 'AwardCode', 'Title', 'Funder', 'URL',
          'Description', 'Amount', 'Status', 'RetrievedUTC', 'EvidenceHash')


def quote(value):
    if not isinstance(value, str) or any(c in value for c in '\r\n\x00'):
        raise ValueError('Single-line M text required')
    return '"' + value.replace('#', '#(#)').replace('"', '""') + '"'


def prepare(definition, *, site, folder, export_run, source_run, rows,
            expected_sha256, expected_parts, archive_receipt, archive_sha256, snapshot_path, snapshot_sha256):
    preimage(definition, expected_sha256, expected_parts)
    if (fingerprint(archive_receipt) != archive_sha256 or archive_receipt.get('complete') is not True
            or archive_receipt.get('next_links') != [] or archive_receipt.get('site') != site
            or archive_receipt.get('folder') != folder or archive_receipt.get('export_run') != export_run
            or archive_receipt.get('source_run') != source_run or type(archive_receipt.get('rows')) is not int
            or archive_receipt['rows'] != rows or archive_receipt.get('fields') != list(FIELDS)
            or archive_receipt.get('record_kind') != 'awards_only'
            or not isinstance(archive_receipt.get('manifest_sha256'),str)
            or not re.fullmatch('[0-9a-f]{64}',archive_receipt['manifest_sha256'])):
        raise ValueError('Complete pinned exact archive receipt required')
    snapshot, _, _ = _load_snapshot(snapshot_path, snapshot_sha256)
    if (snapshot['source_total'] != rows or archive_receipt.get('snapshot_file_sha256') != snapshot_sha256
            or archive_receipt.get('snapshot_records_sha256') != snapshot['snapshot_hash']
            or any(set(FIELDS) != set(row) for row in snapshot['records'])):
        raise ValueError('Archive receipt must bind the complete exact snapshot and fields')
    for row in snapshot['records']:
        if row['Source'] != 'arc' or row['RecordKind'] != 'Award' or any(
                not isinstance(value,str) for value in (row[f] for f in FIELDS)):
            raise ValueError('Qualified text export required; nulls remain unqualified raw snapshot evidence')
    a, b = urlsplit(site), urlsplit(folder)
    if (a.scheme != 'https' or not a.hostname or not a.hostname.endswith('.sharepoint.com')
            or a.username or a.password or a.query or a.fragment or a.port not in (None,443) or site!=site.strip()
            or b.scheme != a.scheme or b.netloc != a.netloc
            or not b.path.startswith(a.path.rstrip('/') + '/') or not b.path.endswith('/')
            or b.query or b.fragment):
        raise ValueError('Exact existing SharePoint site and child export folder required')
    if type(rows) is not int or rows <= 0 or any(not isinstance(x,str) or not x or x!=x.strip() or any(c in x for c in '\r\n\x00') for x in (export_run,source_run)):
        raise ValueError('Exact accepted run identities and row count required')
    result = copy.deepcopy(definition)
    if not isinstance(result, dict) or result.get('format') != 'TMDL' or not isinstance(result.get('parts'), list):
        raise ValueError('Native TMDL definition required')
    parts = result['parts']
    paths = [p['path'] for p in parts]
    if len(paths) != len(set(paths)):
        raise ValueError('Duplicate model part paths')
    by_path = {p['path']: p for p in parts}
    model_path = 'definition/model.tmdl'
    expression_path = 'definition/expressions.tmdl'
    table_path = f'definition/tables/{NAME}.tmdl'
    if table_path in by_path:
        raise ValueError('Award table already exists; reconcile instead of replacing')
    def read(path):
        p = by_path[path]
        if p.get('payloadType') != 'InlineBase64':
            raise ValueError('Inline native preimage required')
        return base64.b64decode(p['payload'], validate=True).decode('utf-8-sig')
    model, expressions = read(model_path), read(expression_path)
    if NAME in model or 'fnReadArcAwardExport' in expressions:
        raise ValueError('Existing award binding must be reconciled')
    # This is a local source check only. The native owner qualifies connection,
    # isolation, target, refresh and preservation before any supported update.
    if quote(site) not in expressions:
        raise ValueError('Site must already occur in the accepted model preimage')
    reader = (ROOT / 'powerquery/fnReadArcAwardExport.m').read_text()
    expressions += '\nexpression fnReadArcAwardExport =\n' + '\n'.join('\t\t' + line for line in reader.splitlines()) + '\n'
    segments = unquote(b.path[len(a.path.rstrip('/')):]).strip('/').split('/')
    if any(not x or x in {'.', '..'} or '\\' in x for x in segments):
        raise ValueError('Exact child folder navigation segments required')
    source = ('let Root = SharePoint.Contents(' + quote(site) + ', [ApiVersion=15]),\n'
              '    Segments = {' + ', '.join(quote(x) for x in segments) + '},\n'
              '    Folder = List.Accumulate(Segments, Root, (Current, Segment) =>\n'
              '        let Matches = Table.SelectRows(Current, each [Name] = Segment),\n'
              '            Child = if Table.RowCount(Matches) = 1 then Matches{0}[Content] else error "Missing or duplicate ARC export folder"\n'
              '        in if Value.Is(Child, type table) then Child else error "ARC export segment is not a folder"),\n'
              '    Scoped = Table.SelectRows(Folder, each [Folder Path] = ' + quote(folder) + '),\n'
              '    Awards = fnReadArcAwardExport(Table.SelectColumns(Scoped, {"Name", "Content"}), '
              + quote(export_run) + ', ' + quote(source_run) + ', ' + str(rows) + ')\nin Awards')
    table = ['/// Retained ARC awards only; not opportunities, applications or institutional attribution.',
             f'table {NAME}', '\tisHidden', '\tlineageTag: ' + str(uuid.uuid5(uuid.NAMESPACE_URL, 'rims/arc-award-context')), '']
    for field in FIELDS:
        table += [f'\tcolumn {field}', '\t\tdataType: string', '\t\tsummarizeBy: none', f'\t\tsourceColumn: {field}']
        if field == 'URL':
            table += ['\t\tdataCategory: WebUrl']
        table += ['']
    table += [f'\tpartition {NAME} = m', '\t\tmode: import', '\t\tsource =']
    table += ['\t\t\t\t' + line for line in source.splitlines()]
    for path, text in [(model_path, model + '\nref table ' + NAME + '\n'),
                       (expression_path, expressions)]:
        by_path[path]['payload'] = base64.b64encode(text.encode()).decode()
    parts.append({'path': table_path, 'payloadType': 'InlineBase64',
                  'payload': base64.b64encode(('\n'.join(table) + '\n').encode()).decode()})
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['definition', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    for name in ['site', 'folder', 'export-run', 'source-run']:
        p.add_argument('--' + name, required=True)
    p.add_argument('--rows', type=int, required=True)
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--expected-parts', required=True, type=Path)
    p.add_argument('--archive-receipt', required=True, type=Path)
    p.add_argument('--archive-sha256', required=True)
    p.add_argument('--snapshot',type=Path,required=True)
    p.add_argument('--snapshot-sha256',required=True)
    args = p.parse_args()
    if any(not x.resolve().is_relative_to((ROOT / 'private/ops').resolve()) for x in [args.definition, args.output]):
        p.error('Native inputs and prepared output must remain private')
    from_inputs = [args.definition,args.expected_parts,args.archive_receipt,args.snapshot]
    if __package__:
        from scripts.plan_publication_stub_restore import private_output
    else:
        from plan_publication_stub_restore import private_output
    private_output(args.output,from_inputs)
    raw = strict_json_loads(args.definition.read_bytes())
    wrapped = set(raw) == {'definition'}
    result = prepare(raw['definition'] if wrapped else raw, site=args.site, folder=args.folder,
                     export_run=args.export_run, source_run=args.source_run, rows=args.rows,
                     expected_sha256=args.expected_sha256, expected_parts=strict_json_loads(args.expected_parts.read_bytes()),
                     archive_receipt=strict_json_loads(args.archive_receipt.read_bytes()), archive_sha256=args.archive_sha256,
                     snapshot_path=args.snapshot,snapshot_sha256=args.snapshot_sha256)
    write_new(args.output, {'definition': result} if wrapped else result, from_inputs)
    print('Prepared additive retained ARC award table; native refresh and full parity remain required')


if __name__ == '__main__':
    main()
