"""Prepare bounded typed Grant Relationships writes using the existing revision ledger.

No source admission or review approval is inferred from persistence.
SPDX-License-Identifier: Apache-2.0
"""
import argparse
import json
import os
from pathlib import Path
import sys

from scripts.deploy_report_definition import strict
from scripts.grants_relationships import RELATIONSHIP_FIELDS
from scripts.relationship_revisions import append, validate_history

JOURNAL = 'RelationshipHistory'
FIELDS = sorted(RELATIONSHIP_FIELDS) + [JOURNAL]


def project(history, previous=None):
    heads = validate_history(history)
    if len(heads) != 1:
        raise ValueError('Exactly one relationship lineage per native item required')
    entry = history[-1]
    if 'RelationshipKind' in entry['record']:
        raise ValueError('Source assertions have no Grant Relationships admission')
    fields = dict(entry['record'])
    if entry['state'] == 'withdrawn':
        fields.update(ReviewStatus='Withdrawn', Confidence='review')
    url = fields['EvidenceURL']
    old = (previous or {}).get('EvidenceURL', {})
    fields['EvidenceURL'] = old if isinstance(old, dict) and old.get('Url') == url else {'Url': url, 'Description': url}
    fields[JOURNAL] = json.dumps(history, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    if len(fields[JOURNAL].encode('utf-16-le')) // 2 > 60000:
        raise ValueError('Relationship journal exceeds bounded field capacity')
    return fields


def prepare(snapshot, revision):
    before = snapshot['fields'] if snapshot else None
    if before and not before.get(JOURNAL):
        raise ValueError('Legacy relationship has no revision ledger; explicit adoption is separate')
    history = strict(before[JOURNAL].encode()) if before else []
    if before and project(history, before) != before:
        raise ValueError('Human-edited projection differs from history; reconcile before writing')
    updated = append(history, **revision)
    plan = {'operation': 'apply', 'item_id': snapshot['item_id'] if snapshot else None,
            'etag': snapshot['etag'] if snapshot else None, 'before': before,
            'after': project(updated, before)}
    validate_plan(plan)
    return plan


def validate_plan(plan):
    if set(plan) != {'operation', 'item_id', 'etag', 'before', 'after'} or plan['operation'] != 'apply':
        raise ValueError('Exact relationship write plan required')
    after = plan['after']
    if set(after) != set(FIELDS):
        raise ValueError('Exact typed relationship fields required')
    history = strict(after[JOURNAL].encode())
    if project(history, plan['before']) != after:
        raise ValueError('Projection/history mismatch')
    before = plan['before']
    if before is None:
        if plan['item_id'] is not None or plan['etag'] is not None or len(history) != 1:
            raise ValueError('New item must begin one lineage')
        if history[0]['record']['Confidence'] == 'confirmed':
            raise ValueError('New confirmed admission requires the existing review workflow')
    else:
        if set(before) != set(FIELDS) or type(plan['item_id']) is not int or plan['item_id'] < 1:
            raise ValueError('Complete existing item preimage required')
        import re
        if not isinstance(plan['etag'], str) or not re.fullmatch(r'(?:W/)?"[^"\r\n]+"', plan['etag']):
            raise ValueError('Exact ETag required')
        old = strict(before[JOURNAL].encode())
        if project(old, before) != before or history[:len(old)] != old or len(history) not in {len(old), len(old)+1}:
            raise ValueError('Preserve complete history and human edits; append at most one revision')
        if len(history) > len(old):
            e = history[-1]
            expected = append(old, e['record'], revision_id=e['revision_id'], supersedes=e['supersedes'], state=e['state'], reason=e['reason'])
            if expected != history:
                raise ValueError('Invalid revision transition')
    return plan


def main():
    if sys.version_info[:3] != (3, 15, 1):
        raise RuntimeError('Use the qualified repository Python 3.15.1')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input'); parser.add_argument('--output'); parser.add_argument('--validate-plan')
    args = parser.parse_args()
    if args.validate_plan:
        validate_plan(strict(Path(args.validate_plan).read_bytes()))
        return
    inputs = strict(Path(args.input).read_bytes())
    plan = prepare(**inputs)
    output = Path(args.output).resolve()
    if not output.is_relative_to(Path(__file__).resolve().parents[1] / 'private' / 'ops'):
        raise ValueError('Private output required')
    with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        json.dump(plan, f, indent=2, allow_nan=False)
    print('Prepared relationship candidate; no native write')


if __name__ == '__main__':
    main()
