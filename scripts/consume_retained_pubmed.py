"""Consume one accepted archive without refreshing or changing the working model.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.publication_source_metadata_contract import reconstruct_metadata_rows
from scripts.source_relationship_evidence import fingerprint


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode()


def consume(receipt, raw_acceptance, read):
    """The caller pins both accepted receipts independently of archive bytes."""
    if receipt.get('state') != 'complete' or receipt.get('errors') != []:
        raise ValueError('Complete typed-byte acceptance required')
    marker = receipt['marker']
    content = marker['content'].encode()
    if (marker['http'] != 200 or len(content) != marker['bytes']
            or sha(content) != marker['sha256']):
        raise ValueError('Committed marker bytes differ')
    commit = json.loads(content)
    batch = commit['BatchID']
    if (commit['Status'] != 'committed' or commit['SchemaVersion'] != 1
            or marker['name'] != 'commit-' + batch + '.json'
            or not all(commit['Validation'].get(k) is True
                       for k in ('Keysets', 'Metadata', 'RefreshGeneration'))
            or raw_acceptance.get('all_files_http200_length_sha256_and_exact_bytes') is not True
            or raw_acceptance.get('all_expected_members_present') is not True
            or raw_acceptance.get('batch') != batch
            or raw_acceptance.get('source_request') != commit['Generation']
            or raw_acceptance.get('RawObservation') != commit.get('RawObservation')):
        raise ValueError('Accepted raw/typed generation binding required')
    sources = commit['Sources']
    if len(sources) != 1 or sources[0]['Source'] != 'PubMed':
        raise ValueError('One explicit PubMed source required')
    source = sources[0]
    tables, names = {}, set()
    for entry in receipt['receipts']:
        name = entry['name']
        table = entry['table']
        if (name in names or Path(name).name != name
                or not name.startswith('uncommitted-' + batch + '-' + table + '-')
                or entry['http'] != 200):
            raise ValueError('Invalid or duplicate retained member')
        names.add(name)
        raw = read(name)
        if len(raw) != entry['bytes'] or sha(raw) != entry['sha256']:
            raise ValueError('Retained member byte drift')
        rows = json.loads(raw)
        if not isinstance(rows, list) or len(rows) != entry['rows']:
            raise ValueError('Retained member row drift')
        tables.setdefault(table, []).extend(rows)
    for table, count in ((source['PublicationTable'], source['PublicationPageCount']),
                         (source['ChunkTable'], source['PageCount'])):
        expected = {'uncommitted-' + batch + '-' + table + '-' + str(i) + '.json'
                    for i in range(count)}
        if {n for n in names if n.startswith('uncommitted-' + batch + '-' + table + '-')} != expected:
            raise ValueError('Incomplete retained page inventory')
    summary = tables['PubMedPublications']
    keys = [r['[PMID]'] for r in summary]
    if (len(keys) != source['ExpectedRecords'] or len(set(keys)) != len(keys)
            or sorted(keys) != sorted(source['ExpectedKeys'])):
        raise ValueError('Retained publication key drift')
    documents, _, _ = reconstruct_metadata_rows(tables['PubMedMetadataChunks'], 'PMID')
    if set(documents) != set(keys):
        raise ValueError('Full metadata key drift')
    authors = tables['PubMedAuthorEvidence']
    author_keys = [(r['[PMID]'], r['[AuthorIndex]'], r['[AffiliationIndex]']) for r in authors]
    if len(set(author_keys)) != len(author_keys) or any(k[0] not in documents for k in author_keys):
        raise ValueError('Author evidence key drift')
    rows = [{'summary': {k[1:-1]: v for k, v in r.items()},
             'metadata': json.loads(documents[r['[PMID]']])} for r in summary]
    return {'kind': 'isolated_retained_pubmed_consumer_v1', 'batch': batch,
            'generation': commit['Generation'], 'observed_utc': commit['ObservedAtUTC'],
            'publication_count': len(rows), 'rows': rows, 'author_evidence': authors,
            'rows_sha256': fingerprint(rows), 'commit_sha256': marker['sha256'],
            'typed_receipt_sha256': sha(encoded(receipt)),
            'raw_acceptance_sha256': sha(encoded(raw_acceptance)),
            'working_model_modified': False, 'canonical_admission': False}


def pinned(path, digest):
    raw = Path(path).read_bytes()
    if sha(raw) != digest:
        raise ValueError('Independent input pin differs')
    return json.loads(raw)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('receipt', 'raw-acceptance'):
        p.add_argument('--' + name, required=True)
        p.add_argument('--' + name + '-sha256', required=True)
    p.add_argument('--archive', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    receipt = pinned(a.receipt, a.receipt_sha256)
    raw = pinned(a.raw_acceptance, a.raw_acceptance_sha256)
    archive = Path(a.archive)
    result = consume(receipt, raw, lambda name: (archive / name).read_bytes())
    # Exclusive creation preserves prior output and all human/native state.
    with Path(a.output).open('xb') as f:
        f.write(encoded(result))
    print(json.dumps({'publication_count': result['publication_count'],
                      'author_evidence_count': len(result['author_evidence']),
                      'output_sha256': sha(encoded(result))}))


if __name__ == '__main__':
    main()
