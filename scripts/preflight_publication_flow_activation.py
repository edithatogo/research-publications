# SPDX-License-Identifier: Apache-2.0
"""Inspect supplied stopped-writer evidence offline; never permit activation."""
import argparse
import copy
from pathlib import Path
import re
import sys
if not __package__:sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import prepare_publication_registry_bootstrap as core
from scripts.validate_publication_platform_contract import validate
ROOT=Path(__file__).resolve().parents[1]
TERMINAL={'Succeeded','Failed','Cancelled','Canceled','TimedOut','Skipped'}


def action_nodes(actions):
    if not isinstance(actions,dict):raise ValueError('Complete action dictionary required')
    for name,node in actions.items():
        core.identifier(name,'action name')
        if not isinstance(node,dict):raise ValueError('Malformed action')
        yield name,node
        for key in ('actions','else','default'):
            if key in node:
                child=node[key]
                if not isinstance(child,dict):raise ValueError('Malformed action branch')
                yield from action_nodes(child if key=='actions' else child.get('actions',{}))
        if 'cases' in node:
            if not isinstance(node['cases'],dict):raise ValueError('Malformed cases')
            for case in node['cases'].values():
                if not isinstance(case,dict):raise ValueError('Malformed case')
                yield from action_nodes(case.get('actions',{}))


def assess(writer,registry,target,*,expected_writer_sha256):
    core.canonical(writer);core.complete(writer);s=core.validate_snapshot(registry)
    if not isinstance(expected_writer_sha256,str) or not re.fullmatch('[a-f0-9]{64}',expected_writer_sha256) or core.sha(writer)!=expected_writer_sha256:raise ValueError('Independent complete writer preimage hash mismatch')
    if not isinstance(target,dict) or set(target)!={'site_url','list_id','model_id','workspace_id','flow_id','environment'}:raise ValueError('Exact independent target required')
    for key in ('list_id','model_id','workspace_id','flow_id'):core.guid(target[key])
    core.identifier(target['environment'],'environment');core.guid(target['environment'].removeprefix('Default-'))
    if target['site_url']!=s['site_url'] or target['list_id']!=s['list_id']:raise ValueError('Registry target differs')
    core.identifier(writer.get('capture_reference'),'writer capture');core.instant(writer.get('observed_at_utc'),'writer capture time')
    revision=core.identifier(writer.get('saved_revision'),'saved writer revision')
    if revision.startswith('version:'):core.version_key(revision[8:])
    elif not re.fullmatch(r'etag:(?:W/)?"[^"\r\n]+"',revision):raise ValueError('Exact saved version/ETag required')
    flow=writer.get('flow');resource=f"/providers/Microsoft.ProcessSimple/environments/{target['environment']}/flows/{target['flow_id']}"
    if not isinstance(flow,dict) or flow.get('id')!=resource or flow.get('name')!=target['flow_id']:raise ValueError('Flow target differs')
    props=flow.get('properties')
    if not isinstance(props,dict) or props.get('state')!='Stopped' or not isinstance(props.get('connectionReferences'),dict) or not props['connectionReferences']:raise ValueError('Complete stopped writer and retained connections required')
    history=writer.get('run_history');core.complete(history)
    core.identifier(history.get('capture_reference'),'run history capture')
    core.instant(history.get('observed_at_utc'),'run history capture time')
    if history.get('flow_id')!=target['flow_id'] or history.get('environment')!=target['environment'] or not isinstance(history.get('value'),list) or type(history.get('item_count')) is not int or history['item_count']!=len(history['value']):raise ValueError('Exact complete run inventory required')
    seen=set()
    for run in history['value']:
        if not isinstance(run,dict) or not isinstance(run.get('properties'),dict):raise ValueError('Malformed run')
        name=core.identifier(run.get('name'),'run identity')
        status=run['properties'].get('status')
        if name in seen or not isinstance(status,str) or status not in TERMINAL:raise ValueError('Duplicate or nonterminal run')
        seen.add(name)
    definition=props.get('definition')
    if not isinstance(definition,dict):raise ValueError('Complete definition required')
    nodes=list(action_nodes(definition.get('actions')));names={n for n,_ in nodes};blockers=[]
    query_count=sharepoint_count=0;conditional=False
    for name,node in nodes:
        inputs=node.get('inputs',{});params=inputs.get('parameters',{}) if isinstance(inputs,dict) else {}
        host=inputs.get('host',{}) if isinstance(inputs,dict) else {}
        if not isinstance(params,dict) or not isinstance(host,dict):raise ValueError('Malformed action inputs')
        api=host.get('apiId','')
        if not isinstance(api,str):raise ValueError('Malformed connector API')
        if api.endswith('shared_sharepointonline'):
            sharepoint_count+=1
            if params.get('dataset')!=target['site_url'] or ('table' in params and params['table']!=target['list_id']):raise ValueError('SharePoint target drift')
            if host.get('operationId') in {'GetItems','GetItem','PostItem','PatchItem'} and params.get('table')!=target['list_id']:raise ValueError('Required list binding missing')
            if host.get('operationId')=='HttpRequest':
                uri=params.get('parameters/uri')
                if not isinstance(uri,str) or not uri.startswith("_api/web/lists(guid'"+target['list_id']+"')/"):raise ValueError('Unqualified HTTP list scope')
        headers=params.get('parameters/headers',{})
        if not isinstance(headers,dict):raise ValueError('Malformed HTTP headers')
        etag=headers.get('IF-MATCH')
        if etag is not None and not isinstance(etag,str):raise ValueError('Malformed conditional ETag')
        conditional=conditional or etag not in (None,'','*')
        if host.get('operationId')=='ExecuteDatasetQuery':
            query_count+=1
            if params.get('datasetid')!=target['model_id'] or params.get('groupid')!=target['workspace_id']:raise ValueError('Query model/workspace drift')
        query=params.get('specification/query','')
        if not isinstance(query,str):raise ValueError('Malformed query text')
        if re.search(r'\bTOPN\s*\(\s*100\b',query,re.I):blockers.append('pilot_topn_100')
        if re.search(r'"dora:"\s*&\s*Publication\[CanonicalKey\]',query,re.I):blockers.append('inferred_dora_source_key')
        foreach=node.get('foreach','')
        if isinstance(foreach,str) and re.search(r'coalesce\s*\(',foreach,re.I) and re.search(r"(?:json\s*\(\s*'\[\]'|createArray\s*\(\s*\))",foreach,re.I):blockers.append('missing_rows_coalesced_to_empty')
        if params.get('item/field_17')=='Needs Review':blockers.append('legacy_needs_review_policy')
    if query_count<2 or sharepoint_count<3:raise ValueError('Required saved query/registry bindings missing')
    required={'Compose_SourceKey_Required','Condition_Publication_Row_Count','Condition_Invalid_SourceKeys'}
    blockers.append('missing_complete_batch_guard' if not required<=names else 'complete_batch_semantics_unqualified')
    blockers.append('missing_full_title_protection' if 'Compose_Source_Full_Title_Required' not in names else 'full_title_semantics_unqualified')
    blockers.append('missing_conditional_etag_protection' if not conditional else 'conditional_etag_semantics_unqualified')
    # This slice qualifies no alternative writer graph. Names, expressions or a
    # successful common structural check never grant a positive readiness result.
    blockers.append('writer_profile_not_qualified')
    try:structural=validate(copy.deepcopy(definition))
    except (KeyError,TypeError,AttributeError,IndexError):raise ValueError('Malformed common writer graph') from None
    return {**core.FLAGS,'kind':'publication_writer_preflight_v1','status':'SUPPLIED_STRUCTURE_ONLY',
        'writer_ready':False,'activation_permitted':False,'diagnostic_run_permitted':False,
        'structural_errors':structural,'blockers':sorted(set(blockers)),
        'writer_sha256':core.sha(writer),'registry_sha256':core.sha(s),'target_sha256':core.sha(target),
        'limits':'Frozen supplied evidence consistency only; native provenance, current access, freshness, save, run and recovery remain unqualified'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('writer','registry','target','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--expected-writer-sha256',required=True);a=p.parse_args(argv)
    try:
        docs={};hashes={}
        for name in ('writer','registry','target'):docs[name],hashes[name]=core.cli_read(getattr(a,name),ROOT)
        result=assess(**docs,expected_writer_sha256=a.expected_writer_sha256)
        core.exclusive_json(core.private_path(a.output,'output',ROOT,output=True),{**core.FLAGS,'kind':'publication_writer_preflight_local_v1','result':result,'source_files_sha256':hashes});return 0
    except (ValueError,OSError,TypeError,KeyError):print('Offline writer preflight failed; inputs and prior files preserved',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
