"""Build manual FlowAgent flows for owner-managed GrantConnect applications."""
import argparse
import json
from pathlib import Path
from uuid import UUID

from scripts.prepare_live_grants_calendar import after, branch, compose, envelope, guard, manual, spo

TITLE = 'RIMS Internal Grant Applications'
LIST = "_api/web/lists/getbytitle('" + TITLE + "')"
TRANSITIONS = {'Draft': ('Submitted', 'Withdrawn'), 'Submitted': ('Awarded', 'Unsuccessful', 'Withdrawn')}


def packet(c, actions, trigger, source):
    refs = {'shared_sharepointonline': {'id':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline',
            'connectionName':c['sharepoint_connection'], 'source':source}}
    return {'definition':envelope(actions,trigger),'connectionReferences':refs}


def setup(c):
    a={'Discover':spo(c,'GET',"_api/web/lists?$select=Id&$filter=Title eq '"+TITLE+"'"),
       'Unused':guard("empty(body('Discover')?['value'])",'Discover')}
    a['CreateList']=spo(c,'POST','_api/web/lists','Unused',body={
        'Title':TITLE,'BaseTemplate':100,'EnableVersioning':True,'ReadSecurity':2,'WriteSecurity':2})
    previous='CreateList'
    for field in ('ApplicationKey','Stage'):
        unique=' Indexed="TRUE"' if field=='ApplicationKey' else ''
        xml=f'<Field Type="Text" Name="{field}" StaticName="{field}" DisplayName="{field}" Required="TRUE"{unique} />'
        a[field]=spo(c,'POST',LIST+'/fields/createfieldasxml',previous,body={'parameters':{'SchemaXml':xml,'Options':0}})
        previous=field
    a['Store']=spo(c,'GET',LIST+'?$select=Id,ReadSecurity,WriteSecurity,EnableVersioning',previous)
    a['Boundary']=guard("and(equals(body('Store')?['ReadSecurity'],2),equals(body('Store')?['WriteSecurity'],2),equals(body('Store')?['EnableVersioning'],true))",'Store')
    return packet(c,a,manual(),'Embedded')


def build(c):
    trigger=manual()
    trigger['manual']['inputs']['schema']={'type':'object','additionalProperties':False,'required':['RegistryID','Target','ExpectedVersion'],
        'properties':{'RegistryID':{'type':'integer','minimum':1},'Target':{'type':'string','enum':['Read','Draft','Submitted','Awarded','Unsuccessful','Withdrawn']},
                      'ExpectedVersion':{'type':'string','description':'Use new for creation, read for lookup, or the saved ETag for a transition.'}}}
    a={'Request':{'type':'ParseJson','runAfter':{},'inputs':{'content':'@triggerBody()','schema':trigger['manual']['inputs']['schema']}},
       'Caller':spo(c,'GET','_api/web/currentuser?$select=Id,Email','Request'),
       'Operator':guard("equals(toLower(body('Caller')?['Email']),'"+c['operator_email'].lower()+"')",'Caller'),
       'Store':spo(c,'GET',LIST+'?$select=ReadSecurity,WriteSecurity,EnableVersioning','Operator'),
       'Boundary':guard("and(greater(int(body('Caller')?['Id']),0),equals(body('Store')?['ReadSecurity'],2),equals(body('Store')?['WriteSecurity'],2),equals(body('Store')?['EnableVersioning'],true))",'Store')}
    registry=str(UUID(c['registry_id']))
    a['Opportunity']=spo(c,'GET',"_api/web/lists(guid'"+registry+"')/items(@{int(triggerBody()['RegistryID'])})?$select=Title,OpportunityKey,Source",'Boundary')
    a['GrantConnect']=guard("and(equals(body('Opportunity')?['Source'],'GrantConnectRSS'),not(empty(body('Opportunity')?['OpportunityKey'])))",'Opportunity')
    a['Key']=compose("@concat(string(body('Caller')?['Id']),'/',body('Opportunity')?['OpportunityKey'])",'GrantConnect')
    lookup=LIST+"/items?$select=Id,AuthorId,ApplicationKey,Stage,Title&$filter=ApplicationKey eq '@{uriComponent(replace(outputs('Key'),'''',''''''))}'&$top=2"
    a['Existing']=spo(c,'GET',lookup,'Key')
    a['Unique']=guard("lessOrEquals(length(body('Existing')?['value']),1)",'Existing')
    first="first(body('Existing')?['value'])"
    create={'New':guard("and(equals(triggerBody()['Target'],'Draft'),equals(triggerBody()['ExpectedVersion'],'new'))"),
            'Create':spo(c,'POST',LIST+'/items','New',body={'ApplicationKey':"@outputs('Key')",'Stage':'Draft','Title':"@body('Opportunity')?['Title']"})}
    rules=','.join("and(equals("+first+"?['Stage'],'"+old+"'),contains(createArray("+','.join("'"+s+"'" for s in targets)+"),triggerBody()['Target']))" for old,targets in TRANSITIONS.items())
    change={'Current':guard("and(equals("+first+"?['AuthorId'],body('Caller')?['Id']),equals("+first+"?['odata.etag'],triggerBody()['ExpectedVersion']),or("+rules+"))"),
            'Save':spo(c,'POST',LIST+"/items(@{int("+first+"?['Id'])})",'Current',body={'Stage':"@triggerBody()['Target']"},etag="@"+first+"?['odata.etag']")}
    a['Write']=branch("@not(equals(triggerBody()['Target'],'Read'))",{'NewOrExisting':branch("@empty(body('Existing')?['value'])",create,change)},previous='Unique')
    a['Saved']=spo(c,'GET',lookup,'Write')
    a['Result']=compose("@body('Saved')?['value']",'Saved')
    return packet(c,a,trigger,'Embedded')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=['setup','writer'])
    p.add_argument('context',type=Path)
    args=p.parse_args()
    print(json.dumps((setup if args.operation=='setup' else build)(json.loads(args.context.read_bytes()))))
