"""Prepare exact ARC grant-ID candidates from retained data; never confirm funding."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.grants_relationships import normalize_relationship, validate_relationship_batch

MATCH_BASIS = 'exact_retained_grant_token_to_unique_arc_award_code'


def prepare_views(before, bindings=None):
    if before.get('complete') is not True or before['list']['ItemCount'] != len(before['items']):
        raise ValueError('Complete bridge preimage required')
    eq = lambda name, kind, value: f'<Eq><FieldRef Name="{name}" /><Value Type="{kind}">{value}</Value></Eq>'
    # Positive admission prevents free-text withdrawal/unknown values from entering
    # the candidate reader. Preserve them unchanged in All Items.
    for row in before['items']:
        status = row.get('ReviewStatus')
        if status is not None and (not isinstance(status, str) or status != status.strip()):
            raise ValueError('Padded or invalid review status requires explicit reader reconciliation; preserve raw history')
    candidate_status = '<Or>' + eq('ReviewStatus', 'Text', 'Needs Review') + eq('ReviewStatus', 'Text', 'Reviewed') + '</Or>'
    candidate = '<And>' + eq('RelationshipType', 'Choice', 'candidate_award_match') + '<And>' + eq('Confidence', 'Choice', 'candidate') + candidate_status + '</And></And>'
    confirmed = '<And>' + eq('RelationshipType', 'Choice', 'funded_by_award') + '<And>' + eq('Confidence', 'Choice', 'confirmed') + eq('ReviewStatus', 'Text', 'Reviewed') + '</And></And>'
    columns = ['LinkTitle', 'RelationshipType', 'AwardID', 'EvidenceURL', 'Confidence',
               'ReviewStatus', 'FromKey', 'ToKey', 'RelationshipKey', 'Modified']
    if not set(columns).issubset({f['InternalName'] for f in before['fields']}):
        raise ValueError('Existing bridge reader fields required')
    changes, expected = [], {}
    for role, title, predicate in [('candidates', 'Funding links | Candidates', candidate),
                                   ('confirmed', 'Funding links | Confirmed reviewed', confirmed)]:
        if bindings is None:
            if any(v['Title'] == title for v in before['views']):
                raise ValueError('Existing view requires exact accepted GUID binding')
            identity = None
        else:
            if set(bindings) != {'candidates', 'confirmed'}:
                raise ValueError('Complete role-to-view GUID bindings required')
            matches = [v for v in before['views'] if v['Id'] == bindings[role]]
            if len(matches) != 1 or matches[0]['DefaultView'] or matches[0]['PersonalView']:
                raise ValueError('Exact nondefault native view required')
            identity = bindings[role]
        desired = {'Title': title, 'ViewQuery': '<Where>' + predicate + '</Where><OrderBy><FieldRef Name="ID" Ascending="FALSE" /></OrderBy>', 'Paged': True, 'RowLimit': 100}
        if identity:
            guard = {k: matches[0][k] for k in ['Id', 'Title', 'ViewQuery', 'DefaultView',
                     'PersonalView', 'Paged', 'RowLimit', 'ServerRelativeUrl']}
            guard['fields'] = matches[0]['resolvedFields']['Items']['results']
        else:
            guard = None
        changes.append({'role': role, 'id': identity, 'before': guard, 'desired': desired, 'fields': columns})
        expected[role] = sorted(r['Id'] for r in before['items'] if (
            r.get('RelationshipType') == 'candidate_award_match' and r.get('Confidence') == 'candidate'
            and (r.get('ReviewStatus') or '').casefold() in {'needs review', 'reviewed'}
            if role == 'candidates' else
            r.get('RelationshipType') == 'funded_by_award' and r.get('Confidence') == 'confirmed'
            and (r.get('ReviewStatus') or '').casefold() == 'reviewed'))
    return {'site_url': before['site_url'], 'list_id': before['list_id'],
            'changes': changes, 'expected_ids': expected, 'before_sha256': digest(before)}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def prepare(registry, publications, awards):
    if registry.get('complete') is not True or registry['list']['ItemCount'] != len(registry['items']):
        raise ValueError('Complete retained registry snapshot required')
    if len({r['Id'] for r in registry['items']}) != len(registry['items']):
        raise ValueError('Duplicate registry item IDs')
    pub_by_pmid = defaultdict(list)
    canonical_keys = []
    for row in publications:
        key = row.get('CanonicalKey')
        if not isinstance(key, str) or not key or key != key.strip():
            raise ValueError('Exact canonical publication key required')
        canonical_keys.append(key)
        if row.get('PMID'):
            if not isinstance(row['PMID'], str) or not row['PMID'].isdigit() or int(row['PMID']) <= 0:
                raise ValueError('Text positive PMID required')
            pub_by_pmid[row['PMID']].append(row)
    if len(set(canonical_keys)) != len(canonical_keys):
        raise ValueError('Duplicate canonical publication keys')
    by_code = defaultdict(list)
    sources = []
    seen = set()
    for row in awards:
        if row.get('RecordKind') != 'Award' or row.get('Source') != 'arc' or row.get('Funder') != 'Australian Research Council':
            raise ValueError('Accepted ARC award source required; no opportunity admission')
        identity, code = row.get('SourceID'), row.get('AwardCode')
        if not isinstance(identity, str) or not identity or identity != identity.strip() or identity in seen:
            raise ValueError('Unique exact award source ID required')
        if not isinstance(code, str) or not code or code != code.strip():
            raise ValueError('Exact source award code required')
        seen.add(identity); by_code[code].append(row)
        sources.append({'AwardKey': 'AWARD:arc:' + identity, 'AwardID': code,
                        'FunderKey': 'FUNDER:arc', 'AwardStatus': row.get('Status') or ''})
    registry_pubkeys = [r['field_2'] for r in registry['items'] if r.get('field_2')]
    pubkey_counts = Counter(registry_pubkeys)
    source_counts = Counter(r.get('field_1') for r in registry['items'] if r.get('field_1'))
    candidates, context, unresolved = [], [], []
    duplicate_tokens = 0
    for row in registry['items']:
        raw = row.get('GrantIDs') or ''
        if not isinstance(raw, str):
            raise ValueError('Retained GrantIDs must be text, not coerced')
        # Trim separator whitespace only. Never extract/fuzzy-match substrings,
        # change case, strip prefixes or join funder/name/topic similarities.
        tokens = [t.strip() for t in raw.split(';') if t.strip()]
        duplicate_tokens += len(tokens) - len(set(tokens))
        for token in sorted(set(tokens)):
            matches = by_code.get(token, [])
            if not matches:
                continue
            source_key, target = row.get('field_1'), row.get('field_2')
            reason = None
            if len(matches) != 1:
                reason = 'ambiguous_award_code'
            elif row.get('field_17') == 'Excluded':
                reason = 'publication_explicitly_excluded'
            elif not isinstance(source_key, str) or not source_key.startswith('pubmed:') or not source_key[7:].isdigit():
                reason = 'publication_source_key_unresolved'
            elif source_counts[source_key] != 1 or not isinstance(target, str) or not target.startswith('PUB:') or pubkey_counts[target] != 1:
                reason = 'publication_registry_identity_ambiguous'
            elif len(pub_by_pmid.get(source_key[7:], [])) != 1:
                reason = 'canonical_publication_identity_unresolved'
            if reason:
                unresolved.append({'RegistryItemID': row['Id'], 'GrantToken': token, 'Reason': reason})
                continue
            publication = pub_by_pmid[source_key[7:]][0]
            url = publication.get('PubMedURL')
            if not isinstance(url, str) or url != 'https://pubmed.ncbi.nlm.nih.gov/' + source_key[7:] + '/':
                raise ValueError('Exact PMID-bound source citation required')
            award = matches[0]
            parts = urlsplit(award.get('URL') or '')
            if parts.scheme != 'https' or parts.netloc != 'dataportal.arc.gov.au' or parts.path != '/NCGP/API/grants/' + award['SourceID']:
                raise ValueError('Exact ARC source citation required')
            candidate = {'RelationshipType': 'candidate_award_match',
                         'FromKey': 'AWARD:arc:' + award['SourceID'], 'ToKey': target,
                         'AwardID': token, 'EvidenceURL': url,
                         'Confidence': 'candidate', 'ReviewStatus': 'Needs Review'}
            candidates.append(candidate)
            context.append({'RegistryItemID': row['Id'], 'RegistryPublicationKey': target,
                            'PublicationCanonicalKey': publication['CanonicalKey'],
                            'PublicationSourceKey': source_key, 'PublicationTitle': publication.get('Title'),
                            'PublicationURL': url, 'AwardSourceID': award['SourceID'],
                            'AwardCode': token, 'AwardTitle': award.get('Title'),
                            'AwardStatus': award.get('Status'), 'AwardURL': award['URL'],
                            'Funder': award['Funder'], 'MatchBasis': MATCH_BASIS,
                            'RetainedGrantIDs': raw, 'RetainedFunderLabels': row.get('FunderNames'),
                            'RegistryRowSHA256': digest(row), 'AwardRowSHA256': digest(award),
                            'CanonicalRowSHA256': digest(publication)})
    validated = validate_relationship_batch(candidates, publication_keys=registry_pubkeys,
        opportunity_keys=[], award_sources=sources, affiliation_sources={})
    if validated['rejected']:
        raise ValueError('Typed candidate validation failed: ' + json.dumps(validated['rejected']))
    for row, link in zip(context, validated['validated'], strict=True):
        row.update(link)
    return {'kind': 'retained_arc_publication_relationship_candidates_v1',
            'relationships': validated['validated'], 'context': context, 'unresolved': unresolved,
            'coverage': {'registry_rows': len(registry['items']), 'canonical_publications': len(publications),
                         'arc_awards': len(awards), 'exact_candidates': len(context),
                         'duplicate_retained_tokens_collapsed': duplicate_tokens,
                         'confirmed_funding': 0, 'opportunity_links': 0},
            'input_hashes': {'registry': digest(registry), 'publications': digest(publications), 'awards': digest(awards)},
            'boundaries': ['Candidates are retained-ID matches, not reviewed funding or paired funder evidence',
                           'Registry PUB keys are preserved; explicit canonical crosswalk is context, not a rekey',
                           'QGIP candidates are not canonical opportunities; no source evidence means no relationship',
                           'Missing source records do not retire relationships; replay must preserve native review/withdrawal history'],
            'native_acceptance': False}


def prepare_identity_material(native, accepted):
    """Register exact hash material for supported type transitions, never review state."""
    material = {}
    for context in accepted['context']:
        identity = (context['FromKey'], context['ToKey'], context['AwardID'])
        urls = {context['EvidenceURL']}
        for row in native['items']:
            if (row.get('FromKey'), row.get('ToKey'), row.get('AwardID')) == identity:
                value = row.get('EvidenceURL')
                value = value.get('Url') if isinstance(value, dict) else value
                if isinstance(value, str) and value and value == value.strip():
                    urls.add(value)
        for url in sorted(urls):
            for kind, confidence, status in [('candidate_award_match', 'candidate', 'Needs Review'),
                                              ('funded_by_award', 'confirmed', 'Reviewed')]:
                try:
                    typed = normalize_relationship({'RelationshipType': kind,
                        'FromKey': identity[0], 'ToKey': identity[1], 'AwardID': identity[2],
                        'EvidenceURL': url, 'Confidence': confidence, 'ReviewStatus': status})
                except ValueError:
                    continue  # Invalid native evidence remains raw/unclassified, never repaired.
                row = {k: typed[k] for k in ['RelationshipKey', 'RelationshipType', 'FromKey',
                                             'ToKey', 'AwardID', 'EvidenceURL']}
                row.update(PublicationCanonicalKey=context['PublicationCanonicalKey'],
                           AwardSourceID=context['AwardSourceID'])
                key = row['RelationshipKey']
                if key in material and material[key] != row:
                    raise ValueError('Ambiguous typed relationship identity material')
                material[key] = row
    return [material[k] for k in sorted(material)]


def prepare_consumer(native, accepted):
    """Project current native state; accepted context supplies identities only.

    This is a local preparation/readback packet, never an authoritative runtime
    replacement for the live list or an instruction to update its human fields.
    """
    if native.get('complete') is not True or native['list']['ItemCount'] != len(native['items']):
        raise ValueError('Complete current native relationship snapshot required')
    if len({r['Id'] for r in native['items']}) != len(native['items']):
        raise ValueError('Duplicate native item identity')
    keys = [r.get('RelationshipKey') for r in native['items']]
    if any(not isinstance(k, str) or not k for k in keys) or len(set(keys)) != len(keys):
        raise ValueError('Unique native relationship keys required')
    identities = defaultdict(list)
    award_sources = {}
    for row in accepted['context']:
        identities[(row['FromKey'], row['ToKey'], row['AwardID'])].append(row)
        source = {'AwardKey': row['FromKey'], 'AwardID': row['AwardID'],
                  'FunderKey': 'FUNDER:arc', 'AwardStatus': row['AwardStatus']}
        award_sources[digest(source)] = source
    typed_rows = []
    for row in native['items']:
        evidence = row.get('EvidenceURL')
        typed_rows.append({**{k: row.get(k) for k in ['RelationshipKey', 'RelationshipType',
                           'FromKey', 'ToKey', 'AwardID', 'Confidence', 'ReviewStatus']},
                           'EvidenceURL': evidence.get('Url') if isinstance(evidence, dict) else evidence})
    validation = validate_relationship_batch(typed_rows,
        publication_keys=sorted({r['ToKey'] for r in accepted['context']}),
        opportunity_keys=[], award_sources=list(award_sources.values()), affiliation_sources={})
    valid_keys = {r['RelationshipKey'] for r in validation['validated']}
    rows = []
    for row in native['items']:
        matches = identities.get((row.get('FromKey'), row.get('ToKey'), row.get('AwardID')), [])
        context = matches[0] if len(matches) == 1 else None
        raw_status = row.get('ReviewStatus')
        canonical_status = (raw_status.casefold() if isinstance(raw_status, str)
                            and raw_status == raw_status.strip() else None)
        state = 'unclassified'
        if not context:
            state = 'unresolved_identity'
        elif (row['RelationshipKey'] in valid_keys
              and row.get('RelationshipType') == 'candidate_award_match'
              and row.get('Confidence') == 'candidate'
              and canonical_status in {'needs review', 'reviewed'}):
            state = 'candidate'
        elif (row['RelationshipKey'] in valid_keys
              and row.get('RelationshipType') == 'funded_by_award'
              and row.get('Confidence') == 'confirmed' and canonical_status == 'reviewed'):
            state = 'confirmed_reviewed'
        rows.append({
            'NativeItemID': row['Id'], 'RelationshipKey': row['RelationshipKey'],
            'FromKey': row.get('FromKey'), 'ToKey': row.get('ToKey'),
            'AwardID': row.get('AwardID'), 'RelationshipType': row.get('RelationshipType'),
            'Confidence': row.get('Confidence'), 'ReviewStatusRaw': raw_status,
            'EvidenceURLRaw': row.get('EvidenceURL'), 'NativeModified': row.get('Modified'),
            'NativeETag': row.get('__metadata', {}).get('etag'),
            'PublicationCanonicalKey': context['PublicationCanonicalKey'] if context else None,
            'AwardSourceID': context['AwardSourceID'] if context else None,
            'PublicationURL': context['PublicationURL'] if context else None,
            'AwardURL': context['AwardURL'] if context else None,
            'AdmissionState': state,
        })
    counts = Counter(r['AdmissionState'] for r in rows)
    return {'kind': 'current_native_funding_relationship_consumer_v1', 'rows': rows,
            'identity_material': prepare_identity_material(native, accepted),
            'coverage': {'native_rows': len(rows), 'candidates': counts['candidate'],
                         'confirmed_reviewed': counts['confirmed_reviewed'],
                         'unclassified': counts['unclassified'],
                         'unresolved_identity': counts['unresolved_identity']},
            'native_snapshot_sha256': digest(native), 'identity_context_sha256': digest(accepted),
            'observed_at_utc': native.get('observedAtUTC'),
            'runtime_requirement': 'Read current native list on the supported Microsoft refresh path; never substitute candidate packet review values',
            'native_acceptance': False}


def query_rows(path):
    envelope = json.loads(path.read_text())
    if envelope.get('status') != 'Success':
        raise ValueError('Accepted native query envelope required')
    data = envelope['result']['data']
    if len(data) != 1 or data[0]['status_code'] != 200:
        raise ValueError('Single successful native query required')
    return data[0]['text']['results'][0]['tables'][0]['rows']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--registry', type=Path, required=True)
    p.add_argument('--publications', type=Path, required=True)
    p.add_argument('--award-pages', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--native-relationships', type=Path,
                   help='Project current native review state using accepted identities; local preparation only')
    a = p.parse_args()
    pages = list(a.award_pages.glob('awards-page-*-readback-private.json'))
    by_number = {int(path.name.split('-')[2]): path for path in pages}
    if len(pages) != 35 or set(by_number) != set(range(1, 36)):
        raise ValueError('Complete accepted 35-page ARC query snapshot required')
    award_rows = [r for n in range(1, 36) for r in query_rows(by_number[n])]
    publications = [{k.removeprefix('Publication[').removesuffix(']'): v for k, v in r.items()}
                    for r in query_rows(a.publications)]
    awards = [{k.removeprefix('[').removesuffix(']'): v for k, v in r.items()} for r in award_rows]
    if len(awards) != 34977 or len(publications) != 1341:
        raise ValueError('Accepted source-generation counts required')
    result = prepare(json.loads(a.registry.read_text()), publications, awards)
    if a.native_relationships:
        result = prepare_consumer(json.loads(a.native_relationships.read_text()), result)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    if a.output.exists():
        raise ValueError('Preserve previous candidate packet; choose a distinct output')
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result['coverage']))


if __name__ == '__main__':
    main()
