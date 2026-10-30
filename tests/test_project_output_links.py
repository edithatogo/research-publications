import unittest
from scripts.project_output_links import prepare,KINDS

class ProjectLinkTests(unittest.TestCase):
    def test_typed_links_exclude_candidates_and_withdrawals_without_fanout(self):
        inventory={'project':['FIC-P'],**{k:['FIC-'+k] for k in KINDS}}
        records=[dict(project_id='FIC-P',output_kind=k,output_id='FIC-'+k,evidence_id='FIC-E-'+k,evidence_revision='1',evidence_sha256='a'*64,status='reviewed' if k in {'publication','dataset'} else 'candidate') for k in sorted(KINDS)]
        result=prepare(records,inventory,complete=True)
        self.assertEqual(len(result['bridges']['publication']),1);self.assertEqual(result['bridges']['award'],[])
        self.assertEqual(len(result['records']),4);self.assertFalse(result['native_acceptance'])
        records[0]['status']='withdrawn'
        self.assertEqual(prepare(records,inventory,complete=True)['bridges']['award'],[])
    def test_unknown_and_duplicate_identity_refused(self):
        inventory={'project':['FIC-P'],**{k:['FIC-'+k] for k in KINDS}}
        r=dict(project_id='FIC-P',output_kind='publication',output_id='FIC-publication',evidence_id='FIC-E',evidence_revision='1',evidence_sha256='a'*64,status='reviewed')
        with self.assertRaises(ValueError):prepare([r,r],inventory,complete=True)
        with self.assertRaises(ValueError):prepare([dict(r,output_kind='dataset')],inventory,complete=True)
