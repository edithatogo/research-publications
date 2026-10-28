"""Fictional frozen topic inputs; no acquisition or native operations."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.dashboard_retained_chunks import reconstruct
from scripts.qualify_dashboard_topic_snapshot import qualify, read_rows
from tests.test_dashboard_topics import observation


class RetainedTopicSnapshotTests(unittest.TestCase):
    def fixture(self, root):
        work='https://openalex.org/W123'
        envelope=observation(dict(id=work,topics=[],mesh=[dict(descriptor_ui='D123')]))
        encoded=json.dumps(envelope).encode().hex()
        chunk={'[OpenAlexWorkID]':work,'[ChunkIndex]':0,'[ChunkCount]':1,
               '[MetadataCharacters]':len(encoded),'[MetadataChunk]':encoded,'[Encoding]':'UTF8-HEX'}
        context={'[OpenAlexWorkID]':work,'[CanonicalKey]':'fictional',
                 '[RawHash]':envelope['raw_response_sha256'],'[Observed]':envelope['observed_utc']}
        files=[]
        for name, rows in [('chunks',[chunk]),('context',[context]),('keys',[{'[CanonicalKey]':'fictional'}])]:
            p=root/(name+'.json');p.write_text(json.dumps({'results':[{'tables':[{'rows':rows}]}]}));files.append(p)
        catalogue=root/'desc.gz'
        catalogue.write_bytes(gzip.compress(b'<DescriptorRecordSet><DescriptorRecord><DescriptorUI>D123</DescriptorUI><DescriptorName><String>Fictional</String></DescriptorName><TreeNumberList><TreeNumber>A01.111</TreeNumber></TreeNumberList></DescriptorRecord></DescriptorRecordSet>'))
        return files+[catalogue,'2026',hashlib.sha256(catalogue.read_bytes()).hexdigest()],chunk

    def test_exact_chunk_catalogue_and_context_preserve_inputs_and_missing_taxonomy(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,_=self.fixture(Path(tmp));before=[p.read_bytes() for p in args[:4]]
            result=qualify(*args)
            self.assertEqual([p.read_bytes() for p in args[:4]],before)
            self.assertEqual(result['coverage']['MeSH']['classified'],1)
            self.assertEqual(result['coverage']['OpenAlex']['classified'],0)
            self.assertFalse(result['qualification']['native_model_write'])

    def test_partial_capture_and_context_drift_cannot_qualify(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,_=self.fixture(Path(tmp))
            value=json.loads(args[0].read_bytes());value['results'][0]['partial']=True
            args[0].write_text(json.dumps(value))
            with self.assertRaises(ValueError):qualify(*args)
            args,_=self.fixture(Path(tmp))
            value=json.loads(args[1].read_bytes());value['results'][0]['tables'][0]['rows'][0]['[RawHash]']='0'*64
            args[1].write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'fingerprint'):qualify(*args)

    def test_boolean_indices_duplicate_chunks_and_corrupt_catalogue_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,chunk=self.fixture(Path(tmp))
            for rows in [[dict(chunk,**{'[ChunkIndex]':False})],[chunk,copy.deepcopy(chunk)]]:
                with self.assertRaises(ValueError):reconstruct(rows,chunk['[OpenAlexWorkID]'])
            args[3].write_bytes(b'corrupted catalogue')
            with self.assertRaisesRegex(ValueError,'fingerprint'):qualify(*args)


if __name__=='__main__':unittest.main()
