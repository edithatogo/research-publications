"""Candidate aliases from independently pinned namespaces and exact identifiers.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
import re
from urllib.parse import urlparse

if __package__:
    from scripts.source_relationship_evidence import fingerprint
else:
    from source_relationship_evidence import fingerprint


def exact_text(value):
    if not isinstance(value, str) or not value or value != value.strip() or re.search(r'[\x00-\x1f\x7f]',value):
        raise ValueError('Exact nonempty unpadded text required')
    return value


def identifier(value):
    exact_text(value)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', value) or value in {'.', '..'}:
        raise ValueError('Exact single-segment award identifier required')
    return value


def authority_contract(authority, expected_sha256):
    """A caller pin binds supplied authority; it is not proof of its authenticity."""
    if (not isinstance(expected_sha256, str) or not re.fullmatch('[0-9a-f]{64}', expected_sha256)
            or not isinstance(authority, dict) or fingerprint(authority) != expected_sha256
            or authority.get('complete') is not True):
        raise ValueError('Independent complete authority binding and SHA256 required')
    identifier(authority.get('namespace'))
    ror = exact_text(authority.get('ror'))
    if not re.fullmatch(r'https://ror\.org/[A-Za-z0-9]+',ror):
        raise ValueError('Exact authority ROR required')
    exact_text(authority.get('evidence_ref'))
    raw_hash = authority.get('authority_raw_sha256')
    if not isinstance(raw_hash, str) or not re.fullmatch('[0-9a-f]{64}', raw_hash):
        raise ValueError('Pinned raw authority hash required')
    fundrefs = authority.get('fundref_dois')
    if (not isinstance(fundrefs, list) or not fundrefs
            or any(not isinstance(f, str) or not re.fullmatch(r'10\.13039/[0-9]+', f) for f in fundrefs)
            or len(set(fundrefs)) != len(fundrefs)):
        raise ValueError('Exact unique authority FundRef DOI list required')
    return copy.deepcopy(authority)


def validate_grant_records(records):
    """Validate complete source shapes without manufacturing a funder identity."""
    if not isinstance(records,list):raise ValueError('Complete record array required')
    seen=set()
    for record in records:
        if not isinstance(record,dict):raise ValueError('Structured grant source record required')
        record_id=exact_text(record.get('id'))
        if record_id in seen:raise ValueError('Duplicate grant source record identity')
        seen.add(record_id)
        exact_text(record.get('type'))
        if record['type']!='grant':continue
        exact_text(record.get('purl'))
        values=record.get('identifiers')
        if not isinstance(values,list):raise ValueError('Explicit identifier array required; no substring matching')
        for value in values:exact_text(value)
        if len(values)!=len(set(values)):raise ValueError('Duplicate explicit grant identifiers')


def qualify_award_alias(award, source_funder_ror, authority, records, *,
                        authority_sha256, source_funder_doi=None):
    """Match source ROR or raw FundRef DOI through an independently pinned binding.

    Search results, checksum/URL validity and these supplied bindings never
    establish human review, institutional attribution or positive funding facts.
    """
    authority = authority_contract(authority, authority_sha256)
    if not isinstance(award, dict) or not isinstance(records, list):
        raise ValueError('Structured award and complete record array required')
    validate_grant_records(records)
    result = dict(state='no_exact_identifier', matches=[], confidence='candidate',
                  identity_qualified=False, canonical_admission=False, mutation_authorized=False)
    number = award.get('funder_award_id')
    if number is None or number == '':
        return {**result, 'state': 'missing_award_number'}
    identifier(number)
    if source_funder_ror is not None:
        exact_text(source_funder_ror)
    if source_funder_doi is not None:
        exact_text(source_funder_doi)
    # Crossref supplies FundRef, not a ROR invented from the authority record.
    qualified = (source_funder_ror == authority['ror'] if source_funder_ror is not None
                 else source_funder_doi in authority['fundref_dois'])
    if (not qualified or (source_funder_doi is not None
                         and source_funder_doi not in authority['fundref_dois'])):
        return {**result, 'state': 'unqualified_funder_namespace'}
    matches = []
    for record in records:
        if record['type'] != 'grant':continue
        record_id=record['id'];uri=record['purl'];identifiers=record['identifiers']
        parsed = urlparse(uri)
        expected = '/au-research/grants/' + authority['namespace'] + '/' + number
        if (parsed.scheme == 'https' and parsed.netloc == 'purl.org'
                and parsed.path == expected and uri == 'https://purl.org' + expected and not parsed.query and not parsed.fragment
                and number in identifiers):
            matches.append({'record_id': record_id, 'award_uri': uri})
    matches.sort(key=lambda row: (row['award_uri'], row['record_id']))
    return {**result, 'state': 'source_supported_alias' if len(matches) == 1
            else 'ambiguous_award_identifier' if matches else 'no_exact_identifier',
            'matches': matches}
