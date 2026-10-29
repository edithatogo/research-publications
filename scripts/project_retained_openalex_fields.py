"""Project compatible existing registry fields from complete retained OpenAlex bytes.

No acquisition, canonical mutation or native writes. Other fields stay in retained
raw storage; source topics/study designs are not institutional classifications.
"""
import base64
import hashlib
import json
import re
from enrich_openalex import clean_doi
from prepare_openalex_retention import utc

PATHS={
    'OpenAlexID':['id'], 'CitationCount_OpenAlex':['cited_by_count'],
    'OpenAccessStatus':['open_access.oa_status'], 'OAUrl':['open_access.oa_url'],
    'FunderNames':['funders[].display_name','awards[].funder_display_name','grants[].funder_display_name'],
    'GrantIDs':['awards[].funder_award_id','grants[].award_id'],
    'MeSHHeadings':['mesh[].descriptor_name'],
    'AuthorKeywords':['keywords[].display_name','keywords[].keyword'],
    'AffiliationsRaw':['authorships[].raw_affiliation_strings[]','authorships[].affiliations[].raw_affiliation_string'],
}

def records(payload,key):
    value=payload.get(key)
    if value is None:return []
    if not isinstance(value,list) or any(not isinstance(v,dict) for v in value):raise ValueError('Invalid '+key+' schema')
    return value

def joined(values):
    seen=[]
    for v in values:
        if v is None:continue
        if not isinstance(v,str):raise ValueError('Text field schema drift')
        if v.strip() and v not in seen:seen.append(v)
    return '; '.join(seen) or None

def project(envelope):
    if envelope.get('kind')!='openalex_retained_observation_v1' or envelope.get('source')!='OpenAlex' or envelope.get('http_status')!=200:raise ValueError('Successful retained OpenAlex envelope required')
    raw=base64.b64decode(envelope['raw_response_base64'],validate=True)
    if len(raw)!=envelope['raw_byte_count'] or hashlib.sha256(raw).hexdigest()!=envelope['raw_response_sha256']:raise ValueError('Raw fingerprint mismatch')
    payload=json.loads(raw);work=payload.get('id');observed=utc(envelope['observed_utc'])
    if (not isinstance(work,str) or re.fullmatch(r'https://openalex\.org/W[0-9]+',work) is None
            or work!=envelope.get('work_id')):raise ValueError('Work identity mismatch')
    requested=clean_doi(envelope.get('requested_doi'));returned=clean_doi(payload.get('doi'))
    if not requested or not returned or requested.casefold()!=returned.casefold():
        raise ValueError('Retained DOI identity mismatch')
    count=payload.get('cited_by_count')
    if count is not None and (isinstance(count,bool) or not isinstance(count,int) or count<0):raise ValueError('Invalid citation count')
    oa=payload.get('open_access');oa={} if oa is None else oa
    if not isinstance(oa,dict):raise ValueError('Invalid OA schema')
    funders=records(payload,'funders');awards=records(payload,'awards');legacy=records(payload,'grants')
    affiliations=[]
    for author in records(payload,'authorships'):
        raw_strings=author.get('raw_affiliation_strings');raw_strings=[] if raw_strings is None else raw_strings
        if not isinstance(raw_strings,list):raise ValueError('Invalid raw affiliations')
        affiliations.extend(raw_strings)
        affiliations.extend(a.get('raw_affiliation_string') for a in records(author,'affiliations'))
    fields={'OpenAlexID':work,'CitationCount_OpenAlex':count,
        'OpenAccessStatus':joined([oa.get('oa_status')]),'OAUrl':joined([oa.get('oa_url')]),
        'FunderNames':joined([f.get('display_name') for f in funders]+[a.get('funder_display_name') for a in awards+legacy]),
        'GrantIDs':joined([a.get('funder_award_id') for a in awards]+[a.get('award_id') for a in legacy]),
        'MeSHHeadings':joined([m.get('descriptor_name') for m in records(payload,'mesh')]),
        'AuthorKeywords':joined([k.get('display_name') or k.get('keyword') for k in records(payload,'keywords')]),
        'AffiliationsRaw':joined(affiliations)}
    provenance=[{'Field':name,'Source':'OpenAlex','ProviderWorkID':work,'SourceObservedUTC':observed,
        'RawResponseSHA256':envelope['raw_response_sha256'],'SourcePaths':PATHS[name],
        'CandidateValue':value,'Decision':'compatible_candidate' if value is not None else 'preserve_missing'} for name,value in fields.items()]
    return {'fields':fields,'provenance':provenance,
        'retained_only_top_level_fields':sorted(set(payload)-{p.split('.')[0].removesuffix('[]') for paths in PATHS.values() for p in paths}),
        'canonical_mutation':False,'native_acceptance':False}


def apply_qualified_limits(projection,limits):
    """Suppress an oversized flat candidate; preserve full raw-linked evidence."""
    import copy
    result=copy.deepcopy(projection);diagnostics=[]
    names=['FunderNames','GrantIDs','MeSHHeadings','AuthorKeywords','AffiliationsRaw']
    if set(limits)!=set(names) or any(type(v) is not int or v<1 for v in limits.values()):
        raise ValueError('Five positive qualified physical limits required')
    for name in names:
        value=result['fields'][name];maximum=min(limits[name],32766)
        if value is not None and len(value)>maximum:
            result['fields'][name]=None
            diagnostics.append({'Field':name,'Status':'projection_rejected_size','Characters':len(value),'Limit':maximum})
            for proof in result['provenance']:
                if proof['Field']==name:proof['Decision']='projection_rejected_size'
    result['projection_diagnostics']=diagnostics
    return result
