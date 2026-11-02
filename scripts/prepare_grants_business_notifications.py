"""GrantConnect business notices using the retained standard-connector worker.

One fixed operator, existing private preferences/ledger, reviewed evidence only.
The legacy monitor retains operational alerts and excludes this source's notices.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
from uuid import UUID

from scripts.prepare_grants_delivery_worker import build as delivery_worker
from scripts.prepare_live_grants_calendar import after, branch, compose, envelope, guard, manual, query, spo

NAME = 'CHHHS RIMS | Grants | Business notifications'
SOURCE_FIELDS = 'Id,OpportunityKey,Title,URL,Source,EvidenceHash,ReviewStatus,FunderKey,CategoryKeysJSON,ClassificationEvidenceJSON'
PREF_FIELDS = 'Id,AuthorId,UserKey,Scope,TargetKey,Active,SubscriptionState,EventTypesJSON,ReminderOffsetsJSON,Cadence,Channel,Timezone'
DATE_FIELDS = 'Id,OpportunityKey,DeadlineKey,Revision,ReviewStatus,RevisionApplied,Cancelled,DeadlinePrecision,Calendar_x0020_day'


def foreach(rows, actions, previous=''):
    return {'type': 'Foreach', 'foreach': rows, 'actions': actions, 'runAfter': after(previous),
            'runtimeConfiguration': {'concurrency': {'repetitions': 1}}}


def html_text(expression):
    return "replace(replace(replace(replace(string(" + expression + "),'&','&amp;'),'<','&lt;'),'>','&gt;'),'\"','&quot;')"


def build(value, *, qualification=False):
    c = copy.deepcopy(value)
    for key in ['ledger_id', 'registry_id', 'watchlist_id', 'calendar_id']:
        c[key] = str(UUID(c[key]))
    # Reuse the already-qualified sender graph; template data never becomes a notice.
    identity = json.dumps(['3', 'GRANT:fixture', 'OPPORTUNITY', 'opportunity_changed', 'fixture', None, 'email'], separators=(',', ':'))
    template = {'Scope': 'grant', 'Channel': 'email', 'Recipient': c['operator_email'], 'UserKey': '3',
                'EventIdentity': identity, 'EventKey': 'EVENT:' + base64.b64encode(identity.encode()).decode(),
                'OpportunityKey': 'GRANT:fixture', 'DeadlineKey': 'OPPORTUNITY', 'EventType': 'opportunity_changed',
                'Revision': 'fixture', 'OffsetDays': None, 'Subject': 'RIMS grants: qualification template',
                'BodyHtml': '<p>Template only</p>', 'SourceRowID': 1, 'PreferenceRowID': 1,
                'SourceEvidenceHash': 'fixture', 'SourceVersion': '"1"', 'PreferenceVersion': '"1"'}
    packet = delivery_worker(c, template)
    sender = packet['properties']['definition']['actions']
    sender['Event'] = compose("@outputs('Prepared_notice')")
    # The generated graph must handle both opportunity and deadline events.
    for label in ['Read_Deadline', 'Guard_deadline']:
        if label not in sender:
            deadline_template = template | {'EventType': 'deadline_changed', 'DeadlineKey': 'DEADLINE:fixture',
                'DeadlineRowID': 1, 'DeadlineVersion': '"1"',
                'EventIdentity': json.dumps(['3', 'GRANT:fixture', 'DEADLINE:fixture', 'deadline_changed', 'fixture', None, 'email'], separators=(',', ':'))}
            deadline_template['EventKey'] = 'EVENT:' + base64.b64encode(deadline_template['EventIdentity'].encode()).decode()
            full = delivery_worker(c, deadline_template)['properties']['definition']['actions']
            sender[label] = full[label]
    deadline_checks = {k: sender.pop(k) for k in ['Read_Deadline', 'Guard_deadline']}
    deadline_checks['Read_Deadline']['runAfter'] = {}
    sender['Deadline_current'] = branch("@not(equals(outputs('Event')?['EventType'],'opportunity_changed'))", deadline_checks, previous='Guard_current')
    sender['Guard_delivery_enabled']['runAfter'] = after('Deadline_current')
    send = sender['If_unclaimed']['actions']
    full_send = delivery_worker(c, deadline_template)['properties']['definition']['actions']['If_unclaimed']['actions']
    checks = {k: full_send[k] for k in ['Read_Deadline_before_send', 'Guard_deadline_before_send']}
    checks['Read_Deadline_before_send']['runAfter'] = {}
    send['Deadline_before_send'] = branch("@not(equals(outputs('Event')?['EventType'],'opportunity_changed'))", checks, previous='Guard_current_before_send')
    send['Send_once']['runAfter'] = after('Deadline_before_send')
    # Native row IDs provide an exact, short receipt marker without a guessed hash.
    send['Send_once']['inputs']['parameters']['emailMessage/Subject'] = "@concat(take(outputs('Event')?['Subject'],180),' [RIMS-',string(body('Claim_event')?['Id']),']')"
    sender['Effective_subject'] = compose("@concat(take(outputs('Event')?['Subject'],180),' [RIMS-',string(first(body('Read_claim')?['value'])?['Id']),']')", 'Guard_claim')
    sender['Read_sent_folder']['runAfter'] = after('Effective_subject')
    sender['Read_receipt']['inputs']['parameters']['Uri'] = sender['Read_receipt']['inputs']['parameters']['Uri'].replace("outputs('Event')?['Subject']", "outputs('Effective_subject')")
    for name in ['Exact_receipt', 'Sent_receipt']:
        sender[name]['inputs']['where'] = sender[name]['inputs']['where'].replace("outputs('Event')?['Subject']", "outputs('Effective_subject')")
        sender[name]['inputs']['where'] = '@and(' + sender[name]['inputs']['where'][1:] + ",equals(length(item()?['toRecipients']),1),equals(toLower(first(item()?['toRecipients'])?['emailAddress']?['address']),'" + c['operator_email'].lower() + "'))"
    sender['Guard_unique']['inputs'] = sender['Guard_unique']['inputs'].replace('@if(lessOrEquals(', "@if(and(empty(body('Read_event')?['odata.nextLink']),empty(body('Read_event')?['@odata.nextLink']),lessOrEquals(").replace(",1),true,json", ",1)),true,json")
    # Once a delivered receipt is retained, unchanged scans do no provider/ledger work.
    tail_names = list(sender)[list(sender).index('If_unclaimed'):]
    # The appended deadline and effective-subject actions also belong to the tail.
    tail_names = [n for n in sender if (n in tail_names or n == 'Effective_subject') and n != 'Deadline_current']
    tail = {n: sender.pop(n) for n in tail_names}
    tail['If_unclaimed']['runAfter'] = {}
    sender['Reconcile_if_needed'] = branch("@not(and(equals(length(body('Read_event')?['value']),1),equals(first(body('Read_event')?['value'])?['Status'],'succeeded'),equals(first(body('Read_event')?['value'])?['EventIdentity'],outputs('Event')?['EventIdentity']),equals(first(body('Read_event')?['value'])?['UserKey'],string(body('Caller')?['Id'])),equals(first(body('Read_event')?['value'])?['DryRun'],false)))", tail, previous='Guard_unique')
    # Bind current source, saved preference author and full classification, twice.
    for actions, suffix in [(sender, ''), (send, '_before_send')]:
        name = 'Guard_current' + suffix
        expr = actions[name]['inputs']
        extra = "and(equals(body('Read_Source" + suffix + "')?['Source'],'GrantConnectRSS'),startsWith(coalesce(body('Read_Source" + suffix + "')?['URL']?['Url'],''),'https://www.grants.gov.au/'),equals(body('Read_Preference" + suffix + "')?['AuthorId'],body('Caller')?['Id']),equals(body('Read_Preference" + suffix + "')?['Timezone'],'Australia/Brisbane'),equals(json(body('Read_Source" + suffix + "')?['ClassificationEvidenceJSON'])?['FunderKey'],body('Read_Source" + suffix + "')?['FunderKey']),equals(json(body('Read_Source" + suffix + "')?['ClassificationEvidenceJSON'])?['CategoryKeys'],json(body('Read_Source" + suffix + "')?['CategoryKeysJSON'])))"
        actions[name]['inputs'] = expr.replace('@if(and(', '@if(and(' + extra + ',', 1)
    root = "_api/web/lists(guid'"
    a = {'Operator': spo(c, 'GET', '_api/web/currentuser?$select=Id,Email'),
         'Operator_guard': guard("and(greater(body('Operator')?['Id'],0),equals(toLower(body('Operator')?['Email']),'" + c['operator_email'].lower() + "'))", 'Operator'),
         'Now': compose('@utcNow()', 'Operator_guard'),
         'Local_now': compose("@convertFromUtc(outputs('Now'),'E. Australia Standard Time')", 'Now')}
    prev = 'Local_now'
    for label, key in [('Preference_boundary', 'watchlist_id'), ('Private_ledger', 'ledger_id')]:
        a[label] = spo(c, 'GET', root + c[key] + "')?$select=ReadSecurity,WriteSecurity,EnableVersioning", prev)
        a[label + '_guard'] = guard("and(equals(body('" + label + "')?['ReadSecurity'],2),equals(body('" + label + "')?['WriteSecurity'],2),equals(body('" + label + "')?['EnableVersioning'],true))", label)
        prev = label + '_guard'
    for label, key, fields in [('Registry', 'registry_id', SOURCE_FIELDS), ('Preferences', 'watchlist_id', PREF_FIELDS), ('Calendar', 'calendar_id', DATE_FIELDS)]:
        a[label] = spo(c, 'GET', root + c[key] + "')/items?$select=" + fields + '&$top=5000', prev)
        a[label + '_complete'] = guard("and(empty(body('" + label + "')?['odata.nextLink']),empty(body('" + label + "')?['@odata.nextLink']))", label)
        prev = label + '_complete'
    a['Eligible_sources'] = query("@body('Registry')?['value']", "@and(equals(item()?['Source'],'GrantConnectRSS'),equals(item()?['ReviewStatus'],'Reviewed'),not(empty(item()?['EvidenceHash'])),startsWith(coalesce(item()?['URL']?['Url'],''),'https://www.grants.gov.au/'))", prev)
    a['Own_rules'] = query("@body('Preferences')?['value']", "@and(equals(item()?['UserKey'],string(body('Operator')?['Id'])),equals(item()?['AuthorId'],body('Operator')?['Id']),equals(item()?['Active'],true),equals(item()?['SubscriptionState'],'active'),equals(item()?['Channel'],'email'),equals(item()?['Timezone'],'Australia/Brisbane'),or(equals(item()?['Cadence'],'immediate'),and(equals(formatDateTime(outputs('Local_now'),'HH'),'08'),or(equals(item()?['Cadence'],'daily'),and(equals(item()?['Cadence'],'weekly'),equals(dayOfWeek(outputs('Local_now')),1))))))", 'Eligible_sources')
    s = "items('Each_source')"
    rule = "items('Each_rule')"
    source_actions = {'Classification': compose("@json(coalesce(" + s + "?['ClassificationEvidenceJSON'],'{}'))"),
        'Classification_current': guard("and(equals(outputs('Classification')?['source_evidence_hash']," + s + "?['EvidenceHash']),equals(outputs('Classification')?['FunderKey']," + s + "?['FunderKey']),equals(outputs('Classification')?['CategoryKeys'],json(coalesce(" + s + "?['CategoryKeysJSON'],'[]'))))", 'Classification'),
        'Matching_rules': query("@body('Own_rules')", "@or(and(equals(item()?['Scope'],'opportunity'),equals(item()?['TargetKey']," + s + "?['OpportunityKey'])),and(equals(item()?['Scope'],'funder'),equals(item()?['TargetKey']," + s + "?['FunderKey'])),and(equals(item()?['Scope'],'category'),contains(outputs('Classification')?['CategoryKeys'],item()?['TargetKey'])))", 'Classification_current'),
        'Source_dates': query("@body('Calendar')?['value']", "@and(equals(item()?['OpportunityKey']," + s + "?['OpportunityKey']),equals(item()?['ReviewStatus'],'Reviewed'),equals(item()?['RevisionApplied'],true),not(empty(item()?['Revision'])))", 'Matching_rules')}
    source_actions['Classification_shape'] = {'type': 'ParseJson', 'runAfter': after('Classification'), 'inputs': {
        'content': "@outputs('Classification')", 'schema': {'type': 'object',
        'required': ['source_evidence_hash', 'FunderKey', 'CategoryKeys'], 'properties': {
            'source_evidence_hash': {'type': 'string', 'minLength': 1},
            'FunderKey': {'type': ['string', 'null']},
            'CategoryKeys': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}}}}}
    source_actions['Classification_current']['runAfter'] = after('Classification_shape')
    deadline_map = {'EventType': "@if(equals(item()?['Cancelled'],true),'deadline_cancelled','deadline_changed')", 'DeadlineKey': "@item()?['DeadlineKey']", 'Revision': "@item()?['Revision']", 'OffsetDays': None, 'DeadlineRowID': "@item()?['Id']", 'DeadlineVersion': "@item()?['odata.etag']", 'CalendarDay': "@item()?['Calendar_x0020_day']"}
    source_actions['Date_changes'] = {'type': 'Select', 'runAfter': after('Source_dates'), 'inputs': {'from': "@body('Source_dates')", 'select': deadline_map}}
    source_actions['Exact_days'] = query("@body('Source_dates')", "@and(not(equals(item()?['Cancelled'],true)),equals(item()?['DeadlinePrecision'],'day'),equals(length(coalesce(item()?['Calendar_x0020_day'],'')),10))", 'Date_changes')
    reminder_map = deadline_map | {'EventType': 'reminder', 'OffsetDays': "@div(sub(ticks(concat(item()?['Calendar_x0020_day'],'T00:00:00')),ticks(concat(formatDateTime(outputs('Local_now'),'yyyy-MM-dd'),'T00:00:00'))),864000000000)"}
    source_actions['Reminders'] = {'type': 'Select', 'runAfter': after('Exact_days'), 'inputs': {'from': "@body('Exact_days')", 'select': reminder_map}}
    opportunity = {'EventType': 'opportunity_changed', 'DeadlineKey': 'OPPORTUNITY', 'Revision': '@' + s + "?['EvidenceHash']", 'OffsetDays': None}
    source_actions['Opportunity_notice'] = compose(opportunity, 'Reminders')
    notice = "items('Each_notice')"
    n = {'Identity': compose("@string(createArray(string(body('Operator')?['Id'])," + s + "?['OpportunityKey']," + notice + "?['DeadlineKey']," + notice + "?['EventType']," + notice + "?['Revision']," + notice + "?['OffsetDays'],'email'))"),
         'Key': compose("@concat('EVENT:',base64(outputs('Identity')))", 'Identity'),
         'Key_bounded': guard("lessOrEquals(length(outputs('Key')),255)", 'Key')}
    prepared = {'Scope': 'grant', 'Channel': 'email', 'Recipient': c['operator_email'], 'UserKey': "@string(body('Operator')?['Id'])", 'EventIdentity': "@outputs('Identity')", 'EventKey': "@outputs('Key')", 'OpportunityKey': '@' + s + "?['OpportunityKey']", 'EventType': '@' + notice + "?['EventType']", 'DeadlineKey': '@' + notice + "?['DeadlineKey']", 'Revision': '@' + notice + "?['Revision']", 'OffsetDays': '@' + notice + "?['OffsetDays']", 'SourceRowID': '@' + s + "?['Id']", 'SourceVersion': '@' + s + "?['odata.etag']", 'SourceEvidenceHash': '@' + s + "?['EvidenceHash']", 'PreferenceRowID': '@' + rule + "?['Id']", 'PreferenceVersion': '@' + rule + "?['odata.etag']", 'DeadlineRowID': '@' + notice + "?['DeadlineRowID']", 'DeadlineVersion': '@' + notice + "?['DeadlineVersion']", 'Subject': "@concat('RIMS grants: ',replace(" + notice + "?['EventType'],'_',' '),' - ',take(" + s + "?['Title'],120))"}
    prepared['BodyHtml'] = ("@concat('<p>'," + html_text(s + "?['Title']") + ",'</p><p>',"
        + html_text(notice + "?['EventType']") + ",'</p>',if(empty(" + notice + "?['CalendarDay']),'',concat('<p>Recorded source calendar day: ',"
        + html_text(notice + "?['CalendarDay']") + ",'</p>')),'<p><a href=\"'," + html_text(s + "?['URL']?['Url']")
        + ",'\">Official source and closing details</a></p><p>Reviewed registry evidence and your saved email preference; this does not establish applicant eligibility.</p>')")
    n['Prepared_notice'] = compose(prepared, 'Key_bounded')
    n['Deliver'] = {'type': 'Scope', 'actions': sender, 'runAfter': after('Prepared_notice')}
    eligible = "@and(contains(json(" + rule + "?['EventTypesJSON']),item()?['EventType']),if(equals(item()?['EventType'],'reminder'),and(greaterOrEquals(item()?['OffsetDays'],0),contains(json(" + rule + "?['ReminderOffsetsJSON']),item()?['OffsetDays'])),true))"
    rules = {'Selected_notices': query("@union(createArray(outputs('Opportunity_notice')),body('Date_changes'),body('Reminders'))", eligible),
             'Each_notice': foreach("@body('Selected_notices')", n, 'Selected_notices')}
    rules['Preference_shape'] = {'type': 'ParseJson', 'runAfter': {}, 'inputs': {'content': {
        'events': '@json(' + rule + "?['EventTypesJSON'])", 'offsets': '@json(' + rule + "?['ReminderOffsetsJSON'])"},
        'schema': {'type': 'object', 'required': ['events', 'offsets'], 'properties': {
            'events': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'enum': ['opportunity_changed', 'deadline_changed', 'deadline_cancelled', 'reminder']}},
            'offsets': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'integer', 'minimum': 0, 'maximum': 3660}}}}}}
    rules['Selected_notices']['runAfter'] = after('Preference_shape')
    source_actions['Each_rule'] = foreach("@body('Matching_rules')", rules, 'Opportunity_notice')
    a['Dispatch'] = branch('@false' if qualification else '@true', {'Each_source': foreach("@body('Eligible_sources')", source_actions)}, previous='Own_rules')
    a['Summary'] = compose({'Qualification': qualification, 'ReviewedGrantConnectSources': "@length(body('Eligible_sources'))", 'DueOwnEmailRules': "@length(body('Own_rules'))", 'AutomaticRetry': False}, 'Dispatch')
    triggers = manual() if qualification else {'Due': {'type': 'Recurrence', 'recurrence': {'frequency': 'Minute', 'interval': 15}, 'runtimeConfiguration': {'concurrency': {'runs': 1}}}}
    return {'definition': envelope(a, triggers), 'connectionReferences': packet['properties']['connectionReferences']}


def main():
    import argparse
    import subprocess
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--qualification', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    source, output = Path(args.context).resolve(), Path(args.output).resolve()
    for path in [source, output]:
        if not path.is_relative_to(root) or 'private' not in path.relative_to(root).parts:
            parser.error('Ignored private context and new output paths inside this checkout required')
        subprocess.run(['git', 'check-ignore', '-q', str(path)], cwd=root, check=True)
    with output.open('x') as handle:
        json.dump(build(json.loads(source.read_text()), qualification=args.qualification), handle, indent=2)


if __name__ == '__main__':
    main()
