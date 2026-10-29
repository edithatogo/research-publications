import base64,gzip,hashlib,json,sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_openalex_retention import build
from extend_openalex_native_bootstrap import extend
class Increment(unittest.TestCase):
    def stage(self,n):
        doi='10.1000/item'+str(n);payload={'id':'https://openalex.org/W'+str(n),'doi':'https://doi.org/'+doi,'cited_by_count':0};raw=json.dumps(payload).encode();frozen=json.dumps([{'DOI':doi}]).encode()
        return build(frozen,{'input_sha256':hashlib.sha256(frozen).hexdigest(),'observations':{doi:{'status':'success','http_status':200,'observed_utc':'2026-01-01T00:00:00Z','raw_payload':payload,'raw_response_base64':base64.b64encode(raw).decode(),'raw_response_sha256':hashlib.sha256(raw).hexdigest()}}})
    def baseline(self,old):
        raw=json.dumps(old).encode();encoded=base64.b64encode(gzip.compress(raw,mtime=0)).decode();text='expression Before = 1\nexpression OpenAlexBootstrapDocument = Json.Document(Binary.Decompress(Binary.FromText("'+encoded+'",BinaryEncoding.Base64),Compression.GZip))\nexpression After = 2\n'
        return {'definition':{'format':'TMDL','parts':[{'path':'definition/expressions.tmdl','payloadType':'InlineBase64','payload':base64.b64encode(text.encode()).decode()},*[{'path':'unchanged'+str(n),'payloadType':'InlineBase64','payload':base64.b64encode(b'unchanged').decode()} for n in range(45)]]}}
    def test_only_compressed_source_changes_and_prior_raw_chunks_survive(self):
        old=self.stage(1);baseline=self.baseline(old);result,merged,receipt=extend(baseline,self.stage(2))
        self.assertEqual(result['definition']['parts'][1:],baseline['definition']['parts'][1:])
        self.assertEqual(merged['chunks'][:len(old['chunks'])],old['chunks'])
        self.assertEqual(merged['expected_keys'],['https://openalex.org/W1','https://openalex.org/W2'])
        self.assertEqual(receipt['preserved_parts'],45)
    def test_failed_or_partial_increment_cannot_advance_history(self):
        new=self.stage(2);new['attempt_statuses'][0]['Status']='unavailable'
        with self.assertRaises(ValueError):extend(self.baseline(self.stage(1)),new)
        new=self.stage(2);new['source_scope_dois'].append('10.1000/unobserved')
        with self.assertRaises(ValueError):extend(self.baseline(self.stage(1)),new)
    def test_existing_identity_or_corrupt_raw_cannot_replace_cache(self):
        with self.assertRaises(ValueError):extend(self.baseline(self.stage(1)),self.stage(1))
        new=self.stage(2);new['chunks'][0]['MetadataChunk']='00'+new['chunks'][0]['MetadataChunk'][2:]
        with self.assertRaises((ValueError,json.JSONDecodeError)):extend(self.baseline(self.stage(1)),new)
