# SPDX-License-Identifier: Apache-2.0
"""Produce bounded immutable candidate feed bytes from a rebuilt admission packet."""
import argparse
import copy
from pathlib import Path
import sys
if not __package__:sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import prepare_publication_admission_packet as admission
from scripts import prepare_publication_registry_bootstrap as core
from scripts.publication_batch_contract import validate_paged_batch,PROTECTED_MANUAL_FIELDS
from scripts.verify_publication_protected_fields import FIELD_MAP
ROOT=Path(__file__).resolve().parents[1]
MANIFEST_KIND='publication_writer_candidate_manifest_v1'
PART_KIND='publication_writer_candidate_part_v1'


def wire(value):return (core.canonical(value)+'\n').encode('utf-8')


def operation(feed_id,proposal):
    value={'SourceKey':proposal['SourceKey'],'CanonicalKey':proposal['CanonicalKey'],'source':proposal['source'],'generation':proposal['generation'],'proposal':copy.deepcopy(proposal)}
    value['operation_id']=core.sha({'feed_id':feed_id,**value});return value


def build(inputs,raw_files,packet,*,input_pins,packet_pin,as_of,max_part_records,max_part_bytes,max_manifest_bytes):
    admission.verify(packet,inputs,raw_files,expected_hashes=input_pins,expected_packet_sha256=packet_pin,as_of=as_of)
    if any(type(v) is not int or v<1 for v in (max_part_records,max_part_bytes,max_manifest_bytes)):raise ValueError('Explicit positive integer part/manifest bounds required')
    context=dict(admission_packet_sha256=packet_pin,input_pins=copy.deepcopy(input_pins),binding_inventory=copy.deepcopy(inputs['bindings']),target=copy.deepcopy(packet['target']),generations=copy.deepcopy(packet['generations']),schema=copy.deepcopy(inputs['schema']),planned_processing_at_utc=as_of,max_part_records=max_part_records,max_part_bytes=max_part_bytes,max_manifest_bytes=max_manifest_bytes)
    feed_id=core.sha(context);rows=[operation(feed_id,p) for p in packet['proposals']]
    rows.sort(key=lambda r:r['SourceKey']);parts={};descriptors=[];cursor=None;pending=[]
    def part_value(values,terminal):
        return dict(kind=PART_KIND,feed_id=feed_id,number=len(descriptors),cursor_before=cursor,cursor_after=values[-1]['SourceKey'] if values else cursor,terminal=terminal,rows=copy.deepcopy(values))
    def emit(values,terminal):
        nonlocal cursor
        value=part_value(values,terminal);raw=wire(value)
        if len(raw)>max_part_bytes:raise ValueError('A complete record or terminal part exceeds supplied byte bound')
        name=f'publication-writer-{feed_id}-{len(descriptors):06d}.json';parts[name]=raw
        descriptors.append({k:copy.deepcopy(value[k]) for k in ('number','cursor_before','cursor_after','terminal')}|dict(name=name,bytes=len(raw),sha256=core.bytes_sha(raw),records=len(values),bindings=[{k:r[k] for k in ('SourceKey','CanonicalKey','source','generation')} for r in values]))
        cursor=value['cursor_after']
    for row in rows:
        if pending and (len(pending)>=max_part_records or len(wire(part_value(pending+[row],False)))>max_part_bytes):emit(pending,False);pending=[]
        if len(wire(part_value(pending+[row],False)))>max_part_bytes:raise ValueError('A complete record exceeds supplied byte bound; no truncation')
        pending.append(row)
    if pending:emit(pending,False)
    emit([],True)
    manifest={**core.FLAGS,'kind':MANIFEST_KIND,'status':'UNPUBLISHED_CANDIDATE','publishing_authorized':False,'feed_id':feed_id,'context':context,
        'parts':descriptors,'part_count':len(descriptors),'record_count':len(rows),'records_sha256':core.sha(rows),
        'bindings':[{k:r[k] for k in ('SourceKey','CanonicalKey','source','generation')} for r in rows],
        'source_raw_files':copy.deepcopy(packet['raw_files']),'registry_sha256':input_pins['registry'],'writer_capture_sha256':input_pins['writer'],
        'retained_state_candidate_sha256':core.sha(packet['retained_state_candidate']),
        'source_authority_qualified':False,'native_file_identities_assigned':False}
    manifest['manifest_sha256']=core.sha(manifest)
    validate(manifest,parts,expected_manifest_sha256=manifest['manifest_sha256'])
    return manifest,parts


def check_row(row,feed_id,planned,schema):
    admission.exact_keys(row,('operation_id','SourceKey','CanonicalKey','source','generation','proposal'),'feed row')
    p=row['proposal']
    if not isinstance(p,dict):raise ValueError('Logical proposal required')
    for key in ('SourceKey','CanonicalKey','source','generation'):
        if not core.same(row[key],p.get(key)):raise ValueError('Changed proposal binding')
        core.identifier(row[key],key)
    source_record=p.get('source_record')
    if not isinstance(source_record,dict) or admission.identity(row['source'],source_record.get('source_id'))!=row['SourceKey']:raise ValueError('Unbound authoritative source identity')
    for key in ('SourceKey','CanonicalKey','source','generation'):
        if source_record.get(key)!=row[key]:raise ValueError('Source record binding differs')
    if p.get('policy_disposition')!='Included':raise ValueError('Unsupported new-record policy')
    if p.get('kind')=='create':
        values=p.get('proposed_values')
        if not isinstance(values,dict) or set(values)-set(admission.MAPPING):raise ValueError('Unqualified create values')
        if values.get('ReviewStatus')!='Included' or values.get('SourceKey')!=row['SourceKey'] or values.get('CanonicalKey')!=row['CanonicalKey']:raise ValueError('Create identity/policy mismatch')
        for name in ('FirstObservedUTC','LastObservedUTC'):
            if values.get(name)!=planned:raise ValueError('Create processing-clock proposal differs')
        full=values.get('SourceFullTitle');title=values.get('Title')
        if not isinstance(full,str) or not full.strip() or full!=source_record.get('record',{}).get('Title') or not isinstance(title,str) or not title.strip():raise ValueError('Full title loss or display/source mismatch')
        cap=schema['capacities']['Title']['utf16_units'];expected=full.encode('utf-16-le')[:cap*2].decode('utf-16-le',errors='ignore')
        if title!=expected:raise ValueError('Display title differs from qualified UTF16 projection')
        for logical,value in values.items():
            if value is None:continue
            if logical=='PublicationYear':
                if type(value) is not int:raise ValueError('Typed source year required')
            elif not isinstance(value,str):raise ValueError('Typed source text required')
            elif admission.MAPPING[logical] in schema['capacities'] and len(value.encode('utf-16-le'))//2>schema['capacities'][admission.MAPPING[logical]]['utf16_units']:raise ValueError('Create value exceeds pinned capacity')
    elif p.get('kind') in ('observe','noop'):
        current=p.get('retained_current');values=p.get('proposed_observation')
        if not isinstance(current,dict) or type(p.get('native_item_id')) is not int or p['native_item_id']<1 or current.get('Id')!=p['native_item_id']:raise ValueError('Exact existing item identity required')
        if current.get('field_1')!=row['SourceKey'] or current.get('field_2')!=row['CanonicalKey']:raise ValueError('Existing identities differ')
        core._metadata(current);core.version_key(p.get('saved_version'))
        if current['__metadata']['etag']!=p.get('saved_etag') or current.get('OData__UIVersionString')!=p['saved_version']:raise ValueError('Existing revision differs')
        expected={name:copy.deepcopy(current[FIELD_MAP[name]]) for name in sorted(PROTECTED_MANUAL_FIELDS)}
        if not core.same(p.get('protected_values'),expected):raise ValueError('Protected human values differ')
        if not core.same(values,{'LastObservedUTC':planned} if p['kind']=='observe' else {}):raise ValueError('Existing update exceeds field_20-only clock scope')
    else:raise ValueError('Unknown logical operation')
    expected=core.sha({'feed_id':feed_id,**{k:v for k,v in row.items() if k!='operation_id'}})
    if row['operation_id']!=expected:raise ValueError('Changed operation ID')


def validate(manifest,parts,*,expected_manifest_sha256):
    core.canonical(manifest);admission.fingerprint(expected_manifest_sha256,'independent manifest')
    admission.exact_keys(manifest,(*core.FLAGS,'kind','status','publishing_authorized','feed_id','context','parts','part_count','record_count','records_sha256','bindings','source_raw_files','registry_sha256','writer_capture_sha256','retained_state_candidate_sha256','source_authority_qualified','native_file_identities_assigned','manifest_sha256'),'candidate manifest')
    if manifest.get('kind')!=MANIFEST_KIND or manifest.get('manifest_sha256')!=expected_manifest_sha256 or core.sha({k:v for k,v in manifest.items() if k!='manifest_sha256'})!=expected_manifest_sha256:raise ValueError('Changed manifest')
    if manifest['status']!='UNPUBLISHED_CANDIDATE':raise ValueError('Candidate feed cannot claim publication/commit')
    for key,value in {**core.FLAGS,'publishing_authorized':False,'source_authority_qualified':False,'native_file_identities_assigned':False}.items():
        if manifest.get(key) is not value:raise ValueError('Candidate cannot grant native or publishing authority')
    context=manifest.get('context')
    if not isinstance(context,dict) or core.sha(context)!=manifest.get('feed_id'):raise ValueError('Changed feed context')
    admission.exact_keys(context,('admission_packet_sha256','input_pins','binding_inventory','target','generations','schema','planned_processing_at_utc','max_part_records','max_part_bytes','max_manifest_bytes'),'feed context')
    admission.exact_keys(context['input_pins'],admission.DOCUMENTS|{'policy','reference'},'input pins')
    for name,value in context['input_pins'].items():admission.fingerprint(value,name)
    for name in ('max_part_records','max_part_bytes','max_manifest_bytes'):
        if type(context.get(name)) is not int or context[name]<1:raise ValueError('Explicit feed bounds required')
    core.instant(context.get('planned_processing_at_utc'),'planned processing clock')
    if len(wire(manifest))>context['max_manifest_bytes']:raise ValueError('Manifest exceeds supplied byte bound')
    bindings_doc=context.get('binding_inventory');core.complete(bindings_doc)
    admission.exact_keys(bindings_doc,('kind','complete','target','generations','records','item_count'),'binding inventory')
    if bindings_doc['kind']!='publication_source_bindings_v1' or not isinstance(bindings_doc['records'],list):raise ValueError('Explicit independent binding profile required')
    if core.sha(bindings_doc)!=context['input_pins']['bindings'] or core.sha(context['schema'])!=context['input_pins']['schema']:raise ValueError('Rebound independent bindings/schema')
    if not core.same(bindings_doc.get('target'),context['target']) or not core.same(bindings_doc.get('generations'),context['generations']):raise ValueError('Binding target/generation differs')
    expected_bindings=[];gens={g['source']:g['generation'] for g in context['generations']}
    for binding in bindings_doc['records']:
        if admission.identity(binding['source'],binding['source_id'])!=binding['SourceKey']:raise ValueError('Inferred source binding')
        expected_bindings.append({k:binding[k] for k in ('SourceKey','CanonicalKey','source')}|dict(generation=gens[binding['source']]))
    if type(bindings_doc.get('item_count')) is not int or bindings_doc['item_count']!=len(expected_bindings) or not core.same(sorted(expected_bindings,key=lambda v:v['SourceKey']),manifest.get('bindings')):raise ValueError('Incomplete independent binding inventory')
    for name,key in (('writer_capture_sha256','writer'),('registry_sha256','registry')):
        if manifest.get(name)!=context['input_pins'][key]:raise ValueError('Rebound feed input pin')
    descriptors=manifest.get('parts')
    if not isinstance(descriptors,list) or not descriptors or type(manifest.get('part_count')) is not int or manifest['part_count']!=len(descriptors) or not isinstance(parts,dict):raise ValueError('Complete bounded part inventory required')
    seen=set();rows=[];pages=[];all_bindings=[];cursor=None
    for index,descriptor in enumerate(descriptors):
        admission.exact_keys(descriptor,('number','cursor_before','cursor_after','terminal','name','bytes','sha256','records','bindings'),'part descriptor')
        name=core.identifier(descriptor['name'],'part name')
        if name in seen or name not in parts or not isinstance(parts[name],bytes):raise ValueError('Duplicate/missing part bytes')
        seen.add(name);raw=parts[name]
        if type(descriptor['bytes']) is not int or descriptor['bytes']!=len(raw) or len(raw)>context['max_part_bytes'] or core.bytes_sha(raw)!=descriptor['sha256']:raise ValueError('Part byte proof/bound differs')
        value=core.decode_json(raw)
        if raw!=wire(value):raise ValueError('Exact canonical UTF-8 part bytes required')
        admission.exact_keys(value,('kind','feed_id','number','cursor_before','cursor_after','terminal','rows'),'part envelope')
        if value['kind']!=PART_KIND or value['feed_id']!=manifest['feed_id'] or type(value['number']) is not int or value['number']!=index:raise ValueError('Wrong part identity/order')
        for key in ('number','cursor_before','cursor_after','terminal'):
            if not core.same(value[key],descriptor[key]):raise ValueError('Part metadata differs')
        terminal=index==len(descriptors)-1;values=value['rows']
        if value['terminal'] is not terminal or not isinstance(values,list) or (not values)!=terminal or type(descriptor['records']) is not int or descriptor['records']!=len(values) or len(values)>context['max_part_records']:raise ValueError('Invalid terminal/count/record bound')
        if value['cursor_before']!=cursor or value['cursor_after']!=(values[-1]['SourceKey'] if values else cursor):raise ValueError('Discontinuous part cursor')
        for row in values:check_row(row,manifest['feed_id'],context['planned_processing_at_utc'],context['schema'])
        bindings=[{k:r[k] for k in ('SourceKey','CanonicalKey','source','generation')} for r in values]
        if not core.same(bindings,descriptor['bindings']):raise ValueError('Part bindings differ')
        all_bindings.extend(bindings);rows.extend(values);pages.append(dict(rows=values,cursor_before=value['cursor_before'],cursor_after=value['cursor_after']));cursor=value['cursor_after']
    if seen!=set(parts) or not core.same(all_bindings,manifest.get('bindings')) or core.sha(rows)!=manifest.get('records_sha256'):raise ValueError('Complete file/value/binding inventory differs')
    if type(manifest.get('record_count')) is not int or manifest['record_count']!=len(rows) or [r['SourceKey'] for r in rows]!=sorted(r['SourceKey'] for r in rows):raise ValueError('Count/ordering differs')
    errors=validate_paged_batch(pages,expected_count=len(rows),expected_keys=[b['SourceKey'] for b in manifest['bindings']])
    if errors:raise ValueError('Incomplete feed: '+'; '.join(errors))
    canonical=[b['CanonicalKey'].casefold() for b in all_bindings]
    if len(canonical)!=len(set(canonical)):raise ValueError('Ambiguous canonical feed bindings')
    return copy.deepcopy(rows)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','files','pins','packet','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--packet-sha256',required=True);p.add_argument('--as-of',required=True);p.add_argument('--max-part-records',type=int,required=True);p.add_argument('--max-part-bytes',type=int,required=True);p.add_argument('--max-manifest-bytes',type=int,required=True);a=p.parse_args(argv)
    try:
        docs={};hashes={}
        for name in ('inputs','files','pins','packet'):docs[name],hashes[name]=core.cli_read(getattr(a,name),ROOT)
        envelope=docs['packet']
        if not isinstance(envelope,dict) or envelope.get('kind')!='publication_admission_local_result_v1':raise ValueError('Exact admission envelope required')
        if not isinstance(docs['files'],dict):raise ValueError('Explicit local raw file map required')
        files={}
        for name,path in docs['files'].items():
            if not isinstance(path,str):raise ValueError('Explicit raw path required')
            raw=core.private_path(Path(path),'raw input',ROOT).read_bytes();files[name]=raw;hashes['raw:'+name]=core.bytes_sha(raw)
        manifest,parts=build(docs['inputs'],files,envelope['result'],input_pins=docs['pins'],packet_pin=a.packet_sha256,as_of=a.as_of,max_part_records=a.max_part_records,max_part_bytes=a.max_part_bytes,max_manifest_bytes=a.max_manifest_bytes)
        core.exclusive_json(core.private_path(a.output,'output',ROOT,output=True),{**core.FLAGS,'kind':'publication_writer_feed_local_v1','manifest':manifest,'parts_utf8':{n:raw.decode('utf-8') for n,raw in parts.items()},'source_files_sha256':hashes});return 0
    except (ValueError,OSError,TypeError,KeyError):print('Offline feed preparation failed; inputs and prior files preserved',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
