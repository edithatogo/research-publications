# SPDX-License-Identifier: Apache-2.0
"""Pure E09 no-send workflow previews. No authentication, storage or dispatch.

Actor/access and revision arguments must come from a trusted native adapter,
never from form fields. These local guards do not prove tenant authorization or
provide an atomic update. Native adoption requires fresh ETag/access readback.
"""
from copy import deepcopy
from hashlib import sha256
import json
from scripts.e09_feed_contracts import (
    _required_identifier, _positive_int, _parse_aware_instant,
    validate_contribution_record, validate_subscription_preference,
)


def _fingerprint(kind, payload):
    return sha256(json.dumps({'kind': kind, 'payload': payload}, sort_keys=True,
        separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def validate_no_send_preview(value):
    """Validate prepared data only; this does not establish actor/access proof."""
    if (not isinstance(value, dict) or set(value) != {'kind','preview_key','payload','intended_outcome','native_write'}
            or value['intended_outcome'] != 'no_send' or value['native_write'] is not False):
        raise ValueError('Exact no-send preview required')
    kind, payload = value['kind'], value['payload']
    if not isinstance(kind, str) or not isinstance(payload, dict):
        raise ValueError('Typed preview kind/payload required')
    if kind == 'contribution':
        record = validate_contribution_record(deepcopy(payload))
        if record['status'] != 'submitted' or record['contributor_id_kind'] != 'authenticated':
            raise ValueError('Submission preview cannot contain a curator decision')
    elif kind == 'curator_decision':
        if set(payload) != {'contribution','curator_urn','decision','rationale','decided_at',
                            'expected_etag','canonical_write','requires_authorised_update_path'}:
            raise ValueError('Exact curator preview required')
        contribution = validate_contribution_record(deepcopy(payload['contribution']))
        if contribution['status'] not in {'submitted','unresolved'}:
            raise ValueError('Prior curator decision must be retained')
        decision = payload['decision']
        if (not isinstance(decision, str) or decision not in {'accept','amend','reject','unresolved'}
                or payload['canonical_write'] is not False
                or payload['requires_authorised_update_path'] is not (decision in {'accept','amend'})):
            raise ValueError('Curator preview cannot grant canonical write authority')
        for field in ['curator_urn','rationale','expected_etag']:
            _required_identifier(payload[field], field)
        if payload['expected_etag'] == '*':
            raise ValueError('Concrete native ETag required')
        if _parse_aware_instant(payload['decided_at'], 'decided_at').date().isoformat() < contribution['submitted_on']:
            raise ValueError('Decision predates submission')
    elif kind == 'subscription_preference':
        if set(payload) != {'before','after'}:
            raise ValueError('Exact preference preview required')
        before, after = (validate_subscription_preference(deepcopy(payload[k])) for k in ['before','after'])
        if (after['delivery_authority_active'] is not False or after['delivery_authority_reference'] is not None
                or after['revision'] != before['revision'] + 1
                or any(after[k] != before[k] for k in ['subscription_id','subscriber_urn','enrolled_on','contact_route'])
                or after['revised_on'] < before['revised_on']):
            raise ValueError('Preference preview cannot grant delivery or overwrite identity/history')
    elif kind == 'grounded_advisory':
        if (set(payload) != {'source_fingerprint','source_revision','prompt_revision','suggestions','authoritative','manual_operation_available'}
                or payload['authoritative'] is not False or payload['manual_operation_available'] is not True):
            raise ValueError('Advisory preview is non-authoritative data only')
        _positive_int(payload['source_revision'], 'source_revision')
        _positive_int(payload['prompt_revision'], 'prompt_revision')
        source_hash = payload['source_fingerprint']
        if not isinstance(source_hash, str) or len(source_hash) != 64 or any(c not in '0123456789abcdef' for c in source_hash):
            raise ValueError('Exact source fingerprint required')
        suggestions = payload['suggestions']
        if not isinstance(suggestions, list) or not 1 <= len(suggestions) <= 20:
            raise ValueError('Bounded advisory suggestions required')
        for item in suggestions:
            if not isinstance(item, dict) or set(item) != {'kind','suggestion','excerpt'}:
                raise ValueError('Exact inert advisory fields required')
            if not isinstance(item['kind'], str) or item['kind'] not in {'topic','study_design','population','location','affiliation','trial_identifier','grant_identifier'}:
                raise ValueError('Unsupported advisory kind')
            _required_identifier(item['suggestion'], 'suggestion')
            _required_identifier(item['excerpt'], 'excerpt')
            if item['kind'] in {'trial_identifier','grant_identifier'} and item['suggestion'] not in item['excerpt']:
                raise ValueError('Identifier must be explicitly stated in excerpt')
    else:
        raise ValueError('Unsupported preview kind')
    if value['preview_key'] != _fingerprint(kind, payload):
        raise ValueError('Preview fingerprint differs')
    return deepcopy(value)


def _preview(kind, payload):
    payload = deepcopy(payload)
    return validate_no_send_preview({'kind': kind, 'preview_key': _fingerprint(kind, payload),
        'payload': payload, 'intended_outcome': 'no_send', 'native_write': False})


def contribution_preview(record, *, actor_urn, current_source_revision,
                         current_project_revision):
    """Bind a submission to a trusted actor and exact current revisions."""
    record = validate_contribution_record(deepcopy(record))
    actor = _required_identifier(actor_urn, 'actor_urn')
    if record['contributor_id_kind'] != 'authenticated' or record['contributor_urn'] != actor:
        raise ValueError('Authenticated contributor must match trusted actor')
    if record['status'] != 'submitted':
        raise ValueError('Submission cannot contain a curator decision')
    if (record['source_revision'] != _positive_int(current_source_revision, 'current_source_revision')
            or record['submitted_at_project_revision'] != _positive_int(current_project_revision, 'current_project_revision')):
        raise ValueError('Stale contribution requires reconciliation')
    return _preview('contribution', record)


def curator_preview(record, *, actor_urn, allowed_curators, decision,
                    rationale, decided_at, current_source_revision,
                    current_project_revision, current_etag):
    """Prepare append-only decision evidence; never mutate accepted fields."""
    record = validate_contribution_record(deepcopy(record))
    actor = _required_identifier(actor_urn, 'actor_urn')
    if not isinstance(allowed_curators, (list, tuple, set)) or actor not in allowed_curators:
        raise ValueError('Trusted curator access required')
    if record['status'] not in {'submitted', 'unresolved'}:
        raise ValueError('Prior decision must be retained; reconcile a new revision')
    if (record['source_revision'] != _positive_int(current_source_revision, 'current_source_revision')
            or record['submitted_at_project_revision'] != _positive_int(current_project_revision, 'current_project_revision')):
        raise ValueError('Stale decision requires reconciliation')
    if not isinstance(decision, str) or decision not in {'accept', 'amend', 'reject', 'unresolved'}:
        raise ValueError('Unsupported curator decision')
    instant = _parse_aware_instant(decided_at, 'decided_at')
    if instant.date().isoformat() < record['submitted_on']:
        raise ValueError('Decision predates submission')
    etag = _required_identifier(current_etag, 'current_etag')
    if etag == '*':
        raise ValueError('Concrete native ETag required')
    return _preview('curator_decision', {
        'contribution': record, 'curator_urn': actor, 'decision': decision,
        'rationale': _required_identifier(rationale, 'rationale'),
        'decided_at': decided_at, 'expected_etag': etag,
        'canonical_write': False, 'requires_authorised_update_path': decision in {'accept', 'amend'},
    })


def preference_preview(record, *, actor_urn, expected_revision, cadence,
                       status, revised_on):
    """Prepare self-service preference revision, retaining enrolment/history."""
    before = validate_subscription_preference(deepcopy(record))
    if before['subscriber_urn'] != _required_identifier(actor_urn, 'actor_urn'):
        raise ValueError('Subscriber must match trusted actor')
    if before['revision'] != _positive_int(expected_revision, 'expected_revision'):
        raise ValueError('Stale preference requires reconciliation')
    after = {**before, 'revision': before['revision'] + 1, 'cadence': cadence,
             'status': status, 'revised_on': revised_on,
             'delivery_authority_active': False, 'delivery_authority_reference': None}
    after = validate_subscription_preference(after)
    if after['revised_on'] < before['revised_on']:
        raise ValueError('Preference revision cannot move backwards')
    return _preview('subscription_preference', {'before': before, 'after': after})


def grounded_advisory_preview(*, source_text, source_fingerprint,
                              source_revision, prompt_revision, suggestions):
    """Check exact excerpts from retained text; performs no AI extraction.

    Hostile text is inert source data. Grounding proves excerpt presence only,
    never the truth of an inference or its relationship to an entity.
    """
    if not isinstance(source_text, str) or not source_text:
        raise ValueError('Retained source text required')
    actual = sha256(source_text.encode()).hexdigest()
    if actual != source_fingerprint:
        raise ValueError('Source fingerprint mismatch')
    _positive_int(source_revision, 'source_revision')
    _positive_int(prompt_revision, 'prompt_revision')
    if not isinstance(suggestions, list) or not 1 <= len(suggestions) <= 20:
        raise ValueError('One to twenty grounded suggestions required')
    for item in suggestions:
        if not isinstance(item, dict) or set(item) != {'kind', 'suggestion', 'excerpt'}:
            raise ValueError('Exact suggestion fields required')
        if not isinstance(item['kind'], str) or item['kind'] not in {'topic', 'study_design', 'population', 'location', 'affiliation', 'trial_identifier', 'grant_identifier'}:
            raise ValueError('Unsupported advisory kind')
        _required_identifier(item['suggestion'], 'suggestion')
        excerpt = _required_identifier(item['excerpt'], 'excerpt')
        if excerpt not in source_text:
            raise ValueError('Excerpt absent from retained source')
        if item['kind'] in {'trial_identifier', 'grant_identifier'} and item['suggestion'] not in excerpt:
            raise ValueError('Identifier must be explicitly stated in excerpt')
    return _preview('grounded_advisory', {
        'source_fingerprint': actual, 'source_revision': source_revision,
        'prompt_revision': prompt_revision, 'suggestions': suggestions,
        'authoritative': False, 'manual_operation_available': True,
    })
