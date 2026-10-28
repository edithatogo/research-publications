# SPDX-License-Identifier: Apache-2.0
"""Offline same-field index proposals; no uniqueness/performance or native claim."""
import argparse
import copy
from collections import defaultdict
from pathlib import Path
import re
import sys
if __package__:
    from scripts import prepare_publication_registry_bootstrap as core
else:
    import prepare_publication_registry_bootstrap as core
ROOT=Path(__file__).resolve().parents[1]
FIELDS=[('field_1','SourceKey'),('field_2','CanonicalKey'),('field_10','PMID'),('field_6','PublicationMonth'),('field_17','ReviewStatus')]


def integrity(rows):
    exact=defaultdict(list);folded=defaultdict(list);blanks=[]
    for row in rows:
        key=row.get('field_1')
        if key in (None,''):blanks.append(row['Id'])
        else:
            core.identifier(key,'SourceKey');exact[key].append(row['Id']);folded[key.casefold()].append(row['Id'])
    return dict(blank_source_keys=len(blanks),placeholder_ids=sorted(blanks),
        exact_duplicate_ids=[v for v in exact.values() if len(v)>1],casefold_collisions=[v for v in folded.values() if len(v)>1],
        required_or_unique_change_proposed=False)


def month(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{4}-(?:0[1-9]|1[0-2])',value) or value[:4]=='0000':raise ValueError('Explicit ASCII YYYY-MM period required')
    return value


def queries(before,period=None):
    rows=before['items'];specs=[];unavailable=[]
    quote=lambda s:"'"+s.replace("'","''")+"'"
    candidates=[r for r in rows if isinstance(r.get('field_1'),str) and r['field_1'] and isinstance(r.get('field_2'),str) and r['field_2'] and isinstance(r.get('field_10'),str) and re.fullmatch(r'[1-9][0-9]*',r['field_10'])]
    if candidates:
        r=min(candidates,key=lambda v:v['Id']);key,canonical,pmid=(r[n] for n in ('field_1','field_2','field_10'))
        for name,field,value in [('source_key','field_1',key),('canonical_key','field_2',canonical),('pmid','field_10',pmid)]:
            specs.append(dict(name=name,filter=field+' eq '+quote(value),expected_ids=sorted(r['Id'] for r in rows if r.get(field)==value)))
        specs.append(dict(name='writer_alias_or',filter=f'field_1 eq {quote(key)} or field_2 eq {quote(canonical)} or field_10 eq {quote(pmid)}',expected_ids=sorted(r['Id'] for r in rows if r.get('field_1')==key or r.get('field_2')==canonical or r.get('field_10')==pmid)))
    else:unavailable.append('positive_pmid_sample_unavailable')
    missing='__RIMS_INDEX_READ_ONLY_MISSING__'
    if not any(r.get('field_1')==missing for r in rows):specs.append(dict(name='missing_key',filter='field_1 eq '+quote(missing),expected_ids=[]))
    else:unavailable.append('missing_probe_not_absent')
    if period is not None:
        if not isinstance(period,list) or len(period)!=2 or month(period[0])>=month(period[1]):raise ValueError('Ordered explicit period bounds required')
        start,end=period
        for r in rows:
            if r.get('field_6') not in (None,''):month(r['field_6'])
        specs.append(dict(name='publication_month',filter=f'field_6 ge {quote(start)} and field_6 lt {quote(end)}',expected_ids=sorted(r['Id'] for r in rows if r.get('field_6') and start<=r['field_6']<end)))
    else:unavailable.append('configured_period_unavailable')
    specs.append(dict(name='status',filter="field_17 eq 'Needs Review'",expected_ids=sorted(r['Id'] for r in rows if r.get('field_17')=='Needs Review')))
    return specs,unavailable


def prepare(before,*,index_budget,period=None):
    s=core.validate_snapshot(before)
    if type(index_budget) is not int or index_budget<1:raise ValueError('Explicit qualified index budget required')
    changes=[]
    for name,title in FIELDS:
        f=core.field_named(s,name)
        if f['Title']!=title or f['TypeAsString']!='Text' or f['ReadOnlyField'] or f['Sealed']:raise ValueError('Existing index field mismatch; no type changes')
        if not f['Indexed']:changes.append(dict(id=f['Id'],name=name,before=copy.deepcopy(f),desired={'Indexed':True}))
    if sum(f['Indexed'] for f in s['fields'])+len(changes)>index_budget:raise ValueError('Supplied index budget exceeded')
    info=integrity(s['items'])
    if info['blank_source_keys'] and core.field_named(s,'field_1')['Required']:raise ValueError('Existing required constraint conflicts with captured blanks; no relaxation')
    q,gaps=queries(s,period)
    return core.make_plan('publication_indexes_offline_v1',s,{'index_budget':index_budget,'period':period},changes,
        dict(integrity=info,queries=q,unavailable_queries=gaps,uniqueness_proven=False,performance_proven=False))


def reconcile(before,plan,after,results,*,expected_plan_sha256):
    core.check_plan(plan,before,expected_plan_sha256)
    if not core.same(plan,prepare(before,**plan['inputs'])):raise ValueError('Changed index scope')
    core.field_readback(before,plan,after)
    expected={q['name']:q['expected_ids'] for q in plan['details']['queries']}
    core.check_queries(before,plan,after,results,expected)
    return core.result(before,after,plan,indexed_fields=len(plan['changes']),query_results_sha256=core.sha(results),
        unavailable_queries=copy.deepcopy(plan['details']['unavailable_queries']),uniqueness_proven=False,performance_proven=False)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--index-budget',type=int,required=True);p.add_argument('--period',nargs=2);p.add_argument('--after',type=Path);p.add_argument('--plan',type=Path);p.add_argument('--query-results',type=Path);p.add_argument('--expected-plan-sha256');a=p.parse_args(argv)
    try:
        s,h=core.cli_read(a.snapshot,ROOT);hashes={'snapshot':h};value=prepare(s,index_budget=a.index_budget,period=a.period)
        if a.after:
            if not a.plan or not a.query_results or not a.expected_plan_sha256:raise ValueError('Pinned complete reconciliation inputs required')
            doc,ph=core.cli_read(a.plan,ROOT);after,ah=core.cli_read(a.after,ROOT);results,rh=core.cli_read(a.query_results,ROOT);plan=core.cli_plan(doc)
            if not core.same(value,plan):raise ValueError('Changed policy/preimage')
            value=reconcile(s,plan,after,results,expected_plan_sha256=a.expected_plan_sha256);hashes.update(plan=ph,after=ah,query_results=rh)
        elif a.plan or a.query_results or a.expected_plan_sha256:raise ValueError('Incomplete reconciliation arguments')
        core.cli_write(a.output,value,hashes,ROOT);return 0
    except (OSError,ValueError,KeyError,TypeError):print('Offline index preparation failed; prior files preserved',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
