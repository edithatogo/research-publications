"""Focused generation, byte and complete-metadata consumer boundaries."""
import copy
import json

import unittest

from scripts.consume_retained_pubmed import consume, encoded, sha


def packet():
    batch = 'test-batch'
    metadata = json.dumps([{'Name': 'MedlineCitation', 'Value': []}]).encode().hex()
    tables = {
        'PubMedPublications': [{'[PMID]': '1', '[Title]': 'Retained'}],
        'PubMedMetadataChunks': [{'[PMID]': '1', '[ChunkIndex]': 0,
                                 '[ChunkCount]': 1, '[MetadataChunk]': metadata,
                                 '[MetadataCharacters]': len(metadata), '[Encoding]': 'UTF8-HEX'}],
        'PubMedAuthorEvidence': [{'[PMID]': '1', '[AuthorIndex]': 1, '[AffiliationIndex]': 1}],
    }
    files, entries = {}, []
    for table, rows in tables.items():
        name = f'uncommitted-{batch}-{table}-0.json'
        files[name] = encoded(rows)
        entries.append(dict(name=name, table=table, http=200, rows=len(rows),
                            bytes=len(files[name]), sha256=sha(files[name])))
    raw = dict(all_files_http200_length_sha256_and_exact_bytes=True,
               all_expected_members_present=True, batch=batch, source_request='generation',
               RawObservation={'Version': 1})
    commit = dict(Status='committed', SchemaVersion=1, BatchID=batch,
                  Generation='generation', ObservedAtUTC='2026-10-21T20:04:50Z',
                  Validation=dict(Keysets=True, Metadata=True, RefreshGeneration=True),
                  RawObservation=raw['RawObservation'], Sources=[dict(Source='PubMed',
                  PublicationTable='PubMedPublications', PublicationPageCount=1,
                  ChunkTable='PubMedMetadataChunks', PageCount=1,
                  ExpectedRecords=1, ExpectedKeys=['1'])])
    content = encoded(commit)
    receipt = dict(state='complete', errors=[], receipts=entries,
                   marker=dict(name=f'commit-{batch}.json', http=200, content=content.decode(),
                               bytes=len(content), sha256=sha(content)))
    return receipt, raw, files


class ConsumerTests(unittest.TestCase):
    def test_complete_consumer_preserves_all_evidence(self):
        receipt, raw, files = packet()
        before = copy.deepcopy((receipt, raw, files))
        result = consume(receipt, raw, files.__getitem__)
        self.assertEqual(result['publication_count'], 1)
        self.assertEqual(result['rows'][0]['summary'], {'PMID': '1', 'Title': 'Retained'})
        self.assertEqual(result['rows'][0]['metadata'][0]['Name'], 'MedlineCitation')
        self.assertEqual(len(result['author_evidence']), 1)
        self.assertIs(result['working_model_modified'], False)
        self.assertIs(result['canonical_admission'], False)
        self.assertEqual((receipt, raw, files), before)

    def test_rejects_drift(self):
        for drift in ['bytes', 'generation', 'missing-page', 'duplicate']:
            with self.subTest(drift=drift):
                receipt, raw, files = packet()
                if drift == 'bytes':
                    files[next(iter(files))] += b' '
                elif drift == 'generation':
                    raw['source_request'] = 'different'
                elif drift == 'missing-page':
                    receipt['receipts'] = receipt['receipts'][1:]
                else:
                    receipt['receipts'].append(receipt['receipts'][0])
                with self.assertRaises(ValueError):
                    consume(receipt, raw, files.__getitem__)
