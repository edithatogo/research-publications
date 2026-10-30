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

    def test_dataset_and_software_assertions_remain_candidates(self):
        for kind in ('Dataset','Software'):
            record=dict(RelationshipKind='datacite_output_reference',EvidenceKey='FIC-EVIDENCE',FromKey='datacite:10.1234/fictional',ToKey='doi:10.1234/publication',SourceSnapshotID='FIC-SNAPSHOT',SourceManifestSHA256='a'*64,ResourceTypeGeneralRaw=kind,ReviewState='Not reviewed',Confidence='candidate',IdentityQualified=False,CanonicalAdmission=False,MutationAuthorized=False,NativeG06Admission=False,SourceRecord={'id':'FICTIONAL'},CanonicalMatchCount=1,CanonicalKeys=['PUB:FIC'],CanonicalKey='PUB:FIC')
            h=append([],record,revision_id='r1',supersedes=None,state='active',reason='retained assertion')
            self.assertEqual(current(h)[0],record)
            withdrawn=append(h,record,revision_id='r2',supersedes='r1',state='withdrawn',reason='source correction')
            self.assertEqual(current(withdrawn),[])
            with self.assertRaises(ValueError): append([],dict(record,CanonicalAdmission=True),revision_id='r1',supersedes=None,state='active',reason='invalid promotion')

    def test_rehashed_malformed_history_is_not_accepted(self):
        from scripts.outcome_persistence import digest
        r=dict(RelationshipType='candidate_award_match',FromKey='AWARD:FIC:1',ToKey='PUB:FIC',AwardID='FIC-1',EvidenceURL='https://example.org/fictional',Confidence='candidate',ReviewStatus='Needs Review')
        h=append([],r,revision_id='r1',supersedes=None,state='active',reason='fictional')
        h[0]['state']='invalid'
        h[0]['sha256']=digest({k:v for k,v in h[0].items() if k!='sha256'})
        with self.assertRaises(ValueError):current(h)
