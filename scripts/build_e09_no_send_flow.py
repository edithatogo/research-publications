# SPDX-License-Identifier: Apache-2.0
"""Prepare an isolated manual, SharePoint-only E09 mapping qualification flow.

No sender, recurrence, new connection or authority resolution is included.
Inputs are operator-qualified envelopes; this is not an untrusted-user service.
"""
import json
from pathlib import Path
from scripts.e09_post_content import TIER_WORDING

FOOTER = ('The Publication Registry remains the record; this thread is an additive '
          'surface for evidence-backed contributions resolved by curators. Do not post '
          'clinical, personal or sensitive research data.')


def _definition(site_url, list_id):
    from urllib.parse import urlsplit
    import re
    if not isinstance(site_url, str) or not isinstance(list_id, str):
        raise ValueError('Exact text target identities required')
    parsed = urlsplit(site_url)
    if (parsed.scheme != 'https' or not parsed.hostname
            or not parsed.hostname.endswith('.sharepoint.com')
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.netloc != parsed.hostname or site_url != site_url.strip()
            or any(ord(c) < 33 for c in site_url) or '\\' in site_url
            or '..' in parsed.path.split('/')
            or re.search(r'%(?:25|2f|5c|2e)', parsed.path, re.I)):
        raise ValueError('Qualified SharePoint site required')
    if not re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}', list_id):
        raise ValueError('Exact owned List ID required')
    root = f"_api/web/lists(guid'{list_id}')/items"
    def compose(value, after=None):
        return {'type': 'Compose', 'inputs': value, 'runAfter': {after: ['Succeeded']} if after else {}}
    def guard(expression, after):
        return {'type': 'ParseJson', 'inputs': {'content': {'ok': expression},
                'schema': {'type': 'object', 'required': ['ok'], 'properties': {'ok': {'enum': [True]}}}},
                'runAfter': {after: ['Succeeded']}}
    def http(method, uri, after=None, body=None, extra=None):
        parameters = {'dataset': site_url, 'parameters/method': method, 'parameters/uri': uri,
                      'parameters/headers': {'Accept': 'application/json;odata=minimalmetadata',
                      'Content-Type': 'application/json;odata=nometadata', **(extra or {})}}
        if body is not None: parameters['parameters/body'] = body
        return {'type': 'OpenApiConnection', 'inputs': {'host': {'apiId': '/providers/Microsoft.PowerApps/apis/shared_sharepointonline',
                'connectionName': 'shared_sharepointonline', 'operationId': 'HttpRequest'},
                'parameters': parameters, 'retryPolicy': {'type': 'none'}},
                'runAfter': {after: ['Succeeded']} if after else {}}
    def parse(content, schema, after=None):
        return {'type': 'ParseJson', 'inputs': {'content': content, 'schema': schema},
                'runAfter': {after: ['Succeeded']} if after else {}}
    def string(nullable=False): return {'type': ['string', 'null'] if nullable else 'string'}
    props = dict(schema={'type':'integer','enum':[1]}, kind={'enum':['thread']}, logical_id=string(),
                 key={'type':'string'}, storage_revision={'type':'integer','minimum':1},
                 payload_json=string(), payload_sha256={'type':'string'},
                 qualification_only={'enum':[True]})
    envelope_schema = {'type':'object','additionalProperties':False,'required':list(props),'properties':props}
    selection_props = dict(publication_key=string(), canonical_key=string(), tier={'enum':['confirmed','possible']},
                           review_status={'enum':['Included','Needs Review']}, discovered_on=string(),
                           suggested_trigger={'enum':['first_discovery','catch_up']},Title=string(True),PublicationMonth=string(True))
    root_path = Path(__file__).resolve().parents[1]
    def native_schema(value):
        if isinstance(value, dict):
            result = {k: native_schema(v) for k, v in value.items() if k not in {'pattern', 'patternProperties'}}
            if 'const' in result: result['enum'] = [result.pop('const')]
            return result
        if isinstance(value, list): return [native_schema(v) for v in value]
        return value
    receipt_schema = native_schema(json.loads((root_path/'contracts/e09-feed-storage.schema.json').read_text())['$defs']['delivery_receipt'])
    # Narrow a local copy only; shared receipt contracts remain unchanged.
    receipt_schema['properties'].update(
        intended_outcome={'enum':['no_send']},
        outcome={'enum':['recorded_only','failed_uncertain']},
        post_reference={'type':'null'}, delivery_authority_reference={'type':'null'})
    post_schema = native_schema(json.loads((root_path/'contracts/e09-feed-preparation.schema.json').read_text())['$defs']['no_send_post_body'])
    thread_props = dict(thread_id=string(),publication_key=string(),canonical_key=string(),source_aliases={'type':'array','minItems':1,'items':string()},
                        render_input={'type':'object','additionalProperties':False,'required':['publication_key','canonical_key','tier','review_status','discovered_on','suggested_trigger'],'properties':selection_props},
                        rendered_post=post_schema,delivery_receipt=receipt_schema,revision={'type':'integer','minimum':1},
                        dispatch_state={'enum':['no_send','reconciliation_required']},human_notes=string(True),input_fingerprint=string(),native_input_reference=string())
    thread_schema = {'type':'object','additionalProperties':False,'required':list(thread_props),'properties':thread_props}
    record = "body('Parse_thread')"
    ri = record+"?['render_input']"
    def quote(text): return "'"+text.replace("'","''")+"'"
    def escape(expr): return f"replace(replace(replace(string({expr}),'&','&amp;'),'<','&lt;'),'>','&gt;')"
    opening = f"if(equals({ri}?['tier'],'confirmed'),{quote(TIER_WORDING['confirmed'])},{quote(TIER_WORDING['possible'])})"
    heading = f"coalesce({ri}?['Title'],{ri}?['canonical_key'])"
    lines = [opening,heading,
             f"concat('First observed in the Publication Registry: ',{ri}?['discovered_on'],' (UTC register processing first-seen)')",
             f"concat('Source key: ',{ri}?['publication_key'])",f"concat('Canonical key: ',{ri}?['canonical_key'])"]
    month = f"concat('Publication month (verified): ',{ri}?['PublicationMonth'])"
    suffix = f"concat(if(equals({ri}?['suggested_trigger'],'catch_up'),'Selected in catch-up backfill','First discovery'),'; publication tier: ',{ri}?['review_status'])"
    html = [part for line in lines for part in [quote('<p>'),escape(line),quote('</p>')]]
    html += [f"if(empty({ri}?['PublicationMonth']),'',concat('<p>',{escape(month)},'</p>'))",quote('<p>'),escape(suffix),quote('</p><p><em>'),escape(quote(FOOTER)),quote('</em></p>')]
    plain = []
    for line in lines: plain.extend([line,"decodeUriComponent('%0A')"])
    plain += [f"if(empty({ri}?['PublicationMonth']),'',concat({month},decodeUriComponent('%0A')))",suffix,"decodeUriComponent('%0A')",quote(FOOTER)]
    actions = {'Parse_envelope':parse("@json(triggerBody()?['EnvelopeJSON'])",envelope_schema),
               'Parse_thread':parse("@json(body('Parse_envelope')?['payload_json'])",thread_schema,'Parse_envelope'),
               'Native_rendered_post':compose({'thread_id':f"@concat('thread:',{ri}?['publication_key'])",'subject':'@'+heading,
                       'body':{'contentType':'html','content':'@concat('+','.join(html)+')'},'plain_text':'@concat('+','.join(plain)+')'},'Parse_thread')}
    receipt = record+"?['delivery_receipt']"
    def hex_only(expr):
        for char in '0123456789abcdef':
            expr = f"replace({expr},'{char}','')"
        return f"equals({expr},'')"
    checks = ["equals(triggerBody()?['NoSendOnly'],true)","equals(body('Parse_envelope')?['qualification_only'],true)",
              "equals(length(body('Parse_envelope')?['key']),68)",
              "startsWith(body('Parse_envelope')?['key'],'e09:')",
              hex_only("substring(body('Parse_envelope')?['key'],4)"),
              "equals(length(body('Parse_envelope')?['payload_sha256']),64)",
              hex_only("body('Parse_envelope')?['payload_sha256']"),
              f"equals({record}?['rendered_post'],outputs('Native_rendered_post'))",
              f"equals({record}?['thread_id'],outputs('Native_rendered_post')?['thread_id'])",
              f"equals({record}?['thread_id'],body('Parse_envelope')?['logical_id'])",
              f"equals({record}?['revision'],body('Parse_envelope')?['storage_revision'])",
              f"equals({record}?['canonical_key'],{ri}?['canonical_key'])",
              f"startsWith({record}?['canonical_key'],'PUB:')",
              f"greater(length({record}?['canonical_key']),4)",
              hex_only(f"substring({record}?['canonical_key'],4)"),
              f"equals({record}?['publication_key'],{ri}?['publication_key'])",
              f"equals({ri}?['review_status'],if(equals({ri}?['tier'],'confirmed'),'Included','Needs Review'))",
              f"equals({receipt}?['intended_outcome'],'no_send')",f"equals({receipt}?['post_reference'],null)",
              f"equals({receipt}?['delivery_authority_reference'],null)",
              f"equals({receipt}?['thread_id'],{record}?['thread_id'])",
              f"equals({receipt}?['receipt_id'],{record}?['thread_id'])",
              f"equals({receipt}?['publication_key'],{record}?['publication_key'])",
              f"equals({receipt}?['revision'],{record}?['revision'])",
              f"equals({receipt}?['outcome'],if(equals({record}?['dispatch_state'],'reconciliation_required'),'failed_uncertain','recorded_only'))",
              f"equals({receipt}?['reconciliation_required'],equals({record}?['dispatch_state'],'reconciliation_required'))"]
    actions['Require_no_send_identity']=guard('@and('+','.join(checks)+')','Native_rendered_post')
    actions['Read_thread']=http('GET',root+"?$filter=Title eq '@{body('Parse_envelope')?['key']}'&$top=2",'Require_no_send_identity')
    values="body('Read_thread')?['value']"; prior="first("+values+")"; saved="json("+prior+"?['PayloadJSON'])"
    actions['Require_unique_match']=guard(f'@lessOrEquals(length({values}),1)','Read_thread')
    row={'Title':"@body('Parse_envelope')?['key']",'RecordKind':'thread','RecordIdentity':"@body('Parse_envelope')?['logical_id']",
         'RecordRevision':"@body('Parse_envelope')?['storage_revision']",'PayloadJSON':"@body('Parse_envelope')?['payload_json']",
         'PayloadSHA256':"@body('Parse_envelope')?['payload_sha256']",'QualificationOnly':True}
    actions['Native_row']=compose(row,'Require_unique_match')
    update_checks=[f"equals({prior}?['RecordRevision'],triggerBody()?['ExpectedRevision'])",
                   f"equals(add(int({prior}?['RecordRevision']),1),body('Parse_envelope')?['storage_revision'])",
                   f"equals(coalesce({prior}?['odata.etag'],{prior}?['@odata.etag']),triggerBody()?['ExpectedETag'])",
                   f"equals({prior}?['PayloadSHA256'],triggerBody()?['ExpectedPayloadSHA256'])",
                   f"greaterOrEquals(ticks({record}?['delivery_receipt']?['recorded_at']),ticks({saved}?['delivery_receipt']?['recorded_at']))",
                   f"equals({prior}?['RecordKind'],'thread')",f"equals({prior}?['QualificationOnly'],true)"]
    for field in ['thread_id','publication_key','canonical_key','human_notes','source_aliases']:
        update_checks.append(f"equals({saved}?['{field}'],{record}?['{field}'])")
    update_guard=guard('@and('+','.join(update_checks)+')','Changed_content')
    update=http('POST',root+f"(@{{{prior}?['Id']}})",'Require_current_revision',"@string(outputs('Native_row'))",
                {'X-HTTP-Method':'MERGE','IF-MATCH':f"@coalesce({prior}?['odata.etag'],{prior}?['@odata.etag'])"})
    same = f"@and(equals({prior}?['PayloadJSON'],body('Parse_envelope')?['payload_json']),equals({prior}?['PayloadSHA256'],body('Parse_envelope')?['payload_sha256']),equals({prior}?['RecordRevision'],body('Parse_envelope')?['storage_revision']))"
    changed={'type':'If','expression':same,'runAfter':{},'actions':{'Unchanged_replay':compose({'no_send':True,'writes':0})},
             'else':{'actions':{'Changed_content':compose(True),'Require_current_revision':update_guard,'Update_mapping':update}}}
    uncertain={'type':'If','expression':f"@equals({saved}?['dispatch_state'],'reconciliation_required')",'runAfter':{},
               'actions':{'Blocked_uncertain_outcome':compose({'no_send':True,'reconciliation_required':True,'writes':0,'resend_allowed':False})},
               'else':{'actions':{'Reconcile_existing_mapping':changed}}}
    create_guard=guard("@and(equals(body('Parse_envelope')?['storage_revision'],1),equals(triggerBody()?['ExpectedRevision'],0),equals(body('Parse_thread')?['dispatch_state'],'no_send'))",'New_mapping')
    actions['Persist_or_preserve_mapping']={'type':'If','expression':f'@equals(length({values}),0)','runAfter':{'Native_row':['Succeeded']},
        'actions':{'New_mapping':compose(True),'Require_initial_revision':create_guard,'Create_mapping':http('POST',root,'Require_initial_revision',"@string(outputs('Native_row'))")},
        'else':{'actions':{'Check_uncertain_outcome':uncertain}}}
    actions['Saved_mapping']=http('GET',root+"?$filter=Title eq '@{body('Parse_envelope')?['key']}'&$top=2",'Persist_or_preserve_mapping')
    actions['No_send_result']=compose({'no_send':True,'message_created':False,'provider_reference':None,'saved_rows':"@body('Saved_mapping')?['value']"},'Saved_mapping')
    return {'$schema':'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#',
            'contentVersion':'1.0.0.0','parameters':{'$authentication':{'type':'SecureObject','defaultValue':{}},'$connections':{'type':'Object','defaultValue':{}}},
            'triggers':{'manual':{'type':'Request','kind':'Button','inputs':{'schema':{'type':'object','additionalProperties':False,'required':['EnvelopeJSON','NoSendOnly','ExpectedETag','ExpectedRevision','ExpectedPayloadSHA256'],
                         'properties':{'EnvelopeJSON':string(),'NoSendOnly':{'type':'boolean','enum':[True]},'ExpectedETag':string(),'ExpectedRevision':{'type':'integer'},'ExpectedPayloadSHA256':string()}}},'runtimeConfiguration':{'concurrency':{'runs':1}}}},
            'actions':actions,'outputs':{}}


def validate_no_send_definition(graph, site_url, list_id):
    """Admit only this closed source template, never a dispatch-capable variant.

    This checks a predeployment artifact, not a saved native definition or its
    engine behavior. Service annotations and future template variants require
    separate explicit qualification; they are not normalized away here.
    """
    expected = _definition(site_url, list_id)
    root = f"_api/web/lists(guid'{list_id}')/items"
    allowed_types = {'Compose', 'ParseJson', 'If', 'OpenApiConnection'}
    def actions(nodes):
        if not isinstance(nodes, dict):
            raise ValueError('Exact no-send action mapping required')
        for action in nodes.values():
            if (not isinstance(action, dict) or not isinstance(action.get('type'), str)
                    or action['type'] not in allowed_types):
                raise ValueError('Send, dispatch, HTTP, child workflow and unknown action types forbidden')
            if action['type'] == 'OpenApiConnection':
                inputs = action.get('inputs', {})
                if not isinstance(inputs, dict):
                    raise ValueError('Typed no-send connector inputs required')
                host = inputs.get('host', {})
                params = inputs.get('parameters', {})
                if not isinstance(params, dict):
                    raise ValueError('Typed no-send target parameters required')
                uri = params.get('parameters/uri')
                if (host != {'apiId':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline',
                             'connectionName':'shared_sharepointonline','operationId':'HttpRequest'}
                        or inputs.get('retryPolicy') != {'type':'none'}
                        or params.get('dataset') != site_url
                        or not isinstance(params.get('parameters/method'), str)
                        or params['parameters/method'] not in {'GET','POST'}
                        or not isinstance(uri, str) or not uri.startswith(root)
                        or uri[len(root):len(root)+1] not in {'','?','('}):
                    raise ValueError('Only exact owned-list no-retry mapping requests allowed')
            if action['type'] == 'If':
                actions(action.get('actions'))
                branch = action.get('else')
                if not isinstance(branch, dict):
                    raise ValueError('Complete no-send branch required')
                actions(branch.get('actions'))
    if not isinstance(graph, dict):
        raise ValueError('Exact no-send definition required')
    actions(graph.get('actions'))
    try:
        trigger = graph['triggers']['manual']
        schema = trigger['inputs']['schema']
        receipt = graph['actions']['Parse_thread']['inputs']['schema']['properties']['delivery_receipt']['properties']
        result = graph['actions']['No_send_result']['inputs']
        if (set(graph['triggers']) != {'manual'} or trigger['type'] != 'Request' or trigger['kind'] != 'Button'
                or schema.get('additionalProperties') is not False
                or schema['properties']['NoSendOnly'] != {'type':'boolean','enum':[True]}
                or 'NoSendOnly' not in schema['required']
                or set(graph['parameters']) != {'$authentication','$connections'}
                or any(p.get('defaultValue') != {} for p in graph['parameters'].values())
                or receipt['intended_outcome'] != {'enum':['no_send']}
                or receipt['outcome'] != {'enum':['recorded_only','failed_uncertain']}
                or receipt['post_reference'] != {'type':'null'}
                or receipt['delivery_authority_reference'] != {'type':'null'}
                or result.get('no_send') is not True or result.get('message_created') is not False
                or result.get('provider_reference') is not None or graph.get('outputs') != {}):
            raise ValueError('Explicit no-send trigger, receipt and result boundaries required')
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('Complete no-send artifact boundaries required') from error
    # The independent action policy above also rejects a future accidental
    # sender in the factory. Exact template comparison then protects every
    # guard, trigger, branch dependency, authority default and output shape.
    if (json.dumps(graph, sort_keys=True, separators=(',', ':'), allow_nan=False)
            != json.dumps(expected, sort_keys=True, separators=(',', ':'), allow_nan=False)):
        raise ValueError('No-send template/guard/trigger/authority differs')
    return graph


def definition(site_url, list_id):
    graph = _definition(site_url, list_id)
    return validate_no_send_definition(graph, site_url, list_id)
