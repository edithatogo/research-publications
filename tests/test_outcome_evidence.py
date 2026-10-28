"""Explicitly FICTIONAL evidence only; no native stores, people or real outcomes."""
import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
import unittest
from scripts.outcome_evidence import intake, project


def encode(record): return json.dumps(record, sort_keys=True).encode()


def known(value): return {'value': value, 'precision': 'day', 'reason': None}


def value(number):
    return {'state': 'confirmed_zero' if number == 0 else 'available', 'value': number, 'reason': None}


def available(item): return {'state': 'available', 'value': item, 'reason': None}


def missing(state='unavailable', reason='FICTIONAL evidence not supplied'):
    return {'state': state, 'value': None, 'reason': reason}


def references():
    evidence = []
    for version in ('1', '2'):
        evidence.append({'id': 'FIC-EVIDENCE', 'revision': version, 'source_id': 'FIC-SOURCE',
                         'source_revision': version,
                         'sha256': hashlib.sha256(('FICTIONAL document '+version).encode()).hexdigest(),
                         'reference': 'fixture://fictional-evidence/'+version, 'status': 'verified'})
    return {'snapshot_id': 'FIC-REFERENCES-1', 'projects': ['FIC-P1', 'FIC-P2'],
            'populations': ['FIC-COHORT'], 'settings': ['FIC-SETTING'], 'methods': ['FIC-METHOD'],
            'evidence': evidence, 'comparators': [{'id': 'FIC-COMPARATOR', 'version': '1'}],
            'baselines': [{'id': 'FIC-BASELINE', 'version': '1'}],
            'indicators': [{'id': 'FIC-INDICATOR', 'version': version, 'unit': 'proportion',
                            'requirements': {name: True for name in ('numerator_denominator', 'comparator',
                                'baseline', 'follow_up', 'uncertainty', 'method')}} for version in ('1', '2')]}


def base(kind, record_id, revision_id):
    return {'kind': kind, 'id': record_id, 'revision_id': revision_id, 'supersedes': None,
            'project_ids': ['FIC-P1'], 'population_id': 'FIC-COHORT', 'setting_id': 'FIC-SETTING',
            'evidence': [{k: v for k, v in references()['evidence'][0].items() if k != 'status'}],
            'contributor': 'FIC-CONTRIBUTOR', 'recorded_at': '2026-01-03T10:00:00Z',
            'verification': {'status': 'verified', 'verifier': 'FIC-VERIFIER', 'verified_at': '2026-01-02T10:00:00Z'},
            'authorized_aggregate': True, 'source_snapshot': 'FIC-BATCH-1'}


def event():
    record = base('TranslationEvent', 'FIC-EVENT', 'FIC-T-R1')
    record.update(project_ids=['FIC-P1', 'FIC-P2'], event_type='fictional_practice_change',
                  change_description='FICTIONAL change description, no real benefit asserted',
                  event_date={'value': '2025-12', 'precision': 'month', 'reason': None})
    return record


def observation():
    record = base('OutcomeObservation', 'FIC-OBSERVATION', 'FIC-O-R1')
    record.update(event_id='FIC-EVENT', indicator={'id': 'FIC-INDICATOR', 'version': '1'},
        period={'start': known('2025-12-01'), 'end': known('2025-12-31')},
        estimate=value(.25), unit='proportion', numerator=value(5), denominator=value(20),
        comparator=available({'id': 'FIC-COMPARATOR', 'version': '1'}),
        baseline=available({'id': 'FIC-BASELINE', 'version': '1'}),
        follow_up=available({'amount': 6, 'unit': 'months', 'anchor': known('2025-06-01')}),
        uncertainty=available('FICTIONAL supplied interval 0.1 to 0.4'), method=available('FIC-METHOD'),
        contribution_explanation='FICTIONAL contribution, not causal attribution',
        limitations='FICTIONAL original source caveat')
    return record


def revised(record, revision_id, supersedes):
    result = copy.deepcopy(record)
    result.update(revision_id=revision_id, supersedes=supersedes,
                  recorded_at='2026-02-03T10:00:00Z', source_snapshot='FIC-BATCH-2')
    return result


def projection(history, refs=None, cutoff='2026-03-01T00:00:00Z'):
    return project(history, references() if refs is None else refs, cutoff_utc=cutoff,
                   source_snapshot='FIC-REPORT-SNAPSHOT', model_revision='FIC-MODEL-1', report_revision='FIC-REPORT-1')


class OutcomeEvidenceTests(unittest.TestCase):
    def initial(self, *, human_edits=None, obs=None):
        history, _ = intake((), encode(event()), references())
        history, _ = intake(history, encode(observation() if obs is None else obs), references(), human_edits=human_edits)
        return history

    def test_fictional_end_to_end_revision_replay_protected_edits_and_as_reported(self):
        refs = references(); before_refs = copy.deepcopy(refs)
        raw_event = encode(event())
        history, _ = intake((), raw_event, refs)
        raw = encode(observation())
        history, _ = intake(history, raw, refs, human_edits={'limitations': 'FICTIONAL protected human caveat'})
        original_projection = projection(history, refs)
        unchanged, receipt = intake(history, raw, refs)
        self.assertEqual(unchanged, history); self.assertEqual(receipt['status'], 'unchanged_replay')
        self.assertEqual(history[-1].source_sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(json.loads(history[-1].effective_json)['limitations'], 'FICTIONAL protected human caveat')
        update = revised(observation(), 'FIC-O-R2', 'FIC-O-R1')
        update.update(indicator={'id': 'FIC-INDICATOR', 'version': '2'}, estimate=value(.30), numerator=value(6),
                      evidence=[{k: v for k, v in refs['evidence'][1].items() if k != 'status'}])
        newer, _ = intake(history, encode(update), refs)
        current = projection(newer, refs)
        self.assertEqual(current['eligible_translation_event_count'], 1)
        self.assertEqual(len(current['event_project_bridge']), 2)  # One event, two explicit project contributions.
        self.assertEqual(len(current['outcome_aggregates']), 1)
        self.assertEqual(current['outcome_aggregates'][0]['components']['estimate']['value'], .30)
        self.assertEqual(len(current['observation_project_bridge']), 1)
        self.assertEqual(json.loads(newer[-1].effective_json)['limitations'], 'FICTIONAL protected human caveat')
        self.assertEqual(json.loads(newer[-2].effective_json)['estimate']['value'], .25)
        self.assertEqual(newer[-1].supersedes, 'FIC-O-R1')
        old = projection(newer, refs, cutoff='2026-01-15T00:00:00Z')
        self.assertEqual(old['outcome_aggregates'][0]['indicator']['version'], '1')
        self.assertEqual(original_projection['outcome_aggregates'][0]['components']['estimate']['value'], .25)
        self.assertEqual(intake(newer, raw, refs)[0], newer)  # Old replay never reactivates a superseded revision.
        self.assertEqual(refs, before_refs); self.assertFalse(current['native_persistence_proved'])
        with self.assertRaises(FrozenInstanceError): newer[-1].revision_id = 'overwrite'

    def test_failure_preserves_history_links_and_human_edits(self):
        history = self.initial(human_edits={'limitations': 'FICTIONAL human review caveat'})
        before = copy.deepcopy(history)
        bad = revised(observation(), 'FIC-O-R2', 'FIC-O-R1'); bad['limitations'] = 'upstream overwrite'
        with self.assertRaisesRegex(ValueError, 'Protected human edit conflict'):
            intake(history, encode(bad), references())
        self.assertEqual(history, before)
        bad = revised(observation(), 'FIC-O-R2', 'FIC-O-R1'); bad['project_ids'] = ['unregistered']
        with self.assertRaisesRegex(ValueError, 'canonical project'): intake(history, encode(bad), references())
        self.assertEqual(history, before)
        # An explicitly supplied new human edit is retained as a new revision, never overwrites history.
        good = revised(observation(), 'FIC-O-R2', 'FIC-O-R1')
        newer, _ = intake(history, encode(good), references(), human_edits={'limitations': 'FICTIONAL explicit new human caveat'})
        self.assertEqual(json.loads(history[-1].effective_json)['limitations'], 'FICTIONAL human review caveat')
        self.assertEqual(json.loads(newer[-1].effective_json)['limitations'], 'FICTIONAL explicit new human caveat')
        self.assertEqual(json.loads(newer[-1].effective_json)['evidence'], observation()['evidence'])

    def test_status_never_advanced_by_intake(self):
        record = event(); record['verification'] = {'status': 'unverified', 'verifier': None, 'verified_at': None}
        history, _ = intake((), encode(record), references())
        self.assertEqual(json.loads(history[0].effective_json)['verification']['status'], 'unverified')
        self.assertEqual(projection(history)['eligible_translation_event_count'], 0)
        bad = event(); bad['verification']['verifier'] = None
        with self.assertRaises(ValueError): intake((), encode(bad), references())

    def test_explicit_absent_evidence_retained_but_unavailable(self):
        obs = observation(); obs['evidence'] = []
        history = self.initial(obs=obs); result = projection(history)
        self.assertEqual(json.loads(history[-1].effective_json)['evidence'], [])
        self.assertEqual(result['outcome_aggregates'], [])
        self.assertIn('required_evidence_unavailable', result['details'][-1]['unavailable_reasons'])

    def test_project_only_observation_does_not_infer_an_event_or_extra_projects(self):
        obs = observation(); obs['event_id'] = None
        history, _ = intake((), encode(obs), references()); result = projection(history)
        self.assertEqual(result['eligible_translation_event_count'], 0)
        self.assertIsNone(result['outcome_aggregates'][0]['event_id'])
        self.assertEqual(result['observation_project_bridge'], [{'observation_id': 'FIC-OBSERVATION', 'project_id': 'FIC-P1'}])

    def test_human_evidence_links_survive_replay_and_source_convergence(self):
        linked = [{k: v for k, v in references()['evidence'][1].items() if k != 'status'}]
        history = self.initial(human_edits={'evidence': linked})
        replayed, _ = intake(history, encode(observation()), references())
        self.assertEqual(json.loads(replayed[-1].effective_json)['evidence'], linked)
        self.assertEqual(json.loads(replayed[-1].source_json)['evidence'], observation()['evidence'])
        converged = revised(observation(), 'FIC-O-R2', 'FIC-O-R1'); converged['evidence'] = linked
        newer, _ = intake(history, encode(converged), references())
        self.assertEqual(json.loads(newer[-1].effective_json)['evidence'], linked)
        self.assertEqual(history[-1].source_sha256, hashlib.sha256(encode(observation())).hexdigest())

    def test_disputed_and_withdrawn_revisions_remain_traceable_not_verified(self):
        for status in ('disputed', 'withdrawn'):
            with self.subTest(status=status):
                history = self.initial(); update = revised(observation(), 'FIC-O-R2', 'FIC-O-R1')
                update['verification']['status'] = status
                newer, _ = intake(history, encode(update), references()); result = projection(newer)
                self.assertEqual(result['outcome_aggregates'], [])
                current = next(d for d in result['details'] if d['revision_id'] == 'FIC-O-R2')
                self.assertIn('verification_'+status, current['unavailable_reasons'])
                self.assertEqual(current['verification_status'], status)
                self.assertEqual(len(result['details']), 3)
                self.assertTrue(any(d['revision_id'] == 'FIC-O-R1' and not d['selected_as_of_cutoff'] for d in result['details']))

    def test_withdrawn_event_excludes_linked_outcome_without_changing_its_status(self):
        history = self.initial(); update = revised(event(), 'FIC-T-R2', 'FIC-T-R1')
        update['verification']['status'] = 'withdrawn'; newer, _ = intake(history, encode(update), references())
        result = projection(newer)
        self.assertEqual(result['eligible_translation_event_count'], 0); self.assertEqual(result['outcome_aggregates'], [])
        obs = next(d for d in result['details'] if d['id'] == 'FIC-OBSERVATION')
        self.assertEqual(obs['verification_status'], 'verified'); self.assertIn('linked_event_unavailable', obs['unavailable_reasons'])
        self.assertEqual(len(projection(newer, cutoff='2026-01-15T00:00:00Z')['outcome_aggregates']), 1)

    def test_reference_withdrawal_and_missing_historical_evidence_do_not_fallback(self):
        history = self.initial(); old = projection(history)
        refs = references(); refs['snapshot_id'] = 'FIC-REFERENCES-2'; refs['evidence'][0]['status'] = 'withdrawn'
        result = projection(history, refs)
        self.assertEqual(result['outcome_aggregates'], []); self.assertEqual(result['eligible_translation_event_count'], 0)
        self.assertTrue(any('evidence_withdrawn' in d['unavailable_reasons'] for d in result['details']))
        refs['evidence'].pop(0); unavailable = projection(history, refs)
        self.assertEqual(unavailable['outcome_aggregates'], [])
        self.assertIn('reference_or_contract_unavailable', ' '.join(unavailable['details'][0]['unavailable_reasons']))
        self.assertNotEqual(old['context']['references_sha256'], result['context']['references_sha256'])
        self.assertEqual(len(old['outcome_aggregates']), 1)  # Retained output is never silently restated.
        refs = references(); refs['indicators'].pop(0)
        unavailable = projection(history, refs)
        self.assertEqual(unavailable['outcome_aggregates'], [])
        self.assertEqual(unavailable['details'][-1]['indicator']['version'], '1')

    def test_precise_partial_unknown_dates_and_incomplete_periods(self):
        record = event(); record['event_date'] = {'value': None, 'precision': 'unknown', 'reason': 'FICTIONAL date not supplied'}
        history, _ = intake((), encode(record), references()); result = projection(history)
        self.assertEqual(result['translation_event_dates_unknown'], 1)
        self.assertIsNone(result['translation_events'][0]['event_date']['value'])
        partial = projection(intake((), encode(event()), references())[0])['translation_events'][0]['event_date']
        self.assertEqual(partial['value'], '2025-12'); self.assertEqual(partial['precision'], 'month')
        year = event(); year['event_date'] = {'value': '2025', 'precision': 'year', 'reason': None}
        self.assertEqual(projection(intake((), encode(year), references())[0])['translation_events'][0]['event_date']['value'], '2025')
        obs = observation(); obs['period']['start'] = copy.deepcopy(record['event_date'])
        history, _ = intake(history, encode(obs), references())
        self.assertEqual(projection(history)['outcome_aggregates'], [])
        for invalid in [{'value': '2025-12-01', 'precision': 'month', 'reason': None},
                        {'value': '2025-02-29', 'precision': 'day', 'reason': None},
                        {'value': '2025', 'precision': 'unknown', 'reason': 'missing'}]:
            bad = event(); bad['event_date'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError): intake((), encode(bad), references())

    def test_zero_missing_not_applicable_not_yet_observable_and_suppressed(self):
        for state in ('unavailable', 'not_applicable', 'not_yet_observable', 'suppressed'):
            with self.subTest(state=state):
                obs = observation(); obs['estimate'] = missing(state)
                result = projection(self.initial(obs=obs))
                self.assertEqual(result['outcome_aggregates'], [])
                self.assertEqual(result['details'][-1]['aggregate_values']['estimate']['state'], state)
        obs = observation(); obs.update(estimate=value(0), numerator=value(0))
        result = projection(self.initial(obs=obs))
        self.assertEqual(result['outcome_aggregates'][0]['components']['estimate'], value(0))
        bad = observation(); bad['estimate'] = {'state': 'available', 'value': 0, 'reason': None}
        with self.assertRaisesRegex(ValueError, 'confirmed_zero'): self.initial(obs=bad)
        bad['estimate'] = missing('not_applicable', reason='')
        with self.assertRaises(ValueError): self.initial(obs=bad)

    def test_denominator_comparator_baseline_and_follow_up_requirements(self):
        for name in ('numerator', 'denominator', 'comparator', 'baseline', 'follow_up', 'uncertainty', 'method'):
            with self.subTest(name=name):
                obs = observation(); obs[name] = missing()
                result = projection(self.initial(obs=obs))
                self.assertEqual(result['outcome_aggregates'], [])
                self.assertIn(name+'_unavailable', result['details'][-1]['unavailable_reasons'])
        obs = observation(); obs['denominator'] = value(0)
        result = projection(self.initial(obs=obs))
        self.assertEqual(result['outcome_aggregates'], []); self.assertIn('zero_eligible_denominator', result['details'][-1]['unavailable_reasons'])
        obs = observation(); obs['follow_up']['value']['anchor'] = {'value': None, 'precision': 'unknown', 'reason': 'FICTIONAL missing anchor'}
        self.assertIn('follow_up_anchor_unavailable', projection(self.initial(obs=obs))['details'][-1]['unavailable_reasons'])

    def test_not_applicable_allowed_only_as_explicit_policy_input_not_guessed(self):
        refs = references(); refs['indicators'][0]['requirements'] = {k: False for k in refs['indicators'][0]['requirements']}
        obs = observation()
        for name in ('numerator', 'denominator', 'comparator', 'baseline', 'follow_up', 'uncertainty', 'method'):
            obs[name] = missing('not_applicable', 'FICTIONAL supplied definition says not applicable')
        history, _ = intake((), encode(event()), refs); history, _ = intake(history, encode(obs), refs)
        self.assertEqual(len(projection(history, refs)['outcome_aggregates']), 1)
        self.assertEqual(projection(history)['outcome_aggregates'], [])  # Same version, changed requirements unavailable.

    def test_invalid_references_units_duplicate_projects_and_numeric_values_fail_without_effect(self):
        history, _ = intake((), encode(event()), references()); before = copy.deepcopy(history)
        cases = []
        bad = observation(); bad['event_id'] = 'unregistered'; cases.append(bad)
        bad = observation(); bad['project_ids'] = ['FIC-P1', 'FIC-P1']; cases.append(bad)
        bad = observation(); bad['indicator']['version'] = 'unknown'; cases.append(bad)
        bad = observation(); bad['unit'] = 'different unit'; cases.append(bad)
        bad = observation(); bad['evidence'][0]['source_revision'] = 'unregistered'; cases.append(bad)
        bad = observation(); bad['method'] = available('unregistered'); cases.append(bad)
        bad = observation(); bad['comparator'] = available({'id': 'unregistered', 'version': '1'}); cases.append(bad)
        for number in (True, float('nan'), float('inf')):
            bad = observation(); bad['estimate'] = available(number); cases.append(bad)
        for bad in cases:
            with self.subTest(record=bad), self.assertRaises(ValueError): intake(history, encode(bad), references())
            self.assertEqual(history, before)

    def test_revision_identity_stale_fork_and_changed_definition_or_source_version_rejected(self):
        history = self.initial(); before = copy.deepcopy(history)
        for bad in [revised(observation(), 'FIC-O-R2', 'wrong'), revised(observation(), 'FIC-O-R1', 'FIC-O-R1')]:
            with self.assertRaises(ValueError): intake(history, encode(bad), references())
        refs = references(); refs['indicators'][0]['requirements']['baseline'] = False
        with self.assertRaisesRegex(ValueError, 'Indicator definition changed'):
            intake(history, encode(revised(observation(), 'FIC-O-R2', 'FIC-O-R1')), refs)
        refs = references(); refs['evidence'][0]['sha256'] = 'a'*64
        bad = revised(observation(), 'FIC-O-R2', 'FIC-O-R1'); bad['evidence'][0]['sha256'] = 'a'*64
        with self.assertRaisesRegex(ValueError, 'without a new revision'): intake(history, encode(bad), refs)
        self.assertEqual(history, before)
        raw = encode(observation()).replace(b'"id": "FIC-OBSERVATION"', b'"id": "FIC-OBSERVATION", "id": "duplicate"')
        with self.assertRaisesRegex(ValueError, 'Duplicate source JSON key'): intake(history, raw, references())

    def test_no_unauthorised_aggregate_values_or_raw_evidence_urls_projected(self):
        obs = observation(); obs['authorized_aggregate'] = False
        result = projection(self.initial(obs=obs)); detail = result['details'][-1]
        self.assertIsNone(detail['aggregate_values']); self.assertEqual(result['outcome_aggregates'], [])
        self.assertNotIn('fixture://', json.dumps(result)); self.assertNotIn('0.25', json.dumps(result))
        self.assertIn('aggregate_not_authorized', detail['unavailable_reasons'])

    def test_multiple_observations_not_pooled_or_averaged(self):
        history = self.initial(); second = observation()
        second.update(id='FIC-OBSERVATION-2', revision_id='FIC-O2-R1', estimate=value(.5), numerator=value(10))
        history, _ = intake(history, encode(second), references()); result = projection(history)
        self.assertEqual([v['components']['estimate']['value'] for v in result['outcome_aggregates']], [.25, .5])
        self.assertEqual(len(result['outcome_aggregates']), 2)
        self.assertNotIn('combined_effect', result)

    def test_invalid_duplicate_or_reordered_history_is_not_silently_repaired(self):
        history = self.initial()
        newer, _ = intake(history, encode(revised(observation(), 'FIC-O-R2', 'FIC-O-R1')), references())
        for bad in (history+(history[0],), (newer[0], newer[2], newer[1]), ({'malformed': True},)):
            with self.subTest(history=bad), self.assertRaises(ValueError): projection(bad)
        self.assertEqual(len(history), 2)


if __name__ == '__main__': unittest.main()
