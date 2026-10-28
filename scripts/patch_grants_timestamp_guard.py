"""Add caught, explicit observation diagnostics without deepening writer branches."""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy
from scripts.grants_order_guard import find


def patch(definition):
    result = copy.deepcopy(definition)
    actions = find(result['actions'], 'Condition_OpportunityKey_Present')['actions']
    conflict = actions.get('Condition_Conflicting_Source_Identity')
    if not conflict or conflict['runAfter'] != {'SharePoint_Get_source_identity': ['Succeeded']}:
        raise ValueError('Exact unpatched chronology preimage required')
    names = ('Validate_Observation_Instant', 'Handle_Malformed_Observation',
             'Validate_Incoming_Observation_UTC', 'Handle_Uncertain_Incoming_Observation')
    if any(name in actions for name in names):
        raise ValueError('Timestamp guard already present')
    def handler(previous, diagnostic, label):
        return {'type':'Scope','runAfter':{previous:['Failed','TimedOut']},'actions':{
            'Compose_'+label+'_Failure':{'type':'Compose','inputs':diagnostic},
            'Increment_'+label+'_Failure':{'type':'IncrementVariable',
                'inputs':{'name':'RowFailureCount','value':1},
                'runAfter':{'Compose_'+label+'_Failure':['Succeeded']}}}}
    actions[names[0]] = {
        'type':'Scope','runAfter':{'SharePoint_Get_source_identity':['Succeeded']},
        'actions':{'Parse_Observation_Ticks':{
            'type':'Compose','inputs':"@ticks(string(coalesce(item()?['RetrievedUTC'], '')))"}}}
    actions[names[1]] = handler(names[0],'MALFORMED_GRANTS_OBSERVATION_TIME','Malformed_Observation')
    # Guard new creates as well as updates, without adding another ancestor to
    # the already eight-level-deep conditional-merge branch.
    actions[names[2]] = {
        'type':'Scope','runAfter':{names[0]:['Succeeded']},
        'actions':{'Require_Incoming_UTC':{'type':'Compose','inputs':
            "@if(and(equals(item()?['RetrievedTimestampStatus'],'valid'),or(endsWith(string(coalesce(item()?['RetrievedUTC'],'')),'Z'),endsWith(string(coalesce(item()?['RetrievedUTC'],'')),'+00:00'))),true,json('UNCERTAIN_GRANTS_OBSERVATION_TIME'))"}}}
    actions[names[3]] = handler(names[2],'UNCERTAIN_GRANTS_OBSERVATION_TIME','Uncertain_Incoming_Observation')
    conflict['runAfter']={names[2]:['Succeeded']}
    return result
