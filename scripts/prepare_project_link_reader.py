"""Add persisted project/output audit and reviewed bridges to existing definitions.

No refresh, source admission or visual acceptance is implied.
SPDX-License-Identifier: Apache-2.0
"""
import base64
import copy
import json
import re
from scripts.deploy_report_definition import parts, fingerprint
from scripts.prepare_outcome_binding import expression
from scripts.prepare_outcome_reader import emit
from scripts.prepare_publication_outcome_reader import projection

TABLES = {
 'ProjectOutputLink': ['project_id','output_kind','output_id','evidence_id','evidence_revision','evidence_sha256','status','link_id','lineage_id','revision_id'],
 'ProjectOutputBridge': ['project_id','output_kind','output_id'],
 'ProjectLinkProject': ['project_id'],
}


def table(name):
    columns=TABLES[name]
    lines=['table '+name]
    for c in columns:lines += ['\tcolumn '+c,'\t\tdataType: string','\t\tsummarizeBy: none','\t\tsourceColumn: '+c]
    if name=='ProjectOutputBridge':lines += ["\tmeasure 'Reviewed project output links' = COALESCE(COUNTROWS(ProjectOutputBridge), 0)",'\t\tformatString: 0']
    source={
      'ProjectOutputLink':'Record.Field(Payload, "records")',
      'ProjectLinkProject':'List.Transform(List.Distinct(List.Transform(Record.Field(Payload, "records"), each Record.Field(_, "project_id"))), each [project_id = _])',
      'ProjectOutputBridge':'List.Combine(List.Transform({"publication", "award", "dataset", "software"}, (kind) => List.Transform(Record.Field(Record.Field(Payload, "bridges"), kind), each Record.AddField(_, "output_kind", kind))))',
    }[name]
    lines += ['\tpartition '+name+' = m','\t\tmode: import','\t\tsource =','\t\t\tlet','\t\t\t    Payload = Json.Document(ProjectLinkProjection),','\t\t\t    Rows = '+source+',','\t\t\t    Selected = Table.FromRecords(Rows, '+'{'+', '.join(json.dumps(c) for c in columns)+'}'+', MissingField.Error),','\t\t\t    Typed = Table.TransformColumnTypes(Selected, {'+', '.join('{'+json.dumps(c)+', type text}' for c in columns)+'}),','\t\t\t    Result = Table.Distinct(Typed)' if name!='ProjectOutputLink' else '\t\t\t    Result = Typed','\t\t\tin Result']
    return '\n'.join(lines)+'\n'


def prepare(model,report,target,*,model_sha256,report_sha256):
    if fingerprint(model)!=model_sha256 or fingerprint(report)!=report_sha256:raise ValueError('Exact current preimages required')
    if target.get('journalField')!='ProjectLinkJournal' or target.get('projectionField')!='ProjectLinkProjection':raise ValueError('Dedicated project-link target required')
    mp,rp=parts(model),parts(report);m,r=copy.deepcopy(model),copy.deepcopy(report)
    expressions=mp['definition/expressions.tmdl'].decode()
    if re.search(r"(?m)^expression '?ProjectLinkProjection'?\s*=",expressions):raise ValueError('Existing project binding requires reconciliation')
    binding=expression(target).replace('expression OutcomeProjection =','expression ProjectLinkProjection =')
    binding=re.sub(r'\t\tRequired = .*', '\t\tRequired = {"records", "bridges", "history", "history_sha256", "inventory_sha256"},',binding)
    binding=binding.replace('Incomplete outcome projection','Incomplete project-link projection')
    changed={'definition/expressions.tmdl':expressions+'\n'+binding,'definition/model.tmdl':mp['definition/model.tmdl'].decode()}
    for name in TABLES:
        path='definition/tables/'+name+'.tmdl'
        if path.casefold() in {p.casefold() for p in mp} or re.search(r"(?m)^\s*ref table '?"+name+r"'?(?:\s|$)",changed['definition/model.tmdl']):raise ValueError('Existing project table collision')
        changed['definition/model.tmdl']+='\nref table '+name+'\n';emit(m,path,table(name))
    relationships=mp.get('definition/relationships.tmdl',b'').decode()
    for identity,name in [('2687f17f-e130-5aa4-8b5c-c8ed1b3cb104','ProjectOutputLink'),('068515c6-6296-5592-a317-bf680e3424b5','ProjectOutputBridge')]:
        if identity in relationships:raise ValueError('Relationship identity collision')
        relationships+='\nrelationship '+identity+'\n\tfromColumn: '+name+'.project_id\n\ttoColumn: ProjectLinkProject.project_id\n'
    changed['definition/relationships.tmdl']=relationships
    for path,text in changed.items():
        part=next((p for p in m['definition']['parts'] if p['path']==path),None)
        if part:part['payload']=base64.b64encode(text.encode()).decode()
        else:emit(m,path,text)
    page='ProjectOutputRelationships';prefix='definition/pages/'+page+'/'
    order=json.loads(rp['definition/pages/pages.json'])
    if page in order['pageOrder'] or any(p.startswith(prefix) for p in rp):raise ValueError('Existing report page must be preserved')
    template=next(json.loads(v) for p,v in rp.items() if p.endswith('/visual.json') and json.loads(v).get('visual',{}).get('visualType')=='tableEx')
    page_schema=json.loads(rp['definition/pages/'+order['pageOrder'][0]+'/page.json'])['$schema']
    emit(r,prefix+'page.json',json.dumps({'$schema':page_schema,'name':page,'displayName':'Project outputs and relationship evidence','width':1920,'height':1080,'displayOption':'FitToPage'}))
    specs=[('project-selector','slicer',[projection('ProjectLinkProject','project_id')],(24,24,450,180)),('reviewed-count','tableEx',[projection('ProjectOutputBridge','Reviewed project output links',measure=True)],(498,24,600,180)),('reviewed-links','tableEx',[projection('ProjectOutputBridge',c) for c in TABLES['ProjectOutputBridge']],(24,228,1872,300)),('relationship-audit','tableEx',[projection('ProjectOutputLink',c) for c in TABLES['ProjectOutputLink']],(24,552,1872,504))]
    for ordinal,(name,kind,projections,rect) in enumerate(specs):
        v={'$schema':template['$schema'],'name':name,'position':dict(zip(['x','y','width','height'],rect),z=ordinal,tabOrder=ordinal),'visual':{'visualType':kind,'query':{'queryState':{'Values':{'projections':projections}}}}}
        emit(r,prefix+'visuals/'+name+'/visual.json',json.dumps(v))
    order['pageOrder'].append(page)
    for part in r['definition']['parts']:
        if part['path']=='definition/pages/pages.json':part['payload']=base64.b64encode(json.dumps(order).encode()).decode()
        if part['path']=='definition/report.json':
            body=json.loads(base64.b64decode(part['payload']));body.pop('linguisticSchemaSyncVersion',None);part['payload']=base64.b64encode(json.dumps(body).encode()).decode()
    return {'model':m,'report':r,'native_runtime_verified':False,'visual_acceptance':False}


def main():
    import argparse
    from pathlib import Path
    from scripts.deploy_report_definition import strict
    from scripts.outcome_intake import ROOT, save
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('model','report','target','model-sha256','report-sha256','output'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();output=Path(args.output).resolve()
    if not output.is_relative_to(ROOT/'private/ops'):raise ValueError('Private output required')
    result=prepare(strict(Path(args.model).read_bytes()),strict(Path(args.report).read_bytes()),strict(Path(args.target).read_bytes()),model_sha256=args.model_sha256,report_sha256=args.report_sha256)
    save(output,result)
    print('Prepared additive project-link definitions; no deployment or refresh')


if __name__=='__main__':main()
