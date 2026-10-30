"""Add C01/C02/F01 source tables and a funding/capacity detail page offline.

Requires a reviewed FundingCapacityProjection expression; never treats raw ARC
amount strings or opportunities as institutional awards. No native execution.
SPDX-License-Identifier: Apache-2.0
"""
import base64
import copy
import hashlib
import json
import re
from scripts.deploy_report_definition import parts, fingerprint
from scripts.prepare_outcome_reader import emit
from scripts.prepare_publication_outcome_reader import projection

FIELDS = {
    'FundingCapacitySummary': [('period_end','string'), ('active_projects','int64'), ('unknown_project_periods','int64'), ('led_projects','int64'), ('known_lead_projects','int64'), ('unknown_lead_projects','int64'), ('evidenced_researchers','int64'), ('incomplete_participation','int64')],
    'AwardStartCohort': [('currency','string'),('start_year','int64'),('amount','string')],
}


def prepare(model, report, *, model_sha256, report_sha256, expression_sha256, table_template_path):
    if fingerprint(model)!=model_sha256 or fingerprint(report)!=report_sha256: raise ValueError('Exact preimages required')
    mp,rp=parts(model),parts(report)
    expr=mp.get('definition/expressions.tmdl',b'')
    if hashlib.sha256(expr).hexdigest()!=expression_sha256 or not re.search(rb"(?m)^expression (?:FundingCapacityProjection|'FundingCapacityProjection')\s*=",expr):
        raise ValueError('Reviewed funding projection expression required')
    if any('definition/tables/'+name+'.tmdl' in mp for name in FIELDS): raise ValueError('Existing tables require explicit update')
    prefix='definition/pages/FundingCapacity/'
    order_path='definition/pages/pages.json'; order=json.loads(rp[order_path])
    if 'FundingCapacity' in order['pageOrder'] or any(p.startswith(prefix) for p in rp): raise ValueError('Existing page must be preserved')
    template=json.loads(rp[table_template_path])
    if template['visual']['visualType']!='tableEx': raise ValueError('Accepted table visual required')
    m,r=copy.deepcopy(model),copy.deepcopy(report)
    root=mp['definition/model.tmdl'].decode()
    for name,fields in FIELDS.items():
        if re.search(r"(?m)^\s*ref table '?"+name+r"'?(?:\s|$)",root): raise ValueError('Table reference collision')
        lines=['table '+name]
        for field,kind in fields: lines += ['\tcolumn '+field,'\t\tdataType: '+kind,'\t\tsummarizeBy: none','\t\tsourceColumn: '+field]
        rows='{Payload}' if name=='FundingCapacitySummary' else 'Payload[award_cohorts]'
        columns=', '.join(json.dumps(f) for f,_ in fields)
        lines += ['\tpartition '+name+' = m','\t\tmode: import','\t\tsource =','\t\t\tlet Payload = Json.Document(FundingCapacityProjection),', '\t\t\t    Rows = '+rows+',', '\t\t\t    Selected = Table.FromRecords(Rows, {'+columns+'}, MissingField.Error)', '\t\t\tin Selected']
        emit(m,'definition/tables/'+name+'.tmdl','\n'.join(lines)+'\n'); root+='\nref table '+name+'\n'
    for part in m['definition']['parts']:
        if part['path']=='definition/model.tmdl': part['payload']=base64.b64encode(root.encode()).decode()
    emit(r,prefix+'page.json',json.dumps(dict(name='FundingCapacity',displayName='Funding and evidenced capacity',width=1920,height=1080,displayOption='FitToPage')))
    for i,(name,fields) in enumerate(FIELDS.items()):
        v={'name':name,'position':dict(x=24,y=24+i*520,width=1872,height=480,z=i,tabOrder=i), 'visual':{'visualType':'tableEx','query':{'queryState':{'Values':{'projections':[projection(name,f) for f,_ in fields]}}}}}
        if '$schema' in template: v['$schema']=template['$schema']
        emit(r,prefix+'visuals/'+name+'/visual.json',json.dumps(v))
    order['pageOrder'].append('FundingCapacity')
    for part in r['definition']['parts']:
        if part['path']==order_path: part['payload']=base64.b64encode(json.dumps(order).encode()).decode()
    return {'model':m,'report':r,'native_ready':False,'limitations':['Award amounts retain exact decimal text by currency/cohort; no cross-currency total.','Charts, project detail navigation and native rendering remain unverified or unfinished.']}


def main(argv=None):
    import argparse,os,subprocess
    from pathlib import Path
    from scripts.deploy_report_definition import strict
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('model','report','model-sha256','report-sha256','expression-sha256','table-template-path','output'): parser.add_argument('--'+name,required=True)
    a=parser.parse_args(argv)
    result=prepare(strict(Path(a.model).read_bytes()),strict(Path(a.report).read_bytes()),model_sha256=a.model_sha256,report_sha256=a.report_sha256,expression_sha256=a.expression_sha256,table_template_path=a.table_template_path)
    root=Path(__file__).resolve().parents[1];output=Path(a.output).resolve()
    if not output.is_relative_to(root/'private'/'ops'): raise ValueError('Private output required')
    subprocess.run(['git','check-ignore','-q',str(output)],cwd=root,check=True)
    with os.fdopen(os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as handle: json.dump(result,handle,indent=2,allow_nan=False)
    print('PASS_LOCAL_ONLY; no native acceptance')


if __name__=='__main__': main()
