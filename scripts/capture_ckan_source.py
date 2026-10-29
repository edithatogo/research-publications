"""Retain complete QGIP agency or DoRA activity source pages via bounded CLI reads.

This is an assisted acquisition alternative to Premium HTTP flows. It does not
upload, admit records, change source policy, or establish unattended operation.
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request
from uuid import UUID

from scripts.grants_qld_qgip_api import API_BASE, INDEX_RESOURCE_ID, SOURCE_ID
from scripts.grants_sources import DEFAULT_CATALOGUE, require_enabled_source
from scripts.source_capture_receipt import (
    commit_generation,
    create_output,
    reject_failure_envelope,
    response_retainer,
    scope_sha256,
    strict_json,
    write_failure_receipt,
)
from scripts.source_http_retry import guarded_urlopen, read_response

MAX_BYTES = 256_000_000
MAX_ROWS = 100000
MAX_RESOURCES = 100
DORA_PACKAGE = 'database-of-research-activity-dora'


def identity(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError('Canonical CKAN resource/package identifier required')
    return value


def rows(payload, offset, limit, expected=None):
    total = payload.get('total')
    records = payload.get('records')
    if (type(total) is not int or not 0 <= total <= MAX_ROWS
            or payload.get('total_was_estimated') is not False
            or type(payload.get('offset')) is not int or payload['offset'] != offset
            or not isinstance(records, list)
            or len(records) != min(limit, max(0, total - offset))
            or (expected is not None and total != expected)):
        raise ValueError('Incomplete, estimated or changed CKAN page coverage')
    indexed = {}
    for record in records:
        if not isinstance(record, dict) or type(record.get('_id')) is not int or record['_id'] <= 0:
            raise ValueError('CKAN record requires positive integer _id')
        key = str(record['_id'])
        if key in indexed:
            raise ValueError('Duplicate CKAN page identity')
        indexed[key] = record
    return indexed, total


def capture(source, output, *, opener=None, sleep=time.sleep, page_size=100, catalogue_path=DEFAULT_CATALOGUE):
    if source not in ('qgip', 'dora-activities'):
        raise ValueError('Existing QGIP or DoRA activity source required')
    if type(page_size) is not int or not 1 <= page_size <= 1000:
        raise ValueError('Bounded CKAN page size required')
    if source == 'qgip':
        require_enabled_source(catalogue_path, SOURCE_ID)
    output = Path(output)
    scope = {'source': source, 'kind': 'complete_unfiltered_source',
             'index_resource': INDEX_RESOURCE_ID if source == 'qgip' else None,
             'package_name': DORA_PACKAGE if source == 'dora-activities' else None}
    create_output(output)
    manifest = {'source': source, 'scope': scope, 'scope_sha256': scope_sha256(scope),
        'generation_id': uuid.uuid4().hex, 'captured_utc': datetime.now(UTC).isoformat(),
        'files': [], 'request_attempts': [], 'resources': [], 'max_read_attempts': 1,
        'native_admission': False, 'record_grain': 'resource_id plus _id; never publication identity'}
    byte_count = 0
    completed = []
    current = None

    def read(action, params, filename):
        nonlocal byte_count
        url = API_BASE + action + '?' + urlencode(params)
        raw, _, _, _ = read_response(Request(url, headers={'Accept': 'application/json'}),
            manifest['request_attempts'], opener=opener or guarded_urlopen, max_attempts=1,
            sleep=sleep, retain=response_retainer(output, manifest, {'source_url': url}, filename))
        byte_count += len(raw)
        if byte_count > MAX_BYTES:
            raise ValueError('CKAN combined raw byte cap exceeded')
        value = strict_json(raw)
        reject_failure_envelope(value)
        if not isinstance(value, dict) or value.get('success') is not True or not isinstance(value.get('result'), dict):
            raise ValueError('Successful CKAN result object required')
        result = value['result']
        reject_failure_envelope(result)
        return result

    try:
        if source == 'qgip':
            initial = read('datastore_search', {'resource_id': INDEX_RESOURCE_ID, 'limit': 5000, 'offset': 0}, 'index-before.json')
            index, count = rows(initial, 0, 5000)
            if not 0 < count < 5000:
                raise ValueError('Complete bounded QGIP agency index required')
            resources = sorted({identity(row.get('Resource')) for row in index.values()})
        else:
            initial = read('package_show', {'id': DORA_PACKAGE}, 'index-before.json')
            if initial.get('name') != DORA_PACKAGE or not isinstance(initial.get('resources'), list):
                raise ValueError('Maintained DoRA activity package required')
            candidates = [r for r in initial['resources'] if isinstance(r, dict)
                          and r.get('datastore_active') is True and str(r.get('format', '')).upper() == 'CSV']
            if not candidates:
                raise ValueError('No active DoRA CSV resource')
            latest = max(str(r.get('last_modified') or r.get('created') or '') for r in candidates)
            candidates = [r for r in candidates if str(r.get('last_modified') or r.get('created') or '') == latest]
            if len(candidates) != 1 or not latest:
                raise ValueError('Ambiguous current DoRA resource')
            resources = [identity(candidates[0]['id'])]
        if len(resources) > MAX_RESOURCES:
            raise ValueError('CKAN resource cap exceeded')
        all_records = []
        for resource_id in resources:
            current = resource_id
            resource = read('resource_show', {'id': resource_id}, resource_id + '-resource-before.json')
            package_id = identity(resource.get('package_id'))
            package = read('package_show', {'id': package_id}, resource_id + '-package-before.json')
            schema = read('datastore_info', {'id': resource_id}, resource_id + '-schema-before.json')
            fields = schema.get('fields')
            if (resource.get('id') != resource_id or package.get('id') != package_id
                    or not isinstance(package.get('license_id'), str) or not package['license_id']
                    or not isinstance(fields, list) or not fields
                    or any(not isinstance(f, dict) or not isinstance(f.get('id'), str)
                           or not f['id'] or not isinstance(f.get('type'), str) for f in fields)):
                raise ValueError('Exact resource, package, licence metadata and schema required')
            field_names = [f['id'] for f in fields]
            if len(field_names) != len(set(field_names)):
                raise ValueError('Duplicate CKAN schema field')
            reference = None
            for pass_number in (1, 2):
                collected, total, offset = {}, None, 0
                while total is None or offset < total:
                    page = read('datastore_search', {'resource_id': resource_id, 'limit': page_size, 'offset': offset},
                                f'{resource_id}-pass{pass_number}-offset{offset}.json')
                    incoming, total = rows(page, offset, page_size, total)
                    page_fields = page.get('fields')
                    if (not isinstance(page_fields, list) or
                            [f.get('id') for f in page_fields if isinstance(f, dict)] != field_names
                            or any(set(row) != set(field_names) for row in incoming.values())):
                        raise ValueError('CKAN page fields differ from complete source schema')
                    if set(collected) & incoming.keys():
                        raise ValueError('Duplicate identity across CKAN pages')
                    collected.update(incoming)
                    offset += page_size
                    if offset < total:
                        sleep(1)
                if len(collected) != total:
                    raise ValueError('CKAN final key count differs')
                if reference is None:
                    reference = collected
                elif reference != collected:
                    raise ValueError('CKAN complete reads differ in keys or full source fields')
            resource_after = read('resource_show', {'id': resource_id}, resource_id + '-resource-after.json')
            package_after = read('package_show', {'id': package_id}, resource_id + '-package-after.json')
            schema_after = read('datastore_info', {'id': resource_id}, resource_id + '-schema-after.json')
            if (any(resource.get(k) != resource_after.get(k) for k in ('id', 'package_id', 'last_modified', 'hash'))
                    or any(package.get(k) != package_after.get(k) for k in ('id', 'license_id', 'metadata_modified'))
                    or schema['fields'] != schema_after.get('fields')):
                raise ValueError('CKAN source metadata changed during complete reads')
            all_records.extend({'resource_id': resource_id, 'record': collected[k]} for k in sorted(collected, key=int))
            manifest['resources'].append({'resource_id': resource_id, 'package_id': package_id,
                'license_id': package['license_id'], 'count': total, 'passes': 2,
                'record_sha256': scope_sha256(collected)})
            completed.append(resource_id)
        final = (read('datastore_search', {'resource_id': INDEX_RESOURCE_ID, 'limit': 5000, 'offset': 0}, 'index-after.json')
                 if source == 'qgip' else read('package_show', {'id': DORA_PACKAGE}, 'index-after.json'))
        if source == 'qgip':
            final_rows, final_count = rows(final, 0, 5000)
            stable = final_rows == index and final_count == count and final.get('fields') == initial.get('fields')
        else:
            stable = final == initial
        if not stable:
            raise ValueError('CKAN source index changed during capture')
        manifest['count'] = len(all_records)
        return commit_generation(output, 'records.json', all_records, manifest)
    except Exception as error:
        write_failure_receipt(output, source=source, scope=scope, files=manifest['files'],
            completed_ids=completed, failed_id=current, error=error,
            generation_id=manifest['generation_id'], request_attempts=manifest['request_attempts'])
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=['qgip', 'dora-activities'], required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--catalogue', type=Path, default=DEFAULT_CATALOGUE)
    args = parser.parse_args()
    if not args.capture:
        print(json.dumps({'source': args.source, 'provider_calls': 0, 'mode': 'offline-preparation'}))
        return
    if args.output is None:
        parser.error('--capture requires private --output')
    result = capture(args.source, args.output, catalogue_path=args.catalogue)
    print(json.dumps({'complete': result['complete'], 'count': result['count'], 'accepted': False}))


if __name__ == '__main__':
    main()
