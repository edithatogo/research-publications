"""Source-code classification for the admitted NIH route, separate from review.

Only explicit Grants.gov agency/activity codes are mapped; labels are evidence,
never inferred keys. Output is an isolated-copy candidate, not send authority.
"""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy
import hashlib
import json
import re
from scripts.grants_nih_observer import selected_detail
from scripts.grants_us_gov_api import FON, OPPORTUNITY_ID, SOURCE

FIELDS = ('FunderKey', 'CategoryKeysJSON', 'ClassificationEvidenceJSON')


def reviewed_mapping(record, raw: bytes):
    if (not isinstance(record, dict) or not isinstance(raw, bytes)
            or record.get('Source') != SOURCE
            or record.get('SourceID') != str(OPPORTUNITY_ID) or record.get('RoundID') != FON
            or not isinstance(record.get('OpportunityKey'), str)
            or not isinstance(record.get('EvidenceHash'), str)
            or not isinstance(record.get('Funder'), str) or not record['Funder']
            or record['Funder'] != record['Funder'].strip()
            or not re.fullmatch(r'GRANT:[a-f0-9]{24}', record.get('OpportunityKey', ''))
            or not re.fullmatch(r'[a-f0-9]{64}', record.get('EvidenceHash', ''))):
        raise ValueError('Exact admitted source identity and evidence hash required')
    data = selected_detail(json.loads(raw))
    synopsis = data.get('synopsis', {})
    if not isinstance(synopsis, dict):
        raise ValueError('Explicit source synopsis required')
    agency = synopsis.get('agencyDetails', {})
    if not isinstance(agency, dict):
        raise ValueError('Explicit source agency required')
    code = agency.get('agencyCode')
    if (data.get('opportunityNumber') != record['RoundID']
            or code != 'HHS-NIH11' or data.get('owningAgencyCode') != code
            or synopsis.get('agencyCode') != code
            or data.get('agencyDetails') != agency
            or agency.get('agencyName') != record.get('Funder')
            or synopsis.get('agencyName') != agency.get('agencyName')):
        raise ValueError('Source response or agency identity conflicts')
    categories = synopsis.get('fundingActivityCategories')
    if not isinstance(categories, list) or not categories:
        raise ValueError('Explicit funding activity categories required')
    seen = set()
    for category in categories:
        if (not isinstance(category, dict)
                or not isinstance(category.get('id'), str)
                or not re.fullmatch(r'[A-Z]{2,4}', category['id'])
                or not isinstance(category.get('description'), str)
                or not category['description'].strip() or category['id'] in seen):
            raise ValueError('Missing, ambiguous or duplicate activity category')
        seen.add(category['id'])
    return {'format': 'rims-reviewed-source-codes-v1', 'OpportunityKey': record['OpportunityKey'],
            'source_evidence_hash': record['EvidenceHash'], 'source_response_sha256': hashlib.sha256(raw).hexdigest(),
            'source_id': '357812', 'round_id': 'PA-25-301',
            'method': 'exact native agency/activity codes; no label inference',
            'agency_pointer': '/data/synopsis/agencyDetails', 'agency': agency,
            'categories_pointer': '/data/synopsis/fundingActivityCategories',
            'categories': copy.deepcopy(categories), 'FunderKey': 'grants.gov:agency:' + code,
            'CategoryKeys': ['grants.gov:category:' + c['id'] for c in categories]}


def apply_mapping(record, mapping, raw: bytes):
    if reviewed_mapping(record, raw) != mapping:
        raise ValueError('Classification decision or source evidence changed')
    if any(record.get(k) not in (None, '') for k in FIELDS):
        raise ValueError('Existing classifications require explicit reconciliation')
    result = copy.deepcopy(record)
    result.update(FunderKey=mapping['FunderKey'],
                  CategoryKeysJSON=json.dumps(mapping['CategoryKeys'], separators=(',', ':')),
                  ClassificationEvidenceJSON=json.dumps(mapping, separators=(',', ':'), sort_keys=True))
    return result


def model_candidate(*args, **kwargs):
    raise ValueError('Model definition preparation is outside this source-only classification packet')
