# SPDX-License-Identifier: Apache-2.0
"""Verify supplied complete captures locally; never retrieve or mutate a registry.

The supported raw profile uses exact Id GUID + ID integer, field_N values and
explicit current/version-history evidence. Completeness and capture references
are supplied assertions, not independently authenticated native evidence.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit
from uuid import UUID

if __package__:
    from scripts.publication_batch_contract import PROTECTED_MANUAL_FIELDS
else:
    from publication_batch_contract import PROTECTED_MANUAL_FIELDS

ROOT=Path(__file__).resolve().parents[1]
FIELD_MAP={'FirstObservedUTC':'field_19','ReviewStatus':'field_17','ReviewNotes':'field_18',
           'Title':'Title','Authors':'field_3','Journal':'field_4','PublicationYear':'field_5',
           'PublicationMonth':'field_6','SourceKey':'field_1','CanonicalKey':'field_2'}
PUBMED_KEY=re.compile(r'pubmed:[1-9][0-9]*')
VERSION=re.compile(r'[1-9][0-9]*\.(?:0|[1-9][0-9]*)')

class VerificationError(ValueError):
    pass


def identifier(value,label):
    if (not isinstance(value,str) or not value or value!=value.strip()
            or any(ord(c)<32 or ord(c)==127 for c in value)):
        raise VerificationError(label+' requires exact nonblank text')
    return value


def instant(value,label):
    identifier(value,label)
    if not value.endswith(('Z','+00:00')):
        raise VerificationError(label+' requires a known timezone-aware UTC instant')
    try:result=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:raise VerificationError(label+' has an unqualified timestamp') from None
    if result.utcoffset() is None or result.utcoffset().total_seconds()!=0:
        raise VerificationError(label+' requires a known UTC instant')
    return result


def canonical(value):
    def check(v):
        if isinstance(v,dict):
            if any(not isinstance(k,str) for k in v):raise VerificationError('JSON field names must be text')
            for item in v.values():check(item)
        elif isinstance(v,list):
            for item in v:check(item)
        elif type(v) not in (str,int,float,bool,type(None)):
            raise VerificationError('Supplied values must be JSON data')
    check(value)
    try:return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    except (ValueError,TypeError):raise VerificationError('Invalid JSON values') from None


def same(left,right):return canonical(left)==canonical(right)

def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()


def decode_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise VerificationError('Duplicate JSON field names')
            result[key]=value
        return result
    def invalid(value):raise VerificationError('Non-finite JSON number')
    try:return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
    except (UnicodeError,json.JSONDecodeError):raise VerificationError('Invalid supplied JSON') from None


def read_json(path):return decode_json(Path(path).read_bytes())

def complete(document):
    if not isinstance(document,dict) or document.get('complete') is not True:
        raise VerificationError('complete=true capture required')
    for key in ('error','errors'):
        if key in document and document[key] is not None:
            raise VerificationError('Error envelope cannot establish complete capture')
    if 'partial' in document and document['partial'] is not False:
        raise VerificationError('Partial or malformed capture flag')
    for key in ('@odata.nextLink','odata.nextLink','nextLink','next_link','next_links','__next'):
        if key in document and document[key] not in (None,'',[]):
            raise VerificationError('Unresolved continuation link')


def fresh(value,now,label):
    stamp=instant(value,label)
    if not isinstance(now,datetime) or now.utcoffset() is None:
        raise VerificationError('Explicit aware evaluation time required')
    if not 0 <= (now-stamp).total_seconds() <= 900:
        raise VerificationError('Capture must be fresh within 15 minutes, never future')
    return stamp


def snapshot(document,key,now):
    canonical(document);complete(document)
    if document.get('history_complete') is not True:
        raise VerificationError('Complete version history evidence required')
    rows=document.get(key)
    if not isinstance(rows,list) or type(document.get('item_count')) is not int or document['item_count']!=len(rows):
        raise VerificationError('Complete count-bound row array required')
    stamp=fresh(document.get('observed_at_utc'),now,'capture observed_at_utc')
    identifier(document.get('capture_reference'),'capture_reference')
    target=document.get('target')
    if not isinstance(target,dict) or set(target)!={'site_url','list_id'}:
        raise VerificationError('Exact site/list provenance required')
    site=identifier(target['site_url'],'site_url');identity=identifier(target['list_id'],'list_id')
    try:guid=str(UUID(identity));url=urlsplit(site)
    except ValueError:raise VerificationError('Invalid exact target') from None
    if (guid!=identity or url.scheme!='https' or not url.hostname or not url.hostname.endswith('.sharepoint.com')
            or url.netloc!=url.hostname or url.query or url.fragment or '\\' in site
            or '..' in url.path.split('/') or re.search(r'%(?:25|2e|2f|5c)',url.path,re.I)):
        raise VerificationError('Exact canonical SharePoint target required')
    return rows,stamp


def version_key(value):
    if not isinstance(value,str) or not VERSION.fullmatch(value):
        raise VerificationError('Exact positive native version label required')
    return tuple((len(part),part) for part in value.split('.'))


def versions(row):
    history=row.get('versions')
    if not isinstance(history,list) or not history:
        raise VerificationError('Complete nonempty version history required')
    seen=set();previous=None
    for entry in history:
        if not isinstance(entry,dict):raise VerificationError('Version evidence must be an object')
        key=version_key(entry.get('version'));etag=identifier(entry.get('etag'),'version etag')
        identifier(entry.get('capture_reference'),'version capture reference')
        if etag=='*' or etag in seen or (previous is not None and key<=previous):
            raise VerificationError('Ambiguous or unordered version history')
        seen.add(etag);previous=key
    if row.get('version')!=history[-1]['version'] or row.get('etag')!=history[-1]['etag']:
        raise VerificationError('Current version/ETag must match saved history')
    return history


def preserve_history(old,new):
    before,after=versions(old),versions(new)
    if len(after)<len(before) or not same(before,after[:len(before)]):
        raise VerificationError('Prior version history changed or disappeared')


def expected_keys(values):
    if not isinstance(values,list) or not values:
        raise VerificationError('Expected keys require a nonempty list')
    if any(not isinstance(k,str) or not PUBMED_KEY.fullmatch(k) for k in values):
        raise VerificationError('Expected keys must be exact positive ASCII PubMed keys')
    if len(set(values))!=len(values):raise VerificationError('duplicate expected keys')
    return set(values)


def _index(rows,label):
    by_guid={};integers=set();sources=set();canonicals=set()
    if set(FIELD_MAP)!=set(PROTECTED_MANUAL_FIELDS):raise VerificationError('Protected-field policy requires reconciliation')
    for row in rows:
        if not isinstance(row,dict):raise VerificationError(label+' contains invalid rows')
        value=row.get('Id')
        try:guid=str(UUID(value)) if isinstance(value,str) else None
        except ValueError:guid=None
        if guid is None or value!=guid or type(row.get('ID')) is not int or row['ID']<1:
            raise VerificationError(label+' requires exact GUID and integer item IDs')
        if guid in by_guid or row['ID'] in integers:raise VerificationError('Duplicate item identity')
        if any(name not in row for name in FIELD_MAP.values()):raise VerificationError('Missing protected fields')
        versions(row)
        for field,seen in [('field_1',sources),('field_2',canonicals)]:
            key=row[field]
            if key not in (None,''):
                identifier(key,'registry key')
                if key in seen:raise VerificationError('Duplicate keyed registry identity')
                seen.add(key)
        by_guid[guid]=row;integers.add(row['ID'])
    return by_guid


def compare(before_path,after_path,expected_new_keys,expected_new_review_status,*,expected_canonical_keys=None,now=None):
    now=now or datetime.now(timezone.utc)
    expected=expected_keys(expected_new_keys)
    if not isinstance(expected_canonical_keys,dict) or set(expected_canonical_keys)!=expected:
        raise VerificationError('Explicit complete expected canonical identity map required')
    for key in expected_canonical_keys.values():identifier(key,'expected canonical identity')
    identifier(expected_new_review_status,'expected ReviewStatus')
    before_raw=Path(before_path).read_bytes();after_raw=Path(after_path).read_bytes()
    before_document=decode_json(before_raw);after_document=decode_json(after_raw)
    before_rows,before_time=snapshot(before_document,'value',now);after_rows,after_time=snapshot(after_document,'value',now)
    if not same(before_document['target'],after_document['target']) or after_time<before_time:
        raise VerificationError('Capture target or chronology differs')
    before=_index(before_rows,'before');after=_index(after_rows,'after')
    if set(before)-set(after):raise VerificationError('Prior item identity disappeared')
    for guid,old in before.items():
        new=after[guid]
        if old['ID']!=new['ID']:raise VerificationError('Prior integer item identity changed')
        if any(not same(old[FIELD_MAP[k]],new[FIELD_MAP[k]]) for k in PROTECTED_MANUAL_FIELDS):
            raise VerificationError('Prior protected fields changed')
        preserve_history(old,new)
    additions=[row for guid,row in after.items() if guid not in before]
    actual=[]
    for row in additions:
        source=row['field_1']
        if not isinstance(source,str) or not PUBMED_KEY.fullmatch(source) or row['field_2']!=expected_canonical_keys.get(source):
            raise VerificationError('New PubMed source/canonical identity differs')
        if row['field_17']!=expected_new_review_status:raise VerificationError('New ReviewStatus differs from explicit expectation')
        actual.append(source)
    if set(actual)!=expected or len(actual)!=len(expected):raise VerificationError('New key set differs from exact expectation')
    return {'status':'verified','native_acceptance':False,'write_authorized':False,
        'before_item_count':len(before),'after_item_count':len(after),'preserved_prior_item_count':len(before),
        'new_item_count':len(additions),'expected_new_key_count':len(expected),'expected_new_review_status':expected_new_review_status,
        'before_export_sha256':hashlib.sha256(before_raw).hexdigest(),
        'after_export_sha256':hashlib.sha256(after_raw).hexdigest(),
        'protected_fields_checked':sorted(PROTECTED_MANUAL_FIELDS),'changed_items':[],
        'native_field_contract_qualified':False,'expected_canonical_keys_sha256':digest(expected_canonical_keys),
        'target':copy.deepcopy(before_document['target']),'evaluated_at_utc':now.astimezone(timezone.utc).isoformat(),
        'capture_references':[before_document['capture_reference'],after_document['capture_reference']]}


def private_path(path,label,root,*,output=False):
    path=Path(path).absolute();base=(Path(root)/'private').resolve()
    if path.is_symlink() or path.parent.resolve(strict=True)!=path.parent:
        raise VerificationError(label+' must not use symlink redirection')
    resolved=path.resolve(strict=not output)
    if not resolved.is_relative_to(base) or (not output and not resolved.is_file()):
        raise VerificationError(label+' must be under repository private/')
    if output and path.exists():raise VerificationError('Output already exists; preserve prior evidence')
    return resolved


def exclusive_json(path,value):
    content=json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n'
    # Link an owned temporary artifact atomically: a concurrent/preexisting output
    # is never overwritten and serialization/write failures create no final file.
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=Path(path).parent) as stream:
        stream.write(content);stream.flush();os.fsync(stream.fileno())
        os.link(stream.name,path,follow_symlinks=False)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('before','after','expected-keys','expected-canonical-keys','output'):parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--new-review-status',required=True);parser.add_argument('--as-of')
    args=parser.parse_args(argv)
    try:
        output=private_path(args.output,'output',ROOT,output=True)
        before=private_path(args.before,'before',ROOT);after=private_path(args.after,'after',ROOT)
        keys=read_json(private_path(args.expected_keys,'expected keys',ROOT))
        now=instant(args.as_of,'evaluation time') if args.as_of else datetime.now(timezone.utc)
        mapping=read_json(private_path(args.expected_canonical_keys,'expected canonical keys',ROOT))
        exclusive_json(output,compare(before,after,keys,args.new_review_status,expected_canonical_keys=mapping,now=now))
        return 0
    except (OSError,ValueError,TypeError,KeyError):
        print('Verification failed; inputs and prior output preserved',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
