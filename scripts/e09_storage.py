# SPDX-License-Identifier: Apache-2.0
"""Lossless E09 storage envelopes; native access and ETags remain separate gates.

The storage revision is independent of publication/project source revisions.
This adapter does not establish an authenticated contributor or grant delivery.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

from scripts.e09_feed_contracts import (
    validate_contribution_record, validate_subscription_preference,
    validate_delivery_receipt,
)
from scripts.e09_thread_mapping import validate_thread, transition_thread
from scripts.e09_edition_storage import validate_edition_snapshot

KINDS = {
    'contribution': (validate_contribution_record, 'contribution_id'),
    'subscription': (validate_subscription_preference, 'subscription_id'),
    'receipt': (validate_delivery_receipt, 'receipt_id'),
    'thread': (validate_thread, 'thread_id'),
    'edition': (validate_edition_snapshot, 'edition_snapshot_id'),
}
FIELDS = {'schema', 'kind', 'logical_id', 'key', 'storage_revision',
          'payload_json', 'payload_sha256', 'qualification_only'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def envelope(kind, record, storage_revision):
    if not isinstance(kind, str) or kind not in KINDS:
        raise ValueError('Unsupported storage kind')
    if type(storage_revision) is not int or storage_revision < 1:
        raise ValueError('Positive storage revision required')
    validate, id_field = KINDS[kind]
    # Retain exact values rather than serializing a validator's projection.
    original = deepcopy(record)
    validate(deepcopy(original))
    if kind == 'subscription':
        if original['delivery_authority_active'] or original['delivery_authority_reference'] is not None:
            raise ValueError('Storage qualification cannot activate delivery')
    if kind == 'receipt' and (original['intended_outcome'] != 'no_send'
                            or original['post_reference'] is not None
                            or original['delivery_authority_reference'] is not None):
        raise ValueError('Storage qualification requires no-send receipts')
    if kind != 'contribution' and original['revision'] != storage_revision:
        raise ValueError('Preference/receipt revision must match storage revision')
    payload = canonical(original)
    if len(payload.encode('utf-8')) > 60000 or len(original[id_field].encode('utf-8')) > 60000:
        raise ValueError('Payload exceeds qualified native text capacity; no truncation')
    identity = canonical([kind, original[id_field]])
    return dict(schema=1, kind=kind, logical_id=original[id_field],
                key='e09:' + sha256(identity.encode()).hexdigest(),
                storage_revision=storage_revision, payload_json=payload,
                payload_sha256=sha256(payload.encode()).hexdigest(),
                qualification_only=True)


def validate_envelope(value):
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError('Exact envelope shape required')
    try:
        record = json.loads(value['payload_json'])
        expected = envelope(value['kind'], record, value['storage_revision'])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Malformed storage envelope') from exc
    if value != expected or type(value['schema']) is not int or value['qualification_only'] is not True:
        raise ValueError('Envelope identity/content fingerprint differs')
    return expected


def transition(before, after):
    """Classify replay or next revision without writing or approving a decision."""
    before, after = validate_envelope(before), validate_envelope(after)
    if before == after:
        return 'unchanged'
    if before['kind'] == 'edition' or after['kind'] == 'edition':
        raise ValueError('Edition snapshots are immutable; preserve original and prepare a new identity')
    if before['kind'] == after['kind'] == 'thread':
        return transition_thread(json.loads(before['payload_json']), json.loads(after['payload_json']))
    if before['key'] != after['key'] or before['kind'] != after['kind']:
        raise ValueError('Storage identity changed')
    if after['storage_revision'] != before['storage_revision'] + 1:
        raise ValueError('Conflicting/stale storage revision')
    a, b = json.loads(before['payload_json']), json.loads(after['payload_json'])
    if before['kind'] == 'receipt' and a['outcome'] == 'failed_uncertain':
        raise ValueError('Uncertain provider outcome requires independent reconciliation; preserve original receipt')
    immutable = {
        'contribution': ['contribution_id', 'publication_key', 'thread_id',
                         'contributor_id_kind', 'contributor_urn', 'identity_verification_ref',
                         'submitted_on', 'source_revision', 'submitted_at_project_revision'],
        'subscription': ['subscription_id', 'subscriber_urn', 'enrolled_on', 'contact_route'],
        'receipt': ['receipt_id', 'publication_key', 'thread_id', 'discovered_on', 'trigger'],
    }[before['kind']]
    if any(a[k] != b[k] for k in immutable):
        raise ValueError('Record identity/provenance changed; retain separate evidence')
    date_field = {'subscription': 'revised_on', 'receipt': 'recorded_at'}.get(before['kind'])
    if date_field:
        from datetime import datetime
        if datetime.fromisoformat(b[date_field]) < datetime.fromisoformat(a[date_field]):
            raise ValueError('Revision chronology moved backwards')
    return 'update'


if __name__ == '__main__':
    import sys
    from pathlib import Path
    packet = json.loads(Path(sys.argv[1]).read_text())
    validate_envelope(packet)
    if len(sys.argv) == 3:
        print(transition(json.loads(Path(sys.argv[2]).read_text()), packet))
    else:
        print('PASS_ENVELOPE')
