"""Prepare source-candidate pages against exact supplied model/binding evidence.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse,base64,copy,hashlib,json,os,re,shutil,tempfile,uuid,sys
from pathlib import Path
if not __package__:sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if __package__:
    from scripts.prepare_source_relationship_model import TABLE,COLUMNS,TEXT,LOGICAL,MEASURES,table_definition,document_hash,preimage,fingerprint,strict_json_loads,ROOT
    from scripts.dashboard_reader_source import digest
    from scripts.prepare_dashboard_overview import projection,literal
    from scripts.plan_publication_stub_restore import private_output,utc
    from scripts.award_identifier_crosswalks import governing_envelope,exact_text
else:
    from prepare_source_relationship_model import TABLE,COLUMNS,TEXT,LOGICAL,MEASURES,table_definition,document_hash,preimage,fingerprint,strict_json_loads,ROOT
    from dashboard_reader_source import digest
    from prepare_dashboard_overview import projection,literal
    from plan_publication_stub_restore import private_output,utc
    from award_identifier_crosswalks import governing_envelope,exact_text
PAGES=('SourceCollaboration','SourceStudyAwards')

def category_filter(column,value):
    return {'name':'candidate-'+column,'field':{'Column':{'Expression':{'SourceRef':{'Entity':TABLE}},'Property':column}},'type':'Categorical',
      'filter':{'Version':2,'From':[{'Name':'e','Entity':TABLE,'Type':0}], 'Where':[{'Condition':{'In':{'Expressions':[{'Column':{'Expression':{'SourceRef':{'Source':'e'}},'Property':column}}],'Values':[[{'Literal':{'Value':"'"+value.replace("'","''")+"'"}}]]}}}]}}

def _capture(source,expected):
    if source.is_symlink() or (source/'.pbi').exists() or any(p.is_symlink() for p in source.rglob('*')):raise ValueError('Clean nonsymlink report capture required')
    files={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file()}
    if digest(files)!=expected:raise ValueError('Complete report bundle drift')
    parsed={p:strict_json_loads(b) for p,b in files.items() if p.endswith(('.json','.pbir'))}
    required={'definition.pbir','definition/report.json','definition/pages/pages.json'}
    if not required<=set(files):raise ValueError('Complete modern PBIR capture required')
    order=parsed['definition/pages/pages.json'].get('pageOrder')
    pages={Path(p).parent.name for p in files if p.startswith('definition/pages/') and p.endswith('/page.json') and len(Path(p).parts)==4}
    if not isinstance(order,list) or len(order)!=len(set(order)) or set(order)!=pages or not {'ResearchRelationships','SourceFreshness'}<=pages or any(p in pages for p in PAGES):raise ValueError('Exact existing page inventory required')
    return files,parsed

def _model(packet,expected,expected_parts):
    if fingerprint(packet)!=expected or packet.get('status')!='prepared' or packet.get('nativeSaveSubmitted') is not False or packet.get('nativeAcceptance') is not False or packet.get('mutationAuthorized') is not False or packet.get('blockers')!=[]:raise ValueError('Unresolved or unpinned model preparation')
    model=packet['modelDefinition']
    if document_hash(model)!=packet.get('outputModelSHA256'):raise ValueError('Prepared model digest drift')
    definition=model.get('definition',{})
    if definition.get('format')!='TMDL':raise ValueError('Typed TMDL model required')
    preimage(definition,document_hash(definition),expected_parts)
    part=next((p for p in definition['parts'] if p['path']==f'definition/tables/{TABLE}.tmdl'),None)
    if part is None:raise ValueError('Typed evidence table dependency missing')
    text=base64.b64decode(part['payload'],validate=True).decode()
    if text.split('\tpartition ',1)[0]!=table_definition('').split('\tpartition ',1)[0]:raise ValueError('Typed field/measure semantics contract drift')
    decl=list(re.finditer(r'^\t(column|measure|partition) (.+)$',text,re.M));columns={};measures=set()
    for i,m in enumerate(decl):
        if m[1]=='column':
            if m[2]in columns:raise ValueError('Duplicate model field')
            columns[m[2]]=text[m.end():decl[i+1].start() if i+1<len(decl) else len(text)]
        elif m[1]=='measure':measures.add(m[2].split(' = ',1)[0].strip("'"))
    if set(columns)!=set(COLUMNS) or not set(MEASURES)<=measures:raise ValueError('Complete typed reader dependencies required')
    for name,block in columns.items():
        dtype='boolean' if name in LOGICAL else 'int64' if name=='CanonicalMatchCount' else 'string'
        if re.findall(r'^\t\tdataType: (\w+)\s*$',block,re.M)!=[dtype] or re.findall(r'^\t\tsummarizeBy: (\w+)\s*$',block,re.M)!=['none']:raise ValueError('Reader field type or summarization drift')
    pub=next(p for p in definition['parts'] if p['path']=='definition/tables/Publication.tmdl')
    if hashlib.sha256(base64.b64decode(pub['payload'],validate=True)).hexdigest()!=packet['publicationSHA256']:raise ValueError('Protected publication part changed')
    if set(packet.get('templateSHA256',{}))!={'source-relationship-evidence.m','pubmed-relationship-evidence.m'}:raise ValueError('Complete producer template bindings required')
    for name,sha in packet['templateSHA256'].items():
        if name not in ('source-relationship-evidence.m','pubmed-relationship-evidence.m') or hashlib.sha256((ROOT/'config'/name).read_bytes()).hexdigest()!=sha:raise ValueError('Producer template contract drift')
    return model

def _binding(files,bundle_hash,packet,evidence,expected):
    if not isinstance(evidence,dict) or fingerprint(evidence)!=expected:raise ValueError('Independent current binding evidence required')
    governing_envelope(evidence)
    for k in ('report_id','model_id'):
        v=exact_text(evidence.get(k))
        if str(uuid.UUID(v))!=v:raise ValueError('Exact current report/model UUID required')
    for k in ('report_capture_ref','model_capture_ref'):exact_text(evidence.get(k))
    utc(evidence.get('observed_at_utc'))
    if (evidence.get('complete') is not True or evidence.get('report_bundle_sha256')!=bundle_hash or evidence.get('source_model_sha256')!=packet['inputModelSHA256'] or evidence.get('candidate_model_sha256')!=packet['outputModelSHA256']):raise ValueError('Exact source/candidate identity association missing')
    response=evidence.get('report_binding_readback',{});governing_envelope(response);body=response.get('text',{});governing_envelope(body)
    if type(response.get('status_code')) is not int or response['status_code']!=200 or body.get('id')!=evidence['report_id'] or body.get('datasetId')!=evidence['model_id']:raise ValueError('Exact saved binding readback required')
    ref=strict_json_loads(files['definition.pbir']).get('datasetReference',{})
    if set(ref)!={'byConnection'} or set(ref['byConnection'])!={'connectionString'}:raise ValueError('Observed supported byConnection binding required')
    text=ref['byConnection']['connectionString'];properties={}
    if not isinstance(text,str):raise ValueError('Binding connection string required')
    for item in text.split(';'):
        if not item:continue
        pair=item.split('=',1)
        if len(pair)!=2 or pair[0].strip().casefold() in properties:raise ValueError('Ambiguous connection binding')
        properties[pair[0].strip().casefold()]=pair[1]
    if properties.get('semanticmodelid')!=evidence['model_id']:raise ValueError('Model binding identity mismatch')

def prepare(source,output,*,expected_sha256,model_packet,model_packet_sha256,expected_model_parts,binding_evidence,binding_sha256):
    source,output=Path(source),Path(output)
    if output.resolve().is_relative_to(source.resolve()):raise ValueError('Candidate must remain outside its source capture')
    private_output(output,[source],root=ROOT)
    files,parsed=_capture(source,expected_sha256);_model(model_packet,model_packet_sha256,expected_model_parts)
    _binding(files,expected_sha256,model_packet,binding_evidence,binding_sha256)
    base='definition/pages/ResearchRelationships/'
    templates={kind:parsed.get(base+'visuals/'+name+'/visual.json') for kind,name in [('textbox','relationships-guidance'),('cardVisual','candidates'),('barChart','author-pattern')]}
    if any(not isinstance(v,dict) or v.get('visual',{}).get('visualType')!=kind for kind,v in templates.items()):raise ValueError('Exact existing reader template dependencies required')
    result=dict(files);order=copy.deepcopy(parsed['definition/pages/pages.json'])
    def emit(path,value):result[path]=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    for pageid,title in zip(PAGES,('Candidate source relationships','Candidate study and award assertions')):
        page=f'definition/pages/{pageid}'
        emit(page+'/page.json',dict(name=pageid,displayName=title,width=1920,height=1080,displayOption='FitToPage'))
        ordinal=0
        def add(name,kind,rect,roles=None,words=None):
            nonlocal ordinal
            template='barChart' if kind=='tableEx' else kind
            v=copy.deepcopy(templates[template]);v['name']=name;v['position']=dict(zip(('x','y','width','height'),rect),z=ordinal*100,tabOrder=ordinal*1000);ordinal+=1
            visual=v['visual'];visual['visualType']=kind
            for k in ('query','objects','columnProperties','projections','prototypeQuery'):visual.pop(k,None)
            v.pop('filterConfig',None)
            style={k:copy.deepcopy(value) for k,value in visual.get('visualContainerObjects',{}).items() if k in ('background','border','padding')}
            style['title']=[{'properties':{'show':literal('false'),'text':{'expr':{'Literal':{'Value':"'"+name+"'"}}}}}]
            style['general']=[{'properties':{'altText':{'expr':{'Literal':{'Value':"'Candidate source evidence: "+name+"'"}}}}}]
            visual['visualContainerObjects']=style
            if roles:visual['query']={'queryState':{k:{'projections':values} for k,values in roles.items()}}
            if words is not None:visual['objects']={'general':[{'properties':{'paragraphs':[{'textRuns':[{'value':words,'textStyle':{'fontFamily':'Segoe UI','fontSize':'14pt'}}]}]}}]}
            emit(page+'/visuals/'+name+'/visual.json',v)
        add('heading','textbox',(32,16,1856,64),words=title)
        add('limits','textbox',(32,88,1856,144),words='Candidate source assertions only. Explicit source IDs and ORCID syntax do not authenticate people or establish institutional funding, projects or outcomes. Unknown dates and retraction states remain unknown. Human review and native G06 admission remain separate. Empty evidence is unavailable, not an inferred zero.')
        measures=list(MEASURES) if pageid==PAGES[0] else [n for n in MEASURES if n!='Candidate author-reference keys']
        for i,name in enumerate(measures):add('count-'+str(i),'cardVisual',(32+i*464,248,448,128),{'Data':[projection(TABLE,name,measure=True,label=name)]})
        columns=['CanonicalKey','SourceProvider','RelationshipKind','ToKey','SourceVersion','SourceRetracted','CanonicalMatchCount'] if pageid==PAGES[0] else ['EvidenceKey','SourceWorkID','ReferenceType','SourceURL','ObservedUTC','SourcePathsJSON']
        add('evidence','tableEx',(32,400,1856,640),{'Values':[projection(TABLE,f,label=f) for f in columns]})
        if pageid==PAGES[1]:
            meta=strict_json_loads(result[page+'/page.json'])
            kinds=['publication_award','publication_study_reference','publication_grant_reference','publication_award_crosswalk','publication_award_crosswalk_diagnostic','publication_government_award_reference','publication_government_award_diagnostic']
            filter=category_filter('RelationshipKind',kinds[0]);filter['filter']['Where'][0]['Condition']['In']['Values']=[[{'Literal':{'Value':"'"+kind+"'"}}] for kind in kinds]
            meta['filterConfig']={'filters':[filter]};emit(page+'/page.json',meta)
        order['pageOrder'].append(pageid)
    emit('definition/pages/pages.json',order)
    changed={p for p in files if result[p]!=files[p]}
    if changed!={'definition/pages/pages.json'}:raise ValueError('Original report content changed')
    # Drift is checked against the same complete scope immediately before installation.
    _capture(source,expected_sha256)
    output.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.relationship-',dir=output.parent))
    try:
        for name,raw in result.items():
            path=stage/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        if output.exists():raise ValueError('Exclusive candidate output required')
        # mkdir reserves the exact path without overwriting an existing object.
        output.mkdir()
        try:
            for item in stage.iterdir():os.rename(item,output/item.name)
        except BaseException:
            shutil.rmtree(output);raise
    finally:shutil.rmtree(stage)
    return dict(sourceSHA256=expected_sha256,candidateSHA256=digest(result),newPages=list(PAGES),originalSemanticsAndLinksPreserved=True,
        nativeSaveSubmitted=False,nativeAcceptance=False,mutationAuthorized=False,nativeBlockers=['E04_exact_version_import_and_inverse','native_M_DAX_key_field_parity','current_reader_identity_and_rendering'],modelPacketSHA256=model_packet_sha256)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);a=p.parse_args()
    args=strict_json_loads(a.input.read_bytes());print(json.dumps(prepare(**args),indent=2))
if __name__=='__main__':main()
