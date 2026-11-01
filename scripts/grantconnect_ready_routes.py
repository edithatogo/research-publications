"""Extend the existing ready-file consumer with fixed calendar and history destinations."""
from scripts.grantconnect_ready_flow import build


def routes(site,library,folder,register,calendar,lists):
    flow=build(site,library,folder,register)
    actions=flow['actions']
    read=actions.pop('Read')
    actions['Batch']['runAfter']={}
    def after(name):return {name:['Succeeded']} if name else {}
    def operation(name,params,prev=''):
        return {'type':'OpenApiConnection','runAfter':after(prev),'inputs':{
            'host':read['inputs']['host']|{'operationId':name},
            'parameters':{'dataset':site,**params},'retryPolicy':{'type':'none'}}}
    def compose(value,prev=''):return {'type':'Compose','inputs':value,'runAfter':after(prev)}
    def guard(expr,prev=''):return compose("@if("+expr+",true,json('READY_CONFLICT'))",prev)
    def select(array,expr,prev=''):return {'type':'Select','inputs':{'from':array,'select':expr},'runAfter':after(prev)}
    def loop(array,steps,prev=''):return {'type':'Foreach','foreach':array,'actions':steps,'runAfter':after(prev),'runtimeConfiguration':{'concurrency':{'repetitions':1}}}
    def condition(expr,yes,no=None,prev=''):return {'type':'If','expression':expr,'actions':yes,'else':{'actions':no or {}},'runAfter':after(prev)}
    raw="@json(base64ToString(body('Read')?['$content']))"
    history={'History_manifest':compose(raw)}
    shard={}
    shard['Target_list']=compose("@outputs('History_targets')[items('History_files')['entity']]")
    shard['Guard_filename']=guard("and(startsWith(items('History_files')['file'],'gc-history-data-'),endsWith(items('History_files')['file'],'.json'),not(contains(items('History_files')['file'],'/')),not(contains(items('History_files')['file'],'..')))",'Target_list')
    shard['Read_shard']=operation('GetFileContentByPath',{'path':"@concat('"+folder+"/',items('History_files')['file'])",'inferContentType':False},'Guard_filename')
    cols=['Title','HistoryKey','GAID','GOID','EvidenceHash','SourceEvidence']
    shard['History_rows']={'type':'ParseJson','runAfter':after('Read_shard'),'inputs':{
        'content':"@json(base64ToString(body('Read_shard')?['$content']))",
        'schema':{'type':'array','items':{'type':'object','additionalProperties':False,'required':cols,
            'properties':{k:{'type':'string'} for k in cols}}}}}
    shard['Guard_shard_count']=guard("equals(length(body('History_rows')),items('History_files')['count'])",'History_rows')
    group={}
    group['Key_filter']=select("@items('History_groups')","@concat('HistoryKey eq ''',replace(item()['HistoryKey'],'''',''''''),'''')")
    group['Existing_history']=operation('GetItems',{'table':"@outputs('Target_list')",'$filter':"@join(body('Key_filter'),' or ')",'$top':100},'Key_filter')
    group['Existing_pairs']=select("@body('Existing_history')['value']","@concat(item()['HistoryKey'],'|',item()['EvidenceHash'])",'Existing_history')
    group['Missing_history']={'type':'Query','runAfter':after('Existing_pairs'),'inputs':{'from':"@items('History_groups')",'where':"@not(contains(body('Existing_pairs'),concat(item()['HistoryKey'],'|',item()['EvidenceHash'])))"}}
    # Build every method, URL and header in the flow. The ready file supplies typed list fields only.
    nl="decodeUriComponent('%0D%0A')"
    wire="@concat('--changeset_gc',N,'Content-Type: application/http',N,'Content-Transfer-Encoding: binary',N,N,'POST "+site+"/_api/web/lists(guid''',outputs('Target_list'),''')/items HTTP/1.1',N,'Content-Type: application/json;odata=nometadata',N,N,string(item()),N)".replace(',N',','+nl)
    wire=wire.replace(",N",","+nl)
    submit={'Parts':select("@body('Missing_history')",wire)}
    payload="@concat('--batch_gc',N,'Content-Type: multipart/mixed; boundary=changeset_gc',N,N,join(body('Parts'),''),'--changeset_gc--',N,'--batch_gc--',N)".replace(',N',','+nl)
    submit['Save_history_group']=operation('HttpRequest',{'parameters/method':'POST','parameters/uri':'_api/$batch','parameters/headers':{'Content-Type':'multipart/mixed; boundary=batch_gc'},'parameters/body':payload},'Parts')
    # SharePoint batch HTTP 200 can contain failed subrequests. Read the unique keys back.
    submit['Read_saved_group']=operation('GetItems',{'table':"@outputs('Target_list')",'$filter':"@join(body('Key_filter'),' or ')",'$top':100},'Save_history_group')
    submit['Saved_pairs']=select("@body('Read_saved_group')['value']","@concat(item()['HistoryKey'],'|',item()['EvidenceHash'])",'Read_saved_group')
    submit['Expected_pairs']=select("@items('History_groups')","@concat(item()['HistoryKey'],'|',item()['EvidenceHash'])",'Saved_pairs')
    submit['Guard_saved_group']=guard("equals(length(intersection(body('Expected_pairs'),body('Saved_pairs'))),length(items('History_groups')))",'Expected_pairs')
    group['Write_missing']=condition("@greater(length(body('Missing_history')),0)",submit,prev='Missing_history')
    shard['History_groups']=loop("@chunk(body('History_rows'),50)",group,'Guard_shard_count')
    history['History_targets']=compose(lists,'History_manifest')
    history['History_files']=loop("@outputs('History_manifest')['files']",shard,'History_targets')
    flow['actions']={'Read':read,'Route':{'type':'Switch','expression':raw+"['kind']",'runAfter':after('Read'),
        'cases':{'Live':{'case':'grantconnect_xml_register_v1','actions':actions},'History':{'case':'grantconnect_history_v1','actions':history}},
        'default':{'actions':{'Unknown_kind':compose("@json('UNKNOWN_READY_KIND')")}}}}
    dates={'Closing_manifest':compose(raw)}
    record="items('Confirmed_dates')"
    key=record+"['OpportunityKey']"
    deadline_key=record+"['DeadlineKey']"
    def lookup(name,field,value,prev):
        return operation('GetItems',{'table':name,'$filter':"@concat('"+field+" eq ''',replace("+value+",'''',''''''),'''')",'$top':2},prev)
    def write(name,lookup_name,body,update):
        base="_api/web/lists(guid'"+name+"')/items"
        headers={'Content-Type':'application/json;odata=nometadata'}
        uri=base
        if update:
            row="first(body('"+lookup_name+"')['value'])"
            uri="@concat('"+base.replace("'","''")+"(',string("+row+"['ID']),')')"
            headers.update({'X-HTTP-Method':'MERGE','IF-MATCH':"@"+row+"['@odata.etag']"})
        return operation('HttpRequest',{'parameters/method':'POST','parameters/uri':uri,'parameters/headers':headers,'parameters/body':body})
    steps={'Closing_identity':guard("and(startsWith("+key+",'GRANT'),startsWith("+deadline_key+",'GC-CLOSE:'),startsWith("+record+"['SourceURL'],'https://www.grants.gov.au/'))")}
    steps['Find_opportunity']=lookup(register,'OpportunityKey',key,'Closing_identity')
    steps['Find_deadline']=lookup(calendar,'DeadlineKey',deadline_key,'Find_opportunity')
    rr="first(body('Find_opportunity')['value'])";cr="first(body('Find_deadline')['value'])"
    steps['Guard_closing_owner']=guard("and(equals(length(body('Find_opportunity')['value']),1),equals("+rr+"['Source'],'GrantConnectRSS'),equals("+rr+"['SourceID'],"+record+"['RegistrySourceID']),lessOrEquals(length(body('Find_deadline')['value']),1))",'Find_deadline')
    data={k:'@'+record+"['"+k+"']" for k in ['DeadlineRaw','DeadlineUTCInstant','DeadlineBrisbaneDate']}
    data.update(Deadline='@'+record+"['DeadlineUTCInstant']",DeadlineTimezone='Australia/Sydney',DeadlinePrecision='day')
    merge=write(register,'Find_opportunity',data,True);merge['runAfter']=after('Guard_registry_edit')
    steps['Update_closing']=condition("@not(equals("+rr+"?['DeadlineUTCInstant'],"+record+"['DeadlineUTCInstant']))",
        {'Guard_registry_edit':guard("and(equals("+rr+"?['ReviewStatus']?['Value'],'Needs Review'),or(empty("+rr+"?['DeadlineRaw']),not(empty(body('Find_deadline')['value']))))"),'Merge_closing':merge},prev='Guard_closing_owner')
    data={k:'@'+record+"['"+k+"']" for k in ['Title','OpportunityKey','DeadlineKey','Revision']}
    data.update(SourceURL={'Url':'@'+record+"['SourceURL']",'Description':'Official closing date'},CalculatedDate='@'+record+"['DeadlineUTCInstant']",
                Calendar_x0020_day='@'+record+"['DeadlineSourceDate']",DeadlinePrecision='day',ReviewStatus='Source confirmed',RevisionApplied=True,Cancelled=False)
    patch=write(calendar,'Find_deadline',data,True);patch['runAfter']=after('Guard_owned_date')
    steps['Save_date']=condition("@empty(body('Find_deadline')['value'])",{'Create_date':write(calendar,'Find_deadline',data,False)},
        {'Date_changed':condition("@not(equals("+cr+"['Revision'],"+record+"['Revision']))",
        {'Guard_owned_date':guard("and(equals("+cr+"['ReviewStatus'],'Source confirmed'),equals("+cr+"['OpportunityKey'],"+key+"))"),'Merge_date':patch})},'Update_closing')
    dates['Confirmed_dates']=loop("@outputs('Closing_manifest')['dates']",steps,'Closing_manifest')
    flow['actions']['Route']['cases']['Calendar']={'case':'grantconnect_closings_v1','actions':dates}
    return flow
