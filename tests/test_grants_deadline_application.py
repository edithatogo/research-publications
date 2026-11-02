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
