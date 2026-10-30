"""Explicit project/output links backed by caller-supplied canonical inventories.

No fuzzy matching, source acquisition, approval or native persistence.
SPDX-License-Identifier: Apache-2.0
"""
import copy
from scripts.outcome_persistence import digest

KINDS={'publication','award','dataset','software'}


def prepare(records, inventories, *, complete):
    if complete is not True or set(inventories)!={'project'}|KINDS:
        raise ValueError('Complete typed canonical inventories required')
    keys={}
    for kind,values in inventories.items():
        if not isinstance(values,list) or any(not isinstance(v,str) or not v or v!=v.strip() for v in values) or len(values)!=len(set(values)):
            raise ValueError('Exact unique canonical keys required')
        keys[kind]=set(values)
    seen=set();result=[]
    for record in records:
        if set(record)!={'project_id','output_kind','output_id','evidence_id','evidence_revision','evidence_sha256','status'}:
            raise ValueError('Complete explicit project link required')
        kind=record['output_kind']
        if kind not in KINDS or record['project_id'] not in keys['project'] or record['output_id'] not in keys[kind]:
            raise ValueError('Unresolved typed canonical link')
        if record['status'] not in {'candidate','reviewed','withdrawn'}: raise ValueError('Explicit link disposition required')
        import re
        if not isinstance(record['evidence_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',record['evidence_sha256']): raise ValueError('Evidence hash required')
        for field in ('evidence_id','evidence_revision'):
            if not isinstance(record[field],str) or not record[field] or record[field]!=record[field].strip():raise ValueError('Exact evidence identity/version required')
        identity=digest([record['project_id'],kind,record['output_id'],record['evidence_id']])
        if identity in seen:raise ValueError('Duplicate link identity; reconcile revisions first')
        seen.add(identity);row=copy.deepcopy(record);row['link_id']=identity;result.append(row)
    # Only explicitly reviewed links enter a reporting bridge. Keeping candidates
    # and withdrawals alongside it preserves their evidence without admission.
    bridges={kind:sorted({(r['project_id'],r['output_id']) for r in result if r['output_kind']==kind and r['status']=='reviewed'}) for kind in sorted(KINDS)}
    return {'records':result,'bridges':{k:[{'project_id':p,'output_id':o} for p,o in v] for k,v in bridges.items()},'inventory_sha256':digest(inventories),'native_acceptance':False}


def main(argv=None):
    import argparse,json,os,subprocess
    from pathlib import Path
    from scripts.deploy_report_definition import strict
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv);result=prepare(**strict(Path(args.input).read_bytes()))
    root=Path(__file__).resolve().parents[1];out=Path(args.output).resolve()
    if not out.is_relative_to(root/'private'/'ops'):raise ValueError('Private output required')
    subprocess.run(['git','check-ignore','-q',str(out)],cwd=root,check=True)
    with os.fdopen(os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:json.dump(result,f,indent=2,allow_nan=False)
    print('PASS_LOCAL_ONLY; caller review assertions are not independently certified')


if __name__=='__main__':main()
