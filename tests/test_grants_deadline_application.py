import hashlib
import json
import unittest

from scripts.grants_deadline_application import application, prepare_override
from tests import test_grants_internal_deadlines as fixtures


def scenario(fixture, context):
    fixture.snapshot['policies'] = [fixture.record()]
    fixture.snapshot['calendar'][0]['Id'] = 1
    basis = json.dumps([fixture.deadline,'TEST_ONLY','1',1],separators=(',',':'))
    row = dict(OverrideKey='OVERRIDE:'+hashlib.sha256(basis.encode()).hexdigest()[:24],
               OverrideRevision=1,AnchorDeadlineKey=fixture.deadline,AnchorDate='2026-12-31',
               AnchorPrecision='day',PolicyKey='TEST_ONLY',PolicyVersion='1',CalculatedDate='2026-12-26',
               OverrideDate='2026-12-24',OverrideReason='Fictional review',ReviewStatus='Reviewed',
               RecordedAtUTC='2026-11-01T00:00:00Z')
    options=dict(organisation='FIXTURE',as_of='2026-11-02',evidence_files=fixture.files)
    return prepare_override(context,fixture.snapshot,row,**options),row,options


class DeadlineApplicationTests(unittest.TestCase):
    def test_approved_override_and_missing_policy(self):
        f=fixtures.InternalDeadlineTests();f.setUp();self.addCleanup(f.doCleanups)
        c={k:'00000000-0000-0000-0000-000000000001' for k in ('override_id','policy_id','calendar_id')}
        flow,row,options=scenario(f,dict(c,site='https://example.invalid',sharepoint_connection='fixture'))
        self.assertIn('PolicyMatches',flow['definition']['actions']['Existing']['runAfter'])
        f.snapshot['overrides']=[{'OverrideKey':row['OverrideKey'],'OverrideJson':json.dumps(row)}]
        self.assertEqual(application(f.snapshot,**options)[0]['EffectiveDate'],'2026-12-24')
        f.snapshot['policies']=[]
        held=application(f.snapshot,**options)[0]
        self.assertIsNone(held['EffectiveDate'])
        self.assertEqual(held['SourceDate'],'2026-12-31')

    def test_calendar_writes_only_separate_internal_identity(self):
        import base64
        from scripts.grants_deadline_calendar import prepare
        f=fixtures.InternalDeadlineTests();f.setUp();self.addCleanup(f.doCleanups)
        c={k:'00000000-0000-0000-0000-000000000001' for k in ('override_id','policy_id','registry_id','calendar_id')}
        c.update(site='https://example.invalid',sharepoint_connection='fixture')
        _,row,options=scenario(f,c)
        f.snapshot['registry'][0].update(Id=1,**{'odata.etag':'"1"'})
        f.snapshot['overrides']=[{'Id':1,'odata.etag':'"1"','OverrideKey':row['OverrideKey'],'OverrideJson':json.dumps(row)}]
        actions=prepare(c,f.snapshot,**options)['definition']['actions']
        params=actions['Apply0']['inputs']['parameters']
        payload=json.loads(base64.b64decode(params['parameters/body'].split("'")[1]))
        self.assertTrue(payload['DeadlineKey'].startswith('INTERNAL:'))
        self.assertEqual(payload['Calendar_x0020_day'],'2026-12-24')
        self.assertEqual(actions['Apply0']['runAfter'],{'CurrentDay':['Succeeded']})

    def test_reader_requires_actual_applied_date(self):
        f=fixtures.InternalDeadlineTests();f.setUp();self.addCleanup(f.doCleanups)
        f.snapshot['policies']=[f.record()]
        options=dict(organisation='FIXTURE',as_of='2026-11-02',evidence_files=f.files)
        with self.assertRaisesRegex(ValueError,'membership'):
            application(f.snapshot,require_applied=True,**options)
