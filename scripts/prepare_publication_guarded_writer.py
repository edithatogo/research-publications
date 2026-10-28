# SPDX-License-Identifier: Apache-2.0
"""Generate a guarded source plan and run its bounded in-memory reference model.

This module has no native adapter and never emits deployable WDL or invokes a
caller-supplied transport. Qualification declarations are not authenticated here.
"""
import argparse
import copy
from pathlib import Path
import sys
if not __package__:sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import prepare_publication_registry_bootstrap as core
from scripts import prepare_publication_admission_packet as admission
from scripts import prepare_publication_writer_feed as feed
ROOT=Path(__file__).resolve().parents[1]
OWNED_ROOTS=('Run_a_query_against_a_dataset','Run_publication_rows_query','Apply_to_each_Publication')
GUARANTEES={
 'version_bound_feed_reads':{'accepted_producer_receipt','exact_file_id_etag_length','same_version_content_read','complete_terminal_inventory'},
 'conditional_etag':{'fresh_exact_item_preimage','opaque_nonwildcard_if_match','conflict_412_no_retry','field_20_only','preserved_human_values'},
 'atomic_create_uniqueness':{'atomic_source_key_reservation','single_create_full_title','included_policy','no_uncertain_resend'},
 'durable_intent_outcome_journal':{'conditional_intent_before_effect','outcome_after_readback','uncertain_no_resend','completion_after_all_operations','stable_generation_and_operation_binding'},
}
STEPS=(('validate_complete_feed','claim_generation'),('claim_generation','check_replay'),('check_replay','fresh_preimage'),('fresh_preimage','processing_clock'),('processing_clock','durable_intent'),('durable_intent','single_effect'),('single_effect','exact_readback'),('exact_readback','durable_outcome'),('durable_outcome','next_record'))


def qualify(profiles,pins,manifest,writer):
    if not isinstance(profiles,dict) or set(profiles)-set(GUARANTEES):raise ValueError('Unknown native qualification profile')
    admission.exact_keys(pins,profiles,'independent profile pins')
    refs=writer['flow']['properties']['connectionReferences'];target=manifest['context']['target']
    expected_scope=dict(target=target,manifest_sha256=manifest['manifest_sha256'],writer_capture_sha256=core.sha(writer),connection_references_sha256=core.sha(refs),schema_qualification_sha256=manifest['context']['input_pins']['schema'])
    for name,profile in profiles.items():
        admission.exact_keys(profile,('kind','name','version','evidence_reference','operation_schema_sha256','scope','guarantees','bindings'),'qualification profile')
        if core.sha(profile)!=admission.fingerprint(pins[name],'profile') or profile['kind']!='publication_writer_qualification_profile_v1' or profile['name']!=name:raise ValueError('Changed qualification profile')
        core.identifier(profile['version'],'profile version');core.identifier(profile['evidence_reference'],'qualification evidence reference');admission.fingerprint(profile['operation_schema_sha256'],'qualified operation schema')
        if not core.same(profile['scope'],expected_scope) or not isinstance(profile['guarantees'],list) or any(not isinstance(v,str) for v in profile['guarantees']) or sorted(profile['guarantees'])!=sorted(GUARANTEES[name]):raise ValueError('Qualification scope/guarantees differ')
        binding=profile['bindings']
        if name=='version_bound_feed_reads':
            admission.exact_keys(binding,('admission_receipt_reference','admission_receipt_sha256','parts'),'feed-read binding')
            core.identifier(binding['admission_receipt_reference'],'producer admission reference');admission.fingerprint(binding['admission_receipt_sha256'],'producer admission receipt')
            admission.exact_keys(binding['parts'],[p['name'] for p in manifest['parts']],'version-bound feed parts');ids=set()
            for descriptor in manifest['parts']:
                part=binding['parts'][descriptor['name']];admission.exact_keys(part,('file_id','etag','bytes','sha256'),'file-version binding');core.guid(part['file_id']);core.identifier(part['etag'],'saved file ETag')
                if part['file_id'] in ids or part['etag']=='*' or type(part['bytes']) is not int or part['bytes']!=descriptor['bytes'] or part['sha256']!=descriptor['sha256']:raise ValueError('File identity/version/bytes differ')
                ids.add(part['file_id'])
        elif name=='conditional_etag':
            admission.exact_keys(binding,('read_response_profile','if_match_header','conflict_status','allowed_internal_fields'),'conditional update binding')
            if binding!=dict(read_response_profile='exact_row_with_opaque_etag_v1',if_match_header='IF-MATCH',conflict_status=412,allowed_internal_fields=['field_20']) or type(binding['conflict_status']) is not int:raise ValueError('Unqualified conditional-update response/header shape')
        elif name=='atomic_create_uniqueness':
            admission.exact_keys(binding,('reservation_scope','full_title_field_id'),'atomic create binding')
            core.identifier(binding['reservation_scope'],'atomic reservation scope');core.guid(binding['full_title_field_id'])
            if binding['full_title_field_id']!=manifest['context']['schema']['capacities']['SourceFullTitle']['field_id']:raise ValueError('Full-title destination differs')
        else:
            admission.exact_keys(binding,('journal_scope','journal_revision_profile'),'durable journal binding')
            core.identifier(binding['journal_scope'],'journal scope')
            if binding['journal_revision_profile']!='conditional_intent_and_verified_outcome_v1':raise ValueError('Unqualified journal revision profile')
    return ['missing_qualification:'+name for name in sorted(set(GUARANTEES)-set(profiles))]


def prepare(writer,manifest,parts,profiles,*,expected_writer_sha256,expected_manifest_sha256,profile_pins):
    rows=feed.validate(manifest,parts,expected_manifest_sha256=expected_manifest_sha256);core.canonical(writer);core.complete(writer)
    if core.sha(writer)!=admission.fingerprint(expected_writer_sha256,'independent writer') or expected_writer_sha256!=manifest['writer_capture_sha256']:raise ValueError('Rebound writer preimage')
    flow=writer.get('flow');props=flow.get('properties') if isinstance(flow,dict) else None
    if not isinstance(props,dict) or props.get('state')!='Stopped' or not isinstance(props.get('connectionReferences'),dict) or not props['connectionReferences']:raise ValueError('Supplied stopped writer and retained references required')
    definition=props.get('definition');actions=definition.get('actions') if isinstance(definition,dict) else None
    if not isinstance(actions,dict) or not all(name in actions for name in OWNED_ROOTS):raise ValueError('Exact supported pilot source roots required; no implicit migration')
    blockers=qualify(profiles,profile_pins,manifest,writer)
    unrelated={name:copy.deepcopy(value) for name,value in actions.items() if name not in OWNED_ROOTS}
    # A declarative transition graph is intentionally separate from WDL. Actual
    # standard-connector action schemas and expression behavior are not present.
    graph=dict(kind='publication_guarded_writer_transition_graph_v1',entry='validate_complete_feed',edges=[dict(source=a,target=b,when='success') for a,b in STEPS]+[
        dict(source='next_record',target='check_replay',when='more_records'),dict(source='next_record',target='complete_batch',when='all_records_verified'),
        dict(source='check_replay',target='next_record',when='verified_done'),dict(source='fresh_preimage',target='durable_outcome',when='verified_noop')],failure_edge='stop_without_consumer_commit',
        complete_feed_before_effects=True,terminal_empty_part_required=True,explicit_source_and_canonical_bindings=True,
        new_record_policy='Included',full_title='single_create_in_existing_qualified_note',clock='one_actual_processing_utc_instant_per_operation',
        existing_update_fields=['field_20'],fresh_full_preimage_required=True,if_match='fresh_opaque_nonwildcard_etag',mutation_retries=0,
        replay='verified_done_skips; intent_or_uncertain_stops',intent_before_effect=True,outcome_after_readback=True,consumer_completion='all_operations_verified_only')
    plan={**core.FLAGS,'kind':'publication_guarded_writer_plan_v1','status':'BLOCKED_QUALIFICATIONS' if blockers else 'DECLARED_PROFILES_SOURCE_PLAN_ONLY',
        'writer_ready':False,'publishing_authorized':False,'native_definition_candidate':None,'native_adapter_implemented':False,
        'qualification_claims_authenticated':False,'source_contract_blockers':blockers,
        'native_blockers':['native_connector_action_graph_not_implemented','declared_profiles_require_native_owner_verification',
            'accepted_feed_marker_and_version_bound_content_action_target_missing',
            'fresh_row_get_conditional_merge_readback_action_schema_missing',
            'atomic_source_key_reservation_and_single_note_create_action_target_missing',
            'conditional_durable_journal_intent_outcome_action_target_missing',
            'actual_processing_clock_and_fail_fast_control_flow_not_runtime_qualified','parent_shared_wiring_pending'],
        'manifest_sha256':expected_manifest_sha256,'writer_capture_sha256':expected_writer_sha256,'profile_sha256':copy.deepcopy(profile_pins),
        'preimage':copy.deepcopy(writer),'transition_graph':graph,
        'migration_scope':dict(owned_root_actions=list(OWNED_ROOTS),owned_preimage_sha256=core.sha({n:actions[n] for n in OWNED_ROOTS}),unrelated_actions_sha256=core.sha(unrelated),
            triggers_sha256=core.sha(definition.get('triggers')),connection_references_sha256=core.sha(props['connectionReferences']),
            recovery='Exact supplied preimage retained; no native install/restore action or trigger/connection rewrite'),
        'records':len(rows)}
    plan['plan_sha256']=core.sha(plan);return plan


class SimulationStop(ValueError):pass


def check_outcome(p,result,clock):
    if not isinstance(result,dict):raise SimulationStop('missing exact readback')
    if type(result.get('Id')) is not int or result['Id']<1:raise SimulationStop('invalid readback item identity')
    core._metadata(result);core.version_key(result.get('OData__UIVersionString'))
    if p['kind']=='noop':
        if not core.same(result,p['retained_current']):raise SimulationStop('noop preimage differs')
    elif p['kind']=='observe':
        current=p['retained_current'];expected=copy.deepcopy(current);expected['field_20']=clock
        for name in ('__metadata','OData__UIVersionString','versions'):expected[name]=copy.deepcopy(result[name])
        if not core.same(expected,result):raise SimulationStop('protected value changed')
        if result['versions'][:len(current.get('versions',[]))]!=current.get('versions',[]):raise SimulationStop('history lost')
    else:
        for logical,proposed in p['proposed_values'].items():
            wanted=clock if logical in ('FirstObservedUTC','LastObservedUTC') else proposed
            if not core.same(result.get(admission.MAPPING[logical]),wanted):raise SimulationStop('create readback differs')
    if p['kind']!='noop':core.instant(clock,'verified processing clock')


class MemoryTransport:
    """In-memory fixture storage only, with explicit bounded failure injection."""
    def __init__(self,rows,clocks,*,faults=None):
        if not isinstance(rows,list) or not isinstance(clocks,list):raise ValueError('Explicit fake rows/clocks required')
        core.canonical(rows);core.canonical(clocks)
        phases={'before_send','after_send','create_race','drop_full_title','concurrent_edit','feed_version_changed','read','intent','after_intent','readback','outcome','commit'}
        if faults is not None and (not isinstance(faults,dict) or any(not isinstance(k,str) or not isinstance(v,str) or v not in phases for k,v in faults.items())):raise ValueError('Explicit supported fake failure phases required')
        if any(not isinstance(r,dict) for r in rows):raise ValueError('Structured fake rows required')
        self.rows=copy.deepcopy(rows);self.clocks=copy.deepcopy(clocks);self.faults=copy.deepcopy(faults or {});self.journal={};self.generation_claims={};self.consumer_commits=[];self.calls=[];self.serial=0
        ids=[r['Id'] for r in rows]
        if any(type(i) is not int or i<1 for i in ids) or len(ids)!=len(set(ids)):raise ValueError('Unique fake item IDs required')
    def snapshot(self):return copy.deepcopy(dict(rows=self.rows,clocks=self.clocks,faults=self.faults,journal=self.journal,generation_claims=self.generation_claims,consumer_commits=self.consumer_commits,calls=self.calls))
    def fail(self,key,phase):
        if self.faults.get(key)==phase:raise SimulationStop('simulated '+phase)
    def lookup(self,key):return [r for r in self.rows if isinstance(r.get('field_1'),str) and r['field_1'].casefold()==key.casefold()]
    def clock(self,minimum):
        if not self.clocks:raise SimulationStop('fake processing clock unavailable')
        value=self.clocks.pop(0)
        if core.instant(value,'fake actual processing time')<core.instant(minimum,'planned processing time'):raise SimulationStop('processing clock regressed')
        return value
    def stamp(self,row):
        self.serial+=1;row['__metadata']={**row.get('__metadata',{}),'etag':f'"fake-{self.serial}"'}
        major=int(row.get('OData__UIVersionString','0.0').split('.')[0])+1;row['OData__UIVersionString']=f'{major}.0'
        row.setdefault('versions',[]).append(dict(version=row['OData__UIVersionString'],evidence='in-memory simulation only'))
    def create(self,p,clock):
        self.calls.append(dict(kind='create',SourceKey=p['SourceKey']))
        self.fail(p['SourceKey'],'before_send')
        if self.faults.get(p['SourceKey'])=='create_race':
            self.rows.append(dict(Id=max((r['Id'] for r in self.rows),default=0)+1,field_1=p['SourceKey'].upper(),field_2=p['CanonicalKey'],Title='Concurrent creator; preserve'))
        if self.lookup(p['SourceKey']) or any(isinstance(r.get('field_2'),str) and r['field_2'].casefold()==p['CanonicalKey'].casefold() for r in self.rows):raise SimulationStop('atomic create identity conflict')
        values=copy.deepcopy(p['proposed_values']);values.update(FirstObservedUTC=clock,LastObservedUTC=clock)
        row={admission.MAPPING[k]:v for k,v in values.items()};row['Id']=max((r['Id'] for r in self.rows),default=0)+1;self.stamp(row);self.rows.append(row)
        if self.faults.get(p['SourceKey'])=='drop_full_title':row.pop('SourceFullTitle')
        self.fail(p['SourceKey'],'after_send');return copy.deepcopy(row)
    def update(self,p,current,clock):
        self.calls.append(dict(kind='observe',SourceKey=p['SourceKey']))
        self.fail(p['SourceKey'],'before_send')
        row=next(r for r in self.rows if r['Id']==current['Id'])
        if self.faults.get(p['SourceKey'])=='concurrent_edit':row['field_18']='Concurrent human edit';self.stamp(row)
        if row['__metadata']['etag']!=current['__metadata']['etag']:raise SimulationStop('conditional ETag conflict; no retry')
        row['field_20']=clock;self.stamp(row);self.fail(p['SourceKey'],'after_send');return copy.deepcopy(row)


def simulate(writer,manifest,parts,profiles,transport,*,expected_writer_sha256,expected_manifest_sha256,profile_pins):
    if type(transport) is not MemoryTransport:raise ValueError('Only the built-in in-memory transport is permitted')
    plan=prepare(writer,manifest,parts,profiles,expected_writer_sha256=expected_writer_sha256,expected_manifest_sha256=expected_manifest_sha256,profile_pins=profile_pins)
    if plan['source_contract_blockers']:return {**core.FLAGS,'status':'BLOCKED_QUALIFICATIONS','simulation_only':True,'blockers':plan['source_contract_blockers'],'consumer_committed':False}
    rows=feed.validate(manifest,parts,expected_manifest_sha256=expected_manifest_sha256);completed=[];active=None
    try:
        claims=[core.sha(dict(target=manifest['context']['target'],source=g['source'],generation=g['generation'])) for g in manifest['context']['generations']]
        if any(k in transport.generation_claims and transport.generation_claims[k]!=expected_manifest_sha256 for k in claims):raise SimulationStop('Generation already bound to a different immutable feed')
        for key in claims:transport.generation_claims[key]=expected_manifest_sha256
        for value in rows:
            p=value['proposal'];key=p['SourceKey'];op=value['operation_id'];active=None
            previous=transport.journal.get(op)
            if previous:
                if previous['feed_sha256']!=expected_manifest_sha256 or previous.get('proposal_sha256')!=core.sha(p):raise SimulationStop('journal/feed/proposal binding conflict')
                if previous['status']=='done':
                    outcome=previous.get('postimage')
                    if previous.get('postimage_sha256')!=core.sha(outcome):raise SimulationStop('journal outcome proof differs')
                    check_outcome(p,outcome,previous.get('processing_utc'));completed.append(op);continue
                raise SimulationStop('Prior intent or uncertain outcome requires reconciliation; no resend')
            transport.fail(key,'feed_version_changed');transport.fail(key,'read');matches=transport.lookup(key)
            if p['kind']=='create':
                if matches or any(r.get('field_2')==p['CanonicalKey'] for r in transport.rows):raise SimulationStop('create preimage changed')
                current=None
            else:
                if len(matches)!=1 or not core.same(matches[0],p['retained_current']):raise SimulationStop('fresh item preimage differs; preserve human changes')
                current=copy.deepcopy(matches[0]);core._metadata(current)
                if current['__metadata']['etag']=='*':raise SimulationStop('wildcard is not a conditional preimage')
            if p['kind']=='noop':
                transport.journal[op]=dict(feed_sha256=expected_manifest_sha256,proposal_sha256=core.sha(p),status='done',effect='none',postimage=copy.deepcopy(current),postimage_sha256=core.sha(current));completed.append(op);continue
            clock=transport.clock(manifest['context']['planned_processing_at_utc'])
            if current is not None and current.get('field_20') not in (None,'') and core.instant(clock,'processing clock')<core.instant(current['field_20'],'retained processing clock'):raise SimulationStop('processing time regressed')
            transport.fail(key,'intent');transport.journal[op]=dict(feed_sha256=expected_manifest_sha256,proposal_sha256=core.sha(p),status='intent',processing_utc=clock,kind=p['kind'],SourceKey=key);active=op
            transport.fail(key,'after_intent')
            result=transport.create(p,clock) if p['kind']=='create' else transport.update(p,current,clock)
            transport.fail(key,'readback')
            check_outcome(p,result,clock)
            saved=next((r for r in transport.rows if r['Id']==result['Id']),None)
            if not core.same(saved,result):raise SimulationStop('saved readback differs')
            transport.fail(key,'outcome');transport.journal[op].update(status='done',item_id=result['Id'],postimage=copy.deepcopy(result),postimage_sha256=core.sha(result));completed.append(op);active=None
        transport.fail('__batch__','commit')
        if expected_manifest_sha256 not in transport.consumer_commits:transport.consumer_commits.append(expected_manifest_sha256)
        return {**core.FLAGS,'status':'SIMULATED_COMPLETE','simulation_only':True,'consumer_committed':True,'completed_operations':completed,'native_runtime_verified':False}
    except (ValueError,KeyError,TypeError,StopIteration) as exc:
        if active is not None:transport.journal[active]['status']='uncertain'
        return {**core.FLAGS,'status':'SIMULATED_STOPPED','simulation_only':True,'consumer_committed':False,'completed_operations':completed,'reason':str(exc),'native_runtime_verified':False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('writer','feed','profiles','profile-pins','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--writer-sha256',required=True);p.add_argument('--manifest-sha256',required=True);a=p.parse_args(argv)
    try:
        docs={};hashes={}
        for name in ('writer','feed','profiles','profile_pins'):docs[name],hashes[name]=core.cli_read(getattr(a,name),ROOT)
        envelope=docs['feed']
        if not isinstance(envelope,dict) or envelope.get('kind')!='publication_writer_feed_local_v1' or not isinstance(envelope.get('parts_utf8'),dict) or any(not isinstance(v,str) for v in envelope['parts_utf8'].values()):raise ValueError('Exact local candidate feed envelope required')
        result=prepare(docs['writer'],envelope['manifest'],{n:v.encode('utf-8') for n,v in envelope['parts_utf8'].items()},docs['profiles'],expected_writer_sha256=a.writer_sha256,expected_manifest_sha256=a.manifest_sha256,profile_pins=docs['profile_pins'])
        core.exclusive_json(core.private_path(a.output,'output',ROOT,output=True),{**core.FLAGS,'kind':'publication_guarded_writer_local_v1','result':result,'source_files_sha256':hashes});return 0
    except (ValueError,OSError,KeyError,TypeError):print('Offline guarded writer preparation failed; prior files preserved',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
