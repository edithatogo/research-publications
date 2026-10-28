"""Build the single-operator email worker using existing standard connections.

Manual management invocation, fixed recipient, frozen reviewed event, native
claim-before-send and receipt reconciliation. No callback credential or retry.
"""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import base64,json,re
from uuid import UUID


def build(context,event):
    c=dict(context)
    for k in ['ledger_id','registry_id','watchlist_id','calendar_id']:c[k]=str(UUID(c[k]))
    if not re.fullmatch(r'[^\s<>\x27";,@]+@[^\s<>\x27";,@]+',c['operator_email']):raise ValueError('One fixed operator mailbox required')
    if not re.fullmatch(r'https://[a-z0-9-]+(?:-my)?\.sharepoint\.com/[^?#]+',c['site'],re.I):raise ValueError('Qualified exact SharePoint site required')
    if event.get('Scope') not in ['activation','operational','grant'] or event.get('Channel')!='email':raise ValueError('Only qualified email events supported')
    for flag in ['ReceiptOnly','NoSendQualification']:
        if flag in event and type(event[flag]) is not bool:raise ValueError('Delivery control flags must be boolean')
    receipt_only=event.get('ReceiptOnly') is True
    if event.get('Recipient','').lower()!=c['operator_email'].lower():raise ValueError('Recipient differs from exact operator')
    if not re.fullmatch(r'EVENT:[A-Za-z0-9+/=]{1,249}',event.get('EventKey','')):raise ValueError('Bounded native event key required')
    if not isinstance(event.get('Subject'),str) or not event['Subject'].startswith('RIMS grants: ') or len(event['Subject'])>220:raise ValueError('Bounded labelled subject required')
    if not isinstance(event.get('BodyHtml'),str) or len(event['BodyHtml'])>20000:raise ValueError('Bounded prepared message required')
    for key in ['EventIdentity','OpportunityKey','EventType','Revision']:
        if not isinstance(event.get(key),str) or not event[key] or event[key]!=event[key].strip():raise ValueError('Exact event identity required')
    identity=json.loads(event['EventIdentity'])
    if not isinstance(identity,list) or event['EventKey']!='EVENT:'+base64.b64encode(event['EventIdentity'].encode()).decode():raise ValueError('Event key does not bind exact identity')
    if event.get('RetainedAttemptHistory'):
        history=json.loads(event['RetainedAttemptHistory'])
        if event['Scope']!='activation' or not isinstance(history,list) or any(not isinstance(r,dict) or r.get('attempt')!=1 or r.get('status') not in ['pending_attempt','unknown','succeeded'] for r in history):raise ValueError('Only retained activation-attempt evidence may be reconciled')
    if event['Scope'] in ['activation','operational']:
        required='system_activation' if event['Scope']=='activation' else 'source_health'
        if event['EventType']!=required or event['OpportunityKey']!='SYSTEM:G07':raise ValueError('Operational notices cannot masquerade as grants')
        if len(identity)!=4 or identity[:2]!=['SYSTEM:G07',required] or identity[-1]!='email':raise ValueError('Operational identity fields differ')
        if event['Scope']=='operational' and identity[2]!=event['Revision']:raise ValueError('Health identity revision differs')
    else:
        if event['EventType'] not in ['opportunity_changed','deadline_changed','deadline_cancelled','reminder']:raise ValueError('Unsupported grant event')
        if not isinstance(event.get('UserKey'),str) or identity!=[event['UserKey'],event['OpportunityKey'],event.get('DeadlineKey'),event['EventType'],event['Revision'],event.get('OffsetDays'),'email']:raise ValueError('Grant identity fields differ')
        if any(type(event.get(k)) is not int or event[k]<1 for k in ['SourceRowID','PreferenceRowID']):raise ValueError('Exact current source/preference rows required')
        if any(not isinstance(event.get(k),str) or not event[k] for k in ['SourceEvidenceHash','SourceVersion','PreferenceVersion']):raise ValueError('Version-bound native guards required')
    if event['Scope']=='grant' and not receipt_only and event['EventType']!='opportunity_changed':
        if type(event.get('DeadlineRowID')) is not int or event['DeadlineRowID']<1 or not isinstance(event.get('DeadlineVersion'),str) or not event['DeadlineVersion']:raise ValueError('Exact reviewed deadline/version required')
    refs={alias:{'id':'/providers/Microsoft.PowerApps/apis/'+alias,'connectionName':c[key],'source':'Embedded'} for alias,key in [('shared_sharepointonline','sharepoint_connection'),('shared_office365','mail_connection')]}
    if any(not isinstance(r['connectionName'],str) or not re.fullmatch('[A-Za-z0-9-]+',r['connectionName']) for r in refs.values()):raise ValueError('Existing native connection names required')
    def after(previous):return {previous:['Succeeded']} if previous else {}
    def compose(value,previous=''):return {'type':'Compose','inputs':value,'runAfter':after(previous)}
    def guard(condition,previous):return compose("@if("+condition+",true,json('GRANTS_LIVE_DELIVERY_GUARD_FAILED'))",previous)
    def spo(method,uri,previous='',body=None,etag=None):
        params={'dataset':c['site'],'parameters/method':method,'parameters/uri':uri,'parameters/headers':{'Accept':'application/json;odata=minimalmetadata'}}
        if body is not None:params.update({'parameters/body':body});params['parameters/headers']['Content-Type']='application/json;odata=nometadata'
        if etag:params['parameters/headers'].update({'X-HTTP-Method':'MERGE','IF-MATCH':etag})
        return {'type':'OpenApiConnection','runAfter':after(previous),'inputs':{'host':{'apiId':refs['shared_sharepointonline']['id'],'connectionName':'shared_sharepointonline','operationId':'HttpRequest'},'parameters':params,'retryPolicy':{'type':'none'}}}
    def mail(operation,params,previous=''):return {'type':'OpenApiConnection','runAfter':after(previous),'inputs':{'host':{'apiId':refs['shared_office365']['id'],'connectionName':'shared_office365','operationId':operation},'parameters':params,'retryPolicy':{'type':'none'}}}
    root="_api/web/lists(guid'"+c['ledger_id']+"')";query="@concat('"+root.replace("'","''")+"/items?$filter=Title eq ''',uriComponent(replace(outputs('Event')?['EventKey'],'''','''''')),'''&$top=2')"
    a={'Event':compose("@json(parameters('EventJSON'))"),'Caller':spo('GET','_api/web/currentuser?$select=Id,Email','Event')}
    a['Guard_caller']=guard("and(equals(toLower(body('Caller')?['Email']),'"+c['operator_email'].lower()+"'),greater(int(body('Caller')?['Id']),0))",'Caller')
    if event['Scope']=='grant':a['Guard_caller']=guard("and(equals(toLower(body('Caller')?['Email']),'"+c['operator_email'].lower()+"'),greater(int(body('Caller')?['Id']),0),equals(outputs('Event')?['UserKey'],string(body('Caller')?['Id'])))",'Caller')
    a['Read_ledger_boundary']=spo('GET',root+'?$select=ReadSecurity,WriteSecurity,EnableVersioning','Guard_caller')
    a['Guard_ledger_private']=guard("and(equals(body('Read_ledger_boundary')?['ReadSecurity'],2),equals(body('Read_ledger_boundary')?['WriteSecurity'],2),equals(body('Read_ledger_boundary')?['EnableVersioning'],true))",'Read_ledger_boundary')
    previous='Guard_ledger_private'
    if event['Scope']=='grant' and not receipt_only:
        a['Read_preference_boundary']=spo('GET',"_api/web/lists(guid'"+c['watchlist_id']+"')?$select=ReadSecurity,WriteSecurity,EnableVersioning",previous)
        a['Guard_preference_private']=guard("and(equals(body('Read_preference_boundary')?['ReadSecurity'],2),equals(body('Read_preference_boundary')?['WriteSecurity'],2),equals(body('Read_preference_boundary')?['EnableVersioning'],true))",'Read_preference_boundary');previous='Guard_preference_private'
        for label,list_id,id_field in [('Source',c['registry_id'],'SourceRowID'),('Preference',c['watchlist_id'],'PreferenceRowID')]:
            uri="@concat('_api/web/lists(guid''"+list_id+"'')/items(',string(outputs('Event')?['"+id_field+"']),')')";a['Read_'+label]=spo('GET',uri,previous);previous='Read_'+label
        a['Guard_current']=guard("and(equals(body('Read_Source')?['ReviewStatus'],'Reviewed'),equals(json(if(empty(body('Read_Source')?['ClassificationEvidenceJSON']),'{}',body('Read_Source')?['ClassificationEvidenceJSON']))?['source_evidence_hash'],body('Read_Source')?['EvidenceHash']),equals(body('Read_Source')?['OpportunityKey'],outputs('Event')?['OpportunityKey']),equals(body('Read_Source')?['EvidenceHash'],outputs('Event')?['SourceEvidenceHash']),equals(body('Read_Source')?['odata.etag'],outputs('Event')?['SourceVersion']),equals(body('Read_Preference')?['odata.etag'],outputs('Event')?['PreferenceVersion']),equals(body('Read_Preference')?['UserKey'],string(body('Caller')?['Id'])),equals(body('Read_Preference')?['Active'],true),equals(body('Read_Preference')?['SubscriptionState'],'active'),equals(body('Read_Preference')?['Channel'],'email'),contains(json(body('Read_Preference')?['EventTypesJSON']),outputs('Event')?['EventType']),or(and(equals(body('Read_Preference')?['Scope'],'opportunity'),equals(body('Read_Preference')?['TargetKey'],outputs('Event')?['OpportunityKey'])),and(equals(json(if(empty(body('Read_Source')?['ClassificationEvidenceJSON']),'{}',body('Read_Source')?['ClassificationEvidenceJSON']))?['source_evidence_hash'],body('Read_Source')?['EvidenceHash']),or(and(equals(body('Read_Preference')?['Scope'],'funder'),equals(body('Read_Preference')?['TargetKey'],body('Read_Source')?['FunderKey'])),and(equals(body('Read_Preference')?['Scope'],'category'),contains(json(if(empty(body('Read_Source')?['CategoryKeysJSON']),'[]',body('Read_Source')?['CategoryKeysJSON'])),body('Read_Preference')?['TargetKey']))))))",previous);previous='Guard_current'
    if event['Scope']=='grant' and not receipt_only and event['EventType']!='opportunity_changed':
        a['Read_Deadline']=spo('GET',"@concat('_api/web/lists(guid''"+c['calendar_id']+"'')/items(',string(outputs('Event')?['DeadlineRowID']),')')",previous)
        a['Guard_deadline']=guard("and(equals(body('Read_Deadline')?['odata.etag'],outputs('Event')?['DeadlineVersion']),equals(body('Read_Deadline')?['ReviewStatus'],'Reviewed'),equals(body('Read_Deadline')?['RevisionApplied'],true),equals(body('Read_Deadline')?['OpportunityKey'],outputs('Event')?['OpportunityKey']),equals(body('Read_Deadline')?['DeadlineKey'],outputs('Event')?['DeadlineKey']),equals(body('Read_Deadline')?['Revision'],outputs('Event')?['Revision']))",'Read_Deadline');previous='Guard_deadline'
    a['Guard_delivery_enabled']=guard("not(equals(outputs('Event')?['NoSendQualification'],true))",previous)
    a['Read_event']=spo('GET',query,'Guard_delivery_enabled');a['Guard_unique']=guard("lessOrEquals(length(body('Read_event')?['value']),1)",'Read_event')
    payload={k:"@outputs('Event')?['"+k+"']" for k in ['OpportunityKey','EventType','Revision','EventIdentity']}
    payload.update({'Title':"@outputs('Event')?['EventKey']",'UserKey':"@string(body('Caller')?['Id'])",'Channel':'email','Status':'pending_attempt','Attempt':1,'DryRun':False,'AttemptHistory':'[{"attempt":1,"status":"pending_attempt"}]'})
    send={'Claim_event':spo('POST',root+'/items',body=payload)}
    send_previous='Claim_event'
    if event['Scope']=='grant' and not receipt_only:
        import copy
        for name in ['Read_Source','Read_Preference','Guard_current']+(['Read_Deadline','Guard_deadline'] if 'Read_Deadline' in a else []):
            renamed=name+'_before_send';action=copy.deepcopy(a[name])
            action=json.loads(json.dumps(action).replace("body('Read_Source')","body('Read_Source_before_send')").replace("body('Read_Preference')","body('Read_Preference_before_send')").replace("body('Read_Deadline')","body('Read_Deadline_before_send')"))
            action['runAfter']=after(send_previous);send[renamed]=action;send_previous=renamed
    send['Send_once']=mail('SendEmailV2',{'emailMessage/To':c['operator_email'],'emailMessage/Subject':"@outputs('Event')?['Subject']",'emailMessage/Body':"@outputs('Event')?['BodyHtml']",'emailMessage/Importance':'Normal'},send_previous)
    a['If_unclaimed']={'type':'If','runAfter':after('Guard_unique'),'expression':{'and':[{'equals':["@length(body('Read_event')?['value'])",0]},{'not':{'equals':["@outputs('Event')?['ReceiptOnly']",True]}}]},'actions':send,'else':{'actions':{}}}
    a['Read_claim']=spo('GET',query);a['Read_claim']['runAfter']={'If_unclaimed':['Succeeded','Failed','TimedOut']}
    a['Guard_claim']=guard("and(equals(length(body('Read_claim')?['value']),1),equals(first(body('Read_claim')?['value'])?['EventIdentity'],outputs('Event')?['EventIdentity']),equals(first(body('Read_claim')?['value'])?['UserKey'],string(body('Caller')?['Id'])),equals(first(body('Read_claim')?['value'])?['DryRun'],false),equals(first(body('Read_claim')?['value'])?['Attempt'],1))",'Read_claim')
    a['Read_sent_folder']=mail('HttpRequest',{'Uri':"https://graph.microsoft.com/v1.0/me/mailFolders/sentitems?$select=id",'Method':'GET','ContentType':'application/json'},'Guard_claim')
    a['Read_outbox_folder']=mail('HttpRequest',{'Uri':"https://graph.microsoft.com/v1.0/me/mailFolders/outbox?$select=id",'Method':'GET','ContentType':'application/json'},'Read_sent_folder')
    mail_query="@concat('https://graph.microsoft.com/v1.0/me/messages?$select=id,subject,parentFolderId,toRecipients,internetMessageId,isDraft&$top=10&$filter=subject eq ''',uriComponent(replace(outputs('Event')?['Subject'],'''','''''')),'''')"
    a['Read_receipt']=mail('HttpRequest',{'Uri':mail_query,'Method':'GET','ContentType':'application/json'},'Read_outbox_folder')
    a['Guard_receipt_complete']=guard("and(empty(body('Read_receipt')?['@odata.nextLink']),lessOrEquals(length(body('Read_receipt')?['value']),10))",'Read_receipt')
    def receipt_query(sent):
        folder_test="equals(item()?['parentFolderId'],body('Read_sent_folder')?['id'])"
        if not sent:folder_test="and(not("+folder_test+"),not(equals(item()?['parentFolderId'],body('Read_outbox_folder')?['id'])),equals(item()?['isDraft'],false))"
        return {'type':'Query','runAfter':after('Guard_receipt_complete'),'inputs':{'from':"@body('Read_receipt')?['value']",'where':"@and(equals(item()?['subject'],outputs('Event')?['Subject']),"+folder_test+")"}}
    a['Exact_receipt']=receipt_query(False);a['Sent_receipt']=receipt_query(True)
    a['Guard_receipt_unique']=guard("and(lessOrEquals(length(body('Exact_receipt')),1),lessOrEquals(length(body('Sent_receipt')),1))",'Exact_receipt');a['Guard_receipt_unique']['runAfter']['Sent_receipt']=['Succeeded']
    status="if(equals(length(body('Exact_receipt')),1),'succeeded',if(equals(length(body('Sent_receipt')),1),'submitted','unknown'))"
    provider="if(equals(length(body('Exact_receipt')),1),coalesce(first(body('Exact_receipt'))?['internetMessageId'],first(body('Exact_receipt'))?['id']),if(equals(length(body('Sent_receipt')),1),coalesce(first(body('Sent_receipt'))?['internetMessageId'],first(body('Sent_receipt'))?['id']),null))"
    update={'Status':'@'+status,'ProviderID':'@'+provider,'AttemptHistory':"@string(union(createArray(setProperty(setProperty(json('{}'),'attempt',1),'status','pending_attempt')),json(if(empty(outputs('Event')?['RetainedAttemptHistory']),'[]',outputs('Event')?['RetainedAttemptHistory'])),json(coalesce(first(body('Read_claim')?['value'])?['AttemptHistory'],'[]')),createArray(setProperty(setProperty(setProperty(json('{}'),'attempt',1),'status',"+status+"),'observed_utc',utcNow()))))"}
    uri="@concat('"+root.replace("'","''")+"/items(',string(first(body('Read_claim')?['value'])?['Id']),')')"
    a['Record_outcome']=spo('POST',uri,'Guard_receipt_unique',update,"@first(body('Read_claim')?['value'])?['odata.etag']")
    a['Result']=compose({'DryRun':False,'Recipient':c['operator_email'],'EventKey':"@outputs('Event')?['EventKey']",'ReceiptMatched':"@equals(length(body('Exact_receipt')),1)",'AutomaticRetry':False},'Record_outcome')
    definition={'$schema':'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#','contentVersion':'1.0.0.0','parameters':{'$authentication':{'type':'SecureObject','defaultValue':{}},'$connections':{'type':'Object','defaultValue':{}},'EventJSON':{'type':'String','defaultValue':json.dumps(event,separators=(',',':'))}},'triggers':{'manual':{'type':'Request','kind':'Button','inputs':{'schema':{'type':'object','additionalProperties':False,'properties':{}}},'runtimeConfiguration':{'concurrency':{'runs':1}}}},'actions':a}
    return {'properties':{'displayName':'CHHHS RIMS | Grants | Live email worker','state':'Stopped','flowFailureAlertSubscribed':False,'definition':definition,'connectionReferences':refs}}
