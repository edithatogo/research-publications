"""Prepare a complete local overview layout; never connect to a service.

The full baseline digest guards concurrent edits. The candidate preserves all
pages, visual identities, queries and filters; native preview/save is separate.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
from scripts.prepare_dashboard_reader_increment import literal, prepare, sha

OVERVIEW='definition/pages/ReportSection3/'
LAYOUT={
 'heading':(24,16,1232,48), 'caption':(24,64,1232,48),
 'all-papers':(24,128,296,80),'pubmed':(336,128,296,80),
 'dora':(648,128,296,80),'overlap':(960,128,296,80),
 'year-filter':(24,224,376,144),'facility-filter':(416,224,256,144),
 'source-filter':(688,224,256,144),'review-filter':(960,224,296,144),
 'annual-trajectory':(24,384,608,144),'facility-breakdown':(648,384,608,144),
 'attribution-breakdown':(24,544,608,160),'provenance-breakdown':(648,544,608,160),
 'footer':(24,720,1232,56),
}


def bundle_digest(source):
    root=Path(source)
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Symbolic baseline refused')
    digest=hashlib.sha256()
    for path in sorted(p for p in root.rglob('*') if p.is_file()):
        name=path.relative_to(root).as_posix().encode();data=path.read_bytes()
        digest.update(name+b'\0'+len(data).to_bytes(8,'big')+data)
    return digest.hexdigest()


def property_value(container,object_name,property_name,value):
    entries=container.setdefault(object_name,[])
    defaults=[e for e in entries if 'selector' not in e]
    if len(defaults)>1:raise ValueError('Ambiguous default formatting')
    if not defaults:
        defaults=[{'properties':{}}];entries.append(defaults[0])
    defaults[0].setdefault('properties',{})[property_name]=literal(value)


def layout_documents(source):
    root=Path(source);page=json.loads((root/OVERVIEW/'page.json').read_text())
    actual={p.parent.name for p in (root/OVERVIEW/'visuals').glob('*/visual.json')}
    if actual!=set(LAYOUT):raise ValueError('Overview visual inventory drift')
    docs={};page['width']=1280;page['height']=800
    docs[OVERVIEW+'page.json']=page
    for name,(x,y,width,height) in LAYOUT.items():
        path=OVERVIEW+'visuals/'+name+'/visual.json'
        doc=json.loads((root/path).read_text());v=doc['visual']
        doc['position'].update(x=x,y=y,width=width,height=height)
        vco=v.setdefault('visualContainerObjects',{})
        if v['visualType']=='textbox':
            for side in ('top','bottom','left','right'):
                property_value(vco,'padding',side,'0D')
            size='28px' if name=='heading' else '18px'
            for block in v['objects']['general']:
                for paragraph in block['properties'].get('paragraphs',[]):
                    for run in paragraph.get('textRuns',[]):
                        run.setdefault('textStyle',{})['fontSize']=size
        else:
            property_value(vco,'title','fontSize','20D')
        if name.endswith('-filter'):
            if v['visualType']!='slicer':raise ValueError('Slicer type drift')
            objects=v.setdefault('objects',{})
            property_value(objects,'items','textSize','18D')
            for side in ('top','bottom','left','right'):
                property_value(vco,'padding',side,'8D')
            if name=='year-filter':
                projections=v['query']['queryState']['Values']['projections']
                if len(projections)!=1 or projections[0]['queryRef']!='Publication.PublicationYear':
                    raise ValueError('Year field binding drift')
                property_value(objects,'data','mode',"'Between'")
                property_value(objects,'numericInputStyle','textSize','18D')
            elif name=='source-filter':
                property_value(objects,'data','mode',"'Basic'")
        elif v['visualType']=='card':
            property_value(v.setdefault('objects',{}),'labels','fontSize','32D')
        elif name=='annual-trajectory':
            if v['visualType']!='lineChart':raise ValueError('Trend type drift')
            property_value(v.setdefault('objects',{}),'lineStyles','lineChartType',"'linear'")
        docs[path]=doc
    # No two reserved regions overlap and no region leaves the canvas.
    values=list(LAYOUT.items())
    for i,(name,(x,y,w,h)) in enumerate(values):
        if min(x,y)<0 or x+w>1280 or y+h>800:raise ValueError('Canvas overflow')
        for other,(a,b,c,d) in values[i+1:]:
            if x<a+c and a<x+w and y<b+d and b<y+h:
                raise ValueError('Overlapping reserved regions: '+name+'/'+other)
    return docs


def prepare_readable(source,destination,expected_baseline_sha256):
    source=Path(source);destination=Path(destination)
    if bundle_digest(source)!=expected_baseline_sha256:
        raise ValueError('Full baseline digest drift')
    changes=layout_documents(source)  # Validate before creating output.
    receipt=prepare(source,destination,sha((source/'definition/report.json').read_bytes()))
    # Apply the layout to normalized candidate documents, retaining label repairs.
    for name,layout in changes.items():
        path=destination/name
        candidate=json.loads(path.read_text())
        if name.endswith('visual.json'):
            normalized_query=candidate['visual'].get('query')
            candidate=copy.deepcopy(layout)
            if normalized_query is not None:candidate['visual']['query']=normalized_query
        else:candidate=layout
        path.write_text(json.dumps(candidate,indent=2)+'\n')
    receipt.update(status='LOCAL_READABLE_LAYOUT_NOT_RENDERED_OR_SAVED',
                   full_baseline_sha256=expected_baseline_sha256,
                   canvas={'width':1280,'height':800},
                   native_writes=0,other_editor_active=True,
                   open_gates=['Other editor terminal handoff','Fresh full baseline digest comparison',
                               'Native preview at 1280x720 and 1920x1080','Range endpoint/reset/unknown-year checks',
                               'Source option and no-result behavior','Native Save/readback and bounded inverse'])
    receipt['output']={p.relative_to(destination).as_posix():sha(p.read_bytes())
                       for p in sorted(destination.rglob('*')) if p.is_file()}
    receipt['changed_files']=[n for n in receipt['input'] if receipt['input'][n]!=receipt['output'][n]]
    destination.with_name(destination.name+'.manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--expected-baseline-sha256',required=True)
    args=parser.parse_args()
    result=prepare_readable(args.source,args.output,args.expected_baseline_sha256)
    print(json.dumps({k:result[k] for k in ('status','canvas','changed_files')}))

if __name__=='__main__':main()
