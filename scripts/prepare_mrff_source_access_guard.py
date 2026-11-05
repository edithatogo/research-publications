"""Prepare explicit MRFF source-block classification; no network or native writes.

This does not solve a provider challenge or replace the live link inventory with
old URLs. Both verified page reads must pass before discovery/commit continues.
"""
from copy import deepcopy

from scripts.capture_official_workbooks import SOURCES, SOURCE_CHALLENGE_MARKERS


def build(collector):
    candidate = deepcopy(collector)
    actions = candidate['properties']['definition']['actions']
    for suffix in ('', '_after'):
        fetch, verify, parser = ('Get_source_page' + suffix, 'Verify_page' + suffix,
                                 'Href_values' + suffix)
        guard = 'Guard_source_access' + suffix
        if (guard in actions or actions[fetch]['type'] != 'Http'
                or actions[fetch]['inputs']['uri'] != SOURCES['mrff'][0]
                or actions[fetch]['inputs'].get('method') != 'GET'
                or actions[parser]['runAfter'] != {verify: ['Succeeded']}):
            raise ValueError('Expected exact unguarded MRFF page-discovery contract')
        checks = ["contains(toLower(string(body('" + fetch + "'))),'" + marker + "')"
                  for marker in SOURCE_CHALLENGE_MARKERS]
        actions[guard] = {
            'type': 'If', 'runAfter': {verify: ['Succeeded']},
            'expression': '@or(' + ','.join(checks) + ')',
            'actions': {'Stop_blocked_source' + suffix: {
                'type': 'Terminate', 'inputs': {'runStatus': 'Failed', 'runError': {
                    'code': 'MRFF_SOURCE_ACCESS_BLOCKED',
                    'message': 'Official MRFF source returned a browser verification page, '
                               'not a workbook inventory. Preserve the last good archive. '
                               'Do not substitute old URLs, replay verification tokens or '
                               'treat this generation as complete.'}}}},
            'else': {'actions': {}}}
        actions[parser]['runAfter'] = {guard: ['Succeeded']}
    return candidate
