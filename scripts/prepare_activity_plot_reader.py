"""Prepare FHD activity plots and retain complete disease-filtered evidence.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import shutil
try:
    from .prepare_publication_outcome_reader import fingerprint, read, write, text
    from .prepare_reconciliation_plot_reader import field
except ImportError:
    from prepare_publication_outcome_reader import fingerprint, read, write, text
    from prepare_reconciliation_plot_reader import field

MAIN='DoraActivityCounts'
DETAIL='DoraActivityEvidence'


def heading(doc, value):
    first=True
    for paragraph in doc['visual']['objects']['general'][0]['properties']['paragraphs']:
        for run in paragraph.get('textRuns',[]):
            run['value']=value if first else '';first=False
    doc['visual'].setdefault('visualContainerObjects',{}).setdefault('general',[{'properties':{}}])[0]['properties']['altText']=text(value)


def prepare(source: Path, output: Path, expected: str, *, modern_year: bool = False) -> dict:
    if (source/'.pbi').exists() or fingerprint(source)!=expected:
        raise ValueError('Clean exact preimage required')
    if output.exists() or output.resolve().is_relative_to(source.resolve()):
        raise ValueError('New candidate outside source required')
    pages=source/'definition/pages';page=read(pages/MAIN/'page.json')
    if (page['width'],page['height'])!=(1920,1488) or (pages/DETAIL).exists():
        raise ValueError('Expected retained activity preimage required')
    originals={f.parent.name:read(f) for f in (pages/MAIN/'visuals').glob('*/visual.json')}
    expected_types={'heading':'textbox','activity-guidance':'textbox','activity-footer':'textbox',
        'activity-total':'cardVisual','activity-site':'slicer','activity-disease':'slicer',
        'activity-year':'slicer','activity-date-status':'slicer','activity-years':'clusteredColumnChart',
        'overview-sites':'barChart','overview-diseases':'barChart','activity-groups':'tableEx'}
    if {n:d['visual']['visualType'] for n,d in originals.items()}!=expected_types:
        raise ValueError('Activity visual inventory drift')
    disease=originals['overview-diseases']['visual']['query']['queryState']['Category']['projections'][0]['field']
    if disease!=field('DoraActivityCounts','DiseaseCategory'):
        raise ValueError('Disease identity binding drift')
    shutil.copytree(source,output);dest=output/'definition/pages'
    page['height']=1080;write(dest/MAIN/'page.json',page)
    layouts={
        'heading':(32,32,1360,56),
        'activity-total':(32,112,280,112),
        'activity-site':(328,112,480,112),
        'activity-disease':(824,112,480,112),
        'activity-year':(1320,112,272,112),
        'activity-date-status':(1608,112,280,112),
        'activity-years':(32,240,1856,304),
        'overview-sites':(32,560,912,424),
        'overview-diseases':(960,560,928,424)}
    if modern_year:
        layouts.update({
            'activity-year':(328,112,1560,112),
            'activity-site':(32,240,608,112),
            'activity-disease':(656,240,608,112),
            'activity-date-status':(1280,240,608,112),
            'activity-years':(32,368,1856,224),
            'overview-sites':(32,608,912,400),
            'overview-diseases':(960,608,928,400)})
    for name,pos in layouts.items():
        doc=copy.deepcopy(originals[name]);doc['position'].update(zip(('x','y','width','height'),pos))
        if name=='heading':heading(doc,'Retained DoRA activities — all source sites')
        if name=='activity-year' and modern_year:
            doc['visual']['visualType']='advancedSlicerVisual'
            doc['visual']['objects']={
                'layout':[{'properties':{
                    'rowCount':text_number(1), 'columnCount':text_number(8),
                    'cellPadding':text_number(8), 'autoGrid':text_bool(True)}}],
                'selection':[{'properties':{
                    'singleSelect':text_bool(False), 'strictSingleSelect':text_bool(False)}}],
                'value':[{'selector':{'id':'default'},'properties':{'showBlankAs':text('Unknown')}}],
                'shapeCustomRectangle':[{'selector':{'id':'default'},'properties':{'tileShape':text('pill')}}]}
        write(dest/MAIN/'visuals'/name/'visual.json',doc)
    detail_positions={'activity-guidance':(32,112,1856,96),
                      'activity-groups':(32,224,1856,640),
                      'activity-footer':(32,880,1856,168)}
    for name,pos in detail_positions.items():
        doc=copy.deepcopy(originals[name]);doc['position'].update(zip(('x','y','width','height'),pos))
        if name=='activity-guidance':
            heading(doc,'The selected disease and site/year/date filters come from the activity page. Use Back to change them. Counts represent retained source activity keys, not institutional outcomes.')
        write(dest/DETAIL/'visuals'/name/'visual.json',doc);shutil.rmtree(dest/MAIN/'visuals'/name)
    title=copy.deepcopy(originals['heading']);title['name']='e04-activity-evidence-heading'
    title['position'].update(x=32,y=32,width=1360,height=56)
    heading(title,'Retained DoRA activity evidence')
    write(dest/DETAIL/'visuals'/title['name']/'visual.json',title)
    back=read(pages/'SourceReconciliationEvidence/visuals/e04-reconciliation-back/visual.json')
    back['name']='e04-activity-back'
    back['visual']['objects']['text'][1]['properties']['text']=text('Back to activity plots')
    back['visual']['visualContainerObjects']['general'][0]['properties']['altText']=text('Back to activity plots')
    write(dest/DETAIL/'visuals'/back['name']/'visual.json',back)
    drill=read(pages/'ReportSection/visuals/e04-source-evidence/visual.json');drill['name']='e04-activity-drill'
    for entry in drill['visual']['objects']['text']:
        state=entry.get('selector',{}).get('id')
        if state in ('default','disabled'):
            entry['properties']['text']=text('Disease evidence' if state=='default' else 'Select a disease bar first')
    drill['visual']['visualContainerObjects']['visualLink'][0]['properties']['drillthroughSection']=text(DETAIL)
    drill['visual']['visualContainerObjects']['general'][0]['properties']['altText']=text('Drill through selected disease to retained activity evidence')
    write(dest/MAIN/'visuals'/drill['name']/'visual.json',drill)
    detail=read(pages/'SourceReconciliationEvidence/page.json')
    detail.update(name=DETAIL,displayName='Activity source evidence')
    detail['pageBinding']={'name':'E04ActivityEvidence','type':'Drillthrough','acceptsFilterContext':'Default',
        'parameters':[{'name':'ActivityDisease','boundFilter':'e04-activity-disease-filter',
                       'asAggregation':False,'fieldExpr':disease}]}
    detail['filterConfig']={'filters':[{'name':'e04-activity-disease-filter','type':'Categorical',
                                      'howCreated':'Drillthrough','field':disease}]}
    write(dest/DETAIL/'page.json',detail)
    metadata=read(dest/'pages.json');metadata['pageOrder'].insert(metadata['pageOrder'].index(MAIN)+1,DETAIL)
    write(dest/'pages.json',metadata)
    for name, original in originals.items():
        owner = DETAIL if name in detail_positions else MAIN
        candidate = read(dest/owner/'visuals'/name/'visual.json')
        intended_type = 'advancedSlicerVisual' if modern_year and name == 'activity-year' else original['visual']['visualType']
        if candidate['name'] != original['name'] or candidate['visual']['visualType'] != intended_type:
            raise ValueError('Existing activity visual identity changed: '+name)
        for key in ('query', 'filterConfig'):
            if candidate['visual'].get(key) != original['visual'].get(key) or candidate.get(key) != original.get(key):
                raise ValueError('Activity binding/filter changed: '+name)
    for original in source.rglob('*'):
        if not original.is_file():
            continue
        relative = original.relative_to(source)
        if relative == Path('definition/pages/pages.json') or relative.is_relative_to(Path('definition/pages')/MAIN):
            continue
        if (output/relative).read_bytes() != original.read_bytes():
            raise ValueError('Unrelated report part changed: '+str(relative))
    if fingerprint(source) != expected:
        raise ValueError('Source changed during preparation')
    for f in (dest/MAIN/'visuals').glob('*/visual.json'):
        d=read(f)
        if d['visual']['visualType'] in ('tableEx','pivotTable'):
            raise ValueError('Primary activity table remains')
        for key in ('x','y','width','height'):
            if d['position'][key]%8:raise ValueError('Activity grid drift')
    return {'sourceSHA256':expected,'candidateSHA256':fingerprint(output),
            'affectedPages':[MAIN,DETAIL],'primaryCanvas':[1920,1080],
            'existingQueriesAndFiltersPreserved':True,'retainedEvidenceTables':1,
            'sourceGrain':'Existing retained activity aggregate; no new model calculation or admission',
            'modernYearSelector':modern_year,
            'nativeSaveSubmitted':False}


def text_number(value: int) -> dict:
    return {'expr': {'Literal': {'Value': str(value)+'D'}}}


def text_bool(value: bool) -> dict:
    return {'expr': {'Literal': {'Value': 'true' if value else 'false'}}}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--expected-sha256',required=True)
    p.add_argument('--modern-year',action='store_true');a=p.parse_args()
    print(json.dumps(prepare(a.source,a.output,a.expected_sha256,modern_year=a.modern_year),indent=2))
