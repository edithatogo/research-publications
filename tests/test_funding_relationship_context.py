import copy
import unittest
from scripts.prepare_funding_relationship_context import prepare, prepare_views, prepare_consumer, prepare_identity_material
from scripts.grants_relationships import normalize_relationship


class FundingContextTests(unittest.TestCase):
    def inputs(self):
        registry = {'complete': True, 'list': {'ItemCount': 1}, 'items': [
            {'Id': 1, 'field_1': 'pubmed:123', 'field_2': 'PUB:retained-key',
             'GrantIDs': 'LP1; LP1; OTHER', 'FunderNames': 'Unpaired labels', 'field_17': 'Included'}]}
        publication = [{'CanonicalKey': 'PMID:123', 'PMID': '123', 'Title': 'Source title',
                        'PubMedURL': 'https://pubmed.ncbi.nlm.nih.gov/123/'}]
        awards = [{'RecordKind': 'Award', 'Source': 'arc', 'SourceID': 'LP1', 'AwardCode': 'LP1',
                   'Funder': 'Australian Research Council', 'Status': 'Closed', 'Title': 'Award title',
                   'URL': 'https://dataportal.arc.gov.au/NCGP/API/grants/LP1'}]
        return registry, publication, awards

    def test_exact_candidates_preserve_keys_evidence_and_inputs(self):
        inputs = self.inputs(); before = copy.deepcopy(inputs); result = prepare(*inputs)
        self.assertEqual(inputs, before); self.assertEqual(len(result['relationships']), 1)
        link = result['relationships'][0]
        self.assertEqual(link['ToKey'], 'PUB:retained-key')
        self.assertEqual(link['FromKey'], 'AWARD:arc:LP1')
        self.assertEqual(link['RelationshipType'], 'candidate_award_match')
        self.assertEqual((link['Confidence'], link['ReviewStatus']), ('candidate', 'Needs Review'))
        self.assertEqual(result['context'][0]['PublicationCanonicalKey'], 'PMID:123')
        self.assertEqual(result['coverage']['confirmed_funding'], 0)

    def test_duplicate_tokens_do_not_duplicate_relationship_and_replay_identity_stable(self):
        inputs = self.inputs(); first = prepare(*inputs)
        inputs[0]['items'][0]['GrantIDs'] = 'OTHER; LP1'
        second = prepare(*inputs)
        self.assertEqual(first['relationships'], second['relationships'])
        self.assertEqual(first['coverage']['duplicate_retained_tokens_collapsed'], 1)

    def test_no_case_fuzzy_funder_or_topic_matching(self):
        inputs = self.inputs(); inputs[0]['items'][0]['GrantIDs'] = 'lp1; PREFIX-LP1'
        self.assertEqual(prepare(*inputs)['relationships'], [])

    def test_duplicate_award_code_and_orphan_canonical_are_explicit(self):
        inputs = self.inputs(); other = copy.deepcopy(inputs[2][0]); other['SourceID'] = 'different'
        inputs[2].append(other); result = prepare(*inputs)
        self.assertFalse(result['relationships']); self.assertEqual(result['unresolved'][0]['Reason'], 'ambiguous_award_code')
        inputs = self.inputs(); inputs[1].clear(); result = prepare(*inputs)
        self.assertEqual(result['unresolved'][0]['Reason'], 'canonical_publication_identity_unresolved')

    def test_exclusion_and_ambiguous_registry_identity_not_admitted(self):
        inputs = self.inputs(); inputs[0]['items'][0]['field_17'] = 'Excluded'
        self.assertEqual(prepare(*inputs)['unresolved'][0]['Reason'], 'publication_explicitly_excluded')
        inputs = self.inputs(); duplicate = copy.deepcopy(inputs[0]['items'][0]); duplicate['Id'] = 2
        inputs[0]['items'].append(duplicate); inputs[0]['list']['ItemCount'] = 2
        self.assertTrue(all(x['Reason'] == 'publication_registry_identity_ambiguous' for x in prepare(*inputs)['unresolved']))

    def test_incomplete_snapshot_wrong_source_and_wrong_citation_refused(self):
        inputs = self.inputs(); inputs[0]['complete'] = False
        with self.assertRaises(ValueError): prepare(*inputs)
        inputs = self.inputs(); inputs[2][0]['RecordKind'] = 'Opportunity'
        with self.assertRaises(ValueError): prepare(*inputs)
        inputs = self.inputs(); inputs[1][0]['PubMedURL'] = 'https://pubmed.ncbi.nlm.nih.gov/456/'
        with self.assertRaises(ValueError): prepare(*inputs)

    def test_current_native_review_overrides_candidate_preparation_without_mutation(self):
        accepted = prepare(*self.inputs())
        row = {**accepted['relationships'][0], 'Id': 3, '__metadata': {'etag': '"4"'},
               'ReviewStatus': ' Withdrawn ', 'Modified': '2026-10-18T00:00:00Z'}
        native = {'complete': True, 'list': {'ItemCount': 1}, 'items': [row]}
        before = copy.deepcopy((native, accepted))
        packet = prepare_consumer(native, accepted)
        self.assertEqual((native, accepted), before)
        self.assertEqual(packet['rows'][0]['ReviewStatusRaw'], ' Withdrawn ')
        self.assertEqual(packet['rows'][0]['AdmissionState'], 'unclassified')
        self.assertEqual(packet['rows'][0]['NativeETag'], '"4"')
        self.assertEqual(packet['coverage']['candidates'], 0)
        self.assertEqual(packet['rows'][0]['PublicationCanonicalKey'], 'PMID:123')
        row.update(RelationshipType='funded_by_award', Confidence='confirmed', ReviewStatus='Reviewed')
        # Changing the type alone cannot bypass the existing typed identity contract.
        self.assertEqual(prepare_consumer(native, accepted)['coverage']['confirmed_reviewed'], 0)
        identity = {k: v for k, v in row.items() if k in {
            'RelationshipType', 'FromKey', 'ToKey', 'AwardID', 'EvidenceURL', 'Confidence', 'ReviewStatus'}}
        row['RelationshipKey'] = normalize_relationship(identity)['RelationshipKey']
        self.assertEqual(prepare_consumer(native, accepted)['coverage']['confirmed_reviewed'], 1)
        row['ReviewStatus'] = 'Reviewed '
        self.assertEqual(prepare_consumer(native, accepted)['coverage']['confirmed_reviewed'], 0)

    def test_consumer_retains_unmapped_rows_and_refuses_incomplete_or_duplicate_identity(self):
        accepted = prepare(*self.inputs())
        row = {**accepted['relationships'][0], 'Id': 3, 'ToKey': 'PUB:unknown'}
        native = {'complete': True, 'list': {'ItemCount': 1}, 'items': [row]}
        packet = prepare_consumer(native, accepted)
        self.assertEqual(packet['rows'][0]['AdmissionState'], 'unresolved_identity')
        self.assertEqual(packet['rows'][0]['ToKey'], 'PUB:unknown')
        self.assertIsNone(packet['rows'][0]['PublicationCanonicalKey'])
        native['complete'] = False
        with self.assertRaises(ValueError): prepare_consumer(native, accepted)
        native['complete'] = True
        native['items'].append({**row, 'Id': 4}); native['list']['ItemCount'] = 2
        with self.assertRaises(ValueError): prepare_consumer(native, accepted)

    def test_identity_material_has_no_review_state_and_binds_changed_evidence(self):
        accepted = prepare(*self.inputs())
        row = {**accepted['relationships'][0], 'Id': 3}
        native = {'complete': True, 'list': {'ItemCount': 1}, 'items': [row]}
        material = prepare_identity_material(native, accepted)
        self.assertEqual(len(material), 2)
        self.assertEqual({r['RelationshipType'] for r in material}, {'candidate_award_match', 'funded_by_award'})
        self.assertTrue(all('ReviewStatus' not in r and 'Confidence' not in r for r in material))
        row.update(ReviewStatus='Withdrawn', Confidence='review')
        self.assertEqual(prepare_identity_material(native, accepted), material)
        row.update(ReviewStatus='Needs Review', Confidence='candidate', EvidenceURL='https://example.test/new-evidence')
        changed = prepare_identity_material(native, accepted)
        self.assertEqual(len(changed), 4)
        matching = [m for m in changed if m['RelationshipType'] == row['RelationshipType']
                    and m['EvidenceURL'] == row['EvidenceURL']]
        self.assertNotEqual(matching[0]['RelationshipKey'], row['RelationshipKey'])
        self.assertEqual(prepare_consumer(native, accepted)['coverage']['candidates'], 0)

    def test_view_roles_do_not_promote_candidates_and_exclude_withdrawals(self):
        columns = ['LinkTitle', 'RelationshipType', 'AwardID', 'EvidenceURL', 'Confidence',
                   'ReviewStatus', 'FromKey', 'ToKey', 'RelationshipKey', 'Modified']
        rows = [{'Id': i, 'RelationshipType': kind, 'Confidence': confidence, 'ReviewStatus': status}
                for i, kind, confidence, status in [
                    (1, 'candidate_award_match', 'candidate', 'Needs Review'),
                    (2, 'candidate_award_match', 'candidate', 'Withdrawn'),
                    (3, 'funded_by_award', 'confirmed', 'Reviewed'),
                    (4, 'funded_by_award', 'candidate', 'Reviewed'),
                    (5, 'candidate_award_match', 'confirmed', 'Reviewed')]]
        before = {'complete': True, 'list': {'ItemCount': len(rows)}, 'items': rows,
                  'fields': [{'InternalName': n} for n in columns], 'views': [],
                  'site_url': 'https://example.test/site', 'list_id': 'retained-target'}
        plan = prepare_views(before)
        self.assertEqual(plan['expected_ids'], {'candidates': [1], 'confirmed': [3]})
        self.assertTrue(all(c['desired']['Paged'] and c['desired']['RowLimit'] == 100 for c in plan['changes']))
        for status in ['Unrecognized', None, '']:
            before['items'][0]['ReviewStatus'] = status
            self.assertEqual(prepare_views(before)['expected_ids']['candidates'], [])
        for status in [' Withdrawn ', ' Needs Review ', 'Reviewed ']:
            before['items'][0]['ReviewStatus'] = status
            with self.assertRaises(ValueError): prepare_views(before)


if __name__ == '__main__': unittest.main()
