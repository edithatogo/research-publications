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


def operation_inventory(definition):
    """Exact paths distinguish reused action names; no connector tier is inferred."""
    def walk(nodes, prefix):
        if not isinstance(nodes, dict):raise ValueError('Complete operation dictionary required')
        for name in nodes:core.identifier(name, 'operation name')
        for name in sorted(nodes):
            node = nodes[name]; path = prefix + [name]
            if not isinstance(node, dict):raise ValueError('Structured operation required')
            node_type = core.identifier(node.get('type'), 'operation type')
            inputs = node.get('inputs'); host = inputs.get('host', {}) if isinstance(inputs, dict) else {}
            if not isinstance(host, dict):raise ValueError('Structured operation host required')
            reference = host.get('connectionName', host.get('connectionReferenceName'))
            if 'connectionName' in host and 'connectionReferenceName' in host and host['connectionName'] != host['connectionReferenceName']:
                raise ValueError('Ambiguous operation connection reference')
            for value in (host.get('apiId'), host.get('operationId'), reference):
                if value is not None:core.identifier(value, 'exact operation binding')
            yield dict(path=path, node_type=node_type, api_id=host.get('apiId'),
                operation_id=host.get('operationId'), connection_reference=reference, node_sha256=core.sha(node))
            if 'actions' in node:yield from walk(node['actions'], path + ['actions'])
            for branch in ('else', 'default'):
                if branch in node:
                    value = node[branch]
                    if not isinstance(value, dict) or 'actions' not in value:raise ValueError('Complete operation branch required')
                    yield from walk(value['actions'], path + [branch, 'actions'])
            if 'cases' in node:
                cases = node['cases']
                if not isinstance(cases, dict):raise ValueError('Complete cases required')
                for case in cases:core.identifier(case, 'case name')
                for case in sorted(cases):
                    value = cases[case]
                    if not isinstance(value, dict) or 'actions' not in value:raise ValueError('Complete case actions required')
                    yield from walk(value['actions'], path + ['cases', case, 'actions'])
    if not isinstance(definition.get('triggers'), dict) or not definition['triggers']:
        raise ValueError('Complete nonempty trigger inventory required')
    return sorted([*walk(definition['actions'], ['actions']),
                   *walk(definition['triggers'], ['triggers'])], key=lambda r: r['path'])


def standard_evidence_diagnostic(writer, target, evidence, pins):
    """Reconcile pinned supplied claims only; this never qualifies licence rights."""
    # Admission itself imports the default preflight; reuse its guards lazily.
    from scripts.prepare_publication_admission_packet import exact_keys, fingerprint
    def literal(value):
        return (isinstance(value, str) and bool(value.strip()) and value == value.strip()
                and not value.startswith('@') and '@{' not in value and '{{' not in value)
    exact_keys(evidence, ('kind', 'complete', 'scope', 'policy', 'inventory', 'classifications'), 'Standard evidence')
    core.complete(evidence)
    if evidence['kind'] != 'publication_standard_connector_evidence_v1':raise ValueError('Versioned Standard evidence required')
    props = writer['flow']['properties']; refs = props['connectionReferences']
    actual = dict(evidence=core.sha(evidence), writer=core.sha(writer), target=core.sha(target),
        revision=core.sha(writer['saved_revision']), connection_references=core.sha(refs),
        policy=core.sha(evidence['policy']), inventory=core.sha(evidence['inventory']),
        classifications=core.sha(evidence['classifications']))
    exact_keys(pins, actual, 'independent Standard evidence pins')
    for name, value in actual.items():
        if fingerprint(pins[name], name) != value:raise ValueError('Independent Standard evidence pin differs: ' + name)
    expected_scope = dict(writer_sha256=actual['writer'], target_sha256=actual['target'],
        saved_revision=writer['saved_revision'], connection_references_sha256=actual['connection_references'])
    if not core.same(evidence['scope'], expected_scope):raise ValueError('Standard evidence target/revision scope differs')
    policy = evidence['policy']
    exact_keys(policy, ('kind', 'version', 'reference', 'power_automate_premium',
        'power_bi_entitlement', 'custom_connectors_allowed', 'allowed_classes'), 'no-Premium workload policy')
    for name in ('version', 'reference'):core.identifier(policy[name], 'policy ' + name)
    if (policy['kind'] != 'publication_standard_workload_policy_v1'
            or policy['power_automate_premium'] is not False or policy['custom_connectors_allowed'] is not False
            or policy['power_bi_entitlement'] != 'not_power_automate_evidence'
            or policy['allowed_classes'] != ['BuiltIn', 'Standard']):
        raise ValueError('Explicit no-Premium workload policy required')
    inventory = operation_inventory(props['definition'])
    if not core.same(evidence['inventory'], inventory):raise ValueError('Complete exact action/trigger inventory differs')
    classifications = evidence['classifications']
    if not isinstance(classifications, list):raise ValueError('Explicit classification inventory required')
    by_path = {tuple(row['path']): row for row in inventory}; claimed = {}; tiers = {}
    for entry in classifications:
        exact_keys(entry, ('operation', 'classification', 'version', 'reference', 'source_sha256',
            'operation_schema_sha256'), 'supplied operation classification')
        operation = entry['operation']
        exact_keys(operation, ('path', 'node_type', 'api_id', 'operation_id',
            'connection_reference', 'node_sha256'), 'classified operation')
        path = operation['path']
        if not isinstance(path, list) or not path or any(not isinstance(v, str) for v in path):raise ValueError('Exact classification path required')
        path = tuple(path)
        if path not in by_path or path in claimed or not core.same(operation, by_path[path]):
            raise ValueError('Ambiguous, extra or rebound operation classification')
        for name in ('version', 'reference'):core.identifier(entry[name], 'classification ' + name)
        for name in ('source_sha256', 'operation_schema_sha256'):fingerprint(entry[name], name)
        if not isinstance(entry['classification'], str) or entry['classification'] not in {'BuiltIn', 'Standard', 'Premium', 'Custom', 'Unknown'}:
            raise ValueError('Explicit supported classification or Unknown required')
        claimed[path] = entry
        identity = (operation['node_type'], operation['api_id'], operation['operation_id'])
        tiers.setdefault(identity, set()).add(entry['classification'])
    identities = {}
    for binding in refs.values():
        if isinstance(binding, dict) and isinstance(binding.get('connectionName'), str):
            identities.setdefault(binding['connectionName'], set()).add(core.sha(binding.get('id')))
    ambiguous = {name for name, apis in identities.items() if len(apis) > 1}
    operations = []; used = set(); blockers = set()
    for operation in inventory:
        path = tuple(operation['path']); claim = claimed.get(path); issues = []
        classification = claim['classification'] if claim else 'Unknown'
        if claim is None:issues.append('missing_classification')
        if classification not in policy['allowed_classes']:issues.append('disallowed_classification:' + classification)
        identity = (operation['node_type'], operation['api_id'], operation['operation_id'])
        if len(tiers.get(identity, ())) > 1:issues.append('inconsistent_classification')
        api, op, ref = (operation[n] for n in ('api_id', 'operation_id', 'connection_reference'))
        has_host = any(v is not None for v in (api, op, ref))
        if has_host or operation['node_type'] in {'OpenApiConnection', 'OpenApiConnectionWebhook'}:
            if classification == 'BuiltIn':issues.append('connector_claimed_builtin')
            if not all(v is not None for v in (api, op, ref)):
                issues.append('incomplete_connector_binding')
            elif not all(literal(v) for v in (api, op, ref)):issues.append('nonliteral_connector_binding')
            if ref is not None:
                used.add(ref); binding = refs.get(ref)
                if (not isinstance(binding, dict) or binding.get('id') != api
                        or not literal(binding.get('connectionName'))):
                    issues.append('unresolved_connection_reference')
                elif binding['connectionName'] in ambiguous:issues.append('ambiguous_connection_identity')
        elif classification == 'Standard':issues.append('standard_claim_without_connector_binding')
        blockers.update(issues)
        operations.append(dict(operation=copy.deepcopy(operation), classification=classification, blockers=sorted(issues)))
    connections = []
    for key in sorted(refs):
        core.identifier(key, 'connection reference key')
        issues = [] if key in used else ['unused_connection_reference']
        if (isinstance(refs[key], dict) and isinstance(refs[key].get('connectionName'), str)
                and refs[key]['connectionName'] in ambiguous):issues.append('ambiguous_connection_identity')
        blockers.update(issues)
        connections.append(dict(reference=key, captured=copy.deepcopy(refs[key]), blockers=issues))
    return dict(kind='publication_standard_connector_diagnostic_v1', claims_authenticated=False,
        licensing_qualified=False, policy_blockers=sorted(blockers), operations=operations,
        connections=connections, supplied_evidence=copy.deepcopy(evidence), independent_sha256=actual,
        limits='Supplied classifications and no-Premium policy are unauthenticated claims; exact rights, '
               'DLP, permissions, connection availability, action schemas and runtime remain unqualified')


def assess(writer,registry,target,*,expected_writer_sha256,standard_evidence=None,standard_pins=None):
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
    result = {**core.FLAGS,'kind':'publication_writer_preflight_v1','status':'SUPPLIED_STRUCTURE_ONLY',
        'writer_ready':False,'activation_permitted':False,'diagnostic_run_permitted':False,
        'structural_errors':structural,'blockers':sorted(set(blockers)),
        'writer_sha256':core.sha(writer),'registry_sha256':core.sha(s),'target_sha256':core.sha(target),
        'limits':'Frozen supplied evidence consistency only; native provenance, current access, freshness, save, run and recovery remain unqualified'}
    if standard_evidence is not None or standard_pins is not None:
        diagnostic = standard_evidence_diagnostic(writer, target, standard_evidence, standard_pins)
        result['standard_connector_evidence'] = diagnostic
        result['blockers'] = sorted(set(result['blockers']) | {'standard_evidence_claims_unauthenticated'} |
            {'standard_evidence:' + v for v in diagnostic['policy_blockers']})
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('writer','registry','target','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--standard-evidence', type=Path)
    p.add_argument('--standard-pins', type=Path)
    p.add_argument('--expected-writer-sha256',required=True);a=p.parse_args(argv)
    try:
        docs={};hashes={}
        for name in ('writer','registry','target'):docs[name],hashes[name]=core.cli_read(getattr(a,name),ROOT)
        if a.standard_evidence is not None or a.standard_pins is not None:
            if a.standard_evidence is None or a.standard_pins is None:raise ValueError('Paired Standard evidence and pins required')
            for name in ('standard_evidence', 'standard_pins'):docs[name],hashes[name]=core.cli_read(getattr(a,name),ROOT)
        result=assess(**docs,expected_writer_sha256=a.expected_writer_sha256)
        core.exclusive_json(core.private_path(a.output,'output',ROOT,output=True),{**core.FLAGS,'kind':'publication_writer_preflight_local_v1','result':result,'source_files_sha256':hashes});return 0
    except (ValueError,OSError,TypeError,KeyError):print('Offline writer preflight failed; inputs and prior files preserved',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
