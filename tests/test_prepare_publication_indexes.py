# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from scripts import prepare_publication_indexes as indexes
from tests.test_prepare_publication_registry_bootstrap import metadata_snapshot,changed_field,query_evidence

class IndexTests(unittest.TestCase):
    def test_only_existing_indexes_are_proposed_without_constraint_changes(self):
        s=metadata_snapshot();p=indexes.prepare(s,index_budget=20,period=['2026-09','2026-10'])
        self.assertEqual(len(p['changes']),5)
        self.assertTrue(all(c['desired']=={'Indexed':True} for c in p['changes']))
        self.assertEqual(p['details']['integrity']['blank_source_keys'],1)
        self.assertFalse(p['details']['uniqueness_proven']);self.assertFalse(p['details']['performance_proven'])
        after=copy.deepcopy(s)
        for c in p['changes']:
            i=next(i for i,f in enumerate(after['fields']) if f['Id']==c['id'])
            after['fields'][i]=changed_field(after['fields'][i],Indexed=True)
        results={q['name']:[{'Id':i,'SourceKey':next(r['field_1'] for r in s['items'] if r['Id']==i)} for i in q['expected_ids']] for q in p['details']['queries']}
        self.assertEqual(indexes.reconcile(s,p,after,query_evidence(s,p,results),expected_plan_sha256=p['plan_sha256'])['status'],'verified_supplied_readback')
        self.assertEqual(indexes.prepare(after,index_budget=20,period=['2026-09','2026-10'])['changes'],[])

    def test_collisions_are_diagnostics_and_no_positive_pmid_is_an_explicit_probe_gap(self):
        s=metadata_snapshot();s['items'][1]['field_1']='PUBMED:1';s['items'][0]['field_10']=None
        p=indexes.prepare(s,index_budget=20)
        self.assertTrue(p['details']['integrity']['casefold_collisions'])
        self.assertIn('positive_pmid_sample_unavailable',p['details']['unavailable_queries'])
        self.assertIn('configured_period_unavailable',p['details']['unavailable_queries'])
        self.assertEqual(s['items'][2]['field_1'],None)

    def test_budget_type_plan_data_and_query_tampering_fail_closed(self):
        s=metadata_snapshot()
        for budget in [True,0,4]:
            with self.subTest(budget=budget),self.assertRaises(ValueError):indexes.prepare(s,index_budget=budget)
        p=indexes.prepare(s,index_budget=20);after=copy.deepcopy(s);after['items'][0]['versions']=[]
        with self.assertRaises(ValueError):indexes.reconcile(s,p,after,{},expected_plan_sha256=p['plan_sha256'])
        p['inputs']['index_budget']=99
        with self.assertRaises(ValueError):indexes.reconcile(s,p,s,{},expected_plan_sha256=p['plan_sha256'])

    def test_existing_required_and_unique_constraints_are_never_relaxed(self):
        s=metadata_snapshot();field=next(f for f in s['fields'] if f['InternalName']=='field_1');field['Required']=True
        with self.assertRaises(ValueError):indexes.prepare(s,index_budget=20)
        field['Required']=False;field['EnforceUniqueValues']=True
        p=indexes.prepare(s,index_budget=20);self.assertTrue(all('EnforceUniqueValues' not in c['desired'] for c in p['changes']))

    def test_odata_literals_are_escaped_and_months_are_not_guessed(self):
        s=metadata_snapshot();s['items'][0]['field_1']="dora:O'Brien";s['items'][0]['field_2']="CAN:O'Brien"
        p=indexes.prepare(s,index_budget=20,period=['2026-09','2026-10'])
        self.assertIn("O''Brien",p['details']['queries'][0]['filter'])
        for bad in ('2026-9','0000-01','２０２６-09','2026-13'):
            s['items'][0]['field_6']=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):indexes.prepare(s,index_budget=20,period=['2026-09','2026-10'])

    def test_cli_roundtrip_preserves_prior_output_and_incomplete_arguments_fail(self):
        import contextlib,io,json,tempfile
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stderr(io.StringIO()):
            root=Path(directory).resolve();private=root/'private';private.mkdir();source=private/'snapshot.json';source.write_text(json.dumps(metadata_snapshot()));out=private/'plan.json'
            args=['--snapshot',str(source),'--index-budget','20','--output',str(out)]
            with patch.object(indexes,'ROOT',root):
                self.assertEqual(indexes.main(args),0);raw=out.read_bytes();self.assertEqual(indexes.main(args),2);self.assertEqual(out.read_bytes(),raw)
                args[-1]=str(private/'other.json');self.assertEqual(indexes.main(args+['--plan',str(out)]),2);self.assertFalse((private/'other.json').exists())
