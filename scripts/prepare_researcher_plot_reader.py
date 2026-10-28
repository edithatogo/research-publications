"""Prepare plot-first author-label evidence against explicit semantic measures.

This does not deploy the measures or claim preview qualification.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import copy
import json
import shutil
from pathlib import Path
try:
    from .prepare_activity_plot_reader import heading, text_bool, text_number
    from .prepare_publication_outcome_reader import fingerprint, read, write, text
    from .prepare_reconciliation_plot_reader import field
except ImportError:
    from prepare_activity_plot_reader import heading, text_bool, text_number
    from prepare_publication_outcome_reader import fingerprint, read, write, text
    from prepare_reconciliation_plot_reader import field

MAIN='ResearcherEvidence'
DETAIL='ResearcherLabelEvidence'
TABLE='ResearcherPublicationMentions'


def projection(prop: str, *, measure: bool=False) -> dict:
    expr={'Measure' if measure else 'Column':{'Expression':{'SourceRef':{'Entity':TABLE}},'Property':prop}}
    return {'field':expr,'queryRef':TABLE+'.'+prop,'nativeQueryRef':prop,'displayName':prop}


def caption(doc: dict, value: str) -> None:
    vco=doc['visual'].setdefault('visualContainerObjects',{})
    vco['title']=[{'properties':{'show':text_bool(True),'text':text(value)}}]
    vco.setdefault('general',[{'properties':{}}])[0]['properties']['altText']=text(value)


def prepare(source: Path, output: Path, expected: str) -> dict:
    if (source/'.pbi').exists() or fingerprint(source)!=expected:
        raise ValueError('Clean exact preimage required')
    if output.exists() or output.resolve().is_relative_to(source.resolve()):
        raise ValueError('New output outside source required')
    pages=source/'definition/pages';originals={f.parent.name:read(f) for f in (pages/MAIN/'visuals').glob('*/visual.json')}
    expected_types={'researcher-heading':'textbox','researcher-guidance':'textbox','researcher-footer':'textbox','researcher-label':'slicer','researcher-year':'slicer','researcher-source':'slicer','researcher-groups':'tableEx','researcher-publications':'tableEx'}
    if {n:v['visual']['visualType'] for n,v in originals.items()}!=expected_types or (pages/DETAIL).exists():
        raise ValueError('Researcher inventory drift')
    required=['Author-label mentions','Author-label groups','Retained publications with author-label evidence','Canonical publications without retained author labels','First-listed publications by author label','Last-listed publications by author label']
    spec=json.loads((Path(__file__).resolve().parents[1]/'config/researcher-evidence-measures.json').read_text())
    if not set(required)<=set(m['name'] for m in spec['measures']) or spec['table']!=TABLE:
        raise ValueError('Reviewed semantic contract missing')
    shutil.copytree(source,output);dest=output/'definition/pages'
    for name,pos in {'researcher-groups':(32,224,600,640),'researcher-publications':(648,224,1240,640),'researcher-guidance':(32,112,1856,96),'researcher-footer':(32,880,1856,168)}.items():
        doc=copy.deepcopy(originals[name]);doc['position'].update(zip(('x','y','width','height'),pos));write(dest/DETAIL/'visuals'/name/'visual.json',doc);shutil.rmtree(dest/MAIN/'visuals'/name)
    title=copy.deepcopy(originals['researcher-heading']);title['position'].update(x=32,y=32,width=1360,height=56);heading(title,'Author-label evidence — labels are not resolved people');write(dest/MAIN/'visuals/researcher-heading/visual.json',title)
    detail_title=copy.deepcopy(title);detail_title['name']='e04-researcher-detail-heading';heading(detail_title,'Retained author-label and publication evidence');write(dest/DETAIL/'visuals'/detail_title['name']/'visual.json',detail_title)
    template=read(pages/'ARCAwardContextReader/visuals/arc-code/visual.json')['visual']
    for name,pos,columns in [('researcher-source',(32,112,608,112),3),('researcher-year',(656,112,1232,112),8),('researcher-label',(32,240,1856,208),3)]:
        doc=copy.deepcopy(originals[name]);doc['position'].update(zip(('x','y','width','height'),pos));v=doc['visual'];v['visualType']='advancedSlicerVisual';v['objects']=copy.deepcopy(template['objects']);v['objects']['layout'][0]['properties']['columnCount']=text_number(columns)
        if name!='researcher-label':
            v['objects'].pop('general',None);v['objects'].pop('search',None)
        else:
            v.setdefault('visualContainerObjects',{})['padding']=copy.deepcopy(template['visualContainerObjects']['padding'])
        write(dest/MAIN/'visuals'/name/'visual.json',doc)
    card=read(pages/'DoraActivityCounts/visuals/activity-total/visual.json')
    for i,metric in enumerate(required[:4]):
        doc=copy.deepcopy(card);doc['name']='e04-researcher-card-'+str(i);doc['position'].update(x=32+464*i,y=464,width=448,height=112,z=800+i,tabOrder=8000+i);doc['visual']['query']={'queryState':{'Data':{'projections':[projection(metric,measure=True)]}}};caption(doc,metric);write(dest/MAIN/'visuals'/doc['name']/'visual.json',doc)
    chart=read(pages/'DoraActivityCounts/visuals/activity-years/visual.json')
    for name,category,metrics,pos,label in [('e04-researcher-source-plot','SourceSet',[required[0]],(32,592,912,456),'Retained author-label mentions by source set'),('e04-researcher-year-plot','PublicationYear',[required[2],required[4],required[5]],(960,592,928,456),'Publication evidence by year — first/last overlap; do not add')]:
        doc=copy.deepcopy(chart);doc['name']=name;doc['position'].update(zip(('x','y','width','height'),pos));doc['position'].update(z=900,tabOrder=9000);doc['visual']['query']={'queryState':{'Category':{'projections':[projection(category)]},'Y':{'projections':[projection(m,measure=True) for m in metrics]}}};caption(doc,label);doc['visual']['objects']['legend']=[{'properties':{'show':text_bool(len(metrics)>1)}}];write(dest/MAIN/'visuals'/name/'visual.json',doc)
    detail=read(pages/'DoraActivityEvidence/page.json');detail.update(name=DETAIL,displayName='Author-label evidence detail');year=field(TABLE,'PublicationYear');detail['pageBinding']={'name':'E04ResearcherEvidence','type':'Drillthrough','acceptsFilterContext':'Default','parameters':[{'name':'EvidenceYear','boundFilter':'e04-researcher-year-filter','asAggregation':False,'fieldExpr':year}]};detail['filterConfig']={'filters':[{'name':'e04-researcher-year-filter','type':'Categorical','howCreated':'Drillthrough','field':year}]};write(dest/DETAIL/'page.json',detail)
    drill=read(pages/'DoraActivityCounts/visuals/e04-activity-drill/visual.json');drill['name']='e04-researcher-drill';drill['visual']['visualContainerObjects']['visualLink'][0]['properties']['drillthroughSection']=text(DETAIL)
    for entry in drill['visual']['objects']['text']:
        state=entry.get('selector',{}).get('id')
        if state in ('default','disabled'):entry['properties']['text']=text('Author-label evidence' if state=='default' else 'Select a year bar first')
    drill['visual']['visualContainerObjects']['general'][0]['properties']['altText']=text('Drill through selected year to retained author-label evidence');write(dest/MAIN/'visuals'/drill['name']/'visual.json',drill)
    back=read(pages/'DoraActivityEvidence/visuals/e04-activity-back/visual.json');back['name']='e04-researcher-back';back['visual']['objects']['text'][1]['properties']['text']=text('Back to author-label plots');back['visual']['visualContainerObjects']['general'][0]['properties']['altText']=text('Back to author-label plots');write(dest/DETAIL/'visuals'/back['name']/'visual.json',back)
    metadata=read(dest/'pages.json');metadata['pageOrder'].insert(metadata['pageOrder'].index(MAIN)+1,DETAIL);write(dest/'pages.json',metadata)
    for f in source.rglob('*'):
        if not f.is_file():continue
        rel=f.relative_to(source)
        if rel==Path('definition/pages/pages.json') or rel.is_relative_to(Path('definition/pages')/MAIN):continue
        if f.read_bytes()!=(output/rel).read_bytes():raise ValueError('Unrelated part changed')
    for name in ('researcher-groups','researcher-publications'):
        if read(dest/DETAIL/'visuals'/name/'visual.json')['visual']['query']!=originals[name]['visual']['query']:
            raise ValueError('Evidence table query changed')
    for name in ('researcher-label','researcher-year','researcher-source'):
        if read(dest/MAIN/'visuals'/name/'visual.json')['visual']['query']!=originals[name]['visual']['query']:
            raise ValueError('Filter query changed')
    if fingerprint(source)!=expected:raise ValueError('Source drift')
    return {'sourceSHA256':expected,'candidateSHA256':fingerprint(output),'requiredNativeMeasures':required,'nativeMeasureAdoptionRequired':True,'modelWrite':False,'nativeSaveSubmitted':False,'previewQualified':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--expected-sha256',required=True);a=p.parse_args();print(json.dumps(prepare(a.source,a.output,a.expected_sha256),indent=2))
