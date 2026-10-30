"""Publish candidate PMID-to-grant references from the isolated retained consumer.

No award-register match, person merge or confirmed funding relationship is implied.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.consume_retained_pubmed import encoded, pinned, sha
from scripts.source_relationship_evidence import fingerprint, pubmed_projection


def project(consumer, publications):
    if (consumer.get('kind') != 'isolated_retained_pubmed_consumer_v1'
            or consumer.get('rows_sha256') != fingerprint(consumer['rows'])
            or consumer.get('publication_count') != len(consumer['rows'])):
        raise ValueError('Exact complete retained consumer required')
    records = []
    keys = []
    for row in consumer['rows']:
        pmid = row['summary']['PMID']
        keys.append(pmid)
        records.append(dict(pmid=pmid, metadata=row['metadata'],
                            metadata_sha256=fingerprint(row['metadata']),
                            source_version=consumer['batch'], observed_utc=consumer['observed_utc'],
                            complete=True, next_links=[], http_status=200))
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate retained publication')
    # This is a PMID-only join. Preserve the complete input digest separately;
    # unrelated DOI content is neither interpreted nor silently repaired here.
    join_rows = [{k: p.get(k, '') for k in ('CanonicalKey', 'PMID')} for p in publications]
    generation = dict(generation_id=consumer['generation'],
                      canonical_snapshot_id=fingerprint(publications),
                      source_snapshot_id=consumer['commit_sha256'], source='pubmed',
                      complete=True, next_links=[], source_count=len(records),
                      publication_count=len(publications), source_sha256=fingerprint(records),
                      publications_sha256=fingerprint(join_rows))
    # Reuse the existing identifier-based producer; retain every grant occurrence,
    # source path and unresolved namespace instead of inferring award identities.
    edges = [r for r in pubmed_projection(records, join_rows, generation=generation)
             if r['RelationshipKind'] == 'publication_grant_reference']
    return dict(kind='retained_pubmed_grant_references_v1', generation=generation,
                consumer_rows_sha256=consumer['rows_sha256'], edges=edges,
                complete_canonical_snapshot_sha256=fingerprint(publications),
                join_fields=['CanonicalKey', 'PMID'],
                edge_count=len(edges), publication_count=len(publications),
                mapped_publication_count=len({r['CanonicalKey'] for r in edges if r['CanonicalKey']}),
                confirmed_relationship_count=0, native_model_modified=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--consumer', required=True)
    p.add_argument('--consumer-sha256', required=True)
    p.add_argument('--publications-csv', required=True)
    p.add_argument('--publications-sha256', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    consumer = pinned(a.consumer, a.consumer_sha256)
    raw = Path(a.publications_csv).read_bytes()
    if sha(raw) != a.publications_sha256:
        raise ValueError('Independent canonical snapshot byte pin differs')
    publications = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline='')))
    result = project(consumer, publications)
    with Path(a.output).open('xb') as f:
        f.write(encoded(result))
    print(json.dumps({k: result[k] for k in ('edge_count', 'mapped_publication_count',
                                            'publication_count', 'confirmed_relationship_count')}))


if __name__ == '__main__':
    main()
