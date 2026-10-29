"""Freeze complete existing discovery and supplementary scopes without network I/O."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from scripts.capture_discovery_source import validate_scope
from scripts.clinicaltrials_source import validate_ids
from scripts.crossref_targeted_policy import validate as validate_hedge
from scripts.source_capture_receipt import (
    create_output,
    json_bytes,
    scope_sha256,
    validate_dois,
)


def build(trials, datacite, hedge, collector, doi_snapshot, crossref_receipt, datacite_receipt):
    validate_hedge(hedge, collector)
    trial_actions = trials['properties']['definition']['actions']
    trial_scope = trial_actions['Acquisition_scope']['inputs']
    ids = validate_ids(trial_actions['Requested_ids']['inputs'])
    ct = {'source': 'clinicaltrials.gov', 'kind': 'complete_discovery', 'queries': [
        {'key': 'maintained-discovery', 'parameters': {'query.term': trial_scope['query_term'],
         'pageSize': '100', 'format': 'json', 'countTotal': 'true'}}]}
    inputs = doi_snapshot.get('publication_dois')
    publication_dois = validate_dois(inputs)
    if not publication_dois or len({d.casefold() for d in publication_dois}) != len(publication_dois):
        raise ValueError('Complete unique retained publication DOI population required')
    retained = datacite['properties']['definition']['actions']['Scope']['inputs']
    if retained['full_metadata_options'] != {'detail': 'true', 'affiliation': 'true', 'publisher': 'true'}:
        raise ValueError('Full DataCite metadata contract changed')
    queries = [{'key': q['key'], 'parameters': {'query': q['query'], 'page[size]': '100',
                **retained['full_metadata_options']}} for q in retained['institutional_queries']]
    if not queries:
        raise ValueError('Institutional discovery must not be replaced by exact DOI queries')
    size = retained['related_dois_per_query']
    if type(size) is not int or size != 20:
        raise ValueError('Existing DataCite related-DOI batch size required')
    for index in range(0, len(publication_dois), size):
        escaped = ['"' + d.replace('\\', '\\\\').replace('"', '\\"') + '"' for d in publication_dois[index:index+size]]
        query = 'relatedIdentifiers.relatedIdentifier:(' + ' OR '.join(escaped) + ')'
        queries.append({'key': 'related-' + str(index // size), 'parameters': {
            'query': query, 'page[size]': '100', **retained['full_metadata_options']}})
    if (datacite_receipt.get('source') != 'datacite' or datacite_receipt.get('complete') is not True
            or datacite_receipt.get('publication_dois') != publication_dois):
        raise ValueError('Matching completed DataCite generation and DOI population required')
    dc_until = datacite_receipt.get('until')
    if not isinstance(dc_until, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', dc_until):
        raise ValueError('Exact retained DataCite UTC cutoff required')
    datetime.fromisoformat(dc_until)
    for query in queries:
        query['parameters']['query'] = '(' + query['parameters']['query'] + ') AND created:[* TO "' + dc_until + '"]'
    dc = {'source': 'datacite', 'kind': 'complete_discovery', 'queries': queries}
    if crossref_receipt.get('source') != 'crossref' or crossref_receipt.get('complete') is not True:
        raise ValueError('Completed retained Crossref cutoff evidence required')
    until = crossref_receipt['until']
    if not isinstance(until, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', until):
        raise ValueError('Exact retained UTC cutoff required')
    datetime.fromisoformat(until)
    crossref_ids = validate_dois(crossref_receipt['source_dois'])
    if len(crossref_ids) != crossref_receipt['source_doi_count'] or len(set(crossref_ids)) != len(crossref_ids):
        raise ValueError('Complete Crossref supplementary DOI inventory required')
    cr = {'source': 'crossref', 'kind': 'complete_discovery', 'queries': [
        {'key': q['key'], 'parameters': {'query.affiliation': q['anchor'], 'rows': '500',
         'filter': 'until-created-date:' + until[:-1]}} for q in hedge['queries']]}
    for scope in (ct, dc, cr):
        validate_scope(scope)
    return {'clinicaltrials-discovery.json': ct,
            'clinicaltrials-supplementary-ids.json': ids,
            'datacite-complete-discovery.json': dc,
            'crossref-discovery.json': cr,
            'crossref-supplementary-dois.json': crossref_ids,
            'scope-receipt.json': {
                'kind': 'source-discovery-scope-package-v1', 'provider_calls': 0, 'native_calls': 0,
                'crossref_hedge_revision': hedge['revision'],
                'crossref_disabled_queries': hedge['disabled_queries'],
                'crossref_limitations': hedge['limitations'],
                'clinicaltrials_supplementary_ids': len(ids), 'datacite_publication_dois': len(publication_dois),
                'datacite_institutional_queries': len(retained['institutional_queries']),
                'datacite_related_queries': len(dc['queries']) - len(retained['institutional_queries']),
                'crossref_supplementary_dois': len(crossref_ids),
                'input_hashes': {k: scope_sha256(v) for k, v in {
                    'trials': trials, 'datacite': datacite, 'hedge': hedge, 'collector': collector,
                    'doi_snapshot': doi_snapshot, 'crossref_receipt': crossref_receipt,
                    'datacite_receipt': datacite_receipt}.items()},
                'complete_source_generation': False, 'deployment_ready': False,
                'remaining': ['Complete retained raw generation matching every discovery and supplementary scope',
                              'Bind independent source generations before consumer admission'],
            }}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('trials', 'datacite', 'hedge', 'collector', 'doi-snapshot', 'crossref-receipt', 'datacite-receipt', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    values = vars(args).copy(); output = values.pop('output')
    result = build(**{k: json.loads(v.read_bytes()) for k, v in values.items()})
    out = create_output(output)
    for name, value in result.items():
        with (out / name).open('xb') as stream:
            stream.write(json_bytes(value))
    print(json.dumps(result['scope-receipt.json']))


if __name__ == '__main__':
    main()
