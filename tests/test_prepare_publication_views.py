# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from scripts import prepare_publication_views as views
from tests.test_prepare_publication_registry_bootstrap import metadata_snapshot,query_evidence

class ViewTests(unittest.TestCase):
    def args(self,s):return {r:v['Id'] for r,v in zip(['publications','month','uncertainty','placeholders'],s['views'][:4])}
    def test_brisbane_boundaries_unknown_months_placeholders_and_exclusion(self):
        self.assertEqual(views.previous_month('2026-12-31T14:00:00Z'),('2026-12','2027-01'))
        self.assertEqual(views.previous_month('2024-03-01T00:00:00+10:00'),('2024-02','2024-03'))
        with self.assertRaises(ValueError):views.previous_month('2026-10-29T00:00:00')
        s=metadata_snapshot();old=copy.deepcopy(s)
        self.assertEqual(views.expected_ids(s['items'],'2026-09','2026-10'),dict(publications=[1,2],month=[1],uncertainty=[2],placeholders=[3]))
        s['items'][1]['field_17']='Excluded'
        self.assertEqual(views.expected_ids(s['items'],'2026-09','2026-10')['uncertainty'],[])
        self.assertEqual(old['items'][1]['field_6'],None)

    def test_bound_ids_preserve_columns_and_exact_supplied_readback(self):
        s=metadata_snapshot();p=views.prepare(s,'2026-10-29T00:00:00Z',self.args(s));after=copy.deepcopy(s)
        for c in p['changes']:
            v=next(v for v in after['views'] if v['Id']==c['id']);v.update(copy.deepcopy(c['desired']))
        results={role:[{'Id':i,'SourceKey':next(r['field_1'] for r in s['items'] if r['Id']==i)} for i in ids] for role,ids in p['details']['expected_ids'].items()}
        self.assertEqual(views.reconcile(s,p,after,query_evidence(s,p,results),expected_plan_sha256=p['plan_sha256'])['status'],'verified_supplied_readback')
        self.assertEqual(views.prepare(after,'2026-10-29T00:00:00Z',self.args(s))['changes'],[])
        self.assertEqual(after['views'][0]['resolvedFields'],s['views'][0]['resolvedFields'])

    def test_default_personal_alias_bindings_and_changed_fields_cannot_be_adopted(self):
        s=metadata_snapshot();bindings=self.args(s);bindings['month']=s['views'][4]['Id']
        with self.assertRaises(ValueError):views.prepare(s,'2026-10-29T00:00:00Z',bindings)
        bindings=self.args(s);bindings['month']=bindings['publications']
        with self.assertRaises(ValueError):views.prepare(s,'2026-10-29T00:00:00Z',bindings)
        p=views.prepare(s,'2026-10-29T00:00:00Z',self.args(s));after=copy.deepcopy(s);after['fields'][0]['__metadata']['etag']='new'
        with self.assertRaises(ValueError):views.reconcile(s,p,after,{},expected_plan_sha256=p['plan_sha256'])

    def test_created_views_require_new_distinct_receipt_ids_and_preserve_existing(self):
        from tests.test_prepare_publication_registry_bootstrap import view,guid
        s=metadata_snapshot();bindings={role:None for role in views.ROLES};p=views.prepare(s,'2026-10-29T00:00:00Z',bindings);after=copy.deepcopy(s);created={}
        for i,c in enumerate(p['changes']):
            v=view(c['role'],300+i);v.update(copy.deepcopy(c['desired']));v['resolvedFields']['Items']['results']=copy.deepcopy(c['fields']);after['views'].append(v);created[c['role']]=v['Id']
        after['counts']['views']=len(after['views']);results={role:[dict(Id=i,SourceKey=next(r['field_1'] for r in s['items'] if r['Id']==i)) for i in ids] for role,ids in p['details']['expected_ids'].items()};e=query_evidence(s,p,results)
        self.assertEqual(views.reconcile(s,p,after,e,expected_plan_sha256=p['plan_sha256'],created=created)['status'],'verified_supplied_readback')
        for receipt in ({},[],dict.fromkeys(views.ROLES,s['views'][0]['Id'])):
            with self.subTest(receipt=receipt),self.assertRaises(ValueError):views.reconcile(s,p,after,e,expected_plan_sha256=p['plan_sha256'],created=receipt)
        after['views'][0]['__metadata']['etag']='other'
        with self.assertRaises(ValueError):views.reconcile(s,p,after,e,expected_plan_sha256=p['plan_sha256'],created=created)

    def test_existing_formatter_columns_and_query_results_cannot_change(self):
        s=metadata_snapshot();p=views.prepare(s,'2026-10-29T00:00:00Z',self.args(s));after=copy.deepcopy(s)
        for c in p['changes']:next(v for v in after['views'] if v['Id']==c['id']).update(copy.deepcopy(c['desired']))
        results={role:[dict(Id=i,SourceKey=next(r['field_1'] for r in s['items'] if r['Id']==i)) for i in ids] for role,ids in p['details']['expected_ids'].items()};e=query_evidence(s,p,results)
        for fault in ('formatter','columns','extraquery','missingquery','etag_shape'):
            a=copy.deepcopy(after);q=copy.deepcopy(e)
            if fault=='formatter':a['views'][0]['CustomFormatter']='new'
            elif fault=='columns':a['views'][0]['resolvedFields']['Items']['results'].append('SourceFullTitle')
            elif fault=='extraquery':q['results']['unowned']=[];q['counts']['unowned']=0
            elif fault=='missingquery':q['results'].pop('month')
            else:a['views'][0]['__metadata']['added']='unqualified'
            with self.subTest(fault=fault),self.assertRaises(ValueError):views.reconcile(s,p,a,q,expected_plan_sha256=p['plan_sha256'])

    def test_cli_local_plan_is_exclusive_and_partial_reconciliation_rejected(self):
        import contextlib,io,json,tempfile
        from pathlib import Path
        from unittest.mock import patch
        s=metadata_snapshot()
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stderr(io.StringIO()):
            root=Path(directory).resolve();private=root/'private';private.mkdir();(private/'snapshot.json').write_text(json.dumps(s));(private/'bindings.json').write_text(json.dumps(self.args(s)));out=private/'plan.json'
            args=['--snapshot',str(private/'snapshot.json'),'--bindings',str(private/'bindings.json'),'--as-of','2026-10-29T00:00:00Z','--output',str(out)]
            with patch.object(views,'ROOT',root):
                self.assertEqual(views.main(args),0);raw=out.read_bytes();self.assertEqual(views.main(args),2);self.assertEqual(out.read_bytes(),raw)
                args[-1]=str(private/'other.json');self.assertEqual(views.main(args+['--created',str(private/'bindings.json')]),2);self.assertFalse((private/'other.json').exists())

    def test_replay_after_new_views_requires_explicit_identity_handover(self):
        from tests.test_prepare_publication_registry_bootstrap import view
        s=metadata_snapshot();bindings=dict.fromkeys(views.ROLES);p=views.prepare(s,'2026-10-29T00:00:00Z',bindings);after=copy.deepcopy(s);created={}
        for i,c in enumerate(p['changes']):
            v=view(c['role'],400+i);v.update(copy.deepcopy(c['desired']));v['resolvedFields']['Items']['results']=copy.deepcopy(c['fields']);after['views'].append(v);created[c['role']]=v['Id']
        after['counts']['views']=len(after['views'])
        with self.assertRaises(ValueError):views.prepare(after,'2026-10-29T00:00:00Z',bindings)
        self.assertEqual(views.prepare(after,'2026-10-29T00:00:00Z',created)['changes'],[])

    def test_other_view_title_collision_cannot_be_created_or_renamed_over(self):
        for new_binding in (True,False):
            for case_variant in (False,True):
                s=metadata_snapshot();bindings=self.args(s);title=views.definitions('2026-09','2026-10')['month']['Title']
                s['views'][4]['Title']=title.upper() if case_variant else title
                if new_binding:bindings['month']=None
                original=copy.deepcopy(s)
                with self.subTest(new_binding=new_binding,case_variant=case_variant),self.assertRaises(ValueError):views.prepare(s,'2026-10-29T00:00:00Z',bindings)
                self.assertEqual(s,original)
