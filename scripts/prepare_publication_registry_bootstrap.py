# SPDX-License-Identifier: Apache-2.0
"""Transport-free registry metadata qualification and comparison utilities.

Historical schema migration, capture and command generation are excluded.
Supplied snapshots and policy references are never native authorization.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime
import hashlib
from pathlib import Path
import re
import sys
from uuid import UUID
import xml.etree.ElementTree as ET

if __package__:
    from scripts.verify_publication_protected_fields import (canonical, digest, same, identifier,
        instant, complete, read_json, decode_json, private_path, exclusive_json, version_key)
else:
    from verify_publication_protected_fields import (canonical, digest, same, identifier,
        instant, complete, read_json, decode_json, private_path, exclusive_json, version_key)

ROOT=Path(__file__).resolve().parents[1]
sha=digest
FLAGS={'native_acceptance':False,'write_authorized':False,'native_schema_qualified':False}


def bytes_sha(raw):return hashlib.sha256(raw).hexdigest()

def guid(value):
    identifier(value,'GUID')
    try:valid=str(UUID(value))==value
    except ValueError:valid=False
    if not valid:raise ValueError('Exact canonical GUID required')
    return value


def _metadata(value):
    metadata=value.get('__metadata')
    if not isinstance(metadata,dict):raise ValueError('Complete supplied metadata required')
    if identifier(metadata.get('etag'),'saved ETag')=='*':raise ValueError('Wildcard ETag is not saved evidence')


def field_xml(field):
    try:root=ET.fromstring(field['SchemaXml'])
    except (ET.ParseError,KeyError,TypeError):raise ValueError('Complete field XML required') from None
    if (root.tag!='Field' or root.get('ID') not in (field['Id'],'{'+field['Id']+'}')
            or root.get('Name')!=field['InternalName'] or root.get('DisplayName')!=field['Title']
            or root.get('Type')!=field['TypeAsString']):raise ValueError('Field/XML identity or type mismatch')
    for attr in ('Description','Required','Indexed','EnforceUniqueValues','ReadOnlyField','Sealed','RichText','AppendOnly'):
        if attr in root.attrib and attr in field:
            wanted=str(field[attr]).upper() if isinstance(field[attr],bool) else field[attr]
            if root.get(attr)!=wanted:raise ValueError('Field/XML property mismatch')
    return root


def validate_snapshot(snapshot):
    canonical(snapshot);complete(snapshot)
    identifier(snapshot.get('capture_reference'),'capture reference');instant(snapshot.get('observedAtUTC'),'snapshot timestamp')
    # Reuse the already qualified lexical site/list guard without translating
    # this metadata profile into another verifier's row schema.
    from urllib.parse import urlsplit
    site=identifier(snapshot.get('site_url'),'site_url');url=urlsplit(site);guid(snapshot.get('list_id'))
    if (url.scheme!='https' or not url.hostname or not url.hostname.endswith('.sharepoint.com')
            or url.netloc!=url.hostname or url.query or url.fragment or '\\' in site
            or '..' in url.path.split('/') or re.search(r'%(?:25|2e|2f|5c)',url.path,re.I)):
        raise ValueError('Exact SharePoint target required')
    metadata=snapshot.get('list');counts=snapshot.get('counts')
    if not isinstance(metadata,dict) or metadata.get('Id')!=snapshot['list_id'] or not isinstance(counts,dict) or set(counts)!={'items','fields','views'}:
        raise ValueError('Exact count-bound list metadata required')
    for key in ('items','fields','views'):
        values=snapshot.get(key)
        if not isinstance(values,list) or type(counts.get(key)) is not int or counts[key]!=len(values):raise ValueError('Complete collection counts required')
        ids=set()
        for value in values:
            if not isinstance(value,dict):raise ValueError('Malformed collection member')
            identity=value.get('Id')
            if key=='items':
                if type(identity) is not int or identity<1:raise ValueError('Positive integer item ID required')
                if 'ID' in value and (type(value['ID']) is not int or value['ID']!=identity):raise ValueError('Item ID aliases disagree')
                version_key(value.get('OData__UIVersionString'))
            else:guid(identity)
            if identity in ids:raise ValueError('Duplicate collection ID')
            ids.add(identity);_metadata(value)
    _metadata(metadata)
    if type(metadata.get('ItemCount')) is not int or metadata['ItemCount']!=counts['items']:raise ValueError('List item count mismatch')
    names=set()
    for f in snapshot['fields']:
        name=identifier(f.get('InternalName'),'internal field name');identifier(f.get('Title'),'field title')
        identifier(f.get('TypeAsString'),'field type')
        if name.casefold() in {n.casefold() for n in names}:raise ValueError('Duplicate internal field name')
        names.add(name)
        for flag in ('Required','Indexed','EnforceUniqueValues','ReadOnlyField','Sealed'):
            if type(f.get(flag)) is not bool:raise ValueError('Explicit field properties required')
        field_xml(f)
    for row in snapshot['items']:
        if not names<=set(row):raise ValueError('Complete supplied field values required on every item')
    for v in snapshot['views']:
        identifier(v.get('Title'),'view title')
        for flag in ('DefaultView','PersonalView','Hidden','Paged'):
            if type(v.get(flag)) is not bool:raise ValueError('Explicit view properties required')
        if v.get('ViewType')!='HTML' or type(v.get('RowLimit')) is not int or v['RowLimit']<1:raise ValueError('Supported bounded HTML view required')
        if not isinstance(v.get('ViewQuery'),str):raise ValueError('View query required')
        try:
            ET.fromstring('<Query>'+v['ViewQuery']+'</Query>')
            columns=v['resolvedFields']['Items']['results']
        except (ET.ParseError,KeyError,TypeError):raise ValueError('Complete saved view query/columns required') from None
        if not isinstance(columns,list) or any(not isinstance(c,str) or c not in names for c in columns) or len(columns)!=len(set(columns)):raise ValueError('Unknown/duplicate view columns')
    return copy.deepcopy(snapshot)


def by_id(values):return {v['Id']:v for v in values}


def field_named(snapshot,name):
    matches=[f for f in snapshot['fields'] if f['InternalName']==name]
    if len(matches)!=1:raise ValueError('Exact existing field required: '+name)
    return matches[0]


def plain_note(field):
    if (field['TypeAsString']!='Note' or field['ReadOnlyField'] or field['Sealed']
            or any(field.get(k) is not False for k in ('RichText','AppendOnly'))):
        raise ValueError('Explicit existing writable plain Note qualification required; no type change')


def qualify_existing_note(target,snapshot):
    s=validate_snapshot(snapshot)
    if target.get('site_url')!=s['site_url'] or target.get('list_id')!=s['list_id']:raise ValueError('Target mismatch')
    f=field_named(s,target.get('internal_name'))
    if f['Id']!=target.get('field_id') or f['Title']!=target.get('display_name'):raise ValueError('Field identity mismatch')
    plain_note(f)
    return {**FLAGS,'status':'compatible_existing_note','field':copy.deepcopy(f),'snapshot_sha256':sha(s)}


def qualify_full_title(snapshot):
    s=validate_snapshot(snapshot);f=field_named(s,'SourceFullTitle');plain_note(f)
    if f['Title']!='SourceFullTitle' or any(f[k] for k in ('Required','Indexed','EnforceUniqueValues')):raise ValueError('Existing full-title profile mismatch; no new field')
    return copy.deepcopy(f)


def make_plan(kind,before,inputs,changes,details=None):
    s=validate_snapshot(before)
    plan={**FLAGS,'kind':kind,'site_url':s['site_url'],'list_id':s['list_id'],
        'preimage_sha256':sha(s),'inputs':copy.deepcopy(inputs),'changes':copy.deepcopy(changes),'details':copy.deepcopy(details or {})}
    plan['plan_sha256']=sha(plan);return plan


def check_plan(plan,before,expected):
    if not isinstance(plan,dict) or not isinstance(expected,str) or not re.fullmatch(r'[a-f0-9]{64}',expected):raise ValueError('Independent plan hash required')
    if plan.get('plan_sha256')!=expected or sha({k:v for k,v in plan.items() if k!='plan_sha256'})!=expected:raise ValueError('Changed plan')
    s=validate_snapshot(before)
    if plan.get('preimage_sha256')!=sha(s) or plan.get('site_url')!=s['site_url'] or plan.get('list_id')!=s['list_id']:raise ValueError('Changed preimage/target')


def postimage(before,after,*,preserve_fields=True,preserve_views=True):
    a=validate_snapshot(before);b=validate_snapshot(after)
    if a['site_url']!=b['site_url'] or a['list_id']!=b['list_id'] or instant(b['observedAtUTC'],'postimage time')<instant(a['observedAtUTC'],'preimage time'):raise ValueError('Postimage target/chronology mismatch')
    keys=['items']+(['fields'] if preserve_fields else [])+(['views'] if preserve_views else [])
    for key in keys:
        left,right=by_id(a[key]),by_id(b[key])
        if set(left)!=set(right) or any(not same(row,right[identity]) for identity,row in left.items()):raise ValueError(key+' values, versions or metadata changed')
    if not same(a['list'],b['list']):raise ValueError('List properties changed')
    return a,b


def allow_metadata_etag(old,new):
    expected=copy.deepcopy(old)
    if not same(old,new):
        if set(old)!=set(new):raise ValueError('Metadata shape changed')
        identifier(new['etag'],'postimage ETag')
        if new['etag']=='*':raise ValueError('Wildcard postimage ETag')
        expected['etag']=new['etag']
    if not same(expected,new):raise ValueError('Unrelated metadata changed')


def check_field_change(old,new,desired):
    if set(desired)-{'Description','Indexed'}:raise ValueError('Unsupported field-change scope')
    expected=copy.deepcopy(old);expected.update(desired)
    left=field_xml(old);right=field_xml(new)
    for key,value in desired.items():left.set(key,str(value).upper() if isinstance(value,bool) else value)
    if right.get('Version')!=left.get('Version'):
        if not re.fullmatch(r'[1-9][0-9]*',left.get('Version','')) or not re.fullmatch(r'[1-9][0-9]*',right.get('Version','')) or int(right.get('Version'))!=int(left.get('Version'))+1:raise ValueError('Unexpected schema version')
        left.set('Version',right.get('Version'))
    if ET.canonicalize(ET.tostring(left,encoding='unicode'))!=ET.canonicalize(ET.tostring(right,encoding='unicode')):raise ValueError('Unrelated field XML changed')
    if 'Indexed' in desired and ('IndexStatus' in old or 'IndexStatus' in new):
        if type(old.get('IndexStatus')) is not int or type(new.get('IndexStatus')) is not int or old['IndexStatus']!=0 or new['IndexStatus']!=1:raise ValueError('Unsupported index status transition')
        expected['IndexStatus']=1
    allow_metadata_etag(old['__metadata'],new['__metadata']);expected['__metadata']=copy.deepcopy(new['__metadata']);expected['SchemaXml']=new['SchemaXml']
    if not same(expected,new):raise ValueError('Unrelated field setting changed')


def field_readback(before,plan,after):
    a,b=postimage(before,after,preserve_fields=False);old,new=by_id(a['fields']),by_id(b['fields'])
    if set(old)!=set(new):raise ValueError('Field membership changed')
    selected={c['id']:c for c in plan['changes']}
    if len(selected)!=len(plan['changes']):raise ValueError('Repeated field proposal')
    for identity,f in old.items():
        if identity in selected:check_field_change(f,new[identity],selected[identity]['desired'])
        elif not same(f,new[identity]):raise ValueError('Unrelated field changed')


def result(before,after,plan,**details):
    return {**FLAGS,'status':'verified_supplied_readback','before_sha256':sha(before),'after_sha256':sha(after),
        'plan_sha256':plan['plan_sha256'],'preserved_items':len(after['items']),**details}


def cli_read(path,root):
    raw=private_path(path,'input',root).read_bytes();return decode_json(raw),bytes_sha(raw)


def cli_write(path,value,hashes,root):
    output=private_path(path,'output',root,output=True)
    exclusive_json(output,{**FLAGS,'kind':'offline_registry_metadata_result_v1','result':value,'source_files_sha256':hashes})


def cli_plan(document):
    if not isinstance(document,dict) or document.get('kind')!='offline_registry_metadata_result_v1' or not isinstance(document.get('result'),dict):raise ValueError('Exact local plan envelope required')
    return document['result']


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
    try:
        value,h=cli_read(a.snapshot,ROOT);s=validate_snapshot(value)
        cli_write(a.output,{**FLAGS,'status':'valid_supplied_snapshot','snapshot_sha256':sha(s)}, {'snapshot':h},ROOT);return 0
    except (OSError,ValueError,KeyError,TypeError):print('Offline snapshot validation failed; prior files preserved',file=sys.stderr);return 2



def check_queries(before,plan,after,evidence,expectations):
    canonical(evidence);complete(evidence)
    if (evidence.get('site_url')!=before['site_url'] or evidence.get('list_id')!=before['list_id']
            or evidence.get('plan_sha256')!=plan['plan_sha256']):raise ValueError('Query evidence target/plan mismatch')
    identifier(evidence.get('capture_reference'),'query capture reference')
    if instant(evidence.get('observedAtUTC'),'query time')<instant(after['observedAtUTC'],'postimage time'):raise ValueError('Query capture predates postimage')
    results=evidence.get('results');counts=evidence.get('counts')
    if not isinstance(results,dict) or not isinstance(counts,dict) or set(results)!=set(expectations) or set(counts)!=set(expectations):raise ValueError('Complete query collection required')
    rows=by_id(before['items'])
    for name,expected in expectations.items():
        values=results[name]
        if not isinstance(values,list) or type(counts[name]) is not int or counts[name]!=len(values):raise ValueError('Complete query count required')
        ids=[]
        for value in values:
            if not isinstance(value,dict) or type(value.get('Id')) is not int or value['Id']<1 or 'SourceKey' not in value:raise ValueError('Exact query row identity/source required')
            identity=value['Id'];ids.append(identity)
            if identity not in rows or not same(value['SourceKey'],rows[identity].get('field_1')):raise ValueError('Query source differs')
        if len(ids)!=len(set(ids)) or sorted(ids)!=sorted(expected):raise ValueError('Query ID set differs')

if __name__=='__main__':raise SystemExit(main())
