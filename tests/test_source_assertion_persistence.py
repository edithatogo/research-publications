import copy
import json
import unittest
from scripts.source_assertion_persistence import prepare,request,reconcile,schema_requirements,FIELDS


def revision(kind='Dataset',**changes):
    record=dict(RelationshipKind='datacite_output_reference',EvidenceKey='fictional-source-evidence',FromKey='datacite:10.1234/fictional',ToKey='doi:10.1234/publication',SourceSnapshotID='fictional-snapshot',SourceManifestSHA256='a'*64,ResourceTypeGeneralRaw=kind,ReviewState='Not reviewed',Confidence='candidate',IdentityQualified=False,CanonicalAdmission=False,MutationAuthorized=False,NativeG06Admission=False,SourceRecord={'id':'fictional','extra':{'preserved':True}},CanonicalMatchCount=1,CanonicalKeys=['PUB:fictional'],CanonicalKey='PUB:fictional')
    return dict(record=record,revision_id='r1',supersedes=None,state='active',reason='Fictional local fixture',**changes)


class SourceAssertionPersistenceTests(unittest.TestCase):
    def test_both_kinds_create_replay_uncertain_write(self):
        for kind in ['Dataset','Software']:
            plan=prepare(None,revision(kind));write=request(plan,None)['write']
            self.assertEqual(write['path'],'/items');self.assertNotIn('OperatorNotes',write['body'])
            current={'item_id':9,'etag':'"1"','fields':plan['after']}
            self.assertIsNone(request(plan,current)['write'])
            self.assertEqual(reconcile(plan,current)['outcome'],'candidate_present')
            self.assertFalse(reconcile(plan,None)['retry_allowed'])
            stored=json.loads(plan['after']['SourceProjectionJSON'])['assertions'][0]
            self.assertEqual(stored,revision(kind)['record'])

    def test_correction_and_withdrawal_preserve_lineage_and_history(self):
        r=revision();first=prepare(None,r);snapshot={'item_id':9,'etag':'"1"','fields':first['after']}
        r=copy.deepcopy(r);r.update(revision_id='r2',supersedes='r1');r['record']['EvidenceKey']='corrected-evidence';r['record']['ToKey']='doi:10.1234/corrected'
        second=prepare(snapshot,r);self.assertEqual(first['after']['SourceKey'],second['after']['SourceKey'])
        write=request(second,snapshot)['write'];self.assertEqual(write['headers']['IF-MATCH'],'"1"');self.assertNotIn('Title',write['body'])
        r.update(revision_id='r3',supersedes='r2',state='withdrawn')
        third=prepare({'item_id':9,'etag':'"2"','fields':second['after']},r)
        self.assertEqual(json.loads(third['after']['SourceProjectionJSON'])['assertions'],[])
        self.assertEqual(len(json.loads(third['after']['SourceProvenanceJSON'])['history']),3)

    def test_human_edits_stale_etag_and_collision_refused(self):
        r=revision();first=prepare(None,r);current={'item_id':9,'etag':'"1"','fields':first['after']};r.update(revision_id='r2',supersedes='r1');second=prepare(current,r)
        with self.assertRaises(ValueError):request(second,{**current,'etag':'"2"'})
        changed=copy.deepcopy(current);changed['fields']['FullSummary']='Human summary'
        with self.assertRaises(ValueError):prepare(changed,r)
        with self.assertRaises(ValueError):request(first,changed)
        with self.assertRaises(ValueError):request(second,{'item_id':10,'etag':'"1"','fields':second['after']})
        self.assertEqual(reconcile(second,changed)['outcome'],'conflict')

    def test_no_admission_kind_drift_or_diagnostic_promotion(self):
        r=revision();r['record']['CanonicalAdmission']=True
        with self.assertRaises(ValueError):prepare(None,r)
        r=revision();first=prepare(None,r);r.update(revision_id='r2',supersedes='r1');r['record']['ResourceTypeGeneralRaw']='Software'
        with self.assertRaises(ValueError):prepare({'item_id':9,'etag':'"1"','fields':first['after']},r)
        r=revision();r['record']['RelationshipKind']='datacite_output_diagnostic'
        with self.assertRaises(ValueError):prepare(None,r)

    def test_schema_uncertainty_and_capacity_are_visible(self):
        schema=[{'InternalName':k,'TypeAsString':v} for k,v in FIELDS.items()]
        checks=schema_requirements(schema);self.assertTrue(any(x['outcome']=='unverified' for x in checks))
        schema[0]['EnforceUniqueValues']=False
        self.assertTrue(any(x['outcome']=='fail' for x in schema_requirements(schema)))
        r=revision();r['record']['SourceRecord']['oversized']='x'*61000
        with self.assertRaises(ValueError):prepare(None,r)
