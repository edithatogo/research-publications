"""Fictional bounded journal transport; no network or authentication."""
import copy
import unittest
from scripts.outcome_persistence import prepare, apply_once, reporting_tables, restore, load_snapshot
from test_outcome_evidence import event, observation, encode, references, revised


class Transport:
    def __init__(self):
        self.snapshot = {'item_id': 1, 'etag': '"1"', 'journal': {'version': 1, 'entries': []}}
        self.writes = 0
        self.mode = None
    def read(self, item_id):
        if self.mode == 'read_failure' and self.writes:
            raise OSError('offline')
        return copy.deepcopy(self.snapshot)
    def compare_and_set(self, item_id, etag, journal):
        self.writes += 1
        if self.mode == 'race':
            self.snapshot['etag'] = '"other"'
        if etag != self.snapshot['etag']:
            raise ValueError('412')
        self.snapshot.update(journal=journal, etag='"'+str(self.writes + 1)+'"')
        if self.mode == 'lost_response':
            raise OSError('response lost after commit')


class PersistenceTests(unittest.TestCase):
    def test_persist_replay_revision_and_protected_edit(self):
        t = Transport()
        for record in (event(), observation()):
            p = prepare(t.read(1), encode(record), references(), human_edits={'limitations': 'FICTIONAL protected'} if record['kind'] == 'OutcomeObservation' else None)
            self.assertEqual(apply_once(p, t)['outcome'], 'candidate_present')
            self.assertEqual(apply_once(p, t)['writes'], 0)
        newer = revised(observation(), 'FIC-O-R2', 'FIC-O-R1')
        p = prepare(t.read(1), encode(newer), references())
        apply_once(p, t)
        self.assertIn('FICTIONAL protected', restore(t.snapshot['journal'])[-1].effective_json)
        self.assertEqual(len(restore(t.snapshot['journal'])), 3)
        self.assertEqual(t.writes, 3)

    def test_concurrent_edit_and_atomic_etag_race(self):
        t = Transport(); p = prepare(t.read(1), encode(event()), references())
        t.snapshot['etag'] = '"changed"'
        with self.assertRaisesRegex(ValueError, 'Concurrent'): apply_once(p, t)
        self.assertEqual(t.writes, 0)
        t = Transport(); p = prepare(t.read(1), encode(event()), references()); t.mode = 'race'
        self.assertEqual(apply_once(p, t)['outcome'], 'conflict')
        self.assertEqual(t.snapshot['journal']['entries'], [])

    def test_uncertain_writes_are_read_back_never_retried(self):
        for mode, expected in [('lost_response', 'candidate_present'), ('read_failure', 'unknown')]:
            t = Transport(); p = prepare(t.read(1), encode(event()), references()); t.mode = mode
            result = apply_once(p, t)
            self.assertEqual(result['outcome'], expected); self.assertEqual(t.writes, 1)
            self.assertFalse(result['retry_allowed'])

    def test_projection_withdrawal_and_bridge_cardinality(self):
        t = Transport()
        for record in (event(), observation()): apply_once(prepare(t.read(1), encode(record), references()), t)
        context = dict(cutoff_utc='2026-03-01T00:00:00Z', source_snapshot='FIC-SOURCE', model_revision='FIC-MODEL', report_revision='FIC-REPORT')
        tables = reporting_tables(t.snapshot['journal'], references(), **context)
        self.assertEqual(len(tables['TranslationEvent']), 1)
        self.assertEqual(len(tables['EventProject']), 2)
        withdrawal = revised(event(), 'FIC-T-R2', 'FIC-T-R1'); withdrawal['verification']['status'] = 'withdrawn'
        apply_once(prepare(t.read(1), encode(withdrawal), references()), t)
        tables = reporting_tables(t.snapshot['journal'], references(), **context)
        self.assertEqual(tables['OutcomeObservation'], [])
        self.assertEqual(len(tables['OutcomeEvidenceDetail']), 3)

    def test_duplicate_json_and_missing_preimage_refused(self):
        with self.assertRaises(ValueError): load_snapshot('{"etag":1,"etag":2}')
        with self.assertRaises(ValueError): prepare({}, encode(event()), references())
        t = Transport(); t.snapshot['etag'] = '*'
        with self.assertRaises(ValueError): prepare(t.snapshot, encode(event()), references())


class SchemaTests(unittest.TestCase):
    def test_schema_addition_and_incompatible_existing_field(self):
        from scripts.outcome_persistence import schema_plan, digest
        capture = dict(complete=True, list_id='FICTIONAL-LIST', source='fixture://schema',
                       captured_at='2026-10-30T00:00:00Z', fields=[])
        plan = schema_plan(capture, expected_sha256=digest(capture), field_name='OutcomeJournal')
        self.assertEqual(len(plan['changes']), 1); self.assertFalse(plan['deployment_ready'])
        capture['fields'] = [dict(InternalName='OutcomeJournal', TypeAsString='Note', RichText=False, AppendOnly=False, ReadOnlyField=False)]
        self.assertEqual(schema_plan(capture, expected_sha256=digest(capture), field_name='OutcomeJournal')['changes'], [])
        capture['fields'][0]['RichText'] = True
        with self.assertRaises(ValueError): schema_plan(capture, expected_sha256=digest(capture), field_name='OutcomeJournal')
        with self.assertRaises(ValueError): schema_plan(capture, expected_sha256='stale', field_name='OutcomeJournal')
