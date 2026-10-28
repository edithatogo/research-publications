# SPDX-License-Identifier: Apache-2.0
import copy
import json
from pathlib import Path
import tempfile
import unittest
from scripts import prepare_publication_guarded_writer as writer
from scripts import prepare_publication_registry_bootstrap as core
from scripts import prepare_publication_writer_feed as feed
from tests.test_prepare_publication_writer_feed import make_feed
from tests.test_prepare_publication_registry_bootstrap import guid
CLOCK='2026-10-29T03:00:00Z'


def declarations(manifest,capture):
    scope=dict(target=manifest['context']['target'],manifest_sha256=manifest['manifest_sha256'],writer_capture_sha256=core.sha(capture),connection_references_sha256=core.sha(capture['flow']['properties']['connectionReferences']),schema_qualification_sha256=manifest['context']['input_pins']['schema'])
    bindings={
        'version_bound_feed_reads':dict(admission_receipt_reference='fixture:declared-only',admission_receipt_sha256='a'*64,parts={d['name']:dict(file_id=guid(700+i),etag='"fixture-file"',bytes=d['bytes'],sha256=d['sha256']) for i,d in enumerate(manifest['parts'])}),
        'conditional_etag':dict(read_response_profile='exact_row_with_opaque_etag_v1',if_match_header='IF-MATCH',conflict_status=412,allowed_internal_fields=['field_20']),
        'atomic_create_uniqueness':dict(reservation_scope='fixture:atomic-reservation',full_title_field_id=manifest['context']['schema']['capacities']['SourceFullTitle']['field_id']),
        'durable_intent_outcome_journal':dict(journal_scope='fixture:durable-journal',journal_revision_profile='conditional_intent_and_verified_outcome_v1')}
    profiles={name:dict(kind='publication_writer_qualification_profile_v1',name=name,version='fixture:v1',evidence_reference='fixture:claims-not-native-proof',operation_schema_sha256='b'*64,scope=copy.deepcopy(scope),guarantees=sorted(guarantees),bindings=bindings[name]) for name,guarantees in writer.GUARANTEES.items()}
    return profiles,{name:core.sha(value) for name,value in profiles.items()}


class GuardedWriterTests(unittest.TestCase):
    def setup_values(self,**kwargs):
        docs,raw,p,m,parts=make_feed(**kwargs);w=docs['writer'];profiles,pins=declarations(m,w)
        return docs,w,m,parts,profiles,dict(expected_writer_sha256=core.sha(w),expected_manifest_sha256=m['manifest_sha256'],profile_pins=pins)

    def test_declarative_plan_preserves_preimage_and_never_claims_working_wdl(self):
        docs,w,m,parts,profiles,args=self.setup_values();before=copy.deepcopy((w,m,parts,profiles));plan=writer.prepare(w,m,parts,profiles,**args)
        self.assertEqual((w,m,parts,profiles),before);self.assertEqual(plan['preimage'],w);self.assertEqual(plan['source_contract_blockers'],[])
        self.assertIsNone(plan['native_definition_candidate']);self.assertFalse(plan['native_adapter_implemented']);self.assertFalse(plan['writer_ready']);self.assertFalse(plan['qualification_claims_authenticated'])
        graph=plan['transition_graph'];self.assertEqual(graph['existing_update_fields'],['field_20']);self.assertEqual(graph['mutation_retries'],0)
        self.assertIn(dict(source='next_record',target='check_replay',when='more_records'),graph['edges']);self.assertIn(dict(source='next_record',target='complete_batch',when='all_records_verified'),graph['edges'])
        d=w['flow']['properties']['definition'];self.assertEqual(plan['migration_scope']['triggers_sha256'],core.sha(d['triggers']));self.assertIn('native_connector_action_graph_not_implemented',plan['native_blockers'])

    def test_every_missing_profile_is_an_explicit_blocker_and_sends_nothing(self):
        docs,w,m,parts,profiles,args=self.setup_values()
        for name in writer.GUARANTEES:
            selected=copy.deepcopy(profiles);selected.pop(name);a=copy.deepcopy(args);a['profile_pins'].pop(name);transport=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*3)
            result=writer.simulate(w,m,parts,selected,transport,**a)
            self.assertEqual(result['status'],'BLOCKED_QUALIFICATIONS');self.assertIn('missing_qualification:'+name,result['blockers']);self.assertEqual(transport.calls,[]);self.assertEqual(transport.journal,{})

    def test_rebound_profile_guarantee_header_shape_and_schema_scope_are_rejected(self):
        for fault in ('pin','scope','guarantee','header','fields','status','file','wildcard','full_title','journal'):
            docs,w,m,parts,profiles,args=self.setup_values();name='conditional_etag';p=profiles[name]
            if fault=='pin':p['version']='changed'
            elif fault=='scope':p['scope']['schema_qualification_sha256']='0'*64
            elif fault=='guarantee':p['guarantees'].pop()
            elif fault=='header':p['bindings']['if_match_header']='*'
            elif fault=='fields':p['bindings']['allowed_internal_fields'].append('field_18')
            elif fault=='status':p['bindings']['conflict_status']='412'
            elif fault=='file':name='version_bound_feed_reads';profiles[name]['bindings']['parts'][m['parts'][0]['name']]['bytes']+=1
            elif fault=='wildcard':name='version_bound_feed_reads';profiles[name]['bindings']['parts'][m['parts'][0]['name']]['etag']='*'
            elif fault=='full_title':name='atomic_create_uniqueness';profiles[name]['bindings']['full_title_field_id']=guid(999)
            else:name='durable_intent_outcome_journal';profiles[name]['bindings']['journal_revision_profile']='unversioned'
            if fault!='pin':args['profile_pins'][name]=core.sha(profiles[name])
            with self.subTest(fault=fault),self.assertRaises(ValueError):writer.prepare(w,m,parts,profiles,**args)

    def test_wrong_preimage_and_bad_feed_fail_before_any_effect(self):
        docs,w,m,parts,profiles,args=self.setup_values();w['flow']['properties']['displayName']='changed'
        with self.assertRaises(ValueError):writer.prepare(w,m,parts,profiles,**args)
        docs,w,m,parts,profiles,args=self.setup_values();parts.pop(m['parts'][-1]['name']);transport=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*3)
        with self.assertRaises(ValueError):writer.simulate(w,m,parts,profiles,transport,**args)
        self.assertEqual(transport.calls,[]);self.assertEqual(transport.journal,{})

    def test_complete_simulated_journey_protects_human_values_full_title_and_clocks(self):
        docs,w,m,parts,profiles,args=self.setup_values();transport=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*3);before=copy.deepcopy(docs['registry']['items']);result=writer.simulate(w,m,parts,profiles,transport,**args)
        self.assertEqual(result['status'],'SIMULATED_COMPLETE');self.assertTrue(result['simulation_only']);self.assertFalse(result['native_runtime_verified']);self.assertEqual(len(transport.calls),3)
        for old in before:
            row=next(r for r in transport.rows if r['Id']==old['Id'])
            if old['field_1'] is None:self.assertEqual(row,old)
            else:
                for field,value in old.items():
                    if field not in ('field_20','__metadata','OData__UIVersionString','versions'):self.assertEqual(row[field],value)
                self.assertEqual(row['field_20'],CLOCK);self.assertEqual(row['versions'][:len(old['versions'])],old['versions'])
        created=next(r for r in transport.rows if r.get('field_1')=='pubmed:2');self.assertEqual(created['field_17'],'Included');self.assertEqual(created['SourceFullTitle'],'New source');self.assertEqual(created['field_19'],CLOCK);self.assertEqual(created['field_20'],CLOCK)
        self.assertEqual(transport.consumer_commits,[m['manifest_sha256']]);self.assertTrue(all(e['status']=='done' for e in transport.journal.values()))

    def test_verified_replay_never_resends_or_advances_processing_time(self):
        docs,w,m,parts,profiles,args=self.setup_values();t=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*3);writer.simulate(w,m,parts,profiles,t,**args);saved=t.snapshot();result=writer.simulate(w,m,parts,profiles,t,**args)
        self.assertEqual(result['status'],'SIMULATED_COMPLETE');self.assertEqual(t.snapshot(),saved)

    def test_uncertain_create_and_update_outcomes_never_resend(self):
        for key in ('dora:1/2','pubmed:2'):
            docs,w,m,parts,profiles,args=self.setup_values();t=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*6,faults={key:'after_send'});first=writer.simulate(w,m,parts,profiles,t,**args);calls=copy.deepcopy(t.calls);rows=copy.deepcopy(t.rows)
            self.assertEqual(first['status'],'SIMULATED_STOPPED');self.assertEqual(t.consumer_commits,[]);self.assertTrue(any(e['status']=='uncertain' for e in t.journal.values()))
            t.faults={};second=writer.simulate(w,m,parts,profiles,t,**args);self.assertEqual(second['status'],'SIMULATED_STOPPED');self.assertEqual(t.calls,calls);self.assertEqual(t.rows,rows)

    def test_failed_intent_read_or_version_checks_stop_before_effect(self):
        for phase in ('intent','read','feed_version_changed'):
            docs,w,m,parts,profiles,args=self.setup_values();t=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*3,faults={'dora:1/2':phase});before=copy.deepcopy(t.rows);result=writer.simulate(w,m,parts,profiles,t,**args)
            self.assertEqual(result['status'],'SIMULATED_STOPPED');self.assertEqual(t.calls,[]);self.assertEqual(t.rows,before);self.assertEqual(t.consumer_commits,[])

    def test_post_intent_failure_and_missing_readback_do_not_complete_batch(self):
        for phase in ('after_intent','before_send','readback','outcome'):
            docs,w,m,parts,profiles,args=self.setup_values();t=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*3,faults={'dora:1/2':phase});result=writer.simulate(w,m,parts,profiles,t,**args)
            self.assertEqual(result['status'],'SIMULATED_STOPPED');self.assertEqual(t.consumer_commits,[]);self.assertEqual(len(t.journal),1);self.assertEqual(next(iter(t.journal.values()))['status'],'uncertain');self.assertLessEqual(len(t.calls),1)

    def test_fresh_human_edit_or_conditional_conflict_is_preserved(self):
        for fresh in (True,False):
            docs,w,m,parts,profiles,args=self.setup_values();t=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*3,faults={} if fresh else {'dora:1/2':'concurrent_edit'})
            row=next(r for r in t.rows if r['field_1']=='dora:1/2')
            if fresh:row['field_18']='Concurrent human edit'
            result=writer.simulate(w,m,parts,profiles,t,**args);self.assertEqual(result['status'],'SIMULATED_STOPPED');self.assertEqual(row['field_18'],'Concurrent human edit');self.assertEqual(row['field_20'],None);self.assertEqual(t.consumer_commits,[])

    def test_atomic_create_race_cannot_duplicate_or_overwrite_other_creator(self):
        docs,w,m,parts,profiles,args=self.setup_values();t=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*3,faults={'pubmed:2':'create_race'});result=writer.simulate(w,m,parts,profiles,t,**args)
        self.assertEqual(result['status'],'SIMULATED_STOPPED');matches=t.lookup('pubmed:2');self.assertEqual(len(matches),1);self.assertEqual(matches[0]['Title'],'Concurrent creator; preserve');self.assertEqual(t.consumer_commits,[])

    def test_full_title_drop_fails_readback_and_stops_consumer_commit(self):
        docs,w,m,parts,profiles,args=self.setup_values();t=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*3,faults={'pubmed:2':'drop_full_title'});result=writer.simulate(w,m,parts,profiles,t,**args)
        self.assertEqual(result['status'],'SIMULATED_STOPPED');self.assertEqual(t.consumer_commits,[])

    def test_changed_feed_partitioning_cannot_rebind_a_claimed_generation(self):
        docs,w,m,parts,profiles,args=self.setup_values();t=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*6);writer.simulate(w,m,parts,profiles,t,**args);calls=copy.deepcopy(t.calls)
        _,_,_,other,other_parts=make_feed(max_part_records=2);other_profiles,other_pins=declarations(other,w)
        result=writer.simulate(w,other,other_parts,other_profiles,t,expected_writer_sha256=core.sha(w),expected_manifest_sha256=other['manifest_sha256'],profile_pins=other_pins)
        self.assertEqual(result['status'],'SIMULATED_STOPPED');self.assertIn('Generation already bound',result['reason']);self.assertEqual(t.calls,calls)

    def test_consumer_commit_failure_can_reconcile_without_repeating_effects(self):
        docs,w,m,parts,profiles,args=self.setup_values();t=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*3,faults={'__batch__':'commit'});result=writer.simulate(w,m,parts,profiles,t,**args);calls=copy.deepcopy(t.calls)
        self.assertEqual(result['status'],'SIMULATED_STOPPED');self.assertEqual(t.consumer_commits,[]);t.faults={};result=writer.simulate(w,m,parts,profiles,t,**args);self.assertEqual(result['status'],'SIMULATED_COMPLETE');self.assertEqual(t.calls,calls);self.assertEqual(len(t.consumer_commits),1)

    def test_no_arbitrary_transport_callbacks_or_clock_regression(self):
        docs,w,m,parts,profiles,args=self.setup_values()
        with self.assertRaises(ValueError):writer.simulate(w,m,parts,profiles,object(),**args)
        t=writer.MemoryTransport(docs['registry']['items'],['2026-10-28T00:00:00Z']);result=writer.simulate(w,m,parts,profiles,t,**args);self.assertEqual(result['status'],'SIMULATED_STOPPED');self.assertEqual(t.calls,[])

    def test_cli_is_exclusive_and_direct_script_loads_without_site_packages(self):
        import subprocess,sys,contextlib,io
        docs,w,m,parts,profiles,args=self.setup_values();root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='guarded-writer-test-',dir=root/'private') as directory,contextlib.redirect_stderr(io.StringIO()):
            private=Path(directory)
            for name,value in dict(writer=w,feed=dict(kind='publication_writer_feed_local_v1',manifest=m,parts_utf8={n:v.decode('utf-8') for n,v in parts.items()}),profiles=profiles,profile_pins=args['profile_pins']).items():(private/(name+'.json')).write_text(json.dumps(value))
            cli=[v for name in ('writer','feed','profiles','profile_pins') for v in ('--'+name.replace('_','-'),str(private/(name+'.json')))]+['--writer-sha256',args['expected_writer_sha256'],'--manifest-sha256',args['expected_manifest_sha256'],'--output',str(private/'plan.json')]
            result=subprocess.run([sys.executable,'-S',str(root/'scripts/prepare_publication_guarded_writer.py'),*cli],cwd=root,capture_output=True,text=True,timeout=20);self.assertEqual(result.returncode,0,result.stderr);raw=(private/'plan.json').read_bytes();plan=json.loads(raw)['result'];self.assertIsNone(plan['native_definition_candidate'])
            self.assertEqual(writer.main(cli),2);self.assertEqual((private/'plan.json').read_bytes(),raw)
            cli[-1]=str(private/'other.json');(private/'profiles.json').write_text('{"duplicate":true,"duplicate":false}')
            self.assertEqual(writer.main(cli),2);self.assertFalse((private/'other.json').exists())

    def test_done_status_without_exact_outcome_and_proposal_binding_cannot_skip_writes(self):
        docs,w,m,parts,profiles,args=self.setup_values();rows=feed.validate(m,parts,expected_manifest_sha256=m['manifest_sha256']);op=rows[0]['operation_id']
        t=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*3);t.journal[op]=dict(feed_sha256=m['manifest_sha256'],status='done')
        result=writer.simulate(w,m,parts,profiles,t,**args);self.assertEqual(result['status'],'SIMULATED_STOPPED');self.assertEqual(t.calls,[]);self.assertEqual(t.consumer_commits,[])
        t=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*3);writer.simulate(w,m,parts,profiles,t,**args);t.consumer_commits=[];t.journal[op]['postimage']['field_18']='forged';t.journal[op]['postimage_sha256']=core.sha(t.journal[op]['postimage']);calls=copy.deepcopy(t.calls)
        result=writer.simulate(w,m,parts,profiles,t,**args);self.assertEqual(result['status'],'SIMULATED_STOPPED');self.assertEqual(t.calls,calls);self.assertEqual(t.consumer_commits,[])
