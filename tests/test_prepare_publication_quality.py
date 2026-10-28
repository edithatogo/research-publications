# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from scripts import prepare_publication_quality as quality
from scripts.prepare_publication_registry_bootstrap import sha
from scripts.prepare_publication_views import definitions
from tests.test_prepare_publication_registry_bootstrap import metadata_snapshot

class QualityTests(unittest.TestCase):
    def inputs(self):
        s=metadata_snapshot();s['views'][2]['ViewQuery']=definitions('0001-01','0001-02')['uncertainty']['ViewQuery'];pin=sha(s)
        d=dict(complete=True,registry_sha256=pin,rule_version='fixture:v1',source_revision='source:v1',
            preserved_semantic_items=[dict(id=1,field='Title',registry='Retained',canonical='=Unapproved')])
        c=dict(complete=True,registry_sha256=pin,source_revision='source:v1',source_sha256='a'*64,case_count=1,difference_count=1,
            cases=[dict(case_id='case:1',records=[dict(record_id='registry:1',source_key='pubmed:1'),dict(record_id='canonical-for:1',source_key='pubmed:1',values={'Title':'=Unapproved'})])])
        return s,d,c

    def test_exact_paired_values_versions_unknowns_and_provenance_survive(self):
        inputs=self.inputs();original=copy.deepcopy(inputs);data=quality.build(*inputs)
        self.assertEqual(data['differences'][0]['CanonicalSourceValue'],'=Unapproved')
        self.assertEqual(data['coverage']['unknown_month_count'],1)
        self.assertEqual(data['rule_version'],'fixture:v1');self.assertFalse(data['write_authorized'])
        self.assertEqual(inputs,original)

    def test_stale_values_mixed_generations_duplicate_cases_and_false_counts_fail(self):
        for fault in ['value','generation','duplicate','count','hash']:
            s,d,c=self.inputs()
            if fault=='value':s['items'][0]['Title']='changed'
            elif fault=='generation':c['source_revision']='other'
            elif fault=='duplicate':c['cases']*=2
            elif fault=='count':c['case_count']=99
            else:c['source_sha256']='unknown'
            with self.subTest(fault=fault),self.assertRaises(ValueError):quality.build(s,d,c)

    def test_local_artifacts_keep_raw_json_and_spreadsheet_safety_without_upload(self):
        s,d,c=self.inputs();data,payloads,plan=quality.prepare(s,d,c,'/Documents/fictional',uncertainty_view_id=s['views'][2]['Id'])
        self.assertTrue(any(b"'=Unapproved" in raw for name,raw in payloads.items() if name.endswith('.csv')))
        self.assertEqual(data['differences'][0]['CanonicalSourceValue'],'=Unapproved')
        self.assertFalse(plan['details']['link_existence_verified'])
        self.assertEqual(plan['inputs']['source_sha256'],'a'*64)
        self.assertEqual(data['differences'][0]['Status'],'Informational; no correction adjudicated')
        with self.assertRaises(ValueError):quality.prepare(s,d,c,'/../elsewhere',uncertainty_view_id=s['views'][2]['Id'])

    def saved(self):
        from tests.test_prepare_publication_registry_bootstrap import view,guid,query_evidence
        s,d,c=self.inputs();data,payloads,p=quality.prepare(s,d,c,'/Documents/fictional',uncertainty_view_id=s['views'][2]['Id'])
        after=copy.deepcopy(s);v=view('quality',99);change=p['changes'][0];v.update(copy.deepcopy(change['desired']));v['resolvedFields']['Items']['results']=change['fields'];after['views'].append(v);after['counts']['views']+=1
        effects=dict(complete=True,site_url=s['site_url'],list_id=s['list_id'],plan_sha256=p['plan_sha256'],capture_reference='fixture:files',observedAtUTC=s['observedAtUTC'],created_views={'quality':v['Id']},files=[])
        for i,(name,wanted) in enumerate(p['details']['files'].items()):
            effects['files'].append(dict(name=name,unique_id=guid(100+i),etag='"1"',status=200,server_relative_url=p['details']['server_folder']+'/'+name,**wanted))
        results={name:[dict(Id=i,SourceKey=next(r['field_1'] for r in s['items'] if r['Id']==i),field_6=next(r.get('field_6') for r in s['items'] if r['Id']==i),field_8=next(r.get('field_8') for r in s['items'] if r['Id']==i)) for i in ids] for name,ids in p['details']['expected_ids'].items()}
        return s,d,c,p,after,effects,query_evidence(s,p,results)

    def test_exact_stored_bytes_view_and_query_receipts_are_compared(self):
        s,d,c,p,after,effects,queries=self.saved();original=copy.deepcopy((s,p,after,effects,queries))
        report=quality.reconcile(s,p,after,effects,queries,expected_plan_sha256=p['plan_sha256'])
        self.assertFalse(report['native_acceptance']);self.assertEqual(report['preserved_items'],3)
        self.assertEqual((s,p,after,effects,queries),original)

    def test_file_receipts_cannot_substitute_paths_ids_counts_or_hashes(self):
        for fault in ('missing','duplicate','hash','path','identity','etag','bool','target','partial','plan'):
            s,d,c,p,after,effects,queries=self.saved();f=effects['files'][0]
            if fault=='missing':effects['files'].pop()
            elif fault=='duplicate':effects['files'][1]=copy.deepcopy(f)
            elif fault=='hash':f['sha256']='0'*64
            elif fault=='path':f['server_relative_url']='/elsewhere/'+f['name']
            elif fault=='identity':effects['files'][1]['unique_id']=f['unique_id']
            elif fault=='etag':f['etag']='*'
            elif fault=='bool':f['bytes']=True
            elif fault=='target':effects['list_id']='other'
            elif fault=='partial':effects['complete']=False
            else:effects['plan_sha256']='f'*64
            with self.subTest(fault=fault),self.assertRaises(ValueError):quality.reconcile(s,p,after,effects,queries,expected_plan_sha256=p['plan_sha256'])

    def test_unknown_labels_and_unrelated_view_or_item_metadata_are_preserved(self):
        for fault in ('precision','key','row_version','formatter','new_default','new_identity','created_shape'):
            s,d,c,p,after,effects,queries=self.saved()
            if fault=='precision':queries['results']['uncertaintyRows'][0]['field_8']='invented'
            elif fault=='key':queries['results']['differenceRows'][0]['SourceKey']='other'
            elif fault=='row_version':after['items'][0]['OData__UIVersionString']='99.0'
            elif fault=='formatter':after['views'][0]['CustomFormatter']='changed'
            elif fault=='new_default':after['views'][-1]['DefaultView']=True
            elif fault=='new_identity':effects['created_views']['quality']=s['views'][0]['Id']
            else:effects['created_views']=[]
            with self.subTest(fault=fault),self.assertRaises(ValueError):quality.reconcile(s,p,after,effects,queries,expected_plan_sha256=p['plan_sha256'])

    def test_zero_differences_and_excluded_unknown_denominators(self):
        s,d,c=self.inputs();s['items'][1]['field_17']='Excluded';d['registry_sha256']=c['registry_sha256']=sha(s)
        d['preserved_semantic_items']=[];c.update(cases=[],case_count=0,difference_count=0)
        data,_,plan=quality.prepare(s,d,c,'/Documents/fictional',uncertainty_view_id=s['views'][2]['Id'])
        self.assertEqual(data['coverage']['unknown_month_count'],1);self.assertEqual(data['coverage']['reader_uncertainty_count'],0)
        self.assertEqual(plan['details']['expected_ids']['differenceRows'],[])
        self.assertNotIn('<In>',plan['changes'][0]['desired']['ViewQuery'])

    def test_large_supplied_cohort_has_no_fixed_record_limit(self):
        s,d,c=self.inputs();d['preserved_semantic_items']=[];c['cases']=[]
        for i in range(1,202):
            row=copy.deepcopy(s['items'][0]);row.update(Id=i,field_1=f'pubmed:{i}');s['items'].append(row) if i>3 else None
            if i<=3:s['items'][i-1]=row
            d['preserved_semantic_items'].append(dict(id=i,field='Title',registry='Retained',canonical=f'candidate{i}'))
            c['cases'].append(dict(case_id=f'case:{i}',records=[dict(record_id=f'registry:{i}',source_key=f'pubmed:{i}'),dict(record_id=f'canonical-for:{i}',source_key=f'pubmed:{i}',values={'Title':f'candidate{i}'})]))
        s['counts']['items']=s['list']['ItemCount']=len(s['items']);d['registry_sha256']=c['registry_sha256']=sha(s);c.update(case_count=201,difference_count=201)
        data=quality.build(s,d,c);self.assertEqual(len(data['differences']),201)

    def test_exact_pair_lexical_identity_and_typed_values_fail_closed(self):
        for fault in ('bool_id','record_id','extra_record','source_key','extra_case','equal','field'):
            s,d,c=self.inputs()
            if fault=='bool_id':d['preserved_semantic_items'][0]['id']=True
            elif fault=='record_id':c['cases'][0]['records'][0]['record_id']='registry:01'
            elif fault=='extra_record':c['cases'][0]['records'].append(copy.deepcopy(c['cases'][0]['records'][0]))
            elif fault=='source_key':c['cases'][0]['records'][1]['source_key']='pubmed:2'
            elif fault=='extra_case':c['cases'].append(dict(case_id='other',records=c['cases'][0]['records']))
            elif fault=='equal':d['preserved_semantic_items'][0]['canonical']='Retained';c['cases'][0]['records'][1]['values']['Title']='Retained'
            else:d['preserved_semantic_items'][0]['field']='field_18'
            with self.subTest(fault=fault),self.assertRaises(ValueError):quality.build(s,d,c)

    def test_cli_envelope_roundtrip_and_exclusive_outputs(self):
        import contextlib,io,json,tempfile
        from pathlib import Path
        from unittest.mock import patch
        s,d,c,p,after,effects,queries=self.saved()
        with tempfile.TemporaryDirectory() as directory,patch.object(quality,'ROOT',Path(directory).resolve()),contextlib.redirect_stderr(io.StringIO()):
            private=Path(directory).resolve()/'private';private.mkdir()
            docs=dict(snapshot=s,disposition=d,cases=c,after=after,effects=effects,queries=queries)
            for name,doc in docs.items():(private/(name+'.json')).write_text(json.dumps(doc))
            output=private/'plan.json';args=['--snapshot',str(private/'snapshot.json'),'--disposition',str(private/'disposition.json'),'--cases',str(private/'cases.json'),'--folder','/Documents/fictional','--uncertainty-view-id',s['views'][2]['Id'],'--output',str(output)]
            self.assertEqual(quality.main(args),0);raw=output.read_bytes();envelope=json.loads(raw)
            self.assertEqual(envelope['result']['plan'],p)
            self.assertEqual(quality.main(args),2);self.assertEqual(output.read_bytes(),raw)
            args[args.index('--output')+1]=str(private/'report.json')
            args+=['--plan',str(output),'--after',str(private/'after.json'),'--effects',str(private/'effects.json'),'--query-results',str(private/'queries.json'),'--expected-plan-sha256',p['plan_sha256']]
            self.assertEqual(quality.main(args),0)
            self.assertFalse(json.loads((private/'report.json').read_bytes())['result']['native_acceptance'])
