"""Prepare generic blank-identity and source-evidence collision guards offline."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path

if __package__:
    from scripts.patch_grants_solution_deadlines import ROOT, COUNT, patch_package
else:
    from patch_grants_solution_deadlines import ROOT, COUNT, patch_package

CONTRACT = ROOT / 'config/flows/grants-registry-reviewed-import.definition.json'


def patch_definition(document):
    result = copy.deepcopy(document)
    actions = result['properties']['definition']['actions']
    required_root = {'Parse_Reviewed_Rows', 'Apply_to_each_Reviewed_Row'}
    # Keep the current NIH coverage gate and failure aggregation in the root
    # graph. These are an intentional extension of the older identity patch.
    if not required_root.issubset(actions) or set(actions) - required_root - {
            'Filter_NIH_Rows', 'Condition_Require_NIH_Originals',
            'Initialize_Row_Failure_Count', 'Condition_Any_Row_Failures'}:
        raise ValueError('Unexpected root action graph')
    loop = actions['Apply_to_each_Reviewed_Row']
    if loop.get('runtimeConfiguration', {}).get('concurrency', {}).get('repetitions') != 1:
        raise ValueError('Serial execution required')
    old = loop['actions']
    if not {'SharePoint_Get_items', 'Condition_Duplicate_OpportunityKey', 'Condition_Is_New_Opportunity'}.issubset(old) or set(old) - {
            'SharePoint_Get_items', 'Condition_Duplicate_OpportunityKey',
            'Condition_Is_New_Opportunity', 'Archive_NIH_Update'}:
        raise ValueError('Unexpected existing row graph')
    duplicate = old['Condition_Duplicate_OpportunityKey']
    branch = old['Condition_Is_New_Opportunity']
    exact = branch['else']['actions']['Condition_Exactly_One_Opportunity']
    if (duplicate['expression'] != {'greater': [COUNT, 1]}
            or branch['expression'] != {'equals': [COUNT, 0]}
            or exact['expression'] != {'equals': [COUNT, 1]}):
        raise ValueError('Existing upsert guards have drifted')
    if (not {'SharePoint_Create_item'}.issubset(branch['actions'])
            or set(branch['actions']) - {'SharePoint_Create_item', 'SharePoint_Create_item_Preserve_ISO_Text', 'Guard_NIH_Parent_Already_Admitted'}
            or not {'SharePoint_Update_item'}.issubset(exact['actions'])
            or set(exact['actions']) - {'SharePoint_Update_item', 'SharePoint_Update_item_Preserve_ISO_Text'}
            or exact.get('else', {}).get('actions', {}) != {}
            or set(duplicate['actions']) != {'Compose_Duplicate_OpportunityKey_Failure'}):
        raise ValueError('Unexpected write or diagnostic branches')
    lookup = old['SharePoint_Get_items']
    params = lookup['inputs']['parameters']
    if lookup['inputs']['host'].get('operationId') != 'GetItems' or params.get('$top') != 2:
        raise ValueError('Unexpected native lookup')
    local = json.loads(CONTRACT.read_text())['properties']['definition']['actions']
    wrapper = copy.deepcopy(local['Apply_to_each_Reviewed_Row']['actions']['Condition_OpportunityKey_Present'])
    valid = wrapper['actions']
    if params.get('$filter') != valid['SharePoint_Get_items']['inputs']['parameters']['$filter']:
        raise ValueError('Identity lookup filter has drifted')
    # Native connection/authentication and exact site/list remain authoritative.
    valid['SharePoint_Get_items'] = copy.deepcopy(lookup)
    source_lookup = copy.deepcopy(lookup)
    source_lookup.pop('metadata', None)  # A new action must not reuse an existing designer identity.
    source_lookup['runAfter'] = {'SharePoint_Get_items': ['Succeeded']}
    source_lookup['inputs']['parameters']['$filter'] = valid['SharePoint_Get_source_identity']['inputs']['parameters']['$filter']
    source_lookup['inputs']['parameters']['$top'] = 1
    valid['SharePoint_Get_source_identity'] = source_lookup
    conflict = valid['Condition_Conflicting_Source_Identity']
    permitted = conflict['else']['actions']
    increment = copy.deepcopy(permitted['Condition_Duplicate_OpportunityKey']['actions']['Increment_Duplicate_Key_Failure_Count'])
    native_duplicate = copy.deepcopy(duplicate)
    native_duplicate['runAfter'] = {}  # Lookup is outside this branch scope.
    native_duplicate['actions']['Increment_Duplicate_Key_Failure_Count'] = increment
    rebuilt = {
        'Condition_Duplicate_OpportunityKey': native_duplicate,
        'Condition_Is_New_Opportunity': copy.deepcopy(branch),
    }
    # Preserve the archive/update branch and its dependency ordering verbatim.
    if 'Archive_NIH_Update' in old:
        rebuilt['Archive_NIH_Update'] = copy.deepcopy(old['Archive_NIH_Update'])
    conflict['else']['actions'] = rebuilt
    loop['actions'] = {'Condition_OpportunityKey_Present': wrapper}
    loop['runAfter'] = copy.deepcopy(local['Apply_to_each_Reviewed_Row']['runAfter'])
    actions['Initialize_Row_Failure_Count'] = copy.deepcopy(local['Initialize_Row_Failure_Count'])
    actions['Condition_Any_Row_Failures'] = copy.deepcopy(local['Condition_Any_Row_Failures'])
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
