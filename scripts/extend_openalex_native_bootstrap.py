"""Extend the accepted OpenAlex bootstrap without changing other model logic.

Local builder only. Exact native lease, drift checks, save/readback and four-table
transactional processing remain the object owner's deployment responsibility.
"""
import base64
import copy
import gzip
import hashlib
import json
import re
from prepare_openalex_retention import schema

EXPRESSION='definition/expressions.tmdl'
LITERAL=re.compile(r'(expression OpenAlexBootstrapDocument =\s*Json.Document\(Binary.Decompress\(Binary.FromText\(")([A-Za-z0-9+/=]+)(",BinaryEncoding.Base64\),Compression.GZip\)\))')

def validate(prepared):
    if prepared.get('kind')!='openalex_retention_preparation_v1' or prepared.get('accepted_commit') is not False:
        raise ValueError('Uncommitted retained preparation required')
    keys=prepared['expected_keys']
    if not keys or len(keys)!=len(set(keys)):raise ValueError('Unique retained work keys required')
    groups={}
    for row in prepared['chunks']:groups.setdefault(row['OpenAlexWorkID'],[]).append(row)
    if set(groups)!=set(keys):raise ValueError('Raw key set differs from declared keys')
    dois=set()
    for work,rows in groups.items():
        rows=sorted(rows,key=lambda r:r['ChunkIndex']);count=len(rows)
        encoded=''.join(r['MetadataChunk'] for r in rows)
        if [r['ChunkIndex'] for r in rows]!=list(range(count)) or any(r['ChunkCount']!=count or r['Encoding']!='UTF8-HEX' or r['MetadataCharacters']!=len(encoded) for r in rows):raise ValueError('Incomplete raw chunk group')
        envelope=json.loads(bytes.fromhex(encoded));raw=base64.b64decode(envelope['raw_response_base64'],validate=True)
        payload=json.loads(raw)
        if (envelope['work_id']!=work or payload['id']!=work or len(raw)!=envelope['raw_byte_count'] or hashlib.sha256(raw).hexdigest()!=envelope['raw_response_sha256'] or schema(payload)!=envelope['observed_schema']):raise ValueError('Raw response/schema mismatch')
        doi=envelope['requested_doi']
        if doi in dois:raise ValueError('Duplicate retained DOI')
        dois.add(doi)
    return dois

def extend(baseline,new_prepared):
    parts=baseline['definition']['parts']
    if baseline['definition']['format']!='TMDL' or len(parts)!=46 or len({p['path'] for p in parts})!=46:
        raise ValueError('Accepted46-part native baseline required')
    part=next(p for p in parts if p['path']==EXPRESSION)
    text=base64.b64decode(part['payload'],validate=True).decode()
    matches=list(LITERAL.finditer(text))
    if len(matches)!=1:raise ValueError('Exact accepted compressed source expression required')
    match=matches[0];old=json.loads(gzip.decompress(base64.b64decode(match[2],validate=True)))
    old_dois=validate(old);new_dois=validate(new_prepared)
    if old_dois & new_dois or set(old['expected_keys']) & set(new_prepared['expected_keys']):
        raise ValueError('Increment must add distinct identifiers; cached history cannot be replaced')
    if not new_prepared.get('ready_for_native_stage') or any(s['Status'] not in ['success','not_found'] for s in new_prepared['attempt_statuses']):
        raise ValueError('Failed/partial provider pass cannot advance native source')
    if len(new_prepared['attempt_statuses'])!=len(new_prepared['source_scope_dois']):
        raise ValueError('Every requested DOI must have an explicit terminal outcome')
    merged=copy.deepcopy(old)
    merged['chunks']+=copy.deepcopy(new_prepared['chunks'])
    merged['expected_keys']=sorted(old['expected_keys']+new_prepared['expected_keys'])
    merged['attempt_statuses']+=copy.deepcopy(new_prepared['attempt_statuses'])
    merged['source_scope_dois']=sorted(set(old['source_scope_dois'])|set(new_prepared['source_scope_dois']))
    merged['source_record_count']=old['source_record_count']+new_prepared['source_record_count']
    fingerprints=old.get('input_provenance_sha256',[old['input_sha256']])+[new_prepared['input_sha256']]
    merged['input_provenance_sha256']=fingerprints
    merged['input_sha256']=hashlib.sha256(json.dumps(fingerprints,separators=(',',':')).encode()).hexdigest()
    merged['input_fingerprint_kind']='composite_of_frozen_source_generations'
    validate(merged)
    raw=json.dumps(merged,ensure_ascii=False,separators=(',',':')).encode();compressed=gzip.compress(raw,mtime=0)
    encoded=base64.b64encode(compressed).decode()
    updated=text[:match.start(2)]+encoded+text[match.end(2):]
    candidate=copy.deepcopy(baseline)
    target=next(p for p in candidate['definition']['parts'] if p['path']==EXPRESSION)
    target['payload']=base64.b64encode(updated.encode()).decode()
    receipt={'kind':'openalex_bootstrap_increment_candidate_v1','model_parts':46,'only_changed_part':EXPRESSION,
        'preserved_parts':45,'all_existing_chunks_preserved':True,'existing_works':len(old['expected_keys']),
        'added_works':len(new_prepared['expected_keys']),'total_works':len(merged['expected_keys']),
        'new_request_outcomes':len(new_prepared['attempt_statuses']),'prepared_bytes':len(raw),
        'compressed_bytes':len(compressed),'native_acceptance':False,'input_generations':len(fingerprints)}
    return candidate,merged,receipt
