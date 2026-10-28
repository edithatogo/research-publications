"""Project retained provider identities without name-based person resolution.

Local-only qualification: publication-time affiliations are source assertions,
not employment or partnerships. Provider-wide metrics are not inferred.
SPDX-License-Identifier: Apache-2.0
"""
from collections import defaultdict
from itertools import combinations
import re

try:
    from .dashboard_topics import objects, retained_work
except ImportError:
    from dashboard_topics import objects, retained_work


def provider_id(value, prefix):
    return isinstance(value, str) and re.fullmatch(
        r'https://openalex.org/' + prefix + r'[0-9]+', value) is not None


def build_researchers(publication_keys, observations, crosswalk):
    """One dated snapshot per provider work; exact supplied canonical crosswalk.

    Aliases remain per provider ID. ORCID assertions are retained without merging
    people. Repeated mentions retain author positions but count once per work.
    """
    keys = set(publication_keys)
    if not keys or any(not isinstance(k, str) or not k for k in keys):
        raise ValueError('Nonempty canonical publication domain required')
    selected = {}
    people = defaultdict(lambda: dict(labels=set(), orcids=set()))
    organisations = defaultdict(lambda: dict(labels=set(), rors=set()))
    authorships = []
    affiliations = []
    diagnostics = []
    person_works = defaultdict(set)
    institution_works = defaultdict(set)
    for envelope in observations:
        work = retained_work(envelope)
        work_id = work['id']
        identity = (envelope['raw_response_sha256'], envelope['observed_utc'])
        if work_id in selected:
            if selected[work_id] != identity:
                raise ValueError('Select one dated provider snapshot per work')
            continue
        selected[work_id] = identity
        mapped = crosswalk.get(work_id, [])
        if not isinstance(mapped, list) or any(k not in keys for k in mapped):
            raise ValueError('Crosswalk contains noncanonical publication keys')
        if not mapped:
            diagnostics.append(dict(work_id=work_id, reason='unmapped_provider_work'))
            continue
        provenance = dict(provider='OpenAlex', provider_work_id=work_id,
                          observed_utc=envelope['observed_utc'],
                          source_hash=envelope['raw_response_sha256'],
                          classification_version='openalex_identity_projection_v1')
        for ordinal, assertion in enumerate(objects(work, 'authorships'), 1):
            author = assertion.get('author') or {}
            if not isinstance(author, dict):
                raise ValueError('Unexpected author schema')
            person = author.get('id')
            resolved = provider_id(person, 'A')
            if resolved:
                people[person]  # Retain valid identifiers even without a label or alias.
                if author.get('display_name'):
                    people[person]['labels'].add(author['display_name'])
                if author.get('orcid'):
                    people[person]['orcids'].add(author['orcid'])
            else:
                diagnostics.append(dict(provenance, author_ordinal=ordinal,
                                        reason='unresolved_author_id', source_id=person,
                                        source_label=author.get('display_name')))
            institutions = objects(assertion, 'institutions')
            for key in sorted(set(mapped)):
                authorships.append(dict(provenance, publication_key=key,
                    person_key=person if resolved else None, author_ordinal=ordinal,
                    source_author_position=assertion.get('author_position'),
                    source_label=author.get('display_name'), source_orcid=author.get('orcid'),
                    identity_status='Source-supported' if resolved else 'Unresolved'))
                if resolved:
                    person_works[key].add(person)
                for institution in institutions:
                    entity = institution.get('id')
                    institution_resolved = provider_id(entity, 'I')
                    if institution_resolved:
                        organisations[entity]  # Unknown labels never remove valid identities.
                        if institution.get('display_name'):
                            organisations[entity]['labels'].add(institution['display_name'])
                        if institution.get('ror'):
                            organisations[entity]['rors'].add(institution['ror'])
                        institution_works[key].add(entity)
                    affiliations.append(dict(provenance, publication_key=key,
                        person_key=person if resolved else None, author_ordinal=ordinal,
                        institution_key=entity if institution_resolved else None,
                        source_institution_id=entity, source_label=institution.get('display_name'),
                        source_ror=institution.get('ror'),
                        identity_status='Source-supported' if institution_resolved else 'Unresolved',
                        relationship_type='publication_time_affiliation'))
    orcid_people = defaultdict(set)
    for key, item in people.items():
        if len(item['orcids']) > 1:
            diagnostics.append(dict(reason='multiple_orcids_for_provider_id',
                                    person_key=key, source_orcids=sorted(item['orcids'])))
        for orcid in item['orcids']:
            orcid_people[orcid].add(key)
    def dimension(items, alias_field):
        return [dict(entity_key=key, labels=sorted(item['labels']),
                     **{alias_field: sorted(item[alias_field])},
                     label_status='Conflicting labels' if len(item['labels']) > 1 else
                                  'Source label' if item['labels'] else 'Unknown label')
                for key, item in sorted(items.items())]
    for orcid, entities in sorted(orcid_people.items()):
        if len(entities) > 1:
            diagnostics.append(dict(reason='orcid_asserted_by_multiple_provider_ids',
                                    source_orcid=orcid, person_keys=sorted(entities)))
    def pairs(works):
        paired = defaultdict(set)
        for publication, entities in works.items():
            for a, b in combinations(sorted(entities), 2):
                paired[(a, b)].add(publication)
        return [dict(a=a, b=b, publication_keys=sorted(publications),
                     shared_publications=len(publications), repeat=len(publications) >= 2)
                for (a, b), publications in sorted(paired.items())]
    # Exact repeated affiliation assertions are not separate memberships.
    affiliations = list({tuple(sorted(row.items())): row for row in affiliations}.values())
    return dict(people=dimension(people, 'orcids'), organisations=dimension(organisations, 'rors'),
                authorships=authorships, affiliations=affiliations,
                coauthor_pairs=pairs(person_works), institution_pairs=pairs(institution_works),
                diagnostics=diagnostics,
                coverage=dict(included_publications=len(keys),
                              publications_with_provider_author_ids=len(person_works),
                              publications_without_provider_author_ids=len(keys)-len(person_works),
                              publications_with_provider_institution_ids=len(institution_works)),
                native_acceptance=False, provider_wide_metrics_available=False,
                external_alias_verification='Unverified source assertions; no identity merging',
                employment_inference=False, partnership_inference=False)
