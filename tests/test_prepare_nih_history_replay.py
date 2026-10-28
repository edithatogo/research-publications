# SPDX-License-Identifier: Apache-2.0
import copy
import json
import unittest
from scripts.prepare_nih_history_replay import prepare


def fixture():
    synopsis={'opportunityId':357812,'agencyName':'NIH','agencyDetails':{'agencyName':'NIH'},'synopsisDesc':'current text',
              'applicantEligibilityDesc':'current eligibility','responseDateStr':'2028-01-07-00-00-00'}
    data={'id':357812,'revision':1,'opportunityNumber':'PA-25-301','opportunityTitle':'Title','synopsis':synopsis}
    history={'opportunityId':357812,'revision':0,'opportunityNumber':'PA-25-301',
             'opportunityTitle':'Title','synopsis':copy.deepcopy(synopsis)}
    history['synopsis']['synopsisDesc']='authentic old fixture text'
    data['opportunityHistoryDetails']=[history]
    record={'OpportunityKey':'GRANT:'+'a'*24,'Source':'us-grants-gov-nih-pa-25-301','SourceID':'357812',
            'RoundID':'PA-25-301','ReviewStatus':'Needs Review','Title':'Title','Funder':'NIH',
            'Description':'current text','Eligibility':'current eligibility','EvidenceHash':'a'*64,'FunderKey':None,'CategoryKeysJSON':'[]','ClassificationEvidenceJSON':None}
    return {'errorcode':0,'data':data},record


class HistoryReplayTests(unittest.TestCase):
    def test_actual_changed_text_retains_identity_review_and_exact_inverse(self):
        d,r=fixture();original=copy.deepcopy(r);result=prepare(json.dumps(d).encode(),r)
        self.assertEqual(result['actual_text_fields_changed'],['Description'])
        self.assertEqual(result['source_identity']['ReviewStatus'],'Needs Review')
        self.assertEqual(result['restore_payload']['Description'],r['Description'])
        self.assertFalse(result['execution_enabled']);self.assertFalse(result['deadline_or_schedule_changed'])
        self.assertEqual(r,original)
        self.assertIsNone(result['historical_payload']['FunderKey'])

    def test_wrong_opportunity_revision_current_preimage_and_date_change_fail_closed(self):
        for fault in ['identity','revision','preimage','date']:
            d,r=fixture()
            if fault=='identity':d['data']['opportunityHistoryDetails'][0]['opportunityId']=1
            elif fault=='revision':d['data']['opportunityHistoryDetails'][0]['revision']=1
            elif fault=='preimage':r['Description']='concurrent edit'
            else:d['data']['opportunityHistoryDetails'][0]['synopsis']['responseDateStr']='2028-01-08-00-00-00'
            with self.assertRaises(ValueError):prepare(json.dumps(d).encode(),r)

    def test_no_change_or_approved_record_cannot_be_relabelled(self):
        d,r=fixture();d['data']['opportunityHistoryDetails'][0]['synopsis']['synopsisDesc']='current text'
        with self.assertRaises(ValueError):prepare(json.dumps(d).encode(),r)
        d,r=fixture();r['ReviewStatus']='Reviewed'
        with self.assertRaises(ValueError):prepare(json.dumps(d).encode(),r)

    def test_typed_success_identity_revision_and_raw_inputs_fail_closed(self):
        for fault in ['boolean-success','numeric-source','float-history-id','bool-revision','negative-revision','missing-key','bad-hash','bad-synopsis','bad-history','missing-restore']:
            d,r=fixture()
            if fault=='boolean-success':d['errorcode']=False
            elif fault=='numeric-source':r['SourceID']=357812
            elif fault=='float-history-id':d['data']['opportunityHistoryDetails'][0]['opportunityId']=357812.0
            elif fault=='bool-revision':d['data']['opportunityHistoryDetails'][0]['revision']=False
            elif fault=='negative-revision':d['data']['opportunityHistoryDetails'][0]['revision']=-1
            elif fault=='missing-key':r.pop('OpportunityKey')
            elif fault=='bad-hash':r['EvidenceHash']='not-a-hash'
            elif fault=='bad-synopsis':d['data']['synopsis']=[]
            elif fault=='missing-restore':r.pop('ClassificationEvidenceJSON')
            else:d['data']['opportunityHistoryDetails'][0]=None
            with self.subTest(fault=fault),self.assertRaises(ValueError):prepare(json.dumps(d).encode(),r)
        d,r=fixture()
        for raw in [None,'{}',b'[]',b'{',b'{"errorcode":0,"data":null}']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):prepare(raw,r)

    def test_raw_and_selected_subtree_hashes_bind_restore_without_mutating_dates(self):
        import hashlib
        d,r=fixture();r['CategoryKeysJSON']='["health"]';r['FunderKey']='funder:fixture'
        r['ClassificationEvidenceJSON']='{"fixture":true}'
        raw=json.dumps(d).encode();old=copy.deepcopy(r);result=prepare(raw,r)
        self.assertEqual(result['source_evidence']['source_response_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['source_evidence']['source_pointer'],'/data/opportunityHistoryDetails/0')
        self.assertEqual(result['historical_payload']['EvidenceHash'],result['source_evidence']['historical_subtree_sha256'])
        self.assertEqual(result['restore_payload']['ClassificationEvidenceJSON'],old['ClassificationEvidenceJSON'])
        self.assertFalse(result['source_evidence']['live_provider_transition_claimed'])
        self.assertFalse(result['source_evidence']['opportunity_reviewed'])
        self.assertFalse(result['notification_activation'])
        self.assertNotIn('Deadline',result['historical_payload'])
        self.assertEqual(r,old)
