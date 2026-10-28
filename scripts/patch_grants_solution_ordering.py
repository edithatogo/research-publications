"""Prepare a no-write guard against older or uncertain grants observations."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path

if __package__:
    from scripts.patch_grants_solution_deadlines import COUNT, patch_package
else:
    from patch_grants_solution_deadlines import COUNT, patch_package

INCOMING = "item()?['RetrievedUTC']"
EXISTING = "first(body('SharePoint_Get_items')?['value'])?['RetrievedUTC']"


def utc_suffix(value):
    return {'or': [{'equals': ["@endsWith(string(coalesce(" + value + ", '')), 'Z')", True]},
                   {'equals': ["@endsWith(string(coalesce(" + value + ", '')), '+00:00')", True]}]}


def failure(code, name):
    return {f'Compose_{name}': {'type': 'Compose', 'inputs': code},
            f'Increment_{name}': {'type': 'IncrementVariable',
                'inputs': {'name': 'RowFailureCount', 'value': 1},
                'runAfter': {f'Compose_{name}': ['Succeeded']}}}


def patch_definition(document):
    result = copy.deepcopy(document)
    root = result['properties']['definition']['actions']
    loop = root['Apply_to_each_Reviewed_Row']
    if loop.get('runtimeConfiguration', {}).get('concurrency', {}).get('repetitions') != 1:
        raise ValueError('Serial row loop required')
    if 'Initialize_Row_Failure_Count' not in root or 'Condition_Any_Row_Failures' not in root:
        raise ValueError('Failed-row aggregation required')
    permitted = loop['actions']['Condition_OpportunityKey_Present']['actions']['Condition_Conflicting_Source_Identity']['else']['actions']
    exact = permitted['Condition_Is_New_Opportunity']['else']['actions']['Condition_Exactly_One_Opportunity']
    predicate = exact['expression']
    if predicate != {'equals': [COUNT, 1]} and not (
            isinstance(predicate.get('and'), list) and predicate['and'][0] == {'equals': [COUNT, 1]}):
        raise ValueError('Exact-one update guard required')
    known = {'type': 'If', 'expression': {'and': [
        {'equals': ["@item()?['RetrievedTimestampStatus']", 'valid']},
        utc_suffix(INCOMING), utc_suffix(EXISTING)]},
        'actions': {'Condition_Observation_Not_Older': {
            'type': 'If', 'expression': {'greaterOrEquals': [
                '@ticks(' + INCOMING + ')', '@ticks(' + EXISTING + ')']},
            'actions': {}, 'else': {'actions': failure('OLDER_GRANTS_OBSERVATION', 'Older_Observation_Failure')}}},
        'else': {'actions': failure('UNCERTAIN_GRANTS_OBSERVATION_TIME', 'Uncertain_Observation_Failure')}}
    if set(exact['actions']) == {'Condition_Observation_Time_Known'}:
        existing = exact['actions']['Condition_Observation_Time_Known']
        update = existing['actions']['Condition_Observation_Not_Older']['actions']
        known['actions']['Condition_Observation_Not_Older']['actions'] = copy.deepcopy(update)
        if existing != known:
            raise ValueError('Existing ordering guard drifted')
        return result
    if set(exact['actions']) not in ({'SharePoint_Update_item'},
                                     {'SharePoint_Update_item', 'SharePoint_Update_item_Preserve_ISO_Text'}):
        raise ValueError('Unexpected update graph')
    update = exact['actions']['SharePoint_Update_item']
    if update['inputs']['host'].get('operationId') != 'PatchItem' or update.get('runAfter', {}) != {}:
        raise ValueError('Unexpected update action')
    safe_update = {'SharePoint_Update_item': copy.deepcopy(update)}
    preserve = exact['actions'].get('SharePoint_Update_item_Preserve_ISO_Text')
    if preserve is not None:
        if (preserve.get('inputs', {}).get('host', {}).get('operationId') != 'HttpRequest'
                or preserve.get('runAfter') != {'SharePoint_Update_item': ['Succeeded']}):
            raise ValueError('Unexpected ISO-text preservation action')
        safe_update['SharePoint_Update_item_Preserve_ISO_Text'] = copy.deepcopy(preserve)
    known['actions']['Condition_Observation_Not_Older']['actions'] = safe_update
    exact['actions'] = {'Condition_Observation_Time_Known': known}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--workflow', required=True)
    parser.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(patch_package(args.source, args.output, args.workflow,
        args.expected_sha256, patcher=patch_definition), indent=2))


if __name__ == '__main__':
    main()
