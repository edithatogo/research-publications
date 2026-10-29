"""Prepare OpenAlex observations for the existing Microsoft retained-data path.

No provider requests, tenant writes or commit markers. Complete response bytes
and observed schema precede the native source-specific projection. The native
owner supplies storage/readback and accepted-generation evidence separately.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from enrich_openalex import clean_doi

CHUNK_CHARACTERS = 24000
STATUSES = {
    'success', 'not_found', 'access_denied', 'rate_limited', 'unavailable',
    'http_error', 'invalid_response', 'identity_mismatch', 'response_too_large',
}


def schema(value):
    """Describe every returned field, including nulls and nested array variants."""
    if value is None:
        return {'type': 'null'}
    if isinstance(value, dict):
        return {'type': 'object', 'fields': {k: schema(v) for k, v in value.items()}}
    if isinstance(value, list):
        variants = {json.dumps(schema(v), sort_keys=True) for v in value}
        return {'type': 'array', 'variants': [json.loads(v) for v in sorted(variants)]}
    return {'type': 'boolean' if isinstance(value, bool) else
            'number' if isinstance(value, (float, int)) else 'string'}


def utc(value):
    if not isinstance(value, str):
        raise ValueError('Observation time required')
    instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if instant.tzinfo is None or instant.utcoffset().total_seconds() != 0:
        raise ValueError('UTC observation time required')
    if instant > datetime.now(timezone.utc):
        raise ValueError('Future observation time')
    return value


def build(frozen: bytes, candidate: dict) -> dict:
    records = json.loads(frozen)
    if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
        raise ValueError('Frozen publication-record list required')
    fingerprint = hashlib.sha256(frozen).hexdigest()
    if candidate.get('input_sha256') != fingerprint:
        raise ValueError('Candidate belongs to a different input generation')
    requested = {d.casefold() for r in records if (d := clean_doi(r.get('DOI')))}
    observations = candidate.get('observations')
    if (not isinstance(observations, dict) or not observations or len(observations) > 50
            or not set(observations).issubset(requested)):
        raise ValueError('Bounded observations must belong to the frozen DOI scope')
    chunks, statuses, works = [], [], set()
    for doi, observation in observations.items():
        status = observation.get('status')
        if status not in STATUSES:
            raise ValueError('Unknown provider outcome')
        observed = utc(observation.get('observed_utc'))
        statuses.append({'RequestedDOI': doi, 'Status': status, 'ObservedUTC': observed,
                         'HTTPStatus': observation.get('http_status')})
        # Failures/not-found never generate a replacement source record.
        if status != 'success':
            continue
        if observation.get('http_status') != 200:
            raise ValueError('Successful observation must have HTTP200 evidence')
        raw = base64.b64decode(observation['raw_response_base64'], validate=True)
        if not raw or len(raw) > 16 * 1024 * 1024:
            raise ValueError('Response size outside acquisition bound')
        if hashlib.sha256(raw).hexdigest() != observation.get('raw_response_sha256'):
            raise ValueError('Raw response fingerprint mismatch')
        payload = json.loads(raw.decode('utf-8'))
        if not isinstance(payload, dict) or payload != observation.get('raw_payload'):
            raise ValueError('Raw bytes differ from candidate payload')
        returned_doi = clean_doi(payload.get('doi'))
        work = payload.get('id')
        if (not returned_doi or returned_doi.casefold() != doi or
                not isinstance(work, str) or not re.fullmatch(r'https://openalex.org/W[0-9]+', work)):
            raise ValueError('Exact DOI and namespaced work identity required')
        if work in works:
            raise ValueError('Duplicate provider work identity')
        works.add(work)
        # Derive from raw bytes only; candidate-record overwrites/metrics are not
        # authoritative and cannot alter canonical titles, dates or affiliations.
        envelope = {
            'kind': 'openalex_retained_observation_v1', 'source': 'OpenAlex',
            'requested_doi': doi, 'work_id': work, 'observed_utc': observed,
            'input_sha256': fingerprint, 'http_status': 200,
            'request': {'origin': 'https://api.openalex.org',
                        'relative_path': 'works/https://doi.org/' + doi},
            'raw_response_base64': observation['raw_response_base64'],
            'raw_response_sha256': observation['raw_response_sha256'],
            'raw_byte_count': len(raw), 'observed_schema': schema(payload),
        }
        encoded = json.dumps(envelope, ensure_ascii=False, separators=(',', ':'),
                             allow_nan=False).encode('utf-8').hex().upper()
        count = (len(encoded) + CHUNK_CHARACTERS - 1) // CHUNK_CHARACTERS
        for index in range(count):
            chunks.append({'OpenAlexWorkID': work, 'ChunkIndex': index,
                           'ChunkCount': count, 'MetadataCharacters': len(encoded),
                           'Encoding': 'UTF8-HEX',
                           'MetadataChunk': encoded[index * CHUNK_CHARACTERS:(index + 1) * CHUNK_CHARACTERS]})
    return {
        'kind': 'openalex_retention_preparation_v1', 'source': 'OpenAlex',
        'input_sha256': fingerprint, 'source_record_count': len(records),
        'source_scope_dois': sorted(requested), 'expected_keys': sorted(works),
        'key_column': 'OpenAlexWorkID', 'chunk_table': 'OpenAlexMetadataChunks',
        'chunks': chunks, 'attempt_statuses': statuses,
        'native_storage_verified': False, 'accepted_commit': False,
        'ready_for_native_stage': bool(chunks),
        'retain_previous_on_failure': True,
    }


def private_path(value, root):
    path = Path(value).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Inputs and output must stay under the supplied private/ops root')
    return path


def require_ignored(root, paths):
    """Refuse inputs or outputs not covered by an active repository ignore rule."""
    for path in (root, *paths):
        try:
            result = subprocess.run(['git', 'check-ignore', '-q', str(path)], cwd=root,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    check=False)
        except OSError as exc:
            raise ValueError('Git ignore qualification is unavailable') from exc
        if result.returncode != 0:
            raise ValueError('Private path must be ignored in its repository')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-root', required=True, type=Path)
    parser.add_argument('--input', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = args.private_root.resolve()
    if root.name != 'ops' or root.parent.name != 'private' or not root.is_dir():
        raise ValueError('Existing ignored private/ops directory required')
    source, candidate, destination = [private_path(v, root) for v in
                                     (args.input, args.candidate, args.output)]
    require_ignored(root, (source, candidate, destination))
    frozen, evidence = source.read_bytes(), candidate.read_bytes()
    result = build(frozen, json.loads(evidence))
    result['candidate_sha256'] = hashlib.sha256(evidence).hexdigest()
    if source.read_bytes() != frozen or candidate.read_bytes() != evidence:
        raise ValueError('Prepared inputs drifted')
    with os.fdopen(os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'status': 'prepared_uncommitted', 'works': len(result['expected_keys']),
                      'chunks': len(result['chunks']), 'attempts': len(result['attempt_statuses']),
                      'native_storage_verified': False}))


if __name__ == '__main__':
    main()
