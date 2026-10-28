"""Prepare supplied historical NIH text changes for isolated replay.

Hashes bind supplied bytes and a selected subtree; they do not authenticate a
provider, grant execution authority or establish a live provider transition.

No service I/O, approval, deadline inference or claim of a live provider transition.
"""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy
import hashlib
import json
import re
from scripts.grants_nih_observer import selected_detail
from scripts.grants_us_gov_api import SOURCE, OPPORTUNITY_ID, FON

TEXT_FIELDS = {'Title': ('opportunityTitle',), 'Funder': ('synopsis', 'agencyDetails', 'agencyName'),
               'Description': ('synopsis', 'synopsisDesc'),
               'Eligibility': ('synopsis', 'applicantEligibilityDesc')}
DATE_FIELDS = ('responseDateStr', 'archiveDateStr', 'postingDateStr')


def prepare(raw: bytes, current_record: dict, *, history_index: int = 0) -> dict:
    if not isinstance(raw, bytes) or not isinstance(current_record, dict):
        raise ValueError('Supplied raw bytes and complete current preimage required')
    data = selected_detail(json.loads(raw))
    restore_fields = [*TEXT_FIELDS, 'EvidenceHash', 'FunderKey', 'CategoryKeysJSON', 'ClassificationEvidenceJSON']
    if (current_record.get('Source') != SOURCE
            or current_record.get('SourceID') != str(OPPORTUNITY_ID)
            or current_record.get('RoundID') != FON
            or current_record.get('ReviewStatus') != 'Needs Review'
            or not isinstance(current_record.get('OpportunityKey'), str)
            or not re.fullmatch(r'GRANT:[a-f0-9]{24}', current_record['OpportunityKey'])
            or not isinstance(current_record.get('EvidenceHash'), str)
            or not re.fullmatch(r'[a-f0-9]{64}', current_record['EvidenceHash'])
            or any(field not in current_record for field in restore_fields)):
        raise ValueError('Exact source identity, evidence hash and complete unapproved restore preimage required')
    histories = data.get('opportunityHistoryDetails')
    if (type(history_index) is not int or history_index < 0 or not isinstance(histories, list)
            or history_index >= len(histories)):
        raise ValueError('Exact retained history index required')
    historical = histories[history_index]
    if (not isinstance(historical, dict)
            or not isinstance(historical.get('synopsis'), dict)
            or not isinstance(data.get('synopsis'), dict)
            or type(historical.get('opportunityId')) is not int
            or historical.get('opportunityId') != data['id']
            or historical.get('opportunityNumber') != data['opportunityNumber']
            or type(historical['synopsis'].get('opportunityId')) is not int
            or historical['synopsis']['opportunityId'] != data['id']
            or type(historical.get('revision')) is not int
            or type(data.get('revision')) is not int
            or historical['revision'] < 0
            or historical['revision'] >= data['revision']):
        raise ValueError('Older official same-opportunity revision required')
    if any(historical['synopsis'].get(k) != data['synopsis'].get(k) for k in DATE_FIELDS):
        raise ValueError('Historical deadline changes require separate date/schedule reconciliation')
    payload, differences = {}, []
    for target, pointer in TEXT_FIELDS.items():
        def value(obj):
            for key in pointer:
                if not isinstance(obj, dict) or key not in obj:
                    raise ValueError('Explicit official source text required')
                obj = obj[key]
            if not isinstance(obj, str) or not obj.strip():
                raise ValueError('Explicit official source text required')
            return obj
        old, new = value(historical), value(data)
        if current_record.get(target) != new:
            raise ValueError('Current record differs from retained official source: ' + target)
        payload[target] = old
        if old != new: differences.append(target)
    if not differences:
        raise ValueError('No substantive source text change in selected revision')
    pointer = f'/data/opportunityHistoryDetails/{history_index}'
    source_hash = hashlib.sha256(raw).hexdigest()
    version_hash = hashlib.sha256(json.dumps(historical, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    prior = {k: copy.deepcopy(current_record[k]) for k in restore_fields}
    evidence = {'format': 'rims-historical-source-replay-v1', 'source_response_sha256': source_hash,
                'source_pointer': pointer, 'historical_revision': historical['revision'],
                'historical_subtree_sha256': version_hash, 'current_revision': data['revision'],
                'classification_review_required': True, 'opportunity_reviewed': False,
                'live_provider_transition_claimed': False}
    payload.update(EvidenceHash=version_hash, FunderKey=None, CategoryKeysJSON='[]',
                   ClassificationEvidenceJSON=json.dumps(evidence, sort_keys=True, separators=(',', ':')))
    return {'kind': 'g07-official-history-replay-v1', 'execution_enabled': False,
            'source_identity': {k: current_record[k] for k in
                                ['OpportunityKey', 'Source', 'SourceID', 'RoundID', 'ReviewStatus']},
            'source_evidence': evidence, 'actual_text_fields_changed': differences,
            'historical_payload': payload, 'restore_payload': prior,
            'deadline_or_schedule_changed': False, 'notification_activation': False,
            'scope': 'Isolated authentic source-version replay; no live transition or opportunity approval.'}
