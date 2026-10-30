"""Persist project/output revisions through the existing paired-field CLI store.

SPDX-License-Identifier: Apache-2.0
"""
import argparse
import json
import os
from pathlib import Path
import sys
from scripts.deploy_report_definition import strict
from scripts.project_output_links import append_revision, project_history
from scripts.outcome_intake import QualifiedStore, save, ROOT


def prepare(snapshot, revision):
    journal = strict(snapshot['journal'].encode())
    projection = strict(snapshot['projection'].encode())
    if set(journal) != {'history', 'inventories', 'complete'}:
        raise ValueError('Complete stored project-link envelope required')
    expected = project_history(journal['history'], journal['inventories'], complete=journal['complete'])
    if expected != projection:
        raise ValueError('Human-edited projection or journal; reconcile before writing')
    history = append_revision(journal['history'], **revision)
    updated = {'history': history, 'inventories': revision['inventories'], 'complete': revision['complete']}
    result = project_history(history, revision['inventories'], complete=revision['complete'])
    after = {'journal': json.dumps(updated, ensure_ascii=False, separators=(',', ':'), allow_nan=False),
             'projection': json.dumps(result, ensure_ascii=False, separators=(',', ':'), allow_nan=False)}
    if any(len(v.encode('utf-16-le'))//2 > 60000 for v in after.values()):
        raise ValueError('Bounded field capacity exceeded; no write')
    return {'operation':'apply', 'etag':snapshot['etag'],
            'before':{k:snapshot[k] for k in after}, 'after':after}


def main():
    if sys.version_info[:3] != (3,15,1): raise RuntimeError('Qualified repository Python 3.15.1 required')
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('binding','target','input','output'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    target=strict(Path(args.target).read_bytes())
    if target.get('journalField')!='ProjectLinkJournal' or target.get('projectionField')!='ProjectLinkProjection':
        raise ValueError('Dedicated project-link fields required')
    directory=Path(args.output).resolve()
    if not directory.is_relative_to(ROOT/'private/ops'):raise ValueError('Private output required')
    os.umask(0o077);directory.mkdir(mode=0o700)
    revision=strict(Path(args.input).read_bytes())
    store=QualifiedStore(args.binding,directory,args.target)
    snapshot=store.execute({'operation':'read'})['snapshot']
    plan=prepare(snapshot,revision);save(directory/'candidate.json',plan)
    result=store.execute(plan) if args.apply else {'outcome':'prepared','writes':0}
    save(directory/'result.json',result)
    print(json.dumps({'outcome':result['outcome'],'writes':result['writes']}))


if __name__=='__main__':main()
