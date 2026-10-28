# SPDX-License-Identifier: Apache-2.0
"""Compare a rebuilt admission candidate with supplied registry/model/export captures.

Transport-free, candidate-only. Neither a supplied mapping nor matching captures
prove native provenance, saved admission, refresh, rendering or scheduled output.
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import prepare_publication_admission_packet as admission
from scripts import prepare_publication_registry_bootstrap as core
from scripts.export_publication_register import (
    EXPORT_FIELDS, MONTH, assemble_paginated_export, export_errors, key_hash,
)
from scripts.reconcile_full_month_exports import reconcile as reconcile_exports

ROOT = Path(__file__).resolve().parents[1]
ROLES = frozenset({'registry', 'model', 'full', 'monthly'})
CONTEXT = frozenset({'generation_id', 'source_snapshot_id', 'query_version',
    'model_refresh_correlation', 'extraction_contract_sha256', 'data_kind',
    'target', 'source_generations', 'admission_packet_sha256', 'registry_preimage_sha256'})
LOGICAL = {**admission.MAPPING, 'CHHHSAffiliatedAuthors': 'field_15'}
FILTERS = dict(model='all_registry_rows', placeholders='exclude_from_exports',
               excluded_statuses=['Excluded'], canonical_multiplicity='reject')
REQUIRED_EXPORT = frozenset({'CanonicalKey', 'Authors', 'Journal', 'PublicationDateRaw',
    'PublicationDatePrecision', 'PublicationYear', 'PublicationMonth', 'PMID',
    'CHHHSAffiliatedAuthors'})
FLAGS = {**core.FLAGS, 'NativeAcceptance': False, 'candidate_only': True,
         'native_invoked': False, 'writer_ready': False}


def exact(value, keys, label):
    admission.exact_keys(value, keys, label)


def equal(actual, expected, label):
    if not core.same(actual, expected):
        raise ValueError(label + ' differs')


def check_contract(contract, packet, snapshot):
    """Validate an explicit mapping against supplied field identities and meanings."""
    exact(contract, ('kind', 'version', 'reference', 'target', 'generations',
        'packet_sha256', 'registry_sha256', 'context', 'reporting_month',
        'registry_fields', 'export_fields', 'filters'), 'consumer contract')
    if contract['kind'] != 'publication_consumer_contract_v1':
        raise ValueError('Versioned consumer contract required')
    for name in ('version', 'reference'):
        core.identifier(contract[name], name)
    equal(contract['target'], packet['target'], 'Consumer target')
    equal(contract['generations'], packet['generations'], 'Source generations')
    equal(contract['packet_sha256'], packet['packet_sha256'], 'Admission packet binding')
    equal(contract['registry_sha256'], core.sha(snapshot), 'Registry preimage binding')
    equal(contract['filters'], FILTERS, 'Supported explicit filter contract')
    context = contract['context']
    exact(context, CONTEXT, 'consumer correlation context')
    for name in ('generation_id', 'source_snapshot_id', 'query_version', 'model_refresh_correlation'):
        core.identifier(context[name], name)
    for key, expected in (('target', packet['target']),
            ('source_generations', packet['generations']),
            ('admission_packet_sha256', packet['packet_sha256']),
            ('registry_preimage_sha256', core.sha(snapshot))):
        equal(context[key], expected, 'Capture source/target binding ' + key)
    admission.fingerprint(context['extraction_contract_sha256'], 'extraction contract')
    if context['data_kind'] not in {'synthetic', 'live_export'}:
        raise ValueError('Explicit capture data kind required')
    if not isinstance(contract['reporting_month'], str) or not MONTH.fullmatch(contract['reporting_month']):
        raise ValueError('Explicit valid reporting month required')
    fields = contract['registry_fields']
    if (not isinstance(fields, dict) or not set(LOGICAL) <= set(fields)
            or set(fields) - (set(LOGICAL) | set(EXPORT_FIELDS))):
        raise ValueError('Complete supported logical registry mapping required')
    bound_fields = set()
    for logical, binding in fields.items():
        internal = LOGICAL.get(logical, binding.get('internal_name') if isinstance(binding, dict) else None)
        exact(binding, ('internal_name', 'field_id', 'missing_new'), 'field binding')
        field = core.field_named(snapshot, binding['internal_name'])
        if (binding['internal_name'] != internal or binding['field_id'] != field['Id']
                or field['Title'] != logical or binding['missing_new'] not in {'null', 'error'}):
            raise ValueError('Ambiguous field identity, meaning or missing-value policy')
        if internal in bound_fields:
            raise ValueError('Two logical meanings alias one physical field')
        bound_fields.add(internal)
    mappings = contract['export_fields']
    exact(mappings, EXPORT_FIELDS, 'complete export field mapping')
    for name, rule in mappings.items():
        if name == 'Title':
            equal(rule, dict(kind='title', existing='Title', create='SourceFullTitle'),
                  'Human/new full-title policy')
        elif name == 'SourceSet':
            equal(rule, dict(kind='source', labels={'pubmed:': 'PubMed', 'dora:': 'DORA'}),
                  'Explicit supported source labels')
        elif name in REQUIRED_EXPORT:
            equal(rule, dict(kind='registry', logical_field=name), 'Required bibliography mapping')
        elif isinstance(rule, dict) and rule.get('kind') == 'registry':
            equal(rule, dict(kind='registry', logical_field=name), 'Additional bibliography mapping')
            if name not in fields:
                raise ValueError('Additional bibliography field lacks exact schema binding')
        else:
            # Missing attribution/identifier authority stays unavailable. No constant
            # funding/identity facts, inferred joins or executable expressions.
            exact(rule, ('kind', 'reason'), 'unavailable export field')
            if rule['kind'] != 'null':
                raise ValueError('Unsupported export derivation; exact source authority required')
            if name in fields or any(
                    f['Title'] == name and any(item[f['InternalName']] not in (None, '')
                        for item in snapshot['items']) for f in snapshot['fields']):
                raise ValueError('Existing bibliography values cannot be declared unavailable')
            core.identifier(rule['reason'], 'unavailable-field reference')
    return context


def projected_registry(packet, snapshot):
    """Preserve every saved field on every old item; never manufacture native IDs."""
    names = [f['InternalName'] for f in snapshot['fields']]
    rows = {}
    by_source = {}
    for item in snapshot['items']:
        row_id = 'item:' + str(item['Id'])
        rows[row_id] = dict(row_id=row_id, origin='existing',
            values={name: copy.deepcopy(item[name]) for name in names})
        key = item['field_1']
        if key not in (None, ''):
            core.identifier(key, 'retained source identity')
            if key in by_source:
                raise ValueError('Duplicate retained SourceKey')
            by_source[key] = row_id
    for proposal in packet['proposals']:
        key = proposal['SourceKey']
        if proposal['kind'] == 'create':
            if key in by_source:
                raise ValueError('Create collides with retained identity')
            row_id = 'new:' + key
            values = {admission.MAPPING[k]: copy.deepcopy(v)
                      for k, v in proposal['proposed_values'].items()}
            rows[row_id] = dict(row_id=row_id, origin='create', values=values)
            by_source[key] = row_id
        else:
            row_id = by_source.get(key)
            if row_id != 'item:' + str(proposal['native_item_id']):
                raise ValueError('Observation target differs from retained item')
            changes = proposal['proposed_observation']
            if set(changes) - {'LastObservedUTC'}:
                raise ValueError('Only explicit LastObservedUTC change permitted')
            rows[row_id]['values'].update({admission.MAPPING[k]: copy.deepcopy(v)
                                         for k, v in changes.items()})
    return sorted(rows.values(), key=lambda r: r['row_id'])


def projected_consumers(registry, contract):
    model, bibliography, keyed, excluded = [], [], [], []
    canonicals = set()
    for row in registry:
        values = {}
        for logical, binding in contract['registry_fields'].items():
            internal = binding['internal_name']
            if internal not in row['values'] and binding['missing_new'] != 'null':
                raise ValueError('Required new-row value unavailable: ' + logical)
            values[logical] = copy.deepcopy(row['values'].get(internal))
        model.append(dict(row_id=row['row_id'], values=values))
        key, canonical = values['SourceKey'], values['CanonicalKey']
        if key in (None, ''):
            if canonical not in (None, ''):
                raise ValueError('Unkeyed row has an ambiguous canonical identity')
            continue
        core.identifier(key, 'SourceKey')
        if not isinstance(canonical, str) or not canonical.strip() or canonical != canonical.strip():
            raise ValueError('Keyed row requires a canonical identity')
        if canonical.casefold() in canonicals:
            raise ValueError('Canonical multiplicity requires a separate qualified alias contract')
        canonicals.add(canonical.casefold());keyed.append(key)
        if values['ReviewStatus'] == 'Excluded':
            excluded.append(key)
            continue
        if values['ReviewStatus'] not in {'Included', 'Needs Review'}:
            raise ValueError('Unqualified publication disposition')
        item = {}
        for name, rule in contract['export_fields'].items():
            if rule['kind'] == 'registry':
                item[name] = copy.deepcopy(values[rule['logical_field']])
            elif rule['kind'] == 'title':
                item[name] = values[rule[row['origin']]]
            elif rule['kind'] == 'source':
                matches = [label for prefix, label in rule['labels'].items() if key.startswith(prefix)]
                if len(matches) != 1:
                    raise ValueError('No qualified source-label binding')
                item[name] = matches[0]
            else:
                item[name] = None
        bibliography.append(item)
    return (sorted(model, key=lambda r: r['row_id']),
            sorted(bibliography, key=lambda r: r['CanonicalKey']), keyed, excluded)


def capture_rows(capture, role, context):
    """A complete normalized field-value capture, including explicit empty terminal."""
    core.complete(capture)
    exact(capture, ('kind', 'complete', 'next_links', 'role', 'context', 'row_count',
                    'rows_sha256', 'pages'), 'normalized consumer capture')
    if capture['kind'] != 'publication_consumer_capture_v1' or capture['role'] != role:
        raise ValueError('Wrong capture role/profile')
    if capture['next_links'] != []:
        raise ValueError('Explicit empty continuation inventory required')
    equal(capture['context'], context, role + ' context')
    pages = capture['pages']
    if not isinstance(pages, list) or not pages:
        raise ValueError('Complete explicit page chain required')
    rows, seen, cursor = [], set(), None
    for number, page in enumerate(pages, 1):
        exact(page, ('number', 'cursor_before', 'cursor_after', 'terminal', 'rows'), 'capture page')
        last = number == len(pages)
        if type(page['number']) is not int or page['number'] != number or page['terminal'] is not last:
            raise ValueError('Page order/terminal differs')
        if page['cursor_before'] != cursor or not isinstance(page['rows'], list):
            raise ValueError('Incomplete cursor chain')
        if last:
            if page['rows'] or page['cursor_after'] != cursor:
                raise ValueError('Explicit empty terminal required')
        else:
            next_cursor = core.identifier(page['cursor_after'], 'next cursor')
            if not page['rows'] or next_cursor in seen:
                raise ValueError('Empty or repeated nonterminal page')
            seen.add(next_cursor)
        rows.extend(page['rows']);cursor = page['cursor_after']
    if type(capture['row_count']) is not int or capture['row_count'] != len(rows):
        raise ValueError('Capture count differs')
    equal(capture['rows_sha256'], core.sha(rows), role + ' row bytes fingerprint')
    row_ids = set()
    for row in rows:
        exact(row, ('row_id', 'origin', 'values') if role == 'registry' else ('row_id', 'values'), 'normalized row')
        row_id = core.identifier(row['row_id'], 'row identity')
        if row_id in row_ids or not isinstance(row['values'], dict):
            raise ValueError('Duplicate row identity or malformed values')
        row_ids.add(row_id)
    return sorted(copy.deepcopy(rows), key=lambda r: r['row_id'])


def prepare(inputs, raw_files, packet, *, input_pins, packet_pin, contract,
            captures, consumer_pins, as_of):
    """Rebuild source admission and compare all supplied candidate consumer layers."""
    exact(captures, ROLES, 'all consumer captures')
    exact(consumer_pins, ROLES | {'contract'}, 'independent consumer pins')
    actual = {'contract': core.sha(contract), **{k: core.sha(v) for k, v in captures.items()}}
    for name, pin in consumer_pins.items():
        admission.fingerprint(pin, name)
        equal(pin, actual[name], 'Independent ' + name + ' pin')
    admission.verify(packet, inputs, raw_files, expected_hashes=input_pins,
                     expected_packet_sha256=packet_pin, as_of=as_of)
    snapshot = core.validate_snapshot(inputs['registry'])
    context = check_contract(contract, packet, snapshot)
    registry = projected_registry(packet, snapshot)
    model, bibliography, keyed, excluded = projected_consumers(registry, contract)
    equal(capture_rows(captures['registry'], 'registry', context), registry, 'Projected registry values')
    equal(capture_rows(captures['model'], 'model', context), model, 'Projected model values')
    assembled = {}
    for role in ('full', 'monthly'):
        envelope = captures[role]
        core.complete(envelope)
        if envelope.get('next_links') != []:
            raise ValueError('Explicit empty export continuation inventory required')
        if not isinstance(envelope.get('pages'), list):
            raise ValueError('Complete export page list required')
        for page in envelope['pages']:
            if not isinstance(page, dict):
                raise ValueError('Export page object required')
            core.complete({'complete': True, **page})
        for name in CONTEXT:
            equal(envelope.get(name), context[name], role + ' ' + name)
        assembled[role] = assemble_paginated_export(envelope)
        errors = export_errors(assembled[role])
        if errors:
            raise ValueError(role + ': ' + '; '.join(errors))
    equal(assembled['full']['scope'], dict(mode='all', reporting_month=None), 'Full scope')
    equal(assembled['monthly']['scope'], dict(mode='month', reporting_month=contract['reporting_month']), 'Month scope')
    equal(sorted(assembled['full']['records'], key=lambda r: r['CanonicalKey']), bibliography,
          'Expected bibliography')
    export_comparison = reconcile_exports(captures['full'], captures['monthly'])
    current = {p['SourceKey'] for p in packet['proposals']}
    counts = dict(registry=len(registry), existing=len(snapshot['items']),
        created=sum(r['origin'] == 'create' for r in registry), model=len(model),
        keyed=len(keyed), placeholders=len(registry)-len(keyed), excluded=len(excluded),
        historical_keyed=len(set(keyed)-current), full=len(bibliography),
        monthly=len(assembled['monthly']['records']),
        unknown_month=sum(r['PublicationMonth'] in (None, '') for r in bibliography))
    result = {**FLAGS, 'kind': 'publication_consumer_parity_receipt_v1',
        'status': 'VERIFIED_SUPPLIED_CANDIDATE_PARITY', 'as_of_utc': as_of,
        'packet_sha256': packet_pin, 'input_sha256': copy.deepcopy(input_pins),
        'consumer_sha256': actual, 'target': copy.deepcopy(packet['target']),
        'generations': copy.deepcopy(packet['generations']), 'context': copy.deepcopy(context),
        'counts': counts, 'expected_registry_sha256': core.sha(registry),
        'expected_model_sha256': core.sha(model), 'expected_full_sha256': core.sha(bibliography),
        'full_key_sha256': key_hash(bibliography), 'export_comparison': export_comparison,
        'limits': 'Supplied candidate projections only; mapping/capture provenance, native admission, '
                  'native generated fields/defaults, refresh, rendering and scheduled output unqualified.'}
    result['receipt_sha256'] = core.sha(result)
    return result


def verify(receipt, *args, receipt_pin, **kwargs):
    admission.fingerprint(receipt_pin, 'independent parity receipt')
    if not isinstance(receipt, dict):
        raise ValueError('Receipt object required')
    equal(receipt.get('receipt_sha256'), receipt_pin, 'Receipt pin')
    equal(core.sha({k: v for k, v in receipt.items() if k != 'receipt_sha256'}), receipt_pin, 'Receipt content')
    equal(receipt, prepare(*args, **kwargs), 'Rebuilt parity receipt')
    return {**FLAGS, 'status': 'VERIFIED_LOCAL_RECEIPT', 'receipt_sha256': receipt_pin}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs', 'files', 'pins', 'packet', 'contract', 'captures', 'consumer-pins', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--packet-sha256', required=True)
    parser.add_argument('--as-of', required=True)
    args = parser.parse_args(argv)
    try:
        docs, hashes = {}, {}
        for name in ('inputs', 'files', 'pins', 'packet', 'contract', 'captures', 'consumer_pins'):
            docs[name], hashes[name] = core.cli_read(getattr(args, name), ROOT)
        envelope = docs['packet']
        if not isinstance(envelope, dict) or envelope.get('kind') != 'publication_admission_local_result_v1':
            raise ValueError('Exact admission local result envelope required')
        if not isinstance(docs['files'], dict):
            raise ValueError('Explicit private raw file map required')
        raw = {}
        for name, path in docs['files'].items():
            if not isinstance(path, str):
                raise ValueError('Explicit private raw path required')
            raw[name] = core.private_path(Path(path), 'raw input', ROOT).read_bytes()
            hashes['raw:' + name] = core.bytes_sha(raw[name])
        result = prepare(docs['inputs'], raw, envelope['result'], input_pins=docs['pins'],
            packet_pin=args.packet_sha256, contract=docs['contract'], captures=docs['captures'],
            consumer_pins=docs['consumer_pins'], as_of=args.as_of)
        core.exclusive_json(core.private_path(args.output, 'output', ROOT, output=True),
            {**FLAGS, 'kind': 'publication_consumer_parity_local_v1', 'result': result,
             'source_files_sha256': hashes})
        return 0
    except (ValueError, OSError, TypeError, KeyError):
        print('Offline consumer parity failed; inputs and prior outputs preserved', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
