import unittest
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.grants_operations import evaluate_run
from scripts.grants_planning import delivery_event_key, validate_policy
from scripts.grants_relationships import normalize_relationship, validate_relationship_batch
from scripts.grants_registry import stable_key
from scripts.author_registry import build_author_registry


class GrantsRelationshipTests(unittest.TestCase):
    @staticmethod
    def _award_link(from_key='AWARD:MRFF:1', award_id='A-1', to_key='PUB:1', **extra):
        return {'RelationshipType': 'funded_by_award', 'FromKey': from_key,
                'ToKey': to_key, 'AwardID': award_id, 'EvidenceURL': 'https://evidence',
                'Confidence': 'confirmed', 'ReviewStatus': 'Reviewed', **extra}

    @staticmethod
    def _award_sources():
        return [{'AwardKey': 'AWARD:MRFF:1', 'AwardID': 'A-1',
                 'FunderKey': 'MRFF', 'AwardStatus': 'active'}]

    def test_batch_resolves_reused_award_id_only_with_funder_scoped_source_key(self):
        records = [self._award_link(), self._award_link(
            from_key='AWARD:NHMRC:1', award_id='A-1', to_key='PUB:2')]
        sources = self._award_sources() + [
            {'AwardKey': 'AWARD:NHMRC:1', 'AwardID': 'A-1',
             'FunderKey': 'NHMRC', 'AwardStatus': 'active'}]
        result = validate_relationship_batch(
            records, publication_keys=['PUB:1', 'PUB:2'], opportunity_keys=[],
            award_sources=sources, affiliation_sources={})
        self.assertEqual(len(result['validated']), 2)
        self.assertEqual({row['FromKey'] for row in result['validated']},
                         {'AWARD:MRFF:1', 'AWARD:NHMRC:1'})
        self.assertEqual(result['rejected'], [])

    def test_batch_rejects_all_duplicate_relationship_keys_order_independently(self):
        record = self._award_link()
        result = validate_relationship_batch(
            [record, dict(record)], publication_keys=['PUB:1'], opportunity_keys=[],
            award_sources=self._award_sources(), affiliation_sources={})
        self.assertEqual(result['validated'], [])
        self.assertEqual(result['rejected'], [
            {'index': 0, 'reasons': ['duplicate_relationship_key']},
            {'index': 1, 'reasons': ['duplicate_relationship_key']},
        ])

    def test_batch_rejects_orphan_publication_and_missing_award_source(self):
        result = validate_relationship_batch(
            [self._award_link(to_key='PUB:orphan'), self._award_link(
                from_key='AWARD:UNKNOWN:9', award_id='A-9', to_key='PUB:1')],
            publication_keys=['PUB:1'], opportunity_keys=[],
            award_sources=self._award_sources(), affiliation_sources={})
        self.assertEqual(result['validated'], [])
        self.assertEqual(result['rejected'][0]['reasons'], ['publication_source_missing'])
        self.assertEqual(result['rejected'][1]['reasons'], ['award_source_missing'])

    def test_batch_rejects_malformed_source_snapshot_types_before_matching(self):
        cases = [
            ({'publication_keys': [123]}, 'publication keys must be text'),
            ({'publication_keys': ['PUB:1', '  ']}, 'publication keys must be nonblank'),
            ({'opportunity_keys': ['']}, 'opportunity keys must be nonblank'),
            ({'award_sources': [{**self._award_sources()[0], 'AwardID': 1}]}, 'award source AwardID must be text'),
            ({'affiliation_sources': {123: ['ORG:1']}}, 'affiliation source keys must be text'),
            ({'affiliation_sources': {'AUTH:1': [1]}}, 'affiliation targets must be text'),
            ({'affiliation_sources': {'AUTH:1': 'ORG:1'}}, 'target collections must be sequences'),
        ]
        for overrides, message in cases:
            arguments = {'publication_keys': ['PUB:1'], 'opportunity_keys': [],
                         'award_sources': self._award_sources(), 'affiliation_sources': {}}
            arguments.update(overrides)
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, message):
                validate_relationship_batch([self._award_link()], **arguments)

    def test_batch_rejects_padded_source_identity_keys_without_normalizing_them(self):
        padded_award = {'AwardKey': ' AWARD:MRFF:1', 'AwardID': 'A-1',
                        'FunderKey': 'MRFF', 'AwardStatus': 'active'}
        cases = [
            ({'publication_keys': [' PUB:1']}, 'publication keys must be unpadded'),
            ({'opportunity_keys': ['GRANT:1 ']}, 'opportunity keys must be unpadded'),
            ({'award_sources': [padded_award]}, 'award source AwardKey must be unpadded'),
            ({'award_sources': [{**self._award_sources()[0], 'AwardID': 'A-1 '}]},
             'award source AwardID must be unpadded'),
            ({'award_sources': [{**self._award_sources()[0], 'FunderKey': 'MRFF '}]},
             'award source FunderKey must be unpadded'),
            ({'affiliation_sources': {' AUTH:1': ['ORG:1']}},
             'affiliation source keys must be nonblank and unpadded'),
            ({'affiliation_sources': {'AUTH:1': ['ORG:1 ']}},
             'affiliation target keys must be nonblank and unpadded'),
        ]
        for overrides, message in cases:
            arguments = {'publication_keys': ['PUB:1'], 'opportunity_keys': [],
                         'award_sources': self._award_sources(), 'affiliation_sources': {}}
            arguments.update(overrides)
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, message):
                validate_relationship_batch([self._award_link()], **arguments)

    def test_relationship_identity_keys_and_award_id_must_not_be_padded(self):
        for record, message in (
            (self._award_link(from_key=' AWARD:MRFF:1'), 'source keys must be nonblank and unpadded'),
            (self._award_link(to_key='PUB:1 '), 'source keys must be nonblank and unpadded'),
            (self._award_link(award_id=' A-1'), 'AwardID must be nonblank and unpadded'),
        ):
            with self.subTest(record=record), self.assertRaisesRegex(ValueError, message):
                normalize_relationship(record)

    def test_award_relationship_requires_funder_scoped_source_key(self):
        for key in ('AWARD:1', 'AWARD::1', 'AWARD:MRFF:', 'AWARD:MRFF: 1'):
            with self.subTest(key=key), self.assertRaisesRegex(
                    ValueError, 'award relationships must link an AWARD key to a PUB key'):
                normalize_relationship(self._award_link(from_key=key))


    def test_batch_rejects_award_key_namespace_that_disagrees_with_funder(self):
        source = {**self._award_sources()[0], 'FunderKey': 'FUNDER:nhmrc'}
        result = validate_relationship_batch(
            [self._award_link()], publication_keys=['PUB:1'], opportunity_keys=[],
            award_sources=[source], affiliation_sources={})
        self.assertEqual(result['validated'], [])
        self.assertEqual(result['rejected'], [{
            'index': 0,
            'reasons': ['award_funder_key_namespace_mismatch'],
        }])


    def test_batch_accepts_canonical_funder_namespace_key(self):
        source = {**self._award_sources()[0], 'AwardKey': 'AWARD:arc:source-1',
                  'FunderKey': 'FUNDER:arc'}
        candidate = self._award_link(from_key='AWARD:arc:source-1')
        result = validate_relationship_batch(
            [candidate], publication_keys=['PUB:1'], opportunity_keys=[],
            award_sources=[source], affiliation_sources={})
        self.assertEqual(len(result['validated']), 1)
        self.assertEqual(result['rejected'], [])


    def test_batch_detects_duplicate_award_identity_across_funder_key_aliases(self):
        sources = [
            {'AwardKey': 'AWARD:MRFF:1', 'AwardID': 'A-1',
             'FunderKey': 'MRFF', 'AwardStatus': 'active'},
            {'AwardKey': 'AWARD:mrff:1', 'AwardID': 'A-1',
             'FunderKey': 'FUNDER:mrff', 'AwardStatus': 'active'},
        ]
        result = validate_relationship_batch(
            [self._award_link()], publication_keys=['PUB:1'], opportunity_keys=[],
            award_sources=sources, affiliation_sources={})
        self.assertEqual(result['validated'], [])
        self.assertEqual(result['rejected'], [{
            'index': 0, 'reasons': ['award_funder_identity_ambiguous'],
        }])


    def test_batch_keeps_candidate_affiliation_unresolved_when_identity_is_ambiguous(self):
        candidate = {'RelationshipType': 'investigator_affiliation',
                     'FromKey': 'AUTH:1', 'ToKey': 'ORG:1',
                     'EvidenceURL': 'https://evidence', 'Confidence': 'candidate'}
        result = validate_relationship_batch(
            [candidate], publication_keys=[], opportunity_keys=[], award_sources=[],
            affiliation_sources={'AUTH:1': ['ORG:1', 'ORG:2']})
        self.assertEqual(result['validated'], [])
        self.assertEqual(result['rejected'], [
            {'index': 0, 'reasons': ['affiliation_identity_ambiguous']},
        ])


    def test_namespace_comparison_does_not_rekey_or_promote_a_candidate(self):
        candidate = self._award_link(Confidence='candidate', RelationshipType='candidate_award_match')
        candidate['ReviewStatus'] = 'Needs Review'
        before = normalize_relationship(candidate)
        result = validate_relationship_batch(
            [candidate], publication_keys=['PUB:1'], opportunity_keys=[],
            award_sources=[{**self._award_sources()[0], 'FunderKey': 'FUNDER:mrff'}],
            affiliation_sources={})
        self.assertEqual(result['validated'], [before])
        self.assertEqual(result['validated'][0]['FromKey'], 'AWARD:MRFF:1')
        self.assertEqual(result['validated'][0]['ReviewStatus'], 'Needs Review')
        self.assertEqual(normalize_relationship(self._award_link())['RelationshipKey'],
                         'REL:43faab7ab068494b3196272b')

    def test_single_target_candidate_affiliation_remains_a_candidate(self):
        candidate = {'RelationshipType': 'investigator_affiliation',
                     'FromKey': 'AUTH:1', 'ToKey': 'ORG:1',
                     'EvidenceURL': 'https://evidence', 'Confidence': 'candidate'}
        result = validate_relationship_batch(
            [candidate], publication_keys=[], opportunity_keys=[], award_sources=[],
            affiliation_sources={'AUTH:1': ['ORG:1']})
        self.assertEqual(result['validated'][0]['Confidence'], 'candidate')
        self.assertEqual(result['validated'][0]['ReviewStatus'], 'Needs Review')
        self.assertEqual(result['rejected'], [])

    def test_batch_rejects_duplicate_source_keys_and_withdrawn_award(self):
        duplicate_sources = self._award_sources() * 2
        result = validate_relationship_batch(
            [self._award_link()], publication_keys=['PUB:1'], opportunity_keys=[],
            award_sources=duplicate_sources, affiliation_sources={})
        self.assertIn('award_source_key_duplicate', result['rejected'][0]['reasons'])
        result = validate_relationship_batch(
            [self._award_link()], publication_keys=['PUB:1'], opportunity_keys=[],
            award_sources=[{**self._award_sources()[0], 'AwardStatus': 'withdrawn'}],
            affiliation_sources={})
        self.assertIn('withdrawn_award_cannot_be_confirmed', result['rejected'][0]['reasons'])

    def test_batch_rejects_duplicate_publication_and_opportunity_keys(self):
        relevance = {'RelationshipType': 'relevant_to_opportunity',
                     'FromKey': 'PUB:1', 'ToKey': 'GRANT:1',
                     'EvidenceURL': 'https://evidence', 'Confidence': 'candidate'}
        result = validate_relationship_batch(
            [relevance], publication_keys=['PUB:1', 'PUB:1'],
            opportunity_keys=['GRANT:1', 'GRANT:1'], award_sources=[],
            affiliation_sources={})
        self.assertEqual(result['validated'], [])
        self.assertEqual(result['rejected'], [{
            'index': 0,
            'reasons': ['opportunity_key_duplicate', 'publication_key_duplicate'],
        }])

    def test_opportunity_relationship_accepts_canonical_extended_key_scheme(self):
        opportunity_key = stable_key({'Source': 'NHMRC', 'SourceID': 'scheme:round'})
        self.assertTrue(opportunity_key.startswith('GRANTX:'))
        record = {'RelationshipType': 'relevant_to_opportunity',
                  'FromKey': 'PUB:1', 'ToKey': opportunity_key,
                  'EvidenceURL': 'https://evidence', 'Confidence': 'candidate'}
        self.assertEqual(normalize_relationship(record)['ToKey'], opportunity_key)
        result = validate_relationship_batch(
            [record], publication_keys=['PUB:1'], opportunity_keys=[opportunity_key],
            award_sources=[], affiliation_sources={})
        self.assertEqual(result['validated'], [normalize_relationship(record)])
        self.assertEqual(result['rejected'], [])

    def test_batch_rejects_missing_affiliation_source_and_unresolved_target(self):
        def link(author, organisation):
            return {'RelationshipType': 'investigator_affiliation',
                    'FromKey': author, 'ToKey': organisation,
                    'EvidenceURL': 'https://evidence', 'Confidence': 'candidate'}
        result = validate_relationship_batch(
            [link('AUTH:missing', 'ORG:1'), link('AUTH:1', 'ORG:absent')],
            publication_keys=[], opportunity_keys=[], award_sources=[],
            affiliation_sources={'AUTH:1': ['ORG:1']})
        self.assertEqual(result['validated'], [])
        self.assertEqual(result['rejected'], [
            {'index': 0, 'reasons': ['affiliation_source_missing']},
            {'index': 1, 'reasons': ['affiliation_target_unresolved']},
        ])

    def test_batch_holds_ambiguous_confirmed_affiliation_and_keeps_candidate_as_candidate(self):
        confirmed = {'RelationshipType': 'investigator_affiliation',
                     'FromKey': 'AUTH:1', 'ToKey': 'ORG:1',
                     'EvidenceURL': 'https://evidence', 'Confidence': 'confirmed',
                     'ReviewStatus': 'Reviewed'}
        candidate = {'RelationshipType': 'candidate_award_match',
                     'FromKey': 'AWARD:MRFF:1', 'ToKey': 'PUB:1',
                     'AwardID': 'A-1', 'EvidenceURL': 'https://evidence',
                     'Confidence': 'candidate'}
        result = validate_relationship_batch(
            [confirmed, candidate], publication_keys=['PUB:1'], opportunity_keys=[],
            award_sources=self._award_sources(),
            affiliation_sources={'AUTH:1': ['ORG:1', 'ORG:2']})
        self.assertEqual([row['RelationshipType'] for row in result['validated']],
                         ['candidate_award_match'])
        self.assertEqual(result['validated'][0]['Confidence'], 'candidate')
        self.assertEqual(result['rejected'], [
            {'index': 0, 'reasons': ['affiliation_identity_ambiguous']},
        ])

    def test_batch_rejects_padded_affiliation_snapshot_key_before_normalization(self):
        confirmed = {'RelationshipType': 'investigator_affiliation',
                     'FromKey': 'AUTH:1', 'ToKey': 'ORG:2',
                     'EvidenceURL': 'https://evidence', 'Confidence': 'confirmed',
                     'ReviewStatus': 'Reviewed'}
        with self.assertRaisesRegex(ValueError, 'affiliation source keys must be nonblank and unpadded'):
            validate_relationship_batch(
                [confirmed], publication_keys=[], opportunity_keys=[], award_sources=[],
                affiliation_sources={'AUTH:1': ['ORG:1'], ' AUTH:1 ': ['ORG:2']})

    def test_generated_author_registry_key_resolves_in_relationship_batch(self):
        authors, _ = build_author_registry(
            dora_records=[{'DORAKey': '1/9', 'Authors': 'Doe, Jane'}]
        )
        author_key = authors[0]['AuthorKey']
        self.assertTrue(author_key.startswith('AUTH:'))
        relation = {
            'RelationshipType': 'investigator_affiliation',
            'FromKey': author_key,
            'ToKey': 'ORG:1',
            'EvidenceURL': 'https://example.org/evidence',
            'Confidence': 'candidate',
        }
        result = validate_relationship_batch(
            [relation], publication_keys=[], opportunity_keys=[], award_sources=[],
            affiliation_sources={author_key: ['ORG:1']},
        )
        self.assertEqual(len(result['validated']), 1)
        self.assertEqual(result['validated'][0]['FromKey'], author_key)
        self.assertEqual(result['rejected'], [])

    def test_relationship_schema_matches_normalized_projection(self):
        schema = json.loads((Path(__file__).parents[1] / 'config/grant-relationships.schema.json').read_text())
        row = normalize_relationship({'RelationshipType':'funded_by_award','FromKey':'AWARD:MRFF:1','ToKey':'PUB:1','AwardID':'MRFF-1','EvidenceURL':'https://evidence','Confidence':'confirmed','ReviewStatus':'Reviewed'})
        self.assertEqual(schema['identity_field'], 'RelationshipKey')
        self.assertEqual({f['display_name'] for f in schema['fields']}, set(row))
        self.assertEqual(schema['list_name'], 'Grant Relationships')
        relationship_type = next(f for f in schema['fields'] if f['display_name'] == 'RelationshipType')
        self.assertIn('candidate_award_match', relationship_type['choices'])
        confidence = next(f for f in schema['fields'] if f['display_name'] == 'Confidence')
        self.assertEqual(confidence['type'], 'choice')
        self.assertEqual(set(confidence['choices']), {'confirmed', 'review', 'candidate'})
        review_status = next(f for f in schema['fields'] if f['display_name'] == 'ReviewStatus')
        self.assertEqual(review_status['type'], 'text')

    def test_relationship_rejects_non_text_award_id_and_review_status(self):
        base = {'RelationshipType': 'candidate_award_match',
                'FromKey': 'AWARD:MRFF:1', 'ToKey': 'PUB:1',
                'AwardID': 'MRFF-1', 'EvidenceURL': 'https://evidence',
                'Confidence': 'candidate'}
        for field, value in (('AwardID', 101), ('ReviewStatus', 7)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                normalize_relationship({**base, field: value})

    def test_relationship_key_uses_unambiguous_typed_field_serialization(self):
        left = normalize_relationship({
            'RelationshipType': 'investigator_affiliation',
            'FromKey': 'AUTH:a|ORG:b', 'ToKey': 'ORG:c',
            'EvidenceURL': 'https://example.org/evidence',
            'Confidence': 'candidate',
        })
        right = normalize_relationship({
            'RelationshipType': 'investigator_affiliation',
            'FromKey': 'AUTH:a', 'ToKey': 'ORG:b|ORG:c',
            'EvidenceURL': 'https://example.org/evidence',
            'Confidence': 'candidate',
        })
        self.assertNotEqual(left['RelationshipKey'], right['RelationshipKey'])

    def test_relationship_normalization_rejects_unknown_fields_and_checks_supplied_key(self):
        record = {
            'RelationshipType': 'relevant_to_opportunity',
            'FromKey': 'PUB:1',
            'ToKey': 'GRANT:1',
            'EvidenceURL': 'https://example.org/evidence',
            'Confidence': 'candidate',
        }
        normalized = normalize_relationship(record)
        self.assertEqual(normalize_relationship(normalized), normalized)
        for supplied_key in (None, 123, 'REL:forged'):
            with self.subTest(supplied_key=supplied_key), self.assertRaisesRegex(
                    ValueError, 'RelationshipKey'):
                normalize_relationship({**record, 'RelationshipKey': supplied_key})
        with self.assertRaisesRegex(ValueError, 'unsupported relationship fields'):
            normalize_relationship({**record, 'ReviewStaus': 'Reviewed'})

    def test_relationship_rejects_non_text_required_identity_and_evidence(self):
        base = {'RelationshipType': 'relevant_to_opportunity', 'FromKey': 'PUB:1',
                'ToKey': 'GRANT:1', 'EvidenceURL': 'https://evidence',
                'Confidence': 'candidate'}
        for field, value in (('RelationshipType', 1), ('FromKey', ['PUB:1']),
                             ('ToKey', 2), ('EvidenceURL', {'url': 'https://evidence'}),
                             ('Confidence', False)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                normalize_relationship({**base, field: value})

    def test_confirmed_award_requires_exact_award_id(self):
        with self.assertRaises(ValueError):
            normalize_relationship({'RelationshipType':'funded_by_award','FromKey':'AWARD:MRFF:1','ToKey':'PUB:1','EvidenceURL':'https://evidence','Confidence':'confirmed'})
        row = normalize_relationship({'RelationshipType':'funded_by_award','FromKey':'AWARD:MRFF:1','ToKey':'PUB:1','AwardID':'MRFF-1','EvidenceURL':'https://evidence','Confidence':'confirmed','ReviewStatus':'Reviewed'})
        self.assertTrue(row['RelationshipKey'].startswith('REL:'))

    def test_relationship_evidence_requires_absolute_http_url_without_credentials(self):
        base = {'RelationshipType': 'relevant_to_opportunity', 'FromKey': 'PUB:1',
                'ToKey': 'GRANT:1', 'Confidence': 'candidate'}
        for evidence in ('evidence/page', '//example.org/evidence', 'ftp://example.org/evidence',
                         'https://user:secret@example.org/evidence', 'https://[invalid/evidence'):
            with self.subTest(evidence=evidence), self.assertRaisesRegex(ValueError, r'absolute HTTP\(S\) URL'):
                normalize_relationship({**base, 'EvidenceURL': evidence})
        row = normalize_relationship({**base, 'EvidenceURL': 'https://example.org/evidence?id=7'})
        self.assertEqual(row['EvidenceURL'], 'https://example.org/evidence?id=7')

    def test_award_and_opportunity_keys_cannot_be_interchanged(self):
        with self.assertRaisesRegex(ValueError, 'AWARD key to a PUB key'):
            normalize_relationship({'RelationshipType':'funded_by_award','FromKey':'GRANT:1','ToKey':'PUB:1','AwardID':'MRFF-1','EvidenceURL':'https://evidence','Confidence':'confirmed'})
        with self.assertRaisesRegex(ValueError, 'PUB key to a GRANT opportunity key'):
            normalize_relationship({'RelationshipType':'relevant_to_opportunity','FromKey':'PUB:1','ToKey':'AWARD:MRFF:1','AwardID':'MRFF-1','EvidenceURL':'https://evidence','Confidence':'candidate'})

    def test_candidate_award_match_is_never_serialized_as_funding(self):
        row = normalize_relationship({'RelationshipType':'candidate_award_match','FromKey':'AWARD:MRFF:1','ToKey':'PUB:1','AwardID':'MRFF-1','EvidenceURL':'https://evidence','Confidence':'candidate'})
        self.assertEqual(row['RelationshipType'], 'candidate_award_match')
        with self.assertRaisesRegex(ValueError, 'unconfirmed award matches'):
            normalize_relationship({'RelationshipType':'funded_by_award','FromKey':'AWARD:MRFF:1','ToKey':'PUB:1','AwardID':'MRFF-1','EvidenceURL':'https://evidence','Confidence':'candidate'})

    def test_withdrawn_award_link_cannot_be_confirmed_as_funded(self):
        with self.assertRaisesRegex(ValueError, 'withdrawn or rejected'):
            normalize_relationship({'RelationshipType':'funded_by_award','FromKey':'AWARD:MRFF:1','ToKey':'PUB:1','AwardID':'MRFF-1','EvidenceURL':'https://evidence','Confidence':'confirmed','ReviewStatus':'Withdrawn'})

    def test_confirmed_award_requires_explicit_reviewed_state(self):
        for status in ('Needs Review', '', None):
            with self.subTest(status=status), self.assertRaisesRegex(
                    ValueError, 'confirmed relationships require ReviewStatus Reviewed'):
                normalize_relationship(self._award_link(ReviewStatus=status))

    def test_confirmed_non_award_relationship_requires_explicit_reviewed_state(self):
        for record in (
            {'RelationshipType': 'relevant_to_opportunity', 'FromKey': 'PUB:1',
             'ToKey': 'GRANT:1', 'EvidenceURL': 'https://evidence',
             'Confidence': 'confirmed'},
            {'RelationshipType': 'investigator_affiliation', 'FromKey': 'AUTH:1',
             'ToKey': 'ORG:1', 'EvidenceURL': 'https://evidence',
             'Confidence': 'confirmed'},
        ):
            with self.subTest(relation=record['RelationshipType']), self.assertRaisesRegex(
                    ValueError, 'confirmed relationships require ReviewStatus Reviewed'):
                normalize_relationship(record)
            reviewed = normalize_relationship({**record, 'ReviewStatus': 'Reviewed'})
            self.assertEqual(reviewed['ReviewStatus'], 'Reviewed')

    def test_topic_relevance_is_not_promoted_to_funding(self):
        row = normalize_relationship({'RelationshipType':'relevant_to_opportunity','FromKey':'PUB:1','ToKey':'GRANT:1','EvidenceURL':'https://evidence','Confidence':'candidate'})
        self.assertEqual(row['RelationshipType'], 'relevant_to_opportunity')
        self.assertEqual(row['Confidence'], 'candidate')

    def test_run_rejects_failed_source_and_preserves_last_batch(self):
        result = evaluate_run([{'OpportunityKey':'GRANT:1'}], [{'source':'nhmrc','status':'failed'}], [{'OpportunityKey':'GRANT:old'}])
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['records'], [{'OpportunityKey':'GRANT:old'}])

    def test_run_rejects_same_source_evidence_under_another_key(self):
        prior = [{'OpportunityKey': 'GRANT:old', 'Source': 'Official',
                  'SourceID': 'stable-id', 'EvidenceHash': 'digest'}]
        incoming = [{**prior[0], 'OpportunityKey': 'GRANT:new'}]
        result = evaluate_run(incoming, [{'source': 'official', 'status': 'succeeded'}], prior)
        self.assertEqual(result['status'], 'rejected')
        self.assertIn('conflicting_opportunity_key_for_source_evidence', result['errors'])
        self.assertEqual(result['records'], prior)

    def test_distinct_observations_do_not_trigger_identity_collision(self):
        prior = [{'OpportunityKey': 'GRANT:old', 'Source': 'Official',
                  'SourceID': 'stable-id', 'EvidenceHash': 'old-digest'}]
        incoming = [{**prior[0], 'OpportunityKey': 'GRANT:new', 'EvidenceHash': 'new-digest'}]
        result = evaluate_run(incoming, [{'source': 'official', 'status': 'succeeded'}], prior)
        self.assertNotIn('conflicting_opportunity_key_for_source_evidence', result['errors'])

    def test_verified_empty_batch_is_distinct_from_failed_or_unverified_empty(self):
        prior = [{'OpportunityKey': 'GRANT:old'}]
        failed = evaluate_run([], [{'source': 'nhmrc', 'status': 'failed'}], prior,
                              verified_empty=True)
        unverified = evaluate_run([], [{'source': 'nhmrc', 'status': 'succeeded'}], prior)
        accepted = evaluate_run([], [{'source': 'nhmrc', 'status': 'succeeded'}], prior,
                                verified_empty=True)

        self.assertEqual(failed['status'], 'rejected')
        self.assertEqual(failed['records'], prior)
        self.assertFalse(failed['verified_empty'])
        self.assertEqual(unverified['status'], 'rejected')
        self.assertEqual(unverified['records'], prior)
        self.assertIn('empty_batch', unverified['errors'])
        self.assertEqual(accepted['status'], 'accepted')
        self.assertEqual(accepted['records'], [])
        self.assertTrue(accepted['verified_empty'])

    def test_run_failure_reports_preservation_of_explicit_empty_snapshot(self):
        result = evaluate_run(
            [{'OpportunityKey': 'GRANT:1'}],
            [{'source': 'nhmrc', 'status': 'failed'}],
            prior_records=[],
        )
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['records'], [])
        self.assertTrue(result['preserved_prior'])

    def test_run_failure_without_prior_snapshot_does_not_claim_rollback(self):
        result = evaluate_run(
            [{'OpportunityKey': 'GRANT:1'}],
            [{'source': 'nhmrc', 'status': 'failed'}],
        )
        self.assertEqual(result['records'], [])
        self.assertFalse(result['preserved_prior'])

    def test_run_rejects_malformed_records_and_unhashable_keys_preserving_last_batch(self):
        prior = [{'OpportunityKey': 'GRANT:old'}]
        for records in ([None], [{'OpportunityKey': ['not', 'a', 'key']}],
                        [{'OpportunityKey': 'GRANT:1'}, {'OpportunityKey': {}}]):
            with self.subTest(records_type=type(records[0]).__name__):
                result = evaluate_run(records, [{'source': 'nhmrc', 'status': 'succeeded'}], prior)
                self.assertEqual(result['status'], 'rejected')
                self.assertEqual(result['records'], prior)
                self.assertTrue(result['preserved_prior'])

    def test_run_rejects_padded_opportunity_source_and_evidence_identities(self):
        prior = [{'OpportunityKey': 'GRANT:accepted'}]
        valid_health = [{'source': 'nhmrc', 'status': 'succeeded'}]
        cases = (
            ([{'OpportunityKey': ' GRANT:new '}], valid_health, 'padded_opportunity_key'),
            ([{'OpportunityKey': 'GRANT:new'}],
             [{'source': ' nhmrc ', 'status': 'succeeded'}], 'invalid_source_identity'),
            ([{'OpportunityKey': 'GRANT:new', 'Source': 'Official',
              'SourceID': ' stable-id ', 'EvidenceHash': 'digest'}],
             valid_health, 'malformed_source_evidence_identity'),
        )
        for records, health, error in cases:
            with self.subTest(error=error):
                result = evaluate_run(records, health, prior)
                self.assertEqual(result['status'], 'rejected')
                self.assertIn(error, result['errors'])
                self.assertEqual(result['records'], prior)
                self.assertTrue(result['preserved_prior'])

    def test_freshness_evaluator_counts_non_object_health_as_malformed(self):
        now = datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)
        result = evaluate_run([{'OpportunityKey': 'GRANT:1'}], [None],
                              source_policy={'nhmrc': {'owner': 'grants-team', 'max_age_seconds': 60}},
                              now=now)
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['source_health']['malformed_health_rows'], 1)
        self.assertIn('source_health:health:source_id_missing', result['errors'])

    def test_freshness_policy_rejects_padded_source_and_owner_identities(self):
        now = datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)
        health = [{'source': 'nhmrc', 'status': 'succeeded', 'owner': 'grants-team',
                   'checked_at': '2026-09-24T23:30:00Z'}]
        records = [{'OpportunityKey': 'GRANT:1'}]
        padded_source = evaluate_run(
            records, health,
            source_policy={' nhmrc ': {'owner': 'grants-team', 'max_age_seconds': 3600}},
            now=now,
        )
        self.assertEqual(padded_source['status'], 'rejected')
        self.assertIn('source_health:policy:source_id_invalid', padded_source['errors'])
        padded_owner = evaluate_run(
            records, [{**health[0], 'owner': ' grants-team '}],
            source_policy={'nhmrc': {'owner': ' grants-team ', 'max_age_seconds': 3600}},
            now=now,
        )
        self.assertEqual(padded_owner['status'], 'rejected')
        self.assertIn('source_health:nhmrc:policy_owner_invalid', padded_owner['errors'])

    def test_operational_source_policy_requires_owned_fresh_and_unique_health(self):
        now = datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)
        policy = {'nhmrc': {'owner': 'grants-team', 'max_age_seconds': 3600}}
        records = [{'OpportunityKey': 'GRANT:1'}]
        good = [{'source': 'nhmrc', 'status': 'succeeded', 'owner': 'grants-team',
                 'checked_at': '2026-09-24T23:30:00Z'}]
        result = evaluate_run(records, good, source_policy=policy, now=now)
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(result['source_health']['status'], 'healthy')
        stale = [{**good[0], 'checked_at': '2026-09-24T22:00:00Z'}]
        result = evaluate_run(records, stale, [{'OpportunityKey': 'GRANT:old'}],
                              source_policy=policy, now=now)
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['records'], [{'OpportunityKey': 'GRANT:old'}])
        self.assertIn('source_health:nhmrc:stale', result['errors'])
        wrong_owner = [{**good[0], 'owner': 'unknown'}]
        result = evaluate_run(records, wrong_owner, source_policy=policy, now=now)
        self.assertIn('source_health:nhmrc:owner_mismatch', result['errors'])
        self.assertIn('source_health:nhmrc:checked_at_missing',
                      evaluate_run(records, [{'source': 'nhmrc', 'status': 'succeeded', 'owner': 'grants-team'}],
                                   source_policy=policy, now=now)['errors'])
        duplicate = good * 2
        self.assertIn('source_health:nhmrc:duplicate_health',
                      evaluate_run(records, duplicate, source_policy=policy, now=now)['errors'])
        malformed = evaluate_run(records, good + [{'status': 'succeeded'}],
                                 source_policy=policy, now=now)
        self.assertIn('source_health:health:source_id_missing', malformed['errors'])

    def test_operational_source_policy_rejects_future_time_and_requires_clock(self):
        policy = {'nhmrc': {'owner': 'grants-team', 'max_age_seconds': 3600}}
        future = [{'source': 'nhmrc', 'status': 'succeeded', 'owner': 'grants-team',
                   'checked_at': '2026-09-25T01:00:00Z'}]
        result = evaluate_run([{'OpportunityKey': 'GRANT:1'}], future,
                              source_policy=policy,
                              now=datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc))
        self.assertIn('source_health:nhmrc:checked_at_in_future', result['errors'])
        with self.assertRaisesRegex(ValueError, 'now is required'):
            evaluate_run([], [], source_policy=policy)

    def test_operational_source_policy_requires_strict_offset_bearing_rfc3339(self):
        now = datetime(2026, 9, 25, tzinfo=timezone.utc)
        policy = {'nhmrc': {'owner': 'funding', 'max_age_seconds': 3600}}
        invalid_times = (
            '2026-09-24 23:30:00Z',
            '2026-09-24T23:30Z',
            '2026-09-24T23:30:00',
            '2026-09-24T23:30:00+0000',
        )
        for checked_at in invalid_times:
            with self.subTest(checked_at=checked_at):
                result = evaluate_run(
                    [{'OpportunityKey': 'GRANT:1'}],
                    [{'source': 'nhmrc', 'owner': 'funding', 'status': 'succeeded',
                      'checked_at': checked_at}],
                    source_policy=policy, now=now,
                )
                self.assertIn('source_health:nhmrc:checked_at_invalid', result['errors'])

    def test_operational_source_policy_rejects_non_finite_freshness_limits(self):
        now = datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)
        records = [{'OpportunityKey': 'GRANT:1'}]
        health = [{'source': 'nhmrc', 'status': 'succeeded', 'owner': 'grants-team',
                   'checked_at': '2026-09-24T23:59:00Z'}]
        for limit in (float('nan'), float('inf'), float('-inf')):
            with self.subTest(limit=limit):
                result = evaluate_run(
                    records, health,
                    source_policy={'nhmrc': {'owner': 'grants-team',
                                             'max_age_seconds': limit}},
                    now=now,
                )
                self.assertEqual(result['status'], 'rejected')
                self.assertIn('source_health:nhmrc:invalid_freshness_policy',
                              result['errors'])

    def test_malformed_operational_policy_rejects_and_preserves_prior_records(self):
        now = datetime(2026, 9, 25, tzinfo=timezone.utc)
        records = [{'OpportunityKey': 'GRANT:new'}]
        prior = [{'OpportunityKey': 'GRANT:accepted'}]
        health = [{'source': 'nhmrc', 'owner': 'grants-team', 'status': 'succeeded',
                   'checked_at': '2026-09-25T00:00:00Z'}]
        malformed_policies = (
            {'nhmrc': None},
            ['nhmrc'],
        )
        for policy in malformed_policies:
            with self.subTest(policy=policy):
                result = evaluate_run(records, health, prior,
                                      source_policy=policy, now=now)
                self.assertEqual(result['status'], 'rejected')
                self.assertEqual(result['records'], prior)
                self.assertTrue(result['preserved_prior'])
                self.assertTrue(any('invalid_policy_entry' in error or 'not_mapping' in error
                                    for error in result['errors']))

    def test_policy_and_delivery_keys_are_versioned(self):
        policy = {'PolicyKey':'CHHHS-DEFAULT','Version':'1.0','OrganisationKey':'CHHHS','AnchorKind':'final','LeadDays':10,'CalendarOrBusinessDays':'calendar','HolidayCalendarVersion':'qld-2026','EffectiveFrom':'2026-01-01'}
        self.assertTrue(validate_policy(policy))
        self.assertEqual(delivery_event_key('u','g','new','1',10,'email'), delivery_event_key('u','g','new','1',10,'email'))


if __name__ == '__main__':
    unittest.main()
