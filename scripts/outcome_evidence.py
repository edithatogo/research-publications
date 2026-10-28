"""Pure fictional/authorised aggregate evidence validation and revision projection.

No store, I/O, identity resolution, review decision, source acquisition or native
persistence. Caller-owned immutable revisions retain exact source fingerprints.
Projection eligibility is technical completeness, not a finding of real impact.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
import json
import math
import re

STATUSES = {'unverified', 'verified', 'disputed', 'withdrawn'}
VALUE_STATES = {'available', 'confirmed_zero', 'unavailable', 'not_applicable',
                'not_yet_observable', 'suppressed'}
REQUIREMENTS = {'numerator_denominator', 'comparator', 'baseline', 'follow_up', 'uncertainty', 'method'}
COMPONENTS = {'estimate', 'numerator', 'denominator', 'comparator', 'baseline',
              'follow_up', 'uncertainty', 'method'}
BASE = {'kind', 'id', 'revision_id', 'supersedes', 'project_ids', 'population_id',
        'setting_id', 'evidence', 'contributor', 'recorded_at', 'verification',
        'authorized_aggregate', 'source_snapshot'}
IMMUTABLE_EDITS = {'kind', 'id', 'revision_id', 'supersedes', 'recorded_at', 'indicator', 'source_snapshot'}


@dataclass(frozen=True)
class Revision:
    kind: str
    record_id: str
    revision_id: str
    supersedes: str | None
    source_sha256: str
    source_json: str
    effective_json: str
    protected_fields: tuple[str, ...]
    indicator_json: str | None
    references_sha256: str


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _text(value):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError('Nonempty exact text/reference required')
    return value


def _keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError('Incomplete or unknown record/contract fields')


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Exact SHA256 required')


def _utc(value):
    _text(value)
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError('Explicit UTC timestamp required')
    return parsed


def _number(value, *, nonnegative=False):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid or (nonnegative and value < 0):
        raise ValueError('Finite numeric aggregate required; booleans are not numbers')


def _date(value):
    if not isinstance(value, dict) or set(value) != {'value', 'precision', 'reason'}:
        raise ValueError('Explicit date value/precision/reason required')
    precision, raw = value['precision'], value['value']
    if precision == 'unknown':
        if raw is not None:
            raise ValueError('Unknown date must not contain an invented value')
        _text(value['reason']); return False
    patterns = {'day': r'\d{4}-\d{2}-\d{2}', 'month': r'\d{4}-\d{2}', 'year': r'\d{4}'}
    if not isinstance(precision, str) or precision not in patterns or not isinstance(raw, str) or not re.fullmatch(patterns[precision], raw):
        raise ValueError('Date precision does not match its supplied value')
    # Calendar checking only; partial dates are never expanded in a projection.
    date.fromisoformat(raw if precision == 'day' else raw+'-01' if precision == 'month' else raw+'-01-01')
    if value['reason'] is not None: _text(value['reason'])
    return True


def _period(value):
    _keys(value, {'start', 'end'})
    start, end = _date(value['start']), _date(value['end'])
    same = value['start']['precision'] == value['end']['precision']
    if start and end and same and value['start']['value'] > value['end']['value']:
        raise ValueError('Observation period is reversed')
    return start and end and same


def _reference_index(references):
    """Validate only the supplied technical reference subset, not a new catalogue."""
    _keys(references, {'snapshot_id', 'projects', 'populations', 'settings', 'methods',
                       'evidence', 'indicators', 'comparators', 'baselines'})
    _text(references['snapshot_id'])
    result = {}
    for key in ('projects', 'populations', 'settings', 'methods'):
        values = references[key]
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            raise ValueError('Explicit canonical reference lists required')
        for value in values: _text(value)
        if len(values) != len(set(values)): raise ValueError('Duplicate canonical reference')
        result[key] = set(values)
    for key in ('evidence', 'indicators', 'comparators', 'baselines'):
        if not isinstance(references[key], list): raise ValueError('Versioned reference list required')
        result[key] = {}
        for value in references[key]:
            if key == 'evidence':
                _keys(value, {'id', 'revision', 'source_id', 'source_revision', 'sha256', 'reference', 'status'})
                for field in ('id', 'revision', 'source_id', 'source_revision', 'reference'): _text(value[field])
                _hash(value['sha256'])
                if not isinstance(value['status'], str) or value['status'] not in STATUSES: raise ValueError('Unknown evidence state')
                identity = (value['id'], value['revision'])
            elif key == 'indicators':
                _keys(value, {'id', 'version', 'unit', 'requirements'})
                for field in ('id', 'version', 'unit'): _text(value[field])
                _keys(value['requirements'], REQUIREMENTS)
                if any(type(v) is not bool for v in value['requirements'].values()):
                    raise ValueError('Indicator requirements must be explicit booleans')
                identity = (value['id'], value['version'])
            else:
                _keys(value, {'id', 'version'})
                identity = (_text(value['id']), _text(value['version']))
            if identity in result[key]: raise ValueError('Duplicate versioned reference')
            result[key][identity] = copy.deepcopy(value)
    return result


def _component(name, component, index):
    _keys(component, {'state', 'value', 'reason'})
    state, value = component['state'], component['value']
    if not isinstance(state, str) or state not in VALUE_STATES: raise ValueError('Unknown availability state')
    if state not in {'available', 'confirmed_zero'}:
        if value is not None: raise ValueError('Unavailable/not-applicable evidence cannot carry a numeric substitute')
        _text(component['reason']); return
    if component['reason'] is not None: _text(component['reason'])
    if name in {'estimate', 'numerator', 'denominator'}:
        _number(value, nonnegative=name == 'denominator')
        if (value == 0) != (state == 'confirmed_zero'):
            raise ValueError('Zero requires explicit confirmed_zero, not missing evidence')
    elif state == 'confirmed_zero':
        raise ValueError('confirmed_zero is only for numeric aggregates')
    elif name in {'baseline', 'comparator'}:
        _keys(value, {'id', 'version'})
        if (_text(value['id']), _text(value['version'])) not in index[name+'s']:
            raise ValueError('Invalid canonical '+name+' reference')
    elif name == 'follow_up':
        _keys(value, {'amount', 'unit', 'anchor'})
        _number(value['amount'], nonnegative=True); _text(value['unit']); _date(value['anchor'])
    elif name == 'method':
        if _text(value) not in index['methods']: raise ValueError('Invalid method reference')
    else:
        _text(value)  # Source-supplied uncertainty; no generated interval or verdict.


def _validate(record, index, history):
    if not isinstance(record, dict): raise ValueError('One structured source record required')
    kind = record.get('kind')
    extra = {'event_type', 'change_description', 'event_date'} if kind == 'TranslationEvent' else (
        {'event_id', 'indicator', 'period', 'unit', 'contribution_explanation', 'limitations'} | COMPONENTS
        if kind == 'OutcomeObservation' else None)
    if extra is None: raise ValueError('Unknown evidence grain')
    _keys(record, BASE | extra)
    for field in ('id', 'revision_id', 'contributor', 'source_snapshot'): _text(record[field])
    if record['supersedes'] is not None: _text(record['supersedes'])
    _utc(record['recorded_at'])
    if type(record['authorized_aggregate']) is not bool: raise ValueError('Explicit aggregate authorisation flag required')
    for field, pool in [('population_id', 'populations'), ('setting_id', 'settings')]:
        if _text(record[field]) not in index[pool]: raise ValueError('Invalid canonical '+field)
    projects = record['project_ids']
    if (not isinstance(projects, list) or any(not isinstance(p, str) or p not in index['projects'] for p in projects)
            or len(projects) != len(set(projects))):
        raise ValueError('Invalid/duplicate canonical project references')
    verification = record['verification']
    _keys(verification, {'status', 'verifier', 'verified_at'})
    if not isinstance(verification['status'], str) or verification['status'] not in STATUSES: raise ValueError('Unknown verification state')
    if verification['status'] == 'verified' or verification['verifier'] is not None or verification['verified_at'] is not None:
        _text(verification['verifier'])
        if _utc(verification['verified_at']) > _utc(record['recorded_at']):
            raise ValueError('Verification cannot postdate this recorded revision')
    evidence = record['evidence']
    if not isinstance(evidence, list): raise ValueError('Explicit evidence revision list required')
    identities = set()
    for ref in evidence:
        _keys(ref, {'id', 'revision', 'source_id', 'source_revision', 'sha256', 'reference'})
        identity = (_text(ref['id']), _text(ref['revision']))
        expected = index['evidence'].get(identity)
        if expected is None or ref != {k: v for k, v in expected.items() if k != 'status'}:
            raise ValueError('Invalid evidence/source revision or fingerprint/reference')
        if identity in identities: raise ValueError('Duplicate evidence revision')
        identities.add(identity)
    if kind == 'TranslationEvent':
        if not projects: raise ValueError('TranslationEvent requires canonical projects')
        _text(record['event_type']); _text(record['change_description']); _date(record['event_date'])
        return None
    _keys(record['indicator'], {'id', 'version'})
    identity = (_text(record['indicator']['id']), _text(record['indicator']['version']))
    indicator = index['indicators'].get(identity)
    if indicator is None: raise ValueError('Invalid indicator revision')
    if record['unit'] != indicator['unit']: raise ValueError('Indicator unit mismatch; no implicit conversion')
    event = record['event_id']
    if event is not None and (_text(event) not in {r.record_id for r in history if r.kind == 'TranslationEvent'}):
        raise ValueError('Invalid canonical event reference')
    if event is None and not projects: raise ValueError('OutcomeObservation requires event or project references')
    _period(record['period'])
    for field in ('contribution_explanation', 'limitations'): _text(record[field])
    for name in COMPONENTS: _component(name, record[name], index)
    return indicator


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('Duplicate source JSON key')
        result[key] = value
    return result


def _constant(_): raise ValueError('Non-finite source JSON constant')


def _history(history):
    """Require the caller-retained revision chain; never silently repair forks."""
    history = tuple(history); seen, current = set(), {}
    for revision in history:
        if not isinstance(revision, Revision) or revision.revision_id in seen:
            raise ValueError('Invalid or duplicate revision history')
        seen.add(revision.revision_id)
        source, effective = json.loads(revision.source_json), json.loads(revision.effective_json)
        expected = {'kind': revision.kind, 'id': revision.record_id,
                    'revision_id': revision.revision_id, 'supersedes': revision.supersedes}
        if any(record.get(k) != v for record in (source, effective) for k, v in expected.items()):
            raise ValueError('History identity drift')
        identity = (revision.kind, revision.record_id); prior = current.get(identity)
        if revision.supersedes != (prior.revision_id if prior else None):
            raise ValueError('History supersession chain is incomplete or reordered')
        if prior and _utc(effective['recorded_at']) < _utc(json.loads(prior.effective_json)['recorded_at']):
            raise ValueError('History recorded time regressed')
        _hash(revision.source_sha256); _hash(revision.references_sha256)
        current[identity] = revision
    return history


def intake(history, source, references, *, human_edits=None):
    """Return a new revision tuple/receipt; failures never mutate supplied inputs.

    Human edits are explicit caller inputs, not generated assessments. Their
    values carry forward while the raw source field is unchanged. Conflicting
    upstream edits fail unless that field is explicitly resolved in human_edits
    on a new revision. Source/effective JSON and superseded revisions survive.
    """
    history = _history(history)
    if not isinstance(source, bytes): raise ValueError('Exact source bytes required')
    record = json.loads(source.decode('utf-8'), object_pairs_hook=_unique_object, parse_constant=_constant)
    index = _reference_index(references)
    _validate(record, index, history)
    edits = {} if human_edits is None else copy.deepcopy(human_edits)
    if not isinstance(edits, dict) or not set(edits) <= set(record)-IMMUTABLE_EDITS:
        raise ValueError('Human edits cannot change source/revision identity')
    fingerprint = hashlib.sha256(source).hexdigest()
    matching = next((r for r in history if r.revision_id == record['revision_id']), None)
    if matching is not None:
        if (matching.kind != record['kind'] or matching.record_id != record['id'] or
                matching.source_sha256 != fingerprint or
                any(json.loads(matching.effective_json)[key] != value for key, value in edits.items())):
            raise ValueError('Revision identity conflict; retain prior history')
        return history, {'status': 'unchanged_replay', 'source_sha256': fingerprint}
    prior = next((r for r in reversed(history) if (r.kind, r.record_id) == (record['kind'], record['id'])), None)
    if record['supersedes'] != (prior.revision_id if prior else None):
        raise ValueError('Supersession must name the exact current revision; no stale fork')
    effective = copy.deepcopy(record); protected = set()
    if prior:
        previous_source, previous = json.loads(prior.source_json), json.loads(prior.effective_json)
        if _utc(record['recorded_at']) < _utc(previous['recorded_at']): raise ValueError('Recorded revision time regressed')
        protected.update(prior.protected_fields)
        for field in protected:
            if field not in edits and record[field] != previous_source[field] and record[field] != previous[field]:
                raise ValueError('Protected human edit conflict: '+field)
            effective[field] = previous[field]
    effective.update(edits); protected.update(edits)
    indicator = _validate(effective, index, history)
    # The same version must never quietly acquire different indicator semantics
    # or evidence/source metadata; a new explicit version is required.
    for old in history:
        previous = json.loads(old.effective_json)
        if indicator and old.indicator_json and previous.get('indicator') == effective['indicator'] and old.indicator_json != _json(indicator):
            raise ValueError('Indicator definition changed without a new version')
        for ref in effective['evidence']:
            for previous_ref in previous['evidence']:
                if (ref['id'], ref['revision']) == (previous_ref['id'], previous_ref['revision']) and ref != previous_ref:
                    raise ValueError('Evidence/source metadata changed without a new revision')
    revision = Revision(record['kind'], record['id'], record['revision_id'], record['supersedes'],
                        fingerprint, _json(record), _json(effective), tuple(sorted(protected)),
                        _json(indicator) if indicator else None,
                        hashlib.sha256(_json(references).encode()).hexdigest())
    return history+(revision,), {'status': 'new_revision', 'source_sha256': fingerprint,
                                'protected_fields': list(revision.protected_fields)}


def project(history, references, *, cutoff_utc, source_snapshot, model_revision, report_revision):
    """Project authorised source aggregates at their own grain; never pool effects.

    No averages of percentages, inferred comparable cohorts or causal verdicts.
    Consumers retain this result plus its exact reference snapshot for historical
    reconstruction; missing/revised references cause unavailability, not fallback.
    """
    history = _history(history); index = _reference_index(references); cutoff = _utc(cutoff_utc)
    for value in (source_snapshot, model_revision, report_revision): _text(value)
    visible = [r for r in history if _utc(json.loads(r.effective_json)['recorded_at']) <= cutoff]
    selected = {(r.kind, r.record_id): r for r in visible}
    reasons = {}
    for identity, revision in selected.items():
        record = json.loads(revision.effective_json); issues = []
        try:
            indicator = _validate(record, index, visible)
            if indicator and revision.indicator_json != _json(indicator): issues.append('indicator_definition_drift')
        except ValueError as error:
            issues.append('reference_or_contract_unavailable: '+str(error)); indicator = None
        if not record['authorized_aggregate']: issues.append('aggregate_not_authorized')
        if record['verification']['status'] != 'verified': issues.append('verification_'+record['verification']['status'])
        if not record['evidence']: issues.append('required_evidence_unavailable')
        for ref in record['evidence']:
            status = index['evidence'].get((ref['id'], ref['revision']), {}).get('status')
            if status != 'verified': issues.append('evidence_'+str(status))
        if record['kind'] == 'OutcomeObservation':
            if not _period(record['period']): issues.append('observation_period_unavailable')
            required = {'estimate'}
            if indicator:
                required |= {name for name in REQUIREMENTS-{'numerator_denominator'} if indicator['requirements'][name]}
                if indicator['requirements']['numerator_denominator']:
                    required |= {'numerator', 'denominator'}
                    if record['denominator']['state'] == 'confirmed_zero': issues.append('zero_eligible_denominator')
            for name in sorted(required):
                if record[name]['state'] not in {'available', 'confirmed_zero'}: issues.append(name+'_'+record[name]['state'])
            if 'follow_up' in required and record['follow_up']['state'] == 'available' and not _date(record['follow_up']['value']['anchor']):
                issues.append('follow_up_anchor_unavailable')
        reasons[identity] = issues
    for identity, revision in selected.items():
        record = json.loads(revision.effective_json)
        if revision.kind == 'OutcomeObservation' and record['event_id'] is not None:
            event = ('TranslationEvent', record['event_id'])
            if event not in selected or reasons[event]: reasons[identity].append('linked_event_unavailable')
    event_facts, event_projects, outcome_aggregates, observation_projects, details = [], [], [], [], []
    for revision in visible:
        record = json.loads(revision.effective_json); identity = (revision.kind, revision.record_id)
        current = selected[identity].revision_id == revision.revision_id
        issues = reasons[identity] if current else ['superseded_revision']
        detail = {'kind': revision.kind, 'id': revision.record_id, 'revision_id': revision.revision_id,
                  'supersedes': revision.supersedes, 'selected_as_of_cutoff': current,
                  'verification_status': record['verification']['status'], 'eligible': current and not issues,
                  'unavailable_reasons': issues.copy(), 'source_sha256': revision.source_sha256,
                  'source_snapshot': record['source_snapshot'], 'references_sha256_at_intake': revision.references_sha256,
                  'evidence': [{k: v for k, v in ref.items() if k != 'reference'} for ref in record['evidence']]}
        if revision.kind == 'TranslationEvent':
            detail['event_date'] = copy.deepcopy(record['event_date']) if record['authorized_aggregate'] else None
            if detail['eligible']:
                event_facts.append({'event_id': revision.record_id, 'revision_id': revision.revision_id,
                                    'event_type': record['event_type'], 'event_date': copy.deepcopy(record['event_date'])})
                event_projects.extend({'event_id': revision.record_id, 'project_id': p} for p in record['project_ids'])
        else:
            detail['indicator'] = record['indicator'].copy(); detail['aggregate_values'] = None
            if record['authorized_aggregate']:
                detail['aggregate_values'] = {name: copy.deepcopy(record[name]) for name in COMPONENTS}
                detail.update(unit=record['unit'], period=copy.deepcopy(record['period']),
                              population_id=record['population_id'], setting_id=record['setting_id'],
                              event_id=record['event_id'], project_ids=record['project_ids'].copy())
            if detail['eligible']:
                outcome_aggregates.append({'observation_id': revision.record_id, 'revision_id': revision.revision_id,
                    'indicator': record['indicator'].copy(), 'unit': record['unit'], 'event_id': record['event_id'],
                    'population_id': record['population_id'], 'setting_id': record['setting_id'],
                    'period': copy.deepcopy(record['period']), 'components': copy.deepcopy(detail['aggregate_values'])})
                observation_projects.extend({'observation_id': revision.record_id, 'project_id': p} for p in record['project_ids'])
        details.append(detail)
    return {'context': {'cutoff_utc': cutoff_utc, 'source_snapshot': source_snapshot,
                        'reference_snapshot': references['snapshot_id'],
                        'references_sha256': hashlib.sha256(_json(references).encode()).hexdigest(),
                        'model_revision': model_revision, 'report_revision': report_revision},
            'eligible_translation_event_count': len(event_facts), 'translation_events': event_facts,
            'translation_event_dates_unknown': sum(e['event_date']['precision'] == 'unknown' for e in event_facts),
            'event_project_bridge': event_projects, 'outcome_aggregates': outcome_aggregates,
            'observation_project_bridge': observation_projects,
            'unavailable_current_records': sum(bool(value) for value in reasons.values()),
            'details': details, 'native_persistence_proved': False}
