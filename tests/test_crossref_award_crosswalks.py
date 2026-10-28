import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from scripts.crossref_award_crosswalks import project_packet as raw_project
from scripts.source_relationship_evidence import fingerprint


class CrossrefAwardCrosswalkTests(unittest.TestCase):
    def fixture(self, directory, number='123', funder='10.13039/1', duplicate=False):
        root = Path(directory)
        funding = {'DOI': funder, 'award': [number] * (2 if duplicate else 1)}
        crossref = {'status': 'ok', 'message': {'DOI': '10.1234/test', 'funder': [funding]}}
        ardc = {'status': 'OK', 'code': '200', 'data': {'offset': 0, 'numFound': 1, 'records': [
            {'type': 'grant', 'id': 'fixture-grant', 'purl': 'https://purl.org/au-research/grants/nhmrc/123', 'identifiers': ['123']}]}}
        authority = {'id': 'https://ror.org/fixture', 'links': [{'type': 'website', 'value': 'https://www.nhmrc.gov.au/'}],
                     'external_ids': [{'type': 'fundref', 'all': ['1']}]}
        files = []
        for name, value in [('crossref.json', crossref), ('ardc.json', ardc), ('authority.json', authority)]:
            raw = json.dumps(value).encode(); (root / name).write_bytes(raw)
            files.append({'name': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        manifest = {'next_links':[],'file_count':3,'crossref_count':1,'ardc_count':1,'kind': 'publication_award_crosswalk_retention_v1', 'batch': 'fixture-batch', 'namespace': 'nhmrc', 'complete': True,
            'files': files, 'authority': files[2],
            'crossref': [{'filename': 'crossref.json', 'doi': '10.1234/test', 'url': 'https://api.crossref.org/works/10.1234/test',
                          'observed_utc': '2026-10-21T00:00:00Z', 'complete':True,'next_links':[],'http_status':200,'sha256': files[0]['sha256']}],
            'ardc': [{'filename': 'ardc.json', 'original_identifier': number, 'complete': True,'next_links':[],'http_status':200,'observed_utc':None,
                      'sha256': files[1]['sha256'], 'url': 'https://researchdata.edu.au/api/v2.0/registry/activities?identifier=' + number}]}
        (root / 'manifest.json').write_text(json.dumps(manifest))
        if not hasattr(self,'pins'):self.pins={}
        self.pins[root]={'expected_manifest_sha256':hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),
            'authority_binding':dict(ror=authority['id'],namespace='nhmrc',fundref_dois=['10.13039/1'],
                evidence_ref='fixture://independently-pinned-binding',complete=True,authority_raw_sha256=files[2]['sha256'])}
        self.pins[root]['authority_binding_sha256']=fingerprint(self.pins[root]['authority_binding'])
        return root

    def arguments(self,root,pubs):
        args=dict(self.pins[root])
        args['generation']=dict(generation_id='fixture-generation',canonical_snapshot_id='fixture-canonical',
            source_snapshot_id='fixture-batch',complete=True,next_links=[],manifest_sha256=args['expected_manifest_sha256'],
            publication_count=len(pubs),publications_sha256=fingerprint(pubs),crossref_count=1,ardc_count=1)
        return args

    def project_packet(self,root,pubs):
        return raw_project(root,pubs,**self.arguments(root,pubs))

    def test_typed_identifier_edge_deduplicates_and_retains_both_sources(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.fixture(d, duplicate=True)
            rows = self.project_packet(root, [{'DOI': '10.1234/test', 'CanonicalKey': 'fixture:publication'}])
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['CanonicalKey'], 'fixture:publication')
            self.assertEqual(rows[0]['ReviewState'], 'Not reviewed')
            self.assertEqual(rows[0]['AuthenticationState'], 'Not authenticated')
            self.assertIn('ardcRawSHA256', json.loads(rows[0]['ReferenceType']))

    def test_funder_collision_not_admitted(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.project_packet(self.fixture(d, funder='10.13039/2'), []), [])

    def test_prefix_variant_not_silently_normalized(self):
        with tempfile.TemporaryDirectory() as d:
            rows=self.project_packet(self.fixture(d, number='APP123'), [])
            self.assertEqual(rows[0]['AliasState'],'no_exact_identifier')
            self.assertEqual(rows[0]['ToKey'],'')
            self.assertFalse(rows[0]['NativeG06Admission'])

    def test_ambiguous_canonical_assignment_retained_unadmitted(self):
        with tempfile.TemporaryDirectory() as d:
            rows = self.project_packet(self.fixture(d), [{'DOI': '10.1234/test', 'CanonicalKey': k} for k in ['fixture:a', 'fixture:b']])
            self.assertEqual(rows[0]['AdmissionState'], 'Ambiguous DOI')
            self.assertEqual(rows[0]['CanonicalKey'], '')

    def test_raw_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.fixture(d); (root / 'crossref.json').write_text('{}')
            with self.assertRaises(ValueError):
                self.project_packet(root, [])

    def test_provenance_hash_cannot_differ_from_verified_payload(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.fixture(d)
            manifest = json.loads((root / 'manifest.json').read_text())
            manifest['crossref'][0]['sha256'] = '0' * 64
            (root / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                self.project_packet(root, [])

    def test_authority_provenance_hash_must_match_verified_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.fixture(d)
            manifest = json.loads((root / 'manifest.json').read_text())
            manifest['authority']['sha256'] = '0' * 64
            (root / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                self.project_packet(root, [])

    def reseal(self,root):
        m=json.loads((root/'manifest.json').read_bytes())
        by_name={}
        for entry in m['files']:
            raw=(root/entry['name']).read_bytes();entry.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());by_name[entry['name']]=entry
        for ref in [m['authority'],*m['crossref'],*m['ardc']]:
            name=ref.get('name',ref.get('filename'));ref['sha256']=by_name[name]['sha256']
            if 'bytes' in ref:ref['bytes']=by_name[name]['bytes']
        (root/'manifest.json').write_text(json.dumps(m))
        self.pins[root]['expected_manifest_sha256']=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()

    def write(self,root,name,value):
        (root/name).write_text(json.dumps(value))

    def test_independent_authority_pin_cannot_be_rebound_with_outer_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);authority=json.loads((root/'authority.json').read_bytes());authority['id']='https://ror.org/other'
            self.write(root,'authority.json',authority);self.reseal(root)
            with self.assertRaisesRegex(ValueError,'Independent raw authority'):self.project_packet(root,[])
            args=self.arguments(root,[]);args['authority_binding']=dict(args['authority_binding'],ror='https://ror.org/other')
            with self.assertRaisesRegex(ValueError,'Independent complete authority'):raw_project(root,[],**args)

    def test_counts_completion_generations_and_canonical_identity_are_strict(self):
        for mode in ('complete','next','count','bool-count','query-http','query-complete','query-next','offset','total','bytes','reference-bytes','generation-hash','generation-complete','duplicate-canonical','pmid','pmid-pad','canonical-doi-pad'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                root=self.fixture(d);m=json.loads((root/'manifest.json').read_bytes());pubs=[{'DOI':'10.1234/test','CanonicalKey':'pub:1'}]
                if mode=='complete':m['complete']=1
                elif mode=='next':m['next_links']=['more']
                elif mode=='count':m['file_count']=4
                elif mode=='bool-count':m['crossref_count']=True
                elif mode=='query-http':m['crossref'][0]['http_status']=True
                elif mode=='query-complete':m['ardc'][0]['complete']='yes'
                elif mode=='query-next':m['ardc'][0]['next_links']=['more']
                elif mode=='bytes':m['files'][0]['bytes']=True
                elif mode=='reference-bytes':m['authority']['bytes']=True
                elif mode=='duplicate-canonical':pubs.append(dict(pubs[0]))
                elif mode=='pmid':pubs[0]['PMID']=True
                elif mode=='pmid-pad':pubs[0]['PMID']='13 '
                elif mode=='canonical-doi-pad':pubs[0]['DOI']='10.1234/test '
                if mode in ('offset','total'):
                    a=json.loads((root/'ardc.json').read_bytes());a['data']['offset' if mode=='offset' else 'numFound']=False if mode=='offset' else True
                    self.write(root,'ardc.json',a);self.reseal(root)
                else:
                    self.write(root,'manifest.json',m);self.pins[root]['expected_manifest_sha256']=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()
                args=self.arguments(root,pubs)
                if mode=='generation-hash':args['generation']['publications_sha256']='0'*64
                elif mode=='generation-complete':args['generation']['complete']=False
                with self.assertRaises(ValueError):raw_project(root,pubs,**args)

    def test_strict_json_inventory_paths_and_duplicate_queries_rejected(self):
        for mode in ('duplicate-json','nan','overflow','extra','unreferenced','symlink','duplicate-files','duplicate-query','duplicate-record','payload-next','payload-error','work-error'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                root=self.fixture(d)
                if mode in ('duplicate-json','nan','overflow'):
                    (root/'crossref.json').write_bytes({'duplicate-json':b'{"status":"ok","status":"error"}','nan':b'{"x":NaN}','overflow':b'{"x":1e999}'}[mode]);self.reseal(root)
                elif mode=='extra':(root/'unexpected.json').write_bytes(b'{}')
                elif mode=='symlink':
                    raw=(root/'crossref.json').read_bytes();(root/'crossref.json').unlink();(root/'target.json').write_bytes(raw);(root/'crossref.json').symlink_to(root/'target.json')
                elif mode in ('payload-next','payload-error','work-error'):
                    name='crossref.json' if mode=='work-error' else 'ardc.json';a=json.loads((root/name).read_bytes())
                    if mode=='payload-next':a['data']['@odata.nextLink']='more'
                    elif mode=='payload-error':a['data']['error']='partial'
                    else:a['message']['error']='failed'
                    self.write(root,name,a);self.reseal(root)
                elif mode=='duplicate-record':
                    a=json.loads((root/'ardc.json').read_bytes());a['data']['records']*=2;a['data']['numFound']=2;self.write(root,'ardc.json',a);self.reseal(root)
                else:
                    m=json.loads((root/'manifest.json').read_bytes())
                    if mode=='duplicate-files':m['files'].append(dict(m['files'][0]));m['file_count']=4
                    elif mode=='duplicate-query':m['crossref'].append(dict(m['crossref'][0]));m['crossref_count']=2
                    else:
                        raw=b'{}';(root/'unused.json').write_bytes(raw);m['files'].append(dict(name='unused.json',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()));m['file_count']=4
                    self.write(root,'manifest.json',m);self.pins[root]['expected_manifest_sha256']=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()
                args=self.arguments(root,[])
                if mode=='duplicate-query':args['generation']['crossref_count']=2
                with self.assertRaises(ValueError):raw_project(root,[],**args)

    def test_exact_doi_pmid_purl_award_and_query_identities_preserve_no_match(self):
        for mode in ('requested-doi','returned-doi','funder-doi','number','purl','query-number','url'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                root=self.fixture(d);m=json.loads((root/'manifest.json').read_bytes())
                if mode=='requested-doi':m['crossref'][0]['doi']=' 10.1234/test'
                elif mode=='query-number':m['ardc'][0]['original_identifier']=' 123'
                elif mode=='url':m['crossref'][0]['url']='https://untrusted.invalid/works/10.1234/test'
                elif mode=='purl':
                    a=json.loads((root/'ardc.json').read_bytes());a['data']['records'][0]['purl']+=' ';self.write(root,'ardc.json',a)
                else:
                    c=json.loads((root/'crossref.json').read_bytes())
                    if mode=='returned-doi':c['message']['DOI']+=' '
                    elif mode=='funder-doi':c['message']['funder'][0]['DOI']+=' '
                    else:c['message']['funder'][0]['award'][0]=' 123'
                    self.write(root,'crossref.json',c)
                self.write(root,'manifest.json',m);self.reseal(root)
                with self.assertRaises(ValueError):self.project_packet(root,[])
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);a=json.loads((root/'ardc.json').read_bytes());a['data']['records'][0]['purl']='https://purl.org/au-research/grants/nhmrc/APP123'
            self.write(root,'ardc.json',a);self.reseal(root)
            result=self.project_packet(root,[])
            self.assertEqual(result[0]['AliasState'],'no_exact_identifier');self.assertEqual(result[0]['ToKey'],'')

    def test_ambiguity_and_missing_lookup_are_visible_candidate_diagnostics(self):
        for mode in ('ambiguous','missing'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                root=self.fixture(d)
                if mode=='ambiguous':
                    a=json.loads((root/'ardc.json').read_bytes());a['data']['records'].append(dict(a['data']['records'][0],id='other'));a['data']['numFound']=2
                    self.write(root,'ardc.json',a)
                else:
                    c=json.loads((root/'crossref.json').read_bytes());c['message']['funder'][0]['award']=['999'];self.write(root,'crossref.json',c)
                self.reseal(root);r=self.project_packet(root,[{'DOI':'10.1234/test','CanonicalKey':'pub:1'}])[0]
                self.assertEqual(r['AliasState'],'ambiguous_award_identifier' if mode=='ambiguous' else 'missing_retained_grant_lookup')
                self.assertEqual(r['RelationshipKind'],'publication_award_crosswalk_diagnostic');self.assertEqual(r['ToKey'],'')
                self.assertFalse(r['CanonicalAdmission']);self.assertFalse(r['NativeG06Admission']);self.assertFalse(r['MutationAuthorized'])
                if mode=='ambiguous':self.assertEqual(len(r['AliasMatches']),2)

    def test_replay_occurrences_revisions_unknown_dates_and_cardinality(self):
        import copy
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d,duplicate=True);m=json.loads((root/'manifest.json').read_bytes());m['crossref'][0]['observed_utc']=None
            self.write(root,'manifest.json',m);self.reseal(root)
            pubs=[{'DOI':'10.1234/test','CanonicalKey':'pub:1','ReviewStatus':'Human reviewed','Date':None}];before=copy.deepcopy(pubs)
            first=self.project_packet(root,pubs);self.assertEqual(first,self.project_packet(root,pubs));self.assertEqual(pubs,before)
            self.assertEqual(len(first),1);self.assertEqual(len(first[0]['SourcePaths']),2);self.assertIsNone(first[0]['ObservedUTC'])
            self.assertEqual(len({r['CanonicalKey'] for r in first if r['ToKey']}),1)
            c=json.loads((root/'crossref.json').read_bytes());c['message']['title']=['Source revision'];self.write(root,'crossref.json',c);self.reseal(root)
            second=self.project_packet(root,pubs)
            self.assertEqual(first[0]['EvidenceKey'],second[0]['EvidenceKey']);self.assertNotEqual(first[0]['SourceVersion'],second[0]['SourceVersion']);self.assertNotEqual(first[0]['ProjectionRevisionSHA256'],second[0]['ProjectionRevisionSHA256'])
            self.assertEqual(second[0]['SourceBatch'],'fixture-batch');self.assertFalse(second[0]['IdentityQualified'])
            from scripts.grants_relationships import normalize_relationship
            with self.assertRaises(ValueError):normalize_relationship(second[0])

    def test_each_verified_artifact_is_read_once_and_imports_close_under_stdlib(self):
        import subprocess
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            root=self.fixture(d);args=self.arguments(root,[]);counts={};read=Path.read_bytes
            def capture(path):
                counts[path.name]=counts.get(path.name,0)+1
                return read(path)
            with patch.object(Path,'read_bytes',capture):raw_project(root,[],**args)
            self.assertEqual(counts,{'manifest.json':1,'crossref.json':1,'ardc.json':1,'authority.json':1})
        repo=Path(__file__).resolve().parents[1]
        for cwd,code in ((repo,'from scripts import award_identifier_crosswalks,crossref_award_crosswalks'),(repo/'scripts','import award_identifier_crosswalks,crossref_award_crosswalks')):
            result=subprocess.run([sys.executable,'-S','-c',code],cwd=cwd,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
