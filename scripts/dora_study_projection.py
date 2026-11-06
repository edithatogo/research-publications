"""Local minimal study view from a pinned existing DoRA activity envelope.

No source requests, identity reconciliation, native admission or evidence copying.
SPDX-License-Identifier: Apache-2.0
"""
import hashlib

from scripts.export_dora_activity import build_rows
from scripts.source_capture_receipt import strict_json


def read_directory(directory, expected_receipt_sha256):
    """Read the existing collector format, pinning original receipt bytes."""
    from pathlib import Path
    import json
    directory = Path(directory)
    receipt = (directory / 'receipt.json').read_bytes()
    if hashlib.sha256(receipt).hexdigest() != expected_receipt_sha256:
        raise ValueError('DoRA receipt hash mismatch')
    envelope = strict_json(receipt)
    if 'records' in envelope:
        raise ValueError('Directory receipt must not override records.json')
    envelope['records'] = strict_json((directory / 'records.json').read_bytes())
    return json.dumps(envelope, ensure_ascii=False, allow_nan=False).encode()


def project_dora(raw, expected_sha256):
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('DoRA envelope hash mismatch')
    envelope = strict_json(raw)
    if not isinstance(envelope, dict) or envelope.get('status') != 'succeeded':
        raise ValueError('Successful retained DoRA envelope required')
    if any(not envelope.get(key) for key in ('records_sha256', 'record_id_sha256')):
        raise ValueError('Complete DoRA record and identity hashes required')
    rows = build_rows(envelope)  # Reuses complete count/schema/key/hash/provenance checks.
    projected = []
    for row in rows:
        def text(field):
            value = row[field]
            if value is not None and not isinstance(value, str):
                raise ValueError('DoRA study source fields must be text or null')
            return value
        def scalar(field):
            value = row[field]
            if value is not None and (isinstance(value, bool) or not isinstance(value, (str, int, float))):
                raise ValueError('DoRA identifiers/dates require source scalar or null')
            return value
        flag = text('Clinical Trial (Yes/No)')
        trial = {'yes': True, 'no': False}.get((flag or '').strip().casefold())
        projected.append({
            'SourceKey': row['DORAActivityKey'],
            'StudyIdentifier': row['DORAActivityKey'],
            'SourceProjectID': scalar('Project ID'),  # Not unique, never the row key.
            'Title': text('Full Project Title') or text('Short Project Title'),
            'StudyType': 'Clinical trial' if trial is True else 'Non-trial activity (clinical scope unverified)' if trial is False else None,
            'IsClinicalTrial': trial, 'ClinicalTrialSourceValue': flag,
            'IsInterventionalTrial': None,  # DoRA yes/no alone does not establish design.
            'OverallStatus': None,  # Never infer recruitment status from source dates.
            'SourceURL': row['DORASourceURL'],
            'SourceObservedUTC': row['DORAObservedUTC'],
            'StartDate': scalar('Start Date'), 'CompletionDate': scalar('Finish Date'),
            'SourceSiteName': text('Site Name'),  # Source assertion, not confirmed participation.
            'Conditions': [text('Disease Category')] if text('Disease Category') else [],
            'Interventions': [], 'Countries': [],
        })
    return projected, envelope['observed_at']
