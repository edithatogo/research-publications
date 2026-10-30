"""Bounded outcome journal persistence using an existing SharePoint item's ETag.

Transport is supplied by the native owner. No authentication, retry, activation or
schema provisioning occurs here. One item holds a bounded complete journal so a
revision cannot commit separately from its predecessor. This is a candidate
adapter, not evidence of an available or provisioned native register.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import base64
import copy
import hashlib
import json
import sys
from pathlib import Path
if not __package__: sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.outcome_evidence import intake, project, _unique_object, _constant

MAX_CHARS = 60000  # Conservative bounded slice; never silently split a journal.


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def restore(journal):
    if not isinstance(journal, dict) or set(journal) != {'version', 'entries'} or journal['version'] != 1:
        raise ValueError('Unsupported journal envelope')
    if not isinstance(journal['entries'], list):
        raise ValueError('Complete journal entries required')
    history = ()
    for entry in journal['entries']:
        if not isinstance(entry, dict) or set(entry) != {'source_base64', 'references', 'human_edits'}:
            raise ValueError('Incomplete journal entry')
        raw = base64.b64decode(entry['source_base64'], validate=True)
        updated, receipt = intake(history, raw, entry['references'], human_edits=entry['human_edits'])
        if receipt['status'] != 'new_revision':
            raise ValueError('Duplicate journal revision')
        history = updated
    return history


def prepare(snapshot, source, references, *, human_edits=None):
    """Prepare a single conditional item update from a complete owner readback.

    snapshot uses logical fields: item_id, etag, journal. Native field mapping and
    exact target remain in the owner's private binding. Empty journals must be
    provisioned separately; absence is never treated as an empty store.
    """
    if set(snapshot) != {'item_id', 'etag', 'journal'}:
        raise ValueError('Complete item snapshot required')
    if type(snapshot['item_id']) is not int or snapshot['item_id'] <= 0:
        raise ValueError('Exact existing item ID required')
    etag = snapshot['etag']
    if not isinstance(etag, str) or not etag or etag == '*':
        raise ValueError('Exact ETag required; wildcard forbidden')
    history = restore(snapshot['journal'])
    _, receipt = intake(history, source, references, human_edits=human_edits)
    candidate = copy.deepcopy(snapshot['journal'])
    if receipt['status'] == 'new_revision':
        candidate['entries'].append({'source_base64': base64.b64encode(source).decode(),
                                    'references': copy.deepcopy(references),
                                    'human_edits': copy.deepcopy(human_edits)})
    payload = encode(candidate)
    if len(payload.encode('utf-16-le')) // 2 > MAX_CHARS:
        raise ValueError('Bounded journal capacity exceeded; no truncation or automatic migration')
    return {'item_id': snapshot['item_id'], 'etag': etag,
            'before_sha256': digest(snapshot['journal']), 'after_sha256': digest(candidate),
            'journal': candidate, 'operation': 'noop' if receipt['status'] == 'unchanged_replay' else 'update',
            'native_persistence_proved': False}


def reconcile(plan, snapshot):
    """Resolve uncertain writes from actual readback; never retry a mutation."""
    if snapshot['item_id'] != plan['item_id']:
        raise ValueError('Readback item identity mismatch')
    restore(snapshot['journal'])
    actual = digest(snapshot['journal'])
    if actual == plan['after_sha256']:
        return 'candidate_present'
    if actual == plan['before_sha256'] and snapshot['etag'] == plan['etag']:
        return 'preimage_present'
    return 'conflict'


def apply_once(plan, transport):
    """Transport exposes read(item_id), compare_and_set(item_id, etag, journal).

    compare_and_set MUST use server-enforced If-Match, update only the bound
    journal field and disable mutation retries/redirects. Transport errors are
    reconciled by readback; this function never submits a second write.
    """
    restore(plan['journal'])
    if digest(plan['journal']) != plan['after_sha256']:
        raise ValueError('Candidate hash mismatch')
    before = transport.read(plan['item_id'])
    state = reconcile(plan, before)
    if state == 'candidate_present':
        return {'outcome': 'unchanged_replay', 'writes': 0}
    if state != 'preimage_present':
        raise ValueError('Concurrent edit; preserve current item')
    if plan['operation'] != 'update':
        raise ValueError('Invalid no-op plan')
    error = None
    try:
        transport.compare_and_set(plan['item_id'], plan['etag'], copy.deepcopy(plan['journal']))
    except Exception as exc:
        error = type(exc).__name__  # Never leak response bodies or credentials.
    try:
        state = reconcile(plan, transport.read(plan['item_id']))
    except Exception:
        return {'outcome': 'unknown', 'writes': 1, 'error_type': error, 'retry_allowed': False}
    return {'outcome': state, 'writes': 1, 'error_type': error, 'retry_allowed': False}


def reporting_tables(journal, references, **context):
    """Reuse eligibility and redaction; expose facts/bridges without a fan-out join."""
    result = project(restore(journal), references, **context)
    return {'context': result['context'], 'TranslationEvent': result['translation_events'],
            'EventProject': result['event_project_bridge'],
            'OutcomeObservation': result['outcome_aggregates'],
            'ObservationProject': result['observation_project_bridge'],
            'OutcomeEvidenceDetail': result['details'], 'native_persistence_proved': False}


def load_snapshot(raw):
    return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_constant)


def schema_plan(capture, *, expected_sha256, field_name):
    """Compare a complete owner-captured field inventory; do not provision it."""
    import re
    from datetime import datetime
    from xml.sax.saxutils import quoteattr
    if digest(capture) != expected_sha256 or capture.get('complete') is not True:
        raise ValueError('Complete hash-bound schema capture required')
    if not capture.get('list_id') or not capture.get('source'):
        raise ValueError('Exact list identity and capture provenance required')
    captured = datetime.fromisoformat(capture['captured_at'].replace('Z', '+00:00'))
    if captured.tzinfo is None:
        raise ValueError('Capture timezone required')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,31}', field_name):
        raise ValueError('Supported internal field name required')
    fields = capture['fields']
    names = [f['InternalName'] for f in fields]
    if len(names) != len(set(n.casefold() for n in names)):
        raise ValueError('Ambiguous duplicate field inventory')
    matches = [f for f in fields if f['InternalName'].casefold() == field_name.casefold()]
    changes = []
    if matches:
        field = matches[0]
        if (field['InternalName'] != field_name or field.get('TypeAsString') != 'Note'
                or field.get('RichText') is not False or field.get('AppendOnly') is not False
                or field.get('ReadOnlyField') is not False):
            raise ValueError('Existing field is incompatible; never rewrite its schema')
    else:
        changes.append({'operation': 'add_field', 'schema_xml': '<Field Type="Note" Name='+quoteattr(field_name)+' DisplayName='+quoteattr(field_name)+' RichText="FALSE" AppendOnly="FALSE" />'})
    return {'list_id': capture['list_id'], 'source': capture['source'], 'captured_at': capture['captured_at'],
            'schema_sha256': expected_sha256, 'field_name': field_name, 'changes': changes,
            'indexes': [], 'index_reason': 'Existing item is addressed by native ID; no Note-field index.',
            'deployment_ready': False, 'requires_current_owner_readback': True}


def main(argv=None):
    import argparse
    from pathlib import Path
    import subprocess
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'project', 'schema'])
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--source')
    parser.add_argument('--references')
    parser.add_argument('--human-edits')
    parser.add_argument('--context')
    parser.add_argument('--field-name')
    parser.add_argument('--expected-sha256')
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    def read(path):
        if not path: raise ValueError('Missing input path')
        return load_snapshot(Path(path).read_bytes())
    snapshot = read(args.snapshot)
    if args.action == 'prepare':
        if not args.source: raise ValueError('Exact source file required')
        result = prepare(snapshot, Path(args.source).read_bytes(), read(args.references),
                         human_edits=read(args.human_edits) if args.human_edits else None)
    elif args.action == 'project':
        result = reporting_tables(snapshot['journal'], read(args.references), **read(args.context))
    else:
        result = schema_plan(snapshot, expected_sha256=args.expected_sha256, field_name=args.field_name or '')
    root = Path(__file__).resolve().parents[1]
    output = Path(args.output).resolve()
    if not output.is_relative_to(root / 'private' / 'ops'):
        raise ValueError('Output must be private/ops inside this checkout')
    subprocess.run(['git', 'check-ignore', '-q', str(output)], cwd=root, check=True)
    import os
    with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as handle:
        handle.write(encode(result)+'\n')
    print('PASS_LOCAL_ONLY; native acceptance not evaluated')


if __name__ == '__main__':
    main()
