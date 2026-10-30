"""Prepare a frozen, operator-qualified journal update inside an isolated flow.

Preserves the supplied wrapper/references/trigger and adds no connections. The
candidate is single-use: exact before/after journal and ETag are bound locally.
No untrusted input service, schedule, activation or send is introduced.
SPDX-License-Identifier: Apache-2.0
"""
import copy
import json
import re
from scripts.outcome_persistence import restore, digest, encode
from scripts.deploy_report_definition import fingerprint


def prepare(envelope, plan, *, expected_sha256, accepted_action, action_sha256, site_url, list_id, field_name):
    if fingerprint(envelope)!=expected_sha256 or fingerprint(accepted_action)!=action_sha256:
        raise ValueError('Exact definition and accepted action preimages required')
    from scripts.build_e09_no_send_flow import _definition
    _definition(site_url,list_id)  # Reuse the existing exact-target admission rules.
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,31}',field_name): raise ValueError('Exact field name required')
    restore(plan['journal'])
    if digest(plan['journal'])!=plan['after_sha256'] or plan['operation']!='update': raise ValueError('Validated update plan required')
    if type(plan['item_id']) is not int or plan['item_id']<1 or not isinstance(plan['etag'],str) or not plan['etag'] or plan['etag']=='*': raise ValueError('Exact item/ETag required')
    definition=envelope['properties']['definition']
    triggers=definition.get('triggers',{})
    if len(triggers)!=1 or any(t.get('type')!='Request' or t.get('kind')!='Button' for t in triggers.values()):
        raise ValueError('Existing isolated manual Button trigger required')
    if definition.get('actions'): raise ValueError('Existing actions require explicit semantic reconciliation; preserve them')
    host=accepted_action['inputs']['host']
    if accepted_action.get('type')!='OpenApiConnection' or host.get('operationId')!='HttpRequest' or host.get('apiId')!='/providers/Microsoft.PowerApps/apis/shared_sharepointonline':
        raise ValueError('Accepted standard SharePoint HTTP action required')
    connection=host.get('connectionName')
    if connection not in envelope['properties']['connectionReferences']: raise ValueError('Existing logical connection reference required')
    result=copy.deepcopy(envelope)
    uri=f"_api/web/lists(guid'{list_id}')/items({plan['item_id']})"
    def action(method,after,body=None):
        value=copy.deepcopy(accepted_action)
        value['runAfter']={after:['Succeeded']} if after else {}
        parameters={'dataset':site_url,'parameters/method':method,'parameters/uri':uri,
                    'parameters/headers':{'Accept':'application/json;odata=minimalmetadata','Content-Type':'application/json;odata=nometadata'}}
        if body is not None:
            parameters['parameters/headers'].update({'X-HTTP-Method':'MERGE','IF-MATCH':plan['etag']})
            parameters['parameters/body']=body
        value['inputs']['parameters']=parameters;value['inputs']['retryPolicy']={'type':'none'}
        return value
    read=action('GET',None)
    update=action('POST',None,{field_name:encode(plan['journal'])})
    # Exact ETag is server-enforced. Replay is read-only; a different current
    # revision fails with 412 rather than being overwritten or retried.
    condition={'type':'If','expression':{'equals':[f"@body('Read_journal')?['{field_name}']",encode(plan['journal'])]},
        'runAfter':{'Read_journal':['Succeeded']},'actions':{'Unchanged_replay':{'type':'Compose','inputs':{'writes':0,'no_send':True},'runAfter':{}}},
        'else':{'actions':{'Write_once':update}}}
    readback=action('GET','Apply_or_replay')
    readback['runAfter']={'Apply_or_replay':['Succeeded','Failed','TimedOut']}
    verify={'type':'ParseJson','inputs':{'content':{'matches':f"@equals(body('Readback')?['{field_name}'],{json.dumps(encode(plan['journal']))})"},'schema':{'type':'object','required':['matches'],'properties':{'matches':{'enum':[True]}}}},'runAfter':{'Readback':['Succeeded']}}
    # WDL string literals use doubled single quotes, not JSON quoting.
    literal="'"+encode(plan['journal']).replace("'","''")+"'"
    verify['inputs']['content']['matches']=f"@equals(body('Readback')?['{field_name}'],{literal})"
    result['properties']['definition']['actions']={'Read_journal':read,'Apply_or_replay':condition,'Readback':readback,'Verify_readback':verify}
    return {'candidate':result,'recovery':envelope,'native_ready':False,'plan_sha256':digest(plan),
            'limits':['Operator-qualified frozen plan only; no dynamic intake or identity resolution.','Actual trigger input transport, connector permissions and replay require native qualification.','Restore requires a fresh postimage ETag and no intervening edits.']}


def main(argv=None):
    import argparse,os,subprocess
    from pathlib import Path
    from scripts.deploy_report_definition import strict
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('envelope','plan','expected-sha256','accepted-action','action-sha256','site-url','list-id','field-name','output'): parser.add_argument('--'+name,required=True)
    a=parser.parse_args(argv)
    result=prepare(strict(Path(a.envelope).read_bytes()),strict(Path(a.plan).read_bytes()),expected_sha256=a.expected_sha256,accepted_action=strict(Path(a.accepted_action).read_bytes()),action_sha256=a.action_sha256,site_url=a.site_url,list_id=a.list_id,field_name=a.field_name)
    root=Path(__file__).resolve().parents[1];out=Path(a.output).resolve()
    if not out.is_relative_to(root/'private'/'ops'): raise ValueError('Private output required')
    subprocess.run(['git','check-ignore','-q',str(out)],cwd=root,check=True)
    with os.fdopen(os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:json.dump(result,f,indent=2,allow_nan=False)
    print('PASS_LOCAL_ONLY; no deployment or activation')


if __name__=='__main__':main()
