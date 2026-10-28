"""Bind the actual grants importer to receipt-owned synthetic runtime cases only."""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy
import json
import re
from uuid import UUID
from scripts.grants_order_guard import find, action_nodes
from scripts.grants_registry import stable_key


def build(importer, diagnostic, owned, case):
    if (owned.get('marker')!='TEST_ONLY_G07_RECOVERY_20261028'
            or owned.get('title')!='TEST_ONLY_G07_RECOVERY_20261028_RESTORED'):
        raise ValueError('Exact accepted isolated list receipt required')
    target=owned.get('id')
    if not isinstance(target,str) or str(UUID(target)) != target:
        raise ValueError('Exact canonical isolated list identity required')
    rows=case.get('rows')
    if not isinstance(rows,list) or len(rows)!=1 or not isinstance(rows[0],dict):
        raise ValueError('One fixed synthetic row per native case required')
    row=rows[0]
    if (not str(row.get('Title','')).startswith('SYNTHETIC ACCEPTANCE')
            or row.get('Source') not in ['SYNTHETIC_ACCEPTANCE','   ']
            or row.get('SourceID') not in ['rims-guard-fixture',"rims-guard-fixture-o'brien",'   ']
            or row.get('RoundID') not in ['round-a','round-b']):
        raise ValueError('Real or unscoped source rows cannot enter this diagnostic')
    keys={stable_key({'Source':'SYNTHETIC_ACCEPTANCE','SourceID':sid,'RoundID':rnd})
          for sid,rnd in [('rims-guard-fixture','round-a'),("rims-guard-fixture-o'brien",'round-a'),('rims-guard-fixture','round-b')]}
    if row.get('OpportunityKey') not in keys|{'   '}:
        raise ValueError('Only the fixed synthetic key namespace may be written')
    source=copy.deepcopy(importer)
    old=find(source['actions'],'SharePoint_Get_items')['inputs']['parameters']['table']
    if not isinstance(old,str) or str(UUID(old))!=old:
        raise ValueError('Exact canonical source list identity required')
    if old==target:raise ValueError('Source and isolated target must differ')
    def replace(v):
        if isinstance(v,str):return re.sub(re.escape(old),target,v,flags=re.I)
        if isinstance(v,list):return [replace(x) for x in v]
        if isinstance(v,dict):return {k:replace(x) for k,x in v.items()}
        return v
    source=replace(source)
    allowed={'Compose','Scope','If','Foreach','ParseJson','InitializeVariable','SetVariable','IncrementVariable','Terminate','OpenApiConnection'}
    if any(n['type'] not in allowed for n in action_nodes(source['actions'])):
        raise ValueError('Unknown or external executable action forbidden')
    source_site=find(source['actions'],'SharePoint_Get_items')['inputs']['parameters']['dataset']
    def verify(v):
        if isinstance(v,dict):
            if v.get('type')=='Http':raise ValueError('No external HTTP acquisition in writer qualification')
            if v.get('type')=='OpenApiConnection':
                inputs=v['inputs'];host=inputs['host'];params=inputs['parameters'];operation=host['operationId']
                if host.get('apiId') != '/providers/Microsoft.PowerApps/apis/shared_sharepointonline':
                    raise ValueError('Only existing SharePoint connector allowed')
                if operation not in ['GetItems','PostItem','HttpRequest','GetItemAttachments','CreateAttachment','GetFileContent']:
                    raise ValueError('Unexpected native operation')
                if params.get('dataset')!=source_site:raise ValueError('Cross-site operation forbidden')
                if operation!='HttpRequest' and params.get('table')!=target:raise ValueError('Exact owned-copy table required')
                if operation=='HttpRequest':
                    uri=params.get('parameters/uri','');method=params.get('parameters/method')
                    if (not isinstance(uri,str) or '..' in uri or '\\' in uri
                            or re.search(r'%(?:25|2e|2f|5c)',uri,re.I)):
                        raise ValueError('Escaped or encoded target path forbidden')
                    if not uri.startswith("_api/web/lists(guid'"+target+"')/items(") or method not in ['GET','POST']:
                        raise ValueError('REST target/method is not an exact owned item read/merge')
                    headers=params.get('parameters/headers',{})
                    lowered={k.lower():v for k,v in headers.items()}
                    attachment=(str(lowered.get('content-type','')).lower().startswith('application/octet-stream')
                                and '/attachmentfiles/add(' in uri.lower())
                    if method=='POST' and not attachment and (lowered.get('x-http-method')!='MERGE' or not lowered.get('if-match') or lowered['if-match']=='*'):
                        raise ValueError('Only exact item merge or existing original-attachment path allowed')
                if 'authentication' in inputs:
                    if inputs['authentication']!="@parameters('$authentication')":raise ValueError('Unknown auth annotation')
                    inputs.pop('authentication')
                inputs['retryPolicy']={'type':'none'}
            for x in v.values():verify(x)
        elif isinstance(v,list):
            for x in v:verify(x)
    verify(source)
    source['triggers']=copy.deepcopy(diagnostic['triggers'])
    t=source['triggers']
    if (set(t)!={'manual'} or t['manual'].get('kind')!='Button'
            or t['manual'].get('type')!='Request'
            or t['manual']['inputs']['schema']!={'type':'object','additionalProperties':False,'properties':{}}):
        raise ValueError('Input-free manual diagnostic required')
    source.setdefault('parameters',{})['QualificationRowsJson']={'type':'String','defaultValue':json.dumps(rows,ensure_ascii=False,separators=(',',':'))}
    source['parameters']['QualificationScenario']={'type':'String','defaultValue':'inspect'}
    source['actions']['Parse_Reviewed_Rows']['inputs']="@json(parameters('QualificationRowsJson'))"
    if old.lower() in json.dumps(source).lower():raise ValueError('Canonical list reference survived isolation')
    return source
