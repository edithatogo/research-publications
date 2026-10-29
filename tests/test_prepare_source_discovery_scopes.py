import copy
import json
import unittest
from pathlib import Path

from scripts.prepare_source_discovery_scopes import build


class SourceScopeTests(unittest.TestCase):
    def args(self):
        return {'trials': {'properties': {'definition': {'actions': {
            'Acquisition_scope': {'inputs': {'query_term': 'AREA[LocationCountry]Australia'}},
            'Requested_ids': {'inputs': ['NCT00000001']}}}}},
            'datacite': {'properties': {'definition': {'actions': {'Scope': {'inputs': {
                'full_metadata_options': {'detail': 'true', 'affiliation': 'true', 'publisher': 'true'},
                'institutional_queries': [{'key': 'institutional-0', 'query': 'creators.affiliation.name:"Fictional"'}],
                'related_dois_per_query': 20}}}}}},
            'hedge': json.loads(Path('config/crossref-acquisition-hedge.json').read_bytes()),
            'collector': json.loads(Path('config/collector.json').read_bytes()),
            'doi_snapshot': {'publication_dois': [f'10.5555/fixture-{i}' for i in range(21)]},
            'datacite_receipt': {'source': 'datacite', 'complete': True, 'until': '2026-10-18T00:00:00Z',
                                 'publication_dois': [f'10.5555/fixture-{i}' for i in range(21)]},
            'crossref_receipt': {'source': 'crossref', 'complete': True, 'until': '2026-10-28T00:00:00Z',
                                 'source_dois': ['10.5555/one'], 'source_doi_count': 1}}

    def test_discovery_and_supplementary_population_both_preserved(self):
        args = self.args(); before = copy.deepcopy(args); out = build(**args)
        self.assertEqual(args, before)
        queries = out['datacite-complete-discovery.json']['queries']
        self.assertEqual(len(queries), 3)
        self.assertEqual(queries[0]['parameters']['query'], '(creators.affiliation.name:"Fictional") AND created:[* TO "2026-10-18T00:00:00Z"]')
        self.assertEqual(out['clinicaltrials-supplementary-ids.json'], ['NCT00000001'])
        self.assertEqual(len(out['crossref-discovery.json']['queries']), len(args['hedge']['queries']))
        self.assertFalse(out['scope-receipt.json']['complete_source_generation'])

    def test_incomplete_population_metadata_and_qualifier_refused(self):
        for variant in ('duplicate', 'missing_institution', 'metadata', 'incomplete_crossref', 'count'):
            args = self.args()
            if variant == 'duplicate': args['doi_snapshot']['publication_dois'].append('10.5555/fixture-0')
            elif variant == 'missing_institution': args['datacite']['properties']['definition']['actions']['Scope']['inputs']['institutional_queries'] = []
            elif variant == 'metadata': args['datacite']['properties']['definition']['actions']['Scope']['inputs']['full_metadata_options']['detail'] = 'false'
            elif variant == 'incomplete_crossref': args['crossref_receipt']['complete'] = False
            else: args['crossref_receipt']['source_doi_count'] = 2
            with self.subTest(variant=variant), self.assertRaises(ValueError): build(**args)
