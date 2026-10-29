"""Freeze retained source bytes and exact existing archive bindings, offline only.

Creates an immutable staging plan, never a native completion marker or consumer
admission. Preserves original member names, observation evidence and file grains.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import stat
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

from scripts.source_capture_receipt import create_output, json_bytes

MAX_MEMBER_BYTES = 100_000_000
MAX_ARCHIVE_BYTES = 256_000_000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def archive_binding(document):
    """Resolve only literal archive roots already present in the frozen graph."""
    props = document['properties']
    references = props['connectionReferences']
    if 'shared_sharepointonline' not in references:
        raise ValueError('Existing SharePoint reference required')
    sites, roots, hosts = set(), set(), []
    def visit(node):
        if isinstance(node, dict):
            inputs = node.get('inputs')
            if node.get('type') == 'OpenApiConnection' and isinstance(inputs, dict):
                host = inputs.get('host', {})
                if host.get('apiId', '').endswith('/shared_sharepointonline'):
                    site = inputs.get('parameters', {}).get('dataset')
                    if site is not None:
                        sites.add(site)
                    hosts.append(host)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
        elif isinstance(node, str):
            # Do not evaluate workflow expressions or invent another destination.
            roots.update(re.findall(r"(/Documents/[^'\"\r\n]*?/01 Source archive)(?=[/'\"]|$)", node))
    visit(props['definition'])
    if len(sites) != 1 or len(roots) != 1 or not hosts:
        raise ValueError('One exact existing SharePoint site/archive root required')
    site, root = next(iter(sites)), next(iter(roots))
    u = urlsplit(site)
    if (u.scheme != 'https' or not u.hostname or not u.hostname.endswith('.sharepoint.com')
            or u.username or u.password or u.port or u.query or u.fragment
            or any(c in root for c in "?#%\\") or any(p in ('', '.', '..') for p in root.split('/')[1:])):
        raise ValueError('Unsafe archive destination')
    for host in hosts:
        if host.get('connectionName') != 'shared_sharepointonline' or 'connection' in host:
            raise ValueError('Unqualified SharePoint host format')
    return {'site': site, 'archive_parent': root,
            'connection_reference': references['shared_sharepointonline'],
            'definition_sha256': sha(json_bytes(document)), 'historical_binding_only': True}


def inspect_archive(archive, receipt):
    """Validate the pinned container plus each independently inventoried asset."""
    raw = Path(archive).read_bytes()
    if sha(raw) != receipt.get('package_sha256'):
        raise ValueError('Retained archive hash differs')
    if receipt.get('raw_asset_preparation_ready') is not True:
        raise ValueError('Complete retained asset receipt required')
    expected = receipt.get('inventory', receipt.get('assets'))
    if not isinstance(expected, list) or not expected:
        raise ValueError('Independent raw asset inventory required')
    pins = {}
    for entry in expected:
        name = entry['name']
        if name in pins:
            raise ValueError('Duplicate pinned asset')
        pins[name] = entry
    files = {}
    total = 0
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            name = member.filename
            if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_. -]{0,200}', name)
                    or name in ('.', '..') or name in files or member.is_dir()
                    or stat.S_ISLNK(member.external_attr >> 16)
                    or member.file_size > MAX_MEMBER_BYTES):
                raise ValueError('Unsafe, duplicate or excessive archive member')
            total += member.file_size
            if total > MAX_ARCHIVE_BYTES:
                raise ValueError('Archive expanded byte cap exceeded')
            content = bundle.read(member)
            if name in pins and (sha(content) != pins[name]['sha256'] or len(content) != pins[name]['bytes']):
                raise ValueError('Original raw asset fingerprint differs')
            files[name] = content
    if not set(pins) <= set(files):
        raise ValueError('Retained archive missing an original asset')
    if not files:
        raise ValueError('Empty archive')
    return files


def prepare(archive, receipt, document, output):
    source = receipt.get('source')
    if source not in ('nhmrc', 'mrff', 'ror'):
        raise ValueError('Selected retained workbook/release source required')
    binding = archive_binding(document)
    files = inspect_archive(archive, receipt)
    # Content-addressed generation; existing native source pointers stay unchanged.
    generation = source + '-offline-' + receipt['package_sha256'][:24]
    inventory = [{'name': name, 'bytes': len(raw), 'sha256': sha(raw),
                  'file_grain': ('original_workbook_all_sheets' if name.endswith('.xlsx') else
                                 'complete_release_archive' if name.endswith('.zip') else 'original_provenance')}
                 for name, raw in sorted(files.items())]
    plan = {'kind': 'retained_source_archive_staging_v1', 'source': source,
            'generation': generation, 'binding': binding,
            'destination_folder': binding['archive_parent'] + '/' + generation,
            'original_receipt': receipt, 'files': inventory,
            'source_observation_changed': False, 'provider_calls': 0, 'native_calls': 0,
            'write_policy': 'server_create_only_then_exact_byte_readback; reconcile_uncertain_write_without_repost',
            'completion_marker_emitted': False, 'consumer_pointer_changed': False,
            'offline_staging_ready': True, 'deployment_ready': False,
            'remaining': ['Exact-target operation qualification and storage readback',
                          'Consumer generation mapping and parity; never infer admission from raw retention']}
    out = create_output(output)
    rawdir = out / 'raw'; rawdir.mkdir(mode=0o700)
    for name, raw in files.items():
        with (rawdir / name).open('xb') as stream:
            stream.write(raw)
        if (rawdir / name).read_bytes() != raw:
            raise OSError('Staged raw bytes differ')
    for name, value in [('collector-preimage.json', document), ('staging-plan.json', plan)]:
        with (out / name).open('xb') as stream:
            stream.write(json_bytes(value))
    return plan


def bind_workbook_consumer(staged, packet, consumer):
    """Bind an unchanged saved consumer packet to one independently staged original.

    This proves byte/sheet/reference compatibility only. It does not run Excel,
    validate the registry projection or promote a historical ready pointer.
    """
    staged = Path(staged)
    plan = json.loads((staged / 'staging-plan.json').read_bytes())
    source = plan['source']
    if source not in ('nhmrc', 'mrff') or packet.get('format') != f'rims-{source}-workbook-verified-v1':
        raise ValueError('Matching existing workbook consumer packet required')
    binding = archive_binding(consumer)
    if any(binding[k] != plan['binding'][k] for k in ('site', 'archive_parent', 'connection_reference')):
        raise ValueError('Consumer archive/reference differs from collector')
    original = base64.b64decode(packet['workbook_base64'], validate=True)
    if sha(original) != packet['workbook_sha256']:
        raise ValueError('Consumer embedded workbook hash differs')
    matches = [e for e in plan['files'] if e['sha256'] == sha(original) and e['name'].endswith('.xlsx')]
    if len(matches) != 1 or (staged / 'raw' / matches[0]['name']).read_bytes() != original:
        raise ValueError('Consumer workbook is not an exact retained original')
    manifest = json.loads(base64.b64decode(packet['manifest_base64'], validate=True))
    if (manifest.get('complete') is not True or manifest.get('source') != source
            or manifest.get('archive_folder') != packet['archive_folder']
            or not packet['archive_folder'].startswith(binding['archive_parent'] + f'/{source}-workbooks-')
            or '..' in packet['archive_folder']):
        raise ValueError('Consumer manifest generation differs')
    entries = [e for e in manifest['files'] if e['name'] == packet['workbook_name']]
    if (len(entries) != 1 or entries[0].get('saved_readback_equal') is not True
            or entries[0].get('stored_bytes') != len(original)
            or entries[0].get('source_url') != packet['source_url']):
        raise ValueError('Consumer selected-file provenance differs')
    from scripts.grants_nhmrc_download import _workbook_inventory
    sheets = _workbook_inventory(original)
    if packet['sheet'] not in [sheet['sheet'] for sheet in sheets]:
        raise ValueError('Consumer selected sheet absent from retained workbook')
    if type(packet.get('count')) is not int or packet['count'] < 0:
        raise ValueError('Exact consumer row count required')
    return {'kind': 'retained_workbook_consumer_binding_v1', 'source': source,
            'consumer_sha256': sha(json_bytes(consumer)), 'packet_sha256': sha(json_bytes(packet)),
            'native_selected_filename': packet['workbook_name'], 'local_original': matches[0],
            'sheet': packet['sheet'], 'rows': packet['count'], 'all_sheets_retained': sheets,
            'existing_pointer_preserved': True, 'offline_input_binding_verified': True,
            'native_calls': 0, 'native_runtime_verified': False,
            'remaining': 'Existing Excel processing and registry output parity remain separate native gates'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'receipt', 'collector', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.archive, json.loads(args.receipt.read_bytes()),
                     json.loads(args.collector.read_bytes()), args.output)
    print(json.dumps({'source': result['source'], 'files': len(result['files']),
                      'offline_staging_ready': True, 'deployment_ready': False, 'native_calls': 0}))


if __name__ == '__main__':
    main()
