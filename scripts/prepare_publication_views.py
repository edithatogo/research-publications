# SPDX-License-Identifier: Apache-2.0
"""Offline fixed-period reader-view proposals; no native mutation or rollover."""
import argparse
import copy
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
if __package__:
    from scripts import prepare_publication_registry_bootstrap as core
    from scripts.prepare_publication_indexes import month
else:
    import prepare_publication_registry_bootstrap as core
    from prepare_publication_indexes import month
ROOT=Path(__file__).resolve().parents[1]
ROLES={'publications','month','uncertainty','placeholders'}
COLUMNS=['LinkTitle','SourceFullTitle','field_1','field_2','field_5','field_6','field_8','field_17','field_18']


def previous_month(as_of):
    core.identifier(as_of,'period as-of')
    if as_of.endswith('-00:00'):raise ValueError('Unknown offset is not a configured period')
    now=datetime.fromisoformat(as_of.replace('Z','+00:00'))
    if now.utcoffset() is None:raise ValueError('Explicit timezone required')
    now=now.astimezone(ZoneInfo('Australia/Brisbane'))
    return f'{now.year-(now.month==1):04d}-{(now.month-2)%12+1:02d}',f'{now.year:04d}-{now.month:02d}'


def expected_ids(rows,start,end):
    month(start);month(end)
    if start>=end:raise ValueError('Ordered period required')
    result={role:[] for role in ROLES}
    for row in rows:
        key=row.get('field_1');period=row.get('field_6');status=row.get('field_17')
        if period not in (None,''):month(period)
        if status is not None and not isinstance(status,str):raise ValueError('Unqualified review label type')
        if key in (None,''):result['placeholders'].append(row['Id'])
        else:
            core.identifier(key,'SourceKey')
            if status!='Excluded':
                result['publications'].append(row['Id'])
                if period in (None,''):result['uncertainty'].append(row['Id'])
                elif start<=period<end:result['month'].append(row['Id'])
    return {role:sorted(ids) for role,ids in result.items()}


def definitions(start,end):
    month(start);month(end)
    keyed='<IsNotNull><FieldRef Name="field_1" /></IsNotNull>'
    admitted='<Or><IsNull><FieldRef Name="field_17" /></IsNull><Neq><FieldRef Name="field_17" /><Value Type="Text">Excluded</Value></Neq></Or>'
    register=f'<And>{keyed}{admitted}</And>'
    period=f'<And><Geq><FieldRef Name="field_6" /><Value Type="Text">{start}</Value></Geq><Lt><FieldRef Name="field_6" /><Value Type="Text">{end}</Value></Lt></And>'
    predicates={'publications':register,'month':f'<And>{register}{period}</And>',
        'uncertainty':f'<And>{register}<IsNull><FieldRef Name="field_6" /></IsNull></And>',
        'placeholders':'<IsNull><FieldRef Name="field_1" /></IsNull>'}
    titles={'publications':'Publications | Keyed register','month':f'Past Month Publications | {start} (configured)',
        'uncertainty':'Publications | Month uncertain','placeholders':'Retained placeholders | No SourceKey'}
    return {role:dict(Title=titles[role],ViewQuery=f'<Where>{query}</Where><OrderBy><FieldRef Name="ID" Ascending="FALSE" /></OrderBy>',Paged=True,RowLimit=100) for role,query in predicates.items()}


def prepare(before,as_of,bindings):
    s=core.validate_snapshot(before);core.qualify_full_title(s)
    if not isinstance(bindings,dict) or set(bindings)!=ROLES:raise ValueError('Explicit complete role bindings required')
    assigned=[v for v in bindings.values() if v is not None]
    for identity in assigned:core.guid(identity)
    if len(assigned)!=len(set(assigned)):raise ValueError('View bindings must be distinct')
    names={f['InternalName'] for f in s['fields']}
    if not set(COLUMNS)<=names:raise ValueError('Existing reader columns required; no field creation')
    for name in ('field_1','field_6','field_17'):
        if core.field_named(s,name)['TypeAsString']!='Text':raise ValueError('Existing reader filter types mismatch')
    start,end=previous_month(as_of);wanted=definitions(start,end);old=core.by_id(s['views']);changes=[]
    for role in sorted(ROLES):
        identity=bindings[role];v=old.get(identity) if identity is not None else None
        if identity is not None and v is None:raise ValueError('Bound view missing; no identity guessing')
        if v is not None and (v['DefaultView'] or v['PersonalView'] or v['Hidden']):raise ValueError('Protected view cannot be replaced')
        desired=wanted[role]
        if v is None or any(not core.same(v.get(k),value) for k,value in desired.items()):
            changes.append(dict(role=role,id=identity,before=copy.deepcopy(v),desired=copy.deepcopy(desired),
                fields=copy.deepcopy(v['resolvedFields']['Items']['results'] if v else COLUMNS)))
    return core.make_plan('publication_views_offline_v1',s,{'as_of':as_of,'bindings':bindings},changes,
        {'start':start,'end_exclusive':end,'timezone':'Australia/Brisbane','automatic_rollover':False,
         'expected_ids':expected_ids(s['items'],start,end),'population':'keyed retained rows excluding explicit Excluded; not accepted-canonical totals'})


def check_view_change(old,new,desired,columns):
    if new['DefaultView'] or new['PersonalView'] or new['Hidden'] or new['resolvedFields']['Items']['results']!=columns:raise ValueError('View privacy/default/columns changed')
    for key,value in desired.items():
        if not core.same(new.get(key),value):raise ValueError('Desired view setting not saved')
    if old is not None:
        expected=copy.deepcopy(old);expected.update(copy.deepcopy(desired))
        core.allow_metadata_etag(old['__metadata'],new['__metadata']);expected['__metadata']=copy.deepcopy(new['__metadata'])
        if not core.same(expected,new):raise ValueError('Unrelated view property/formatter/XML changed')


def view_readback(before,after,changes,created):
    a,b=core.postimage(before,after,preserve_views=False);old,new=core.by_id(a['views']),core.by_id(b['views'])
    pending={c['role'] for c in changes if c['id'] is None}
    if not isinstance(created,dict) or set(created)!=pending:raise ValueError('Exact new-view receipt bindings required')
    ids=list(created.values())
    for identity in ids:core.guid(identity)
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate created view identity')
    for identity in ids:
        if identity in old:raise ValueError('New view replaced an existing identity')
    if set(new)!=set(old)|set(ids):raise ValueError('View membership changed')
    selected=set()
    for c in changes:
        identity=c['id'] if c['id'] is not None else created[c['role']]
        if identity not in new:raise ValueError('Saved view missing')
        if c['id'] is not None:selected.add(identity)
        check_view_change(old.get(identity),new[identity],c['desired'],c['fields'])
    for identity,v in old.items():
        if identity not in selected and not core.same(v,new[identity]):raise ValueError('Unrelated view changed')


def reconcile(before,plan,after,results,*,expected_plan_sha256,created=None):
    core.check_plan(plan,before,expected_plan_sha256)
    if not core.same(plan,prepare(before,**plan['inputs'])):raise ValueError('Changed view scope')
    view_readback(before,after,plan['changes'],{} if created is None else created)
    core.check_queries(before,plan,after,results,plan['details']['expected_ids'])
    return core.result(before,after,plan,automatic_rollover=False,query_results_sha256=core.sha(results))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','bindings','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--as-of',required=True);p.add_argument('--after',type=Path);p.add_argument('--plan',type=Path);p.add_argument('--query-results',type=Path);p.add_argument('--created',type=Path);p.add_argument('--expected-plan-sha256');a=p.parse_args(argv)
    try:
        s,sh=core.cli_read(a.snapshot,ROOT);bindings,bh=core.cli_read(a.bindings,ROOT);value=prepare(s,a.as_of,bindings);hashes={'snapshot':sh,'bindings':bh}
        if a.after:
            if not a.plan or not a.query_results or not a.expected_plan_sha256:raise ValueError('Pinned reconciliation inputs required')
            doc,ph=core.cli_read(a.plan,ROOT);after,ah=core.cli_read(a.after,ROOT);results,rh=core.cli_read(a.query_results,ROOT);plan=core.cli_plan(doc)
            created={}
            if a.created:created,ch=core.cli_read(a.created,ROOT);hashes['created']=ch
            if not core.same(value,plan):raise ValueError('Period/bindings/preimage changed')
            value=reconcile(s,plan,after,results,expected_plan_sha256=a.expected_plan_sha256,created=created);hashes.update(plan=ph,after=ah,query_results=rh)
        elif a.plan or a.query_results or a.created or a.expected_plan_sha256:raise ValueError('Incomplete reconciliation arguments')
        core.cli_write(a.output,value,hashes,ROOT);return 0
    except (OSError,ValueError,KeyError,TypeError):print('Offline view preparation failed; prior files preserved',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
