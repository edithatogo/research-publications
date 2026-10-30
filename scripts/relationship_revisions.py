"""Immutable correction/withdrawal ledger around existing normalized relations.

No native writes or identity resolution. Typed source adapters validate records
before intake; this ledger never upgrades candidate evidence to confirmed links.
SPDX-License-Identifier: Apache-2.0
"""
import copy
from scripts.grants_relationships import normalize_relationship
from scripts.outcome_persistence import digest


def append(history, record, *, revision_id, supersedes, state, reason):
    if not isinstance(revision_id,str) or not revision_id or revision_id!=revision_id.strip(): raise ValueError('Exact revision identity required')
    if state not in {'active','withdrawn'} or not isinstance(reason,str) or not reason.strip(): raise ValueError('Explicit state and reason required')
    normalized=normalize_relationship(record)
    result=copy.deepcopy(history)
    seen=set();heads={}
    for entry in result:
        if entry['revision_id'] in seen or entry['sha256']!=digest({k:v for k,v in entry.items() if k!='sha256'}): raise ValueError('Invalid retained revision history')
        seen.add(entry['revision_id'])
        key=entry['identity']
        if entry['supersedes']!=heads.get(key): raise ValueError('Incomplete or forked history')
        heads[key]=entry['revision_id']
    identity=normalized['RelationshipKey']
    prior=next((e for e in result if e['revision_id']==supersedes),None)
    if prior:
        identity=prior['identity'] # Corrections may change evidence/key; retain lineage identity.
    payload={'identity':identity,'revision_id':revision_id,'supersedes':supersedes,'state':state,'reason':reason,'record':normalized}
    payload['sha256']=digest(payload)
    existing=next((e for e in result if e['revision_id']==revision_id),None)
    if existing:
        if existing!=payload: raise ValueError('Revision identity conflict')
        return result
    if supersedes!=heads.get(identity): raise ValueError('Stale or missing predecessor')
    if prior and prior['record']['Confidence']!='confirmed' and normalized['Confidence']=='confirmed':
        raise ValueError('Confirmation requires the existing review/admission workflow, not revision persistence')
    result.append(payload)
    return result


def current(history):
    heads={}
    for entry in history:
        if entry['sha256']!=digest({k:v for k,v in entry.items() if k!='sha256'}): raise ValueError('History hash mismatch')
        previous=heads.get(entry['identity'])
        if entry['supersedes']!=(previous['revision_id'] if previous else None): raise ValueError('Forked history')
        heads[entry['identity']]=entry
    return [copy.deepcopy(e['record']) for e in heads.values() if e['state']=='active']
