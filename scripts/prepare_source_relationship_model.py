"""Prepare candidate evidence semantics from pinned inputs; no native execution.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse,base64,copy,hashlib,json,re,uuid
from pathlib import Path
if __package__:
    from scripts.reconcile_arc_awards_snapshots import preimage,fingerprint as document_hash,write_new,strict_json_loads
    from scripts.source_relationship_evidence import fingerprint
    from scripts.award_identifier_crosswalks import governing_envelope,exact_text
else:
    from reconcile_arc_awards_snapshots import preimage,fingerprint as document_hash,write_new,strict_json_loads
    from source_relationship_evidence import fingerprint
    from award_identifier_crosswalks import governing_envelope,exact_text
ROOT=Path(__file__).resolve().parents[1]
TABLE='SourceRelationshipEvidence'
TEXT=['AssertionRevisionKey','ProjectionID','EvidenceKey','RelationshipKind','SourceWorkID','PublicationDOI','PublicationPMID','ReferenceType','FromKey','ToKey','FromLabel','ToLabel','ORCID','ORCIDStatus','ROR','IdentityStatus','SourceURL','ObservedUTC','RawSHA256','StructuredMetadataSHA256','SourceVersion','ReviewState','AuthenticationState','SourceProvider','CanonicalKey','GenerationID','CanonicalSnapshotID','SourceSnapshotID','ProjectionRevisionSHA256','SourcePathsJSON','RawAssertionJSON']
LOGICAL=['CandidateEligible','SourceRetracted','IdentityQualified','CanonicalAdmission','MutationAuthorized','NativeG06Admission']
COLUMNS=TEXT+['CanonicalMatchCount']+LOGICAL
MEASURES={'Candidate mapped publications':(None,'CanonicalKey'),'Candidate author-reference keys':('authorship','ToKey'),'Candidate study references':('publication_study_reference','AssertionRevisionKey'),'Candidate award assertions':('publication_award','AssertionRevisionKey')}

FAMILIES={
    'OpenAlex':{'publication','authorship','identity_alias','publication_affiliation','coauthorship','institution_cooccurrence','publication_award','unresolved_award_reference'},
    'PubMed':{'publication','authorship','publication_affiliation','coauthorship','institution_cooccurrence','publication_grant_reference','publication_study_reference'},
    'ClinicalTrials.gov':{'publication_study_reference'},
    'Crossref':{'publication_award_crosswalk','publication_award_crosswalk_diagnostic','publication_government_award_reference','publication_government_award_diagnostic'},
    'NHMRCWorkbook':{'historical_workbook_cell_diagnostic'},
}

def _integer(v,n):
    if type(v)is not int or v<0 or v!=n:raise ValueError('Exact integer count required')

def project_rows(rows,publications,context):
    if not isinstance(rows,list) or not isinstance(publications,list):raise ValueError('Complete arrays required')
    governing_envelope(context)
    for k in ('projection_id','producer_expression'):exact_text(context.get(k))
    fields=context.get('publication_fields')
    if not isinstance(fields,list) or not fields or len(fields)!=len(set(fields)) or 'CanonicalKey' not in fields:raise ValueError('Complete publication field inventory required')
    for f in fields:exact_text(f)
    keys=[]
    for p in publications:
        if not isinstance(p,dict) or set(p)!=set(fields):raise ValueError('Complete canonical field parity required')
        keys.append(exact_text(p.get('CanonicalKey')))
    if len(keys)!=len({key.casefold() for key in keys}):raise ValueError('Casefold-equivalent canonical keys are ambiguous; preserve literals')
    if (context.get('complete') is not True or context.get('next_links')!=[] or context.get('publications_sha256')!=fingerprint(publications)
            or context.get('rows_sha256')!=fingerprint(rows) or context.get('canonical_keys_sha256')!=fingerprint(sorted(keys))):raise ValueError('Unbound producer/canonical generation')
    _integer(context.get('publication_count'),len(publications));_integer(context.get('row_count'),len(rows))
    providers=context.get('providers');eligibility=context.get('eligibility')
    if not isinstance(providers,dict) or not isinstance(eligibility,dict):raise ValueError('Explicit per-assertion source and eligibility context required')
    out=[];seen=set();evidence=set()
    for r in rows:
        if not isinstance(r,dict):raise ValueError('Typed candidate row required')
        for flag in ('IdentityQualified','CanonicalAdmission','MutationAuthorized'):
            if r.get(flag) is not False:raise ValueError('Only explicitly unqualified candidate rows accepted')
        if 'NativeG06Admission' in r and r['NativeG06Admission'] is not False:raise ValueError('Native admission is excluded')
        for k in ('EvidenceKey','RelationshipKind','SourceWorkID','GenerationID','CanonicalSnapshotID','SourceSnapshotID','SourceVersion'):exact_text(r.get(k))
        key=r['EvidenceKey'];evidence.add(key)
        provider=exact_text(providers.get(key));eligible=eligibility.get(key)
        if provider not in FAMILIES or r['RelationshipKind'] not in FAMILIES[provider]:raise ValueError('Producer row family requires its own typed contract')
        patterns={'OpenAlex':r'https://openalex\.org/W[0-9]+','PubMed':r'pubmed:[1-9][0-9]*','ClinicalTrials.gov':r'clinicaltrials\.gov:NCT[0-9]{8}','Crossref':r'crossref:10\.[0-9]{4,9}/[^\s]+','NHMRCWorkbook':r'workbook:[0-9a-f]{64}'}
        if not re.fullmatch(patterns[provider],r['SourceWorkID']):raise ValueError('Explicit provider contradicts source work namespace')
        if type(eligible)is not bool or ('CandidateEligible'in r and r['CandidateEligible'] is not eligible):raise ValueError('Explicit source eligibility mismatch')
        if 'SourceProvider'in r and r['SourceProvider']!=provider:raise ValueError('Provider context mismatch')
        retract=r.get('SourceRetracted')
        if retract is not None and type(retract)is not bool:raise ValueError('Retraction must be boolean or unknown')
        if retract is True and eligible:raise ValueError('Retracted source cannot be eligible')
        if not r['RelationshipKind'].endswith('_diagnostic'):
            exact_text(r.get('FromKey'));exact_text(r.get('ToKey'))
        count=r.get('CanonicalMatchCount');canon=r.get('CanonicalKey')
        if type(count)is not int or count<0 or not isinstance(canon,str) or (canon and (count!=1 or canon not in keys)) or (count==1 and not canon):raise ValueError('Canonical candidate mapping mismatch')
        if provider=='PubMed':
            if not isinstance(r.get('StructuredMetadataSHA256'),str) or not re.fullmatch('[0-9a-f]{64}',r['StructuredMetadataSHA256']) or r.get('RawSHA256') not in (None,''):raise ValueError('Structured PubMed provenance required; raw XML is unqualified')
        elif not isinstance(r.get('RawSHA256'),str) or not re.fullmatch('[0-9a-f]{64}',r['RawSHA256']):raise ValueError('Exact retained payload hash required')
        paths=r.get('SourcePaths')
        if not isinstance(paths,list) or not paths or len(paths)!=len(set(paths)):raise ValueError('Complete occurrence provenance required')
        for path in paths:exact_text(path)
        identity=json.dumps([key,r['SourceVersion'],r['GenerationID'],r.get('ProjectionRevisionSHA256')],separators=(',',':'))
        if identity in seen:raise ValueError('Duplicate assertion revision')
        seen.add(identity);row={f:r.get(f) for f in TEXT}
        row.update(AssertionRevisionKey=identity,ProjectionID=context['projection_id'],SourceProvider=provider,
            SourcePathsJSON=json.dumps(paths,separators=(',',':')),RawAssertionJSON=json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False),
            CanonicalMatchCount=count,CandidateEligible=eligible,SourceRetracted=retract,IdentityQualified=False,CanonicalAdmission=False,MutationAuthorized=False,NativeG06Admission=False)
        if r.get('ReviewState')!='Not reviewed' or r.get('AuthenticationState')!='Not authenticated':raise ValueError('Human review/authentication fields cannot be repurposed')
        for f in TEXT:
            if row[f] is not None and not isinstance(row[f],str):raise ValueError('Text field type drift')
        out.append(row)
    if set(providers)!=evidence or set(eligibility)!=evidence:raise ValueError('Complete exact provider/eligibility key sets required')
    return out

def table_definition(m_source):
    lines=['/// Candidate source assertions only; no review, identity or funding admission.',f'table {TABLE}']
    for field in COLUMNS:
        dtype='int64' if field=='CanonicalMatchCount' else 'boolean' if field in LOGICAL else 'string'
        lines.extend([f'\tcolumn {field}',f'\t\tdataType: {dtype}','\t\tsummarizeBy: none',f'\t\tsourceColumn: {field}'])
    for name,(kind,field) in MEASURES.items():
        # BLANK on absent evidence; no +0 or implicit completeness/identity claim.
        kind_filter='' if kind is None else f'{TABLE}[RelationshipKind] = "{kind}", '
        formula=f'IF(ISEMPTY({TABLE}), BLANK(), CALCULATE(DISTINCTCOUNT({TABLE}[{field}]), '+kind_filter+f'{TABLE}[CanonicalMatchCount] = 1, {TABLE}[CanonicalKey] <> "", {TABLE}[CandidateEligible] = TRUE()))'
        lines.extend([f"\tmeasure '{name}' = {formula}",'\t\tformatString: #,0'])
    lines.extend([f'\tpartition {TABLE} = m','\t\tmode: import','\t\tsource =',*['\t\t\t\t'+x for x in m_source.splitlines()]])
    return '\n'.join(lines)+'\n'

def prepare(document,*,expected_sha256,expected_parts,rows,publications,producer_context,producer_context_sha256):
    if document_hash(document)!=expected_sha256:raise ValueError('Full model preimage drift')
    definition=document.get('definition',{})
    if definition.get('format')!='TMDL':raise ValueError('Explicit TMDL format required')
    preimage(definition,document_hash(definition),expected_parts)
    if fingerprint(producer_context)!=producer_context_sha256:raise ValueError('Independent producer-context pin mismatch')
    typed=project_rows(rows,publications,producer_context)
    parts={p['path']:p for p in definition['parts']}
    required={'definition/model.tmdl','definition/relationships.tmdl','definition/expressions.tmdl','definition/tables/Publication.tmdl'}
    if not required<=set(parts) or f'definition/tables/{TABLE}.tmdl'in parts:raise ValueError('Required model dependency missing or evidence table already exists')
    decode=lambda p:base64.b64decode(parts[p]['payload'],validate=True).decode('utf-8-sig')
    publication=decode('definition/tables/Publication.tmdl')
    if not re.search(r'^\tcolumn CanonicalKey\s*$',publication,re.M):raise ValueError('Canonical model key dependency missing')
    columns=[(m[0] or m[1]).replace("''","'").strip() for m in re.findall(r"^\tcolumn (?:'((?:[^']|'')+)'|([^\n=]+?))\s*(?:=|$)",publication,re.M)]
    if len(columns)!=len(set(columns)) or set(columns)!=set(producer_context['publication_fields']):raise ValueError('Complete model/publication field inventory parity required')
    expressions=decode('definition/expressions.tmdl');expression=producer_context['producer_expression']
    if not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',expression):raise ValueError('Exact producer expression identity required')
    expression_count=len(re.findall(r'^expression '+re.escape(expression)+r'\s*=',expressions,re.M))
    if expression_count>1:raise ValueError('Ambiguous producer expression')
    exp_hash=hashlib.sha256(base64.b64decode(parts['definition/expressions.tmdl']['payload'],validate=True)).hexdigest()
    if producer_context.get('model_sha256')!=expected_sha256 or producer_context.get('producer_expression_part_sha256')!=exp_hash:raise ValueError('Producer/model capture binding mismatch')
    blockers=[] if expression_count==1 else ['existing_typed_producer_expression']
    caps=producer_context.get('capabilities',{})
    if not isinstance(caps,dict):raise ValueError('Structured capability inventory required')
    for name in ('native_typed_input','upstream_byte_hash_verification','canonical_source_parity'):
        cap=caps.get(name,{})
        if not isinstance(cap,dict):raise ValueError('Structured capability receipt required')
        governing_envelope(cap)
        if cap.get('status')!='qualified':blockers.append(name);continue
        exact_text(cap.get('evidence_ref'))
        if cap.get('model_sha256')!=expected_sha256 or cap.get('typed_rows_sha256')!=fingerprint(typed) or cap.get('producer_expression_part_sha256')!=exp_hash:raise ValueError('Capability receipt is not bound to this exact producer and projection')
    common=dict(preparationScope='source_only_candidate',nativeBlockers=['consumer_M_execution','DAX_key_field_filter_parity','native_import_inverse_and_reader_acceptance'],nativeSaveSubmitted=False,nativeAcceptance=False,mutationAuthorized=False,inputModelSHA256=expected_sha256,
        producerContextSHA256=producer_context_sha256,typedRowsSHA256=fingerprint(typed),publicationSHA256=hashlib.sha256(base64.b64decode(parts['definition/tables/Publication.tmdl']['payload'])).hexdigest(),blockers=blockers)
    if blockers:return dict(common,status='blocked',modelDefinition=None)
    templates={n:(ROOT/'config'/n).read_bytes() for n in ('source-relationship-evidence.m','pubmed-relationship-evidence.m')}
    core=templates['source-relationship-evidence.m'].decode();pub=templates['pubmed-relationship-evidence.m'].decode()
    def mtext(value):return '"'+value.replace('#','#(#)').replace('"','""')+'"'
    expected='[ProjectionID='+mtext(producer_context['projection_id'])+', RowCount='+str(len(typed))+', PublicationCount='+str(len(publications))+', PublicationFields={'+','.join(mtext(f) for f in producer_context['publication_fields'])+'}, CanonicalKeys={'+','.join(mtext(p['CanonicalKey']) for p in publications)+'}]'
    source='let\n    Projector = '+core.rstrip()+',\n    PubMedTyped = '+pub.rstrip()+',\n    Rows = Projector('+expression+', '+expected+', PubMedTyped, Publication)\nin Rows'
    result=copy.deepcopy(document);by={p['path']:p for p in result['definition']['parts']}
    root=decode('definition/model.tmdl');rels=decode('definition/relationships.tmdl')
    if TABLE in root or TABLE in rels:raise ValueError('Existing consumer requires reconciliation')
    rid=str(uuid.uuid5(uuid.NAMESPACE_URL,'rims/source-relationships/candidate-publication'))
    if rid in rels:raise ValueError('Existing relationship identity conflict')
    rel=f'\nrelationship {rid}\n\tfromColumn: {TABLE}.CanonicalKey\n\ttoColumn: Publication.CanonicalKey\n\tfromCardinality: many\n\ttoCardinality: one\n\tcrossFilteringBehavior: oneDirection\n'
    for path,addition in [('definition/model.tmdl','\nref table '+TABLE+'\n'),('definition/relationships.tmdl',rel)]:
        by[path]['payload']=base64.b64encode(base64.b64decode(parts[path]['payload'],validate=True)+addition.encode()).decode()
    result['definition']['parts'].append(dict(path=f'definition/tables/{TABLE}.tmdl',payloadType='InlineBase64',payload=base64.b64encode(table_definition(source).encode()).decode()))
    return dict(common,status='prepared',modelDefinition=result,outputModelSHA256=document_hash(result),templateSHA256={k:hashlib.sha256(v).hexdigest() for k,v in templates.items()})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=strict_json_loads(a.input.read_bytes());result=prepare(**data);write_new(a.output,result,[a.input])
    print(result['status']+'; no native save submitted')
if __name__=='__main__':main()
