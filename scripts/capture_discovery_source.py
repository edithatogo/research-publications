"""Bounded CLI discovery capture for existing Crossref, DataCite and ClinicalTrials scopes.

Two complete reads must agree on every full source record before committing a
local generation. Raw responses are retained before parsing. No Microsoft API,
native admission, schedule, exact-ID scope substitution, or automatic retry.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request

from scripts.clinicaltrials_source import validate_ids
from scripts.source_capture_receipt import (
    commit_generation,
    create_output,
    reject_failure_envelope,
    response_retainer,
    scope_sha256,
    strict_json,
    validate_dois,
    write_failure_receipt,
)
from scripts.source_http_retry import guarded_urlopen, read_response

ENDPOINTS = {'crossref': 'https://api.crossref.org/works',
             'clinicaltrials.gov': 'https://clinicaltrials.gov/api/v2/studies',
             'datacite': 'https://api.datacite.org/dois'}
MAX_PAGES = 1000
MAX_RECORDS = 50000
MAX_TOTAL_BYTES = 2_500_000_000
SOURCE_BYTE_LIMITS = {'crossref': 256_000_000, 'datacite': 256_000_000,
                      'clinicaltrials.gov': 2_500_000_000}


def validate_scope(scope):
    if not isinstance(scope, dict) or set(scope) != {'source', 'kind', 'queries'}:
        raise ValueError('Exact source, kind and queries required')
    source = scope['source']
    if source not in ENDPOINTS or scope['kind'] != 'complete_discovery':
        raise ValueError('Existing complete discovery source required')
    queries = scope['queries']
    if not isinstance(queries, list) or not 1 <= len(queries) <= 100:
        raise ValueError('Bounded explicit query inventory required')
    seen = set()
    for query in queries:
        if not isinstance(query, dict) or set(query) != {'key', 'parameters'}:
            raise ValueError('Exact query key and parameters required')
        key, params = query['key'], query['parameters']
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', key) or key in seen:
            raise ValueError('Unique safe query key required')
        seen.add(key)
        if not isinstance(params, dict) or not params or any(
                not isinstance(k, str) or not isinstance(v, str) or not v or v != v.strip()
                for k, v in params.items()):
            raise ValueError('Explicit literal query parameters required')
        if source == 'crossref':
            if set(params) != {'query.affiliation', 'filter', 'rows'} or params['rows'] != '500':
                raise ValueError('Full affiliation discovery with bounded rows required')
            # Frozen immutable created-date partitions, not changing index windows.
            pattern = r'(?:from-created-date:\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2},)?until-created-date:\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
            if not re.fullmatch(pattern, params['filter']):
                raise ValueError('Explicit frozen created-date bounds required')
            for bound in params['filter'].split(','):
                datetime.fromisoformat(bound.split(':', 1)[1])
            bounds = params['filter'].split(',')
            if len(bounds) == 2 and bounds[0].split(':', 1)[1] > bounds[1].split(':', 1)[1]:
                raise ValueError('Discovery bounds reversed')
        elif source == 'datacite':
            if (set(params) != {'query', 'page[size]', 'detail', 'affiliation', 'publisher'}
                    or params['page[size]'] != '100'
                    or any(params[k] != 'true' for k in ('detail', 'affiliation', 'publisher'))):
                raise ValueError('Full DataCite metadata and bounded explicit query required')
        else:
            allowed = {'query.loc', 'query.term', 'filter.advanced', 'pageSize', 'countTotal', 'format'}
            page_size = params.get('pageSize', '')
            if (set(params) - allowed or not page_size.isascii() or not page_size.isdigit()
                    or not 1 <= int(page_size) <= 1000
                    or params.get('countTotal') != 'true' or params.get('format') != 'json'
                    or not set(params) & {'query.loc', 'query.term', 'filter.advanced'}):
                raise ValueError('Complete explicit trial query required; no fields or ID restriction')
    return scope


def page_records(source, payload, expected):
    reject_failure_envelope(payload)
    if not isinstance(payload, dict):
        raise ValueError('Discovery response object required')  # noqa: TRY004 - retained evidence validation contract
    if source == 'crossref':
        if payload.get('status') != 'ok' or payload.get('message-type') != 'work-list':
            raise ValueError('Expected Crossref work-list response')
        data = payload.get('message')
        if not isinstance(data, dict):
            raise ValueError('Crossref message required')
        reject_failure_envelope(data)
        rows, count, token = data.get('items'), data.get('total-results'), data.get('next-cursor')
    elif source == 'datacite':
        if not isinstance(payload.get('meta'), dict) or not isinstance(payload.get('links', {}), dict):
            raise ValueError('DataCite metadata and links required')
        rows, count, token = payload.get('data'), payload['meta'].get('total'), payload.get('links', {}).get('next')
    else:
        rows, count, token = payload.get('studies'), payload.get('totalCount', expected), payload.get('nextPageToken')
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('Complete source records required')
    if type(count) is not int or not 0 <= count <= MAX_RECORDS or (expected is not None and count != expected):
        raise ValueError('Missing, changing or excessive declared discovery total')
    if token is not None and (not isinstance(token, str) or len(token) > 32000):
        raise ValueError('Invalid continuation token')
    indexed = {}
    for row in rows:
        reject_failure_envelope(row)
        if source == 'crossref':
            key = validate_dois([row.get('DOI')])[0].lower()
        elif source == 'datacite':
            attrs = row.get('attributes')
            if not isinstance(attrs, dict) or not isinstance(attrs.get('xml'), str) or not attrs['xml']:
                raise ValueError('Complete DataCite XML metadata required')
            key = validate_dois([row.get('id')])[0].lower()
            if validate_dois([attrs.get('doi')])[0].lower() != key:
                raise ValueError('DataCite record identity conflict')
        else:
            key = validate_ids([row.get('protocolSection', {}).get('identificationModule', {}).get('nctId')])[0]
        if key in indexed:
            raise ValueError('Duplicate discovery identity within page')
        indexed[key] = row
    return indexed, count, token


def capture(scope, output, *, opener=None, sleep=time.sleep):
    validate_scope(scope)
    output = Path(output)
    create_output(output)
    source = scope['source']
    manifest = {'source': source, 'scope': scope, 'scope_sha256': scope_sha256(scope),
        'generation_id': uuid.uuid4().hex, 'captured_utc': datetime.now(UTC).isoformat(),
        'files': [], 'request_attempts': [], 'queries': [], 'max_read_attempts': 1,
        'coverage': 'Complete explicit discovery queries; no source metadata fields removed',
        'native_admission': False}
    all_records = {}
    completed = []
    current = None
    total_bytes = 0
    def read(url, name, metadata):
        nonlocal total_bytes
        raw, _, _, _ = read_response(Request(url, headers={'Accept': 'application/json',
            'User-Agent': 'RIMS-source-retention/1.0'}), manifest['request_attempts'],
            opener=opener or guarded_urlopen, max_attempts=1, sleep=sleep,
            retain=response_retainer(output, manifest, {'source_url': url, **metadata}, name))
        total_bytes += len(raw)
        if total_bytes > min(MAX_TOTAL_BYTES, SOURCE_BYTE_LIMITS[source]):
            raise ValueError('Combined discovery raw byte cap exceeded')
        return strict_json(raw)

    def version(name):
        value = read('https://clinicaltrials.gov/api/v2/version', name, {'kind': 'version'})
        reject_failure_envelope(value)
        if not isinstance(value, dict) or any(not isinstance(value.get(k), str) or not value[k]
                                              for k in ('apiVersion', 'dataTimestamp')):
            raise ValueError('Complete trial API/data version required')
        return value
    try:
        before_version = version('version-before.json') if source == 'clinicaltrials.gov' else None
        for query in scope['queries']:
            current = query['key']
            reference = None
            for pass_number in (1, 2):
                initial_token = {'crossref': '*', 'datacite': '1'}.get(source)
                records, expected, token, seen_tokens = {}, None, initial_token, set()
                for page in range(MAX_PAGES):
                    params = dict(query['parameters'])
                    if token:
                        params[{'crossref': 'cursor', 'datacite': 'page[cursor]', 'clinicaltrials.gov': 'pageToken'}[source]] = token
                    url = ENDPOINTS[source] + '?' + urlencode(params)
                    name = f'{current}-pass{pass_number}-page{page:04d}.json'
                    payload = read(url, name, {'query_key': current, 'pass': pass_number, 'page': page})
                    incoming, expected, next_token = page_records(source, payload, expected)
                    if set(incoming) & records.keys():
                        raise ValueError('Repeated discovery identities across pages')
                    if len(incoming) > int(params[{'crossref': 'rows', 'datacite': 'page[size]', 'clinicaltrials.gov': 'pageSize'}[source]]):
                        raise ValueError('Response exceeds requested page bound')
                    records.update(incoming)
                    if len(records) > expected:
                        raise ValueError('Discovery rows exceed declared total')
                    if source == 'crossref':
                        terminal = not incoming or len(incoming) < int(params['rows'])
                    else:
                        terminal = not next_token
                    if terminal:
                        if len(records) != expected:
                            raise ValueError('Discovery ended before exact total was captured')
                        break
                    if not next_token or not incoming:
                        raise ValueError('Nonterminal discovery lacks rows or continuation')
                    if source == 'datacite':
                        link = urlsplit(next_token)
                        query_values = parse_qs(link.query, keep_blank_values=True)
                        cursor = query_values.pop('page[cursor]', None)
                        if (link.scheme != 'https' or link.netloc != 'api.datacite.org'
                                or link.path != '/dois' or link.fragment
                                or not cursor or len(cursor) != 1 or not cursor[0]
                                or query_values != {k: [v] for k, v in query['parameters'].items()}):
                            raise ValueError('DataCite continuation changed the complete query scope')
                        next_token = cursor[0]
                    if source != 'crossref' and (next_token == token or next_token in seen_tokens):
                        raise ValueError('Repeated discovery continuation token')
                    seen_tokens.add(next_token)
                    token = next_token
                    sleep(1)
                else:
                    raise ValueError('Discovery page cap reached without terminal proof')
                if reference is None:
                    reference = {key: scope_sha256(row) for key, row in records.items()}
                elif reference != {key: scope_sha256(row) for key, row in records.items()}:
                    raise ValueError('Complete discovery reads differ in identities or full metadata')
            for key, row in records.items():
                if key in all_records and all_records[key] != row:
                    raise ValueError('Conflicting full source records across query scopes')
                all_records[key] = row
            manifest['queries'].append({'key': current, 'count': len(records), 'passes': 2,
                                         'complete': True, 'record_sha256': scope_sha256(records)})
            completed.append(current)
        if source == 'clinicaltrials.gov' and version('version-after.json') != before_version:
            raise ValueError('Trial API/data version changed during complete capture')
        manifest['count'] = len(all_records)
        return commit_generation(output, 'records.json', [all_records[k] for k in sorted(all_records)], manifest)
    except Exception as error:
        write_failure_receipt(output, source=source, scope=scope, files=manifest['files'],
            completed_ids=completed, failed_id=current, error=error,
            generation_id=manifest['generation_id'], request_attempts=manifest['request_attempts'])
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--capture', action='store_true', help='Explicitly perform provider reads; otherwise validate scope offline')
    args = parser.parse_args()
    scope = validate_scope(strict_json(args.scope.read_bytes()))
    if args.capture:
        if args.output is None:
            parser.error('--capture requires private --output')
        result = capture(scope, args.output)
        print(json.dumps({'complete': result['complete'], 'count': result['count'], 'accepted': False}))
    else:
        print(json.dumps({'scope_sha256': scope_sha256(scope), 'queries': len(scope['queries']), 'provider_calls': 0}))


if __name__ == '__main__':
    main()
