"""Pure candidate assertions from pinned, complete Crossref/ARDC captures.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, unquote, urlparse

if __package__:
    from scripts.award_identifier_crosswalks import qualify_award_alias, authority_contract, exact_text, identifier, validate_grant_records, governing_envelope
    from scripts.source_relationship_evidence import normalise_doi, fingerprint
    from scripts.plan_publication_stub_restore import strict_json_loads, utc
else:
    from award_identifier_crosswalks import qualify_award_alias, authority_contract, exact_text, identifier, validate_grant_records, governing_envelope
    from source_relationship_evidence import normalise_doi, fingerprint
    from plan_publication_stub_restore import strict_json_loads, utc


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Caller-pinned SHA256 required')
    return value


def _count(value, expected):
    if type(value) is not int or value < 0 or value != expected:
        raise ValueError('Exact actual-integer count or length required')


def _doi(value):
    exact_text(value)
    normalized = normalise_doi(value)
    if not normalized:
        raise ValueError('Exact DOI identity required')
    return normalized


def _observed(query):
    if 'observed_utc' not in query:
        raise ValueError('Explicit observation time or unknown null required')
    if query['observed_utc'] is not None:
        if not isinstance(query['observed_utc'],str):raise ValueError('Observation time must be text or unknown null')
        utc(query['observed_utc'])
    return query['observed_utc']


def _complete(query):
    governing_envelope(query)
    if (query.get('complete') is not True or query.get('next_links') != []
            or type(query.get('http_status')) is not int or query['http_status'] != 200):
        raise ValueError('Successful complete unpaged query required')
    _observed(query)


def _capture(folder, expected_manifest_sha256):
    folder = Path(folder)
    if folder.is_symlink():
        raise ValueError('Symlink capture root refused')
    root = folder.resolve()
    manifest_path = root / 'manifest.json'
    if manifest_path.is_symlink():
        raise ValueError('Symlink manifest refused')
    raw = manifest_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != _sha(expected_manifest_sha256):
        raise ValueError('Independent manifest pin mismatch')
    manifest = strict_json_loads(raw)
    governing_envelope(manifest)
    if (not isinstance(manifest, dict) or manifest.get('kind') != 'publication_award_crosswalk_retention_v1'
            or manifest.get('complete') is not True or manifest.get('next_links') != []
            or manifest.get('namespace') != 'nhmrc'):
        raise ValueError('Complete retained NHMRC crosswalk manifest required')
    exact_text(manifest.get('batch'))
    files = manifest.get('files')
    if not isinstance(files, list):
        raise ValueError('Explicit file inventory required')
    _count(manifest.get('file_count'), len(files))
    payloads = {}
    for entry in files:
        if not isinstance(entry, dict):
            raise ValueError('Structured file inventory required')
        name = exact_text(entry.get('name'))
        if (Path(name).name != name or '/' in name or '\\' in name or name in {'.', '..', 'manifest.json'}
                or name in payloads):
            raise ValueError('Duplicate or unsafe retained filename')
        path = root / name
        if path.is_symlink() or not path.is_file() or path.resolve().parent != root:
            raise ValueError('Contained regular source files required')
        captured = path.read_bytes()
        _count(entry.get('bytes'), len(captured))
        if hashlib.sha256(captured).hexdigest() != _sha(entry.get('sha256')):
            raise ValueError('Retained source hash drift')
        payloads[name] = (entry, strict_json_loads(captured))
    if {p.name for p in root.iterdir()} != set(payloads) | {'manifest.json'}:
        raise ValueError('Complete exact capture file inventory required')
    return manifest, payloads


def project_packet(folder, publications, *, expected_manifest_sha256,
                   authority_binding, authority_binding_sha256, generation):
    """Caller pins must come from independent retained evidence, not this folder.

    Complete means this declared input scope; it never proves institutional
    completeness, review, current grant status or that funding caused an output.
    """
    authority = authority_contract(authority_binding, authority_binding_sha256)
    manifest, payloads = _capture(folder, expected_manifest_sha256)
    publications, generation = copy.deepcopy((publications, generation))
    if not isinstance(publications, list) or not isinstance(generation, dict):
        raise ValueError('Caller-bound canonical generation required')
    governing_envelope(generation)
    for key in ('generation_id', 'canonical_snapshot_id'):
        exact_text(generation.get(key))
    if (generation.get('complete') is not True or generation.get('next_links') != []
            or generation.get('source_snapshot_id') != manifest['batch']
            or generation.get('manifest_sha256') != expected_manifest_sha256
            or generation.get('publications_sha256') != fingerprint(publications)):
        raise ValueError('Incomplete or unbound canonical/source generation')
    _count(generation.get('publication_count'), len(publications))
    index, canonical_keys = {}, set()
    for row in publications:
        if not isinstance(row, dict):
            raise ValueError('Structured canonical records required')
        key = exact_text(row.get('CanonicalKey'))
        if key in canonical_keys:
            raise ValueError('Duplicate canonical identity')
        canonical_keys.add(key)
        pmid = row.get('PMID')
        if pmid not in (None, '') and (not isinstance(pmid, str) or not re.fullmatch('[1-9][0-9]*', pmid)):
            raise ValueError('Exact ASCII positive PMID text required')
        if row.get('DOI') not in (None, ''):
            index.setdefault(_doi(row['DOI']), set()).add(key)
    crossref, ardc = manifest.get('crossref'), manifest.get('ardc')
    if not isinstance(crossref, list) or not isinstance(ardc, list):
        raise ValueError('Complete query inventories required')
    for kind, queries in (('crossref', crossref), ('ardc', ardc)):
        _count(manifest.get(kind + '_count'), len(queries))
        _count(generation.get(kind + '_count'), len(queries))
    used = set()
    def read_reference(reference, name_key):
        if not isinstance(reference, dict):
            raise ValueError('Structured exact file reference required')
        name = reference.get(name_key)
        if not isinstance(name, str) or name not in payloads or name in used:
            raise ValueError('Missing, repeated or overlapping source reference')
        entry, value = payloads[name]
        if reference.get('sha256') != entry['sha256']:
            raise ValueError('Referenced provenance hash drift')
        if 'bytes' in reference:_count(reference['bytes'],entry['bytes'])
        used.add(name)
        return value
    raw_authority = read_reference(manifest.get('authority'), 'name')
    if (manifest['namespace'] != authority['namespace']
            or manifest['authority']['sha256'] != authority['authority_raw_sha256']
            or not isinstance(raw_authority, dict) or any(k in raw_authority for k in ('error','errors')) or raw_authority.get('id') != authority['ror']):
        raise ValueError('Independent raw authority and namespace binding mismatch')
    websites = raw_authority.get('links')
    external = raw_authority.get('external_ids')
    if (not isinstance(websites, list) or not isinstance(external, list)
            or not any(isinstance(r, dict) and r.get('type') == 'website'
                       and r.get('value') == 'https://www.nhmrc.gov.au/' for r in websites)):
        raise ValueError('Exact NHMRC source authority required')
    funders = set()
    for record in external:
        if not isinstance(record, dict):
            raise ValueError('Structured authority external IDs required')
        if record.get('type') == 'fundref':
            ids = record.get('all')
            if not isinstance(ids, list):
                raise ValueError('Explicit authority FundRef array required')
            for value in ids:
                exact_text(value)
                normalized=_doi('10.13039/' + value)
                if normalized in funders:raise ValueError('Duplicate authority FundRef identity')
                funders.add(normalized)
    if funders != set(authority['fundref_dois']):
        raise ValueError('Independent FundRef/ROR binding mismatch')
    lookups = {}
    for query in ardc:
        _complete(query)
        number = identifier(query.get('original_identifier'))
        if number in lookups:
            raise ValueError('Duplicate grant lookup identity')
        url = urlparse(exact_text(query.get('url')))
        if (url.scheme != 'https' or url.netloc != 'researchdata.edu.au'
                or url.path != '/api/v2.0/registry/activities' or url.fragment
                or parse_qs(url.query, keep_blank_values=True) != {'identifier': [number]}):
            raise ValueError('Exact retained ARDC query identity required')
        response = read_reference(query, 'filename')
        if (not isinstance(response, dict) or 'error' in response or 'errors' in response
                or response.get('status') != 'OK' or response.get('code') != '200'):
            raise ValueError('Successful grant response required')
        data = response.get('data')
        if not isinstance(data, dict) or not isinstance(data.get('records'), list):
            raise ValueError('Complete grant record array required')
        _count(data.get('offset'), 0)
        _count(data.get('numFound'), len(data['records']))
        if any(part.get(k) is not None for part in (response,data) for k in ('next','nextLink','@odata.nextLink','odata.nextLink')):
            raise ValueError('Grant pagination remains incomplete')
        if any(k in data for k in ('error','errors')):raise ValueError('Failed grant payload')
        # Validate every captured record even if no selected Crossref claim uses it.
        validate_grant_records(data['records'])
        lookups[number] = (query, data['records'])
    result, seen_dois = {}, set()
    for query in crossref:
        _complete(query)
        doi = _doi(query.get('doi'))
        if doi in seen_dois:
            raise ValueError('Duplicate publication query identity')
        seen_dois.add(doi)
        url = urlparse(exact_text(query.get('url')))
        if (url.scheme != 'https' or url.netloc != 'api.crossref.org' or url.query or url.fragment
                or not url.path.startswith('/works/') or _doi(unquote(url.path[len('/works/'):])) != doi):
            raise ValueError('Exact retained Crossref query identity required')
        response = read_reference(query, 'filename')
        work = response.get('message') if isinstance(response, dict) else None
        if (not isinstance(work, dict) or response.get('status') != 'ok'
                or any(k in part for part in (response,work) for k in ('error','errors')) or _doi(work.get('DOI')) != doi):
            raise ValueError('Publication response identity or status drift')
        funding = work.get('funder', [])
        if not isinstance(funding, list):
            raise ValueError('Structured source funder array required')
        for funder_index, funder in enumerate(funding):
            if not isinstance(funder, dict):
                raise ValueError('Structured source funder required')
            if funder.get('DOI') in (None, ''):
                continue
            fid = _doi(funder['DOI'])
            if fid not in funders:
                continue
            numbers = funder.get('award', [])
            if not isinstance(numbers, list):
                raise ValueError('Explicit award identifier array required')
            for award_index, number in enumerate(numbers or [None]):
                if number is not None and number != '':
                    identifier(number)
                lookup, records = lookups.get(number, (None, []))
                match = qualify_award_alias({'funder_award_id': number}, None, authority, records,
                    authority_sha256=authority_binding_sha256, source_funder_doi=fid)
                if lookup is None and number not in (None, ''):
                    match['state'] = 'missing_retained_grant_lookup'
                state = match['state']
                unique = state == 'source_supported_alias'
                uri = match['matches'][0]['award_uri'] if unique else ''
                source, keys = 'crossref:' + doi, index.get(doi, set())
                kind = 'publication_award_crosswalk' if unique else 'publication_award_crosswalk_diagnostic'
                key = '|'.join([source, kind, 'doi:' + doi, fid, number or '', uri])
                path = '/message/funder/' + str(funder_index) + '/award/' + str(award_index) if numbers else '/message/funder/' + str(funder_index) + '/award'
                provenance = dict(relationship='explicit_publication_award_identifier', funderDOI=fid,
                    sourceFunderDOIRaw=funder['DOI'],requestedDOIRaw=query['doi'],returnedDOIRaw=work['DOI'],
                    awardNumber=number, ardcRawSHA256=lookup['sha256'] if lookup else None,
                    ardcSourceURL=lookup['url'] if lookup else None, ardcObservedUTC=lookup['observed_utc'] if lookup else None,
                    authorityROR=authority['ror'], authorityRawSHA256=authority['authority_raw_sha256'],
                    authorityBindingSHA256=authority_binding_sha256)
                row = dict(EvidenceKey=key, RelationshipKind=kind, SourceWorkID=source,
                    PublicationDOI=doi, PublicationPMID='', ReferenceType=json.dumps(provenance, separators=(',', ':'), ensure_ascii=False),
                    FromKey='doi:' + doi, ToKey=uri, FromLabel=fid, ToLabel=number,
                    ORCID='', ORCIDStatus='Absent', ROR=authority['ror'], IdentityStatus='Source assertion; not qualified',
                    SourceURL=query['url'], ObservedUTC=query['observed_utc'], RawSHA256=query['sha256'],
                    SourceVersion=expected_manifest_sha256, SourceVersionKind='retained_manifest_sha256', SourceBatch=manifest['batch'], ReviewState='Not reviewed', AuthenticationState='Not authenticated',
                    SourceProvider='Crossref', CanonicalKey=next(iter(keys)) if len(keys) == 1 else '', CanonicalMatchCount=len(keys),
                    AdmissionState='Ambiguous DOI' if len(keys) > 1 else 'Unmapped publication' if not keys else 'Candidate only',
                    AliasState=state, AliasMatches=match['matches'], Confidence='candidate', IdentityQualified=False,
                    CanonicalAdmission=False, MutationAuthorized=False, NativeG06Admission=False,
                    GenerationID=generation['generation_id'], CanonicalSnapshotID=generation['canonical_snapshot_id'],
                    SourceSnapshotID=manifest['batch'], SourceManifestSHA256=expected_manifest_sha256,
                    CanonicalInputSHA256=generation['publications_sha256'],AuthorityBindingSHA256=authority_binding_sha256,
                    ProjectionRevisionSHA256=fingerprint([expected_manifest_sha256,authority_binding_sha256,generation['publications_sha256']]))
                if key in result:
                    before = {k: v for k, v in result[key].items() if k != 'SourcePaths'}
                    if before != row:
                        raise ValueError('Conflicting repeated source assertion')
                    result[key]['SourcePaths'].append(path)
                else:
                    result[key] = {**row, 'SourcePaths': [path]}
    if used != set(payloads):
        raise ValueError('Unreferenced retained source inventory entries')
    return sorted(result.values(), key=lambda row: row['EvidenceKey'])
