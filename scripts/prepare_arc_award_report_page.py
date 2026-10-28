"""Prepare one ARC award-context page in the accepted Legacy report; no network effects."""
from __future__ import annotations
import argparse
import base64
import copy
import json
import re
import uuid
from pathlib import Path
# SPDX-License-Identifier: Apache-2.0
if __package__:
    from scripts.build_legacy_report_json import make_visual_container
    from scripts.prepare_arc_award_model import FIELDS
    from scripts.plan_publication_stub_restore import utc
    from scripts.reconcile_arc_awards_snapshots import fingerprint, preimage, write_new, strict_json_loads
else:
    from build_legacy_report_json import make_visual_container
    from prepare_arc_award_model import FIELDS
    from plan_publication_stub_restore import utc
    from reconcile_arc_awards_snapshots import fingerprint, preimage, write_new, strict_json_loads

PAGE_ID = 'ARCAwardContextReader'
PAGE_LABEL = 'ARC award context'
TABLE = 'ARCAwardContext'
SCHEMA = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'
LABELS = {'SourceID':'Source record ID','Source':'Source','AwardCode':'Award code',
          'Title':'Source title','Status':'Source status','Amount':'Source amount (text)',
          'URL':'Source record','RetrievedUTC':'Source acquired (UTC)'}


def projection(column, *, count=False):
    if column not in LABELS or count and column != 'SourceID':
        raise ValueError('Field outside accepted award reader')
    field = {'Column': {'Expression': {'SourceRef': {'Entity':TABLE}}, 'Property':column}}
    ref = TABLE + '.' + column
    label = LABELS[column]
    if count:
        # Function5 is CountNonNull, qualified from the existing native report.
        # Accepted SourceID values are nonempty and unique; amounts are never summed.
        field = {'Aggregation': {'Expression':field, 'Function':5}}
        ref = 'CountNonNull(' + ref + ')';label = 'ARC source records'
    return {'field':field,'queryRef':ref,'nativeQueryRef':label,'displayName':label}


def page_visuals():
    legacy,modern=[],[]
    def add(name,kind,title,rect,roles=None,text=None):
        roles={role:[projection(c,count=kind=='cardVisual') for c in cols]
               for role,cols in (roles or {}).items()}
        order=len(legacy);container=make_visual_container(name,kind,title,rect,text=text,order=order)
        config=json.loads(container['config']);single=config['singleVisual']
        if roles:
            single['projections']={r:[{'queryRef':p['queryRef']} for p in ps] for r,ps in roles.items()}
            single['columnProperties']={p['queryRef']:{'displayName':p['displayName']} for ps in roles.values() for p in ps}
            selected=[]
            for ps in roles.values():
                for p in ps:
                    field=json.loads(json.dumps(p['field']).replace('"Entity": "ARCAwardContext"','"Source": "a"'))
                    selected.append({**field,'Name':p['queryRef'],'NativeReferenceName':p['nativeQueryRef']})
            single['prototypeQuery']={'Version':2,'From':[{'Name':'a','Entity':TABLE,'Type':0}],'Select':selected}
        if kind=='cardVisual':
            single['objects']={'label':[{'selector':{'id':'default'},'properties':{'show':{'expr':{'Literal':{'Value':'false'}}}}}],
                'value':[{'selector':{'id':'default'},'properties':{'fontSize':{'expr':{'Literal':{'Value':'40D'}}}}}]}
        if name=='arc-code':
            single['objects']['general']=[{'properties':{'selfFilterEnabled':{'expr':{'Literal':{'Value':'true'}}}}}]
        if kind=='tableEx':
            head=single['objects']['columnHeaders'][0]['properties'];head['columnAdjustment']={'expr':{'Literal':{'Value':"'fixedWidth'"}}};head['autoSizeColumnWidth']={'expr':{'Literal':{'Value':'false'}}}
            single['objects']['columnWidth']=[{'selector':{'metadata':p['queryRef']},'properties':{'value':{'expr':{'Literal':{'Value':str(w)+'D'}}}}} for p,w in zip(roles['Values'],[170,830,190,190,140,300],strict=True)]
            # URL is already WebUrl in the additive model. Use the canonical
            # global icon option; tableEx does not honour the retained webURL rule.
            single['objects']['values'][0]['properties']['urlIcon']={'expr':{'Literal':{'Value':'true'}}}
        container['config']=json.dumps(config,ensure_ascii=False);legacy.append(container)
        visual={k:copy.deepcopy(v) for k,v in single.items() if k not in ['projections','prototypeQuery','vcObjects','columnProperties']}
        visual['visualContainerObjects']=copy.deepcopy(single['vcObjects'])
        if roles:visual['query']={'queryState':{r:{'projections':ps} for r,ps in roles.items()}}
        x,y,w,h=rect;modern.append({'$schema':SCHEMA+'visualContainer/2.0.0/schema.json','name':name,'position':{'x':x,'y':y,'width':w,'height':h,'z':order*100,'tabOrder':order},'visual':visual})
    add('heading','textbox','',(32,16,1856,56),text='ARC AWARD CONTEXT | Retained source records')
    add('arc-guidance','textbox','',(32,80,1856,92),text=(
        'Historical ARC source context, not funding opportunities or applications. Records include Closed, Active, Declined and Not yet accepted source statuses. '
        'This global source snapshot is not CHHHS institutional attribution or a performance measure.'))
    add('arc-total','cardVisual','ARC source records in selection',(32,188,350,180),{'Data':['SourceID']})
    add('arc-source','slicer','Source',(398,188,330,100),{'Values':['Source']})
    add('arc-status','slicer','Source status',(744,188,480,100),{'Values':['Status']})
    add('arc-code','slicer','Award code — search or select',(1240,188,648,100),{'Values':['AwardCode']})
    add('arc-reset-guidance','textbox','',(398,304,1490,64),text='Clear the source, status and award-code slicers (or Reset to default) to restore all source records. Open Source record for the original ARC entry.')
    add('arc-records','tableEx','ARC source records — amounts retained as text; no totals',(32,390,1856,562),{'Values':['AwardCode','Title','Status','Amount','URL','RetrievedUTC']})
    add('arc-footer','textbox','',(32,972,1856,84),text=(
        'Coverage: the accepted retained ARC snapshot, not a current opportunities feed. Blank source amounts and other unknowns remain unknown, not zero. '
        'Award amounts are source text and are not summed. Source dates and statuses are retained without inferred lifecycle decisions.'))
    return legacy,modern


def reader_dependencies(model, expected_sha256, expected_parts):
    """Validate only this reader's exact TMDL dependencies; no fixed part count."""
    if fingerprint(model)!=expected_sha256: raise ValueError('Complete model preimage digest mismatch')
    model = model['definition'] if set(model)=={'definition'} else model
    if model.get('format') != 'TMDL': raise ValueError('Complete TMDL model required')
    preimage(model, fingerprint(model), expected_parts)
    parts={p['path']:base64.b64decode(p['payload'],validate=True).decode('utf-8-sig') for p in model['parts']}
    root=parts.get('definition/model.tmdl','')
    if len(re.findall(r'^ref table ARCAwardContext\s*$',root,re.M)) != 1:
        raise ValueError('Exact ARC model table reference required')
    table=parts.get('definition/tables/ARCAwardContext.tmdl','')
    if re.findall(r'^table (.+)$',table,re.M) != ['ARCAwardContext']:
        raise ValueError('Exact ARCAwardContext table required')
    declarations=list(re.finditer(r'^\t(column|measure|partition) ([^\n]+)$',table,re.M))
    columns={}
    for index,decl in enumerate(declarations):
        if decl[1]!='column': continue
        name=decl[2]
        if name in columns: raise ValueError('Duplicate ARC column')
        columns[name]=table[decl.end():declarations[index+1].start() if index+1<len(declarations) else len(table)]
    for field in FIELDS:
        block=columns.get(field,'')
        if (re.findall(r'^\t\tdataType: (\w+)\s*$',block,re.M) != ['string']
                or re.findall(r'^\t\tsummarizeBy: (\w+)\s*$',block,re.M) != ['none']
                or re.findall(r'^\t\tsourceColumn: (\w+)\s*$',block,re.M) != [field]):
            raise ValueError('ARC reader requires exact string, no-summary source columns')
        if field=='URL' and re.findall(r'^\t\tdataCategory: (\w+)\s*$',block,re.M) != ['WebUrl']:
            raise ValueError('ARC URL requires WebUrl metadata')


def binding_contract(definition, model, evidence, expected_sha256):
    """Require separately pinned capture association and observed binding readback.

    Hashes prove supplied-byte association, not the authenticity or currency of
    the caller's capture evidence. Missing native identity blocks preparation.
    """
    if not isinstance(evidence,dict) or fingerprint(evidence)!=expected_sha256:
        raise ValueError('Independently pinned binding evidence required; identity unqualified')
    for key in ('report_id','model_id'):
        value=evidence.get(key)
        if not isinstance(value,str) or str(uuid.UUID(value))!=value:
            raise ValueError('Exact report/model UUID identities required')
    for key in ('report_capture_ref','model_capture_ref'):
        value=evidence.get(key)
        if not isinstance(value,str) or not value or value!=value.strip():
            raise ValueError('Independent current capture references required')
    utc(evidence.get('observed_at_utc'))
    if (evidence.get('complete') is not True
            or evidence.get('report_preimage_sha256')!=fingerprint(definition)
            or evidence.get('model_preimage_sha256')!=fingerprint(model)):
        raise ValueError('Binding evidence must bind both complete current preimages')
    response=evidence.get('report_binding_readback',{})
    body=response.get('text',{})
    if (type(response.get('status_code')) is not int or response['status_code']!=200
            or not isinstance(body,dict) or body.get('id')!=evidence['report_id']
            or body.get('datasetId')!=evidence['model_id']):
        raise ValueError('Successful exact report/dataset binding readback required')
    part=next(p for p in definition['definition']['parts'] if p['path']=='definition.pbir')
    binding=strict_json_loads(base64.b64decode(part['payload'],validate=True))
    reference=binding.get('datasetReference',{})
    if set(reference)!={'byConnection'} or set(reference['byConnection'])!={'connectionString'}:
        raise ValueError('Observed byConnection binding shape required; identity unqualified')
    text=reference['byConnection']['connectionString']
    if not isinstance(text,str): raise ValueError('Binding connection string required')
    properties={}
    for component in text.split(';'):
        if not component: continue
        pair=component.split('=',1)
        if len(pair)!=2 or not pair[0].strip() or pair[0].strip().casefold() in properties:
            raise ValueError('Ambiguous binding connection string')
        properties[pair[0].strip().casefold()]=pair[1]
    if properties.get('semanticmodelid')!=evidence['model_id']:
        raise ValueError('Report connection and independent model identity disagree')


def prepare(definition, *, expected_sha256, expected_parts, model_definition,
            model_expected_sha256, model_expected_parts, binding_evidence, binding_sha256):
    if definition.get('definition',{}).get('format')!='PBIR-Legacy':raise ValueError('Qualified native Legacy preimage required')
    if fingerprint(definition) != expected_sha256: raise ValueError('Complete report preimage digest mismatch')
    preimage(definition.get('definition',{}), fingerprint(definition.get('definition',{})), expected_parts)
    result=copy.deepcopy(definition);parts=result['definition']['parts'];matches=[p for p in parts if p['path']=='report.json']
    if not any(p['path']=='definition.pbir' for p in parts):raise ValueError('Existing model binding part required')
    if len(matches)!=1:raise ValueError('Exactly one report.json required')
    reader_dependencies(model_definition,model_expected_sha256,model_expected_parts)
    binding_contract(definition,model_definition,binding_evidence,binding_sha256)
    part=matches[0];report=strict_json_loads(base64.b64decode(part['payload'],validate=True))
    if any(s['name']==PAGE_ID or s['displayName']==PAGE_LABEL for s in report['sections']):raise ValueError('ARC page exists;reconcile instead of duplicating')
    if any(not isinstance(s.get('name'),str) or not s['name'] or s['name']!=s['name'].strip() or type(s.get('ordinal')) is not int or s['ordinal']<0 for s in report['sections']):raise ValueError('Exact section identities and ordinal integers required')
    if len({s['name'] for s in report['sections']})!=len(report['sections']):raise ValueError('Duplicate section identity')
    if len(report['sections'])!=8:raise ValueError('Expected accepted eight-page baseline')
    visuals,_=page_visuals();report['sections'].append({'name':PAGE_ID,'displayName':PAGE_LABEL,'ordinal':max(s.get('ordinal',0) for s in report['sections'])+1,'displayOption':1,'width':1920,'height':1080,'filters':'[]','config':'{}','visualContainers':visuals})
    part['payload']=base64.b64encode(json.dumps(report,ensure_ascii=False).encode()).decode();return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--definition',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--expected-sha256',required=True)
    p.add_argument('--expected-parts',type=Path,required=True)
    p.add_argument('--model-definition',type=Path,required=True)
    p.add_argument('--model-expected-sha256',required=True)
    p.add_argument('--model-expected-parts',type=Path,required=True)
    p.add_argument('--binding-evidence',type=Path,required=True)
    p.add_argument('--binding-sha256',required=True)
    a=p.parse_args()
    inputs=[a.definition,a.expected_parts,a.model_definition,a.model_expected_parts,a.binding_evidence]
    if __package__:
        from scripts.plan_publication_stub_restore import private_output
    else:
        from plan_publication_stub_restore import private_output
    private_output(a.output,inputs)
    d=prepare(strict_json_loads(a.definition.read_bytes()),expected_sha256=a.expected_sha256,
              expected_parts=strict_json_loads(a.expected_parts.read_bytes()),
              model_definition=strict_json_loads(a.model_definition.read_bytes()),
              model_expected_sha256=a.model_expected_sha256,
              model_expected_parts=strict_json_loads(a.model_expected_parts.read_bytes()),
              binding_evidence=strict_json_loads(a.binding_evidence.read_bytes()),binding_sha256=a.binding_sha256)
    write_new(a.output,d,inputs)
    print('Prepared one source-context page; native save/render/readback remain unqualified')
if __name__=='__main__':main()
