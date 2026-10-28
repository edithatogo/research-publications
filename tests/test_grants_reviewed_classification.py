# SPDX-License-Identifier: Apache-2.0
import copy
import json
import unittest
from scripts.grants_reviewed_classification import reviewed_mapping, apply_mapping, model_candidate, FIELDS
from scripts.audit_grants_classification import audit
from scripts.grants_planning import subscribers


class ReviewedClassificationTests(unittest.TestCase):
    def setUp(self):
        self.row = {'OpportunityKey': 'GRANT:'+'a'*24, 'Source': 'us-grants-gov-nih-pa-25-301',
                    'SourceID': '357812', 'RoundID': 'PA-25-301', 'EvidenceHash': 'b'*64,
                    'Funder': 'National Institutes of Health', 'ReviewStatus': 'Needs Review'}
        agency = {'agencyCode': 'HHS-NIH11', 'agencyName': self.row['Funder']}
        self.doc = {'errorcode': 0, 'data': {'id': 357812, 'opportunityNumber': 'PA-25-301',
                    'owningAgencyCode': 'HHS-NIH11', 'agencyDetails': agency,
                    'synopsis': {'agencyDetails': copy.deepcopy(agency), 'agencyCode': 'HHS-NIH11',
                                 'agencyName': self.row['Funder'],
                                 'fundingActivityCategories': [{'id': c, 'description': c} for c in ['ED','ENV','FN','HL','ISS']]}}}
    def raw(self): return json.dumps(self.doc).encode()

    def test_all_source_codes_and_review_state_preserved(self):
        mapping = reviewed_mapping(self.row, self.raw())
        output = apply_mapping(self.row, mapping, self.raw())
        self.assertEqual(len(mapping['CategoryKeys']), 5)
        self.assertEqual({k:v for k,v in output.items() if k not in FIELDS}, self.row)
        self.assertEqual(output['ReviewStatus'], 'Needs Review')
        self.assertEqual(audit([output])['rows_with_both_key_types'], 1)
        self.assertNotIn('token', output['ClassificationEvidenceJSON'])

    def test_source_identity_missing_codes_and_duplicates_refused(self):
        for mutate in (lambda d:d['data'].update(id=1),
                       lambda d:d['data']['synopsis'].update(agencyCode='other'),
                       lambda d:d['data']['synopsis'].update(fundingActivityCategories=[]),
                       lambda d:d['data']['synopsis']['fundingActivityCategories'].append({'id':'HL','description':'duplicate'})):
            d=copy.deepcopy(self.doc);mutate(d)
            with self.assertRaises(ValueError): reviewed_mapping(self.row,json.dumps(d).encode())

    def test_stale_forged_and_existing_assignments_refused(self):
        mapping=reviewed_mapping(self.row,self.raw())
        for row,m,raw in (({**self.row,'EvidenceHash':'c'*64},mapping,self.raw()),
                          (self.row,{**mapping,'FunderKey':'forged'},self.raw()),
                          ({**self.row,'FunderKey':'existing'},mapping,self.raw()),
                          (self.row,mapping,self.raw()+b' ')):
            with self.assertRaises(ValueError): apply_mapping(row,m,raw)

    def test_existing_matcher_consumes_each_category_and_funder_without_duplicate_user(self):
        mapping=reviewed_mapping(self.row,self.raw())
        opportunity={**self.row,'CategoryKeys':mapping['CategoryKeys'],'FunderKey':mapping['FunderKey']}
        subscriptions=[{'UserKey':'operator','Scope':'category','TargetKey':key,'Active':True} for key in mapping['CategoryKeys']]
        subscriptions.append({'UserKey':'operator','Scope':'funder','TargetKey':mapping['FunderKey'],'Active':True})
        self.assertEqual(subscribers(opportunity,subscriptions),['operator'])


    def test_typed_identity_and_success_cannot_be_coerced(self):
        for field,value in [('SourceID',357812),('OpportunityKey',False),('EvidenceHash',False)]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                reviewed_mapping({**self.row,field:value},self.raw())
        for field,value in [('errorcode',False),('id',357812.0)]:
            doc=copy.deepcopy(self.doc)
            if field=='errorcode':doc[field]=value
            else:doc['data'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):reviewed_mapping(self.row,json.dumps(doc).encode())

    def test_malformed_envelope_and_missing_agency_name_fail_with_domain_error(self):
        for value in [[],{'errorcode':0,'data':[]},{'errorcode':0,'data':{'synopsis':[]}}]:
            with self.subTest(value=value),self.assertRaises(ValueError):reviewed_mapping(self.row,json.dumps(value).encode())
        doc=copy.deepcopy(self.doc);doc['data']['synopsis']['agencyDetails'].pop('agencyName');doc['data']['agencyDetails'].pop('agencyName');doc['data']['synopsis'].pop('agencyName')
        with self.assertRaises(ValueError):reviewed_mapping({k:v for k,v in self.row.items() if k!='Funder'},json.dumps(doc).encode())

    def test_model_preparation_is_explicitly_unsupported_without_touching_input(self):
        document={'definition':{'parts':[{'path':'synthetic-only','payload':'eA=='}]}}
        before=copy.deepcopy(document)
        with self.assertRaisesRegex(ValueError,'outside this source-only'):model_candidate(document)
        self.assertEqual(document,before)
