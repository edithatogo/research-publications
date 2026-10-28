# SPDX-License-Identifier: Apache-2.0
"""Offline description proposals; no field creation, conversion or native calls."""
import argparse
import copy
from pathlib import Path
import sys
if __package__:
    from scripts import prepare_publication_registry_bootstrap as core
else:
    import prepare_publication_registry_bootstrap as core
ROOT=Path(__file__).resolve().parents[1]


def prepare(before,meanings,*,qualification=None):
    s=core.validate_snapshot(before);core.canonical(meanings)
    if (not isinstance(meanings,dict) or not isinstance(meanings.get('fields'),list) or not meanings['fields']):raise ValueError('Versioned field meanings required')
    core.identifier(meanings.get('version'),'meaning version')
    if (not isinstance(qualification,dict) or qualification.get('field_semantics_confirmed') is not True
            or qualification.get('profile_sha256')!=core.sha(meanings) or qualification.get('preimage_sha256')!=core.sha(s)):
        raise ValueError('Independent exact-profile/preimage semantics qualification required')
    core.identifier(qualification.get('reference'),'policy qualification reference')
    core.identifier(qualification.get('writer_semantics_reference'),'timestamp/writer semantics reference')
    seen=set();changes=[]
    for m in meanings['fields']:
        if not isinstance(m,dict) or set(m)!={'name','title','type','description'}:raise ValueError('Exact field-meaning record required')
        name=core.identifier(m['name'],'field name')
        if name in seen:raise ValueError('Duplicate field meaning')
        seen.add(name);f=core.field_named(s,name)
        if f['Title']!=m['title'] or f['TypeAsString']!=m['type'] or f['ReadOnlyField'] or f['Sealed']:raise ValueError('Existing field profile mismatch; no schema changes')
        if f['TypeAsString']=='Note':core.plain_note(f)
        text=core.identifier(m['description'],'plain description')
        if len(text.encode('utf-16-le'))//2>255:raise ValueError('Description exceeds supplied bounded profile')
        if not isinstance(f.get('Description'),str):raise ValueError('Complete original description required')
        if f['Description']!=text:changes.append(dict(id=f['Id'],name=name,before=copy.deepcopy(f),desired={'Description':text}))
    return core.make_plan('publication_field_help_offline_v1',s,{'meanings':meanings,'qualification':qualification},changes)


def reconcile(before,plan,after,*,expected_plan_sha256):
    core.check_plan(plan,before,expected_plan_sha256)
    inputs=plan['inputs'];rebuilt=prepare(before,inputs['meanings'],qualification=inputs['qualification'])
    if not core.same(plan,rebuilt):raise ValueError('Changed description scope')
    core.field_readback(before,plan,after)
    return core.result(before,after,plan,updated_descriptions=len(plan['changes']))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','qualification','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--meanings',type=Path);p.add_argument('--plan',type=Path);p.add_argument('--after',type=Path);p.add_argument('--expected-plan-sha256');a=p.parse_args(argv)
    try:
        s,sh=core.cli_read(a.snapshot,ROOT);q,qh=core.cli_read(a.qualification,ROOT)
        if a.meanings:m,mh=core.cli_read(a.meanings,ROOT)
        else:
            raw=(ROOT/'config/publication-field-meanings.json').read_bytes();m=core.decode_json(raw);mh=core.bytes_sha(raw)
        hashes={'snapshot':sh,'meanings':mh,'qualification':qh}
        value=prepare(s,m,qualification=q)
        if a.after:
            if not a.plan or not a.expected_plan_sha256:raise ValueError('Pinned plan required')
            doc,ph=core.cli_read(a.plan,ROOT);after,ah=core.cli_read(a.after,ROOT);plan=core.cli_plan(doc)
            if not core.same(plan,value):raise ValueError('Policy/preimage changed')
            value=reconcile(s,plan,after,expected_plan_sha256=a.expected_plan_sha256);hashes.update(plan=ph,after=ah)
        elif a.plan or a.expected_plan_sha256:raise ValueError('Incomplete reconciliation arguments')
        core.cli_write(a.output,value,hashes,ROOT);return 0
    except (OSError,ValueError,KeyError,TypeError):print('Offline field-help preparation failed; prior files preserved',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
