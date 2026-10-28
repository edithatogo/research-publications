"""Reconcile a retained native OpenAlex chunk snapshot to canonical topic rows.

Local files only; preserve all input bytes. Annual NLM catalogue is pinned by
edition and SHA256. Output is preparation for isolated native qualification.
SPDX-License-Identifier: Apache-2.0
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from dashboard_topics import build_topics, mesh_xml_catalogue
from dashboard_retained_chunks import reconstruct
from reconcile_publication_outcome_views import rows as checked_capture_rows


def read_rows(path):
    payload=json.loads(path.read_bytes())
    checked_capture_rows(payload)  # Validate completeness before retaining raw field names.
    return payload['results'][0]['tables'][0]['rows']


def qualify(chunks_path,context_path,keys_path,catalogue_path,edition,catalogue_sha):
    chunks=[{k.replace('OpenAlexMetadataChunks[','['):v for k,v in x.items()} for x in read_rows(chunks_path)]
    contexts=read_rows(context_path);key_rows=read_rows(keys_path)
    keys=[r['[CanonicalKey]'] for r in key_rows]
    if not keys or len(keys)!=len(set(keys)):raise ValueError('Unique complete canonical key set required')
    works=sorted({x['[OpenAlexWorkID]'] for x in contexts})
    if set(works)!={x['[OpenAlexWorkID]'] for x in chunks}:raise ValueError('Raw/context provider key sets differ')
    cross={w:sorted({x['[CanonicalKey]'] for x in contexts if x['[OpenAlexWorkID]']==w}) for w in works}
    envelopes=[]
    for work in works:
        envelope,_=reconstruct(chunks,work)
        if any(x['[RawHash]']!=envelope['raw_response_sha256']
               or x['[Observed]']!=envelope['observed_utc'] for x in contexts if x['[OpenAlexWorkID]']==work):
            raise ValueError('Native context fingerprint/observation mismatch')
        envelopes.append(envelope)
    catalog=mesh_xml_catalogue(catalogue_path,edition,catalogue_sha)
    bridge=build_topics(keys,envelopes,cross,catalog,edition)
    bridge['qualification']=dict(status='PASS_LOCAL_RETAINED_SNAPSHOT',provider_works=len(works),
        context_rows=len(contexts),canonical_keys=len(keys),nlm_catalogue_records=len(catalog),edition=edition,
        input_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (chunks_path,context_path,keys_path,catalogue_path)},
        native_model_write=False,native_processing=False,reader_accepted=False)
    return bridge


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('chunks','context','publication-years','mesh-catalogue','output'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--mesh-edition',required=True)
    parser.add_argument('--mesh-sha256',required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Output exists; preserve previous qualification')
    result=qualify(args.chunks,args.context,args.publication_years,args.mesh_catalogue,args.mesh_edition,args.mesh_sha256)
    with args.output.open('x') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(dict(status=result['qualification']['status'],coverage=result['coverage'],
                         memberships=len(result['memberships']),diagnostics=len(result['diagnostics']))))

if __name__=='__main__':main()
