"""Promotion preparation and source-change invalidation; no service I/O.

Canonical execution is deliberately absent. Review history is retained in the
returned journal and native version/preimage receipts, never silently replaced.
"""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy
import hashlib
import json
from scripts.grants_reviewed_classification import FIELDS, reviewed_mapping, apply_mapping
from scripts.grants_registry import sharepoint_field_map


def inspect_classification(record, raw):
    """Separate classification currency from substantive opportunity approval."""
    if not isinstance(record, dict):
        raise ValueError('Classification record must be an object')
    try:
        decision = json.loads(record.get('ClassificationEvidenceJSON') or '{}')
        expected = reviewed_mapping(record, raw)
        valid = (decision == expected and record.get('FunderKey') == decision['FunderKey']
                 and json.loads(record.get('CategoryKeysJSON') or '[]') == decision['CategoryKeys'])
    except (ValueError, TypeError, KeyError, AttributeError):
        valid = False
    return {'classification_current': valid,
            'opportunity_reviewed': record.get('ReviewStatus') == 'Reviewed',
            'delivery_ready': False,
            'reason': 'current_source_codes' if valid else 'classification_review_required'}


def invalidate_source_change(previous, current, previous_raw, current_raw):
    if (not isinstance(current, dict) or not isinstance(current_raw, bytes)
            or not isinstance(current.get('EvidenceHash'), str)
            or len(current['EvidenceHash']) != 64
            or any(c not in '0123456789abcdef' for c in current['EvidenceHash'])):
        raise ValueError('Typed current source record/hash and exact response bytes required')
    if not inspect_classification(previous, previous_raw)['classification_current']:
        raise ValueError('Verified previous classification required')
    for field in ('OpportunityKey', 'Source', 'SourceID', 'RoundID'):
        if previous.get(field) != current.get(field):
            raise ValueError('Cross-opportunity source replacement refused')
    expected_prior = {field: previous[field] for field in FIELDS}
    if any(current.get(field) != value for field, value in expected_prior.items()):
        raise ValueError('Concurrent classification edit requires reconciliation')
    changed = (previous['EvidenceHash'] != current.get('EvidenceHash')
               or hashlib.sha256(previous_raw).digest() != hashlib.sha256(current_raw).digest())
    if not changed:
        return {'state': 'unchanged', 'record': copy.deepcopy(current), 'journal': None}
    archive = json.loads(previous['ClassificationEvidenceJSON'])
    invalidation = {'format': 'rims-classification-invalidated-v1', 'OpportunityKey': current['OpportunityKey'],
                    'source_evidence_hash': current.get('EvidenceHash'),
                    'source_response_sha256': hashlib.sha256(current_raw).hexdigest(),
                    'previous_mapping': archive, 'reason': 'source_changed_requires_classification_review'}
    record = copy.deepcopy(current)
    record.update(FunderKey=None, CategoryKeysJSON='[]',
                  ClassificationEvidenceJSON=json.dumps(invalidation, sort_keys=True, separators=(',', ':')))
    return {'state': 'classification_review_required', 'record': record,
            'journal': {'previous': expected_prior, 'invalidation': invalidation}}


def review_invalidated(record, raw):
    if not isinstance(record, dict) or not isinstance(raw, bytes):
        raise ValueError('Typed invalidated record and exact response bytes required')
    invalidation = json.loads(record.get('ClassificationEvidenceJSON') or '{}')
    if (not isinstance(invalidation, dict)
            or invalidation.get('format') != 'rims-classification-invalidated-v1'
            or invalidation.get('OpportunityKey') != record.get('OpportunityKey')
            or invalidation.get('source_evidence_hash') != record.get('EvidenceHash')
            or invalidation.get('source_response_sha256') != hashlib.sha256(raw).hexdigest()
            or not isinstance(invalidation.get('previous_mapping'), dict)
            or record.get('FunderKey') is not None or record.get('CategoryKeysJSON') != '[]'):
        raise ValueError('Exact invalidation preimage required before replacement review')
    mapping = reviewed_mapping(record, raw)
    clean = {k: v for k, v in record.items() if k not in FIELDS}
    result = apply_mapping(clean, mapping, raw)
    return {'state': 'source_codes_reviewed', 'record': result,
            'journal': {'previous_invalidation': invalidation, 'reviewed_mapping': mapping}}


def classified_projection(record, raw):
    if not inspect_classification(record, raw)['classification_current']:
        raise ValueError('Stale or unsupported classification cannot enter downstream projection')
    return {**sharepoint_field_map(record), **{k: record[k] for k in FIELDS}}


def promotion_candidate(*args, **kwargs):
    raise ValueError('Schema/model promotion is outside this source-only classification packet')
