"""Immutable correction/withdrawal ledger around existing normalized relations.

No native writes or identity resolution. Typed source adapters validate records
before intake; this ledger never upgrades candidate evidence to confirmed links.
SPDX-License-Identifier: Apache-2.0
"""
import copy
from scripts.grants_relationships import normalize_relationship
from scripts.outcome_persistence import digest


def normalize_assertion(record):
    if record.get('RelationshipKind') != 'datacite_output_reference':
        return normalize_relationship(record)
    import re
    for flag in ('IdentityQualified','CanonicalAdmission','MutationAuthorized','NativeG06Admission'):
        if record.get(flag) is not False: raise ValueError('Source assertion cannot acquire native admission')
    if record.get('ResourceTypeGeneralRaw') not in {'Dataset','Software'} or record.get('ReviewState')!='Not reviewed' or record.get('Confidence')!='candidate':
        raise ValueError('Retained review-only dataset/software assertion required')
    for key in ('EvidenceKey','FromKey','ToKey','SourceSnapshotID'):
        if not isinstance(record.get(key),str) or not record[key] or record[key]!=record[key].strip(): raise ValueError('Exact source assertion identity required')
    if not re.fullmatch('[0-9a-f]{64}',record.get('SourceManifestSHA256','')): raise ValueError('Source manifest hash required')
    if not isinstance(record.get('SourceRecord'),dict): raise ValueError('Retained source record required')
    count=record.get('CanonicalMatchCount'); keys=record.get('CanonicalKeys')
    if type(count) is not int or count<0 or not isinstance(keys,list) or len(keys)!=count or len(set(keys))!=count:
        raise ValueError('Exact canonical mapping cardinality required')
    if record.get('CanonicalKey') != (keys[0] if count==1 else ''): raise ValueError('Canonical mapping mismatch')
    return copy.deepcopy(record)


def append(history, record, *, revision_id, supersedes, state, reason):
    if not isinstance(revision_id,str) or not revision_id or revision_id!=revision_id.strip(): raise ValueError('Exact revision identity required')
    if state not in {'active','withdrawn'} or not isinstance(reason,str) or not reason.strip(): raise ValueError('Explicit state and reason required')
    normalized=normalize_assertion(record)
    result=copy.deepcopy(history)
    heads = validate_history(result)
    identity=normalized.get('RelationshipKey',normalized.get('EvidenceKey'))
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
    if prior and ('RelationshipKind' in prior['record']) != ('RelationshipKind' in normalized):
        raise ValueError('Cannot change relationship family through correction')
    if prior and prior['record']['Confidence']!='confirmed' and normalized['Confidence']=='confirmed':
        raise ValueError('Confirmation requires the existing review/admission workflow, not revision persistence')
    result.append(payload)
    return result


def validate_history(history):
    if not isinstance(history,list): raise ValueError('Complete revision array required')
    heads={}; seen=set()
    required={'identity','revision_id','supersedes','state','reason','record','sha256'}
    for entry in history:
        if not isinstance(entry,dict) or set(entry)!=required: raise ValueError('Incomplete revision envelope')
        if entry['revision_id'] in seen or not isinstance(entry['revision_id'],str) or not entry['revision_id']:
            raise ValueError('Duplicate or invalid revision identity')
        seen.add(entry['revision_id'])
        if entry['state'] not in {'active','withdrawn'} or not isinstance(entry['reason'],str) or not entry['reason'].strip(): raise ValueError('Invalid revision disposition')
        if normalize_assertion(entry['record'])!=entry['record']: raise ValueError('History record normalization drift')
        if entry['sha256']!=digest({k:v for k,v in entry.items() if k!='sha256'}): raise ValueError('History hash mismatch')
        previous=heads.get(entry['identity'])
        if entry['supersedes']!=(previous['revision_id'] if previous else None): raise ValueError('Forked history')
        if previous is None and entry['identity']!=entry['record'].get('RelationshipKey',entry['record'].get('EvidenceKey')):
            raise ValueError('Initial lineage identity mismatch')
        if previous and ('RelationshipKind' in previous['record']) != ('RelationshipKind' in entry['record']): raise ValueError('History family drift')
        if previous and previous['record']['Confidence']!='confirmed' and entry['record']['Confidence']=='confirmed': raise ValueError('Unqualified historical confirmation')
        heads[entry['identity']]=entry
    return {key:value['revision_id'] for key,value in heads.items()}


def current(history):
    heads=validate_history(history)
    return [copy.deepcopy(e['record']) for e in history if heads[e['identity']]==e['revision_id'] and e['state']=='active']


def main(argv=None):
    import argparse,json,os,subprocess
    from pathlib import Path
    from scripts.deploy_report_definition import strict
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv);inputs=strict(Path(args.input).read_bytes())
    history=append(**inputs)
    result={'history':history,'current':current(history),'native_acceptance':False}
    root=Path(__file__).resolve().parents[1];out=Path(args.output).resolve()
    if not out.is_relative_to(root/'private'/'ops'):raise ValueError('Private output required')
    subprocess.run(['git','check-ignore','-q',str(out)],cwd=root,check=True)
    with os.fdopen(os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as handle:json.dump(result,handle,indent=2,allow_nan=False)
    print('PASS_LOCAL_ONLY; no source admission or native persistence')


if __name__=='__main__':main()
