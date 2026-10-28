# SPDX-License-Identifier: Apache-2.0
"""No-send logical thread records; unknown provider outcomes never auto-retry."""
from copy import deepcopy
import hashlib
import json
from scripts.e09_feed_contracts import (validate_delivery_receipt, stable_thread_id,
                                       publication_source_key, _parse_aware_instant,
                                       _required_identifier)
from scripts.e09_post_content import render_post_body

FIELDS = {'thread_id', 'publication_key', 'canonical_key', 'source_aliases',
          'render_input', 'rendered_post', 'delivery_receipt', 'revision',
          'dispatch_state', 'human_notes', 'input_fingerprint', 'native_input_reference'}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def prepare_thread(selection, *, revision, recorded_at, native_input_reference,
                   source_aliases=None, human_notes=None, uncertain=False):
    if type(uncertain) is not bool:
        raise ValueError('Explicit boolean uncertainty required')
    post = render_post_body(selection)
    if type(revision) is not int or revision < 1:
        raise ValueError('Positive thread revision required')
    if source_aliases is None:
        source_aliases = [selection['publication_key']]
    if not isinstance(source_aliases, list) or not source_aliases or any(not isinstance(a, str) for a in source_aliases):
        raise ValueError('Explicit source aliases must be a nonempty text list')
    aliases = sorted(set(source_aliases))
    receipt = dict(receipt_id=post['thread_id'], publication_key=selection['publication_key'],
                   thread_id=post['thread_id'], trigger=selection['suggested_trigger'],
                   intended_outcome='no_send', outcome='failed_uncertain' if uncertain else 'recorded_only',
                   discovered_on=selection['discovered_on'], recorded_at=recorded_at,
                   delivery_authority_reference=None, suppression_reason=None,
                   post_reference=None, reconciliation_required=uncertain, revision=revision)
    result = dict(thread_id=post['thread_id'], publication_key=selection['publication_key'],
                  canonical_key=selection['canonical_key'], source_aliases=aliases,
                  render_input=deepcopy(selection), rendered_post=post, delivery_receipt=receipt,
                  revision=revision, dispatch_state='reconciliation_required' if uncertain else 'no_send',
                  human_notes=human_notes, input_fingerprint=fingerprint(selection),
                  native_input_reference=native_input_reference)
    return validate_thread(result)


def validate_thread(record):
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise ValueError('Exact logical thread record required')
    if record['rendered_post'] != render_post_body(record['render_input']):
        raise ValueError('Saved post differs from deterministic renderer')
    if type(record['revision']) is not int or record['revision'] < 1:
        raise ValueError('Positive thread revision required')
    if record['thread_id'] != stable_thread_id(record['publication_key']):
        raise ValueError('Thread identity differs')
    source = record['render_input']
    for field in ['publication_key', 'canonical_key']:
        if record[field] != source[field]:
            raise ValueError('Render/mapping identity differs')
    aliases = record['source_aliases']
    if not isinstance(aliases, list) or any(not isinstance(a, str) for a in aliases):
        raise ValueError('Stable source aliases must be text')
    if aliases != sorted(set(aliases)) or record['publication_key'] not in aliases:
        raise ValueError('Complete stable source aliases required')
    for alias in aliases:
        publication_source_key(alias)
    receipt = validate_delivery_receipt(record['delivery_receipt'])
    if (receipt['intended_outcome'] != 'no_send' or receipt['post_reference'] is not None
            or receipt['delivery_authority_reference'] is not None
            or receipt['revision'] != record['revision']
            or receipt['thread_id'] != record['thread_id']
            or receipt['receipt_id'] != record['thread_id']
            or receipt['publication_key'] != record['publication_key']
            or receipt['discovered_on'] != source['discovered_on']
            or receipt['trigger'] != source['suggested_trigger']):
        raise ValueError('No-send receipt/mapping binding differs')
    state = 'reconciliation_required' if receipt['outcome'] == 'failed_uncertain' else 'no_send'
    if receipt['outcome'] not in {'recorded_only', 'failed_uncertain'} or record['dispatch_state'] != state:
        raise ValueError('Provider uncertainty must block dispatch')
    if record['input_fingerprint'] != fingerprint(source):
        raise ValueError('Selection fingerprint differs')
    if record['human_notes'] is not None and not isinstance(record['human_notes'], str):
        raise ValueError('Human notes must be retained text or null')
    _required_identifier(record['native_input_reference'], 'native_input_reference')
    return deepcopy(record)


def transition_thread(before, after):
    before, after = validate_thread(before), validate_thread(after)
    if before == after:
        return 'unchanged'
    if before['dispatch_state'] == 'reconciliation_required':
        raise ValueError('Uncertain provider outcome requires independent reconciliation; no resend')
    for field in ['thread_id', 'publication_key', 'canonical_key', 'human_notes']:
        if before[field] != after[field]:
            raise ValueError('Prior identity/human edits must be preserved')
    if not set(before['source_aliases']) <= set(after['source_aliases']):
        raise ValueError('Historical source aliases cannot be removed')
    if after['revision'] != before['revision'] + 1:
        raise ValueError('Stale/conflicting thread revision')
    if _parse_aware_instant(after['delivery_receipt']['recorded_at'], 'recorded_at') < _parse_aware_instant(before['delivery_receipt']['recorded_at'], 'recorded_at'):
        raise ValueError('Receipt revision chronology moved backwards')
    return 'update'
