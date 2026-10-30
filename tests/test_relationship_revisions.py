import unittest
from scripts.relationship_revisions import append,current

class RelationshipRevisionTests(unittest.TestCase):
    def test_correction_withdrawal_replay_and_stale_fork(self):
        r=dict(RelationshipType='candidate_award_match',FromKey='AWARD:FIC:1',ToKey='PUB:FIC',AwardID='FIC-1',EvidenceURL='https://example.org/fictional',Confidence='candidate',ReviewStatus='Needs Review')
        h=append([],r,revision_id='r1',supersedes=None,state='active',reason='fictional')
        corrected=dict(r,EvidenceURL='https://example.org/corrected')
        h2=append(h,corrected,revision_id='r2',supersedes='r1',state='active',reason='correct source')
        self.assertEqual(len(current(h2)),1);self.assertEqual(current(h)[0]['EvidenceURL'],r['EvidenceURL'])
        self.assertEqual(append(h2,corrected,revision_id='r2',supersedes='r1',state='active',reason='correct source'),h2)
        h3=append(h2,corrected,revision_id='r3',supersedes='r2',state='withdrawn',reason='withdraw assertion')
        self.assertEqual(current(h3),[])
        with self.assertRaises(ValueError):append(h3,r,revision_id='r4',supersedes='r1',state='active',reason='stale')
