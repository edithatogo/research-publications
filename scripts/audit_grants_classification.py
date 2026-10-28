"""Audit exported opportunity classification coverage; no writes or inference.

This reports transport coverage only. Even complete keys do not prove reviewed
provenance, native propagation, matching acceptance or permission to send.
"""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _key(value):
    return isinstance(value, str) and bool(value) and value == value.strip()


def audit(document):
    rows = document.get('value') if isinstance(document, dict) else document
    if not isinstance(rows, list):
        raise ValueError('Expected an exported row array or native value array')
    seen = set()
    details = []
    for row in rows:
        if not isinstance(row, dict) or not _key(row.get('OpportunityKey')):
            raise ValueError('Every row requires an exact nonblank OpportunityKey')
        key = row['OpportunityKey']
        if key in seen:
            raise ValueError('Duplicate OpportunityKey; coverage is ambiguous')
        seen.add(key)
        errors = []
        funder = row.get('FunderKey')
        if funder not in (None, '') and not _key(funder):
            errors.append('invalid_funder_key')
        categories = row.get('CategoryKeys')
        encoded = row.get('CategoryKeysJSON')
        if encoded not in (None, ''):
            try:
                parsed = json.loads(encoded) if isinstance(encoded, str) else None
            except (ValueError, TypeError):
                parsed = None
            if not isinstance(parsed, list):
                errors.append('invalid_category_json')
            elif categories is not None and categories != parsed:
                errors.append('conflicting_category_representations')
            else:
                categories = parsed
        if categories is None:
            categories = []
        if (not isinstance(categories, list) or any(not _key(x) for x in categories)
                or (isinstance(categories, list) and all(isinstance(x, str) for x in categories)
                    and len(set(categories)) != len(categories))):
            errors.append('invalid_category_keys')
        has_funder = _key(funder)
        has_categories = isinstance(categories, list) and bool(categories) and not errors
        details.append({'OpportunityKey': key, 'funder_key_present': has_funder,
                        'category_keys_present': has_categories,
                        'errors': errors})
    malformed = sum(bool(r['errors']) for r in details)
    covered = sum(r['funder_key_present'] and r['category_keys_present'] and not r['errors'] for r in details)
    return {'status': ('INVALID' if malformed else 'EMPTY_UNQUALIFIED' if not rows
                       else 'KEYS_PRESENT_PROVENANCE_UNQUALIFIED' if covered == len(rows)
                       else 'INCOMPLETE_CLASSIFICATION'),
            'rows': len(rows), 'rows_with_both_key_types': covered,
            'rows_missing_funder_keys': sum(not r['funder_key_present'] for r in details),
            'rows_missing_category_keys': sum(not r['category_keys_present'] for r in details),
            'malformed_rows': malformed, 'details': details,
            'reviewed_provenance_accepted': False, 'native_propagation_accepted': False,
            'notification_activation_authorized': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('readback', type=Path)
    args = parser.parse_args()
    result = audit(json.loads(args.readback.read_text()))
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'KEYS_PRESENT_PROVENANCE_UNQUALIFIED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
