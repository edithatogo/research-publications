"""Bounded exact-ID Activities lookups; full-corpus acceptance is separate."""
from __future__ import annotations

import hashlib
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

try:
    from scripts.ardc_activities_archive import API, MAX_PAGE_BYTES, _NoRedirect, _contains_credential, decode_page
except ModuleNotFoundError:
    from ardc_activities_archive import API, MAX_PAGE_BYTES, _NoRedirect, _contains_credential, decode_page


def _expected(identities: list[dict]) -> dict[str, str]:
    if not isinstance(identities, list) or not 1 <= len(identities) <= 100:
        raise ValueError('One to 100 identities required')
    expected = {}
    for row in identities:
        if not isinstance(row, dict):
            raise ValueError('Invalid identity')
        identity, source_key = row.get('id'), row.get('key')
        if (not isinstance(identity, str) or not identity.isascii() or not identity.isdigit() or len(identity) > 20
                or identity in expected or not isinstance(source_key, str) or not source_key.strip()):
            raise ValueError('Invalid or duplicate identity')
        expected[identity] = source_key
    return expected


def validate_batch(raw: bytes, identities: list[dict], credential: bytes) -> dict[str, dict]:
    """Reject leakage, ambiguous JSON, partial results and ID or key drift."""
    expected = _expected(identities)
    if not isinstance(credential, bytes) or not credential or not isinstance(raw, bytes):
        raise ValueError('Credential and response bytes are required')
    if len(raw) > MAX_PAGE_BYTES or _contains_credential(raw, credential):
        raise ValueError('Unsafe response; not archived')
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON object key')
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError('Non-finite JSON value')
    try:
        json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('Invalid or ambiguous JSON response') from None
    total, records = decode_page(raw, 0, len(expected))
    actual = {r['id']: r.get('key') for r in records}
    if total != len(expected) or actual != expected:
        raise ValueError('Batch ID and source-key sets did not reconcile')
    return {r['id']: r for r in records}


def lookup_batch(identities: list[dict], credential: bytes, *, opener=None) -> bytes:
    """Read and reconcile a bounded batch; return the original response bytes.

    This requires an independently established identity set. A successful
    batch does not prove that the identity set is complete or current.
    """
    if not isinstance(credential, bytes) or not credential:
        raise ValueError('Credential is required')
    try:
        key = credential.decode('ascii')
    except UnicodeDecodeError:
        raise ValueError('Invalid credential encoding') from None
    if any(c.isspace() for c in key):
        raise ValueError('Invalid credential whitespace')
    expected = _expected(identities)
    query = 'id:(' + ' OR '.join(expected) + ')'
    url = API + '?' + urlencode({'api_key': key, 'q': query, 'limit': len(expected), 'offset': 0})
    request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'RIMS-G02-qualification/1.0'})
    try:
        with (opener if opener is not None else build_opener(_NoRedirect())).open(request, timeout=30) as response:
            if response.status != 200:
                raise ValueError('ARDC request returned non-success status')
            raw = response.read(MAX_PAGE_BYTES + 1)
    except HTTPError as exc:
        status = exc.code
        exc.close()
        raise ValueError(f'ARDC HTTP status {status}') from None
    except (URLError, OSError, TimeoutError):
        raise ValueError('ARDC request failed') from None
    validate_batch(raw, identities, credential)
    return raw


def capture_batches(overlay: dict, read_total, fetch_batch, probe, put, read, *, credential: bytes, batch_size: int = 32,
                    on_archived=None) -> dict:
    """Prepare unfiltered archive batches from a verified source-identity set.

    ``probe(name)`` must return None only for a proven absent file, bytes for
    an existing file, and raise on permission or transport errors. ``put`` must
    be create-only. The caller must independently qualify the overlay's
    freshness, snapshot scope, native target and transport. This function does
    not publish a completion marker or certify those properties.
    """
    if (not isinstance(overlay, dict) or overlay.get('generation_lineage_verified') is not True
            or (on_archived is not None and not callable(on_archived))
            or type(batch_size) is not int or not 1 <= batch_size <= 32):
        raise ValueError('Invalid batch capture configuration')
    for field in ('baseline_manifest_sha256', 'incremental_manifest_sha256'):
        if not isinstance(overlay.get(field), str) or re.fullmatch(r'[0-9a-f]{64}', overlay[field]) is None:
            raise ValueError('Reconciled baseline and incremental manifest hashes required')
    rows = overlay.get('activities')
    if not isinstance(rows, list) or not rows or not isinstance(credential, bytes) or not credential:
        raise ValueError('Activity identities and credential are required')
    identities, source_keys = set(), set()
    for i in range(0, len(rows), batch_size):
        batch = _expected(rows[i:i + batch_size])
        if identities.intersection(batch) or source_keys.intersection(batch.values()) or len(set(batch.values())) != len(batch):
            raise ValueError('Duplicate activity ID or source key')
        identities.update(batch)
        source_keys.update(batch.values())
    total = read_total()
    if type(total) is not int or total != len(rows):
        raise ValueError('Activity total differs from source key set; no archive files created')
    receipt = []
    for offset in range(0, len(rows), batch_size):
        batch = rows[offset:offset + batch_size]
        raw = fetch_batch(batch)
        records = validate_batch(raw, batch, credential)
        name = f'activities-batch-{offset:09d}.json'
        normalized = json.dumps(records, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
        existing = probe(name)
        reused = existing is not None
        if reused:
            existing_records = validate_batch(existing, batch, credential)
            prior_normalized = json.dumps(existing_records, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
            if prior_normalized != normalized:
                raise ValueError('Existing archive batch differs from current source')
            raw = existing
        else:
            put(name, raw)
        if read(name) != raw:
            raise ValueError('Archive readback differs from source bytes')
        if on_archived is not None:
            on_archived(name, raw)
        receipt.append({'name': name, 'count': len(batch), 'reused': reused, 'sha256': hashlib.sha256(raw).hexdigest(),
                        'record_fields_sha256': hashlib.sha256(normalized).hexdigest()})
    after_capture = read_total()
    if type(after_capture) is not int or after_capture != total:
        raise ValueError('Activity total changed during capture')
    byte_replay = True
    for index, offset in enumerate(range(0, len(rows), batch_size)):
        batch = rows[offset:offset + batch_size]
        raw = fetch_batch(batch)
        records = validate_batch(raw, batch, credential)
        normalized = json.dumps(records, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
        if hashlib.sha256(normalized).hexdigest() != receipt[index]['record_fields_sha256']:
            raise ValueError('Activity record fields changed during replay')
        if hashlib.sha256(raw).hexdigest() != receipt[index]['sha256']:
            byte_replay = False
    after_replay = read_total()
    if type(after_replay) is not int or after_replay != total:
        raise ValueError('Activity total changed during replay')
    return {'source': 'ardc-research-activities', 'records': len(rows), 'batches': receipt,
            'baseline_manifest_sha256': overlay['baseline_manifest_sha256'],
            'incremental_manifest_sha256': overlay['incremental_manifest_sha256'],
            'raw_readback': True, 'record_fields_replayed': True, 'byte_replay': byte_replay,
            'native_completion_marker': False,
            'provider_snapshot_isolation_verified': False, 'archive_freshness_verified': False}
