"""Author a separate Power Automate observer; no deployment or local runtime.

Reuse the selected export's SharePoint binding and paths. A commissioning body
reads one explicitly pinned accepted run and cannot claim a scheduled occurrence.
The scheduled body is prepared separately and must remain stopped until authorised.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID
from zoneinfo import ZoneInfo


def prepare_schedule_repair(exporter, observer, *, as_of):
    """Prepare only the two existing schedules; never deploy or invoke them.

    An explicit past anchor avoids the documented future-start lead-time trap.
    The observer runs five minutes after its existing three-hour deadline.
    Existing exporter actions, connections and observer evidence rules survive.
    """
    if not isinstance(as_of, datetime) or as_of.utcoffset() is None:
        raise ValueError('Explicit timezone-aware observation clock required')
    export_trigger = exporter['properties']['definition']['triggers']['Recurrence']
    monitor_trigger = observer['properties']['definition']['triggers']['Recurrence']
    recurrence = export_trigger['recurrence']
    schedule = recurrence.get('schedule', {})
    if (recurrence.get('frequency') != 'Month' or recurrence.get('interval') != 1
            or recurrence.get('timeZone') != 'E. Australia Standard Time'
            or schedule.get('monthDays') != [1]
            or list(map(str, schedule.get('hours', []))) != ['7']
            or list(map(str, schedule.get('minutes', []))) != ['0']):
        raise ValueError('Reconcile exact selected day-1 07:00 export policy')
    monitor = monitor_trigger['recurrence']
    if (monitor.get('frequency') != 'Day' or monitor.get('interval') != 1
            or monitor.get('timeZone') != recurrence['timeZone']):
        raise ValueError('Existing daily observer identity/policy required')
    actions = observer['properties']['definition']['actions']
    expected = "@convertToUtc(concat(formatDateTime(convertTimeZone(outputs('Observed_at'),'UTC','E. Australia Standard Time'),'yyyy-MM'),'-01T07:00:00'),'E. Australia Standard Time')"
    if (actions['Expected_at']['inputs'] != expected
            or actions['Deadline']['inputs'] != "@addHours(outputs('Expected_at'),3)"):
        raise ValueError('Expected-export clock or deadline changed; reconcile first')
    local = as_of.astimezone(ZoneInfo('Australia/Brisbane'))
    previous_month = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    anchor = previous_month.replace(day=1)
    result = copy.deepcopy((exporter, observer))
    for flow, hour, minute in ((result[0], 7, 0), (result[1], 10, 5)):
        trigger = flow['properties']['definition']['triggers']['Recurrence']
        if ('evaluatedRecurrence' in trigger
                and trigger['evaluatedRecurrence'] != trigger['recurrence']):
            raise ValueError('Evaluated recurrence differs; refuse ambiguous schedule')
        trigger['recurrence']['startTime'] = anchor.replace(hour=hour, minute=minute).strftime('%Y-%m-%dT%H:%M:%S')
        if flow is result[1]:
            trigger['recurrence']['schedule'] = {'hours': [hour], 'minutes': [minute]}
        if 'evaluatedRecurrence' in trigger:
            trigger['evaluatedRecurrence'] = copy.deepcopy(trigger['recurrence'])
    result[1]['properties']['definition']['actions']['Due']['expression'] = "@greaterOrEquals(ticks(outputs('Observed_at')),ticks(outputs('Deadline')))"
    return result


def prepare(source, runtime_flow_id, *, commissioning_run=None):
    try:
        exact_id = str(UUID(runtime_flow_id))
    except (ValueError, TypeError, AttributeError):
        exact_id = None
    if exact_id != runtime_flow_id:
        raise ValueError('Exact retained runtime flow identity required')
    if commissioning_run is not None and not re.fullmatch(r'085[0-9A-Za-z]{20,50}', commissioning_run):
        raise ValueError('Exact accepted commissioning run required')
    props = source['properties']
    original = props['definition']
    export = original['actions']['Export_Run']['actions']
    save = export['Printable_Save_completion_manifest']['inputs']['parameters']
    site, folder = save['dataset'], save['folderPath']
    parsed = urlparse(site)
    if (parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.sharepoint.com')
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError('Qualified existing SharePoint site required')
    if not folder.startswith('/Documents/') or '..' in folder or "'" in folder:
        raise ValueError('Existing reporting folder required')
    refs = props['connectionReferences']
    if set(refs) != {'shared_sharepointonline'}:
        raise ValueError('Reconcile the selected SharePoint-only source binding')
    recurrence = original['triggers']['Recurrence']['recurrence']
    if (recurrence.get('startTime') != '2026-11-01T09:00:00'
            or recurrence.get('frequency') != 'Month' or recurrence.get('interval') != 1
            or recurrence.get('timeZone') != 'E. Australia Standard Time'
            or recurrence.get('schedule', {}).get('monthDays') != [1]
            or list(map(str, recurrence.get('schedule', {}).get('hours', []))) != ['9']
            or list(map(str, recurrence.get('schedule', {}).get('minutes', []))) != ['0']):
        raise ValueError('Selected first occurrence changed; reconcile operating policy')
    definition = {k: copy.deepcopy(original[k]) for k in ('$schema', 'contentVersion', 'parameters') if k in original}
    definition['triggers'] = ({'manual': {'type': 'Request', 'kind': 'Button',
        'inputs': {'schema': {'type': 'object', 'properties': {}}}}} if commissioning_run else
        {'Recurrence': {'type': 'Recurrence', 'recurrence': {'frequency': 'Day', 'interval': 1,
            'timeZone': 'E. Australia Standard Time', 'startTime': '2026-11-01T12:05:00',
            'schedule': {'hours': [12], 'minutes': [5]}},
            'runtimeConfiguration': {'concurrency': {'runs': 1}}}})

    def compose(value, after=None):
        return {'type': 'Compose', 'inputs': value, 'runAfter': {after: ['Succeeded']} if after else {}}

    def sp(operation, parameters, after=None):
        return {'type': 'OpenApiConnection', 'inputs': {
            'host': {'apiId': '/providers/Microsoft.PowerApps/apis/shared_sharepointonline',
                     'connectionName': 'shared_sharepointonline', 'operationId': operation},
            'parameters': {'dataset': site, **parameters}},
            'runAfter': {after: ['Succeeded']} if after else {}}

    def set_status(status, after=None):
        return {'type': 'SetVariable', 'inputs': {'name': 'DeliveryStatus', 'value': status},
                'runAfter': {after: ['Succeeded']} if after else {}}

    def condition(expression, actions, otherwise, after=None):
        return {'type': 'If', 'expression': expression, 'actions': actions,
                'else': {'actions': otherwise}, 'runAfter': {after: ['Succeeded']} if after else {}}

    def decoded(name):
        return "@json(base64ToString(body('"+name+"')?['$content']))"

    def read(path, after=None):
        return sp('GetFileContentByPath', {'path': path, 'inferContentType': False}, after)

    def require(expression, label, after=None):
        # A failed guard fails the scope before any success status can be set.
        return compose('@if('+expression+",'VERIFIED',int('"+label+"'))", after)

    a = {'Init_status': {'type': 'InitializeVariable', 'inputs': {'variables': [
        {'name': 'DeliveryStatus', 'type': 'string', 'value': 'UNKNOWN'}]}, 'runAfter': {}}}
    a['Observed_at'] = compose('@utcNow()', 'Init_status')
    a['Expected_at'] = compose("@convertToUtc(concat(formatDateTime(convertTimeZone(outputs('Observed_at'),'UTC','E. Australia Standard Time'),'yyyy-MM'),'-01T09:00:00'),'E. Australia Standard Time')", 'Observed_at')
    a['Deadline'] = compose("@addHours(outputs('Expected_at'),3)", 'Expected_at')
    server_folder = parsed.path.rstrip('/')+folder
    uri = "/_api/web/GetFolderByServerRelativeUrl('"+server_folder+"')/Files?$select=Name,TimeCreated,ServerRelativeUrl,Length&$orderby=TimeCreated desc&$top=5000"
    if not commissioning_run:
        uri = "@concat('"+uri.replace("'", "''")+"&$filter=TimeCreated ge datetime''',outputs('Expected_at'),'''' )"
    observe = {'List_receipts': sp('HttpRequest', {'parameters/method': 'GET',
        'parameters/uri': uri, 'parameters/headers': {'accept': 'application/json;odata=nometadata'}})}
    observe['Require_complete_listing'] = require(
        "and(empty(body('List_receipts')?['odata.nextLink']),empty(body('List_receipts')?['@odata.nextLink']),less(length(body('List_receipts')?['value']),5000))",
        'INCOMPLETE_RECEIPT_LIST', 'List_receipts')
    health_filter = ("@equals(item()?['Name'],'publication-register-"+commissioning_run+"-health.json')"
        if commissioning_run else "@and(startsWith(item()?['Name'],'publication-register-'),endsWith(item()?['Name'],'-health.json'))")
    observe['Health_receipts'] = {'type': 'Query', 'inputs': {'from': "@body('List_receipts')?['value']",
        'where': health_filter}, 'runAfter': {'Require_complete_listing': ['Succeeded']}}
    failure_filter = ("@equals(item()?['Name'],'publication-register-"+commissioning_run+"-failure.json')"
        if commissioning_run else "@and(startsWith(item()?['Name'],'publication-register-'),endsWith(item()?['Name'],'-failure.json'))")
    observe['Failure_receipts'] = {'type': 'Query', 'inputs': {'from': "@body('List_receipts')?['value']",
        'where': failure_filter},
        'runAfter': {'Health_receipts': ['Succeeded']}}
    good = {'Read_health': read("@concat('"+folder+"/',first(body('Health_receipts'))?['Name'])")}
    good['Health'] = compose(decoded('Read_health'), 'Read_health')
    good['Require_health'] = require(
        "and(equals(outputs('Health')?['kind'],'rims_register_export_health_v1'),equals(outputs('Health')?['flow_id'],'"+runtime_flow_id+"'),equals(outputs('Health')?['status'],'export-and-native-readback-succeeded'),equals(first(body('Health_receipts'))?['Name'],concat('publication-register-',outputs('Health')?['run_id'],'-health.json')),equals(outputs('Health')?['manifest_file'],concat('"+folder+"/publication-register-',outputs('Health')?['run_id'],'-manifest.json')))",
        'HEALTH_IDENTITY_OR_LINK_MISMATCH', 'Health')
    health_time = "lessOrEquals(ticks(outputs('Health')?['completed_at_utc']),ticks(outputs('Observed_at')))"
    if not commissioning_run:
        health_time = "and("+health_time+",greaterOrEquals(ticks(outputs('Health')?['completed_at_utc']),ticks(outputs('Expected_at'))))"
    good['Require_health_time'] = require(health_time, 'HEALTH_OUTSIDE_OBSERVATION_WINDOW', 'Require_health')
    good['Read_manifest'] = read("@outputs('Health')?['manifest_file']", 'Require_health_time')
    good['Manifest'] = compose(decoded('Read_manifest'), 'Read_manifest')
    good['Require_manifest'] = require(
        "and(equals(outputs('Manifest')?['kind'],'publication_register_printable_snapshot_v1'),equals(outputs('Manifest')?['status'],'generated-register-snapshot'),equals(outputs('Manifest')?['flow_run_id'],outputs('Health')?['run_id']),equals(outputs('Manifest')?['native_stored_content_readback_verified'],true),equals(outputs('Manifest')?['scope'],'all-keyed-register-rows; no publication-month filter'),greater(outputs('Manifest')?['register_row_count'],0),less(outputs('Manifest')?['register_row_count'],5000),equals(outputs('Manifest')?['part_size'],20),equals(outputs('Manifest')?['part_count'],div(add(outputs('Manifest')?['register_row_count'],19),20)),equals(outputs('Manifest')?['part_name_pattern'],concat('publication-register-',outputs('Health')?['run_id'],'-part-{zero-based-index}.html')),and(startsWith(outputs('Manifest')?['csv_file']?['Path'],'"+folder+"/publication-register-'),endsWith(outputs('Manifest')?['csv_file']?['Path'],'.csv'),not(contains(substring(outputs('Manifest')?['csv_file']?['Path'],"+str(len(folder)+1)+"),'/')),not(contains(outputs('Manifest')?['csv_file']?['Path'],'..'))),equals(outputs('Manifest')?['index_file']?['Path'],concat('"+folder+"/publication-register-',outputs('Health')?['run_id'],'-index.html')))",
        'MANIFEST_SCOPE_OR_CORRELATION_MISMATCH', 'Manifest')
    good['Read_CSV'] = read("@outputs('Manifest')?['csv_file']?['Path']", 'Require_manifest')
    good['Require_CSV'] = require("not(empty(body('Read_CSV')?['$content']))", 'CSV_CONTENT_ABSENT', 'Read_CSV')
    good['Read_index'] = read("@outputs('Manifest')?['index_file']?['Path']", 'Require_CSV')
    good['Require_index'] = require("contains(base64ToString(body('Read_index')?['$content']),'Publication register snapshot')", 'INDEX_CONTENT_ABSENT', 'Read_index')
    good['Read_all_parts'] = {'type': 'Foreach', 'foreach': "@range(0,outputs('Manifest')?['part_count'])",
        'runtimeConfiguration': {'concurrency': {'repetitions': 1}}, 'actions': {
            'Read_part': read("@concat('"+folder+"/publication-register-',outputs('Health')?['run_id'],'-part-',string(item()),'.html')"),
            'Require_part': require("contains(base64ToString(body('Read_part')?['$content']),'Publication register snapshot')", 'PART_CONTENT_ABSENT', 'Read_part')},
        'runAfter': {'Require_index': ['Succeeded']}}
    good['Set_delivered'] = set_status('COMMISSIONING_CONTENT_VERIFIED' if commissioning_run else
        "@if(lessOrEquals(ticks(outputs('Health')?['completed_at_utc']),ticks(outputs('Deadline'))),'DELIVERED_TRIGGER_ORIGIN_UNVERIFIED','LATE_DELIVERY_TRIGGER_ORIGIN_UNVERIFIED')", 'Read_all_parts')
    failure = {'Read_failure': read("@concat('"+folder+"/',first(body('Failure_receipts'))?['Name'])")}
    failure['Failure'] = compose(decoded('Read_failure'), 'Read_failure')
    failure['Require_failure'] = require(
        "and(equals(outputs('Failure')?['kind'],'rims_register_export_failure_v1'),equals(outputs('Failure')?['flow_id'],'"+runtime_flow_id+"'),equals(outputs('Failure')?['status'],'failed-or-timed-out'),equals(first(body('Failure_receipts'))?['Name'],concat('publication-register-',outputs('Failure')?['run_id'],'-failure.json')),lessOrEquals(ticks(outputs('Failure')?['observed_at_utc']),ticks(outputs('Observed_at'))))",
        'FAILURE_RECEIPT_IDENTITY_MISMATCH', 'Failure')
    failure['Export_failure'] = set_status('EXPORT_FAILURE_RECEIPT_PRESENT', 'Require_failure')
    missing = condition("@greater(length(body('Failure_receipts')),0)", failure,
        {'No_completion': set_status('MISSING_DELIVERY_EVIDENCE')})
    observe['One_health_receipt'] = condition("@equals(length(body('Health_receipts')),1)", good,
        {'No_unique_health': condition("@greater(length(body('Health_receipts')),1)",
            {'Ambiguous_delivery': set_status('MULTIPLE_DELIVERY_RECEIPTS')}, {'Missing_health': missing})}, 'Failure_receipts')
    active = {'Observe_delivery': {'type': 'Scope', 'actions': observe, 'runAfter': {}}}
    if commissioning_run:
        a.update(active)
        a['Observe_delivery']['runAfter'] = {'Deadline': ['Succeeded']}
        receipt_after = 'Observe_delivery'
    else:
        a['Due'] = condition("@and(greaterOrEquals(ticks(outputs('Observed_at')),ticks('2026-10-31T23:00:00Z')),greaterOrEquals(ticks(outputs('Observed_at')),ticks(outputs('Deadline'))))",
            active, {'Before_deadline': set_status('PENDING')}, 'Deadline')
        receipt_after = 'Due'
    a['Observation_receipt'] = compose({
        'kind': 'rims_delivery_observation_v1', 'status': "@variables('DeliveryStatus')",
        'observed_at_utc': "@outputs('Observed_at')", 'expected_at_utc': "@outputs('Expected_at')",
        'deadline_utc': "@outputs('Deadline')", 'runtime_flow_id': runtime_flow_id,
        'monitor_run_id': "@workflow()?['run']?['name']", 'commissioning': bool(commissioning_run),
        'export_run_id': "@outputs('Health')?['run_id']",
        'export_completed_at_utc': "@outputs('Health')?['completed_at_utc']",
        'completion_manifest': "@outputs('Health')?['manifest_file']",
        'health_receipt_count': "@length(coalesce(body('Health_receipts'),json('[]')))",
        'failure_receipt_count': "@length(coalesce(body('Failure_receipts'),json('[]')))",
        'failure_run_id': "@outputs('Failure')?['run_id']",
        'scheduled_trigger_proved': False, 'hashes_verified': False,
        'scope': 'Existing register CSV, printable index and every HTML part; not canonical monthly membership',
        'recovery': 'Preserve the last good generation; reconcile source run and missing content before replay. Never infer scheduled origin from Dataverse Scheduled label.'})
    a['Observation_receipt']['runAfter'] = {receipt_after: ['Succeeded', 'Failed', 'TimedOut', 'Skipped']}
    a['Save_observation'] = sp('CreateFile', {'folderPath': folder,
        'name': "@concat('delivery-observation-',workflow()?['run']?['name'],'.json')",
        'body': "@string(outputs('Observation_receipt'))"}, 'Observation_receipt')
    a['Read_observation'] = read("@body('Save_observation')?['Path']", 'Save_observation')
    a['Verify_observation'] = require("equals(body('Read_observation')?['$content'],base64(string(outputs('Observation_receipt'))))", 'OBSERVATION_SAVE_MISMATCH', 'Read_observation')
    a['Retain_non_success'] = condition("@not(contains(createArray('PENDING','COMMISSIONING_CONTENT_VERIFIED','DELIVERED_TRIGGER_ORIGIN_UNVERIFIED'),variables('DeliveryStatus')))",
        {'Incomplete': {'type': 'Terminate', 'inputs': {'runStatus': 'Failed',
            'runError': {'code': 'DeliveryEvidenceIncomplete', 'message': "@variables('DeliveryStatus')"}}, 'runAfter': {}}}, {}, 'Verify_observation')
    definition['actions'] = a
    result = copy.deepcopy(source)
    result['properties']['definition'] = definition
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('runtime_flow_id')
    parser.add_argument('output', type=Path)
    parser.add_argument('--commissioning-run')
    args = parser.parse_args()
    result = prepare(json.loads(args.source.read_text()), args.runtime_flow_id,
                     commissioning_run=args.commissioning_run)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    args.output.chmod(0o600)
    print('PREPARED_ONLY — no flow created, enabled or run')


if __name__ == '__main__':
    main()
