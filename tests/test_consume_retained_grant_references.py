import copy
import unittest

from scripts.consume_retained_grant_references import project
from scripts.source_relationship_evidence import fingerprint
from tests.test_source_relationship_evidence import node, pm_record


class GrantConsumerTests(unittest.TestCase):
    def consumer(self):
        grants = [node('Grant', [node('GrantID', '123'), node('Agency', agency),
                                node('Country', 'Australia')]) for agency in ['One', 'Two', '']]
        record = pm_record([], grants=grants)
        rows = [dict(summary={'PMID': '13'}, metadata=record['metadata'])]
        return dict(kind='isolated_retained_pubmed_consumer_v1', rows=rows,
                    publication_count=1, rows_sha256=fingerprint(rows), batch='batch',
                    generation='generation', commit_sha256='a' * 64,
                    observed_utc='2026-10-21T20:04:50Z')

    def test_identifiers_provenance_candidate_state_and_filter(self):
        consumer = self.consumer()
        before = copy.deepcopy(consumer)
        result = project(consumer, [{'CanonicalKey': 'pub:13', 'PMID': '13', 'DOI': 'retained unrelated invalid DOI'}])
        self.assertEqual(result['edge_count'], 3)
        self.assertEqual(len({r['ToKey'] for r in result['edges']}), 3)
        self.assertEqual(result['mapped_publication_count'], 1)
        self.assertTrue(all(r['SourcePaths'] and r['StructuredMetadataSHA256']
                            and not r['CanonicalAdmission'] and not r['MutationAuthorized']
                            for r in result['edges']))
        self.assertEqual(sum(r['IdentityStatus'] == 'Unresolved award namespace'
                             for r in result['edges']), 1)
        self.assertEqual(consumer, before)

    def test_ambiguous_mapping_is_held_and_drift_is_rejected(self):
        consumer = self.consumer()
        result = project(consumer, [{'CanonicalKey': k, 'PMID': '13'} for k in ['a', 'b']])
        self.assertTrue(all(r['CanonicalKey'] == '' and r['CanonicalMatchCount'] == 2
                            for r in result['edges']))
        consumer['rows'][0]['summary']['PMID'] = '14'
        with self.assertRaises(ValueError):
            project(consumer, [])
