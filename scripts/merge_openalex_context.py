"""Reference overlay for the matching native M function; no acquisition/writes."""
from __future__ import annotations

from datetime import datetime, timezone
import re
from enrich_openalex import clean_doi

FIELDS = ('CitationCount_OpenAlex', 'OpenAccessStatus_OpenAlex', 'OAUrl_OpenAlex')


def _instant(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError('Provider observation time must be text')
    instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if instant.tzinfo is None or instant.utcoffset().total_seconds() != 0:
        raise ValueError('UTC provider observation time required')
    return instant


def merge(publications: list[dict], enrichment: list[dict]) -> tuple[list[dict], list[dict]]:
    """DOI-only, one-to-one provider join; preserve canonical fields and membership.

    Enrichment must come from the accepted retained provider projection. Absence
    is unknown, never a zero value/deletion; older observations cannot replace
    newer known values. Each changed field carries its own observation time.
    """
    keys = [p.get('CanonicalKey') for p in publications]
    if (any(not isinstance(k, str) or not k.strip() for k in keys)
            or len(set(keys)) != len(keys)):
        raise ValueError('Unique existing canonical keys required')
    by_doi, works = {}, set()
    for row in enrichment:
        doi, work = clean_doi(row.get('DOI')), row.get('OpenAlexWorkID')
        if not doi or not isinstance(work, str) or re.fullmatch(r'https://openalex\.org/W[0-9]+', work) is None:
            raise ValueError('Exact provider identity required')
        doi = doi.casefold()
        if doi in by_doi or work in works:
            raise ValueError('Conflicting provider DOI/work identity')
        observed = _instant(row.get('OpenAlexObservedUTC'))
        if observed is None or observed > datetime.now(timezone.utc):
            raise ValueError('Successful source observation time required')
        count = row.get('CitationCount_OpenAlex')
        if count is not None and (type(count) is not int or count < 0):
            raise ValueError('Provider citation count must be a nonnegative integer or null')
        if any(row.get(f) is not None and not isinstance(row[f], str) for f in FIELDS[1:]):
            raise ValueError('Provider OA fields must be text or null')
        by_doi[doi] = row
        works.add(work)
    publication_dois = [doi.casefold() for row in publications if (doi := clean_doi(row.get('DOI'))) and doi.casefold() in by_doi]
    if len(publication_dois) != len(set(publication_dois)):
        raise ValueError('Ambiguous publication DOI requires identity reconciliation')
    result, provenance = [], []
    for publication in publications:
        current = dict(publication)
        doi = clean_doi(publication.get('DOI'))
        incoming = by_doi.get(doi.casefold()) if doi else None
        if incoming:
            for field in FIELDS:
                value, prior = incoming.get(field), current.get(field)
                time_field = field + '_ObservedUTC'
                previous_time = _instant(current.get(time_field))
                observed = _instant(incoming['OpenAlexObservedUTC'])
                stale = previous_time is not None and observed < previous_time
                if value is None:
                    decision = 'preserve_missing'
                elif stale:
                    decision = 'preserve_newer'
                elif previous_time == observed and prior is not None and prior != value:
                    raise ValueError('Same-observation provider conflict')
                else:
                    current[field] = value
                    current[time_field] = incoming['OpenAlexObservedUTC']
                    decision = 'source_observation'
                provenance.append({'CanonicalKey': publication['CanonicalKey'], 'Field': field,
                                   'Source': 'OpenAlex', 'ProviderWorkID': incoming['OpenAlexWorkID'],
                                   'DOI': doi.casefold(), 'AttemptObservedUTC': incoming['OpenAlexObservedUTC'],
                                   'OriginalValue': prior, 'IncomingValue': value,
                                   'SelectedValue': current.get(field),
                                   'SelectedObservedUTC': current.get(time_field), 'Decision': decision})
        result.append(current)
    if [p['CanonicalKey'] for p in result] != keys:
        raise ValueError('Canonical identity or order changed')
    return result, provenance
