# SPDX-License-Identifier: Apache-2.0
"""Prepare frozen local quality artifacts and compare supplied receipts, offline."""
import argparse
import copy
import csv
import io
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
if not __package__:sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import prepare_publication_registry_bootstrap as core
from scripts import prepare_publication_views as views
from scripts.publication_metadata_conflicts import metadata_difference_kind
from scripts.export_publication_register import safe_cell
ROOT=Path(__file__).resolve().parents[1]
FIELDS=dict(Title='Title',Authors='field_3',Journal='field_4',PublicationYear='field_5',
    PublicationMonth='field_6',PublicationDateRaw='field_7',PublicationDatePrecision='field_8',
    CHHHSAffiliatedAuthors='field_15',MatchedFacilities='field_14')
STATUS='Informational; no correction adjudicated'


def build(snapshot,disposition,packet):
    s=core.validate_snapshot(snapshot);rows=core.by_id(s['items'])
    for doc in (disposition,packet):
        core.canonical(doc);core.complete(doc)
        if doc.get('registry_sha256')!=core.sha(s):raise ValueError('Exact current registry binding required')
        core.identifier(doc.get('source_revision'),'source revision')
    if disposition['source_revision']!=packet['source_revision']:raise ValueError('Mixed source generations')
    core.identifier(disposition.get('rule_version'),'disposition rule version')
    if not isinstance(packet.get('source_sha256'),str) or not re.fullmatch('[a-f0-9]{64}',packet['source_sha256']):raise ValueError('Source fingerprint required')
    cases=packet.get('cases');diffs=disposition.get('preserved_semantic_items')
    if not isinstance(cases,list) or not isinstance(diffs,list):raise ValueError('Complete case/difference arrays required')
    paired={};case_ids=set()
    for case in cases:
        if not isinstance(case,dict):raise ValueError('Malformed case')
        case_id=core.identifier(case.get('case_id'),'case ID');records=case.get('records')
        if case_id in case_ids or not isinstance(records,list) or len(records)!=2 or any(not isinstance(r,dict) for r in records):raise ValueError('Unique exact case pair required')
        case_ids.add(case_id)
        retained=[r for r in records if isinstance(r.get('record_id'),str) and re.fullmatch(r'registry:[1-9][0-9]*',r['record_id'])]
        if len(retained)!=1:raise ValueError('Exact retained record required')
        record=retained[0];identity=int(record['record_id'][9:]);source=[r for r in records if r.get('record_id')==f'canonical-for:{identity}']
        if identity not in rows or identity in paired or len(source)!=1 or not isinstance(source[0].get('values'),dict):raise ValueError('Exact unique source pair required')
        key=core.identifier(record.get('source_key'),'SourceKey')
        if not core.same(key,rows[identity].get('field_1')) or not core.same(key,source[0].get('source_key')):raise ValueError('Source identities disagree')
        if 'values' in record:
            retained_values=record['values']
            if not isinstance(retained_values,dict) or set(retained_values)-set(FIELDS):raise ValueError('Retained values require supported logical metadata fields')
            for field,value in retained_values.items():
                native=FIELDS[field]
                if native not in rows[identity] or not core.same(value,rows[identity][native]):raise ValueError('Retained case value differs from current registry')
        paired[identity]=(case_id,source[0]['values'])
    output=[];seen=set()
    for d in diffs:
        if not isinstance(d,dict) or set(d)!={'id','field','registry','canonical'}:raise ValueError('Exact disposition entry required')
        identity,field=d['id'],d['field']
        if type(identity) is not int or identity not in paired or not isinstance(field,str) or field not in FIELDS or (identity,field) in seen:raise ValueError('Duplicate/unknown difference')
        seen.add((identity,field));row=rows[identity];case_id,values=paired[identity];native=FIELDS[field]
        if native not in row or field not in values or not core.same(row[native],d['registry']) or not core.same(values[field],d['canonical']) or core.same(d['registry'],d['canonical']):raise ValueError('Stale, equal or unbound pair values')
        kind=metadata_difference_kind(field,d['registry'],d['canonical'])
        output.append(dict(RegistryItemID=identity,SourceKey=row['field_1'],RetainedDisplayTitle=row.get('Title'),Field=field,
            RetainedRegistryValue=copy.deepcopy(d['registry']),CanonicalSourceValue=copy.deepcopy(d['canonical']),
            DifferenceKind=kind,CaseID=case_id,Status=STATUS))
    if set(paired)!={r['RegistryItemID'] for r in output}:raise ValueError('Uncovered case')
    for key,count in (('case_count',len(paired)),('difference_count',len(output))):
        if type(packet.get(key)) is not int or packet[key]!=count:raise ValueError('Case counts differ')
    # All keyed unknown months include Excluded rows. Reader uncertainty has its
    # own explicit denominator, and placeholders are retained separately.
    cohorts=views.expected_ids(s['items'],'0001-01','0001-02');unknown=[];keyed=0
    for row in s['items']:
        if row.get('field_1') not in (None,''):
            keyed+=1
            if row.get('field_6') in (None,''):
                unknown.append({k:copy.deepcopy(v) for k,v in dict(RegistryItemID=row['Id'],SourceKey=row['field_1'],PublicationMonth=row.get('field_6'),PublicationDatePrecision=row.get('field_8'),PublicationDateRaw=row.get('field_7'),ReviewStatus=row.get('field_17')).items()})
    return {**core.FLAGS,'kind':'publication_quality_snapshot_v1','rule_version':disposition['rule_version'],
        'source_revision':packet['source_revision'],'source_sha256':packet['source_sha256'],
        'registry_sha256':core.sha(s),'disposition_sha256':core.sha(disposition),'case_packet_sha256':core.sha(packet),
        'coverage':dict(registry_rows=len(rows),keyed_registry_rows=keyed,retained_placeholders=len(rows)-keyed,
            difference_count=len(output),case_count=len(paired),unknown_month_count=len(unknown),reader_uncertainty_count=len(cohorts['uncertainty']),
            limits='Complete supplied historical difference set; not a fresh complete source audit, adjudication or accepted-canonical total'),
        'differences':sorted(output,key=lambda r:(r['RegistryItemID'],r['Field'])),
        'unknown_month_records':sorted(unknown,key=lambda r:r['RegistryItemID'])}


def prepare(snapshot,disposition,packet,folder,*,uncertainty_view_id):
    data=build(snapshot,disposition,packet);s=core.validate_snapshot(snapshot)
    core.identifier(folder,'site-relative folder')
    if not folder.startswith('/') or folder.startswith('//') or any(part in ('','.','..') for part in folder[1:].split('/')) or any(c in folder for c in '%?#\\:'):raise ValueError('Exact unencoded site-relative folder required')
    core.guid(uncertainty_view_id);old=core.by_id(s['views']).get(uncertainty_view_id)
    if old is None or old['DefaultView'] or old['PersonalView'] or old['Hidden']:raise ValueError('Exact existing public uncertainty view required')
    cohorts=views.expected_ids(s['items'],'0001-01','0001-02')
    desired_uncertainty=views.definitions('0001-01','0001-02')['uncertainty']
    # Receipt reconciliation tests this existing view's query directly. Its
    # supplied definition must already be the qualified uncertainty predicate.
    if old['ViewQuery']!=desired_uncertainty['ViewQuery']:raise ValueError('Existing uncertainty query needs separate view qualification')
    observed=core.instant(s['observedAtUTC'],'capture time').astimezone(ZoneInfo('Australia/Brisbane'))
    prefix=f'publication-quality-{observed:%Y%m%d}-{core.sha(data)[:12]}'
    payloads={prefix+'.json':(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')}
    table=io.StringIO(newline='');columns=['RegistryItemID','SourceKey','Field','RetainedRegistryValue','CanonicalSourceValue','DifferenceKind','CaseID','Status']
    writer=csv.DictWriter(table,fieldnames=columns);writer.writeheader()
    for row in data['differences']:
        cells={k:(json.dumps(row[k],ensure_ascii=False,allow_nan=False) if not isinstance(row[k],str) else row[k]) for k in columns}
        writer.writerow({k:safe_cell(v) for k,v in cells.items()})
    payloads[prefix+'.csv']=b'\xef\xbb\xbf'+table.getvalue().encode('utf-8')
    files={n:dict(bytes=len(raw),sha256=core.bytes_sha(raw)) for n,raw in payloads.items()}
    manifest={**core.FLAGS,'files':copy.deepcopy(files),'registry_sha256':core.sha(s),'quality_sha256':core.sha(data)}
    raw=(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8');payloads[prefix+'-manifest.json']=raw
    files[prefix+'-manifest.json']=dict(bytes=len(raw),sha256=core.bytes_sha(raw))
    ids=sorted({r['RegistryItemID'] for r in data['differences']})
    # Empty sets use a false positive-ID predicate, never an empty CAML In.
    predicate=('<In><FieldRef Name="ID" /><Values>'+''.join(f'<Value Type="Counter">{i}</Value>' for i in ids)+'</Values></In>') if ids else '<Eq><FieldRef Name="ID" /><Value Type="Counter">0</Value></Eq>'
    desired=dict(Title=f'Source differences | {observed:%Y-%m-%d} | {core.sha(data)[:12]}',ViewQuery=f'<Where>{predicate}</Where><OrderBy><FieldRef Name="ID" Ascending="TRUE" /></OrderBy>',Paged=True,RowLimit=100)
    if any(v['Title']==desired['Title'] for v in s['views']):raise ValueError('Existing quality view requires separate identity handover; no replay')
    changes=[dict(role='quality',id=None,before=None,desired=desired,fields=copy.deepcopy(old['resolvedFields']['Items']['results']))]
    inputs=dict(disposition=disposition,packet=packet,folder=folder,uncertainty_view_id=uncertainty_view_id,source_sha256=packet['source_sha256'])
    plan=core.make_plan('publication_quality_offline_v1',s,inputs,changes,dict(files=files,link_existence_verified=False,
        expected_ids=dict(differenceRows=ids,uncertaintyRows=cohorts['uncertainty']),server_folder=urlsplit(s['site_url']).path.rstrip('/')+folder))
    return data,payloads,plan


def reconcile(before,plan,after,effects,queries,*,expected_plan_sha256):
    core.check_plan(plan,before,expected_plan_sha256);inputs=copy.deepcopy(plan['inputs']);source_hash=inputs.pop('source_sha256')
    _,_,expected=prepare(before,**inputs)
    if source_hash!=inputs['packet']['source_sha256'] or not core.same(expected,plan):raise ValueError('Changed quality plan/source')
    core.canonical(effects);core.complete(effects)
    if any(effects.get(k)!=plan[k] for k in ('site_url','list_id','plan_sha256')):raise ValueError('File receipts target/plan mismatch')
    core.identifier(effects.get('capture_reference'),'file receipt reference')
    if core.instant(effects.get('observedAtUTC'),'file receipt time')<core.instant(after['observedAtUTC'],'postimage time'):raise ValueError('Stale file receipt')
    views.view_readback(before,after,plan['changes'],effects.get('created_views'))
    core.check_queries(before,plan,after,queries,plan['details']['expected_ids'])
    # In addition to row identity, preserve native unknown-date/precision labels.
    rows=core.by_id(before['items'])
    for values in queries['results'].values():
        for row in values:
            for name in ('field_6','field_8'):
                if name not in row or not core.same(row[name],rows[row['Id']].get(name)):raise ValueError('Query date/precision differs')
    receipts=effects.get('files');wanted=plan['details']['files']
    if not isinstance(receipts,list) or len(receipts)!=len(wanted):raise ValueError('Complete file receipts required')
    names=set();identities=set()
    for f in receipts:
        if not isinstance(f,dict) or not isinstance(f.get('name'),str) or f['name'] not in wanted or f['name'] in names:raise ValueError('Unexpected/duplicate file receipt')
        names.add(f['name']);core.guid(f.get('unique_id'))
        if f['unique_id'] in identities:raise ValueError('Duplicate stored file identity')
        identities.add(f['unique_id']);core.identifier(f.get('etag'),'stored file ETag')
        if f['etag']=='*' or type(f.get('status')) is not int or f['status']!=200 or type(f.get('bytes')) is not int or f['bytes']!=wanted[f['name']]['bytes'] or f.get('sha256')!=wanted[f['name']]['sha256'] or f.get('server_relative_url')!=plan['details']['server_folder']+'/'+f['name']:raise ValueError('Stored file bytes/identity/location differ')
    return core.result(before,after,plan,file_receipts_sha256=core.sha(effects),query_results_sha256=core.sha(queries),link_existence_verified=False)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','disposition','cases','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--folder',required=True);p.add_argument('--uncertainty-view-id',required=True)
    for name in ('plan','after','effects','query-results'):p.add_argument('--'+name,type=Path)
    p.add_argument('--expected-plan-sha256');a=p.parse_args(argv)
    try:
        docs={};hashes={}
        for name in ('snapshot','disposition','cases'):docs[name],hashes[name]=core.cli_read(getattr(a,name),ROOT)
        data,payloads,plan=prepare(docs['snapshot'],docs['disposition'],docs['cases'],a.folder,uncertainty_view_id=a.uncertainty_view_id)
        value={'data':data,'plan':plan,'local_payloads_utf8':{name:raw.decode('utf-8') for name,raw in payloads.items()}}
        if a.after:
            if not all((a.plan,a.effects,a.query_results,a.expected_plan_sha256)):raise ValueError('Pinned reconciliation inputs required')
            for name in ('plan','after','effects','query_results'):docs[name],hashes[name]=core.cli_read(getattr(a,name),ROOT)
            supplied=core.cli_plan(docs['plan'])
            if not core.same(supplied,value):raise ValueError('Changed source/preimage/inputs/artifacts')
            supplied=supplied['plan']
            value=reconcile(docs['snapshot'],supplied,docs['after'],docs['effects'],docs['query_results'],expected_plan_sha256=a.expected_plan_sha256)
        elif a.plan or a.effects or a.query_results or a.expected_plan_sha256:raise ValueError('Incomplete reconciliation arguments')
        # Artifacts stay in a single exclusive local envelope; this never uploads.
        core.cli_write(a.output,value,hashes,ROOT);return 0
    except (OSError,ValueError,KeyError,TypeError):print('Offline quality preparation failed; prior files preserved',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
