"""Build a private preservation ledger from current and retained native evidence.

Preservation is a disposition, not deletion or restore authority. This module
performs no network I/O and never creates a mutation or restore payload.
"""
from __future__ import annotations

import argparse

if __package__:
    from scripts.plan_publication_stub_restore import strict_json_loads, same_target, target_qualification
else:
    from plan_publication_stub_restore import strict_json_loads, same_target, target_qualification
import copy
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


# SPDX-License-Identifier: Apache-2.0
if __package__:
    from scripts.plan_publication_stub_restore import count, version_entries, private_output, utc as _utc
else:
    from plan_publication_stub_restore import count, version_entries, private_output, utc as _utc


def visible_inventory(fields, receipt):
    if not isinstance(fields, list) or not fields:
        raise ValueError('Native field inventory required')
    names = [f.get('InternalName') if isinstance(f, dict) else None for f in fields]
    if any(not isinstance(n,str) or not n or n != n.strip() for n in names) or len(names) != len(set(names)):
        raise ValueError('Missing, padded or duplicate native field name')
    if any(type(f.get(k)) is not bool for f in fields for k in ('ReadOnlyField','Hidden')):
        raise ValueError('Explicit native field flags required')
    if any(not isinstance(f.get('TypeAsString'),str) or not f['TypeAsString'] or f['TypeAsString'] != f['TypeAsString'].strip() for f in fields):
        raise ValueError('Explicit native field types required')
    if (not isinstance(receipt,dict) or receipt.get('complete') is not True or receipt.get('next_links') != []
            or not isinstance(receipt.get('source'),str) or not receipt['source'] or receipt['source']!=receipt['source'].strip()
            or count(receipt.get('field_count')) != len(fields) or receipt.get('fields_sha256')!=fingerprint(fields)
            or not isinstance(receipt.get('artifact_sha256'),str) or not re.fullmatch('[0-9a-f]{64}',receipt['artifact_sha256'])):
        raise ValueError('Complete fingerprint-bound native field inventory receipt required')
    return [f['InternalName'] for f in fields if f['ReadOnlyField'] is False and f['Hidden'] is False
            and f['TypeAsString'] not in {'Computed','Attachments'}]


def artifact(directory, name, expected_sha):
    if not isinstance(name,str) or Path(name).is_absolute() or '..' in Path(name).parts or '\\' in name:
        raise ValueError('Unsafe native artifact reference')
    path=directory/name
    if path.is_symlink() or any((directory/p).is_symlink() for p in Path(name).parents if p != Path('.')) or not path.resolve().is_relative_to(directory.resolve()):
        raise ValueError('Native artifact escapes the capture')
    raw=path.read_bytes()
    if not isinstance(expected_sha,str) or not re.fullmatch('[0-9a-f]{64}',expected_sha) or hashlib.sha256(raw).hexdigest()!=expected_sha:
        raise ValueError('Native response bytes changed')
    return raw


def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def index_rows(rows: object, name: str, key: str = 'Id', *, allow_empty=False) -> dict[int, dict]:
    if not isinstance(rows, list) or (not rows and not allow_empty):
        raise ValueError(name + ' must contain a nonempty row array')
    result = {}
    for row in rows:
        ident = row.get(key) if isinstance(row, dict) else None
        if type(ident) is not int or ident <= 0 or ident in result:
            raise ValueError(name + ' has invalid or duplicate item IDs')
        result[ident] = row
    return result


def utc(value: str) -> datetime:
    return _utc(value)


def verify_action_references(correlation: dict, private_root: Path) -> dict:
    """Recheck exact item returns in retained native artifacts, never a cohort."""
    artifacts = {}
    verified = 0
    indexed=index_rows(correlation.get('items'),'action references','id')
    count(correlation.get('candidate_count'),len(indexed),'action candidate count')
    for row in indexed.values():
        if row['grade'] == 'unmatched':
            if row.get('action') is not None: raise ValueError('Unmatched origin cannot carry action evidence')
            continue
        if row['grade'] != 'direct_action_id_match': raise ValueError('Unsupported provenance grade')
        action = row['action']
        path_text, fragment = action['evidence_ref'].split('#', 1)
        path = Path(path_text)
        if path.is_symlink() or not path.resolve().is_relative_to(private_root.resolve()):
            raise ValueError('Native action evidence must remain in the private root')
        match = re.fullmatch(r'items\[([0-9]+)\]', fragment)
        if not match:
            raise ValueError('Exact native action item reference required')
        raw = path.read_bytes()
        capture = strict_json_loads(raw)
        if (capture.get('schema_version') != 'publication-create-repetition-ids/v1'
                or capture.get('read_only') is not True
                or capture.get('complete_repetition_index_set') is not True):
            raise ValueError('Retained native repetition capture is incomplete')
        index = int(match[1])
        items = capture['items']
        iterations=[item.get('iteration_zero_based') for item in items]
        if any(type(i) is not int or i<0 for i in iterations) or sorted(iterations)!=list(range(len(items))):
            raise ValueError('Native repetition index set is incomplete or duplicated')
        if index >= len(items):
            raise ValueError('Native action item reference is out of bounds')
        item = items[index]
        expected_action = ('Apply_to_each_Publication/iteration_' +
                           str(item['iteration_zero_based'] + 1) + '/' + capture['action'])
        if (capture['run_id'] != action['run_id'] or expected_action != action['action_id']
                or item['action_status'] != 'Succeeded' or type(item['response_status']) is not int or item['response_status'] != 201
                or type(item['created_item_id']) is not int or item['created_item_id'] != row['id']):
            raise ValueError('Retained native action does not return the exact candidate ID')
        artifacts[str(path)] = hashlib.sha256(raw).hexdigest()
        verified += 1
    return {'exact_returns_rechecked': verified, 'artifact_sha256': artifacts}


def verify_native_files(cohort: dict, registry: list[dict], directory: Path,
                        fields: list[dict], *, version_field_map: dict, inventory_receipt: dict) -> dict:
    """Bind every inventoried visible value and saved history/attachment byte.

    Version JSON names are supplied explicitly; no underscore/lookup renaming is
    inferred. A writable metadata flag is backup coverage, never write authority.
    """
    rows=index_rows(registry,'registry'); evidence_rows=index_rows(cohort.get('items'),'native cohort')
    count(cohort.get('candidate_count'),len(evidence_rows),'native candidate count')
    if cohort.get('complete') is not True or cohort.get('next_links') != []:
        raise ValueError('Complete native cohort required')
    if set(evidence_rows)-set(rows): raise ValueError('Native item set differs from registry')
    writable=visible_inventory(fields,inventory_receipt)
    if (not writable or not isinstance(version_field_map,dict) or set(version_field_map)!=set(writable)
            or any(not isinstance(v,str) or not v or v!=v.strip() for v in version_field_map.values())
            or len(set(version_field_map.values()))!=len(version_field_map)):
        raise ValueError('Complete unambiguous inventory-bound version field map required')
    comparisons=0; attachments_verified=0
    for ident,evidence in evidence_rows.items():
        row=rows[ident]; pages=evidence.get('version_pages'); versions=[]
        if (evidence.get('version_history_complete') is not True or evidence.get('GUID')!=row.get('GUID')
                or evidence.get('ETag')!=row.get('odata.etag') or evidence.get('version')!=row.get('OData__UIVersionString')):
            raise ValueError('Native identity/version metadata differs from current item')
        if not isinstance(pages,list) or not pages: raise ValueError('Native version page references required')
        if len({p.get('file') for p in pages})!=len(pages): raise ValueError('Duplicate version page reference')
        for index,page in enumerate(pages):
            if not re.fullmatch(r'versions-'+str(ident)+r'-[0-9]+\.json',page['file']):
                raise ValueError('Version filename is not bound to the item')
            capture=strict_json_loads(artifact(directory,page['file'],page['sha256']))
            if 'error' in capture or capture.get('errors') or not isinstance(capture.get('value'),list):
                raise ValueError('Native version response is incomplete')
            if '@odata.nextLink' in capture and 'odata.nextLink' in capture and capture['@odata.nextLink']!=capture['odata.nextLink']:
                raise ValueError('Conflicting native pagination aliases')
            observed=capture.get('@odata.nextLink',capture.get('odata.nextLink'))
            expected=pages[index+1].get('url') if index+1<len(pages) else None
            if observed!=expected or (index+1<len(pages) and not isinstance(expected,str)):
                raise ValueError('Native version pagination chain incomplete')
            versions.extend(capture['value'])
        version_entries(versions); count(evidence.get('version_count'),len(versions),'native version count')
        current=next(v for v in versions if v['IsCurrentVersion'] is True)
        if current.get('VersionLabel')!=row['OData__UIVersionString'] or any(v.get('GUID')!=row['GUID'] for v in versions):
            raise ValueError('Native current version differs from the current item')
        for field,version_name in version_field_map.items():
            if field not in row or version_name not in current or fingerprint(row[field])!=fingerprint(current[version_name]):
                raise ValueError('Native current version values differ from the current item')
            comparisons+=1
        attachments=evidence.get('attachments')
        if evidence.get('attachment_export_complete') is not True or not isinstance(attachments,list):
            raise ValueError('Complete attachment export required')
        if type(row.get('Attachments')) is not bool or row['Attachments']!=bool(attachments):
            raise ValueError('Attachment presence differs from current item')
        names=set()
        for attachment in attachments:
            name=attachment.get('name')
            if not isinstance(name,str) or not name or name!=name.strip() or name in names:
                raise ValueError('Missing or duplicate attachment identity')
            names.add(name)
            artifact(directory,attachment['file'],attachment['sha256']);attachments_verified+=1
    return {'native_history_files_value_bound':len(evidence_rows),'visible_field_value_comparisons':comparisons,
            'inventory_field_count':len(writable),'attachment_files_hash_bound':attachments_verified,
            'version_field_map_sha256':fingerprint(version_field_map)}


def build(registry: list[dict], cohort: dict, original: dict, correlation: dict,
          shapes: dict, fields: list[dict], context: dict) -> dict:
    registry,cohort,original,correlation,shapes,fields,context=copy.deepcopy((registry,cohort,original,correlation,shapes,fields,context))
    all_rows = index_rows(registry, 'registry')
    if any('field_1' not in row or (row['field_1'] not in (None,'') and
           (not isinstance(row['field_1'],str) or row['field_1']!=row['field_1'].strip())) for row in all_rows.values()):
        raise ValueError('Missing, padded or non-text source identity')
    current = {key: row for key, row in all_rows.items() if row.get('field_1') in (None, '')}
    historical = index_rows(original.get('items'), 'original cohort', 'id')
    native = index_rows(cohort.get('items'), 'current native cohort')
    actions = index_rows(correlation.get('items'), 'action correlation', 'id')
    ids = set(current)
    if not ids or any(set(value) != ids for value in (historical, native, actions)):
        raise ValueError('Current, historical, native and action candidate sets differ')
    for source in (cohort, original, correlation):
        if type(source.get('candidate_count')) is not int or source['candidate_count'] != len(ids):
            raise ValueError('Candidate count is not exact')
    if (cohort.get('complete') is not True or cohort.get('next_links') != []
            or cohort.get('registry_metadata_stable') is not True
            or type(cohort.get('native_writes')) is not int or cohort['native_writes'] != 0):
        raise ValueError('Complete stable current native evidence required')
    if (correlation.get('schema_version') != 'publication-stub-action-correlation/v1'
            or correlation.get('read_only') is not True
            or correlation.get('candidate_snapshot_sha256') != fingerprint(original)):
        raise ValueError('Action correlation does not bind the original cohort')
    if (context.get('list_id') != original.get('list_id')
            or type(context.get('native_data_writes')) is not int or context['native_data_writes'] != 0):
        raise ValueError('Exact native list identity and read-only context required')
    if not isinstance(context.get('list_id'),str) or not context['list_id'] or context['list_id']!=context['list_id'].strip():
        raise ValueError('Exact native list identity required')
    if context.get('effective_retention_qualified') is not False:
        raise ValueError('This preservation ledger does not qualify effective retention')
    reviewed_at = context.get('preservation_reviewed_at_utc')
    if not isinstance(reviewed_at, str):
        raise ValueError('Explicit preservation review time required')
    utc(reviewed_at)
    writable=visible_inventory(fields,context.get('field_inventory'))
    if not writable: raise ValueError('Writable visible field inventory is empty')
    shape_rows = index_rows(shapes.get('items'), 'retained creation field shapes', 'created_item_id', allow_empty=True)
    if (shapes.get('schema_version') != 'publication-create-field-shape-inventory/v1'
            or shapes.get('read_only') is not True or count(shapes.get('item_count')) != len(shape_rows)
            or not set(shape_rows).issubset(ids)):
        raise ValueError('Creation field shapes differ from the cohort')
    result = []
    grades = Counter()
    shape_count = 0
    for ident in sorted(ids):
        row, evidence, action = current[ident], native[ident], actions[ident]
        if any(not isinstance(row.get(k),str) or not row[k] or row[k]!=row[k].strip()
               for k in ('GUID','odata.etag','OData__UIVersionString')):
            raise ValueError('Missing or padded item identity/version')
        utc(row['Modified'])
        if any(field not in row for field in writable):
            raise ValueError('Current export lacks a writable visible field')
        if ('field_1' not in row or row['field_1'] not in (None, '')
                or row.get('Title') not in (None, '') or row.get('field_2') not in (None, '')):
            raise ValueError('Selected item is not a blank-key/title/canonical stub')
        if not evidence.get('version_pages'):
            raise ValueError('Saved native version response references are required')
        if (row.get('GUID') != evidence.get('GUID') or row.get('odata.etag') != evidence.get('ETag')
                or row.get('OData__UIVersionString') != evidence.get('version')
                or evidence.get('version_history_complete') is not True
                or type(evidence.get('version_count')) is not int
                or evidence['version_count'] < 1 or not isinstance(evidence.get('version'),str) or evidence['version']!=evidence['version'].strip()
                or evidence.get('current_core_fields_equal_snapshot') is not True
                or evidence.get('attachment_export_complete') is not True
                or not isinstance(evidence.get('attachments'),list) or type(row.get('Attachments')) is not bool or row['Attachments'] != bool(evidence['attachments'])):
            raise ValueError('Current identity/version/attachment evidence is incomplete or drifted')
        if utc(row['Created']) != utc(historical[ident]['created']):
            raise ValueError('Current creation time differs from original candidate')
        grade = action.get('grade')
        detail = action.get('action')
        if grade == 'direct_action_id_match':
            if not isinstance(detail, dict) or any(not isinstance(detail.get(key), str) or not detail[key].strip() or detail[key]!=detail[key].strip()
                                                   for key in ('run_id', 'action_id', 'evidence_ref')):
                raise ValueError('Exact creation provenance lacks run/action/evidence')
        elif grade != 'unmatched' or detail is not None:
            raise ValueError('Unsupported or inferred creation provenance')
        grades[grade] += 1
        shape = shape_rows.get(ident)
        if shape:
            if (not detail or detail['run_id'] != shapes['run_id']
                    or shape.get('output_version_populated_parity') is not True
                    or not isinstance(shape.get('input_nonblank_fields'),list)
                    or not isinstance(shape.get('output_nonblank_fields'),list)
                    or any(not isinstance(n,str) or not n or n!=n.strip() for n in shape['input_nonblank_fields']+shape['output_nonblank_fields'])
                    or set(shape['input_nonblank_fields']) != set(shape['output_nonblank_fields'])
                    or len(shape['input_nonblank_fields']) != len(set(shape['input_nonblank_fields']))
                    or len(shape['output_nonblank_fields']) != len(set(shape['output_nonblank_fields']))
                    or not set(shape['input_nonblank_fields']) <= {f['InternalName'] for f in fields}
                    or set(shape['input_nonblank_fields']) & {'Title','field_1','field_2'}):
                raise ValueError('Blank-create field proof is not exact or run-bound')
            shape_count += 1
        result.append({
            'Id': ident, 'GUID': row['GUID'], 'ETag': row['odata.etag'],
            'Created': row['Created'], 'Modified': row['Modified'],
            'AuthorId': row.get('AuthorId'), 'EditorId': row.get('EditorId'),
            'current_version': evidence['version'],
            'current_record': row,
            'current_record_sha256': fingerprint(row),
            'writable_visible_fields_exported': len(writable),
            'version_history': evidence['version_pages'],
            'version_history_complete': True, 'older_saved_versions': evidence['version_count']-1,
            'attachments': evidence['attachments'], 'attachment_export_complete': True,
            'creation_provenance_grade': grade, 'retained_create_action': detail,
            'retained_blank_create_input_output_proven': shape is not None,
            'unresolved_provenance': grade == 'unmatched',
            'disposition': 'retain_in_place',
            'disposition_basis': 'User directs preservation unless a justified disposition is authorised; creation correlation alone does not authorise removal.',
            'preservation_review': {
                'status': 'preservation_only', 'decision': 'retain', 'reviewed_at_utc': reviewed_at,
                'actor': 'not asserted; source validation is not human review',
                'item_evidence': 'current record/hash, complete native version and retained item-specific creation evidence or explicit unresolved origin',
                'rationale': ('Exact creation provenance exists, but older content recoverability is not assessed, and there is no effective policy clearance or removal authority.'
                              if grade == 'direct_action_id_match' else
                              'Exact creation action remains unresolved; retain the item without inference from neighbouring IDs or timestamps.'),
            },
            'restore_ready': False, 'mutation_authorized': False, 'write_payload': None,
            'recovery_limits': ['Older saved publication content recoverability is not assessed; version counts alone do not prove content absence.',
                                'Effective site/list retention, holds and record declarations remain unqualified.',
                                'Ordinary recreation cannot promise original ID/GUID, system audit fields or version history.',
                                'No removal, quarantine or native restore was executed.'],
        })
    if (grades['direct_action_id_match'] != count(correlation.get('exact_match_count'))
            or grades['unmatched'] != count(correlation.get('unmatched_candidate_count'))):
        raise ValueError('Action provenance aggregate differs from per-item evidence')
    return {
        'schema': 'publication-stub-preservation-ledger/v1',
        "target_binding": target_qualification(cohort, original, correlation, context),
        'read_only': True, 'candidate_count': len(ids),
        'disposition_scope': 'preservation_only', 'disposition_decided': False,
        'mutation_authorized': False, 'cleanup_authorized': False, 'restore_ready_count': 0,
        'counts': {'exact_create_matches': grades['direct_action_id_match'],
                   'unresolved_create_provenance': grades['unmatched'],
                   'retained_blank_create_input_output_proven': shape_count,
                   'current_version_1_only': sum(e['version_count']==1 and e['version']=='1.0' for e in native.values()), 'no_attachments': sum(not e['attachments'] for e in native.values()),
                   'retain_in_place': len(ids), 'older_saved_content_recoverable': 0 if all(e['version_count']==1 for e in native.values()) else None},
        'context': context,
        'input_sha256': {name: fingerprint(value) for name, value in
                         [('registry', registry), ('cohort', cohort), ('original', original),
                          ('correlation', correlation), ('shapes', shapes), ('fields', fields)]},
        'items': result,
        'boundary': 'Complete preservation/provenance accounting is not cleanup eligibility, effective policy clearance or native restore acceptance.',
    }


def saved_inputs(paths: list[Path]) -> tuple[list[bytes], list]:
    """Parse and hash only the same single capture of each input."""
    payloads = [path.read_bytes() for path in paths]
    return payloads, [strict_json_loads(raw) for raw in payloads]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('registry', 'cohort', 'original', 'correlation', 'shapes', 'fields', 'context', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--version-field-map', required=True, type=Path)
    args = parser.parse_args()
    private = (Path(__file__).resolve().parents[1] / 'private/ops').resolve()
    paths = [getattr(args, name) for name in ('registry', 'cohort', 'original', 'correlation', 'shapes', 'fields', 'context', 'output')]
    if any(not path.resolve().is_relative_to(private) or path.is_symlink() for path in paths):
        parser.error('All ledger inputs/output must remain under ignored private/ops without symlinks')
    if len({path.resolve() for path in paths}) != len(paths) or args.output.exists():
        parser.error('Distinct inputs and a new output are required')
    private_output(args.output, [*paths[:-1],args.version_field_map])
    payloads, values = saved_inputs(paths[:-1])
    if isinstance(values[5], dict):
        if values[5].get('@odata.nextLink',values[5].get('odata.nextLink')) is not None:
            parser.error('Native field inventory pagination remains incomplete')
        values[5] = values[5]['value']
    if values[6].get('field_inventory',{}).get('artifact_sha256') != hashlib.sha256(payloads[5]).hexdigest():
        parser.error('Native field inventory response bytes changed')
    result = build(*values)
    cohort_bytes = payloads[0]
    if values[1].get('baseline_rows_sha256') != hashlib.sha256(cohort_bytes).hexdigest():
        parser.error('Current registry bytes do not match the native cohort baseline')
    result['native_file_verification'] = verify_native_files(values[1], values[0], args.cohort.parent / 'native', values[5], version_field_map=strict_json_loads(args.version_field_map.read_bytes()), inventory_receipt=values[6]['field_inventory'])
    result['retained_action_verification'] = verify_action_references(values[3], private)
    with args.output.open('x', encoding='utf-8') as output:
        output.write(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(str(result['candidate_count']) + ' rows accounted for; preserve all; no cleanup/restore authority')


if __name__ == '__main__':
    main()
