"""Prepare complete Power BI definition update/recovery packets without tokens.

Native execution belongs to the existing authenticated owner. This replaces the
historical browser-session-token deploy entrypoint; it never calls a service.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
from uuid import UUID


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def parts(document):
    if not isinstance(document, dict) or set(document) != {'definition'}:
        raise ValueError('Complete definition envelope required; metadata updates excluded')
    definition = document['definition']
    if (not isinstance(definition, dict) or set(definition) - {'parts', 'format'}
            or not isinstance(definition.get('parts'), list) or not definition['parts']
            or ('format' in definition and (not isinstance(definition['format'], str) or not definition['format']))):
        raise ValueError('Nonempty complete parts required')
    result = {}
    for part in definition['parts']:
        if set(part) != {'path', 'payload', 'payloadType'} or part['payloadType'] != 'InlineBase64':
            raise ValueError('Supported InlineBase64 part required')
        path = part['path']
        if not isinstance(path, str) or not path or '\\' in path or PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts or path != str(PurePosixPath(path)):
            raise ValueError('Unsafe part path')
        if path.casefold() in {key.casefold() for key in result}:
            raise ValueError('Duplicate part identity')
        result[path] = base64.b64decode(part['payload'], validate=True)
    return result


def prepare(before, candidate, *, expected_sha256, changed_paths, workspace_id, item_id, kind, scope):
    if scope != 'isolated' or kind not in {'reports', 'semanticModels'}:
        raise ValueError('Explicit isolated report/model target required')
    UUID(workspace_id); UUID(item_id)
    if fingerprint(before) != expected_sha256:
        raise ValueError('Preimage hash mismatch')
    original, updated = parts(before), parts(candidate)
    if not set(original) <= set(updated):
        raise ValueError('Omitted parts would delete existing content')
    actual = sorted(p for p in updated if updated[p] != original.get(p))
    if len(changed_paths) != len(set(changed_paths)) or sorted(changed_paths) != actual:
        raise ValueError('Exact reviewed semantic part delta required')
    if any(p in actual for p in ('definition.pbir', '.platform')):
        raise ValueError('Binding/identity changes require a separately reviewed route')
    return {'endpoint': f'https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/{kind}/{item_id}/updateDefinition',
            'before_sha256': expected_sha256, 'candidate_sha256': fingerprint(candidate),
            'changed_paths': actual, 'candidate': candidate, 'recovery': before,
            'native_ready': False, 'qualification_required': [
                'current exact-target same-client permissions and non-premium eligibility',
                'complete current preimage, consumer inventory and single native writer',
                'no-retry/no-redirect mutation transport and durable one-send journal',
                'terminal operation state and complete definition readback'],
            'manual_acceptance': 'Changed-page rendering and interaction; source validation does not prove these.'}


def strict(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value: raise ValueError('Duplicate JSON key')
            value[key] = item
        return value
    def constant(value): raise ValueError('Non-finite JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('preimage', 'candidate', 'expected-sha256', 'workspace-id', 'item-id', 'output'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--kind', choices=['reports', 'semanticModels'], required=True)
    parser.add_argument('--scope', choices=['isolated'], required=True)
    parser.add_argument('--changed-path', action='append', default=[])
    args = parser.parse_args(argv)
    before = strict(Path(args.preimage).read_bytes()); candidate = strict(Path(args.candidate).read_bytes())
    packet = prepare(before, candidate, expected_sha256=args.expected_sha256, changed_paths=args.changed_path,
                     workspace_id=args.workspace_id, item_id=args.item_id, kind=args.kind, scope=args.scope)
    root = Path(__file__).resolve().parents[1]; output = Path(args.output).resolve()
    if not output.is_relative_to(root / 'private' / 'ops'):
        raise ValueError('Packet must remain under checkout private/ops')
    subprocess.run(['git', 'check-ignore', '-q', str(output)], cwd=root, check=True)
    with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as handle:
        json.dump(packet, handle, indent=2, allow_nan=False)
    print('PASS_LOCAL_ONLY: packet prepared; native execution not performed')


if __name__ == '__main__': main()
