"""Reconcile retained DoRA generations without native writes or implicit admission.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from scripts.dora_study_projection import project_dora, read_directory
from scripts.source_capture_receipt import create_output, strict_json
from scripts.study_explorer import explore_dora, render
from scripts.study_reviewed_evidence import load_review, validate_receipt_binding, validate_ppg_references


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2).encode() + b'\n'


def _fingerprint(row):
    return sha(encoded(row))


def reconcile(previous_raw, current_raw, previous_receipt_sha256, current_receipt_sha256,
              review_raw, review_sha256, facilities_raw, facilities_sha256, revision_id, ppg_references=None):
    if not isinstance(revision_id, str) or not revision_id.strip():
        raise ValueError('An explicit refresh revision identity is required')
    previous_rows, previous_at = project_dora(previous_raw, sha(previous_raw))
    current_rows, current_at = project_dora(current_raw, sha(current_raw))
    if datetime.fromisoformat(current_at.replace('Z', '+00:00')) < datetime.fromisoformat(previous_at.replace('Z', '+00:00')):
        raise ValueError('Out-of-order source observation; previous generation preserved')
    old = strict_json(previous_raw)
    new = strict_json(current_raw)
    scope = lambda value: tuple(value['source_payload'].get(key) for key in ('package_name', 'package_id', 'api', 'fields'))
    if scope(old) != scope(new):
        raise ValueError('Source scope/schema changed; separate qualification required')
    packet = load_review(review_raw, review_sha256)
    reviewed_keys = {link['source_key'] for link in packet['associations']} | {link['source_key'] for link in packet['registry_decisions']} | {link['source_key'] for link in packet.get('ppg_references', [])}
    validate_receipt_binding(packet, previous_receipt_sha256)
    # Validate accepted review and its referenced registry bytes before considering reuse.
    explore_dora(previous_raw, sha(previous_raw), associations=packet['associations'], reviewed_evidence=packet)
    if sha(facilities_raw) != facilities_sha256:
        raise ValueError('Facility reference hash mismatch')
    facilities = strict_json(facilities_raw)['rows']
    if not facilities or any(not isinstance(row.get('FacilityKey'), str) or not isinstance(row.get('FacilityName'), str) for row in facilities):
        raise ValueError('Maintained facility identities/names required')
    resource = lambda value: value['source_payload']['resource']['id']
    replaced = resource(old) != resource(new)
    before_raw = {row['SourceKey']: source for row, source in zip(previous_rows, old['records'], strict=True)}
    after_raw = {row['SourceKey']: source for row, source in zip(current_rows, new['records'], strict=True)}
    before = {row['SourceKey']: row for row in previous_rows}
    after = {row['SourceKey']: row for row in current_rows}
    same = set(before) & set(after) if not replaced else set()
    unchanged = {key for key in same if _fingerprint(before_raw[key]) == _fingerprint(after_raw[key])}
    changed = same - unchanged
    removed, added = set(before) - set(after), set(after) - set(before)
    facility_changed = {key for key, proof in packet['association_evidence'].items() if proof['facilities_contract_sha256'] != facilities_sha256}
    carried = unchanged - facility_changed
    def reference_key(link):
        receipt = link['receipt']
        return (link['source_key'], link['frameworkKey'], link['requirementKey'], link['relationshipScope'], receipt['sourceId'], receipt['nativeVersionRef'])
    references = {reference_key(link): copy.deepcopy(link) for link in packet.get('ppg_references', []) if link['source_key'] in carried}
    added_references = 0
    if ppg_references is not None:
        validate_ppg_references({'ppg_references': ppg_references}, set(after))
        eligible = {link['source_key'] for link in packet['associations']} & carried
        if any(link['source_key'] not in eligible for link in ppg_references):
            raise ValueError('New PPG references require an unchanged reviewed CHHHS association')
        for link in ppg_references:
            identity = reference_key(link)
            if identity in references and references[identity] != link:
                raise ValueError('PPG metadata changed for an existing reference/version; explicit review required')
            if identity not in references:
                added_references += 1
            references[identity] = copy.deepcopy(link)
    if sha(previous_raw) == sha(current_raw) and previous_receipt_sha256 == current_receipt_sha256 and not facility_changed and not added_references:
        next_packet = copy.deepcopy(packet)
        outcome = 'unchanged_replay'
    else:
        if revision_id == packet['review_id']:
            raise ValueError('Changed source generation requires a new refresh revision identity')
        next_packet = copy.deepcopy(packet)
        next_packet.update(schema_version=2, review_id=revision_id,
                           scope='Unchanged same-resource source rows reused from ' + packet['review_id'] + '; changed/new/missing identities require review. Not a new clinical or identity adjudication.',
                           capture_sha256=sha(current_raw))
        next_packet['associations'] = [copy.deepcopy(link) for link in packet['associations'] if link['source_key'] in carried]
        for link in next_packet['associations']:
            link['evidence_url'] = after[link['source_key']]['SourceURL']
        next_packet['association_evidence'] = {key: copy.deepcopy(proof) for key, proof in packet['association_evidence'].items() if key in carried}
        for proof in next_packet['association_evidence'].values():
            proof.update(source_observed_at=current_at, source_receipt_sha256=current_receipt_sha256)
        next_packet['registry_decisions'] = [copy.deepcopy(link) for link in packet['registry_decisions'] if link['source_key'] in carried]
        next_packet['ppg_references'] = [copy.deepcopy(link) for link in packet.get('ppg_references', []) if link['source_key'] in carried]
        next_packet['refresh_lineage'] = {'policy': 'unchanged_same_resource_only', 'previous_capture_sha256': sha(previous_raw),
            'previous_review_sha256': review_sha256, 'previous_review_id': packet['review_id'],
            'previous_observed_at': previous_at, 'carried_source_keys': sorted(carried & reviewed_keys)}
        next_packet['ppg_references'] = list(references.values())
        outcome = 'resource_replaced_review_required' if replaced else 'ppg_references_reconciled' if added_references and sha(previous_raw) == sha(current_raw) else 'capture_receipt_rebound' if sha(previous_raw) == sha(current_raw) else 'reconciled_source_generation'
    def normal(value):
        return ' '.join(re.findall('[a-z0-9]+', unicodedata.normalize('NFKD', value or '').casefold()))
    queue = []
    for key in sorted(changed | removed | added | (facility_changed & set(after))):
        row = after.get(key, before.get(key))
        site = normal(row['SourceSiteName'])
        hints = [item['FacilityKey'] for item in facilities if re.search(r'\b' + re.escape(normal(item['FacilityName'])) + r'\b', site)]
        reason = 'source_resource_replaced' if replaced else 'source_row_missing_not_closed' if key in removed else 'new_source_row' if key in added else 'facility_reference_changed' if key in facility_changed else 'source_row_changed'
        queue.append({'source_key': key, 'reason': reason, 'previous_study': before.get(key), 'current_study': after.get(key),
                      'candidate_site_matches': hints, 'previous_review_present': key in reviewed_keys,
                      'changed_fields': sorted(field for field in before_raw.get(key, {})
                          if key in changed and before_raw[key][field] != after_raw[key][field]),
                      'disposition': 'review_required; no inferred closure, deletion or identity crosswalk'})
    quarantined = {'associations': [copy.deepcopy(link) for link in packet['associations'] if link['source_key'] not in carried],
                   'association_evidence': {key: copy.deepcopy(proof) for key, proof in packet['association_evidence'].items() if key not in carried},
                   'registry_decisions': [copy.deepcopy(link) for link in packet['registry_decisions'] if link['source_key'] not in carried],
                   'ppg_references': [copy.deepcopy(link) for link in packet.get('ppg_references', []) if link['source_key'] not in carried]}
    # Verify the newly derived packet at the same reader boundary, retaining old registry timestamps.
    next_raw = review_raw if outcome == 'unchanged_replay' else encoded(next_packet)
    next_packet = load_review(next_raw, sha(next_raw))
    validate_receipt_binding(next_packet, current_receipt_sha256)
    view = explore_dora(current_raw, sha(current_raw), associations=next_packet['associations'], reviewed_evidence=next_packet)
    view.update(reviewed_evidence_sha256=sha(next_raw), dora_receipt_sha256=current_receipt_sha256,
                maintenance={'outcome': outcome, 'changed': len(changed), 'added': len(added), 'source_missing': len(removed),
                             'review_queue': len(queue), 'source_missing_is_not_closure': True,
                             'ppg_link_status': 'retained_versioned_references; current access/authority unverified' if view['ppg_reference_count'] else 'no_verified_versioned_PPG_references_recorded'})
    queue_by_key = {item['source_key']: item for item in queue}
    for selected in view['views'].values():
        for row in selected:
            if row['SourceKey'] in queue_by_key:
                row['SourceReviewState'] = queue_by_key[row['SourceKey']]['reason']
    view['source_history'] = [item['previous_study'] for item in queue if item['source_key'] in removed]
    summary = {'outcome': outcome, 'previous_rows': len(before), 'current_rows': len(after), 'unchanged': len(unchanged),
               'changed': len(changed), 'added': len(added), 'source_missing': len(removed), 'resource_replaced': replaced,
               'carried_reviewed_associations': len(next_packet['associations']), 'review_queue': len(queue),
               'quarantined_registry_decisions': len(quarantined['registry_decisions']), 'added_ppg_references': added_references, 'native_changed': False}
    return {'next_packet_raw': next_raw, 'view': view, 'summary': summary, 'review_queue': queue, 'quarantined_review': quarantined}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('previous', 'current'):
        parser.add_argument('--' + name + '-directory', type=Path, required=True)
        parser.add_argument('--' + name + '-receipt-sha256', required=True)
    parser.add_argument('--reviewed-evidence', type=Path, required=True)
    parser.add_argument('--reviewed-evidence-sha256', required=True)
    parser.add_argument('--facilities', type=Path, required=True)
    parser.add_argument('--facilities-sha256', required=True)
    parser.add_argument('--revision-id', required=True)
    parser.add_argument('--ppg-references', type=Path)
    parser.add_argument('--ppg-references-sha256')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if any(args.output.resolve().is_relative_to(path.resolve()) for path in (args.previous_directory, args.current_directory)):
        parser.error('Output must not modify an input capture directory')
    if bool(args.ppg_references) != bool(args.ppg_references_sha256):
        parser.error('--ppg-references and its SHA-256 must be supplied together')
    references = None
    if args.ppg_references:
        raw = args.ppg_references.read_bytes()
        if sha(raw) != args.ppg_references_sha256:
            raise ValueError('PPG reference input hash mismatch')
        references = strict_json(raw)
    previous = read_directory(args.previous_directory, args.previous_receipt_sha256)
    current = read_directory(args.current_directory, args.current_receipt_sha256)
    result = reconcile(previous, current, args.previous_receipt_sha256, args.current_receipt_sha256,
                       args.reviewed_evidence.read_bytes(), args.reviewed_evidence_sha256,
                       args.facilities.read_bytes(), args.facilities_sha256, args.revision_id, ppg_references=references)
    files = {'next-reviewed-evidence.json': result['next_packet_raw'], 'study-explorer.json': encoded(result['view']),
             'study-explorer.html': render(result['view']).encode(), 'reconciliation.json': encoded(result['summary']),
             'review-queue.json': encoded(result['review_queue']), 'quarantined-review.json': encoded(result['quarantined_review'])}
    out = create_output(args.output)
    for name, raw in files.items():
        with (out / name).open('xb') as stream:
            stream.write(raw)
        if (out / name).read_bytes() != raw:
            raise OSError('Local maintenance artifact readback mismatch')
    manifest = {'status': 'complete_local_generation', 'native_changed': False,
                'previous_receipt_sha256': args.previous_receipt_sha256, 'current_receipt_sha256': args.current_receipt_sha256,
                'previous_review_sha256': args.reviewed_evidence_sha256, 'ppg_reference_input_sha256': args.ppg_references_sha256,
                'files': {name: {'sha256': sha(raw), 'bytes': len(raw)} for name, raw in files.items()}}
    (out / 'maintenance-manifest.json').write_bytes(encoded(manifest))  # Commit last; no native selector changed.
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
