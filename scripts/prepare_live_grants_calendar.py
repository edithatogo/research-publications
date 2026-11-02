"""Current-operator Outlook subscriptions over retained GrantConnect deadlines.

Existing private preferences and ledger; one serial event writer. Change signals
coalesce in an owned SharePoint file. No mail, invitations or public feed tokens.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import re
from urllib.parse import quote, urlsplit
from uuid import UUID

from scripts.grants_live_delivery import current_classification

PROPERTY = 'String {52a615fa-f078-528a-9cec-313cbff44596} Name RIMSCalendarKey'
SIGNAL = 'rims-calendar-sync.json'
ZONE = 'E. Australia Standard Time'


def decision(row, source, rules, *, user_key):
    """Keep unknown evidence distinct from explicit withdrawal of a follow."""
    active = [r for r in rules if r.get('UserKey') == str(user_key)
              and str(r.get('AuthorId')) == str(user_key) and r.get('Active') is True
              and r.get('SubscriptionState') == 'active' and r.get('Channel') == 'calendar']
    if not active:
        return 'remove'
    classified = current_classification(source)
    categories = json.loads(source['CategoryKeysJSON']) if classified else []
    match = any((r.get('Scope') == 'opportunity' and r.get('TargetKey') == row.get('OpportunityKey'))
                or (classified and r.get('Scope') == 'funder' and r.get('TargetKey') == source.get('FunderKey'))
                or (classified and r.get('Scope') == 'category' and r.get('TargetKey') in categories)
                for r in active)
    if not match:
        return 'hold' if not classified and any(r.get('Scope') in ('funder', 'category') for r in active) else 'remove'
    source_url = row.get('SourceURL')
    source_url = source_url.get('Url') if isinstance(source_url, dict) else source_url
    registry_url = source.get('URL')
    registry_url = registry_url.get('Url') if isinstance(registry_url, dict) else registry_url
    official = (source.get('Source') == 'GrantConnectRSS' and source_url == registry_url
                and isinstance(source_url, str) and source_url.startswith('https://www.grants.gov.au/')
                and re.fullmatch(r'GC-CLOSE:[0-9a-f]{32}', str(row.get('DeadlineKey', ''))))
    if not official or row.get('RevisionApplied') is not True or row.get('ReviewStatus') not in ('Reviewed', 'Source confirmed'):
        return 'hold'
    if row.get('Cancelled') is True or row.get('DeadlinePrecision') != 'day':
        return 'remove'
    day = row.get('Calendar_x0020_day')
    if not isinstance(day, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        return 'hold'
    try:
        dt.date.fromisoformat(day)
    except ValueError:
        return 'hold'
    return 'upsert'


def context(value):
    c = copy.deepcopy(value)
    for key in ('registry_id', 'calendar_list_id', 'watchlist_id', 'ledger_id', 'library_id'):
        c[key] = str(UUID(c[key]))
    u = urlsplit(c['site'])
    if u.scheme != 'https' or not re.fullmatch(r'[a-z0-9-]+(?:-my)?\.sharepoint\.com', u.netloc):
        raise ValueError('Exact retained SharePoint site required')
    if (not re.fullmatch(r'/[A-Za-z0-9_ /-]+', c['server_folder'])
            or c['server_folder'] != u.path + c['folder'] or not c['folder'].startswith('/Documents/')):
        raise ValueError('Existing reporting folder binding required')
    if not re.fullmatch(r'[^\s<>\x27";,@]+@[^\s<>\x27";,@]+', c['operator_email']):
        raise ValueError('One pinned operator required')
    for key in ('sharepoint_connection', 'outlook_connection'):
        if not re.fullmatch(r'[A-Za-z0-9-]+', c[key]):
            raise ValueError('Existing connection name required')
    if not isinstance(c['calendar_id'], str) or not re.fullmatch(r'[A-Za-z0-9_+=/-]{20,1000}', c['calendar_id']):
        raise ValueError('Exact owned calendar ID required')
    return c


def refs(c):
    return {alias: {'id': '/providers/Microsoft.PowerApps/apis/' + alias,
                   'connectionName': c[key], 'source': 'Embedded'}
            for alias, key in [('shared_sharepointonline', 'sharepoint_connection'),
                               ('shared_office365', 'outlook_connection')]}


def after(name):
    return {name: ['Succeeded']} if name else {}


def compose(value, previous=''):
    return {'type': 'Compose', 'runAfter': after(previous), 'inputs': value}


def guard(expression, previous=''):
    return compose("@if(" + expression + ",true,json('RIMS_CALENDAR_GUARD_FAILED'))", previous)


def branch(expression, yes, no=None, previous=''):
    return {'type': 'If', 'expression': expression, 'runAfter': after(previous),
            'actions': yes, 'else': {'actions': no or {}}}


def spo(c, method, uri, previous='', body=None, etag=None):
    params = {'dataset': c['site'], 'parameters/method': method, 'parameters/uri': uri,
              'parameters/headers': {'Accept': 'application/json;odata=minimalmetadata'}}
    if body is not None:
        params['parameters/body'] = body
        params['parameters/headers']['Content-Type'] = 'application/json;odata=nometadata'
    if etag is not None:
        params['parameters/headers'].update({'X-HTTP-Method': 'MERGE', 'IF-MATCH': etag})
    return {'type': 'OpenApiConnection', 'runAfter': after(previous), 'inputs': {
        'host': {'apiId': '/providers/Microsoft.PowerApps/apis/shared_sharepointonline',
                 'connectionName': 'shared_sharepointonline', 'operationId': 'HttpRequest'},
        'parameters': params, 'retryPolicy': {'type': 'none'}}}


def graph(method, uri, previous='', body=None, etag=None):
    params = {'Uri': uri, 'Method': method, 'ContentType': 'application/json',
              'CustomHeader1': 'Prefer: outlook.timezone="' + ZONE + '", outlook.body-content-type="text"'}
    if body is not None:
        params['Body'] = body
    if etag is not None:
        params['CustomHeader2'] = etag
    return {'type': 'OpenApiConnection', 'runAfter': after(previous), 'inputs': {
        'host': {'apiId': '/providers/Microsoft.PowerApps/apis/shared_office365',
                 'connectionName': 'shared_office365', 'operationId': 'HttpRequest'},
        'parameters': params, 'retryPolicy': {'type': 'none'}}}


def envelope(actions, triggers):
    return {'$schema': 'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#',
            'contentVersion': '1.0.0.0', 'parameters': {
                '$authentication': {'type': 'SecureObject', 'defaultValue': {}},
                '$connections': {'type': 'Object', 'defaultValue': {}}},
            'triggers': triggers, 'actions': actions}


def manual():
    return {'manual': {'type': 'Request', 'kind': 'Button',
                       'runtimeConfiguration': {'concurrency': {'runs': 1}},
                       'inputs': {'schema': {'type': 'object', 'additionalProperties': False, 'properties': {}}}}}


def polling(c, operation, table, *, file=False):
    trigger = {'type': 'OpenApiConnection', 'recurrence': {'frequency': 'Minute', 'interval': 5},
        'splitOn': "@triggerOutputs()?['body/value']", 'runtimeConfiguration': {'concurrency': {'runs': 1}},
        'inputs': {'host': {'apiId': '/providers/Microsoft.PowerApps/apis/shared_sharepointonline',
                           'connectionName': 'shared_sharepointonline', 'operationId': operation},
                   'parameters': {'dataset': c['site'], 'table': table}}}
    if file:
        trigger['inputs']['parameters']['folderPath'] = c['folder']
        trigger['conditions'] = [{'expression': "@equals(triggerBody()?['{FilenameWithExtension}'],'" + SIGNAL + "')"}]
    return {'Changed': trigger}


def signal_adapter(value, source):
    c = context(value)
    if source not in ('watchlist_id', 'calendar_list_id', 'registry_id'):
        raise ValueError('Only preference/deadline/classification change signals supported')
    uri = "_api/web/GetFolderByServerRelativeUrl('" + c['server_folder'] + "')/Files/Add(url='" + SIGNAL + "',overwrite=true)"
    actions = {'Signal': spo(c, 'POST', uri,
        body="@string(setProperty(setProperty(json('{}'),'changedUtc',utcNow()),'sourceRun',workflow()?['run']?['name']))")}
    return envelope(actions, polling(c, 'GetOnUpdatedItems', c[source]))


def find_uri(c, key):
    prefix = 'https://graph.microsoft.com/v1.0/me/calendars/' + quote(c['calendar_id'], safe='') + '/events?'
    # The key is URI encoded data; no caller-selected endpoint or recipient.
    query = "$filter=singleValueExtendedProperties/Any(p:p/id eq '" + PROPERTY + "' and p/value eq '"
    tail = "')&$expand=singleValueExtendedProperties($filter=id eq '" + PROPERTY + "')&$top=2"
    return "@concat('" + quote(prefix + query, safe=":/?$=&()'").replace("'", "''") + "',uriComponent(" + key + "),'" + quote(tail, safe=":/?$=&()'").replace("'", "''") + "')"


def qualification(value):
    """One explicit native create/update/delete cycle; no source or preference edits."""
    c = context(value)
    base = 'https://graph.microsoft.com/v1.0/me/calendars/' + quote(c['calendar_id'], safe='')
    key = "concat('RIMSQUAL:',workflow()?['run']?['name'])"
    payload = {'subject': 'TEST ONLY RIMS live calendar qualification', 'body': {'contentType': 'text', 'content': 'Temporary RIMS calendar qualification; no invitation.'},
        'start': {'dateTime': '2026-12-30T00:00:00', 'timeZone': ZONE},
        'end': {'dateTime': '2026-12-31T00:00:00', 'timeZone': ZONE},
        'isAllDay': True, 'showAs': 'free', 'sensitivity': 'private', 'isReminderOn': False,
        'transactionId': '@' + key, 'singleValueExtendedProperties': [{'id': PROPERTY, 'value': '@' + key}]}
    a = {'Target': graph('GET', base + '?$select=id,owner,canEdit'),
         'Guard_target': guard("and(equals(toLower(body('Target')?['owner']?['address']),'" + c['operator_email'].lower() + "'),equals(body('Target')?['canEdit'],true))", 'Target'),
         'Payload': compose(payload, 'Guard_target'),
         'Create': graph('POST', base + '/events', 'Payload', '@string(outputs(\'Payload\'))')}
    uri = "@concat('" + base + "/events/',uriComponent(body('Create')?['id']))"
    a['Read_created'] = graph('GET', uri, 'Create')
    a['Guard_created'] = guard("and(equals(body('Read_created')?['id'],body('Create')?['id']),empty(body('Read_created')?['attendees']),equals(body('Read_created')?['isAllDay'],true),equals(body('Read_created')?['sensitivity'],'private'),not(empty(body('Read_created')?['@odata.etag'])))", 'Read_created')
    a['Locate_owned'] = graph('GET', find_uri(c, key), 'Guard_created')
    a['Guard_located'] = guard("and(empty(body('Locate_owned')?['@odata.nextLink']),equals(length(body('Locate_owned')?['value']),1),equals(first(body('Locate_owned')?['value'])?['id'],body('Create')?['id']))", 'Locate_owned')
    a['Changed_payload'] = compose({'subject': 'TEST ONLY RIMS live calendar qualification updated',
        'start': {'dateTime': '2026-12-31T00:00:00', 'timeZone': ZONE},
        'end': {'dateTime': '2027-01-01T00:00:00', 'timeZone': ZONE}}, 'Guard_located')
    a['Update'] = graph('PATCH', uri, 'Changed_payload', "@string(outputs('Changed_payload'))",
                        "@concat('If-Match: ',body('Read_created')?['@odata.etag'])")
    a['Read_updated'] = graph('GET', uri, 'Update')
    a['Guard_updated'] = guard("and(equals(body('Read_updated')?['id'],body('Create')?['id']),empty(body('Read_updated')?['attendees']),equals(body('Read_updated')?['subject'],'TEST ONLY RIMS live calendar qualification updated'),equals(formatDateTime(body('Read_updated')?['start']?['dateTime'],'yyyy-MM-dd'),'2026-12-31'))", 'Read_updated')
    a['Delete'] = graph('DELETE', uri, 'Guard_updated', etag="@concat('If-Match: ',body('Read_updated')?['@odata.etag'])")
    a['Read_removed'] = graph('GET', find_uri(c, key), 'Delete')
    a['Guard_removed'] = guard("and(empty(body('Read_removed')?['@odata.nextLink']),empty(body('Read_removed')?['value']))", 'Read_removed')
    a['Result'] = compose({'Created': True, 'UpdatedSameEvent': True, 'Removed': True,
                           'Invitations': 0, 'ExistingEventsChanged': 0}, 'Guard_removed')
    return envelope(a, manual())


def query(rows, expression, previous=''):
    return {'type': 'Query', 'inputs': {'from': rows, 'where': expression}, 'runAfter': after(previous)}


def items_uri(c, name, fields, extra=''):
    return "_api/web/lists(guid'" + c[name] + "')/items?$select=" + fields + '&$top=5000&$orderby=Id' + extra


PREF_FIELDS = 'Id,AuthorId,PreferenceKey,UserKey,Scope,TargetKey,Active,SubscriptionState,Channel'
DATE_FIELDS = 'Id,Title,Calendar_x0020_day,RevisionApplied,DeadlineKey,OpportunityKey,Revision,SourceURL,Cancelled,ReviewStatus,DeadlinePrecision'
SOURCE_FIELDS = 'Id,OpportunityKey,URL,Source,EvidenceHash,ReviewStatus,FunderKey,CategoryKeysJSON,ClassificationEvidenceJSON'
LEDGER_FIELDS = 'Id,Title,UserKey,OpportunityKey,EventType,Revision,Channel,Status,Attempt,ProviderID,EventIdentity,AttemptHistory,DryRun'


def worker(value):
    """Saved preferences -> confirmed source day -> one serial Outlook writer.

    Pending attempts are reconciled by marker reads, never retried as POSTs.
    Provider change keys protect subsequent human edits. Unknown evidence holds.
    """
    c = context(value)
    base = 'https://graph.microsoft.com/v1.0/me/calendars/' + quote(c['calendar_id'], safe='')
    prefs_uri = items_uri(c, 'watchlist_id', PREF_FIELDS)
    a = {'User': spo(c, 'GET', '_api/web/currentuser?$select=Id,Email'),
         'Guard_user': guard("and(greater(body('User')?['Id'],0),equals(toLower(body('User')?['Email']),'" + c['operator_email'].lower() + "'))", 'User'),
         'Target_calendar': graph('GET', base + '?$select=id,owner,canEdit', 'Guard_user'),
         'Guard_calendar': guard("and(equals(toLower(body('Target_calendar')?['owner']?['address']),'" + c['operator_email'].lower() + "'),equals(body('Target_calendar')?['canEdit'],true))", 'Target_calendar')}
    prev = 'Guard_calendar'
    for name, key in [('Preference_boundary', 'watchlist_id'), ('Ledger_boundary', 'ledger_id')]:
        a[name] = spo(c, 'GET', "_api/web/lists(guid'" + c[key] + "')?$select=ReadSecurity,WriteSecurity,EnableVersioning", prev)
        a['Guard_' + name] = guard("and(equals(body('" + name + "')?['ReadSecurity'],2),equals(body('" + name + "')?['WriteSecurity'],2),equals(body('" + name + "')?['EnableVersioning'],true))", name)
        prev = 'Guard_' + name
    for name, uri in [('Preferences', prefs_uri), ('Dates', items_uri(c, 'calendar_list_id', DATE_FIELDS)),
                      ('Sources', items_uri(c, 'registry_id', SOURCE_FIELDS)), ('Ledger', items_uri(c, 'ledger_id', LEDGER_FIELDS))]:
        a[name] = spo(c, 'GET', uri, prev)
        a['Complete_' + name] = guard("and(empty(body('" + name + "')?['odata.nextLink']),empty(body('" + name + "')?['@odata.nextLink']))", name)
        prev = 'Complete_' + name
    own = "and(equals(item()?['UserKey'],string(body('User')?['Id'])),equals(item()?['AuthorId'],body('User')?['Id']),equals(item()?['Active'],true),equals(item()?['SubscriptionState'],'active'),equals(item()?['Channel'],'calendar'))"
    a['Own_preferences'] = query("@body('Preferences')?['value']", '@' + own, prev)
    row = "items('Each_deadline')"
    hex_tail = "substring(concat(coalesce(" + row + "?['DeadlineKey'],''),'-----------------------------------------'),9,32)"
    for char in '0123456789abcdef':
        hex_tail = "replace(" + hex_tail + ",'" + char + "','')"
    r = {'Canonical': guard("and(startsWith(coalesce(" + row + "?['DeadlineKey'],''),'GC-CLOSE:'),equals(length(coalesce(" + row + "?['DeadlineKey'],'')),41),empty(" + hex_tail + "))"),
         'Key': compose("@concat('RIMSCAL:',string(body('User')?['Id']),':',toLower(" + row + "?['DeadlineKey']))", 'Canonical'),
         'Source_matches': query("@body('Sources')?['value']", "@equals(item()?['OpportunityKey']," + row + "?['OpportunityKey'])", 'Key'),
         'Ledger_matches': query("@body('Ledger')?['value']", "@equals(item()?['Title'],outputs('Key'))", 'Source_matches'),
         'Unique_rows': guard("and(lessOrEquals(length(body('Source_matches')),1),lessOrEquals(length(body('Ledger_matches')),1))", 'Ledger_matches'),
         'Source': compose("@if(empty(body('Source_matches')),json('{}'),first(body('Source_matches')))", 'Unique_rows'),
         'Previous': compose("@if(empty(body('Ledger_matches')),json('{}'),first(body('Ledger_matches')))", 'Source'),
         'Identity': compose({'User': "@string(body('User')?['Id'])", 'Calendar': c['calendar_id'], 'Deadline': '@' + row + "?['DeadlineKey']"}, 'Previous'),
         'Identity_guard': guard("or(empty(outputs('Previous')),and(equals(outputs('Previous')?['UserKey'],string(body('User')?['Id'])),equals(outputs('Previous')?['Channel'],'calendar'),equals(outputs('Previous')?['EventIdentity'],string(outputs('Identity')))))", 'Identity'),
         'Classification': compose("@json(if(empty(outputs('Source')?['ClassificationEvidenceJSON']),'{}',outputs('Source')?['ClassificationEvidenceJSON']))", 'Identity_guard'),
         'Categories': compose("@json(if(empty(outputs('Source')?['CategoryKeysJSON']),'[]',outputs('Source')?['CategoryKeysJSON']))", 'Classification'),
         'Classified': compose("@and(equals(outputs('Source')?['ReviewStatus'],'Reviewed'),not(empty(outputs('Source')?['EvidenceHash'])),equals(outputs('Classification')?['source_evidence_hash'],outputs('Source')?['EvidenceHash']),equals(outputs('Classification')?['FunderKey'],outputs('Source')?['FunderKey']),equals(outputs('Classification')?['CategoryKeys'],outputs('Categories')))", 'Categories'),
         'Matched': query("@body('Own_preferences')", "@or(and(equals(item()?['Scope'],'opportunity'),equals(item()?['TargetKey']," + row + "?['OpportunityKey'])),and(outputs('Classified'),or(and(equals(item()?['Scope'],'funder'),equals(item()?['TargetKey'],outputs('Source')?['FunderKey'])),and(equals(item()?['Scope'],'category'),contains(outputs('Categories'),item()?['TargetKey'])))))", 'Classified'),
         'Broad': query("@body('Own_preferences')", "@or(equals(item()?['Scope'],'funder'),equals(item()?['Scope'],'category'))", 'Matched')}
    official = "and(equals(outputs('Source')?['Source'],'GrantConnectRSS'),equals(" + row + "?['SourceURL']?['Url'],outputs('Source')?['URL']?['Url']),startsWith(coalesce(outputs('Source')?['URL']?['Url'],''),'https://www.grants.gov.au/'),equals(" + row + "?['RevisionApplied'],true),contains(createArray('Reviewed','Source confirmed')," + row + "?['ReviewStatus']))"
    # The SharePoint source-day field is text; formatDateTime rejects impossible days.
    decision_expr = "if(empty(body('Own_preferences')),'remove',if(empty(body('Matched')),if(and(not(outputs('Classified')),not(empty(body('Broad')))),'hold','remove'),if(not(" + official + "),'hold',if(or(equals(" + row + "?['Cancelled'],true),not(equals(" + row + "?['DeadlinePrecision'],'day'))),'remove',if(empty(" + row + "?['Calendar_x0020_day']),'hold','upsert')))))"
    r['Decision'] = compose('@' + decision_expr, 'Broad')
    # Hold rows never reach a provider boundary. No rules/explicit withdrawal can remove.
    w = {'Find': graph('GET', find_uri(c, "outputs('Key')")),
         'Unique_event': guard("and(empty(body('Find')?['@odata.nextLink']),lessOrEquals(length(body('Find')?['value']),1))", 'Find'),
         'Live': compose("@if(empty(body('Find')?['value']),json('{}'),first(body('Find')?['value']))", 'Unique_event'),
         'History': compose("@json(if(empty(outputs('Previous')?['AttemptHistory']),'[]',outputs('Previous')?['AttemptHistory']))", 'Live'),
         'Last': compose("@if(empty(outputs('History')),json('{}'),last(outputs('History')))", 'History'),
         'Owned_event': guard("or(empty(outputs('Live')),and(empty(outputs('Live')?['attendees']),not(empty(outputs('Live')?['@odata.etag'])),equals(length(outputs('Live')?['singleValueExtendedProperties']),1),equals(first(outputs('Live')?['singleValueExtendedProperties'])?['id'],'" + PROPERTY + "'),equals(first(outputs('Live')?['singleValueExtendedProperties'])?['value'],outputs('Key')),or(empty(outputs('Previous')?['ProviderID']),equals(outputs('Previous')?['ProviderID'],outputs('Live')?['id']))))", 'Last')}
    desired = {'subject': "@concat('RIMS grant: ',take(string(" + row + "?['Title']),200))", 'body': {'contentType': 'text', 'content': "@concat('Confirmed source closing day. Check the official page for the precise closing time: '," + row + "?['SourceURL']?['Url'],' | '," + row + "?['DeadlineKey'])"},
               'start': {'dateTime': '@concat(' + row + "?['Calendar_x0020_day'],'T00:00:00')", 'timeZone': ZONE},
               'end': {'dateTime': "@addDays(concat(" + row + "?['Calendar_x0020_day'],'T00:00:00'),1,'yyyy-MM-ddTHH:mm:ss')", 'timeZone': ZONE},
               'isAllDay': True, 'showAs': 'free', 'sensitivity': 'private', 'isReminderOn': False}
    w['Wanted'] = branch("@equals(outputs('Decision'),'upsert')", {'Desired': compose(desired)}, previous='Owned_event')
    w['Desired_value'] = compose("@if(equals(outputs('Decision'),'upsert'),outputs('Desired'),json('{}'))", 'Wanted')
    w['Source_day_valid'] = guard("if(not(equals(outputs('Decision'),'upsert')),true,and(equals(length(coalesce(" + row + "?['Calendar_x0020_day'],'')),10),equals(formatDateTime(concat(coalesce(" + row + "?['Calendar_x0020_day'],'2000-01-01'),'T00:00:00'),'yyyy-MM-dd')," + row + "?['Calendar_x0020_day'])))", 'Desired_value')
    w['Operation'] = compose("@if(equals(outputs('Decision'),'remove'),if(empty(outputs('Live')),'none','delete'),if(empty(outputs('Live')),'create',if(and(equals(outputs('Previous')?['Status'],'succeeded'),equals(outputs('Last')?['Desired'],outputs('Desired_value'))),'none','update')))", 'Source_day_valid')
    # Preserve human changes even for unchanged replay; pending recovery is read-only.
    w['Provider_version'] = guard("or(empty(outputs('Live')),and(equals(outputs('Previous')?['Status'],'succeeded'),equals(outputs('Last')?['ChangeKey'],outputs('Live')?['changeKey'])))", 'Operation')
    w['No_ambiguous_retry'] = guard("and(not(equals(outputs('Previous')?['Status'],'pending_attempt')),or(not(equals(outputs('Operation'),'create')),empty(outputs('Previous')?['ProviderID'])))", 'Provider_version')
    b = {'Current_preferences': spo(c, 'GET', prefs_uri),
         'Preferences_unchanged': guard("and(empty(body('Current_preferences')?['odata.nextLink']),empty(body('Current_preferences')?['@odata.nextLink']),equals(body('Current_preferences')?['value'],body('Preferences')?['value']))", 'Current_preferences'),
         'Current_day': spo(c, 'GET', "@concat('_api/web/lists(guid''" + c['calendar_list_id'] + "'')/items(',string(" + row + "?['Id']),')?$select=" + DATE_FIELDS + "')", 'Preferences_unchanged'),
         'Day_unchanged': guard("and(equals(body('Current_day')?['odata.etag']," + row + "?['odata.etag']),equals(body('Current_day')?['Revision']," + row + "?['Revision']))", 'Current_day'),
         'Source_still_present': branch("@not(empty(outputs('Source')))", {
             'Current_source': spo(c, 'GET', "@concat('_api/web/lists(guid''" + c['registry_id'] + "'')/items(',string(outputs('Source')?['Id']),')?$select=" + SOURCE_FIELDS + "')"),
             'Source_unchanged': guard("equals(body('Current_source')?['odata.etag'],outputs('Source')?['odata.etag'])", 'Current_source')}, previous='Day_unchanged'),
         'Attempt': compose("@add(int(coalesce(outputs('Previous')?['Attempt'],0)),1)", 'Source_still_present'),
         'Pending': compose({'Run': "@workflow()?['run']?['name']", 'State': 'pending', 'Operation': "@outputs('Operation')", 'Desired': "@outputs('Desired_value')", 'At': '@utcNow()'}, 'Attempt'),
         'Pending_history': compose("@union(outputs('History'),createArray(outputs('Pending')))", 'Pending'),
         'History_capacity': guard("less(length(string(outputs('Pending_history'))),58000)", 'Pending_history')}
    claim = {'Title': "@outputs('Key')", 'UserKey': "@string(body('User')?['Id'])", 'OpportunityKey': '@' + row + "?['OpportunityKey']", 'EventType': 'calendar_sync', 'Revision': '@' + row + "?['Revision']", 'Channel': 'calendar', 'Status': 'pending_attempt', 'Attempt': "@outputs('Attempt')", 'EventIdentity': "@string(outputs('Identity'))", 'AttemptHistory': "@string(outputs('Pending_history'))", 'DryRun': False}
    b['Claim'] = compose(claim, 'History_capacity')
    b['Claim_existing'] = branch("@not(empty(outputs('Previous')))",
        {'Claim_update': spo(c, 'POST', "@concat('_api/web/lists(guid''" + c['ledger_id'] + "'')/items(',string(outputs('Previous')?['Id']),')')", body="@string(outputs('Claim'))", etag="@outputs('Previous')?['odata.etag']")},
        {'Claim_create': spo(c, 'POST', "_api/web/lists(guid'" + c['ledger_id'] + "')/items", body="@string(outputs('Claim'))")}, 'Claim')
    b['Claim_id'] = compose("@if(empty(outputs('Previous')),body('Claim_create')?['Id'],outputs('Previous')?['Id'])", 'Claim_existing')
    b['Claim_read'] = spo(c, 'GET', "@concat('_api/web/lists(guid''" + c['ledger_id'] + "'')/items(',string(outputs('Claim_id')),')')", 'Claim_id')
    b['Claim_owned'] = guard("and(equals(body('Claim_read')?['Title'],outputs('Key')),equals(body('Claim_read')?['AttemptHistory'],string(outputs('Pending_history'))),equals(body('Claim_read')?['Status'],'pending_attempt'))", 'Claim_read')
    event_uri = "@concat('" + base + "/events/',uriComponent(outputs('Live')?['id']))"
    post_payload = "@string(setProperty(setProperty(outputs('Desired_value'),'transactionId',concat(outputs('Key'),':',string(outputs('Attempt')))),'singleValueExtendedProperties',createArray(setProperty(setProperty(json('{}'),'id','" + PROPERTY + "'),'value',outputs('Key')))))"
    b['Create_or_change'] = branch("@equals(outputs('Operation'),'create')", {'Create_event': graph('POST', base + '/events', body=post_payload)},
        {'Update_or_remove': branch("@equals(outputs('Operation'),'update')", {'Update_event': graph('PATCH', event_uri, body="@string(outputs('Desired_value'))", etag="@concat('If-Match: ',outputs('Live')?['@odata.etag'])")},
             {'Remove_event': graph('DELETE', event_uri, etag="@concat('If-Match: ',outputs('Live')?['@odata.etag'])")})}, 'Claim_owned')
    b['Read_result'] = graph('GET', find_uri(c, "outputs('Key')"), 'Create_or_change')
    b['Result_complete'] = guard("and(empty(body('Read_result')?['@odata.nextLink']),if(equals(outputs('Operation'),'delete'),empty(body('Read_result')?['value']),equals(length(body('Read_result')?['value']),1)))", 'Read_result')
    b['Result_event'] = compose("@if(empty(body('Read_result')?['value']),json('{}'),first(body('Read_result')?['value']))", 'Result_complete')
    b['Provider_result_matches'] = guard("if(equals(outputs('Operation'),'delete'),true,and(empty(outputs('Result_event')?['attendees']),equals(outputs('Result_event')?['subject'],outputs('Desired_value')?['subject']),equals(outputs('Result_event')?['body']?['content'],outputs('Desired_value')?['body']?['content']),equals(formatDateTime(outputs('Result_event')?['start']?['dateTime'],'yyyy-MM-dd')," + row + "?['Calendar_x0020_day']),equals(outputs('Result_event')?['isAllDay'],true),equals(outputs('Result_event')?['sensitivity'],'private'),equals(outputs('Result_event')?['showAs'],'free'),equals(outputs('Result_event')?['isReminderOn'],false),not(empty(outputs('Result_event')?['changeKey'])),or(equals(outputs('Operation'),'create'),equals(outputs('Result_event')?['id'],outputs('Live')?['id']))))", 'Result_event')
    b['Outcome'] = compose({'Run': "@workflow()?['run']?['name']", 'State': 'succeeded', 'Desired': "@outputs('Desired_value')", 'Operation': "@outputs('Operation')", 'ChangeKey': "@outputs('Result_event')?['changeKey']", 'At': '@utcNow()'}, 'Provider_result_matches')
    b['Save_outcome'] = spo(c, 'POST', "@concat('_api/web/lists(guid''" + c['ledger_id'] + "'')/items(',string(outputs('Claim_id')),')')", 'Outcome',
        body="@string(setProperty(setProperty(setProperty(json('{}'),'Status','succeeded'),'ProviderID',coalesce(outputs('Result_event')?['id'],'')),'AttemptHistory',string(union(outputs('Pending_history'),createArray(outputs('Outcome'))))))", etag="@body('Claim_read')?['odata.etag']")
    w['Apply_change'] = branch("@not(equals(outputs('Operation'),'none'))", b, previous='No_ambiguous_retry')
    r['Act_on_known_decision'] = branch("@and(not(equals(outputs('Decision'),'hold')),or(equals(outputs('Decision'),'upsert'),not(empty(outputs('Previous')))))", w, previous='Decision')
    # Only official namespace rows; unrelated calendars do not fail the whole run.
    a['Confirmed_rows'] = query("@body('Dates')?['value']", "@startsWith(coalesce(item()?['DeadlineKey'],''),'GC-CLOSE:')", 'Own_preferences')
    a['Each_deadline'] = {'type': 'Foreach', 'foreach': "@body('Confirmed_rows')", 'runAfter': after('Confirmed_rows'),
                          'runtimeConfiguration': {'concurrency': {'repetitions': 1}}, 'actions': r}
    return envelope(a, polling(c, 'GetOnUpdatedFileItems', c['library_id'], file=True))


def main():
    """Prepare private JSON; native authoring stays with FlowAgent."""
    import argparse
    from pathlib import Path
    import subprocess

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    source, output = Path(args.context).resolve(), Path(args.output).resolve()
    for path in [source, output]:
        if not path.is_relative_to(root) or 'private' not in path.relative_to(root).parts:
            parser.error('Use ignored private paths inside this checkout')
        subprocess.run(['git', 'check-ignore', '-q', str(path)], cwd=root, check=True)
    c = context(json.loads(source.read_text()))
    packet = {'worker': worker(c), 'preferences': signal_adapter(c, 'watchlist_id'),
              'deadlines': signal_adapter(c, 'calendar_list_id'), 'classification': signal_adapter(c, 'registry_id'),
              'connectionReferences': refs(c)}
    with output.open('x') as handle:
        json.dump(packet, handle, indent=2)
    print('Prepared private definitions; no native operation performed')


if __name__ == '__main__':
    main()
