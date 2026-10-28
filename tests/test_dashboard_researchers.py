"""Fictional identifiers test ambiguity, order and distinct collaboration counts."""
import unittest
from scripts.dashboard_researchers import build_researchers
from tests.test_dashboard_topics import observation


class ResearcherProjectionTests(unittest.TestCase):
    def assertion(self, person='A1', label='Same name', institution='I1', orcid=None):
        return dict(author=dict(id='https://openalex.org/'+person, display_name=label, orcid=orcid),
                    author_position='first', institutions=[dict(id='https://openalex.org/'+institution,
                                                              display_name='Fictional institution')])

    def build(self, assertions, extra=None):
        work=dict(id='https://openalex.org/W1', authorships=assertions)
        observations=[observation(work)]
        cross={work['id']:['p1']}
        if extra:
            observations.append(observation(dict(id='https://openalex.org/W2', authorships=extra)))
            cross['https://openalex.org/W2']=['p2']
        return build_researchers(['p1','p2','p3'], observations, cross)

    def test_same_name_different_ids_and_order_preserved(self):
        result=self.build([self.assertion(), self.assertion('A2')])
        self.assertEqual(len(result['people']),2)
        self.assertEqual([x['author_ordinal'] for x in result['authorships']],[1,2])
        self.assertEqual(result['coverage']['publications_without_provider_author_ids'],2)
        self.assertFalse(result['employment_inference'])

    def test_reversed_duplicate_pairs_count_distinct_works_and_repeat(self):
        a=self.assertion();b=self.assertion('A2',institution='I2')
        result=self.build([a,b,a],[b,a])
        self.assertEqual(len(result['coauthor_pairs']),1)
        self.assertEqual(result['coauthor_pairs'][0]['shared_publications'],2)
        self.assertTrue(result['coauthor_pairs'][0]['repeat'])
        self.assertEqual(len(result['institution_pairs']),1)

    def test_unresolved_mentions_and_orcid_conflicts_do_not_merge(self):
        a=self.assertion(orcid='https://orcid.org/fictional')
        b=self.assertion('A2',orcid='https://orcid.org/fictional')
        unknown=self.assertion();unknown['author']['id']=None
        result=self.build([a,b,unknown])
        self.assertEqual(len(result['people']),2)
        self.assertIsNone(result['authorships'][-1]['person_key'])
        self.assertEqual({d['reason'] for d in result['diagnostics']},
                         {'unresolved_author_id','orcid_asserted_by_multiple_provider_ids'})

    def test_unlabelled_valid_ids_are_retained_in_dimensions(self):
        assertion=self.assertion(label=None)
        assertion['institutions'][0]['display_name']=None
        result=self.build([assertion])
        self.assertEqual(result['people'][0]['label_status'],'Unknown label')
        self.assertEqual(result['organisations'][0]['label_status'],'Unknown label')

    def test_multiple_orcids_are_retained_without_selecting_one(self):
        result=self.build([self.assertion(orcid='raw-alias-1')],
                          [self.assertion(orcid='raw-alias-2')])
        self.assertEqual(len(result['people']),1)
        self.assertIn('multiple_orcids_for_provider_id',
                      {d['reason'] for d in result['diagnostics']})

    def test_multiple_snapshots_and_noncanonical_crosswalk_rejected(self):
        work=dict(id='https://openalex.org/W1',authorships=[self.assertion()])
        other=dict(work,authorships=[])
        with self.assertRaisesRegex(ValueError,'one dated'):
            build_researchers(['p1'],[observation(work),observation(other)],{work['id']:['p1']})
        with self.assertRaisesRegex(ValueError,'noncanonical'):
            build_researchers(['p1'],[observation(work)],{work['id']:['outside']})

    def test_duplicate_snapshot_and_aliases_preserve_identity(self):
        a=self.assertion();other=self.assertion(label='Variant name')
        result=self.build([a],[other])
        self.assertEqual(result['people'][0]['labels'],['Same name','Variant name'])
        self.assertEqual(result['people'][0]['label_status'],'Conflicting labels')
        work=dict(id='https://openalex.org/W1',authorships=[a])
        env=observation(work)
        repeated=build_researchers(['p1'],[env,env],{work['id']:['p1','p1']})
        self.assertEqual(len(repeated['authorships']),1)


if __name__=='__main__':unittest.main()
