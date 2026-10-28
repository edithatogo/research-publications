"""Compose accepted Calendar/Ledger logic on receipt-owned test stores only."""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy,json,re
from scripts.grants_order_guard import action_nodes


def namespace_actions(actions, prefix):
    """Namespace executable actions/references, preserving data property names."""
    if not isinstance(prefix,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*_',prefix):
        raise ValueError('Explicit action namespace required')
    names=[]
    def collect(nodes):
        for name,node in nodes.items():
            names.append(name)
            if 'actions' in node:collect(node['actions'])
            for branch in [node.get('else'),node.get('default'),*node.get('cases',{}).values()]:
                if branch is not None:collect(branch['actions'])
    list(action_nodes(actions));collect(actions)
    if len(names)!=len(set(names)):raise ValueError('Ambiguous nested action names')
    mapping={name:prefix+name for name in names}
    pattern=re.compile(r"\b(outputs|body|actions|items|result)\('([^']+)'\)")
    def values(value):
        if isinstance(value,str):
            if not value.startswith('@') and '@{' not in value:return value
            return pattern.sub(lambda m:m[1]+"('"+mapping.get(m[2],m[2])+"')",value)
        if isinstance(value,list):return [values(v) for v in value]
        if isinstance(value,dict):return {k:values(v) for k,v in value.items()}
        return value
    def transform(nodes):
        result={}
        for name,node in nodes.items():
            updated={k:values(v) for k,v in node.items() if k not in {'actions','else','default','cases','runAfter'}}
            if 'runAfter' in node:updated['runAfter']={mapping.get(k,k):copy.deepcopy(v) for k,v in node['runAfter'].items()}
            if 'actions' in node:updated['actions']=transform(node['actions'])
            for key in ['else','default']:
                if key in node:updated[key]={**copy.deepcopy(node[key]),'actions':transform(node[key]['actions'])}
            if 'cases' in node:updated['cases']={k:{**copy.deepcopy(v),'actions':transform(v['actions'])} for k,v in node['cases'].items()}
            result[mapping[name]]=updated
        return result
    return transform(actions)


def build(calendar, ledger, stores, *, source_stores, source_list_id, source_item_id, mapping, marker):
    kinds={'calendar','changes','watchlist','ledger'}
    def guid(value):
        return isinstance(value,str) and bool(re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',value))
    if (not isinstance(marker,str) or not re.fullmatch(r'TEST_ONLY_G0708_[0-9]{8}',marker)
            or not isinstance(stores,dict) or set(stores)!=kinds
            or not isinstance(source_stores,dict) or set(source_stores)!=kinds
            or not guid(source_list_id) or any(not guid(v) for v in source_stores.values())):
        raise ValueError('Explicit exact source/store identities required')
    if type(source_item_id) is not int or source_item_id!=1:
        raise ValueError('Exact source item identity required')
    if any(not isinstance(r,dict) or not guid(r.get('id')) for r in stores.values()):
        raise ValueError('Exact owned store receipts required')
    if len({r['id'] for r in stores.values()})!=4 or len(set(source_stores.values()))!=4:
        raise ValueError('Distinct source and owned stores required')
    for key,r in stores.items():
        if r.get('marker')!=marker or r.get('key')!=key or r.get('title')!=marker+'_'+key:
            raise ValueError('Store ownership marker mismatch')
    if (not isinstance(mapping,dict) or not isinstance(mapping.get('OpportunityKey'),str)
            or not re.fullmatch(r'GRANT:[a-f0-9]{24}',mapping['OpportunityKey'])
            or not isinstance(mapping.get('source_response_sha256'),str)
            or not re.fullmatch(r'[a-f0-9]{64}',mapping['source_response_sha256'])
            or not isinstance(mapping.get('FunderKey'),str) or not mapping['FunderKey']
            or mapping['FunderKey']!=mapping['FunderKey'].strip()
            or not isinstance(mapping.get('CategoryKeys'),list) or not mapping['CategoryKeys']
            or any(not isinstance(v,str) or not v or v!=v.strip() for v in mapping['CategoryKeys'])):
        raise ValueError('Explicit supplied classification identity/hash required')
    mapping=copy.deepcopy(mapping)
    mapping['FunderKey']=mapping['FunderKey'].replace("'","''")
    c=copy.deepcopy(calendar['properties']['definition']);l=copy.deepcopy(ledger['properties']['definition'])
    # Explicit contract-bound old identities, no field renaming or target guessing.
    old=dict(source_stores)
    forbidden={value.lower() for value in old.values()} | {source_list_id.lower()}
    if any(not re.fullmatch(r'[a-fA-F0-9-]{36}',r['id']) or r['id'].lower() in forbidden for r in stores.values()):
        raise ValueError('Canonical/source identities can never be downstream mutation targets')
    for d in [c,l]:
        text=json.dumps(d)
        for key,value in old.items():text=text.replace(value,stores[key]['id'])
        d.clear();d.update(json.loads(text))
    if any(value in json.dumps([c,l]) for value in old.values()):raise ValueError('Canonical store binding remains')
    ca=c['actions'];la=l['actions'];ca['Calendar_result']=ca.pop('Result');la['Ledger_result']=la.pop('Result')
    connector=copy.deepcopy(la['Caller_identity']);connector['runAfter']={}
    if connector['inputs'].get('authentication') not in (None,"@parameters('$authentication')"):
        raise ValueError('Unknown authentication annotation')
    connector['inputs'].pop('authentication',None)
    params=connector['inputs']['parameters']
    if params.get('parameters/method')!='GET':raise ValueError('Supplied caller identity must be read-only')
    params.pop('parameters/body',None)
    params['parameters/method']='GET';params['parameters/uri']=f"_api/web/lists(guid'{source_list_id}')/items({source_item_id})?$select=Id,OpportunityKey,EvidenceHash,ReviewStatus,FunderKey,CategoryKeysJSON,ClassificationEvidenceJSON"
    connector['inputs']['retryPolicy']={'type':'none'}
    source="outputs('Source')";evidence="json(coalesce("+source+"?['ClassificationEvidenceJSON'],'{}'))"
    predicate=("and(equals("+source+"?['OpportunityKey'],'"+mapping['OpportunityKey']+"'),"
               "equals("+evidence+"?['format'],'rims-reviewed-source-codes-v1'),"
               "equals("+evidence+"?['OpportunityKey'],"+source+"?['OpportunityKey']),"
               "equals("+evidence+"?['source_evidence_hash'],"+source+"?['EvidenceHash']),"
               "equals("+evidence+"?['source_response_sha256'],'"+mapping['source_response_sha256']+"'),"
               "equals("+evidence+"?['FunderKey'],"+source+"?['FunderKey']),"
               "equals("+evidence+"?['CategoryKeys'],json(coalesce("+source+"?['CategoryKeysJSON'],'[]'))),"
               "equals("+evidence+"?['FunderKey'],'"+mapping['FunderKey']+"'),"
               "equals("+evidence+"?['CategoryKeys'],json('"+json.dumps(mapping['CategoryKeys'],separators=(',',':')).replace("'","''")+"')))" )
    fixture={'DeadlineKey':'TEST_ONLY_G0708_DAY','OpportunityKey':'TEST_ONLY_G0708_OP','Revision':'TEST_ONLY_R1',
             'CalculatedDate':'2099-01-07','SourceURL':'https://example.invalid/TEST_ONLY_G0708',
             'Cancelled':False,'PolicyKey':'TEST_ONLY_NO_POLICY','ReviewStatus':'Reviewed','DeadlinePrecision':'day',
             'Title':marker+' FICTIONAL downstream case','FunderKey':'@'+source+"?['FunderKey']",
             'CategoryKeysJSON':'@'+source+"?['CategoryKeysJSON']",'PreviousRevision':None}
    ca['Parse_Calendar_Rows']['inputs']['content']=[fixture]
    request={'Operation':'plan','OpportunityKey':fixture['OpportunityKey'],'DeadlineKey':fixture['DeadlineKey'],
             'EventType':'deadline_changed','Revision':fixture['Revision'],'Channel':'email','OffsetDays':None}
    la['Validate_request']['inputs']['content']=request
    source_site=params.get('dataset')
    allowed={'Compose','Scope','If','Foreach','Switch','ParseJson','Select','Query','InitializeVariable','SetVariable','IncrementVariable','Terminate','OpenApiConnection'}
    for branch in [ca,la]:
        for node in action_nodes(branch):
            if node['type'] not in allowed:raise ValueError('Unknown or dispatch-capable action forbidden')
            if node['type']=='OpenApiConnection':
                inputs=node['inputs'];host=inputs['host'];p=inputs['parameters']
                if (host.get('apiId')!='/providers/Microsoft.PowerApps/apis/shared_sharepointonline'
                        or host.get('operationId')!='HttpRequest' or p.get('dataset')!=source_site):
                    raise ValueError('Only same-site standard SharePoint operations allowed')
                uri=p.get('parameters/uri','');method=p.get('parameters/method')
                if (not isinstance(uri,str) or '..' in uri or '\\' in uri
                        or re.search(r'%(?:25|2e|2f|5c)',uri,re.I)):
                    raise ValueError('Escaped or encoded target path forbidden')
                if not (method=='GET' and uri=='_api/web/currentuser'):
                    if method not in {'GET','POST'} or not any(re.match(r"^_api/web/lists\(guid'"+re.escape(r['id'])+r"'\)/items(?:$|[(/?])",uri) for r in stores.values()):
                        raise ValueError('Operation outside exact owned stores')
                if inputs.get('authentication') not in (None,"@parameters('$authentication')"):
                    raise ValueError('Unknown authentication annotation')
                inputs.pop('authentication',None);inputs['retryPolicy']={'type':'none'}
    ca=namespace_actions(ca,'Cal_');la=namespace_actions(la,'Led_')
    definition={'$schema':c['$schema'],'contentVersion':'1.0.0.0',
                'metadata':{'failureAlertSubscription':False},'parameters':{**copy.deepcopy(c['parameters']),'QualificationScenario':{'type':'String','defaultValue':'inspect'}},
                'triggers':{'manual':{'type':'Request','kind':'Button','inputs':{'schema':{'type':'object','additionalProperties':False,'properties':{}}},'runtimeConfiguration':{'concurrency':{'runs':1}}}},
                'actions':{'Read_source_copy':connector,
                           'Source':{'type':'Compose','runAfter':{'Read_source_copy':['Succeeded']},'inputs':"@body('Read_source_copy')"},
                           'Guard_classification_current':{'type':'Compose','runAfter':{'Source':['Succeeded']},'inputs':"@if("+predicate+",true,json('TEST_ONLY_CLASSIFICATION_REVIEW_REQUIRED'))"},
                           'Select_operation':{'type':'Switch','runAfter':{'Guard_classification_current':['Succeeded']},'expression':"@parameters('QualificationScenario')",'cases':{
                               'Calendar_copy':{'case':'calendar','actions':ca},'Ledger_copy':{'case':'plan','actions':la}},'default':{'actions':{}}},
                           'Qualification_result':{'type':'Compose','runAfter':{'Select_operation':['Succeeded']},'inputs':{
                               'Scenario':"@parameters('QualificationScenario')",'TestOnly':True,'NotificationDelivered':False,'DeliveryEnabled':False,
                               'ActualOpportunityReviewed':"@equals(outputs('Source')?['ReviewStatus'],'Reviewed')",
                               'ActualSourceClassificationCurrent':True,'FixtureScope':'explicit fictional Calendar/Ledger keys; no source approval or real deadline change'}}}}
    refs=copy.deepcopy(calendar['properties']['connectionReferences'])
    if set(refs)!={'shared_sharepointonline'}:raise ValueError('Exact existing standard connection required')
    if refs!=ledger['properties'].get('connectionReferences'):
        raise ValueError('Exact common supplied connection references required')
    # Preserve caller-owned references verbatim; native adoption/auth is separate.
    props={'displayName':marker+' downstream qualification','definition':definition,'connectionReferences':refs,
           'state':'Stopped','flowFailureAlertSubscribed':False}
    return {'properties':props}
