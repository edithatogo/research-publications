"""Build no-data, no-write native HTTP fixture qualification definitions."""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy


def definition(baseline, status):
    if type(status) is not int or status not in (429, 206):
        raise ValueError('Only the two bounded HTTP fixture responses are allowed')
    d=copy.deepcopy(baseline)
    if (set(d['triggers'])!={'manual'} or d['triggers']['manual'].get('type')!='Request'
            or d['triggers']['manual'].get('kind')!='Button'
            or d['triggers']['manual']['inputs']['schema']!={'type':'object','additionalProperties':False,'properties':{}}
            or d['parameters']['QualificationScenario']['defaultValue']!='inspect'):
        raise ValueError('Existing input-free manual diagnostic required')
    d['actions']={
        'Fetch_controlled_response':{'type':'Http','inputs':{'uri':'https://httpbin.org/status/'+str(status),
            'method':'GET','retryPolicy':{'type':'none'}},'runAfter':{}},
        'Read_status':{'type':'Compose','runAfter':{'Fetch_controlled_response':['Succeeded','Failed','TimedOut']},
            'inputs':"@int(coalesce(outputs('Fetch_controlled_response')?['statusCode'],0))"},
        'Assert_expected_status':{'type':'Compose','runAfter':{'Read_status':['Succeeded']},
            'inputs':"@if(equals(outputs('Read_status'),"+str(status)+"),true,json('TEST_ONLY_UNEXPECTED_HTTP_STATUS'))"},
        'Qualification_result':{'type':'Compose','runAfter':{'Assert_expected_status':['Succeeded']},
            'inputs':{'FixtureResponseCode':"@outputs('Read_status')",'DispatchEnabled':False,
                      'NotificationDelivered':False,'SourceWrites':0,'ActualGrantProviderFault':False}}}
    return d
