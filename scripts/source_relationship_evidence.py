"""Project explicit retained-source assertions; never infer identities from names."""
from __future__ import annotations
import base64
import copy
import hashlib
import itertools
import json
import re
from collections import defaultdict


# SPDX-License-Identifier: Apache-2.0
if __package__:
    from scripts.plan_publication_stub_restore import strict_json_loads, utc
else:
    from plan_publication_stub_restore import strict_json_loads, utc


def fingerprint(value):
    """Typed digest including raw byte buffers; never reread or coerce evidence."""
    def typed(x):
        if isinstance(x,bytes): return ['bytes',base64.b64encode(x).decode()]
        if isinstance(x,dict):
            if any(not isinstance(k,str) for k in x): raise ValueError('Text object keys required')
            return ['object',[[k,typed(v)] for k,v in sorted(x.items())]]
        if isinstance(x,list): return ['array',[typed(v) for v in x]]
        if x is None: return ['null']
        if type(x) is bool: return ['bool',x]
        if type(x) in (int,float): return [type(x).__name__,x]
        if isinstance(x,str): return ['text',x]
        raise ValueError('Unsupported evidence value type')
    return hashlib.sha256(json.dumps(typed(value),ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _text(value):
    if not isinstance(value,str) or not value or value!=value.strip():
        raise ValueError('Exact nonempty text identity required')
    return value


def _observed(value):
    if value is not None: utc(value)
    return value


def _generation(inputs,publications,generation,source):
    if not isinstance(inputs,list) or not isinstance(publications,list) or not isinstance(generation,dict):
        raise ValueError('Explicit arrays and caller-bound generation required')
    for name in ('generation_id','canonical_snapshot_id','source_snapshot_id'):_text(generation.get(name))
    if (generation.get('source')!=source or generation.get('complete') is not True
            or generation.get('next_links')!=[]
            or type(generation.get('source_count')) is not int or generation['source_count']!=len(inputs)
            or type(generation.get('publication_count')) is not int or generation['publication_count']!=len(publications)
            or generation.get('source_sha256')!=fingerprint(inputs)
            or generation.get('publications_sha256')!=fingerprint(publications)):
        raise ValueError('Incomplete, conflicting or unbound generation')
    keys=set()
    for row in publications:
        if not isinstance(row,dict):raise ValueError('Canonical publication records required')
        key=_text(row.get('CanonicalKey'))
        if key in keys:raise ValueError('Duplicate canonical publication identity')
        keys.add(key)
        if row.get('PMID') not in (None,'') and (not isinstance(row['PMID'],str) or not re.fullmatch('[1-9][0-9]*',row['PMID'])):
            raise ValueError('Exact PMID text required')
        if row.get('DOI') not in (None,''):
            _text(row['DOI'])
            if not normalise_doi(row['DOI']):raise ValueError('Invalid canonical DOI')


def _complete(item):
    if (not isinstance(item,dict) or item.get('complete') is not True or item.get('next_links')!=[]
            or type(item.get('http_status')) is not int or item['http_status']!=200):
        raise ValueError('Complete successful source capture required')
    if 'observed_utc' not in item:raise ValueError('Explicit observed time or unknown null required')
    _observed(item['observed_utc'])


def _merge(result,key,row,path):
    """Keep repeated occurrence paths without multiplying an assertion grain."""
    if key in result:
        before={k:v for k,v in result[key].items() if k!='SourcePaths'}
        if before!=row:raise ValueError('Conflicting repeated source assertion')
        if path in result[key]['SourcePaths']:raise ValueError('Duplicate source occurrence')
        result[key]['SourcePaths'].append(path)
    else:
        result[key]={**row,'SourcePaths':[path]}


def _finish(rows,generation):
    for row in rows:
        row.update(GenerationID=generation['generation_id'],CanonicalSnapshotID=generation['canonical_snapshot_id'],
            SourceSnapshotID=generation['source_snapshot_id'],SourceInputSHA256=generation['source_sha256'],
            CanonicalInputSHA256=generation['publications_sha256'],Confidence='candidate',IdentityQualified=False,
            RelationshipAdmission='source_assertion_only',MutationAuthorized=False,CanonicalAdmission=False)
    return rows


def normalise_doi(value):
    if not isinstance(value,str): return ''
    value=value.strip().lower()
    for prefix in ('https://doi.org/','http://doi.org/','http://dx.doi.org/','https://dx.doi.org/'):
        if value.startswith(prefix): value=value[len(prefix):]
    return value if re.fullmatch(r'10\.\d{4,9}/\S+',value) else ''


def orcid_status(value):
    if value in (None,''):return 'Absent'
    if not isinstance(value,str):return 'Invalid'
    s=value.removeprefix('https://orcid.org/').removeprefix('http://orcid.org/')
    if not re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{3}[\dX]',s):return 'Invalid'
    total=0
    for c in s.replace('-','')[:15]:total=(total+int(c))*2
    check=(12-total%11)%11
    return 'Valid syntax; unauthenticated' if s[-1]==('X' if check==10 else str(check)) else 'Invalid'


def provider_id(value,kind):
    return value if isinstance(value,str) and re.fullmatch(r'https://openalex\.org/'+kind+r'[0-9]+',value) else ''


def _project(envelopes,publications):
    """Return all evidence, including unknown/ambiguous canonical assignments."""
    mappings=defaultdict(set)
    for p in publications:
        doi=normalise_doi(p.get('DOI'))
        if doi:mappings[doi].add(p['CanonicalKey'])
    parsed=[];seen_work=set();author_orcids=defaultdict(set)
    for e in envelopes:
        raw=base64.b64decode(e['raw_response_base64'],validate=True)
        if hashlib.sha256(raw).hexdigest()!=e['raw_response_sha256']:raise ValueError('Raw source hash mismatch')
        w=strict_json_loads(raw)
        if not isinstance(w,dict) or any(k in w for k in ('error','errors')):raise ValueError('Failed work payload')
        if not isinstance(w.get('authorships'),list) or not isinstance(w.get('awards'),list):raise ValueError('Partial work payload')
        for authorship in w['authorships']:
            if (not isinstance(authorship,dict) or not isinstance(authorship.get('author'),dict)
                    or not isinstance(authorship.get('institutions'),list)
                    or any(not isinstance(i,dict) for i in authorship['institutions'])):
                raise ValueError('Partial authorship payload')
            for name in ('display_name','orcid'):
                if authorship['author'].get(name) is not None and not isinstance(authorship['author'][name],str):
                    raise ValueError('Source labels and ORCID must be raw text')
            for institution in authorship['institutions']:
                if any(institution.get(k) is not None and not isinstance(institution[k],str) for k in ('display_name','ror')):
                    raise ValueError('Raw institution labels/identifiers must be text')
        if any(not isinstance(a,dict) for a in w['awards']):raise ValueError('Partial award payload')
        if any(a.get('funder_display_name') is not None and not isinstance(a['funder_display_name'],str) for a in w['awards']):
            raise ValueError('Raw funder label must be text')
        if 'is_retracted' in w and type(w['is_retracted']) is not bool:raise ValueError('Explicit boolean source retraction marker required')
        if not provider_id(w.get('id'),'W') or e['work_id']!=w['id']:raise ValueError('Work identity mismatch')
        _text(w.get('doi'))
        if normalise_doi(e['requested_doi'])!=normalise_doi(w.get('doi')) or not normalise_doi(w.get('doi')):raise ValueError('DOI identity mismatch')
        if w['id'] in seen_work:raise ValueError('Duplicate retained work')
        seen_work.add(w['id']);parsed.append((e,w))
        for a in w.get('authorships',[]):
            author=a.get('author') or {};aid=provider_id(author.get('id'),'A');o=author.get('orcid') or ''
            if aid and orcid_status(o).startswith('Valid'):author_orcids[aid].add(o.removeprefix('https://orcid.org/').removeprefix('http://orcid.org/'))
    reverse=defaultdict(set)
    for aid,values in author_orcids.items():
        for o in values:reverse[o].add(aid)
    actor_keys={aid:'orcid:'+next(iter(values)) for aid,values in author_orcids.items() if len(values)==1 and len(reverse[next(iter(values))])==1}
    result={}
    for e,w in parsed:
        doi=normalise_doi(w['doi']);ks=sorted(mappings[doi]);canonical=ks[0] if len(ks)==1 else ''
        def add(kind,from_key,to_key,from_label='',to_label='',orcid='',identity='Source-supported',ror=''):
            k='|'.join([w['id'],kind,from_key,to_key])
            row=dict(EvidenceKey=k,RelationshipKind=kind,SourceWorkID=w['id'],PublicationDOI=doi,PublicationPMID='',ReferenceType='',FromKey=from_key,ToKey=to_key,FromLabel=from_label or '',ToLabel=to_label or '',ORCID=orcid,ORCIDStatus=orcid_status(orcid),ROR=ror,IdentityStatus=identity,SourceURL=w['id'],ObservedUTC=e['observed_utc'],RawSHA256=e['raw_response_sha256'],SourceVersion=e['raw_response_sha256'],CanonicalKey=canonical,CanonicalMatchCount=len(ks),ReviewState='Not reviewed',AuthenticationState='Not authenticated',SourceRetracted=w.get('is_retracted'),CandidateEligible=w.get('is_retracted') is not True,EvidenceState='source_marked_retracted' if w.get('is_retracted') is True else 'source_assertion')
            _merge(result,k,row,source_path)
        source_path='/id'
        add('publication','doi:'+doi,w['id'])
        aids={};iids={}
        for i,a in enumerate(w.get('authorships',[]),1):
            source_path='/authorships/'+str(i-1)
            author=a.get('author') or {};aid=provider_id(author.get('id'),'A');o=author.get('orcid') or '';state='Source-supported'
            if not aid:aid=w['id']+'/unresolved-author/'+str(i);state='Unresolved identity'
            elif len(author_orcids[aid])>1:state='Conflicting identifiers'
            provider_actor=aid
            aid=actor_keys.get(aid,aid)
            if provider_actor in actor_keys and orcid_status(o).startswith('Valid'):
                add('identity_alias',provider_actor,aid,author.get('display_name'),o,o,state)
            add('authorship','doi:'+doi,aid,to_label=author.get('display_name') or a.get('raw_author_name') or '',orcid=o,identity=state)
            if state=='Source-supported':aids[aid]=author.get('display_name') or ''
            for j,inst in enumerate(a.get('institutions',[])):
                source_path='/authorships/'+str(i-1)+'/institutions/'+str(j)
                iid=provider_id(inst.get('id'),'I')
                if iid:
                    add('publication_affiliation',aid,iid,author.get('display_name'),inst.get('display_name'),o,state,inst.get('ror') or '')
                    iids[iid]=inst.get('display_name') or ''
        source_path='/authorships'
        for a,b in itertools.combinations(sorted(aids),2):add('coauthorship',a,b,aids[a],aids[b])
        for a,b in itertools.combinations(sorted(iids),2):add('institution_cooccurrence',a,b,iids[a],iids[b])
        for index,award in enumerate(w.get('awards',[])):
            source_path='/awards/'+str(index)
            gid=provider_id(award.get('id'),'G');funder=provider_id(award.get('funder_id'),'F');number=award.get('funder_award_id')
            if number is None:number=''
            if not isinstance(number,str) or number!=number.strip():raise ValueError('Exact award identifier text required')
            if gid:add('publication_award','doi:'+doi,gid,to_label=(award.get('funder_display_name') or '')+' | '+number)
            elif funder and number:add('publication_award','doi:'+doi,funder+'/award/'+number,to_label=number)
            else:add('unresolved_award_reference','doi:'+doi,w['id']+'/unresolved-award/'+str(index),to_label=number,identity='Unresolved award namespace')
    return sorted(result.values(),key=lambda r:r['EvidenceKey'])


def _study_references(studies,publications):
    """Explicit result/derived references only; no background citation as output."""
    index=defaultdict(set)
    for p in publications:
        if p.get('PMID'):index[str(p['PMID'])].add(p['CanonicalKey'])
    out=[]
    for item in studies:
        s=item['record'];nct=s['protocolSection']['identificationModule']['nctId']
        if not re.fullmatch(r'NCT[0-9]{8}',nct):raise ValueError('Invalid study identifier')
        raw=item['raw'];h=hashlib.sha256(raw).hexdigest()
        if item.get('raw_response_sha256')!=h or fingerprint(strict_json_loads(raw))!=fingerprint(s):raise ValueError('Study capture/content mismatch')
        for ref_index,ref in enumerate(s['protocolSection'].get('referencesModule',{}).get('references',[])):
            kind=ref.get('type')
            if kind not in {'RESULT','DERIVED'}:continue
            pmid=ref.get('pmid')
            if pmid is None or (isinstance(pmid,str) and pmid==''):continue
            if not isinstance(pmid,str) or not re.fullmatch('[1-9][0-9]*',pmid):
                raise ValueError('RESULT/DERIVED reference requires ASCII positive PMID text')
            ks=sorted(index[pmid]);source='clinicaltrials.gov:'+nct
            out.append(dict(EvidenceKey='|'.join([source,'publication_study_reference','pmid:'+pmid,source]),RelationshipKind='publication_study_reference',SourceWorkID=source,PublicationDOI='',PublicationPMID=pmid,ReferenceType=kind,FromKey='pmid:'+pmid,ToKey=source,FromLabel='',ToLabel=nct,ORCID='',ORCIDStatus='Absent',ROR='',IdentityStatus='Source-supported',SourceURL='https://clinicaltrials.gov/study/'+nct,ObservedUTC=item['observed_utc'],RawSHA256=h,SourceVersion=h,CanonicalKey=ks[0] if len(ks)==1 else '',CanonicalMatchCount=len(ks),ReviewState='Not reviewed',AuthenticationState='Not authenticated',SourcePaths=['/protocolSection/referencesModule/references/'+str(ref_index)]))
    dedup={}
    for r in out:
        k=r['EvidenceKey']
        paths=r.pop('SourcePaths')
        _merge(dedup,k,r,paths[0])
    return sorted(dedup.values(),key=lambda r:r['EvidenceKey'])


def orcid_normalised(value):
    return (value or '').removeprefix('https://orcid.org/').removeprefix('http://orcid.org/')


def _pubmed_projection(records,publications):
    """Structured Author identifiers and explicit GrantList/DataBankList only."""
    index=defaultdict(set)
    for p in publications:
        if p.get('PMID'):index[str(p['PMID'])].add(p['CanonicalKey'])
    def children(node,name):
        xs=node if isinstance(node,list) else node.get('Value',[]) if isinstance(node,dict) else []
        return [x for x in xs if isinstance(x,dict) and x.get('Name')==name] if isinstance(xs,list) else []
    def child(node,name):
        matches=children(node,name)
        if len(matches)>1:raise ValueError('Duplicate singleton PubMed field')
        return next(iter(matches),{})
    def text(node):
        v=node.get('Value','') if isinstance(node,dict) else node
        return ''.join(text(x) for x in v) if isinstance(v,list) else str(v or '')
    result={}
    for record in records:
        pmid=record['pmid'];citation=child(record['metadata'],'MedlineCitation')
        if text(child(citation,'PMID'))!=pmid:raise ValueError('PubMed payload PMID mismatch')
        article=child(citation,'Article');source='pubmed:'+pmid;ks=sorted(index[pmid]);canonical=ks[0] if len(ks)==1 else ''
        def add(kind,f,t,fl='',tl='',orcid='',identity='Source-supported',ref=''):
            k='|'.join([source,kind,f,t])
            if kind=='publication_affiliation':k+='|'+tl.encode().hex().upper()
            r=dict(EvidenceKey=k,RelationshipKind=kind,SourceWorkID=source,PublicationDOI='',PublicationPMID=pmid,ReferenceType=ref,FromKey=f,ToKey=t,FromLabel=fl,ToLabel=tl,ORCID=orcid,ORCIDStatus=orcid_status(orcid),ROR='',IdentityStatus=identity,SourceURL='https://pubmed.ncbi.nlm.nih.gov/'+pmid+'/',ObservedUTC=record.get('observed_utc',''),RawSHA256='',SourceVersion=record.get('source_version',''),StructuredMetadataSHA256=record['metadata_sha256'],CanonicalKey=canonical,CanonicalMatchCount=len(ks),ReviewState='Not reviewed',AuthenticationState='Not authenticated')
            _merge(result,k,r,source_path)
        source_path='/MedlineCitation/PMID'
        add('publication','pmid:'+pmid,source)
        people={};institutions={}
        for i,a in enumerate(children(child(article,'AuthorList'),'Author'),1):
            source_path='/MedlineCitation/Article/AuthorList/Author/'+str(i-1)
            name=text(child(a,'CollectiveName')) or ' '.join(filter(None,[text(child(a,'ForeName')) or text(child(a,'Initials')),text(child(a,'LastName')),text(child(a,'Suffix'))]))
            ids=[]
            for node in children(a,'Identifier'):
                attrs={x.get('Name'):x.get('Value') for x in node.get('Attributes',[])}
                if attrs.get('Source')=='ORCID':ids.append(orcid_normalised(text(node)))
            ids=sorted(set(ids));o=ids[0] if len(ids)==1 else ''
            good=len(ids)==1 and orcid_status(o).startswith('Valid')
            actor='orcid:'+o if good else source+'/unresolved-author/'+str(i)
            state='Source-supported' if good else 'Conflicting identifiers' if len(ids)>1 else 'Unresolved identity'
            add('authorship','pmid:'+pmid,actor,tl=name,orcid=o,identity=state)
            if good:people[actor]=name
            for af_index,af in enumerate(children(a,'AffiliationInfo')):
                source_path='/MedlineCitation/Article/AuthorList/Author/'+str(i-1)+'/AffiliationInfo/'+str(af_index)
                label=text(child(af,'Affiliation'))
                for node in children(af,'Identifier'):
                    attrs={x.get('Name'):x.get('Value') for x in node.get('Attributes',[])};value=text(node)
                    if attrs.get('Source')=='RINGGOLD' and value.isdecimal():
                        iid='ringgold:'+value;institutions.setdefault(iid,label)
                        add('publication_affiliation',actor,iid,name,label,o,state)
        source_path='/MedlineCitation/Article/AuthorList'
        for a,b in itertools.combinations(sorted(people),2):add('coauthorship',a,b,people[a],people[b])
        for a,b in itertools.combinations(sorted(institutions),2):add('institution_cooccurrence',a,b,institutions[a],institutions[b])
        for i,g in enumerate(children(child(article,'GrantList'),'Grant'),1):
            source_path='/MedlineCitation/Article/GrantList/Grant/'+str(i-1)
            number=text(child(g,'GrantID'));agency=text(child(g,'Agency'));country=text(child(g,'Country'))
            if not number:continue
            key='pubmed:grant:'+'|'.join(v.encode().hex().upper() for v in [agency,country,number])
            state='Source-supported' if agency else 'Unresolved award namespace'
            add('publication_grant_reference','pmid:'+pmid,key,tl=agency+' | '+number,identity=state,ref='PubMed GrantList; source-scoped agency label')
        for db_index,db in enumerate(children(child(article,'DataBankList'),'DataBank')):
            source_path='/MedlineCitation/Article/DataBankList/DataBank/'+str(db_index)
            name=text(child(db,'DataBankName')).casefold()
            schemes={'clinicaltrials.gov':('clinicaltrials.gov',r'NCT[0-9]{8}'),'anzctr':('anzctr',r'ACTRN[0-9]{14}'),'isrctn':('isrctn',r'ISRCTN[0-9]{8}')}
            if name not in schemes:continue
            scheme,pattern=schemes[name]
            for accession_index,n in enumerate(children(child(db,'AccessionNumberList'),'AccessionNumber')):
                source_path='/MedlineCitation/Article/DataBankList/DataBank/'+str(db_index)+'/AccessionNumberList/AccessionNumber/'+str(accession_index)
                value=text(n)
                if re.fullmatch(pattern,value):add('publication_study_reference','pmid:'+pmid,scheme+':'+value,tl=value,ref='PubMed DataBankList')
    return sorted(result.values(),key=lambda r:r['EvidenceKey'])


def project(envelopes,publications,*,generation):
    """One complete caller-bound OpenAlex snapshot; all joins remain candidates."""
    _generation(envelopes,publications,generation,'openalex')
    envelopes,publications=copy.deepcopy((envelopes,publications))
    seen_dois=set()
    for envelope in envelopes:
        _complete(envelope)
        doi=normalise_doi(envelope.get('requested_doi'))
        if not doi or doi in seen_dois:raise ValueError('Duplicate or invalid requested DOI')
        seen_dois.add(doi)
        _text(envelope.get('requested_doi'))
    result=_project(envelopes,publications)
    return _finish(result,generation)


def study_references(studies,publications,*,generation):
    """Exact retained study content only; no inferred project/award membership."""
    _generation(studies,publications,generation,'clinicaltrials.gov')
    studies,publications=copy.deepcopy((studies,publications));seen=set()
    for item in studies:
        _complete(item)
        nct=item['record']['protocolSection']['identificationModule']['nctId']
        if nct in seen:raise ValueError('Duplicate study capture')
        seen.add(nct)
        refs=item['record']['protocolSection'].get('referencesModule',{}).get('references',[])
        if not isinstance(refs,list) or any(not isinstance(r,dict) for r in refs):raise ValueError('Partial study references')
        if not isinstance(item.get('raw'),bytes):raise ValueError('Exact saved study bytes required')
    result=_study_references(studies,publications)
    statuses={'clinicaltrials.gov:'+i['record']['protocolSection']['identificationModule']['nctId']:i['record']['protocolSection'].get('statusModule',{}).get('overallStatus') for i in studies}
    for row in result:
        row.update(EvidenceState='source_assertion',CandidateEligible=True,SourceStatusRaw=statuses[row['SourceWorkID']])
    return _finish(result,generation)


def _metadata_tree(nodes):
    if not isinstance(nodes,list):raise ValueError('Complete structured PubMed metadata required')
    def validate(items):
        for node in items:
            if not isinstance(node,dict) or not isinstance(node.get('Name'),str):raise ValueError('Invalid metadata node')
            attrs=node.get('Attributes',[])
            if not isinstance(attrs,list) or any(not isinstance(a,dict) or not isinstance(a.get('Name'),str) or not isinstance(a.get('Value'),str) for a in attrs):raise ValueError('Invalid metadata attributes')
            if len({a['Name'] for a in attrs})!=len(attrs):raise ValueError('Duplicate metadata attributes')
            value=node.get('Value')
            if isinstance(value,list):validate(value)
            elif not isinstance(value,str):raise ValueError('Unqualified structured metadata text')
    validate(nodes)
    singletons={'PMID','Article','AuthorList','GrantList','DataBankList','PublicationTypeList','ForeName','Initials','LastName','Suffix','CollectiveName','GrantID','Agency','Country','DataBankName','AccessionNumberList','Affiliation'}
    def cardinality(items):
        names=[n['Name'] for n in items if n['Name'] in singletons]
        if len(names)!=len(set(names)):raise ValueError('Duplicate singleton PubMed field')
        for n in items:
            if isinstance(n['Value'],list):cardinality(n['Value'])
    cardinality(nodes)
    citations=[n for n in nodes if n['Name']=='MedlineCitation']
    if len(citations)!=1 or not isinstance(citations[0]['Value'],list):raise ValueError('Exactly one citation required')
    articles=[n for n in citations[0]['Value'] if n['Name']=='Article']
    if len(articles)!=1 or not isinstance(articles[0]['Value'],list):raise ValueError('Exactly one article required')


def pubmed_projection(records,publications,*,generation):
    """Structured metadata digest does not substitute for retained raw XML proof."""
    _generation(records,publications,generation,'pubmed')
    records,publications=copy.deepcopy((records,publications));seen=set()
    for record in records:
        _complete(record)
        pmid=record.get('pmid')
        if not isinstance(pmid,str) or not re.fullmatch('[1-9][0-9]*',pmid) or pmid in seen:
            raise ValueError('Exact unique PubMed record identity required')
        seen.add(pmid);_text(record.get('source_version'))
        _metadata_tree(record.get('metadata'))
        if record.get('metadata_sha256')!=fingerprint(record.get('metadata')):
            raise ValueError('Retained PubMed structured metadata hash mismatch')
    result=_pubmed_projection(records,publications)
    retracted=set()
    for record in records:
        citation=next(n for n in record['metadata'] if n['Name']=='MedlineCitation')
        article=next(n for n in citation['Value'] if n['Name']=='Article')
        for types in (n for n in article['Value'] if n['Name']=='PublicationTypeList'):
            if isinstance(types['Value'],list) and any(n['Name']=='PublicationType' and n['Value']=='Retracted Publication' for n in types['Value']):
                retracted.add('pubmed:'+record['pmid'])
    for row in result:
        marked=True if row['SourceWorkID'] in retracted else None
        row.update(EvidenceState='source_marked_retracted' if marked is True else 'source_assertion',CandidateEligible=marked is not True,SourceRetracted=marked)
    return _finish(result,generation)
