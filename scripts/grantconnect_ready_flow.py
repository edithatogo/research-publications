"""Build a serial SharePoint ready-file consumer for GrantConnect register observations."""
from scripts.grantconnect_rss import definition as manual_envelope

CONNECTOR = 'shared_sharepointonline'


def build(site, library, folder, register):
    def inputs(operation, parameters):
        return {'host':{'apiId':'/providers/Microsoft.PowerApps/apis/'+CONNECTOR,
                        'connectionName':CONNECTOR,'operationId':operation},
                'parameters':{'dataset':site,**parameters}}

    def action(operation, parameters, after=None):
        return {'type':'OpenApiConnection','runAfter':after or {},
                'inputs':{**inputs(operation, parameters),'retryPolicy':{'type':'none'}}}

    flow = manual_envelope()
    flow['triggers'] = {'Ready_file':{'type':'OpenApiConnection','recurrence':{'frequency':'Minute','interval':5},
        'splitOn':"@triggerOutputs()?['body/value']",
        'conditions':[{'expression':"@and(startsWith(triggerBody()?['{FilenameWithExtension}'],'grantconnect-ready-'),endsWith(triggerBody()?['{FilenameWithExtension}'],'.json'))"}],
        'runtimeConfiguration':{'concurrency':{'runs':1}},
        'inputs':inputs('GetOnNewFileItems',{'table':library,'folderPath':folder})}}
    schema={'type':'object','required':['kind','count','rows'],'properties':{
        'kind':{'type':'string','enum':['grantconnect_xml_register_v1']},'count':{'type':'integer','minimum':1},
        'rows':{'type':'array','minItems':1,'items':{'type':'object','required':['OpportunityKey','Title','SourceID','URL','EvidenceHash','Source','ReviewStatus'],
        'properties':{'OpportunityKey':{'type':'string','minLength':30,'maxLength':31},
        'Source':{'enum':['GrantConnectRSS']},'ReviewStatus':{'enum':['Needs Review']},
        'EvidenceHash':{'type':'string','minLength':64,'maxLength':64},'Title':{'type':'string','minLength':1},
        'SourceID':{'type':'string','minLength':1},'URL':{'type':'string','minLength':1}}}}}}
    ref="items('Each_record')"
    fields={k:'@'+ref+"?['"+k+"']" for k in ('Title','OpportunityKey','SourceID','Description','EvidenceHash','RetrievedUTC','RetrievedTimestampStatus','DeadlinePrecision','DeadlineTemporalStatus')}
    fields.update(Source='GrantConnectRSS',ReviewStatus='Needs Review',Status='Unknown',URL={'Url':'@'+ref+"?['URL']",'Description':'GrantConnect'})
    flow['actions']={'Read':action('GetFileContent',{'id':"@triggerBody()?['{Identifier}']",'inferContentType':False}),
        'Batch':{'type':'ParseJson','runAfter':{'Read':['Succeeded']},'inputs':{'content':"@json(base64ToString(body('Read')?['$content']))",'schema':schema}},
        'Guard_count':{'type':'Compose','runAfter':{'Batch':['Succeeded']},'inputs':"@if(equals(body('Batch')['count'],length(body('Batch')['rows'])),true,json('INVALID_COUNT'))"},
        'Each_record':{'type':'Foreach','foreach':"@body('Batch')['rows']",'runAfter':{'Guard_count':['Succeeded']},
        'runtimeConfiguration':{'concurrency':{'repetitions':1}},'actions':{
        'Guard_source':{'type':'Compose','runAfter':{},'inputs':"@if(and(startsWith(items('Each_record')['URL'],'https://www.grants.gov.au/'),or(startsWith(items('Each_record')['OpportunityKey'],'GRANT:'),startsWith(items('Each_record')['OpportunityKey'],'GRANTX:'))),true,json('INVALID_SOURCE'))"},
        'Find':action('GetItems',{'table':register,'$filter':"@concat('OpportunityKey eq ''',replace(items('Each_record')['OpportunityKey'],'''',''''''),'''')",'$top':2},{'Guard_source':['Succeeded']}),
        'Create_if_missing':{'type':'If','expression':"@empty(body('Find')['value'])",'runAfter':{'Find':['Succeeded']},
        'actions':{'Create':action('HttpRequest',{'parameters/method':'POST','parameters/uri':f"_api/web/lists(guid'{register}')/items",
            'parameters/headers':{'Content-Type':'application/json;odata=nometadata'},'parameters/body':fields})},
        'else':{'actions':{'Check_existing':{'type':'Compose','runAfter':{},'inputs':"@if(and(equals(length(body('Find')['value']),1),equals(first(body('Find')['value'])?['EvidenceHash'],items('Each_record')['EvidenceHash'])),true,json('EXISTING_RECORD_CONFLICT'))"}}}}}}}
    return flow
