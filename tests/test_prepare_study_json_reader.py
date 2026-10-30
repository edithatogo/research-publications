import io
import json
import hashlib
import zipfile
import unittest
from scripts.prepare_study_json_reader import prepare, qualify_zip
from scripts.deploy_report_definition import fingerprint, parts
from scripts.prepare_outcome_reader import emit
from scripts.prepare_study_archive_path_fix import PATH


def fixture(wrong_id=False):
    n='NCT00000001';raw=json.dumps({'protocolSection':{'identificationModule':{'nctId':'NCT00000002' if wrong_id else n},'referencesModule':{'references':[{'pmid':'123','type':'RESULT'}]}}}).encode()
    digest=hashlib.sha256(raw).hexdigest()
    m={'source':'ClinicalTrials.gov','count':1,'files':[{'name':n+'.json','bytes':len(raw),'sha256':digest}], 'observations':[{'id':n,'status':200,'bytes':len(raw),'sha256':digest,'source_url':'https://clinicaltrials.gov/api/v2/studies/'+n}]}
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr(n+'.json',raw);z.writestr('source-manifest.json',json.dumps(m))
    return buf.getvalue()


class StudyJSONTests(unittest.TestCase):
    def test_zip_is_not_json_and_verified_member_is(self):
        raw=fixture()
        with self.assertRaises((ValueError,UnicodeError)):json.loads(raw)
        members=qualify_zip(raw,hashlib.sha256(raw).hexdigest())
        import base64,zlib
        body=json.loads(zlib.decompress(base64.b64decode(members['NCT00000001']['payload']),-15))
        self.assertEqual(body['protocolSection']['referencesModule']['references'],[{'pmid':'123','type':'RESULT'}])

    def test_archive_and_identity_drift_refused(self):
        raw=fixture()
        with self.assertRaises(ValueError):qualify_zip(raw,'0'*64)
        raw=fixture(True)
        with self.assertRaises(ValueError):qualify_zip(raw,hashlib.sha256(raw).hexdigest())

    def test_transformation_preserves_projection_and_indentation(self):
        model={'definition':{'parts':[]}}
        old='StudyEvidence=List.Combine(List.Transform(Table.ToRecords(StudyRows),(R)=>let SE=Json.Document(ReadStudy(R[ArchiveFileURL]))'
        suffix=',S=SE[response][body],Valid=ExistingIdentityGuards in ExistingOutput)),\n'
        emit(model,PATH,'table SourceRelationshipEvidence\n\t\t\t\t'+old+suffix)
        emit(model,'definition/model.tmdl','model Preserved')
        raw=fixture();kw={'expected_sha256':fingerprint(model),'archive_url':'https://example.invalid/archive.zip','archive_bytes':raw,'archive_sha256':hashlib.sha256(raw).hexdigest()}
        result=prepare(model,**kw);self.assertEqual(result,prepare(model,**kw))
        s=parts(result['candidate'])[PATH].decode()
        self.assertTrue(s.endswith(suffix));self.assertIn('\n\t\t\t\tStudyJSONRows=',s)
        self.assertEqual(parts(result['candidate'])['definition/model.tmdl'],parts(model)['definition/model.tmdl'])
        self.assertEqual(result['recovery'],model)
        self.assertIn('error "Unqualified study archive format"',s)
        self.assertIn('Member[sha256]=R[SourcePayloadSHA256]',s)
