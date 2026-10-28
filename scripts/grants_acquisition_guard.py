"""Qualify the actual NIH acquisition boundary with isolated HTTP faults."""
# SPDX-License-Identifier: Apache-2.0
import copy
from scripts.grants_order_guard import find, action_nodes


def strict_http_guard(definition):
    result=copy.deepcopy(definition);guard=find(result['actions'],'Guard_source')
    original=guard.get('inputs','')
    if guard.get('type') != 'Compose' or not isinstance(original, str) or not original.startswith('@if(and(equals(outputs(\'Fetch_response\')?[\'statusCode\'],200),'):
        raise ValueError('Exact current NIH acquisition guard required')
    guard['inputs']="@if(equals(outputs('Fetch_response')?['statusCode'],200),"+original[1:]+",json('NIH_HTTP_RESPONSE_REJECTED'))"
    return result


def fault_definition(source,diagnostic,code):
    if code not in [206,429]:raise ValueError('Only bounded controlled responses allowed')
    result=strict_http_guard(source)
    trigger=diagnostic['triggers']
    if set(trigger)!={'manual'} or trigger['manual'].get('kind')!='Button' or trigger['manual'].get('type')!='Request' or trigger['manual']['inputs']['schema']!={'type':'object','additionalProperties':False,'properties':{}}:
        raise ValueError('Exact input-free isolated trigger required')
    result['triggers']=copy.deepcopy(trigger)
    result.setdefault('parameters',{})['QualificationScenario']={'type':'String','defaultValue':'inspect'}
    actions=result['actions']
    if actions['Processing']['type']!='Scope' or actions['Acquisition']['type']!='Scope':raise ValueError('Exact acquisition/processing graph required')
    actions['Processing']['actions']={'Processing_would_run':{'type':'Compose','inputs':'UNEXPECTED_SOURCE_ACCEPTANCE'}}
    actions['Observe_processing_failure']['actions']={'Processing_failure':{'type':'Compose','inputs':'UNEXPECTED_PROCESSING_FAILURE'}}
    actions['Run_folder']['inputs']="@concat('/Documents/CHHHS Research System - DEV/01 Source archive/TEST_ONLY_G07_HTTP_"+str(code)+"-',workflow()?['run']?['name'])"
    fetch=find(actions,'Fetch_response')
    if fetch['type']!='Http' or fetch['inputs'].get('retryPolicy')!={'type':'none'}:raise ValueError('Existing no-retry HTTP fetch required')
    fetch['inputs']={'uri':'https://httpbin.org/status/'+str(code),'method':'GET','retryPolicy':{'type':'none'}}
    find(actions,'Fetch_attachment')['inputs']=copy.deepcopy(fetch['inputs'])
    failure=find(actions,'Save_failure')['inputs']['parameters']
    failure['folderPath']="@outputs('Run_folder')";failure['name']='failure.json'
    find(actions,'Read_failure')['inputs']['parameters']['path']="@concat(outputs('Run_folder'),'/failure.json')"
    def validate(v):
        if isinstance(v,dict):
            if v.get('type')=='Http' and v.get('inputs')!=fetch['inputs']:
                raise ValueError('No other HTTP acquisition or transmission allowed')
            if v.get('type')=='OpenApiConnection':
                i=v['inputs'];host=i['host'];p=i['parameters']
                if not host['apiId'].endswith('/shared_sharepointonline') or host['operationId'] not in ['HttpRequest','CreateFile','GetFileContentByPath']:
                    raise ValueError('Only archival SharePoint operations allowed')
                if host['operationId']=='HttpRequest' and (p.get('parameters/method')!='POST' or p.get('parameters/uri')!='_api/web/folders'):raise ValueError('Only isolated folder creation allowed')
                if host['operationId']=='CreateFile' and p.get('folderPath')!="@outputs('Run_folder')":raise ValueError('Archive write outside isolated folder')
                if host['operationId']=='GetFileContentByPath' and "outputs('Run_folder')" not in p.get('path',''):raise ValueError('Archive read outside isolated folder')
                if i.get('authentication')=="@parameters('$authentication')":i.pop('authentication')
                i['retryPolicy']={'type':'none'}
            for x in v.values():validate(x)
        elif isinstance(v,list):
            for x in v:validate(x)
    allowed = {'Compose','Scope','If','Foreach','Switch','ParseJson','InitializeVariable',
               'SetVariable','IncrementVariable','Terminate','Http','OpenApiConnection'}
    if any(node['type'] not in allowed for node in action_nodes(actions)):
        raise ValueError('Unknown or dispatch-capable action forbidden')
    validate(actions)
    return result
