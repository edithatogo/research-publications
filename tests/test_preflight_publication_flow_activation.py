# SPDX-License-Identifier: Apache-2.0
"""Synthetic offline writer diagnostics; no activation or capture."""
import copy
import json
from pathlib import Path
import unittest
from scripts import preflight_publication_flow_activation as preflight
from scripts import prepare_publication_registry_bootstrap as core
from tests.test_prepare_publication_registry_bootstrap import metadata_snapshot,guid


def target():
    s=metadata_snapshot()
    return dict(site_url=s['site_url'],list_id=s['list_id'],model_id=guid(501),workspace_id=guid(502),flow_id=guid(503),environment=guid(504))


def writer_fixture():
    t=target();document=json.loads((Path(__file__).parents[1]/'config/flows/publication-registry-upsert.definition.json').read_bytes())
    def visit(node):
        if not isinstance(node,dict):return
        inputs=node.get('inputs',{})
        if isinstance(inputs,dict):
            params=inputs.get('parameters',{});host=inputs.get('host',{})
            if host.get('apiId','').endswith('shared_sharepointonline'):
                if 'dataset' in params:params['dataset']=t['site_url']
                if 'table' in params:params['table']=t['list_id']
            for key,value in (('datasetid',t['model_id']),('groupid',t['workspace_id'])):
                if key in params:params[key]=value
        for value in node.values():
            if isinstance(value,dict):visit(value)
    definition=document['properties']['definition'];visit(definition)
    document.update(id=f"/providers/Microsoft.ProcessSimple/environments/{t['environment']}/flows/{t['flow_id']}",name=t['flow_id'])
    document['properties'].update(state='Stopped',connectionReferences={'fixture':{'connectionName':'fictional'}})
    return dict(complete=True,capture_reference='fixture:writer',observed_at_utc='2026-10-29T00:00:00Z',saved_revision='version:1.0',flow=document,
        run_history=dict(complete=True,capture_reference='fixture:run-history',observed_at_utc='2026-10-29T00:00:00Z',item_count=0,value=[],flow_id=t['flow_id'],environment=t['environment']))


class PreflightTests(unittest.TestCase):
    def assess(self,w=None,s=None):
        w=writer_fixture() if w is None else w;s=metadata_snapshot() if s is None else s
        return preflight.assess(w,s,target(),expected_writer_sha256=core.sha(w))

    def test_canonical_pilot_gaps_are_explicit_despite_structural_success(self):
        result=self.assess();self.assertEqual(result['structural_errors'],[])
        required={'pilot_topn_100','missing_rows_coalesced_to_empty','inferred_dora_source_key','missing_complete_batch_guard','missing_full_title_protection','missing_conditional_etag_protection','legacy_needs_review_policy'}
        self.assertTrue(required<=set(result['blockers']));self.assertFalse(result['writer_ready']);self.assertFalse(result['write_authorized']);self.assertFalse(result['native_acceptance'])

    def test_changed_preimage_target_or_nonterminal_writer_is_rejected(self):
        for fault in ('pin','target','state','run','revision','partial'):
            w=writer_fixture();s=metadata_snapshot();pin=core.sha(w)
            if fault=='pin':w['capture_reference']='changed'
            elif fault=='target':w['flow']['properties']['definition']['actions']['Run_publication_rows_query']['inputs']['parameters']['datasetid']=guid(999)
            elif fault=='state':w['flow']['properties']['state']='Started'
            elif fault=='run':w['run_history'].update(item_count=1,value=[dict(name='run',properties={'status':'Running'})])
            elif fault=='revision':w['saved_revision']='etag:*'
            else:w['complete']=False
            if fault!='pin':pin=core.sha(w)
            with self.subTest(fault=fault),self.assertRaises(ValueError):preflight.assess(w,s,target(),expected_writer_sha256=pin)

    def test_guard_names_and_policy_literal_cannot_imply_qualified_semantics(self):
        w=writer_fixture();a=w['flow']['properties']['definition']['actions'];a['Condition_Publication_Row_Count']={'type':'Compose','inputs':'unqualified'};a['Condition_Invalid_SourceKeys']={'type':'Compose','inputs':'unqualified'};a['Apply_to_each_Publication']['actions']['Compose_SourceKey_Required']={'type':'Compose','inputs':'unqualified'}
        a['Apply_to_each_Publication']['actions']['Condition_Is_New_Publication']['actions']['SharePoint_Create_item']['inputs']['parameters']['item/field_17']='Included'
        result=self.assess(w);self.assertFalse(result['writer_ready']);self.assertIn('complete_batch_semantics_unqualified',result['blockers']);self.assertIn('writer_profile_not_qualified',result['blockers'])

    def test_assessment_preserves_every_supplied_property(self):
        w=writer_fixture();s=metadata_snapshot();original=copy.deepcopy((w,s));self.assess(w,s);self.assertEqual((w,s),original)

    def test_cli_exclusive_strict_private_readback_and_hashes(self):
        import contextlib,io,tempfile
        from unittest.mock import patch
        w=writer_fixture();s=metadata_snapshot()
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stderr(io.StringIO()):
            root=Path(directory).resolve();private=root/'private';private.mkdir()
            for name,value in dict(writer=w,registry=s,target=target()).items():(private/(name+'.json')).write_text(json.dumps(value))
            args=[v for name in ('writer','registry','target') for v in ('--'+name,str(private/(name+'.json')))]+['--expected-writer-sha256',core.sha(w),'--output',str(private/'report.json')]
            with patch.object(preflight,'ROOT',root):
                self.assertEqual(preflight.main(args),0);out=private/'report.json';raw=out.read_bytes();report=json.loads(raw)
                self.assertFalse(report['result']['writer_ready']);self.assertEqual(report['source_files_sha256']['writer'],core.bytes_sha((private/'writer.json').read_bytes()))
                self.assertEqual(preflight.main(args),2);self.assertEqual(out.read_bytes(),raw)
                args[-1]=str(private/'other.json');(private/'writer.json').write_text('{"complete":true,"complete":false}')
                self.assertEqual(preflight.main(args),2);self.assertFalse((private/'other.json').exists())

    def test_malformed_headers_missing_bindings_and_history_capture_fail_closed(self):
        for fault in ('headers','table','history','status'):
            w=writer_fixture();a=w['flow']['properties']['definition']['actions'];p=a['Apply_to_each_Publication']['actions']['SharePoint_Get_items']['inputs']['parameters']
            if fault=='headers':p['parameters/headers']=[]
            elif fault=='table':p.pop('table')
            elif fault=='history':w['run_history'].pop('capture_reference')
            else:w['run_history'].update(item_count=1,value=[dict(name='run',properties={'status':[]})])
            with self.subTest(fault=fault),self.assertRaises(ValueError):self.assess(w)
