"""Native relationship planning without authentication or tenant access."""
import copy
import unittest
from scripts.relationship_intake import prepare, validate_plan


def revision(**changes):
    value={'record':{'RelationshipType':'candidate_award_match','FromKey':'AWARD:fictional:ONE','ToKey':'PUB:fictional','AwardID':'ONE','EvidenceURL':'https://example.invalid/evidence','Confidence':'candidate','ReviewStatus':'Fictional - not reviewed'},'revision_id':'r1','supersedes':None,'state':'active','reason':'Fictional fixture'}
    value.update(changes)
    return value


class RelationshipIntakeTests(unittest.TestCase):
    def test_create_replay_correction_withdrawal(self):
        first=prepare(None,revision())
        snapshot={'item_id':8,'etag':'"1"','fields':first['after']}
        replay=prepare(snapshot,revision())
        self.assertEqual(first['after'],replay['after'])
        r=revision(revision_id='r2',supersedes='r1');r['record']['EvidenceURL']='https://example.invalid/correction'
        corrected=prepare(snapshot,r)
        self.assertNotEqual(first['after']['RelationshipKey'],corrected['after']['RelationshipKey'])
        withdrawn=prepare({'item_id':8,'etag':'"2"','fields':corrected['after']},{**r,'revision_id':'r3','supersedes':'r2','state':'withdrawn'})
        self.assertEqual(withdrawn['after']['ReviewStatus'],'Withdrawn')
        self.assertEqual(withdrawn['after']['Confidence'],'review')

    def test_human_edits_legacy_and_stale_revision_refused(self):
        p=prepare(None,revision());s={'item_id':8,'etag':'"1"','fields':p['after']}
        changed=copy.deepcopy(s);changed['fields']['ReviewStatus']='Human correction'
        with self.assertRaises(ValueError):prepare(changed,revision())
        changed['fields']['RelationshipHistory']=''
        with self.assertRaises(ValueError):prepare(changed,revision())
        with self.assertRaises(ValueError):prepare(s,revision(revision_id='r2'))

    def test_tampered_history_and_confirmed_creation_refused(self):
        p=prepare(None,revision());p['after']['Confidence']='confirmed'
        with self.assertRaises(ValueError):validate_plan(p)
        r=revision();r['record'].update(RelationshipType='funded_by_award',Confidence='confirmed',ReviewStatus='Reviewed')
        with self.assertRaises(ValueError):prepare(None,r)

    def test_url_description_preserved(self):
        p=prepare(None,revision());s={'item_id':8,'etag':'"1"','fields':p['after']}
        s['fields']['EvidenceURL']['Description']='Human evidence description'
        self.assertEqual(prepare(s,revision())['after']['EvidenceURL']['Description'],'Human evidence description')
