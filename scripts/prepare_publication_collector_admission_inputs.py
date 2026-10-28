# SPDX-License-Identifier: Apache-2.0
"""Adapt pinned frozen collector/union artifacts; no capture, store or admission."""
import argparse
import copy
from pathlib import Path
import sys
if not __package__:sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import prepare_publication_admission_packet as admission
from scripts import prepare_publication_registry_bootstrap as core
from scripts.reconcile_pubmed_source_cycle import prepare_offline_typed_candidate
from scripts.prepare_dora_metadata_cycle import prepare as prepare_dora_cycle
from scripts.publication_source_metadata_contract import _page_rows,reconstruct_metadata_rows
ROOT=Path(__file__).resolve().parents[1]


def inventory(artifacts):
    if not isinstance(artifacts,dict) or not artifacts:raise ValueError('Explicit frozen byte artifacts required')
    result={}
    for name,value in artifacts.items():
        core.identifier(name,'artifact role')
        if isinstance(value,bytes):result[name]=dict(bytes=len(value),sha256=core.bytes_sha(value))
        elif isinstance(value,dict):
            for filename,raw in value.items():
                core.identifier(filename,'artifact filename')
                if filename in ('.','..') or any(c in filename for c in '/\\') or not isinstance(raw,bytes):raise ValueError('Safe explicit frozen file bytes required')
                result[name+'/'+filename]=dict(bytes=len(raw),sha256=core.bytes_sha(raw))
        else:raise ValueError('No invented artifact values or automatic path discovery')
    return result


def result_hash(result):
    value={k:v for k,v in result.items() if k not in ('result_sha256','files')};value['files']=inventory({'files':result.get('files',{})})
    return core.sha(value)


def blocked(source,proofs,reason):
    value={**core.FLAGS,'source':source,'status':'BLOCKED_RETAINED_INPUT','blockers':[reason],'files':{},'provenance':dict(original_artifacts=proofs,original_artifacts_untouched=True),'native_admission_accepted':False}
    value['result_sha256']=result_hash(value);return value


def selected_bindings(bindings,source,expected_sha256):
    if core.sha(bindings)!=admission.fingerprint(expected_sha256,'independent bindings'):raise ValueError('Rebound independent bindings')
    core.complete(bindings);admission.exact_keys(bindings,('kind','complete','target','generations','records','item_count'),'independent bindings')
    if bindings['kind']!='publication_source_bindings_v1' or not isinstance(bindings['records'],list) or type(bindings['item_count']) is not int or bindings['item_count']!=len(bindings['records']):raise ValueError('Complete independent binding inventory required')
    gens=admission.generations(bindings['generations'],bindings['target']);chosen={};seen=set();canonical=set()
    for row in bindings['records']:
        admission.exact_keys(row,('source','source_id','SourceKey','CanonicalKey'),'binding row');key=admission.identity(row['source'],row['source_id']);canon=core.identifier(row['CanonicalKey'],'independent CanonicalKey')
        if key!=row['SourceKey'] or key in seen or canon.casefold() in canonical:raise ValueError('Duplicate/ambiguous identity binding')
        seen.add(key);canonical.add(canon.casefold())
        if row['source']==source:chosen[row['source_id']]=copy.deepcopy(row)
    admission.dora_alias_guard(list(seen))
    if source not in gens or not chosen:raise ValueError('Explicit selected-source generation and identities required')
    return chosen,gens[source]


def check_bridge(bridge,*,source,proofs,bindings_sha256,generation,expected_sha256,raw_reference,content_sha256,commit_sha256,role):
    core.canonical(bridge);core.complete(bridge)
    admission.exact_keys(bridge,('kind','complete','source','reference','artifact_inventory_sha256','binding_inventory_sha256','generation','raw_generation_reference','candidate_generation_sha256','commit_sha256','binding_role'),'generation bridge')
    if core.sha(bridge)!=admission.fingerprint(expected_sha256,'independent bridge') or bridge['kind']!='publication_collector_generation_bridge_v1' or bridge['source']!=source:raise ValueError('Changed generation bridge')
    core.identifier(bridge['reference'],'generation authority reference');core.identifier(raw_reference,'original generation reference')
    if bridge['artifact_inventory_sha256']!=core.sha(proofs) or bridge['binding_inventory_sha256']!=bindings_sha256 or not core.same(bridge['generation'],generation) or bridge['raw_generation_reference']!=raw_reference or bridge['candidate_generation_sha256']!=content_sha256 or bridge['commit_sha256']!=commit_sha256 or bridge['binding_role']!=role:raise ValueError('Generation/content/consumer bridge differs')


def pages(rows,page_records):
    if type(page_records) is not int or page_records<1:raise ValueError('Explicit positive page bound required')
    result=[];cursor=None
    for start in range(0,len(rows),page_records):
        values=copy.deepcopy(rows[start:start+page_records]);after=values[-1]['SourceKey'];result.append(dict(rows=values,cursor_before=cursor,cursor_after=after));cursor=after
    result.append(dict(rows=[],cursor_before=cursor,cursor_after=cursor));return result


def finish(source,files,parts,bound,generation,bridge,proofs,*,representation_profile=None,page_records):
    rows=[]
    for part in parts:
        projected=admission.project_part(part,files[part['name']],representation_profile=representation_profile)
        for source_id,(record,metadata) in projected.items():
            if source_id not in bound:raise ValueError('Raw identity missing from independent bindings')
            row=bound[source_id];rows.append(dict(source=source,source_id=source_id,SourceKey=row['SourceKey'],CanonicalKey=row['CanonicalKey'],generation=generation['generation'],part=part['name'],record=record,metadata=metadata))
    if len(rows)!=len(bound) or {r['source_id'] for r in rows}!=set(bound):raise ValueError('Incomplete full-scope source identity coverage')
    rows.sort(key=lambda r:r['SourceKey']);reference=bridge['reference']
    value={**core.FLAGS,'source':source,'status':'PREPARED_LOCAL_INPUTS','files':copy.deepcopy(files),
        'acquisition':dict(kind='publication_frozen_acquisition_v1',complete=True,unfiltered=True,capture_reference=reference,scope_reference=reference,generations=[copy.deepcopy(generation)],parts=copy.deepcopy(parts)),
        'typed':dict(kind='publication_typed_admission_input_v1',complete=True,capture_reference=reference,generations=[copy.deepcopy(generation)],records=rows,pages=pages(rows,page_records)),
        'provenance':dict(original_artifacts=copy.deepcopy(proofs),generation_bridge=copy.deepcopy(bridge),representation_profile_sha256=core.sha(representation_profile) if representation_profile is not None else None,original_artifacts_untouched=True),
        'native_admission_accepted':False}
    value['result_sha256']=result_hash(value);return value


def adapt_pubmed(artifacts,bridge,bindings,*,artifact_sha256,bridge_sha256,bindings_sha256,page_records):
    proofs=inventory(artifacts)
    if core.sha(proofs)!=admission.fingerprint(artifact_sha256,'artifact inventory'):raise ValueError('Changed PubMed artifact bytes')
    admission.exact_keys(artifacts,('manifest','readback','commit','source_pages','typed_receipt','raw_files','typed_files','candidate','comparison','differences','receipt'),'PubMed artifact bundle')
    if not isinstance(artifacts['raw_files'],dict) or not isinstance(artifacts['typed_files'],dict) or any(not isinstance(v,bytes) for k,v in artifacts.items() if k not in ('raw_files','typed_files')):raise ValueError('Exact PubMed document bytes and file maps required')
    docs={name:core.decode_json(value) for name,value in artifacts.items() if isinstance(value,bytes)}
    if any(not isinstance(v,dict) for k,v in docs.items() if k!='differences') or not isinstance(docs['differences'],list):raise ValueError('Structured PubMed evidence documents required')
    for name,raw in artifacts['raw_files'].items():
        try:admission.pubmed_root(raw)
        except (ValueError,TypeError) as exc:return blocked('PubMed',proofs,'unsupported_pubmed_structure_or_encoding_retained: '+str(exc))
    prior_chunks=[]
    for raw in artifacts['typed_files'].values():
        values=core.decode_json(raw)
        if not isinstance(values,list) or any(not isinstance(r,dict) for r in values):raise ValueError('Complete prior typed row arrays required')
        prior_chunks.extend(r for r in values if '[MetadataChunk]' in r)
    if prior_chunks:
        prior_documents,_,_=reconstruct_metadata_rows(prior_chunks,'PMID')
        for text in prior_documents.values():core.decode_json(text)
    candidate,comparison,differences=prepare_offline_typed_candidate(docs['manifest'],docs['readback'],docs['commit'],artifacts['raw_files'],docs['typed_receipt'],artifacts['source_pages'],artifacts['typed_files'])
    for key,expected in (('candidate',candidate),('comparison',comparison),('differences',differences)):
        if not core.same(docs[key],expected):raise ValueError('Saved PubMed '+key+' differs from frozen rebuild')
    receipt=docs['receipt'];admission.exact_keys(receipt,('counts','input_paths','input_sha256','native_invoked','output_path','output_sha256'),'frozen comparison receipt')
    names=('manifest','readback','commit','source_pages','typed_receipt');admission.exact_keys(receipt['input_paths'],names,'receipt source paths');admission.exact_keys(receipt['input_sha256'],names,'receipt input hashes')
    for name in names:
        core.identifier(receipt['input_paths'][name],'original input path')
        if receipt['input_sha256'][name]!=core.bytes_sha(artifacts[name]):raise ValueError('Comparison receipt input bytes differ')
    admission.exact_keys(receipt['output_sha256'],('candidate.json','comparison.json','differences-private.json'),'comparison output hashes')
    for name,label in (('candidate','candidate.json'),('comparison','comparison.json'),('differences','differences-private.json')):
        if receipt['output_sha256'][label]!=core.bytes_sha(artifacts[name]):raise ValueError('Comparison receipt output bytes differ')
    if receipt['native_invoked'] is not False or not core.same(receipt['counts'],comparison['counts']):raise ValueError('Comparison scope/count differs')
    core.identifier(receipt['output_path'],'original output path')
    manifest=docs['manifest']
    if manifest.get('downstream_selection_applied') is not False:raise ValueError('Unfiltered selected PubMed scope required')
    bound,generation=selected_bindings(bindings,'PubMed',bindings_sha256)
    check_bridge(bridge,source='PubMed',proofs=proofs,bindings_sha256=bindings_sha256,generation=generation,expected_sha256=bridge_sha256,raw_reference=manifest.get('run'),content_sha256=candidate['generation_sha256'],commit_sha256=core.bytes_sha(artifacts['commit']),role='offline_candidate_for_consumer_validation')
    if generation['generation']!=candidate['generation_sha256'] or generation['generation']==docs['commit'].get('Generation') or generation['request_id']==docs['commit'].get('RefreshRequestID'):raise ValueError('Current raw candidate cannot inherit prior consumed native generation/request')
    parts=[]
    for entry in manifest['files']:
        name=entry['file'];raw=artifacts['raw_files'][name];parts.append(dict(name=name,source='PubMed',generation=generation['generation'],format='pubmed_efetch_xml_v1',bytes=len(raw),sha256=core.bytes_sha(raw),source_ids=sorted(entry['ids'])))
    result=finish('PubMed',artifacts['raw_files'],parts,bound,generation,bridge,proofs,page_records=page_records)
    result['provenance'].update(original_input_paths=copy.deepcopy(receipt['input_paths']),original_output_path=receipt['output_path'],original_candidate_generation_sha256=candidate['generation_sha256'],prior_consumed_typed_generation=docs['commit'].get('Generation'),richer_candidate_and_author_evidence_retained=True,
        fidelity=manifest.get('fidelity'),limits='Frozen complete saved XML and richer candidate references; no original wire-byte or native typed admission claim')
    result['result_sha256']=result_hash(result);return result


def adapt_dora(artifacts,bridge,bindings,*,artifact_sha256,bridge_sha256,bindings_sha256,state,state_sha256,representation_profile,profile_sha256,page_records):
    proofs=inventory(artifacts)
    if core.sha(proofs)!=admission.fingerprint(artifact_sha256,'artifact inventory'):raise ValueError('Changed DoRA artifact bytes')
    if 'manifest' in artifacts:
        marker=core.decode_json(artifacts['manifest'])
        if marker.get('format')=='rims-dora-publication-raw-commit-v1':return blocked('DORA',proofs,'unsupported_full_HTML_retained; lossless HTML extraction is not implemented')
    admission.exact_keys(artifacts,('pages','generation','validation','commit'),'DoRA retained union artifacts')
    if any(not isinstance(v,bytes) for v in artifacts.values()):raise ValueError('Exact retained union document bytes required')
    if core.sha(state)!=admission.fingerprint(state_sha256,'independent prior state') or core.sha(representation_profile)!=admission.fingerprint(profile_sha256,'independent representations'):raise ValueError('Rebound prior state or representation authority')
    representations=admission.dora_representations(representation_profile);docs={name:core.decode_json(raw) for name,raw in artifacts.items()}
    if any(not isinstance(v,dict) for v in docs.values()):raise ValueError('Structured retained union evidence required')
    extraction=docs['pages'];native=docs['generation'];commit=docs['commit']
    # Strictly decode reconstructed metadata before calling the existing union
    # validator, which historically used a permissive JSON decoder internally.
    chunks,_=_page_rows(extraction.get('sources',{}).get('DoraMetadataChunks'),'DoraMetadataChunks',('DORAKey','ChunkIndex'))
    documents,payloads,characters=reconstruct_metadata_rows(chunks,'DORAKey');metadata={key:core.decode_json(value) for key,value in documents.items()}
    _,cycle=prepare_dora_cycle(extraction,native,docs['validation'],state)
    bound,generation=selected_bindings(bindings,'DORA',bindings_sha256)
    if type(commit.get('SchemaVersion')) is not int or commit['SchemaVersion']!=1 or commit.get('Status')!='committed' or commit.get('Generation')!=native.get('generation') or commit.get('ModelID')!=native.get('modelId') or commit.get('RefreshRequestID')!=native.get('refreshRequestId'):raise ValueError('Completed union marker generation/model/request differs')
    sources=commit.get('Sources');selected=[s for s in sources if isinstance(s,dict) and s.get('Source')=='DORA'] if isinstance(sources,list) else []
    if len(selected)!=1 or selected[0].get('MetadataProfile')!='dora_complete_metadata_v1' or type(selected[0].get('ExpectedRecords')) is not int or selected[0]['ExpectedRecords']!=len(documents) or not core.same(sorted(selected[0].get('ExpectedKeys',[])),sorted(documents)):raise ValueError('Complete committed DoRA identity/profile inventory differs')
    ext=commit.get('SourceExtraction',{});payload_hash=core.sha(payloads)
    expected=dict(MetadataPayloadSHA256=payload_hash,MetadataPayloadCharacters=characters,MetadataChunkCount=len(chunks),PublicationKeySHA256=core.sha(sorted(documents)),MetadataKeySHA256=core.sha(sorted(documents)))
    expected.update(Generation=native['generation'],ModelID=native['modelId'],RefreshRequestID=native['refreshRequestId'],MetadataTerminalPageVerified=True,PublicationTerminalPageVerified=True)
    if any(not core.same(ext.get(k),v) for k,v in expected.items()):raise ValueError('Committed full metadata count/hash proof differs')
    if not core.same(commit.get('RefreshCompletedAtUTC'),native.get('refreshCompletedAtUTC')):raise ValueError('Committed union completion time differs')
    check_bridge(bridge,source='DORA',proofs=proofs,bindings_sha256=bindings_sha256,generation=generation,expected_sha256=bridge_sha256,raw_reference=native.get('generation'),content_sha256=payload_hash,commit_sha256=core.bytes_sha(artifacts['commit']),role='retained_union_candidate_for_consumer_validation')
    if generation['generation']!=native.get('generation') or generation['model_id']!=native.get('modelId') or generation['request_id']!=native.get('refreshRequestId') or generation['observed_at_utc']!=native.get('refreshCompletedAtUTC'):raise ValueError('Selected union processing lineage differs')
    if set(representations)!=set(documents):raise ValueError('Literal representation authority must cover the exact union')
    admission.dora_alias_guard(list(state['latest'])+[r['SourceKey'] for r in bound.values()])
    body=dict(kind='dora_literal_metadata_records_v1',complete=True,representation_profile_sha256=profile_sha256,records=[dict(source_id=key,metadata=copy.deepcopy(metadata[key])) for key in sorted(metadata)])
    raw=(core.canonical(body)+'\n').encode('utf-8');name='dora-literal-metadata-'+core.bytes_sha(raw)+'.json';files={name:raw}
    parts=[dict(name=name,source='DORA',generation=generation['generation'],format=body['kind'],bytes=len(raw),sha256=core.bytes_sha(raw),source_ids=sorted(metadata))]
    result=finish('DORA',files,parts,bound,generation,bridge,proofs,representation_profile=representation_profile,page_records=page_records)
    result['provenance'].update(union_cycle_comparison=cycle,reconstructed_metadata_sha256={k:core.bytes_sha(v.encode('utf-8')) for k,v in documents.items()},fidelity='derived retained metadata JSON; original chunk/capture byte proofs retained; not HTTP wire bytes')
    result['result_sha256']=result_hash(result);return result


def combine(results,external,*,result_pins,external_pins,as_of,page_records):
    admission.exact_keys(external,('registry','schema','writer','bindings','state','ledger'),'external authoritative inputs')
    admission.exact_keys(external_pins,set(external)|{'policy','reference'},'external pins')
    actual={name:core.sha(value) for name,value in {**external,'policy':admission.load_policy(),'reference':admission.load_reference()}.items()}
    if not core.same(actual,external_pins):raise ValueError('Rebound external authoritative inputs/configuration')
    if not isinstance(results,dict):raise ValueError('Exact source result dictionary required')
    admission.exact_keys(result_pins,results,'source result pins');expected_sources={g['source'] for g in external['bindings']['generations']}
    if set(results)!=expected_sources:raise ValueError('Missing selected source; blocked input cannot be dropped')
    files={};parts=[];rows=[]
    for source,result in results.items():
        if result.get('status')!='PREPARED_LOCAL_INPUTS' or result.get('source')!=source or result_hash(result)!=result_pins[source] or result.get('result_sha256')!=result_pins[source] or any(result.get(k) is not False for k in (*core.FLAGS,'native_admission_accepted')):raise ValueError('Blocked, authoritative or changed source result')
        bridge=result['provenance']['generation_bridge']
        if bridge['source']!=source or bridge['artifact_inventory_sha256']!=core.sha(result['provenance']['original_artifacts']) or bridge['binding_inventory_sha256']!=external_pins['bindings']:raise ValueError('Source result bound to different original evidence/identities')
        if source=='DORA' and result['provenance']['representation_profile_sha256']!=core.sha(external['schema'].get('dora_representation_profile')):raise ValueError('External schema lacks matching literal authority')
        expected_generation=[g for g in external['bindings']['generations'] if g['source']==source]
        if not core.same(result['acquisition']['generations'],expected_generation) or not core.same(result['typed']['generations'],expected_generation):raise ValueError('Source generation differs from selected external generation')
        if set(files)&set(result['files']):raise ValueError('Artifact name collision; no silent renaming')
        files.update(copy.deepcopy(result['files']));parts.extend(copy.deepcopy(result['acquisition']['parts']));rows.extend(copy.deepcopy(result['typed']['records']))
    rows.sort(key=lambda r:r['SourceKey']);reference='collector-adapter:'+core.sha(result_pins);inputs=copy.deepcopy(external);gens=copy.deepcopy(external['bindings']['generations'])
    inputs['acquisition']=dict(kind='publication_frozen_acquisition_v1',complete=True,unfiltered=True,capture_reference=reference,scope_reference=reference,generations=gens,parts=parts)
    inputs['typed']=dict(kind='publication_typed_admission_input_v1',complete=True,capture_reference=reference,generations=copy.deepcopy(gens),records=rows,pages=pages(rows,page_records))
    pins={**actual,'acquisition':core.sha(inputs['acquisition']),'typed':core.sha(inputs['typed'])}
    packet=admission.prepare(inputs,files,expected_hashes=pins,as_of=as_of)
    return {**core.FLAGS,'status':'LOCAL_ADMISSION_INPUTS_ONLY','inputs':inputs,'files':files,'input_pins':pins,'packet':packet,'source_result_pins':copy.deepcopy(result_pins)}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
    try:
        request,rh=core.cli_read(a.request,ROOT)
        if not isinstance(request,dict) or not isinstance(request.get('artifacts'),dict):raise ValueError('Explicit structured adapter request required')
        common={'source','artifacts','bridge','bindings','artifact_sha256','bridge_sha256','bindings_sha256','page_records'}
        if request.get('source')=='DORA':common|={'state','state_sha256','representation_profile','profile_sha256'}
        admission.exact_keys(request,common,'adapter request');artifacts={};hashes={'request':rh}
        for role,path in request['artifacts'].items():
            if isinstance(path,str):raw=core.private_path(Path(path),'artifact input',ROOT).read_bytes();artifacts[role]=raw;hashes[role]=core.bytes_sha(raw)
            elif isinstance(path,dict):
                artifacts[role]={}
                for name,item in path.items():
                    if not isinstance(item,str):raise ValueError('Explicit artifact file path required')
                    raw=core.private_path(Path(item),'artifact input',ROOT).read_bytes();artifacts[role][name]=raw;hashes[role+'/'+name]=core.bytes_sha(raw)
            else:raise ValueError('No automatic original-path discovery')
        kwargs={k:v for k,v in request.items() if k not in ('source','artifacts')}
        if request['source']=='PubMed':result=adapt_pubmed(artifacts,**kwargs)
        elif request['source']=='DORA':result=adapt_dora(artifacts,**kwargs)
        else:raise ValueError('Unsupported selected source')
        serialized={k:v for k,v in result.items() if k!='files'};serialized['files_utf8']={n:raw.decode('utf-8') for n,raw in result['files'].items()}
        core.exclusive_json(core.private_path(a.output,'output',ROOT,output=True),{**core.FLAGS,'kind':'publication_collector_adapter_local_v1','result':serialized,'source_files_sha256':hashes});return 0
    except (OSError,ValueError,TypeError,KeyError):print('Offline collector adaptation failed; original artifacts and prior outputs preserved',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
