# SPDX-License-Identifier: Apache-2.0
import pytest

import copy
import json
from datetime import datetime

import unittest

from scripts.patch_grants_solution_identity import CONTRACT
from scripts.patch_grants_solution_ordering import patch_definition, INCOMING, EXISTING


def exact(document):
    permitted = document['properties']['definition']['actions']['Apply_to_each_Reviewed_Row']['actions']['Condition_OpportunityKey_Present']['actions']['Condition_Conflicting_Source_Identity']['else']['actions']
    return permitted['Condition_Is_New_Opportunity']['else']['actions']['Condition_Exactly_One_Opportunity']


def baseline():
    result = json.loads(CONTRACT.read_text())
    branch = exact(result)
    branch['actions'] = branch['actions']['Condition_Observation_Time_Known']['actions']['Condition_Observation_Not_Older']['actions']
    return result


def test_only_update_is_wrapped_and_native_mappings_are_preserved():
    original = baseline()
    snapshot = copy.deepcopy(original)
    patched = patch_definition(original)
    assert original == snapshot
    assert patch_definition(patched) == patched
    wrapper = exact(patched)['actions']['Condition_Observation_Time_Known']
    exact(patched)['actions'] = wrapper['actions']['Condition_Observation_Not_Older']['actions']
    assert patched == original


def test_unknown_and_older_branches_have_diagnostics_and_no_writes():
    wrapper = exact(patch_definition(baseline()))['actions']['Condition_Observation_Time_Known']
    for condition, code in [(wrapper, 'UNCERTAIN_GRANTS_OBSERVATION_TIME'),
            (wrapper['actions']['Condition_Observation_Not_Older'], 'OLDER_GRANTS_OBSERVATION')]:
        actions = condition['else']['actions']
        assert [v['type'] for v in actions.values()] == ['Compose', 'IncrementVariable']
        assert next(iter(actions.values()))['inputs'] == code
        assert list(actions.values())[1]['inputs'] == {'name': 'RowFailureCount', 'value': 1}


@pytest.mark.parametrize('incoming,prior,permitted', [
    ('2026-10-04T00:00:00Z', '2026-10-05T00:00:00Z', False),
    ('2026-10-05T00:00:00Z', '2026-10-05T00:00:00+00:00', True),
    ('2026-10-06T00:00:00+00:00', '2026-10-05T00:00:00Z', True),
])
def test_actual_ordering_predicate_compares_instants(incoming, prior, permitted):
    wrapper = exact(patch_definition(baseline()))['actions']['Condition_Observation_Time_Known']
    predicate = wrapper['actions']['Condition_Observation_Not_Older']['expression']
    assert predicate == {'greaterOrEquals': ['@ticks(' + INCOMING + ')', '@ticks(' + EXISTING + ')']}
    left, right = (datetime.fromisoformat(t.replace('Z', '+00:00')) for t in (incoming, prior))
    assert (left >= right) is permitted


def test_non_utc_or_missing_observations_cannot_reach_ticks_or_update():
    wrapper = exact(patch_definition(baseline()))['actions']['Condition_Observation_Time_Known']
    predicates = wrapper['expression']['and']
    assert predicates[0] == {'equals': ["@item()?['RetrievedTimestampStatus']", 'valid']}
    for value, predicate in zip((INCOMING, EXISTING), predicates[1:]):
        assert predicate == {'or': [
            {'equals': ["@endsWith(string(coalesce(" + value + ", '')), 'Z')", True]},
            {'equals': ["@endsWith(string(coalesce(" + value + ", '')), '+00:00')", True]}]}
    # Parsing is nested inside the known-UTC branch: malformed dates fail the
    # condition before the connector, rather than gaining an invented date.
    assert 'ticks' not in json.dumps(wrapper['expression'])


def test_guard_drift_and_missing_failure_aggregation_are_rejected():
    patched = patch_definition(baseline())
    exact(patched)['actions']['Condition_Observation_Time_Known']['expression'] = {'equals': [1, 1]}
    with pytest.raises(ValueError):
        patch_definition(patched)
    original = baseline()
    del original['properties']['definition']['actions']['Condition_Any_Row_Failures']
    with pytest.raises(ValueError):
        patch_definition(original)


def test_iso_preservation_stays_inside_chronology_gate_without_field_changes():
    original=baseline();actions=exact(original)['actions']
    preserve={'type':'OpenApiConnection','inputs':{'host':{'operationId':'HttpRequest'}},'runAfter':{'SharePoint_Update_item':['Succeeded']}}
    actions['SharePoint_Update_item_Preserve_ISO_Text']=preserve
    result=patch_definition(original)
    guarded=exact(result)['actions']['Condition_Observation_Time_Known']['actions']['Condition_Observation_Not_Older']['actions']
    assert guarded==actions
    assert patch_definition(result)==result
