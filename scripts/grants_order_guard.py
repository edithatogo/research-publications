"""Replay the saved importer chronology predicate read-only on an owned copy."""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy
from datetime import datetime, timedelta
from uuid import UUID


def find(actions, name):
    matches=[]
    def walk(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key==name and isinstance(item,dict):matches.append(item)
                walk(item)
        elif isinstance(value,list):
            for item in value:walk(item)
    walk(actions)
    if len(matches)!=1:raise ValueError('Exactly one native source action/predicate required: '+name)
    return matches[0]


def definition(diagnostic, importer, source_list_id, current):
    UUID(source_list_id)
    d=copy.deepcopy(diagnostic)
    if (d['triggers']['manual'].get('kind')!='Button' or d['triggers']['manual'].get('type')!='Request'
            or set(d['triggers'])!={'manual'}
            or d['triggers']['manual']['inputs']['schema']!={'type':'object','additionalProperties':False,'properties':{}}):
        raise ValueError('Input-free manual diagnostic required')
    read=copy.deepcopy(find(importer['actions'],'SharePoint_Get_items'))
    predicate=copy.deepcopy(find(importer['actions'],'Condition_Observation_Not_Older')['expression'])
    if (read.get('type')!='OpenApiConnection' or read['inputs']['host'].get('operationId')!='GetItems'
            or not read['inputs']['host'].get('apiId','').lower().endswith('/shared_sharepointonline')):
        raise ValueError('Only actual native read action may be cloned')
    observed=datetime.fromisoformat(current['RetrievedUTC'].replace('Z','+00:00'))
    if observed.utcoffset() is None:raise ValueError('Qualified source timestamp required')
    incoming=copy.deepcopy(current);incoming['RetrievedUTC']=(observed-timedelta(days=1)).isoformat()
    read['runAfter']={};read['inputs']['parameters']['table']=source_list_id
    read['inputs']['retryPolicy']={'type':'none'}
    if 'authentication' in read['inputs']:
        if read['inputs']['authentication']!="@parameters('$authentication')":raise ValueError('Unknown authentication annotation')
        read['inputs'].pop('authentication')
    d['actions']={
        'Initialize_rejected':{'type':'InitializeVariable','inputs':{'variables':[{'name':'Rejected','type':'boolean','value':False}]},'runAfter':{}},
        'For_each_observation':{'type':'Foreach','foreach':[incoming],'runAfter':{'Initialize_rejected':['Succeeded']},
            'runtimeConfiguration':{'concurrency':{'repetitions':1}},'actions':{
                'SharePoint_Get_items':read,
                'Condition_Observation_Not_Older':{'type':'If','expression':predicate,
                    'runAfter':{'SharePoint_Get_items':['Succeeded']},
                    'actions':{'Unexpected_acceptance':{'type':'Compose','inputs':"@json('TEST_ONLY_OLDER_OBSERVATION_ACCEPTED')"}},
                    'else':{'actions':{'Record_rejection':{'type':'SetVariable','inputs':{'name':'Rejected','value':True}}}}}}},
        'Assert_rejected':{'type':'Compose','inputs':"@if(equals(variables('Rejected'),true),true,json('TEST_ONLY_REJECTION_NOT_OBSERVED'))",'runAfter':{'For_each_observation':['Succeeded']}},
        'Qualification_result':{'type':'Compose','inputs':{'OlderObservationRejected':"@variables('Rejected')",'SourceWrites':0,'NotificationDelivered':False,'TimestampFixture':True},'runAfter':{'Assert_rejected':['Succeeded']}}}
    return d


def action_nodes(actions):
    """Walk executable action maps only, excluding schema/data type fields."""
    if not isinstance(actions, dict):
        raise ValueError('Action mapping required')
    for node in actions.values():
        if not isinstance(node, dict) or not isinstance(node.get('type'), str):
            raise ValueError('Typed executable action required')
        yield node
        if 'actions' in node:
            yield from action_nodes(node['actions'])
        for branch in [node.get('else'), node.get('default'), *node.get('cases', {}).values()]:
            if branch is not None:
                if not isinstance(branch, dict) or not isinstance(branch.get('actions'), dict):
                    raise ValueError('Complete action branch required')
                yield from action_nodes(branch['actions'])
