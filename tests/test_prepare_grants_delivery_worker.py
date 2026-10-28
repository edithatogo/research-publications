# SPDX-License-Identifier: Apache-2.0
import base64,copy,json,unittest
from scripts.prepare_grants_delivery_worker import build

class DeliveryWorkerTests(unittest.TestCase):
 def fixture(self):
  c={'site':'https://example-my.sharepoint.com/personal/operator','operator_email':'operator@example.invalid','ledger_id':'12345678-1234-1234-1234-123456789abc','registry_id':'22345678-1234-1234-1234-123456789abc','watchlist_id':'32345678-1234-1234-1234-123456789abc','calendar_id':'42345678-1234-1234-1234-123456789abc','sharepoint_connection':'existing-sp','mail_connection':'existing-mail'}
  e={'Scope':'activation','Channel':'email','Recipient':c['operator_email'],'EventKey':'EVENT:'+base64.b64encode(b'["SYSTEM:G07","system_activation","fixture","email"]').decode(),'EventIdentity':'["SYSTEM:G07","system_activation","fixture","email"]','OpportunityKey':'SYSTEM:G07','EventType':'system_activation','Revision':'1','Subject':'RIMS grants: activation','BodyHtml':'<p>Activation test.</p>'};return c,e
 def test_one_send_follows_claim_and_repeat_branch_has_no_sender(self):
  c,e=self.fixture();before=copy.deepcopy((c,e));d=build(c,e);a=d['properties']['definition']['actions'];branch=a['If_unclaimed']
  self.assertEqual(branch['actions']['Send_once']['runAfter'],{'Claim_event':['Succeeded']});self.assertEqual(branch['else']['actions'],{})
  self.assertEqual(branch['actions']['Send_once']['inputs']['retryPolicy'],{'type':'none'})
  self.assertEqual(branch['actions']['Send_once']['inputs']['parameters']['emailMessage/To'],c['operator_email'])
  self.assertEqual(d['properties']['state'],'Stopped');self.assertEqual((c,e),before)
 def test_other_recipients_unreviewed_event_shapes_and_connections_rejected(self):
  for fault in ['recipient','event','connection']:
   c,e=self.fixture()
   if fault=='recipient':e['Recipient']='someone@example.invalid'
   elif fault=='event':e['Scope']='grant'
   else:c['mail_connection']='arbitrary/path'
   with self.assertRaises(ValueError):build(c,e)

 def test_receipt_only_explicitly_disables_claim_and_send_even_without_a_row(self):
  c,e=self.fixture();e['ReceiptOnly']=True;d=build(c,e)['properties']['definition']['actions']
  exclusion=d['If_unclaimed']['expression']['and'][1]
  self.assertEqual(exclusion,{'not':{'equals':["@outputs('Event')?['ReceiptOnly']",True]}})
  self.assertEqual(d['If_unclaimed']['else']['actions'],{})
  self.assertIn("['Attempt'],1",d['Guard_claim']['inputs'])
