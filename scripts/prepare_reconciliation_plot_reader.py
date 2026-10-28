"""Prepare plot-first source reconciliation while preserving native evidence.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil

try:
    from .prepare_publication_outcome_reader import fingerprint, read, write, literal, text
except ImportError:
    from prepare_publication_outcome_reader import fingerprint, read, write, literal, text

MAIN = 'ReportSection'
DETAIL = 'SourceReconciliationEvidence'


def field(entity, name, kind='Column'):
    return {kind: {'Expression': {'SourceRef': {'Entity': entity}}, 'Property': name}}


def projection(entity, name, kind='Column'):
    return {'field': field(entity, name, kind), 'queryRef': entity+'.'+name,
            'nativeQueryRef': name}


def chart(template, name, entity, category, title, position):
    result=copy.deepcopy(template)
    result['name']=name
    result['position']=position
    for index, item in enumerate(result.get('filterConfig',{}).get('filters',[])):
        item['name']=name+'-filter-'+str(index)
    result['visual']={
        'visualType':'barChart', 'drillFilterOtherVisuals':True,
        'query':{'queryState':{
            'Category':{'projections':[projection(entity,category)]},
            'Y':{'projections':[projection('Publication','Publications','Measure')]}},
            'sortDefinition':{'sort':[{'field':field('Publication','Publications','Measure'),
                                       'direction':'Descending'}]}},
        'objects':{
            'labels':[{'properties':{'show':literal('true'),'labelPosition':text('OutsideEnd')}}],
            'valueAxis':[{'properties':{'start':literal('0D'),'show':literal('false')}}]},
        'visualContainerObjects':{
            'title':[{'properties':{'show':literal('true'),'text':text(title)}}],
            'general':[{'properties':{'altText':text(title)}}]}}
    return result


def prepare(source: Path, output: Path, expected: str) -> dict:
    if (source/'.pbi').exists() or fingerprint(source)!=expected:
        raise ValueError('Clean exact preimage required')
    if output.exists() or output.resolve().is_relative_to(source.resolve()):
        raise ValueError('New candidate outside source required')
    pages=source/'definition/pages'
    if (pages/DETAIL).exists():
        raise ValueError('Evidence page already exists; reconcile first')
    main=pages/MAIN
    originals={p.parent.name:read(p) for p in (main/'visuals').glob('*/visual.json')}
    for name in ('facility-contributions','reconciliation-register'):
        if originals[name]['visual']['visualType']!='tableEx':
            raise ValueError('Expected evidence table: '+name)
    if len(originals)!=17:
        raise ValueError('Source reconciliation inventory drift')
    modern=read(pages/'ReportSection3/visuals/all-papers/visual.json')
    back=read(pages/'PublicationVersionEvidence/visuals/t18-version-back/visual.json')
    drill=read(pages/'ReportSection3/visuals/t18-drill/visual.json')
    shutil.copytree(source,output)
    dest=output/'definition/pages'
    # Existing text explanations and complete tables remain on the evidence page.
    positions={
        'caption':{'x':32,'y':96,'width':1856,'height':64},
        'reconciliation-register':{'x':32,'y':176,'width':1856,'height':544},
        'footer':{'x':32,'y':736,'width':1856,'height':48},
        'facility-contributions':{'x':32,'y':800,'width':1856,'height':248}}
    for name, pos in positions.items():
        doc=copy.deepcopy(originals[name]);doc['position'].update(pos)
        if name=='caption':
            for paragraph in doc['visual']['objects']['general'][0]['properties']['paragraphs']:
                for run in paragraph.get('textRuns',[]):
                    run['value']='Source, year and date-precision context flows from reconciliation. Use Back to change selection. Unknown/range dates stay retained; source differences are evidence, not approved corrections.'
            doc['visual']['visualContainerObjects']['general'][0]['properties']['altText']=text('Source, year and date-precision context flows from reconciliation. Use Back to change selection. Unknown/range dates stay retained; source differences are evidence, not approved corrections.')
        if name=='facility-contributions':
            doc['visual']['visualContainerObjects']['title'][0]['properties']['text']=text(
                'PubMed search audit — independent of source-provenance selection')
            doc['visual']['visualContainerObjects']['general'][0]['properties']['altText']=text('PubMed search audit — independent of source-provenance selection')
        write(dest/DETAIL/'visuals'/name/'visual.json',doc)
        shutil.rmtree(dest/MAIN/'visuals'/name)
    heading=copy.deepcopy(originals['heading'])
    heading['position'].update(x=32,y=32,width=1360,height=56)
    write(dest/MAIN/'visuals/heading/visual.json',heading)
    for name, old in originals.items():
        if old['visual']['visualType']!='card':
            continue
        doc=copy.deepcopy(modern);doc['name']=name;doc['position']=copy.deepcopy(old['position'])
        projections=copy.deepcopy(old['visual']['query']['queryState']['Values']['projections'])
        label=old['visual']['visualContainerObjects']['title'][0]['properties']['text']['expr']['Literal']['Value'][1:-1]
        projections[0]['displayName']=label
        doc['visual']['query']['queryState']={'Data':{'projections':projections}}
        doc['visual']['visualContainerObjects']['general'][0]['properties']['altText']=text(label)
        doc['visual']['visualContainerObjects']['title'][0]['properties']['text']=text(label)
        # Preserve the measure's own format; a date must not inherit integer precision.
        doc['visual']['objects'].pop('value',None)
        if name in ('refresh-time','searches','warnings'):
            doc['position'].update(y=912,height=80)
        write(dest/MAIN/'visuals'/name/'visual.json',doc)
    overlap=copy.deepcopy(originals['source-overlap'])
    overlap['position'].update(width=600)
    write(dest/MAIN/'visuals/source-overlap/visual.json',overlap)
    for args in (
        ('dedup-method','Publication','DedupMethod','Reconciliation method',
         {'x':648,'y':224,'width':680,'height':304,'z':700,'tabOrder':9000}),
        ('e04-facility-summary','Facility','FacilityName','Publications by facility / service — overlaps allowed',
         {'x':1344,'y':224,'width':544,'height':304,'z':800,'tabOrder':8000}),
        ('e04-date-precision','Publication','PublicationDatePrecision','Publication date precision — unknowns retained',
         {'x':32,'y':672,'width':1856,'height':232,'z':900,'tabOrder':4000})):
        doc=chart(originals['dedup-method'],*args)
        write(dest/MAIN/'visuals'/doc['name']/'visual.json',doc)
    drill['name']='e04-source-evidence'
    drill['position'].update(x=1448,y=32,width=440,height=56)
    objects=drill['visual']['objects']
    for entry in objects['text']:
        if entry.get('selector',{}).get('id') in ('default','disabled'):
            entry['properties']['text']=text('Source evidence' if entry['selector']['id']=='default'
                                               else 'Select a source bar first')
    drill['visual']['visualContainerObjects']['visualLink'][0]['properties']['drillthroughSection']=text(DETAIL)
    drill['visual']['visualContainerObjects']['general'][0]['properties']['altText']=text('Drill through selected source provenance to full reconciliation evidence')
    write(dest/MAIN/'visuals'/drill['name']/'visual.json',drill)
    back['name']='e04-reconciliation-back'
    back['position'].update(x=1448,y=32,width=440,height=48)
    back['visual']['objects']['text'][1]['properties']['text']=text('Back to source reconciliation')
    back['visual']['visualContainerObjects']['general'][0]['properties']['altText']=text('Back to source reconciliation')
    write(dest/DETAIL/'visuals'/back['name']/'visual.json',back)
    evidence_heading=copy.deepcopy(heading)
    evidence_heading['name']='e04-evidence-heading'
    evidence_heading['position'].update(width=1360)
    for paragraph in evidence_heading['visual']['objects']['general'][0]['properties']['paragraphs']:
        for run in paragraph.get('textRuns',[]):
            run['value']='Source reconciliation evidence'
    evidence_heading['visual']['visualContainerObjects']['general'][0]['properties']['altText']=text('Source reconciliation evidence')
    write(dest/DETAIL/'visuals'/evidence_heading['name']/'visual.json',evidence_heading)
    page=read(pages/'PublicationOutcomeDetails/page.json')
    page.update(name=DETAIL,displayName='Source reconciliation evidence',
                visibility='HiddenInViewMode',type='Drillthrough')
    source_field=field('Publication','SourceSet')
    page['pageBinding']={'name':'E04SourceEvidence','type':'Drillthrough',
        'acceptsFilterContext':'Default','parameters':[{'name':'SourceEvidence',
        'boundFilter':'e04-source-evidence-filter','asAggregation':False,'fieldExpr':source_field}]}
    page['filterConfig']={'filters':[{'name':'e04-source-evidence-filter',
        'type':'Categorical','howCreated':'Drillthrough','field':source_field}]}
    write(dest/DETAIL/'page.json',page)
    metadata=read(dest/'pages.json');metadata['pageOrder'].insert(metadata['pageOrder'].index(MAIN)+1,DETAIL)
    write(dest/'pages.json',metadata)
    before={p.relative_to(source).as_posix():p.read_bytes() for p in source.rglob('*') if p.is_file()}
    after={p.relative_to(output).as_posix():p.read_bytes() for p in output.rglob('*') if p.is_file()}
    return {'sourceSHA256':expected,'candidateSHA256':fingerprint(output),
        'affectedPages':[MAIN,DETAIL],'changedParts':[p for p in after if before.get(p)!=after[p]],
        'removedPaths':sorted(set(before)-set(after)), 'evidenceTablesRetained':2,
        'legacyCardsConverted':7,'nativeSaveSubmitted':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--expected-sha256',required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.source,args.output,args.expected_sha256),indent=2))
