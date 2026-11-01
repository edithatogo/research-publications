"""Prepare same-object watchlist lifecycle over the existing Invoker connection.

Local preparation only. Requires the qualified additive preference schema before
native deployment. No sharing, scheduled delivery or external sends are defined.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
from zoneinfo import available_timezones


def build(preimage: dict) -> dict:
    """Bind caller identity to the native connection, never to supplied user fields."""
    result = copy.deepcopy(preimage)
    data = json.loads(result['clientdata'])
    props = data['properties']
    refs = props['connectionReferences']
    if (set(refs) != {'shared_sharepointonline'}
            or refs['shared_sharepointonline'].get('runtimeSource') != 'invoker'):
        raise ValueError('Existing qualified Invoker binding required')
    definition = props['definition']
    old = definition['actions']['Apply_to_each_Watchlist_Row']['actions']['SharePoint_Get_items']['inputs']
    site, table = old['parameters']['dataset'], old['parameters']['table']
    host, auth = copy.deepcopy(old['host']), copy.deepcopy(old['authentication'])
    def compose(value, previous=''):
        return {'type':'Compose','runAfter':{previous:['Succeeded']} if previous else {},'inputs':value}
    def guard(expression, previous):
        return compose("@if("+expression+",true,json('WATCHLIST_LIFECYCLE_GUARD_FAILED'))",previous)
    def http(method, uri, previous, *, body=None, headers=None):
        h=copy.deepcopy(host);h['operationId']='HttpRequest'
        params={'dataset':site,'parameters/method':method,'parameters/uri':uri,
                'parameters/headers':{'Accept':'application/json;odata=minimalmetadata',**(headers or {})}}
        if body is not None:params['parameters/body']=body
        return {'type':'OpenApiConnection','runAfter':{previous:['Succeeded']} if previous else {},
                'inputs':{'host':h,'parameters':params,'authentication':copy.deepcopy(auth),
                          'retryPolicy':{'type':'none'}}}
    preferences_schema={'type':'object','additionalProperties':False,
        'required':['EventTypes','ReminderOffsets','Cadence','Channel','Timezone'],
        'properties':{
            'EventTypes':{'type':'array','minItems':1,'uniqueItems':True,'items':{'type':'string','enum':['opportunity_changed','deadline_changed','deadline_cancelled','reminder']}},
            'ReminderOffsets':{'type':'array','uniqueItems':True,'items':{'type':'integer','minimum':0,'maximum':3660}},
            'Cadence':{'type':'string','enum':['immediate','daily','weekly']},
            'Channel':{'type':'string','enum':['email','calendar']},
            'Timezone':{'type':'string','enum':sorted(available_timezones())}}}
    trigger=definition['triggers']['manual']
    trigger['inputs']['schema']={'type':'object','additionalProperties':False,
        'required':['Operation','Scope','TargetKey'],'properties':{
            'Operation':{'type':'string','enum':['subscribe','pause','resume','unsubscribe']},
            'Scope':{'type':'string','enum':['opportunity','category','funder']},
            'TargetKey':{'type':'string','minLength':1,'maxLength':100},
            'ExpectedVersion':{'type':'string','maxLength':100},
            'Preferences':{'type':'string','maxLength':4000,'description':'Subscription preferences JSON; required for subscribe.'}}}
    trigger['runtimeConfiguration']={'concurrency':{'runs':1}}
    a={}
    a['Validate_request']={'type':'ParseJson','runAfter':{},'inputs':{
        'content':'@triggerBody()','schema':copy.deepcopy(trigger['inputs']['schema'])}}
    a['Guard_request']=guard("and(equals(triggerBody()?['TargetKey'],trim(triggerBody()?['TargetKey'])),not(empty(triggerBody()?['TargetKey'])))",'Validate_request')
    a['Configure_preferences']={'type':'If','runAfter':{'Guard_request':['Succeeded']},
        'expression':"@equals(triggerBody()?['Operation'],'subscribe')",
        'actions':{
            'Validate_preferences':{'type':'ParseJson','runAfter':{},'inputs':{'content':"@json(triggerBody()?['Preferences'])",'schema':preferences_schema}},
            'Guard_reminder_offsets':guard("equals(contains(body('Validate_preferences')?['EventTypes'],'reminder'),greater(length(body('Validate_preferences')?['ReminderOffsets']),0))",'Validate_preferences')},
        'else':{'actions':{}}}
    a['Caller_identity']=http('GET','_api/web/currentuser?$select=Id','Configure_preferences')
    a['Guard_caller']=guard("and(equals(outputs('Caller_identity')?['statusCode'],200),greater(int(body('Caller_identity')?['Id']),0))",'Caller_identity')
    # The site user ID comes from the connector's own authenticated identity.
    a['Preference_key']=compose("@concat('PREF:',base64(string(createArray(string(body('Caller_identity')?['Id']),triggerBody()?['Scope'],triggerBody()?['TargetKey']))))",'Guard_caller')
    a['Guard_key']=guard("lessOrEquals(length(outputs('Preference_key')),255)",'Preference_key')
    uri="@concat('_api/web/lists(guid''"+table+"'')/items?$select=Id,AuthorId,PreferenceKey,UserKey,Scope,TargetKey,Active,SubscriptionState,EventTypesJSON,ReminderOffsetsJSON,Cadence,Channel,Timezone&$filter=PreferenceKey eq ''',uriComponent(replace(outputs('Preference_key'),'''','''''')),'''&$top=2')"
    a['Read_store_boundary']=http('GET',"_api/web/lists(guid'"+table+"')?$select=ReadSecurity,WriteSecurity,EnableVersioning",'Guard_key')
    a['Guard_store_boundary']=guard("and(equals(outputs('Read_store_boundary')?['statusCode'],200),equals(body('Read_store_boundary')?['ReadSecurity'],2),equals(body('Read_store_boundary')?['WriteSecurity'],2),equals(body('Read_store_boundary')?['EnableVersioning'],true))",'Read_store_boundary')
    a['Read_preference']=http('GET',uri,'Guard_store_boundary')
    a['Guard_unique']=guard("and(equals(outputs('Read_preference')?['statusCode'],200),lessOrEquals(length(body('Read_preference')?['value']),1))",'Read_preference')
    a['Desired_state']=compose("@if(or(equals(triggerBody()?['Operation'],'subscribe'),equals(triggerBody()?['Operation'],'resume')),'active',if(equals(triggerBody()?['Operation'],'pause'),'paused','unsubscribed'))",'Guard_unique')
    values={'PreferenceKey':"@outputs('Preference_key')",'UserKey':"@string(body('Caller_identity')?['Id'])",
            'Scope':"@triggerBody()?['Scope']",'TargetKey':"@triggerBody()?['TargetKey']",
            'OpportunityKey':"@if(equals(triggerBody()?['Scope'],'opportunity'),triggerBody()?['TargetKey'],null)",
            'Active':"@equals(outputs('Desired_state'),'active')",'SubscriptionState':"@outputs('Desired_state')"}
    for stored,editable in [('EventTypesJSON','EventTypes'),('ReminderOffsetsJSON','ReminderOffsets'),('Cadence','Cadence'),('Channel','Channel'),('Timezone','Timezone')]:
        desired="body('Validate_preferences')?['"+editable+"']"
        if stored.endswith('JSON'):desired='string('+desired+')'
        values[stored]="@if(equals(triggerBody()?['Operation'],'subscribe'),"+desired+",first(body('Read_preference')?['value'])?['"+stored+"'])"
    create={'Guard_create':guard("equals(triggerBody()?['Operation'],'subscribe')",'')}
    create['Create_preference']=http('POST',"_api/web/lists(guid'"+table+"')/items",'Guard_create',body=values,headers={'Content-Type':'application/json;odata=nometadata'})
    update={}
    owner_matches = "equals(first(body('Read_preference')?['value'])?['AuthorId'],body('Caller_identity')?['Id'])"
    update['Guard_owner_version']=guard("and("+owner_matches+",equals(first(body('Read_preference')?['value'])?['UserKey'],string(body('Caller_identity')?['Id'])),equals(first(body('Read_preference')?['value'])?['PreferenceKey'],outputs('Preference_key')),equals(first(body('Read_preference')?['value'])?['Scope'],triggerBody()?['Scope']),equals(first(body('Read_preference')?['value'])?['TargetKey'],triggerBody()?['TargetKey']),not(empty(triggerBody()?['ExpectedVersion'])),not(equals(triggerBody()?['ExpectedVersion'],'*')),equals(triggerBody()?['ExpectedVersion'],coalesce(first(body('Read_preference')?['value'])?['odata.etag'],first(body('Read_preference')?['value'])?['@odata.etag'])))",'')
    update['Guard_transition']=guard("and(contains(createArray('active','paused','unsubscribed'),first(body('Read_preference')?['value'])?['SubscriptionState']),or(contains(createArray('subscribe','unsubscribe'),triggerBody()?['Operation']),and(equals(triggerBody()?['Operation'],'pause'),contains(createArray('active','paused'),first(body('Read_preference')?['value'])?['SubscriptionState'])),and(equals(triggerBody()?['Operation'],'resume'),contains(createArray('active','paused'),first(body('Read_preference')?['value'])?['SubscriptionState']))))",'Guard_owner_version')
    update['Update_preference']=http('POST',"@concat('_api/web/lists(guid''"+table+"'')/items(',string(first(body('Read_preference')?['value'])?['Id']),')')",'Guard_transition',body=values,headers={'Content-Type':'application/json;odata=nometadata','X-HTTP-Method':'MERGE','IF-MATCH':"@triggerBody()?['ExpectedVersion']"})
    a['Apply_transition']={'type':'If','runAfter':{'Desired_state':['Succeeded']},
        'expression':"@equals(length(body('Read_preference')?['value']),0)",'actions':create,'else':{'actions':update}}
    a['Read_saved_preference']=http('GET',uri,'Apply_transition')
    a['Guard_saved']=guard("and(equals(length(body('Read_saved_preference')?['value']),1),equals(first(body('Read_saved_preference')?['value'])?['AuthorId'],body('Caller_identity')?['Id']),equals(first(body('Read_saved_preference')?['value'])?['UserKey'],string(body('Caller_identity')?['Id'])),equals(first(body('Read_saved_preference')?['value'])?['SubscriptionState'],outputs('Desired_state')),equals(first(body('Read_saved_preference')?['value'])?['Active'],equals(outputs('Desired_state'),'active')))",'Read_saved_preference')
    a['Result']=compose({'PreferenceKey':"@outputs('Preference_key')",'SubscriptionState':"@outputs('Desired_state')",
        'Preferences':{'EventTypes':"@json(first(body('Read_saved_preference')?['value'])?['EventTypesJSON'])",'ReminderOffsets':"@json(first(body('Read_saved_preference')?['value'])?['ReminderOffsetsJSON'])",'Cadence':"@first(body('Read_saved_preference')?['value'])?['Cadence']",'Channel':"@first(body('Read_saved_preference')?['value'])?['Channel']",'Timezone':"@first(body('Read_saved_preference')?['value'])?['Timezone']"},
        'Version':"@coalesce(first(body('Read_saved_preference')?['value'])?['odata.etag'],first(body('Read_saved_preference')?['value'])?['@odata.etag'])",'DeliveryEnabled':False},'Guard_saved')
    definition['actions']=a
    result['clientdata']=json.dumps(data,separators=(',',':'))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preimage',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();private=Path(__file__).resolve().parents[1]/'private/ops'
    if not args.output.resolve().is_relative_to(private.resolve()):raise ValueError('Private output required')
    candidate=build(json.loads(args.preimage.read_text()))
    with args.output.open('x') as f:json.dump(candidate,f,indent=2)
    args.output.chmod(0o600)
    print('Prepared same-ID Invoker lifecycle candidate; additive schema/native proof still required')


if __name__=='__main__':main()
