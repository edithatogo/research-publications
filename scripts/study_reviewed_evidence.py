"""Bind private reviewed associations/registry decisions to an exact study capture.

Validation preserves reviewed assertions; it does not perform identity adjudication.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
import hashlib
import re
from pathlib import Path

from scripts.source_capture_receipt import strict_json


def load_review(raw, expected_sha256):
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Reviewed evidence hash mismatch')
    packet = strict_json(raw)
    fields = {'schema_version', 'capture_sha256', 'review_id', 'scope', 'associations',
              'association_evidence', 'registry_decisions'}
    if not isinstance(packet, dict) or type(packet.get('schema_version')) is not int or packet['schema_version'] not in {1, 2}:
        raise ValueError('Reviewed evidence contract mismatch')
    if packet['schema_version'] == 2:
        fields |= {'ppg_references', 'refresh_lineage'}
    if set(packet) != fields:
        raise ValueError('Reviewed evidence contract mismatch')
    if not re.fullmatch('[a-f0-9]{64}', packet['capture_sha256']):
        raise ValueError('Reviewed capture hash required')
    if any(not isinstance(packet[k], str) or not packet[k].strip() for k in ('review_id', 'scope')):
        raise ValueError('Review identity and scope required')
    return packet


def validate_receipt_binding(packet, receipt_sha256):
    if not receipt_sha256 or any(proof['source_receipt_sha256'] != receipt_sha256
                                 for proof in packet['association_evidence'].values()):
        raise ValueError('Reviewed evidence refers to a different DoRA receipt')


def validate_ppg_references(packet, source_keys):
    """Retain PPG citation identities, not evidence content or authority decisions."""
    from scripts.study_explorer import _url
    from scripts.export_dora_activity import _required_timestamp
    links = packet.get('ppg_references', [])
    if not isinstance(links, list):
        raise ValueError('PPG references must be an array')
    seen = set()
    for link in links:
        fields = {'source_key', 'frameworkKey', 'requirementKey', 'relationshipScope', 'receipt'}
        if not isinstance(link, dict) or set(link) != fields or link['source_key'] not in source_keys:
            raise ValueError('PPG reference must identify a captured study and requirement')
        for field in ('frameworkKey', 'requirementKey'):
            if not isinstance(link[field], str) or not link[field].strip():
                raise ValueError('PPG framework and requirement identities required')
        if link['relationshipScope'] not in {'study', 'service'}:
            raise ValueError('PPG evidence scope must distinguish study and service')
        receipt = link['receipt']
        required = {'sourceId', 'canonicalUrl', 'retrievedAtUtc', 'nativeUniqueId',
                    'nativeVersionRef', 'sha256', 'authorityLabel', 'status'}
        if not isinstance(receipt, dict) or set(receipt) != required or receipt['status'] != 'retrieved':
            raise ValueError('Only a retrieved PPG source receipt can supply reference metadata')
        for field in ('sourceId', 'nativeUniqueId', 'nativeVersionRef'):
            if not isinstance(receipt[field], str) or not receipt[field].strip():
                raise ValueError('PPG source identity and native version required')
        if receipt['authorityLabel'] not in {'captured-reference-unconfirmed', 'draft-unapproved', 'authority-recorded-not-independently-verified'}:
            raise ValueError('PPG source authority label required; no compliance assertion')
        _url(receipt['canonicalUrl'])
        _required_timestamp(receipt['retrievedAtUtc'])
        if not isinstance(receipt['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', receipt['sha256']):
            raise ValueError('PPG extracted-text hash required')
        identity = (link['source_key'], link['frameworkKey'], link['requirementKey'],
                    link['relationshipScope'], receipt['sourceId'], receipt['nativeVersionRef'])
        if identity in seen:
            raise ValueError('Duplicate PPG requirement/evidence reference')
        seen.add(identity)
    lineage = packet.get('refresh_lineage')
    if lineage is not None:
        required = {'policy', 'previous_capture_sha256', 'previous_review_sha256',
                    'previous_review_id', 'previous_observed_at', 'carried_source_keys'}
        if not isinstance(lineage, dict) or set(lineage) != required or lineage['policy'] != 'unchanged_same_resource_only':
            raise ValueError('Explicit refresh lineage required')
        for field in ('previous_capture_sha256', 'previous_review_sha256'):
            if not isinstance(lineage[field], str) or not re.fullmatch('[a-f0-9]{64}', lineage[field]):
                raise ValueError('Pinned previous generation/review required')
        if not isinstance(lineage['previous_review_id'], str) or not lineage['previous_review_id'].strip():
            raise ValueError('Previous review identity required')
        _required_timestamp(lineage['previous_observed_at'])
        carried = lineage['carried_source_keys']
        if not isinstance(carried, list) or any(not isinstance(key, str) for key in carried) or len(carried) != len(set(carried)) or set(carried) - source_keys:
            raise ValueError('Refresh carry keys must be unique captured identities')
    return links


def apply_review(result, packet, source_rows):
    """Check the full capture domain before applying evidence to filtered rows."""
    if result['capture_sha256'] != packet['capture_sha256']:
        raise ValueError('Review belongs to a different study capture')
    from scripts.study_explorer import validate_associations
    associations = validate_associations(packet['associations'])
    source_by_key = {row['SourceKey']: row for row in source_rows}
    source_keys = set(source_by_key)
    ppg_references = validate_ppg_references(packet, source_keys)
    evidence = packet['association_evidence']
    if not isinstance(evidence, dict) or set(evidence) != set(associations):
        raise ValueError('Every reviewed association requires source evidence')
    if set(associations) - source_keys:
        raise ValueError('Reviewed association references absent from capture')
    for key, proof in evidence.items():
        required = {'basis', 'source_field', 'source_value', 'source_observed_at',
                    'source_receipt_sha256', 'facilities_contract_sha256', 'matched_facility_keys'}
        if (not isinstance(proof, dict) or set(proof) != required
                or proof['basis'] != 'source_reported_site'
                or proof['source_field'] != 'Site Name'
                or not isinstance(proof['source_value'], str) or not proof['source_value']
                or not isinstance(proof['matched_facility_keys'], list) or not proof['matched_facility_keys']):
            raise ValueError('Explicit source-site evidence required')
        if proof['source_observed_at'] != result['observed_at']:
            raise ValueError('Association observation differs from study capture')
        if source_by_key[key].get('SourceSiteName') != proof['source_value']:
            raise ValueError('Reviewed source site differs from captured value')
        for field in ('source_receipt_sha256', 'facilities_contract_sha256'):
            if not isinstance(proof[field], str) or not re.fullmatch('[a-f0-9]{64}', proof[field]):
                raise ValueError('Source association provenance hash required')
    decisions = packet['registry_decisions']
    if not isinstance(decisions, list):
        raise ValueError('Registry decisions must be an array')
    pairs = set()
    by_key = {}
    files = {}
    for decision in decisions:
        required = {'source_key', 'registry_key', 'registry_url', 'decision', 'basis',
                    'corroboration', 'differences', 'review_scope', 'registry_evidence'}
        if not isinstance(decision, dict) or set(decision) != required:
            raise ValueError('Registry decision contract mismatch')
        key = decision['source_key']
        registry_key = decision['registry_key']
        if key not in source_keys:
            raise ValueError('Registry decision references absent from capture')
        if not isinstance(registry_key, str) or not re.fullmatch(r'clinicaltrials\.gov:NCT[0-9]{8}', registry_key):
            raise ValueError('Qualified retained ClinicalTrials.gov identity required')
        nct = registry_key.split(':', 1)[1]
        if decision['registry_url'] != 'https://clinicaltrials.gov/study/' + nct:
            raise ValueError('Registry identity/URL mismatch')
        pair = (key, registry_key)
        if pair in pairs:
            raise ValueError('Duplicate or conflicting registry decision')
        pairs.add(pair)
        if decision['decision'] not in {'confirmed', 'candidate'}:
            raise ValueError('Explicit confirmed/candidate decision required')
        if any(not isinstance(decision[k], str) or not decision[k].strip()
               for k in ('basis', 'review_scope')):
            raise ValueError('Registry decision basis and review scope required')
        for field in ('corroboration', 'differences'):
            if not isinstance(decision[field], list) or any(not isinstance(x, str) or not x.strip() for x in decision[field]):
                raise ValueError('Registry evidence statements must be text arrays')
        if decision['decision'] == 'confirmed' and len(decision['corroboration']) < 2:
            raise ValueError('Confirmed review requires multiple corroborating statements')
        proof = decision['registry_evidence']
        if not isinstance(proof, dict) or set(proof) != {'file', 'sha256', 'locator', 'snapshot_at', 'last_update_source'}:
            raise ValueError('Registry payload provenance required')
        if proof['locator'] != nct:
            raise ValueError('Registry evidence locator differs from identity')
        path = Path(proof['file'])
        cache_key = (str(path.resolve()), proof['sha256'])
        if cache_key not in files:
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != proof['sha256']:
                raise ValueError('Registry evidence payload hash mismatch')
            page = strict_json(raw)
            if page.get('response', {}).get('statusCode') != 200:
                raise ValueError('Successful retained registry page required')
            records = page['response']['body']['studies']
            ids = [row['protocolSection']['identificationModule']['nctId'] for row in records]
            if len(ids) != len(set(ids)):
                raise ValueError('Registry page has duplicate identities')
            files[cache_key] = {row['protocolSection']['identificationModule']['nctId']: row['protocolSection'].get('statusModule', {}).get('lastUpdatePostDateStruct') for row in records}
        if nct not in files[cache_key]:
            raise ValueError('Registry identity absent from pinned evidence payload')
        if proof['last_update_source'] != files[cache_key][nct]:
            raise ValueError('Registry update metadata differs from pinned source')
        from scripts.export_dora_activity import _required_timestamp
        _required_timestamp(proof['snapshot_at'])
        by_key.setdefault(key, []).append(copy.deepcopy(decision))
    # Only selected rows are displayed; unselected evidence remains in the source packet.
    for rows in result['views'].values():
        for row in rows:
            key = row['SourceKey']
            if row.get('CHHHSInvolvement') != associations.get(key):
                raise ValueError('View associations differ from reviewed packet')
            if key in evidence:
                if row.get('SourceSiteName') != evidence[key]['source_value']:
                    raise ValueError('Reviewed source site differs from captured value')
                row['CHHHSAssociationEvidence'] = copy.deepcopy(evidence[key])
            row['RegistryLinks'] = sorted(by_key.get(key, []), key=lambda item: item['registry_key'])
            row['PPGEvidenceReferences'] = [copy.deepcopy(link) for link in ppg_references if link['source_key'] == key]
    result['review_id'] = packet['review_id']
    result['review_scope'] = packet['scope']
    result['refresh_lineage'] = copy.deepcopy(packet.get('refresh_lineage'))
    result['ppg_packet_reference_count'] = len(ppg_references)
    result['ppg_reference_count'] = sum(len(row.get('PPGEvidenceReferences', [])) for rows in result['views'].values() for row in rows)
    return result
