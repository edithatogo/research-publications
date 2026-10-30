"""Read-only proposal mapping of retained DoRA and award context snapshots.

No identity approval, native writes or inference from names/titles.
SPDX-License-Identifier: Apache-2.0
"""
import argparse
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from scripts.deploy_report_definition import strict
from scripts.outcome_persistence import digest
from scripts.outcome_intake import ROOT,save


def rows(document):
    if any('next' in k.lower() for k in document):raise ValueError('Complete selected snapshot required')
    return document['value']


def identity(value):
    return value if isinstance(value,str) and value and value==value.strip() else None


def iso(value):
    if not value:return None
    try:return date.fromisoformat(value).isoformat() if len(value)==10 else None
    except (ValueError,TypeError):return None


def prepare(project_document,award_document):
    projects,awards=rows(project_document),rows(award_document)
    counts=Counter(r.get('Project_x0020_ID') for r in projects)
    award_counts=Counter(r.get('SourceKey') for r in awards)
    output={'projects':[],'awards':[],'participation':[],'proposed_links':[],
            'unmatched':[],'ambiguous':[],'source_hashes':{'projects':digest(project_document),'awards':digest(award_document)},
            'approved':False,'native_ready':False}
    project_index={}
    for r in projects:
        key=identity(r.get('Project_x0020_ID'));evidence={'source_key':r.get('DORAActivityKey'),'item_id':r.get('Id'),'sha256':digest(r)}
        if not key:output['unmatched'].append({'kind':'project','reason':'missing_exact_project_id','evidence':evidence});continue
        pid='dora-project:'+key
        proposed={'project_id':pid,'start_date':iso(r.get('Start_x0020_Date')),'end_date':iso(r.get('Finish_x0020_Date')),'end_date_known':iso(r.get('Finish_x0020_Date')) is not None,'chhhs_led':None}
        reasons=['leadership_not_qualified']
        if proposed['start_date'] is None:reasons.append('start_date_unavailable_or_unqualified')
        if not proposed['end_date_known']:reasons.append('end_date_unknown_not_open_ended')
        if counts[key]>1:reasons.append('duplicate_project_id');output['ambiguous'].append({'kind':'project','project_id':pid,'source_count':counts[key],'evidence':evidence})
        else:project_index[key]=pid
        output['projects'].append({'candidate':proposed,'status':'candidate','gaps':reasons,'evidence':evidence,'source_record':r})
        if r.get('PI_x0020_Name') or r.get('PI_x0020_Email'):
            participation={'participation_id':'dora-pi:'+digest([r.get('DORAActivityKey'),r.get('Id')]),'project_id':pid,'person_id':None,'role':'principal_investigator','start_date':None,'end_date':None,'end_date_known':False}
            output['participation'].append({'candidate':participation,'status':'unmatched','gaps':['person_identity_unresolved','participation_period_unknown'],'source_name':r.get('PI_x0020_Name'),'source_email':r.get('PI_x0020_Email'),'evidence':evidence})
            output['unmatched'].append({'kind':'participation','reason':'person_identity_unresolved','evidence':evidence})
    for r in awards:
        key=identity(r.get('SourceKey'));evidence={'source_key':key,'item_id':r.get('Id'),'sha256':digest(r)}
        if not key:output['unmatched'].append({'kind':'award','reason':'missing_exact_source_key','evidence':evidence});continue
        gaps=['currency_not_explicit','award_date_not_qualified','institutional_attribution_not_qualified']
        amount=r.get('ReportedAmountSource')
        try:
            if not isinstance(amount,str) or not Decimal(amount).is_finite() or Decimal(amount)<0:raise ValueError()
        except (InvalidOperation,ValueError):amount=None;gaps.append('amount_unqualified')
        if award_counts[key]>1:output['ambiguous'].append({'kind':'award','award_id':key,'source_count':award_counts[key],'evidence':evidence});gaps.append('duplicate_award_key')
        output['awards'].append({'candidate':{'award_id':key,'record_kind':'Award','amount':amount,'currency':None,'start_date':None},'status':'candidate','gaps':gaps,'evidence':evidence,'source_record':r})
        raw=r.get('RelatedIdentifiersJSON')
        try:related=strict(raw.encode()) if isinstance(raw,str) and raw else {}
        except ValueError:related={};output['unmatched'].append({'kind':'award_project','reason':'malformed_related_identifiers','evidence':evidence})
        # Only an explicit project identifier in this source contract is usable.
        project=identity(related.get('project_id')) if isinstance(related,dict) else None
        if project in project_index and award_counts[key]==1:
            record={'project_id':project_index[project],'output_kind':'award','output_id':key,'evidence_id':key,'evidence_revision':str(r.get('OData__UIVersionString') or r.get('odata.etag') or digest(r)),'evidence_sha256':digest(r),'status':'candidate'}
            output['proposed_links'].append(record)
        else:output['unmatched'].append({'kind':'award_project','reason':'ambiguous_project_or_award' if project and (counts[project]>1 or award_counts[key]>1) else 'missing_or_unresolved_explicit_project_id','evidence':evidence})
    output['counts']={k:len(output[k]) for k in ['projects','awards','participation','proposed_links','unmatched','ambiguous']}
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['projects','awards','output']:parser.add_argument('--'+name,required=True)
    args=parser.parse_args();output=Path(args.output).resolve()
    if not output.is_relative_to(ROOT/'private/ops'):raise ValueError('Private output required')
    result=prepare(strict(Path(args.projects).read_bytes()),strict(Path(args.awards).read_bytes()));save(output,result)
    print(result['counts'])


if __name__=='__main__':main()
