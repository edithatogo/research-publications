"""Prepare read-only native fault cases for an owned diagnostic flow.

No service I/O, source mutation, credential revocation or operational acceptance.
Restore the complete captured flow after qualification; never deploy to production.
"""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy

CASES = ('schema-missing', 'item-missing', 'partial-key', 'empty-success',
         'duplicate-shape', 'malformed-json')


def fault_definition(baseline: dict, case: str) -> dict:
    if case not in CASES:
        raise ValueError('Unknown bounded diagnostic case')
    definition = copy.deepcopy(baseline)
    trigger = definition['triggers']
    if (set(trigger) != {'manual'} or trigger['manual'].get('type') != 'Request'
            or trigger['manual'].get('kind') != 'Button'
            or trigger['manual'].get('inputs', {}).get('schema') != {
                'type': 'object', 'additionalProperties': False, 'properties': {}}
            or definition['parameters']['QualificationScenario']['defaultValue'] != 'inspect'):
        raise ValueError('Input-free manual inspect baseline required')
    actions = definition['actions']
    if set(actions) != {'Read_source_copy', 'Source', 'Guard_classification_current',
                        'Select_operation', 'Qualification_result'}:
        raise ValueError('Unexpected diagnostic graph')
    if any(actions[name].get('type') != 'Compose' for name in
           ('Source', 'Guard_classification_current', 'Qualification_result')):
        raise ValueError('Only source-read and Compose actions may remain executable')
    read = actions['Read_source_copy']
    params = read['inputs']['parameters']
    if (read['type'] != 'OpenApiConnection'
            or read['inputs']['host']['operationId'] != 'HttpRequest'
            or read['inputs']['host'].get('apiId') != '/providers/Microsoft.PowerApps/apis/shared_sharepointonline'
            or params['parameters/method'] != 'GET'
            or read['inputs'].get('retryPolicy') != {'type': 'none'}):
        raise ValueError('Read-only no-retry source action required')
    uri = params['parameters/uri']
    if '/items(1)?$select=' not in uri or 'OpportunityKey' not in uri:
        raise ValueError('Exact captured one-item selection required')
    # Remove all dormant Calendar/Ledger writers, rather than relying on a switch.
    actions['Select_operation'] = {
        'type': 'Compose', 'runAfter': {'Guard_classification_current': ['Succeeded']},
        'inputs': {'TEST_ONLY': True, 'DispatchEnabled': False}}
    if case == 'schema-missing':
        params['parameters/uri'] += ',TEST_ONLY_MISSING_COLUMN_20261028'
    elif case == 'item-missing':
        params['parameters/uri'] = uri.replace('/items(1)?', '/items(2147483000)?')
    elif case == 'partial-key':
        params['parameters/uri'] = uri.split('?$select=')[0] + '?$select=Id'
    elif case == 'empty-success':
        actions['Source']['inputs'] = []
    elif case == 'duplicate-shape':
        actions['Source']['inputs'] = "@createArray(body('Read_source_copy'),body('Read_source_copy'))"
    elif case == 'malformed-json':
        actions['Source']['inputs'] = "@setProperty(body('Read_source_copy'),'ClassificationEvidenceJSON','{TEST_ONLY_MALFORMED')"
    return definition
