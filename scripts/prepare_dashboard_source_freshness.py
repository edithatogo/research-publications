"""Prepare distinct timestamp meanings from a frozen typed consumer inventory.

Amended from retained source. No string maxima, date coercion, assumed refresh
success, new acquisitions or model changes. Missing evidence stays unavailable.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from scripts.dashboard_reader_source import (add_page, capture, dependencies, direct,
    model_contract, visual, write_candidate)

PAGE = 'SourceFreshness'
SOURCES = (
    ('PubMed', 'observation', 'FreshSearchAudit', 'RefreshedAtUTC',
     'Search-execution observation only; not publication date, acquisition completeness or provider update.'),
    ('DORA publications', 'acquisition', None, None,
     'No qualified publication acquisition scalar exposed; activity timestamps do not substitute.'),
    ('DORA activities', 'observation', 'DORA Activity Registry', 'DORAObservedUTC',
     'Activity source observation only; acquisition is not independently qualified. Source project IDs and publication records remain distinct.'),
    ('OpenAlex', 'observation', 'OpenAlexWorks', 'OpenAlexObservedUTC',
     'Newest observation among imported works; not whole-provider currency or complete coverage.'),
    ('ARC awards', 'acquisition', 'ARCAwardContext', 'RetrievedUTC',
     'Retained award retrieval; not the award decision or publication date.'),
    ('ClinicalTrials.gov', 'acquisition', 'Study register', 'SourceObservedUTC',
     'Retained study acquisition; not study start, completion or source record update.'),
    ('NHMRC awards', 'acquisition', None, None, 'No qualified scalar exposed; source provenance remains separate.'),
    ('MRFF awards', 'acquisition', None, None, 'No qualified scalar exposed; source provenance remains separate.'),
    ('ROR', 'observation', None, None, 'No qualified scalar exposed; retained assertions remain separate.'),
    ('Crossref', 'observation', None, None, 'No qualified scalar exposed; retained assertions remain separate.'),
    ('ARDC', 'observation', None, None, 'No qualified scalar exposed; retained assertions remain separate.'),
    ('DataCite', 'observation', None, None, 'No qualified scalar exposed; retained assertions remain separate.'),
)


def timestamp_dependency(contract, table, column):
    if table is None:
        return [{'table': None, 'field': None, 'kind': 'Column',
                 'reason': 'No qualified scalar exposed', 'required_types': ['dateTime']}]
    return dependencies(contract, [(table, column, {'dateTime'})])


def prepare(source, output, *, expected_sha, model_definition, expected_model_sha):
    files = capture(source, expected_sha)
    contract = model_contract(model_definition, expected_model_sha)
    items, missing = [], []
    def add(name, rect, title, text=None, table=None, column=None):
        item = visual(files, name, 'card' if table else 'textbox', rect, title,
                      text=text, roles={'Values': [direct(table, column, maximum=True)]} if table else None)
        items.append(item)
    def scalar(name, rect, title, table, column, event):
        issues = timestamp_dependency(contract, table, column)
        if issues:
            missing.extend(dict(issue, event=event, consumer=name) for issue in issues)
            reason = 'no qualified scalar exposed' if table is None else (
                table+'.'+column+' has type '+str(issues[0].get('actual_type'))+'; a dateTime consumer is required')
            add(name, rect, title, text=title+': Unavailable. '+reason+'. No date conversion or substitute timestamp is inferred.')
        else:
            add(name, rect, title, table=table, column=column)
    add('heading', (32, 8, 1856, 64), 'Source timestamp evidence',
        text='SOURCE TIMESTAMP EVIDENCE | Separate event meanings')
    add('meaning', (32, 88, 1856, 128), 'How to read timestamps',
        text='Observation is when retained evidence was observed; acquisition is when it was retrieved. Processing is a model operation; publication dates describe research records. Provider modification is another event. A newest retained date does not establish complete coverage or successful scheduled delivery. Blank cards mean unavailable in this filter scope. UTC meaning is preserved; no timezone or text-date conversion is performed.')
    for index, (source_name, event, table, column, note) in enumerate(SOURCES):
        y = 248+index*224
        meanings = ['Observation: '+('see qualified scalar if present' if event == 'observation' else 'Unavailable'),
                    'Acquisition: '+('see qualified scalar if present' if event == 'acquisition' else 'Unavailable'),
                    'Processing completion: Unavailable; no per-source runtime receipt consumed',
                    'Publication date: separate record event, not a freshness scalar']
        add('source-'+str(index), (32, y, 880, 192), source_name+' timestamp meanings',
            text=source_name+'. '+note+'\n'+'\n'.join(meanings))
        scalar('timestamp-'+str(index), (960, y, 928, 192),
               source_name+' latest retained '+event+' UTC', table, column, event)
    y = 248+len(SOURCES)*224
    add('processing-meaning', (32, y, 880, 176), 'Materialization versus processing completion',
        text='Reporting-window materialization is a dated source value produced by that query. It is not proof that the whole model processed successfully, every source acquired data, recurrence ran or outputs were delivered. Processing completion remains Unavailable without its own runtime receipt.')
    scalar('materialization', (960, y, 928, 176), 'Reporting-window materialization UTC',
           'ReportingWindow', 'RefreshedAtUTC', 'materialization_context')
    y += 208
    add('provider-meaning', (32, y, 880, 176), 'Provider modification is separate',
        text='DORA activity resource modification is resource-level provider metadata, not acquisition or publication freshness. Other provider update events remain Unavailable here. Study LastUpdateSource is structured record-level evidence and is not reduced or parsed into a scalar by this reader.')
    scalar('provider-dora', (960, y, 928, 176), 'DORA activity resource provider modification UTC',
           'DORA Activity Registry', 'DORAResourceLastModified', 'provider_update')
    add('limits', (32, y+208, 1856, 112), 'Freshness limits',
        text='No publication dates, human review states or source timestamps are overwritten. No maximum over string timestamps, missing-as-zero, invented date, successful-refresh badge or provider-wide freshness claim is produced. Current report filters and every existing page are preserved; this page needs native rendering and interaction acceptance.')
    updates = add_page(files, PAGE, 'Source timestamp evidence', y+360, items)
    return write_candidate(source, output, files, updates, contract,
                           'LOCAL_SOURCE_TIMESTAMP_READER_NOT_SAVED', missing=missing)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--expected-sha', required=True); p.add_argument('--model', type=Path, required=True)
    p.add_argument('--expected-model-sha', required=True)
    a = p.parse_args()
    print(json.dumps(prepare(a.source, a.output, expected_sha=a.expected_sha,
        model_definition=a.model.read_bytes(), expected_model_sha=a.expected_model_sha), indent=2))


if __name__ == '__main__': main()
