# SPDX-License-Identifier: Apache-2.0
import json,unittest
from datetime import datetime
import hashlib
from pathlib import Path
import tempfile
from unittest.mock import patch
from scripts.grants_live_delivery import candidates
from scripts.grants_live_delivery import dispatch_snapshot

class LiveDeliveryTests(unittest.TestCase):
 def fixture(self):
  s={'Id':14,'OpportunityKey':'GRANT:'+'a'*24,'EvidenceHash':'b'*64,'ReviewStatus':'Reviewed','FunderKey':'fund','CategoryKeysJSON':'["cat"]','ClassificationEvidenceJSON':json.dumps({'source_evidence_hash':'b'*64,'FunderKey':'fund','CategoryKeys':['cat']}),'Title':'A grant <reviewed>','URL':'https://example.invalid/grant'}
  r={'Id':1,'UserKey':'7','Active':True,'SubscriptionState':'active','Channel':'email','Scope':'opportunity','TargetKey':s['OpportunityKey'],'EventTypesJSON':'["opportunity_changed","deadline_changed","reminder"]','ReminderOffsetsJSON':'[7,1]','Cadence':'daily','Timezone':'Australia/Brisbane'}
  return s,r
 def plan(self,s,r,ledger=None,calendar=None):return candidates([s],calendar or [],[r],ledger or [],now=datetime.fromisoformat('2026-10-28T08:05:00+10:00'),recipient='operator@example.invalid',user_key='7')
 def test_review_current_evidence_owner_and_active_consent_all_required(self):
  s,r=self.fixture();self.assertEqual(len(self.plan(s,r)),1)
  for source,rule in [({**s,'ReviewStatus':'Needs Review'},r),({**s,'EvidenceHash':'changed'},r),(s,{**r,'Active':False}),(s,{**r,'UserKey':'someone-else'})]:self.assertEqual(self.plan(source,rule),[])
 def test_existing_unknown_or_dry_run_identity_prevents_automatic_resend(self):
  s,r=self.fixture();event=self.plan(s,r)[0]
  for state in ['pending_attempt','unknown','succeeded']:
   self.assertEqual(self.plan(s,r,[{'Title':event['EventKey'],'Status':state,'DryRun':True}]),[])
  self.assertIn('&lt;reviewed&gt;',event['BodyHtml']);self.assertNotIn('ReviewNotes',event['BodyHtml'])
 def test_daily_window_and_exact_date_reminders(self):
  s,r=self.fixture();d={'Id':1,'OpportunityKey':s['OpportunityKey'],'DeadlineKey':'DEADLINE:'+'c'*24,'Revision':'revision1','ReviewStatus':'Reviewed','RevisionApplied':True,'Cancelled':False,'DeadlinePrecision':'day','Calendar_x0020_day':'2026-11-04'}
  events=self.plan(s,r,calendar=[d]);self.assertEqual({e['EventType'] for e in events},{'opportunity_changed','deadline_changed','reminder'})
  self.assertEqual(next(e['OffsetDays'] for e in events if e['EventType']=='reminder'),7)
  self.assertEqual(candidates([s],[d],[r],[],now=datetime.fromisoformat('2026-10-28T07:59:00+10:00'),recipient='operator@example.invalid',user_key='7'),[])

 def dispatch_fixture(self, directory):
  s,r=self.fixture()
  rows={'registry':[s],'calendar':[],'watchlist':[r],'ledger':[]}
  config={'outbox':str(Path(directory)/'outbox'),'context':{'operator_email':'operator@example.invalid'},'operator_user_key':'7'}
  health={'healthy':True,'sources':[{'source':'fixture','status':'VERIFIED_UNCHANGED'}]}
  return rows,config,health

 def test_unsubscribe_after_snapshot_prevents_worker_construction(self):
  with tempfile.TemporaryDirectory() as directory:
   rows,config,health=self.dispatch_fixture(directory)
   def read_record(store, identity):
    row=rows[store][0]
    self.assertEqual(identity,row['Id'])
    return {**row,'odata.etag':'"1"',**({'Active':False} if store=='watchlist' else {})}
   with patch('scripts.grants_live_delivery.MailWorker',side_effect=AssertionError('No native worker allowed')):
    result=dispatch_snapshot(config,rows,read_record,now=datetime.fromisoformat('2026-10-28T08:05:00+10:00'),directory=directory,health=health)
   self.assertEqual(result['eligible_grant_notices'],1)
   self.assertIn('no submission',result['submissions'][0]['disposition'])
   self.assertFalse(list(Path(directory).rglob('*-intent.json')))

 def test_prior_one_send_intent_survives_and_blocks_all_native_calls(self):
  with tempfile.TemporaryDirectory() as directory:
   rows,config,health=self.dispatch_fixture(directory)
   event=self.plan(rows['registry'][0],rows['watchlist'][0])[0]
   target=Path(config['outbox'])/hashlib.sha256(event['EventKey'].encode()).hexdigest()/'qualification-prior'
   target.mkdir(parents=True);intent=target/'invoke-intent.json';intent.write_text('{"one_send":true}')
   with patch('scripts.grants_live_delivery.MailWorker',side_effect=AssertionError('No native worker allowed')):
    result=dispatch_snapshot(config,rows,lambda *args:self.fail('No read after a one-send intent'),now=datetime.fromisoformat('2026-10-28T08:05:00+10:00'),directory=directory,health=health)
   self.assertIn('prior_one_send_journal_preserved',result['submissions'][0]['disposition'])
   self.assertEqual(intent.read_text(),'{"one_send":true}')

 def test_needs_review_produces_zero_submissions_without_native_calls(self):
  with tempfile.TemporaryDirectory() as directory:
   rows,config,health=self.dispatch_fixture(directory);rows['registry'][0]['ReviewStatus']='Needs Review'
   with patch('scripts.grants_live_delivery.MailWorker',side_effect=AssertionError('No native worker allowed')):
    result=dispatch_snapshot(config,rows,lambda *args:self.fail('No eligible record to reread'),now=datetime.fromisoformat('2026-10-28T08:05:00+10:00'),directory=directory,health=health)
   self.assertEqual(result['eligible_grant_notices'],0)
   self.assertEqual(result['submissions'],[])
