"""Bind unchanged ARDC lookup inputs to verified retained OAI generation lineage.

Offline preparation only. A lookup no-hit is never an OAI absence assertion.
"""
from __future__ import annotations

import base64
import hashlib
import json
from urllib.parse import quote

from scripts.ardc_generation_lineage import overlay_verified_lineage
from scripts.source_capture_receipt import scope_sha256


def bind(packet, consumer, baseline, incremental, baseline_raw, incremental_raw):
    lineage = overlay_verified_lineage(baseline, incremental, baseline_raw, incremental_raw)
    if packet.get('format') != 'rims-source-assertion-verified-v1' or packet.get('source') != 'ardc':
        raise ValueError('Existing ARDC assertion packet required')
    manifest_raw = base64.b64decode(packet['manifest_base64'], validate=True)
    if hashlib.sha256(manifest_raw).hexdigest() != packet['manifest_sha256']:
        raise ValueError('Lookup manifest fingerprint differs')
    manifest = json.loads(manifest_raw)
    rows = json.loads(base64.b64decode(packet['projection_base64'], validate=True))
    if (manifest.get('source') != 'ardc' or manifest.get('complete') is not True
            or len(rows) != packet['count'] or len(rows) != manifest['count']):
        raise ValueError('Lookup manifest/projection count differs')
    raw = {}
    for entry in packet['raw_files']:
        if entry['name'] in raw:
            raise ValueError('Duplicate raw lookup file')
        raw[entry['name']] = base64.b64decode(entry['content_base64'], validate=True)
    activities = {row['id'] for row in lineage['activities']}
    selected = []
    keys = set()
    for row in rows:
        key = row['SourceKey']
        if key in keys or not key.startswith('ardc-lookup:') or row.get('BusinessRelationshipConfirmed') is not False:
            raise ValueError('Invalid or admitted lookup assertion')
        keys.add(key)
        entry = packet['entries'][quote(key, safe="~()*!.'-_")]
        content = raw[entry['name']]
        if hashlib.sha256(content).hexdigest() != entry['sha256']:
            raise ValueError('Raw lookup fingerprint differs')
        value = json.loads(content)
        if value['response']['statusCode'] != 200:
            raise ValueError('Successful retained lookup required')
        ids = row['ActivityIDs']
        if not isinstance(ids, list) or any(str(identity) not in activities for identity in ids):
            raise ValueError('Lookup activity missing from reconciled OAI lineage')
        selected.append({'source_key': key, 'activity_ids': ids,
                         'disposition_preserved': row['Disposition'],
                         'no_hit_is_not_source_absence': not bool(ids)})
    actions = consumer['properties']['definition']['actions']
    if (actions['Read_raw'] if 'Read_raw' in actions else actions.get('Verify_raw_files')) is None:
        raise ValueError('Existing raw-verifying assertion consumer required')
    if 'ardc' not in actions['Guard_packet']['inputs'] or 'ardc-lookup:' not in actions['Invalid_rows']['inputs']['where']:
        raise ValueError('Existing ARDC lookup consumer contract required')
    return {'kind': 'ardc-consumer-generation-binding-v1',
            'consumer_packet': packet, 'consumer_packet_sha256': scope_sha256(packet),
            'consumer_definition_sha256': scope_sha256(consumer),
            'baseline_manifest_sha256': lineage['baseline_manifest_sha256'],
            'increment_manifest_sha256': lineage['incremental_manifest_sha256'],
            'as_of': lineage['as_of'], 'selected_assertions': selected,
            'activity_identities_in_lineage': len(activities),
            'offline_input_package_ready': True, 'consumer_packet_changed': False,
            'native_calls': 0, 'native_runtime_verified': False,
            'canonical_admission': False, 'current_provider_snapshot_verified': False}
