import base64,hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from project_retained_openalex_fields import project
class Alignment(unittest.TestCase):
    def envelope(self,**payload):
        p={'id':'https://openalex.org/W1','doi':'https://doi.org/10.1000/example',**payload};raw=json.dumps(p).encode()
        return {'kind':'openalex_retained_observation_v1','source':'OpenAlex','http_status':200,'work_id':p['id'],'requested_doi':'10.1000/example','observed_utc':'2026-01-01T00:00:00Z','raw_response_base64':base64.b64encode(raw).decode(),'raw_byte_count':len(raw),'raw_response_sha256':hashlib.sha256(raw).hexdigest()}
    def test_current_funding_and_keyword_fields_are_not_lost(self):
        fields=project(self.envelope(funders=[{'display_name':'Funder'}],awards=[{'funder_display_name':'Other','funder_award_id':'A1'}],keywords=[{'display_name':'Clinical research'}]))['fields']
        self.assertEqual(fields['FunderNames'],'Funder; Other');self.assertEqual(fields['GrantIDs'],'A1');self.assertEqual(fields['AuthorKeywords'],'Clinical research')
    def test_all_values_survive_without_old_presentation_caps(self):
        fields=project(self.envelope(mesh=[{'descriptor_name':str(i)} for i in range(20)],keywords=[{'display_name':str(i)} for i in range(20)],authorships=[{'raw_affiliation_strings':[str(i)],'affiliations':[]} for i in range(8)]))['fields']
        self.assertEqual(len(fields['MeSHHeadings'].split('; ')),20);self.assertEqual(len(fields['AuthorKeywords'].split('; ')),20);self.assertEqual(len(fields['AffiliationsRaw'].split('; ')),8)
    def test_null_zero_and_canonical_classification_boundaries(self):
        out=project(self.envelope(cited_by_count=0,title='Provider title',primary_topic={'field':{'display_name':'Different taxonomy'}},open_access=None))
        self.assertEqual(out['fields']['CitationCount_OpenAlex'],0);self.assertIsNone(out['fields']['OAUrl']);self.assertNotIn('Title',out['fields']);self.assertNotIn('FieldOfResearch',out['fields']);self.assertIn('primary_topic',out['retained_only_top_level_fields'])
    def test_fingerprint_rejects_corrupt_transport(self):
        env=self.envelope();env['raw_response_sha256']='wrong'
        with self.assertRaises(ValueError):project(env)

    def test_envelope_and_raw_identity_must_match(self):
        env=self.envelope();env['requested_doi']='10.1000/other'
        with self.assertRaisesRegex(ValueError,'DOI identity'):project(env)
        env=self.envelope(id='https://openalex.org/W1?foreign=1')
        with self.assertRaisesRegex(ValueError,'Work identity'):project(env)
        env=self.envelope();del env['requested_doi']
        with self.assertRaisesRegex(ValueError,'DOI identity'):project(env)

    def test_retention_preparer_output_projects_with_exact_identity(self):
        from prepare_openalex_retention import build
        source=json.dumps([{'DOI':'10.1000/example'}]).encode()
        raw=json.dumps({'id':'https://openalex.org/W1',
                        'doi':'https://doi.org/10.1000/example', 'cited_by_count':0}).encode()
        candidate={'input_sha256':hashlib.sha256(source).hexdigest(),
                   'observations':{'10.1000/example':{'status':'success','http_status':200,
                       'observed_utc':'2026-01-01T00:00:00Z','raw_payload':json.loads(raw),
                       'raw_response_base64':base64.b64encode(raw).decode(),
                       'raw_response_sha256':hashlib.sha256(raw).hexdigest()}}}
        retained=build(source,candidate)
        encoded=''.join(c['MetadataChunk'] for c in sorted(retained['chunks'],key=lambda x:x['ChunkIndex']))
        envelope=json.loads(bytes.fromhex(encoded))
        projection=project(envelope)
        self.assertEqual(projection['fields']['CitationCount_OpenAlex'],0)
        self.assertFalse(projection['native_acceptance'])

class PhysicalLimits(unittest.TestCase):
    def test_oversized_candidate_never_trims_or_alters_full_source_evidence(self):
        from project_retained_openalex_fields import apply_qualified_limits
        original={'fields':{k:None for k in ['FunderNames','GrantIDs','MeSHHeadings','AuthorKeywords','AffiliationsRaw']},'provenance':[{'Field':'GrantIDs','CandidateValue':'0123456789','Decision':'compatible_candidate','RawResponseSHA256':'raw-link'}]}
        original['fields']['GrantIDs']='0123456789'
        limits={k:100 for k in original['fields']};limits['GrantIDs']=5
        checked=apply_qualified_limits(original,limits)
        self.assertIsNone(checked['fields']['GrantIDs']);self.assertEqual(checked['provenance'][0]['CandidateValue'],'0123456789');self.assertEqual(checked['provenance'][0]['Decision'],'projection_rejected_size');self.assertEqual(original['fields']['GrantIDs'],'0123456789')
