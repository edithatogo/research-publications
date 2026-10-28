# SPDX-License-Identifier: Apache-2.0
"""Join frozen raw/typed evidence to logical registry proposals, entirely offline."""
import argparse
import copy
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
if not __package__:sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import prepare_publication_registry_bootstrap as core
from scripts.preflight_publication_flow_activation import assess
from scripts.publication_batch_contract import validate_paged_batch,validate_update_allowlist,PROTECTED_MANUAL_FIELDS
from scripts.publication_policy import evaluate,load_policy
from scripts.publication_retained_cycle import retain,validate_state
from scripts.organisation_enrichment import load_reference
from scripts.capture_report_bound_source_union import project_current_pubmed_efetch
from scripts.publication_xml_metadata import article_metadata
from scripts.verify_retained_canary_metadata_values import _dora
from scripts.verify_publication_protected_fields import FIELD_MAP
ROOT=Path(__file__).resolve().parents[1]
DOCUMENTS={'acquisition','typed','registry','writer','bindings','state','ledger','schema'}
MAPPING={**FIELD_MAP,'PublicationDateRaw':'field_7','PublicationDatePrecision':'field_8','LastObservedUTC':'field_20','PMID':'field_10','SourceFullTitle':'SourceFullTitle'}
OFFICIAL='https://dora.health.qld.gov.au/qldresearchjspui/handle/'


def exact_keys(value,keys,label):
    if not isinstance(value,dict) or set(value)!=set(keys):raise ValueError('Exact '+label+' shape required')


def fingerprint(value,label):
    if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value):raise ValueError(label+' SHA256 required')
    return value


def identity(source,source_id):
    core.identifier(source_id,'source identity')
    if source=='PubMed' and re.fullmatch('[1-9][0-9]*',source_id):return 'pubmed:'+source_id
    if source=='DORA' and re.fullmatch('DORA:1/[1-9][0-9]*',source_id):return 'dora:'+source_id[5:]
    raise ValueError('Explicit configured source identity required; no CanonicalKey inference')


def generations(values,target):
    if not isinstance(values,list) or not values:raise ValueError('Explicit source generations required')
    result={}
    for g in values:
        exact_keys(g,('source','generation','model_id','workspace_id','request_id','observed_at_utc'),'generation')
        source=g['source']
        if source not in ('PubMed','DORA') or source in result:raise ValueError('Duplicate/unsupported source generation')
        core.identifier(g['generation'],'generation');core.identifier(g['request_id'],'request ID');core.instant(g['observed_at_utc'],'source observation')
        if g['model_id']!=target['model_id'] or g['workspace_id']!=target['workspace_id']:raise ValueError('Generation consumer model/workspace mismatch')
        result[source]=copy.deepcopy(g)
    return result


def project_part(part,raw):
    """Only two explicit retained profiles; unknown raw content is never guessed."""
    if not isinstance(raw,bytes):raise ValueError('Exact artifact bytes required')
    source=part['source'];projected={}
    try:
        if source=='PubMed' and part['format']=='pubmed_efetch_xml_v1':
            if b'<!ENTITY' in raw.upper():raise ValueError('XML entity declarations unsupported')
            rows=project_current_pubmed_efetch(raw);root=ET.fromstring(raw)
            metadata={a.findtext('MedlineCitation/PMID'):core.decode_json(article_metadata(a)['MetadataJSON']) for a in root}
            projected={key:(row,metadata[key]) for key,row in rows.items()}
        elif source=='DORA' and part['format']=='dora_metadata_records_v1':
            doc=core.decode_json(raw);core.complete(doc)
            exact_keys(doc,('kind','complete','records'),'DoRA raw metadata envelope')
            if doc['kind']!='dora_metadata_records_v1' or not isinstance(doc['records'],list) or not doc['records']:raise ValueError('Complete retained DoRA records required')
            for entry in doc['records']:
                exact_keys(entry,('source_id','metadata'),'DoRA raw record');key=entry['source_id'];identity(source,key)
                if key in projected or not isinstance(entry['metadata'],list):raise ValueError('Duplicate/malformed DoRA metadata')
                for node in entry['metadata']:
                    if not isinstance(node,dict) or not isinstance(node.get('Field'),str) or node.get('Value') is not None and not isinstance(node['Value'],str):raise ValueError('Explicit DoRA field/value metadata required')
                if any(n['Field']=='rims.source.format' and n.get('Value')=='dora_rss_v1' for n in entry['metadata']):raise ValueError('Sparse RSS requires the existing DoRA union/cycle gate; no full-metadata substitution')
                uris={n.get('Value') for n in entry['metadata'] if n['Field']=='dc.identifier.uri'}
                if uris!={OFFICIAL+key[5:]}:raise ValueError('DoRA own identifier conflicts with declared source ID')
                projected[key]=(_dora(entry['metadata']),copy.deepcopy(entry['metadata']))
        else:raise ValueError('Unsupported raw source profile; retained native capture is not imported')
    except (ET.ParseError,TypeError,KeyError,AttributeError):raise ValueError('Malformed retained source projection') from None
    if sorted(projected)!=part['source_ids']:raise ValueError('Raw part key inventory differs')
    return projected


def qualify_schema(schema,s,policy,reference):
    core.complete(schema)
    exact_keys(schema,('kind','complete','fields_sha256','policy_sha256','reference_sha256','timestamp_profile','timestamp_semantics_reference','full_title_semantics_reference','capacities'),'schema qualification')
    if schema['kind']!='publication_admission_schema_v1' or schema['fields_sha256']!=core.sha(s['fields']) or schema['policy_sha256']!=core.sha(policy) or schema['reference_sha256']!=core.sha(reference):raise ValueError('Schema/policy/reference binding mismatch')
    for name in ('timestamp_semantics_reference','full_title_semantics_reference'):core.identifier(schema[name],name)
    if schema['timestamp_profile']!='registry_processing_utc':raise ValueError('Explicit registry processing-time semantics required; source observations stay separate')
    capacities=schema['capacities']
    if not isinstance(capacities,dict):raise ValueError('Explicit field capacities required')
    # Capacities are supplied qualification assertions, never native acceptance.
    for internal,cap in capacities.items():
        if internal not in MAPPING.values():raise ValueError('Unsupported capacity field')
        exact_keys(cap,('field_id','utf16_units'),'capacity');f=core.field_named(s,internal)
        if cap['field_id']!=f['Id'] or type(cap['utf16_units']) is not int or cap['utf16_units']<1:raise ValueError('Invalid capacity identity/limit')
        if f['TypeAsString']=='Text' and (type(f.get('MaxLength')) is not int or cap['utf16_units']>f['MaxLength']):raise ValueError('Capacity exceeds supplied Text profile')
    for logical,internal in MAPPING.items():
        f=core.field_named(s,internal)
        if f['Title']!=logical:raise ValueError('Logical/physical destination meaning mismatch')
        if f['ReadOnlyField'] or f['Sealed']:raise ValueError('Existing destination is not writable')
        if logical=='PublicationYear':
            if f['TypeAsString']!='Number':raise ValueError('Existing year Number field required')
        elif logical=='ReviewStatus' and f['TypeAsString']=='Choice':
            choices=f.get('Choices',{}).get('results') if isinstance(f.get('Choices'),dict) else None
            if not isinstance(choices,list) or 'Included' not in choices:raise ValueError('Included policy is unsupported by current Choice field')
        else:
            if f['TypeAsString'] not in ('Text','Note'):raise ValueError('Existing compatible text field required')
            if f['TypeAsString']=='Note':core.plain_note(f)
            if internal not in capacities:raise ValueError('Explicit text capacity required')
    core.qualify_full_title(s)


def check_values(values,s,schema):
    for logical,value in values.items():
        if logical not in MAPPING:raise ValueError('Unsupported logical proposal field')
        f=core.field_named(s,MAPPING[logical]);kind=f['TypeAsString']
        if value is None:
            if f['Required']:raise ValueError('Required destination has unknown source value')
        elif kind=='Number':
            if type(value) is not int:raise ValueError('Exact integer source year required')
        elif not isinstance(value,str):raise ValueError('Exact source text required')
        elif kind=='Choice':
            if value not in f['Choices']['results']:raise ValueError('Unqualified Choice label')
        elif len(value.encode('utf-16-le'))//2>schema['capacities'][f['InternalName']]['utf16_units']:raise ValueError('Source value exceeds qualified destination capacity')


def prepare(inputs,files,*,expected_hashes,as_of):
    exact_keys(inputs,DOCUMENTS,'input bundle');core.canonical(inputs);core.instant(as_of,'evaluation time')
    policy=load_policy();reference=load_reference();expected_keys=DOCUMENTS|{'policy','reference'}
    exact_keys(expected_hashes,expected_keys,'independent input pins')
    actual={name:core.sha(value) for name,value in {**inputs,'policy':policy,'reference':reference}.items()}
    for name,value in expected_hashes.items():
        if fingerprint(value,name)!=actual[name]:raise ValueError('Changed/rebound '+name+' input')
    a,t,b=inputs['acquisition'],inputs['typed'],inputs['bindings']
    for doc in (a,t,b,inputs['ledger']):core.complete(doc)
    exact_keys(b,('kind','complete','target','generations','records','item_count'),'independent bindings')
    if b['kind']!='publication_source_bindings_v1':raise ValueError('Independent source bindings required')
    target=b['target'];s=core.validate_snapshot(inputs['registry'])
    report=assess(inputs['writer'],s,target,expected_writer_sha256=expected_hashes['writer'])
    gens=generations(b['generations'],target)
    for stamp in [s['observedAtUTC'],inputs['writer']['observed_at_utc'],inputs['writer']['run_history']['observed_at_utc']]+[g['observed_at_utc'] for g in gens.values()]:
        if core.instant(stamp,'input time')>core.instant(as_of,'evaluation time'):raise ValueError('Future input evidence')
    records=b['records']
    if not isinstance(records,list) or not records or type(b['item_count']) is not int or b['item_count']!=len(records):raise ValueError('Complete nonempty independent identity inventory required')
    bound={};canonical_keys=set()
    for row in records:
        exact_keys(row,('source','source_id','SourceKey','CanonicalKey'),'binding row')
        key=identity(row['source'],row['source_id']);canonical=core.identifier(row['CanonicalKey'],'independent CanonicalKey')
        if row['SourceKey']!=key or row['source'] not in gens or key in bound or canonical.casefold() in canonical_keys:raise ValueError('Duplicate/ambiguous independent identities')
        bound[key]=row;canonical_keys.add(canonical.casefold())
    if set(gens)!={r['source'] for r in records}:raise ValueError('Every declared source requires an explicit nonempty identity inventory')
    exact_keys(a,('kind','complete','unfiltered','capture_reference','scope_reference','generations','parts'),'acquisition proof')
    if a['kind']!='publication_frozen_acquisition_v1' or a['unfiltered'] is not True or not core.same(a['generations'],b['generations']):raise ValueError('Acquisition generation/scope mismatch')
    for key in ('capture_reference','scope_reference'):core.identifier(a[key],key)
    parts=a['parts']
    if not isinstance(parts,list) or not parts or not isinstance(files,dict):raise ValueError('Complete raw part inventory required')
    projected={};names=set()
    for part in parts:
        exact_keys(part,('name','source','generation','format','bytes','sha256','source_ids'),'raw part')
        name=core.identifier(part['name'],'raw filename')
        if name in names or name in ('.','..') or any(c in name for c in '/\\') or name not in files:raise ValueError('Duplicate/missing/unsafe raw file')
        names.add(name);source=part['source']
        if source not in gens or part['generation']!=gens[source]['generation']:raise ValueError('Raw part generation differs')
        if type(part['bytes']) is not int or part['bytes']<1 or not isinstance(files[name],bytes) or len(files[name])!=part['bytes'] or core.bytes_sha(files[name])!=fingerprint(part['sha256'],'raw part'):raise ValueError('Exact raw byte proof differs')
        if not isinstance(part['source_ids'],list) or any(not isinstance(v,str) for v in part['source_ids']) or part['source_ids']!=sorted(set(part['source_ids'])):raise ValueError('Unique ordered raw source IDs required')
        for source_id,(record,metadata) in project_part(part,files[name]).items():
            key=identity(source,source_id)
            if key in projected or key not in bound:raise ValueError('Duplicate/unbound raw identity')
            projected[key]=dict(source=source,source_id=source_id,SourceKey=key,CanonicalKey=bound[key]['CanonicalKey'],generation=part['generation'],part=name,record=record,metadata=metadata)
    if set(files)!=names or set(projected)!=set(bound):raise ValueError('Incomplete/extra raw file or record inventory')
    exact_keys(t,('kind','complete','capture_reference','generations','records','pages'),'typed evidence')
    if t['kind']!='publication_typed_admission_input_v1' or not core.same(t['generations'],b['generations']):raise ValueError('Typed generation differs')
    core.identifier(t['capture_reference'],'typed capture')
    expected_records=[projected[k] for k in sorted(projected)]
    if not core.same(t['records'],expected_records):raise ValueError('Typed values/metadata/lineage differ from supplied raw projection')
    if not isinstance(t['pages'],list):raise ValueError('Explicit complete typed page sequence required')
    for page in t['pages']:
        if not isinstance(page,dict) or any(key in page and page[key] is not None for key in ('error','errors')):raise ValueError('Typed page contains an error envelope')
    errors=validate_paged_batch(t['pages'],expected_count=len(bound),expected_keys=list(bound))
    if errors:raise ValueError('Incomplete typed batch: '+'; '.join(errors))
    if not core.same([row for page in t['pages'] for row in page['rows']],t['records']):raise ValueError('Typed page values differ')
    qualify_schema(inputs['schema'],s,policy,reference)
    state=inputs['state'];validate_state(state);ledger=inputs['ledger']
    exact_keys(ledger,('kind','complete','entries','item_count'),'packet ledger')
    if ledger['kind']!='publication_admission_ledger_v1' or not isinstance(ledger['entries'],list) or type(ledger['item_count']) is not int or ledger['item_count']!=len(ledger['entries']):raise ValueError('Complete packet ledger required')
    prior=set();packet_ids=set()
    for entry in ledger['entries']:
        exact_keys(entry,('packet_sha256','generations'),'ledger entry');fingerprint(entry['packet_sha256'],'prior packet')
        if entry['packet_sha256'] in packet_ids:raise ValueError('Duplicate ledger packet')
        packet_ids.add(entry['packet_sha256'])
        for source,g in generations(entry['generations'],target).items():
            pair=(source,g['generation'])
            if pair in prior:raise ValueError('Duplicate ledger generation')
            prior.add(pair)
    prior.update((c['source'],c['generation']) for c in state['cycles'])
    if prior&{(source,g['generation']) for source,g in gens.items()}:raise ValueError('Generation already retained or proposed; explicit terminal handover required')
    current={};aliases={};canonical_current={}
    for row in s['items']:
        key=row['field_1'];canon=row['field_2']
        if key in (None,''):
            if canon not in (None,''):raise ValueError('Unkeyed row has ambiguous canonical identity')
            continue
        core.identifier(key,'current SourceKey')
        if key.casefold() in aliases:raise ValueError('Duplicate/ambiguous current SourceKey')
        aliases[key.casefold()]=key
        if key.startswith('dora:') and re.fullmatch('dora:1/[1-9][0-9]*',key) is None:raise ValueError('Historical DoRA alias requires separately qualified resolution; no implicit adoption')
        if key.startswith('pubmed:') and re.fullmatch('pubmed:[1-9][0-9]*',key) is None:raise ValueError('Unqualified PubMed identity')
        core.identifier(canon,'current CanonicalKey')
        if canon.casefold() in canonical_current:raise ValueError('Ambiguous current CanonicalKey')
        canonical_current[canon.casefold()]=key;current[key]=row
    candidate_state=copy.deepcopy(state);proposals=[]
    for source in sorted(gens):
        g=gens[source];selected=[v for v in expected_records if v['source']==source]
        start=len(candidate_state['versions'])
        candidate_state=retain(candidate_state,[(v['source_id'],v['record']) for v in selected],generation=g['generation'],observed_at=g['observed_at_utc'],source=source,complete=True,policy=policy)
        selected_by_key={r['SourceKey']:r for r in selected}
        for version in candidate_state['versions'][start:]:
            evidence=selected_by_key[version['SourceKey']]
            version['SourceEvidence']={'typed_record':copy.deepcopy(evidence),'raw_part':copy.deepcopy(next(p for p in parts if p['name']==evidence['part']))}
    if not core.same(reference,load_reference()) or not core.same(policy,load_policy()):raise ValueError('Policy/reference changed during preparation')
    for record in expected_records:
        key=record['SourceKey'];canon=record['CanonicalKey'];source=record['source'];stamp=as_of;existing=current.get(key)
        if key.casefold() in aliases and aliases[key.casefold()]!=key:raise ValueError('Case-alias identity is unresolved')
        if canon.casefold() in canonical_current and canonical_current[canon.casefold()]!=key:raise ValueError('Candidate CanonicalKey shadows a different retained source identity')
        decision=evaluate(source,record['source_id'],record['record'],policy=policy,reference=reference)
        if decision['SourceKey']!=key or decision['RegistryDisposition']!='Included':raise ValueError('Incompatible automatic inclusion policy')
        common=dict(SourceKey=key,CanonicalKey=canon,source=source,generation=gens[source]['generation'],source_record=copy.deepcopy(record),policy_disposition=decision['RegistryDisposition'],uncertainty_flags=decision['UncertaintyFlags'])
        if existing is not None:
            if existing['field_2']!=canon:raise ValueError('Independent CanonicalKey differs from current identity')
            previous=existing['field_20']
            if previous not in (None,'') and core.instant(stamp,'observation')<core.instant(previous,'retained observation'):raise ValueError('Observation time regressed')
            values={} if core.same(previous,stamp) else {'LastObservedUTC':stamp};check_values(values,s,inputs['schema'])
            if validate_update_allowlist(values) or set(values)-{'LastObservedUTC'}:raise ValueError('Existing proposal violates the observation-only protected-field contract')
            proposals.append({**common,'kind':'observe' if values else 'noop','native_item_id':existing['Id'],'saved_etag':existing['__metadata']['etag'],'saved_version':existing['OData__UIVersionString'],'retained_current':copy.deepcopy(existing),'protected_values':{logical:copy.deepcopy(existing[FIELD_MAP[logical]]) for logical in sorted(PROTECTED_MANUAL_FIELDS)},'proposed_observation':values})
        else:
            values={k:copy.deepcopy(v) for k,v in record['record'].items() if k in MAPPING}
            values.update(SourceKey=key,CanonicalKey=canon,ReviewStatus='Included',FirstObservedUTC=stamp,LastObservedUTC=stamp)
            if source=='PubMed':values['PMID']=record['source_id']
            title=values.get('Title')
            if not isinstance(title,str) or not title.strip():raise ValueError('New source title unavailable')
            capacity=inputs['schema']['capacities']['Title']['utf16_units']
            values['SourceFullTitle']=title
            if len(title.encode('utf-16-le'))//2>capacity:values['Title']=title.encode('utf-16-le')[:capacity*2].decode('utf-16-le',errors='ignore')
            if not values['Title'].strip():raise ValueError('Qualified display capacity cannot retain a nonblank title')
            check_values(values,s,inputs['schema'])
            proposals.append({**common,'kind':'create','proposed_values':values,'unmapped_source_fields':sorted(set(record['record'])-set(MAPPING))})
    packet={**core.FLAGS,'kind':'publication_admission_packet_v1','status':'OFFLINE_PROPOSALS_ONLY','writer_ready':False,
        'as_of_utc':as_of,'input_sha256':actual,'target':copy.deepcopy(target),'generations':copy.deepcopy(b['generations']),
        'raw_files':{p['name']:dict(bytes=p['bytes'],sha256=p['sha256']) for p in parts},'writer_preflight':report,
        'counts':dict(raw_parts=len(parts),source_records=len(expected_records),create_proposals=sum(p['kind']=='create' for p in proposals),observation_proposals=sum(p['kind']=='observe' for p in proposals),noops=sum(p['kind']=='noop' for p in proposals)),
        'allowed_existing_internal_fields':['field_20'],'proposals':proposals,'retained_state_candidate':candidate_state,
        'timestamp_profile':'registry_processing_utc','proposed_processing_at_utc':as_of,
        'preserved_registry_sha256':core.sha(s),'source_truth_or_native_admission_accepted':False,
        'limits':'Supplied raw/typed/binding consistency and local proposals only; neither native payload nor apply authority; current pilot graph remains blocked'}
    packet['packet_sha256']=core.sha(packet);return packet


def verify(packet,inputs,files,*,expected_hashes,expected_packet_sha256,as_of):
    fingerprint(expected_packet_sha256,'independent packet')
    if not isinstance(packet,dict) or packet.get('packet_sha256')!=expected_packet_sha256 or core.sha({k:v for k,v in packet.items() if k!='packet_sha256'})!=expected_packet_sha256:raise ValueError('Changed packet')
    if not core.same(packet,prepare(inputs,files,expected_hashes=expected_hashes,as_of=as_of)):raise ValueError('Changed packet scope or proposals')
    return {**core.FLAGS,'kind':'publication_admission_packet_comparison_v1','status':'VERIFIED_LOCAL_PACKET','packet_sha256':expected_packet_sha256,'writer_ready':False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','files','pins','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--as-of',required=True);p.add_argument('--packet',type=Path);p.add_argument('--expected-packet-sha256');a=p.parse_args(argv)
    try:
        docs={};hashes={}
        for name in ('inputs','files','pins'):docs[name],hashes[name]=core.cli_read(getattr(a,name),ROOT)
        if not isinstance(docs['files'],dict):raise ValueError('Explicit file-to-private-path map required')
        files={}
        for name,path in docs['files'].items():
            if not isinstance(path,str):raise ValueError('Explicit private raw path required')
            raw=core.private_path(Path(path),'raw artifact',ROOT).read_bytes();files[name]=raw;hashes['raw:'+name]=core.bytes_sha(raw)
        result=prepare(docs['inputs'],files,expected_hashes=docs['pins'],as_of=a.as_of)
        if a.packet:
            if not a.expected_packet_sha256:raise ValueError('Independent packet pin required')
            envelope,hashes['packet']=core.cli_read(a.packet,ROOT)
            if not isinstance(envelope,dict) or envelope.get('kind')!='publication_admission_local_result_v1':raise ValueError('Exact local packet envelope required')
            result=verify(envelope.get('result'),docs['inputs'],files,expected_hashes=docs['pins'],expected_packet_sha256=a.expected_packet_sha256,as_of=a.as_of)
        elif a.expected_packet_sha256:raise ValueError('Incomplete comparison arguments')
        core.exclusive_json(core.private_path(a.output,'output',ROOT,output=True),{**core.FLAGS,'kind':'publication_admission_local_result_v1','result':result,'source_files_sha256':hashes});return 0
    except (ValueError,OSError,TypeError,KeyError):print('Offline admission preparation failed; inputs and prior files preserved',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
