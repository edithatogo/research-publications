# SPDX-License-Identifier: Apache-2.0
import copy,json,unittest
from scripts.grants_nih_observer import compare

class NihObserverTests(unittest.TestCase):
 def fixture(self):return {'errorcode':0,'data':{'id':357812,'opportunityNumber':'PA-25-301','synopsis':{'applicantTypes':[{'id':'fixture','description':'Synthetic category'}],'responseDateStr':'Apr13,2028','archiveDateStr':'May13,2028'},'revision':1}}
 def test_non200_is_rejected_before_parsing_even_if_body_looks_complete(self):
  base=self.fixture()
  for status in [206,401,403,429,500]:
   r=compare(status,b'not complete json',base);self.assertEqual(r['status'],'SOURCE_HTTP_REJECTED');self.assertTrue(r['last_good_preserved']);self.assertFalse(r['automatic_retry'])
 def test_observed_date_difference_is_distinct_from_description_and_no_zone_inferred(self):
  base=self.fixture();changed=copy.deepcopy(base);changed['data']['synopsis']['responseDateStr']='Apr14,2028'
  r=compare(200,json.dumps(changed).encode(),base);self.assertEqual(r['status'],'DEADLINE_CHANGED_REVIEW_REQUIRED');self.assertFalse(r['deadline_timezone_inferred']);self.assertTrue(r['last_good_preserved'])
  self.assertEqual(compare(200,json.dumps(base).encode(),base)['status'],'VERIFIED_UNCHANGED')

 def test_both_selected_envelopes_require_typed_success_and_exact_public_identity(self):
  for side in ['baseline','current']:
   for fault in ['false_success','float_identity','wrong_number','missing_number','not_object']:
    with self.subTest(side=side,fault=fault):
     baseline=self.fixture();current=copy.deepcopy(baseline)
     bad=baseline if side=='baseline' else current
     if fault=='false_success':bad['errorcode']=False
     elif fault=='float_identity':bad['data']['id']=357812.0
     elif fault=='wrong_number':bad['data']['opportunityNumber']='OTHER'
     elif fault=='missing_number':bad['data'].pop('opportunityNumber')
     else:
      if side=='baseline':baseline=[]
      else:current=[]
     with self.assertRaises(ValueError):compare(200,json.dumps(current).encode(),baseline)

 def test_description_change_requires_review_without_a_deadline_change(self):
  baseline=self.fixture();current=copy.deepcopy(baseline)
  current['data']['synopsis']['synopsisDesc']='Changed public description'
  before=copy.deepcopy(baseline)
  result=compare(200,json.dumps(current).encode(),baseline)
  self.assertEqual(result['status'],'SOURCE_CHANGED_REVIEW_REQUIRED')
  self.assertEqual(result['changed_date_fields'],{})
  self.assertFalse(result['actual_changed_deadline_observed'])
  self.assertEqual(baseline,before)
