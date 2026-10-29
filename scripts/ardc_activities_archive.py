"""Validate unfiltered ARDC Activities pages for a create-only source archive.

The caller owns immutable native storage. This module does not write a
completion marker or claim a SharePoint capture.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import xml.etree.ElementTree as ET
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote_to_bytes, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

API = 'https://researchdata.edu.au/api/v2.0/registry/activities'
MAX_PAGE_BYTES = 20_000_000
OAI = '{http://www.openarchives.org/OAI/2.0/}'
RIF = '{http://ands.org.au/standards/rif-cs/registryObjects}'
OAI_ID_PREFIX = 'oai:ands.org.au::'


def extract_archive_page(raw: bytes) -> dict:
    """Extract activity IDs from one retained OAI page without altering it.

    This does not establish a complete generation: the caller must verify the
    saved manifest, every page and its token chain, and reconcile duplicates
    and deletion headers across the whole archive.
    """
    if not isinstance(raw, bytes) or len(raw) > MAX_PAGE_BYTES or b'\x00' in raw or b'<!DOCTYPE' in raw.upper():
        raise ValueError('Invalid or unsafe OAI page')
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise ValueError('Invalid OAI XML') from None
    if root.tag != OAI + 'OAI-PMH' or root.findall(OAI + 'error'):
        raise ValueError('OAI response contains an error or wrong root')
    lists = root.findall(OAI + 'ListRecords')
    if len(lists) != 1:
        raise ValueError('Expected one OAI ListRecords page')
    seen, activities, tombstones = set(), [], []
    for record in lists[0].findall(OAI + 'record'):
        headers = record.findall(OAI + 'header')
        if len(headers) != 1:
            raise ValueError('Expected one OAI header')
        header = headers[0]
        identifier = header.findtext(OAI + 'identifier')
        if not identifier or not identifier.startswith(OAI_ID_PREFIX):
            raise ValueError('Unexpected OAI identifier namespace')
        activity_id = identifier[len(OAI_ID_PREFIX):]
        if not activity_id.isascii() or not activity_id.isdigit() or activity_id in seen:
            raise ValueError('Invalid or duplicate OAI identifier')
        seen.add(activity_id)
        if header.get('status') == 'deleted':
            tombstones.append(activity_id)
            continue
        if header.get('status') is not None:
            raise ValueError('Unexpected OAI header status')
        objects = record.findall('./' + OAI + 'metadata/' + RIF + 'registryObjects/' + RIF + 'registryObject')
        if len(objects) != 1:
            raise ValueError('Expected one RIF-CS object')
        obj = objects[0]
        classes = [name for name in ('activity', 'collection', 'party', 'service')
                   for _ in obj.findall(RIF + name)]
        if len(classes) != 1:
            raise ValueError('Expected one RIF-CS entity class')
        if classes[0] == 'activity':
            key = obj.findtext(RIF + 'key')
            if not key or not key.strip():
                raise ValueError('Activity has no source key')
            activities.append({'id': activity_id, 'key': key})
    tokens = lists[0].findall(OAI + 'resumptionToken')
    if len(tokens) > 1:
        raise ValueError('Multiple OAI continuation tokens')
    return {'records': len(seen), 'ids': sorted(seen), 'activities': activities,
            'tombstones': tombstones, 'next_token': (tokens[0].text or '') if tokens else '',
            'page_sha256': hashlib.sha256(raw).hexdigest(), 'complete_generation': False}


def reconcile_archive(manifest_raw: bytes, expected_sha256: str, read, *, allow_incremental: bool = False) -> dict:
    """Reconcile an accepted native baseline manifest and all stored XML pages.

    ``read(filename)`` must fetch bytes from the exact existing archive. This
    verifies the retained manifest, counts, IDs and token chain; the manifest
    does not contain per-page source hashes, so it does not independently
    establish that current page bytes match original provider transport bytes.
    """
    if not isinstance(manifest_raw, bytes) or hashlib.sha256(manifest_raw).hexdigest() != expected_sha256:
        raise ValueError('Archive manifest hash mismatch')
    try:
        manifest = json.loads(manifest_raw)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('Invalid archive manifest') from None
    if (not isinstance(manifest, dict) or manifest.get('source') != 'ardc'
            or manifest.get('format') != 'rims-ardc-public-registry-v1'
            or manifest.get('complete') is not True
            or manifest.get('metadata_prefix') != 'rif'
            or manifest.get('scope') != 'complete_public_registry_metadata_before_local_selection'):
        raise ValueError('Unqualified archive manifest')
    full = manifest.get('full_reconciliation')
    if full is not True and not (allow_incremental and full is False):
        raise ValueError('Incremental archive requires explicit qualification')
    pages = manifest.get('pages')
    total = manifest.get('records')
    if (type(total) is not int or total < 1 or not isinstance(pages, list) or not pages
            or manifest.get('unique_identifiers') != total or manifest.get('provider_total') != total):
        raise ValueError('Archive total not reconciled')
    seen, activities, tombstones, hashes = set(), [], [], []
    token = ''
    initial = urlsplit(manifest.get('initial_uri', ''))
    initial_query = parse_qs(initial.query, keep_blank_values=True, strict_parsing=True)
    initial_keys = {'verb', 'metadataPrefix'} if full else {'verb', 'metadataPrefix', 'from', 'until'}
    if (initial.scheme != 'https' or initial.netloc != 'researchdata.edu.au'
            or initial.path != '/registry/services/oai' or initial.fragment
            or set(initial_query) != initial_keys or initial_query['verb'] != ['ListRecords']
            or initial_query['metadataPrefix'] != ['rif']
            or (not full and (len(initial_query['from']) != 1 or len(initial_query['until']) != 1
                              or initial_query['until'][0] != manifest.get('until')))):
        raise ValueError('Invalid archive initial request')
    if not full:
        try:
            start = datetime.fromisoformat(initial_query['from'][0].replace('Z', '+00:00'))
            end = datetime.fromisoformat(initial_query['until'][0].replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('Invalid incremental window') from None
        if start.utcoffset() != timezone.utc.utcoffset(start) or end.utcoffset() != timezone.utc.utcoffset(end) or start > end:
            raise ValueError('Invalid incremental window')
    for index, entry in enumerate(pages):
        if not isinstance(entry, dict) or entry.get('file') != f'page-{index}.xml' or entry.get('saved_content_equal') is not True:
            raise ValueError('Invalid archive page entry')
        u = urlsplit(entry.get('request', ''))
        query = parse_qs(u.query, keep_blank_values=True, strict_parsing=True)
        expected_query = initial_query if index == 0 else {'verb': ['ListRecords'], 'resumptionToken': [token]}
        if (u.scheme != 'https' or u.netloc != 'researchdata.edu.au'
                or u.path != '/registry/services/oai' or u.fragment or query != expected_query):
            raise ValueError('Archive continuation request mismatch')
        if index == 0 and entry['request'] != manifest['initial_uri']:
            raise ValueError('Archive initial request differs from manifest')
        if index and not token:
            raise ValueError('Archive continued after terminal page')
        page = extract_archive_page(read(entry['file']))
        if page['records'] != entry.get('rows') or page['next_token'] != entry.get('next_token'):
            raise ValueError('Archive page count or token mismatch')
        if len(page['tombstones']) != entry.get('deleted_headers'):
            raise ValueError('Archive deletion header mismatch')
        if seen.intersection(page['ids']):
            raise ValueError('Duplicate ID across archived pages')
        seen.update(page['ids'])
        activities.extend(page['activities'])
        tombstones.extend(page['tombstones'])
        hashes.append({'file': entry['file'], 'sha256': page['page_sha256']})
        token = page['next_token']
    if token or len(seen) != total:
        raise ValueError('Archive terminal token or count mismatch')
    return {'records': len(seen), 'ids': sorted(seen), 'activities': activities, 'tombstones': tombstones,
            'pages': hashes, 'manifest_sha256': expected_sha256,
            'full_reconciliation': full, 'from': None if full else initial_query['from'][0],
            'until': manifest.get('until'), 'stored_generation_reconciled': True,
            'original_transport_bytes_verified': False}


def overlay_incremental(baseline: dict, incremental: dict) -> dict:
    """Overlay one complete, overlapping incremental window on a full baseline.

    No provider snapshot or currentness is inferred. An incremental record
    replaces the corresponding baseline class and key; exposed tombstones are
    preserved as observations, not promoted to downstream deletion commands.
    """
    if (not isinstance(baseline, dict) or not isinstance(incremental, dict)
            or baseline.get('stored_generation_reconciled') is not True
            or incremental.get('stored_generation_reconciled') is not True
            or baseline.get('full_reconciliation') is not True
            or incremental.get('full_reconciliation') is not False):
        raise ValueError('A reconciled baseline and incremental generation are required')
    try:
        base_end = datetime.fromisoformat(baseline['until'].replace('Z', '+00:00'))
        update_start = datetime.fromisoformat(incremental['from'].replace('Z', '+00:00'))
        update_end = datetime.fromisoformat(incremental['until'].replace('Z', '+00:00'))
    except (KeyError, AttributeError, ValueError):
        raise ValueError('Invalid generation window') from None
    if (any(x.utcoffset() != timezone.utc.utcoffset(x) for x in (base_end, update_start, update_end))
            or update_start > base_end or update_end < base_end or update_start > update_end):
        raise ValueError('Incremental window does not cover baseline cutoff')

    def validate(generation):
        ids, activities, tombstones = generation.get('ids'), generation.get('activities'), generation.get('tombstones')
        if not isinstance(ids, list) or not isinstance(activities, list) or not isinstance(tombstones, list):
            raise ValueError('Invalid generation identities')
        if any(not isinstance(i, str) or not i.isascii() or not i.isdigit() for i in ids) or len(set(ids)) != len(ids) or generation.get('records') != len(ids):
            raise ValueError('Invalid generation key set')
        idset = set(ids)
        activity_map = {}
        for activity in activities:
            if not isinstance(activity, dict):
                raise ValueError('Invalid activity')
            identity, key = activity.get('id'), activity.get('key')
            if identity not in idset or identity in activity_map or not isinstance(key, str) or not key.strip():
                raise ValueError('Invalid activity identity')
            activity_map[identity] = key
        if any(i not in idset for i in tombstones) or len(set(tombstones)) != len(tombstones) or set(tombstones).intersection(activity_map):
            raise ValueError('Invalid tombstone set')
        return idset, activity_map

    _, current = validate(baseline)
    changed, replacement = validate(incremental)
    for identity in changed:
        current.pop(identity, None)
    current.update(replacement)
    return {'activities': [{'id': i, 'key': current[i]} for i in sorted(current)],
            'baseline_manifest_sha256': baseline.get('manifest_sha256'),
            'incremental_manifest_sha256': incremental.get('manifest_sha256'),
            'as_of': incremental['until'], 'tombstones_observed': incremental['tombstones'],
            'current_provider_snapshot_verified': False, 'per_record_version_order_verified': False,
            'downstream_deletions_authorized': False}


def _contains_credential(raw: bytes, credential: bytes) -> bool:
    # The API key is sent in a URL. A provider may echo that URL with the key
    # percent-encoded, so inspecting the literal bytes alone is insufficient.
    return credential in raw or credential in unquote_to_bytes(raw)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def activities_fetcher(credential: bytes, *, opener=None, activity_id: str | None = None):
    """Return a bounded, no-retry fetcher; never include the key in errors.

    The API requires the key in the query string. Its URL must not be logged,
    persisted, used in a subprocess argument, or followed across redirects.
    """
    if not isinstance(credential, bytes) or not credential:
        raise ValueError('Credential is required')
    try:
        key = credential.decode('ascii')
    except UnicodeDecodeError:
        raise ValueError('Invalid credential encoding') from None
    if any(c.isspace() for c in key):
        raise ValueError('Invalid credential whitespace')
    if activity_id is not None and (not isinstance(activity_id, str) or not activity_id.isascii() or not activity_id.isdigit()):
        raise ValueError('Exact numeric activity ID required')
    client = opener if opener is not None else build_opener(_NoRedirect())

    def fetch(offset: int, limit: int) -> bytes:
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError('Invalid offset or limit')
        params = {'api_key': key, 'limit': limit, 'offset': offset}
        if activity_id is not None:
            params['q'] = 'id:' + activity_id
        url = API + '?' + urlencode(params)
        request = Request(url, headers={'Accept': 'application/json',
                                        'User-Agent': 'RIMS-G02-qualification/1.0'})
        try:
            with client.open(request, timeout=30) as response:
                if response.status != 200:
                    raise ValueError('ARDC request returned non-success status')
                raw = response.read(MAX_PAGE_BYTES + 1)
        except HTTPError as exc:
            status = exc.code
            exc.close()
            raise ValueError(f'ARDC HTTP status {status}') from None
        except (URLError, OSError, TimeoutError):
            raise ValueError('ARDC request failed') from None
        if len(raw) > MAX_PAGE_BYTES:
            raise ValueError('ARDC page exceeds size limit')
        if _contains_credential(raw, credential):
            raise ValueError('Response contains credential; not archived')
        return raw
    fetch.query_scope = 'exact_id' if activity_id is not None else 'all_activities'
    return fetch


def exact_activity(raw: bytes, activity_id: str, *, source_key: str) -> dict:
    """Accept only an exact-ID result with the retained RIF-CS source key."""
    if not isinstance(activity_id, str) or not activity_id.isascii() or not activity_id.isdigit():
        raise ValueError('Exact numeric activity ID required')
    if not isinstance(source_key, str) or not source_key.strip():
        raise ValueError('Original RIF-CS source key required')
    total, records = decode_page(raw, 0, 2)
    if total != 1 or records[0]['id'] != activity_id or records[0].get('key') != source_key:
        raise ValueError('Exact activity identity did not reconcile')
    return records[0]


def capture_reconciled_ids(archive: dict, read_total, fetch_id, put, read, *, credential: bytes) -> dict:
    """Capture an already-reconciled OAI activity set via exact-ID lookups.

    The caller must qualify the archive's freshness, transport, native target,
    create-only writes and recovery independently. This never writes a native
    completion marker and does not make those qualifications on its own.
    """
    if not isinstance(credential, bytes) or not credential:
        raise ValueError('Credential is required for response leak checks')
    if not isinstance(archive, dict) or archive.get('stored_generation_reconciled') is not True:
        raise ValueError('A reconciled OAI archive is required')
    items = archive.get('activities')
    if not isinstance(items, list) or not items:
        raise ValueError('A nonempty activity set is required')
    seen, keys = set(), set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Invalid activity identity')
        identity, key = item.get('id'), item.get('key')
        if (not isinstance(identity, str) or not identity.isascii() or not identity.isdigit()
                or not isinstance(key, str) or not key.strip() or identity in seen or key in keys):
            raise ValueError('Invalid or duplicate activity identity')
        seen.add(identity)
        keys.add(key)
    start_total = read_total()
    if type(start_total) is not int or start_total != len(items):
        raise ValueError('OAI and Activities totals do not reconcile; no archive files created')
    pages = []
    for item in items:
        raw = fetch_id(item['id'])
        if isinstance(raw, bytes) and _contains_credential(raw, credential):
            raise ValueError('Response contains credential; not archived')
        exact_activity(raw, item['id'], source_key=item['key'])
        name = 'activity-' + item['id'] + '.json'
        put(name, raw)
        if read(name) != raw:
            raise ValueError('Archive readback differs from source bytes')
        pages.append({'name': name, 'id': item['id'], 'sha256': hashlib.sha256(raw).hexdigest()})
    after_capture = read_total()
    if type(after_capture) is not int or after_capture != start_total:
        raise ValueError('Activities total changed during capture')
    for item, page in zip(items, pages):
        raw = fetch_id(item['id'])
        if isinstance(raw, bytes) and _contains_credential(raw, credential):
            raise ValueError('Replay response contains credential')
        exact_activity(raw, item['id'], source_key=item['key'])
        if hashlib.sha256(raw).hexdigest() != page['sha256']:
            raise ValueError('Activity changed during replay')
    after_replay = read_total()
    if type(after_replay) is not int or after_replay != start_total:
        raise ValueError('Activities total changed during replay')
    return {'source': 'ardc-research-activities', 'records': len(items), 'pages': pages,
            'raw_readback': True, 'byte_replay': True, 'native_completion_marker': False,
            'archive_freshness_independently_verified': False,
            'provider_snapshot_isolation_verified': False}


def decode_page(raw: bytes, offset: int, limit: int) -> tuple[int, list[dict]]:
    """Validate an exact page before its original bytes are archived."""
    if not isinstance(raw, bytes) or type(limit) is not int or not 1 <= limit <= 1000 or type(offset) is not int or offset < 0:
        raise ValueError('Invalid page input')
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError('Invalid JSON response') from exc
    if not isinstance(payload, dict) or payload.get('status') != 'OK' or str(payload.get('code')) != '200':
        raise ValueError('ARDC application status is not successful')
    data = payload.get('data')
    # The provider documents an empty array rather than an object for no hits.
    if data == [] and offset == 0:
        return 0, []
    if not isinstance(data, dict):
        raise ValueError('Missing page data')
    total, actual_offset, records = data.get('numFound'), data.get('offset'), data.get('records')
    if type(total) is not int or total < 0 or type(actual_offset) is not int or actual_offset != offset:
        raise ValueError('Invalid total or offset')
    if not isinstance(records, list) or len(records) != min(limit, max(total - offset, 0)):
        raise ValueError('Incomplete or unexpected page')
    ids = [record.get('id') if isinstance(record, dict) else None for record in records]
    if any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Missing or duplicate record ID')
    return total, records


def capture(fetch, put, read, *, credential: bytes, limit: int = 1000) -> dict:
    """Save every page, verify its readback, and independently replay all pages.

    ``fetch(offset, limit)`` returns raw bytes. ``put(name, bytes)`` must be
    create-only, and ``read(name)`` must return the stored bytes. The returned
    receipt is deliberately not a published completion marker. An exception
    leaves any existing pages intact for explicit recovery.
    """
    if not isinstance(credential, bytes) or not credential:
        raise ValueError('Credential is required for response leak checks')
    if getattr(fetch, 'query_scope', None) == 'exact_id':
        raise ValueError('Exact-ID search cannot represent the full source')
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError('Invalid page limit')
    # Offset paging is unsafe when the provider reorders results between reads.
    # Check before creating the first native file, then still replay every page
    # after capture because an initial stable pair cannot prove later stability.
    first = fetch(0, limit)
    if isinstance(first, bytes) and _contains_credential(first, credential):
        raise ValueError('Response contains credential; not archived')
    decode_page(first, 0, limit)
    repeat = fetch(0, limit)
    if isinstance(repeat, bytes) and _contains_credential(repeat, credential):
        raise ValueError('Replay response contains credential')
    decode_page(repeat, 0, limit)
    if first != repeat:
        raise ValueError('First page is unstable; no archive files created')
    pages, seen, baseline_total, offset = [], set(), None, 0
    while baseline_total is None or offset < baseline_total:
        raw = first if offset == 0 else fetch(offset, limit)
        if isinstance(raw, bytes) and _contains_credential(raw, credential):
            raise ValueError('Response contains credential; not archived')
        total, records = decode_page(raw, offset, limit)
        if baseline_total is None:
            baseline_total = total
        if total != baseline_total:
            raise ValueError('Source count changed during capture')
        ids = [r['id'] for r in records]
        if seen.intersection(ids):
            raise ValueError('Duplicate record across pages')
        seen.update(ids)
        name = f'activities-page-{offset:09d}.json'
        put(name, raw)
        if read(name) != raw:
            raise ValueError('Archive readback differs from source bytes')
        pages.append({'name': name, 'offset': offset, 'count': len(records),
                      'sha256': hashlib.sha256(raw).hexdigest()})
        offset += len(records)
        if not records:
            break
    if len(seen) != baseline_total:
        raise ValueError('Incomplete key set')
    for page in pages:
        raw = fetch(page['offset'], limit)
        if isinstance(raw, bytes) and _contains_credential(raw, credential):
            raise ValueError('Replay response contains credential')
        total, records = decode_page(raw, page['offset'], limit)
        if total != baseline_total or hashlib.sha256(raw).hexdigest() != page['sha256']:
            raise ValueError('Source changed during replay')
        if len(records) != page['count']:
            raise ValueError('Replay page count changed')
    return {'source': 'ardc-research-activities', 'records': baseline_total,
            'page_size': limit, 'pages': pages, 'raw_readback': True,
            'byte_replay': True, 'native_completion_marker': False}
