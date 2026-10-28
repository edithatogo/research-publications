"""Review-gated typed relationships between grants and existing RIMS entities."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlsplit

from scripts.grants_registry import OPPORTUNITY_KEY_PREFIXES

RELATION_TYPES = {
    'funded_by_award', 'candidate_award_match', 'relevant_to_opportunity',
    'investigator_affiliation',
}
CONFIDENCE = {'confirmed', 'review', 'candidate'}
RELATIONSHIP_FIELDS = {
    'RelationshipKey', 'RelationshipType', 'FromKey', 'ToKey', 'AwardID',
    'EvidenceURL', 'Confidence', 'ReviewStatus',
}
AWARD_KEY_PATTERN = re.compile(r'^AWARD:([^:\s]+):([^\s]+)$')


def award_key_namespace(value: str) -> str | None:
    """Read the supplied AWARD:<funder>:<id> namespace without rewriting its key."""
    match = AWARD_KEY_PATTERN.fullmatch(value)
    return match.group(1).casefold() if match else None


def funder_key_namespace(value: str) -> str | None:
    """Compare canonical FUNDER:<namespace> and retained single-label aliases."""
    namespace = value.removeprefix('FUNDER:')
    if not namespace or ':' in namespace or any(c.isspace() for c in namespace):
        return None
    return namespace.casefold()


def normalize_relationship(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ValueError('relationship record must be an object')
    unknown_fields = set(record) - RELATIONSHIP_FIELDS
    if unknown_fields:
        raise ValueError(f'unsupported relationship fields: {", ".join(sorted(map(str, unknown_fields)))}')
    for field, default in (
        ('RelationshipType', ''), ('FromKey', ''), ('ToKey', ''),
        ('EvidenceURL', ''), ('Confidence', 'review'),
    ):
        if not isinstance(record.get(field, default), str):
            raise ValueError(f'{field} must be text')
    relation = record.get('RelationshipType', '').strip()
    source_key = record.get('FromKey', '').strip()
    target_key = record.get('ToKey', '').strip()
    if (not source_key or not target_key or
            source_key != record.get('FromKey') or target_key != record.get('ToKey')):
        raise ValueError('relationship source keys must be nonblank and unpadded')
    evidence = str(record.get('EvidenceURL', '')).strip()
    confidence = str(record.get('Confidence', 'review')).strip().lower()
    if relation not in RELATION_TYPES:
        raise ValueError('unsupported relationship type')
    if not source_key or not target_key or not evidence:
        raise ValueError('relationship requires from/to keys and evidence')
    try:
        evidence_url = urlsplit(evidence)
        valid_evidence_url = (
            evidence_url.scheme.casefold() in {'http', 'https'}
            and bool(evidence_url.hostname)
            and evidence_url.username is None
            and evidence_url.password is None
        )
    except ValueError:
        valid_evidence_url = False
    if not valid_evidence_url:
        raise ValueError('relationship evidence must be an absolute HTTP(S) URL without embedded credentials')
    if confidence not in CONFIDENCE:
        raise ValueError('unsupported confidence')
    raw_award_id = record.get('AwardID', '')
    if raw_award_id is not None and not isinstance(raw_award_id, str):
        raise ValueError('AwardID must be text')
    award_id = (raw_award_id or '').strip()
    if raw_award_id and award_id != raw_award_id:
        raise ValueError('AwardID must be nonblank and unpadded')
    if relation in {'funded_by_award', 'candidate_award_match'}:
        if award_key_namespace(source_key) is None or not target_key.startswith('PUB:'):
            raise ValueError('award relationships must link an AWARD key to a PUB key')
        if not award_id:
            raise ValueError('award relationships require exact AwardID')
        if relation == 'funded_by_award' and confidence != 'confirmed':
            raise ValueError('unconfirmed award matches must use candidate_award_match')
        if relation == 'candidate_award_match' and confidence == 'confirmed':
            raise ValueError('confirmed award relationships must use funded_by_award')
    if relation == 'relevant_to_opportunity' and not (
            source_key.startswith('PUB:')
            and any(target_key.startswith(prefix) for prefix in OPPORTUNITY_KEY_PREFIXES)):
        raise ValueError('opportunity relevance must link a PUB key to a GRANT opportunity key')
    raw_review_status = record.get('ReviewStatus', 'Needs Review')
    if raw_review_status is not None and not isinstance(raw_review_status, str):
        raise ValueError('ReviewStatus must be text')
    review_status = (raw_review_status or '').strip() or 'Needs Review'
    if relation == 'funded_by_award' and review_status.casefold() in {'withdrawn', 'retracted', 'rejected'}:
        raise ValueError('withdrawn or rejected award relationship cannot be confirmed as funded')
    if confidence == 'confirmed' and review_status.casefold() != 'reviewed':
        raise ValueError('confirmed relationships require ReviewStatus Reviewed')
    # Encode the fields as a typed tuple. A delimiter-joined string can alias
    # distinct relationships when a valid key or evidence URL contains that
    # delimiter, undermining idempotency and duplicate detection.
    basis = json.dumps(
        [relation, source_key, target_key, award_id, evidence],
        ensure_ascii=False,
        separators=(',', ':'),
        allow_nan=False,
    )
    normalized = {
        'RelationshipKey': 'REL:' + hashlib.sha256(basis.encode('utf-8')).hexdigest()[:24],
        'RelationshipType': relation,
        'FromKey': source_key,
        'ToKey': target_key,
        'AwardID': award_id,
        'EvidenceURL': evidence,
        'Confidence': confidence,
        'ReviewStatus': review_status,
    }
    if 'RelationshipKey' in record:
        supplied_key = record['RelationshipKey']
        if not isinstance(supplied_key, str):
            raise ValueError('RelationshipKey must be text')
        if supplied_key != normalized['RelationshipKey']:
            raise ValueError('RelationshipKey does not match the normalized relationship identity')
    return normalized


def validate_relationship_batch(
    records: Iterable[dict[str, Any]],
    *,
    publication_keys: Iterable[str],
    opportunity_keys: Iterable[str],
    award_sources: Iterable[Mapping[str, Any]],
    affiliation_sources: Mapping[str, Iterable[str]],
) -> dict[str, list[dict[str, Any]]]:
    """Validate relationship candidates against caller-supplied source snapshots.

    This function deliberately does not discover identities or edit source rows.
    Callers must provide the complete, independently read source key sets. Any
    absent/duplicate identity is rejected with stable reason codes. Candidate
    relationships that resolve cleanly retain their candidate type/confidence.
    """
    def source_keys(values: Iterable[str], label: str) -> list[str]:
        normalized = []
        for value in values:
            if not isinstance(value, str):
                raise ValueError(f'{label} keys must be text')
            if not value.strip():
                raise ValueError(f'{label} keys must be nonblank')
            if value != value.strip():
                raise ValueError(f'{label} keys must be unpadded')
            normalized.append(value)
        return normalized

    pubs = source_keys(publication_keys, 'publication')
    opportunities = source_keys(opportunity_keys, 'opportunity')
    pub_counts, opportunity_counts = Counter(pubs), Counter(opportunities)
    pub_set, opportunity_set = set(pubs), set(opportunities)

    awards = []
    for row in award_sources:
        if not isinstance(row, Mapping):
            raise ValueError('award source rows must be objects')
        for field in ('AwardKey', 'AwardID', 'FunderKey', 'AwardStatus'):
            if row.get(field) is not None and not isinstance(row[field], str):
                raise ValueError(f'award source {field} must be text')
        for field in ('AwardKey', 'AwardID', 'FunderKey'):
            value = row.get(field)
            if value is not None and value != value.strip():
                raise ValueError(f'award source {field} must be unpadded')
        awards.append(dict(row))
    awards_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    awards_by_identity: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in awards:
        key = row.get('AwardKey') or ''
        award_id = row.get('AwardID') or ''
        funder_key = row.get('FunderKey') or ''
        if key:
            awards_by_key[key].append(row)
        if award_id and funder_key:
            # Compare aliases only for ambiguity detection; never rewrite keys.
            namespace = funder_key_namespace(funder_key) or funder_key.casefold()
            awards_by_identity[(award_id, namespace)].append(row)

    affiliation_index: dict[str, list[str]] = {}
    for identity, targets in affiliation_sources.items():
        if not isinstance(identity, str):
            raise ValueError('affiliation source keys must be text')
        if isinstance(targets, (str, bytes)) or not isinstance(targets, Iterable):
            raise ValueError('affiliation target collections must be sequences of text keys')
        if not identity.strip() or identity != identity.strip():
            raise ValueError('affiliation source keys must be nonblank and unpadded')
        key = identity
        # Distinct source keys can collapse to the same canonical identity
        # after whitespace normalization. Preserve all targets so that this
        # collision remains visible as ambiguity instead of last-write-wins.
        normalized_targets = []
        for target in targets:
            if not isinstance(target, str):
                raise ValueError('affiliation targets must be text')
            if not target.strip() or target != target.strip():
                raise ValueError('affiliation target keys must be nonblank and unpadded')
            normalized_targets.append(target)
        affiliation_index.setdefault(key, []).extend(normalized_targets)

    raw_records = list(records)
    normalized: dict[int, dict[str, Any]] = {}
    failures: dict[int, list[str]] = defaultdict(list)
    for index, record in enumerate(raw_records):
        try:
            normalized[index] = normalize_relationship(record)
        except (AttributeError, TypeError, ValueError) as exc:
            failures[index].append(f'invalid_relationship:{str(exc)}')

    # Reject every member of a duplicate group, independent of input order.
    relationship_groups: dict[str, list[int]] = defaultdict(list)
    for index, row in normalized.items():
        relationship_groups[row['RelationshipKey']].append(index)
    for indexes in relationship_groups.values():
        if len(indexes) > 1:
            for index in indexes:
                failures[index].append('duplicate_relationship_key')

    for index, row in normalized.items():
        relation, source, target = row['RelationshipType'], row['FromKey'], row['ToKey']
        if relation in {'funded_by_award', 'candidate_award_match'}:
            source_rows = awards_by_key.get(source, [])
            if not source_rows:
                failures[index].append('award_source_missing')
                continue
            if len(source_rows) != 1:
                failures[index].append('award_source_key_duplicate')
                continue
            award = source_rows[0]
            award_id = award.get('AwardID') or ''
            funder_key = award.get('FunderKey') or ''
            if not award_id or not funder_key:
                failures[index].append('award_identity_incomplete')
                continue
            if award_key_namespace(source) != funder_key_namespace(funder_key):
                failures[index].append('award_funder_key_namespace_mismatch')
            if row['AwardID'] != award_id:
                failures[index].append('award_id_mismatch')
            namespace = funder_key_namespace(funder_key) or funder_key.casefold()
            identity_rows = awards_by_identity[(award_id, namespace)]
            if len(identity_rows) != 1:
                failures[index].append('award_funder_identity_ambiguous')
            if target not in pub_set:
                failures[index].append('publication_source_missing')
            elif pub_counts[target] != 1:
                failures[index].append('publication_key_duplicate')
            award_status = (award.get('AwardStatus') or '').strip().casefold()
            withdrawn = {'withdrawn', 'retracted', 'rejected', 'cancelled', 'canceled'}
            if (award_status in withdrawn or row['ReviewStatus'].casefold() in withdrawn) and relation == 'funded_by_award':
                failures[index].append('withdrawn_award_cannot_be_confirmed')
        elif relation == 'relevant_to_opportunity':
            if source not in pub_set:
                failures[index].append('publication_source_missing')
            elif pub_counts[source] != 1:
                failures[index].append('publication_key_duplicate')
            if target not in opportunity_set:
                failures[index].append('opportunity_source_missing')
            elif opportunity_counts[target] != 1:
                failures[index].append('opportunity_key_duplicate')
        elif relation == 'investigator_affiliation':
            targets = affiliation_index.get(source)
            if targets is None:
                failures[index].append('affiliation_source_missing')
                continue
            unique_targets = set(targets)
            if target not in unique_targets:
                failures[index].append('affiliation_target_unresolved')
            if len(unique_targets) > 1:
                failures[index].append('affiliation_identity_ambiguous')

    accepted = [normalized[index] for index in range(len(raw_records)) if index in normalized and not failures[index]]
    rejected = [
        {'index': index, 'reasons': sorted(set(failures[index]))}
        for index in range(len(raw_records)) if failures[index]
    ]
    return {'validated': accepted, 'rejected': rejected}
