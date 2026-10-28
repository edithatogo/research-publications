"""Prepare funding detail/limits locally while preserving existing keyed queries.

Amended from the retained reader helper: no source admission, schedule, native
transport, model changes or review decisions. Existing table fields are retained.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
from scripts.dashboard_reader_source import (capture, direct, model_contract, require,
    require_table_key, visual, write_candidate)

OPPORTUNITIES = '8dd811a45e8c948dd69a'
CALENDAR = 'b3e90f3eba2dbe0a1c1a'
TABLES = {OPPORTUNITIES: ('8dda39704411e961cda3', 'Grants Registry', 'OpportunityKey'),
          CALENDAR: ('739383a647a9679c269d', 'Funding Calendar', 'DeadlineKey')}
DETAIL_FIELDS = ('OpportunityKey', 'Title', 'Funder', 'Eligibility', 'Description',
                 'Geography', 'ReviewStatus', 'DeadlinePrecision', 'URL')
REQUIRED = [('Grants Registry', name, {'string'}) for name in DETAIL_FIELDS]
REQUIRED += [('Funding Calendar', name, {'string'}) for name in ('DeadlineKey', 'OpportunityKey')]
REQUIRED += [('My Funding Watchlist', name, {'string'}) for name in ('OpportunityKey', 'Scope', 'TargetKey')]


def funding_candidate(source, output, expected_sha, model_definition, expected_model_sha):
    files = capture(source, expected_sha)
    contract = model_contract(model_definition, expected_model_sha)
    require(contract, REQUIRED)
    updates = {}
    for page, (name, table, key) in TABLES.items():
        path = f'definition/pages/{page}/visuals/{name}/visual.json'
        if path not in files:
            raise ValueError('Expected funding table identity missing')
        doc = json.loads(files[path])
        if doc.get('name') != name:
            raise ValueError('Funding table identity drift')
        require_table_key(doc, table, key, contract)
    watch = f'definition/pages/{CALENDAR}/visuals/876392c7006b1020eeea/visual.json'
    if watch not in files:
        raise ValueError('Expected watchlist identity missing')
    require_table_key(json.loads(files[watch]), 'My Funding Watchlist', 'OpportunityKey', contract)
    # A watchlist scope/target remains a source record, never a person/publication join.
    require_table_key(json.loads(files[watch]), 'My Funding Watchlist', 'TargetKey', contract)
    require_table_key(json.loads(files[watch]), 'My Funding Watchlist', 'Scope', contract)
    for page, title, height in [(OPPORTUNITIES, 'Funding Opportunities', 1440),
                                (CALENDAR, 'Funding Calendar & Watchlist', 1200)]:
        path = f'definition/pages/{page}/page.json'; info = json.loads(files[path])
        if info.get('name') != page or info.get('displayName') != title or info.get('width') != 1920:
            raise ValueError('Funding page identity/name/canvas drift')
        info['height'] = max(info['height'], height); updates[path] = info
    old_table_path = f'definition/pages/{OPPORTUNITIES}/visuals/{TABLES[OPPORTUNITIES][0]}/visual.json'
    table = copy.deepcopy(json.loads(files[old_table_path]))
    table['position'].update(y=208, height=448)  # Preserve x/width/z/tabOrder, full query and filters.
    updates[old_table_path] = table
    specs = [
        (OPPORTUNITIES, 'funding-context', (32, 680, 1856, 136),
         'Source records and detail limits',
         'Opportunities, awards and applications have separate identities. The existing keyed table retains all its fields. Details below use OpportunityKey; selection/filter behavior needs native verification. Blank deadlines are unknown. Empty results mean no retained rows in this filter scope, not no opportunities. Confirm current terms at the source.'),
        (CALENDAR, 'funding-context', (32, 1000, 1856, 160),
         'Calendar and watchlist limits',
         'Calendar source day, deadline precision, cancellation and revision fields remain unchanged. Empty results mean no retained rows in the current filter scope; they do not establish that no opportunities exist. Watchlist scope and target keys are source evidence, not inferred people or funding links. Notifications and subscriptions are not activated.')]
    for page, name, rect, title, text in specs:
        path = f'definition/pages/{page}/visuals/{name}/visual.json'
        if path in files:
            raise ValueError('Funding context already exists')
        item = visual(files, name, 'textbox', rect, title, text=text)
        item['position'].update(z=100000, tabOrder=100000)
        updates[path] = item
    path = f'definition/pages/{OPPORTUNITIES}/visuals/opportunity-details/visual.json'
    if path in files:
        raise ValueError('Opportunity detail already exists')
    item = visual(files, 'opportunity-details', 'tableEx', (32, 848, 1856, 512),
                  'Retained opportunity evidence; OpportunityKey remains explicit',
                  roles={'Values': [direct('Grants Registry', name) for name in DETAIL_FIELDS]})
    item['position'].update(z=101000, tabOrder=99000)
    updates[path] = item
    return write_candidate(source, output, files, updates, contract, 'LOCAL_FUNDING_READER_NOT_SAVED')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--expected-sha', required=True); p.add_argument('--model', type=Path, required=True)
    p.add_argument('--expected-model-sha', required=True)
    a = p.parse_args()
    print(json.dumps(funding_candidate(a.source, a.output, a.expected_sha,
                                      a.model.read_bytes(), a.expected_model_sha), indent=2))


if __name__ == '__main__': main()
