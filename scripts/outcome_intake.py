"""Dynamic outcome intake through the retained qualified M365 client.

One complete record batch becomes one ETag-protected journal/projection update.
No login, provisioning, flow invocation, refresh, retry or activation is implicit.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
if not __package__: sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.outcome_persistence import prepare, restore, reporting_tables, encode, load_snapshot, digest

ROOT = Path(__file__).resolve().parents[1]


def prepare_batch(snapshot, records, references, context):
    """Revalidate every supplied revision; project only the complete final history.

    records contain exact source bytes plus optional explicit protected edits.
    A bad last record rejects the whole batch before any native call.
    """
    if set(snapshot) != {'item_id', 'etag', 'journal', 'projection'}:
        raise ValueError('Complete paired-field snapshot required')
    journal = load_snapshot(snapshot['journal'])
    restore(journal)
    if not records:
        raise ValueError('At least one explicit record required')
    for source, edits in records:
        plan = prepare(dict(item_id=snapshot['item_id'], etag=snapshot['etag'], journal=journal),
                       source, references, human_edits=edits)
        journal = plan['journal']
    tables = reporting_tables(journal, references, **context)
    # Bind the projection to the exact journal while preserving the reader's
    # existing top-level table contract. Both values share one server update.
    tables['journal_sha256'] = digest(journal)
    after = {'journal': encode(journal), 'projection': encode(tables)}
    if any(len(value.encode('utf-16-le')) // 2 > 60000 for value in after.values()):
        raise ValueError('Bounded journal/projection capacity exceeded')
    return {'operation': 'apply', 'etag': snapshot['etag'],
            'before': {key: snapshot[key] for key in after}, 'after': after}


def recovery_plan(original, current):
    """Recover both exact field preimages only if the candidate is still current."""
    if any(current[key] != original['after'][key] for key in ('journal', 'projection')):
        raise ValueError('Intervening edit; automatic recovery refused')
    return {'operation': 'apply', 'etag': current['etag'],
            'before': original['after'], 'after': original['before']}


def save(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as handle:
        handle.write(encode(value)+'\n'); handle.flush(); os.fsync(handle.fileno())


class QualifiedStore:
    def __init__(self, binding, directory):
        self.binding, self.directory, self.ordinal = Path(binding).resolve(), Path(directory).resolve(), 0

    def execute(self, plan):
        self.ordinal += 1
        plan_path = self.directory / f'plan-{self.ordinal}.json'
        receipt_path = self.directory / f'operation-{self.ordinal}'
        save(plan_path, plan)
        result = subprocess.run(['node', str(ROOT/'scripts/m365-qualified.mjs'), 'outcome-store',
                                 str(self.binding), str(plan_path), str(receipt_path)], cwd=ROOT,
                                capture_output=True, text=True)
        # The wrapper writes only bounded summaries here, never tokens. Detailed
        # HTTP bodies stay inside its private readback files.
        (self.directory / f'command-{self.ordinal}.log').write_text(result.stdout + result.stderr)
        result_file = receipt_path / 'result.json'
        if not result_file.exists():
            raise RuntimeError('Qualified transport stopped; inspect private receipt, do not resubmit')
        receipt = load_snapshot(result_file.read_bytes())
        if result.returncode or receipt['outcome'] not in {'read', 'candidate_present', 'unchanged_replay'}:
            raise RuntimeError('Native outcome unresolved; inspect receipt and reconcile without resubmission')
        return receipt


def run(store, records, references, context, *, apply=False):
    snapshot = store.execute({'operation': 'read'})['snapshot']
    plan = prepare_batch(snapshot, records, references, context)
    if not apply:
        return {'plan': plan, 'outcome': 'prepared', 'writes': 0}
    result = store.execute(plan)
    return {'plan': plan, 'result': result, 'outcome': result['outcome'],
            'writes': result['writes'], 'native_runtime_proved': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binding', 'output'):
        parser.add_argument('--'+name, required=True)
    for name in ('references','context','records'): parser.add_argument('--'+name)
    parser.add_argument('--recover-plan', help='Original paired-field plan; prepare conditional recovery from a fresh read')
    parser.add_argument('--apply', action='store_true', help='Apply one conditional paired-field update; default prepares only')
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    if not output.is_relative_to(ROOT/'private/ops'):
        raise ValueError('Private output directory required')
    subprocess.run(['git', 'check-ignore', '-q', str(output)], cwd=ROOT, check=True)
    os.umask(0o077)
    if args.recover_plan:
        if any((args.references,args.context,args.records)):
            raise ValueError('Recovery and new intake inputs are mutually exclusive')
        original = load_snapshot(Path(args.recover_plan).read_bytes())
        output.mkdir(mode=0o700)
        store = QualifiedStore(args.binding,output)
        current = store.execute({'operation':'read'})['snapshot']
        plan = recovery_plan(original,current)
        save(output/'recovery-plan.json',plan)
        result = store.execute(plan) if args.apply else {'outcome':'recovery_prepared','writes':0}
        save(output/'recovery-result.json',result)
        print(json.dumps({'outcome':result['outcome'],'writes':result['writes']}))
        return
    if not all((args.references,args.context,args.records)):
        raise ValueError('New intake needs records, references and projection context')
    references = load_snapshot(Path(args.references).read_bytes())
    context = load_snapshot(Path(args.context).read_bytes())
    manifest_path = Path(args.records).resolve()
    manifest = load_snapshot(manifest_path.read_bytes())
    records = []
    identities = []
    for entry in manifest:
        if set(entry) - {'path', 'human_edits'} or 'path' not in entry:
            raise ValueError('Record manifest requires path and optional human_edits')
        source = (manifest_path.parent/entry['path']).read_bytes()
        records.append((source, entry.get('human_edits')))
        identities.append({'sha256': hashlib.sha256(source).hexdigest()})
    output.mkdir(mode=0o700)
    save(output/'inputs.json', {'records': identities, 'references_sha256': digest(references), 'context': context})
    result = run(QualifiedStore(args.binding, output), records, references, context, apply=args.apply)
    save(output/'intake-result.json', result)
    print(json.dumps({'outcome': result['outcome'], 'writes': result['writes']}))


if __name__ == '__main__': main()
