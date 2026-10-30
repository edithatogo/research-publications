import json
import unittest
from scripts.project_link_intake import prepare
from scripts.project_output_links import project_history

class ProjectLinkIntakeTests(unittest.TestCase):
    def fixture(self,kind='publication'):
        inventories={k:[] for k in ['project','publication','award','dataset','software']}
        inventories['project']=['fictional-project'];inventories[kind]=['fictional-output']
        empty={k:[] for k in inventories}
        snapshot={'item_id':1,'etag':'"1"','journal':json.dumps({'history':[],'inventories':empty,'complete':True}),'projection':json.dumps(project_history([],empty,complete=True))}
        revision={'record':{'project_id':'fictional-project','output_kind':kind,'output_id':'fictional-output','evidence_id':'fictional-evidence','evidence_revision':'v1','evidence_sha256':'a'*64,'status':'candidate'},'inventories':inventories,'complete':True,'revision_id':'r1','supersedes':None,'reason':'Fictional fixture'}
        return snapshot,revision

    def test_all_four_types_and_identical_replay(self):
        for kind in ['publication','award','dataset','software']:
            snapshot,r=self.fixture(kind);plan=prepare(snapshot,r)
            next_snapshot={**snapshot,**plan['after']}
            self.assertEqual(prepare(next_snapshot,r)['after'],plan['after'])
            self.assertFalse(any(json.loads(plan['after']['projection'])['bridges'].values()))

    def test_correction_withdrawal_retains_history(self):
        snapshot,r=self.fixture();first=prepare(snapshot,r)
        r={**r,'record':{**r['record'],'status':'reviewed'},'revision_id':'r2','supersedes':'r1'}
        second=prepare({**snapshot,**first['after']},r)
        self.assertEqual(len(json.loads(second['after']['projection'])['bridges']['publication']),1)
        r={**r,'record':{**r['record'],'status':'withdrawn'},'revision_id':'r3','supersedes':'r2'}
        third=prepare({**snapshot,**second['after']},r)
        self.assertEqual(len(json.loads(third['after']['journal'])['history']),3)
        self.assertEqual(json.loads(third['after']['projection'])['bridges']['publication'],[])

    def test_human_edit_and_stale_revision_refused(self):
        snapshot,r=self.fixture();plan=prepare(snapshot,r);current={**snapshot,**plan['after']}
        with self.assertRaises(ValueError):prepare({**current,'projection':'{}'},r)
        with self.assertRaises(ValueError):prepare(current,{**r,'revision_id':'r2'})

    def test_missing_inventory_and_changed_revision_refused(self):
        snapshot,r=self.fixture()
        with self.assertRaises(ValueError):prepare(snapshot,{**r,'complete':False})
        plan=prepare(snapshot,r)
        with self.assertRaises(ValueError):prepare({**snapshot,**plan['after']},{**r,'reason':'Different same revision'})
