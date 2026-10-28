"""Prepare an overview layout or bounded six-page textbox clearance offline.

The full baseline digest guards concurrent edits. The candidate preserves all
pages, visual identities, queries and filters; native preview/save is separate.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
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

# Current six-page identities, separate from the historical overview redesign.
TEXTBOX_PAGES = {'ReportSection', 'ReportSection2', 'ReportSection3',
                 'ReportSection4', '8dd811a45e8c948dd69a', 'b3e90f3eba2dbe0a1c1a'}
TEXTBOX_TARGETS = {(page, name) for page in ('ReportSection', 'ReportSection2',
                   'ReportSection3', 'ReportSection4') for name in ('heading', 'caption')}
TEXTBOX_TARGETS |= {('ReportSection2', 'footer'), ('ReportSection4', 'footer')}


def textbox_clearance_documents(files):
    """Only repair ten known textbox footprints/padding; do not repair queries.

    The one-line floor is the CLI 0.5.0 conservative heuristic, not a prediction
    of wrapping, native rendering, zoom, keyboard behavior or accessibility.
    """
    order = json.loads(files['definition/pages/pages.json'])['pageOrder']
    actual_pages = {Path(p).parent.name for p in files
                    if p.startswith('definition/pages/') and p.endswith('/page.json')
                    and len(Path(p).parts) == 4}
    if len(order) != 6 or set(order) != TEXTBOX_PAGES or actual_pages != TEXTBOX_PAGES:
        raise ValueError('Expected exact current six-page inventory')
    changes = {}

    def rectangle(doc):
        position = doc['position']
        values = tuple(position[k] for k in ('x', 'y', 'width', 'height'))
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError('Non-finite or non-numeric geometry')
        if min(values[2:]) <= 0:
            raise ValueError('Non-positive geometry')
        return values

    def overlaps(a, b):
        x, y, w, h = a; left, top, width, height = b
        return x < left+width and left < x+w and y < top+height and top < y+h

    for page in sorted(TEXTBOX_PAGES):
        page_root = 'definition/pages/'+page+'/'
        canvas = json.loads(files[page_root+'page.json'])
        if any(type(canvas[k]) not in (int, float) or not math.isfinite(canvas[k])
               or canvas[k] <= 0 for k in ('width', 'height')):
            raise ValueError('Invalid canvas')
        visuals = {Path(p).parent.name: (p, json.loads(raw)) for p, raw in files.items()
                   if p.startswith(page_root+'visuals/') and p.endswith('/visual.json')
                   and len(Path(p).parts) == 6}
        for name in sorted(n for p, n in TEXTBOX_TARGETS if p == page):
            if name not in visuals:
                raise ValueError('Expected textbox identity missing: '+page+'/'+name)
            path, original = visuals[name]
            doc = copy.deepcopy(original)
            visual = doc['visual']
            if doc['name'] != name or visual['visualType'] != 'textbox':
                raise ValueError('Textbox identity/type drift')
            blocks = visual.get('objects', {}).get('general', [])
            if len(blocks) != 1 or not blocks[0].get('properties', {}).get('paragraphs'):
                raise ValueError('Ambiguous textbox content')
            sizes = [run.get('textStyle', {}).get('fontSize')
                     for paragraph in blocks[0]['properties']['paragraphs']
                     for run in paragraph.get('textRuns', [])]
            expected_size = '36px' if name == 'heading' else '22px'
            if not sizes or any(size != expected_size for size in sizes):
                raise ValueError('Textbox typography drift')
            vco = visual.setdefault('visualContainerObjects', {})
            if any('selector' in entry for entry in vco.get('padding', [])):
                raise ValueError('Selector-specific padding requires review')
            for side in ('top', 'bottom'):
                property_value(vco, 'padding', side, '0D')
            if name == 'heading':
                doc['position'].update(y=0, height=64)
            elif page == 'ReportSection2' and name == 'footer':
                doc['position']['height'] = max(doc['position']['height'], 40)
            x, y, width, height = rectangle(doc)
            if min(x, y) < 0 or x+width > canvas['width'] or y+height > canvas['height']:
                raise ValueError('Textbox canvas overflow')
            floor = max(18, math.ceil(int(expected_size[:-2])*25/16))
            if height < floor:
                raise ValueError('Textbox below conservative one-line floor')
            for other, (_, neighbor) in visuals.items():
                if other != name and overlaps(rectangle(doc), rectangle(neighbor)):
                    raise ValueError('Textbox overlaps visual: '+page+'/'+name+'/'+other)
            if doc != original:
                changes[path] = doc
    return changes


def prepare_textbox_clearance(source, destination, expected_baseline_sha256):
    """Create a source-only immutable candidate with exact untouched file bytes."""
    source = Path(source); destination = Path(destination).resolve()
    if bundle_digest(source) != expected_baseline_sha256:
        raise ValueError('Full baseline digest drift')
    receipt_path = destination.with_name(destination.name+'.manifest.json')
    if destination.exists() or receipt_path.exists() or destination == source.resolve() or source.resolve() in destination.parents:
        raise ValueError('Use a new output and manifest outside the source')
    files = {p.relative_to(source).as_posix(): p.read_bytes()
             for p in source.rglob('*') if p.is_file()}
    # Transform and fingerprint the same captured bytes, even if another writer
    # changes a file between the initial filesystem guard and capture.
    digest = hashlib.sha256()
    for name, data in sorted(files.items(), key=lambda pair: Path(pair[0])):
        digest.update(name.encode()+b'\0'+len(data).to_bytes(8, 'big')+data)
    if digest.hexdigest() != expected_baseline_sha256:
        raise ValueError('Full baseline digest drift during capture')
    changes = textbox_clearance_documents(files)  # Refuse drift before output.
    updates = {name: (json.dumps(doc, ensure_ascii=False, indent=2)+'\n').encode()
               for name, doc in changes.items()}
    destination.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        path = destination/name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(updates.get(name, content))
    receipt = {'status': 'LOCAL_TEXTBOX_CLEARANCE_NOT_RENDERED_OR_SAVED',
               'native_writes': 0, 'full_baseline_sha256': expected_baseline_sha256,
               'input': {k: sha(v) for k, v in sorted(files.items())},
               'output': {k: sha(updates.get(k, v)) for k, v in sorted(files.items())},
               'changed_files': sorted(updates),
               'allowed_changes': ['Target textbox position.y/height', 'Target textbox default padding.top/bottom'],
               'recovery': 'Restore exact input bytes only after output-hash and sole-writer checks; native import recovery is unqualified',
               'open_gates': ['Exact-version schema/export-import compatibility and bounded recovery',
                              'Fresh native scope/preimage and saved definition readback',
                              'Actual all-page light/dark and viewport/zoom/wrapping inspection',
                              'Keyboard/focus/long-label and reader accessibility acceptance']}
    receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


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
    parser.add_argument('--textbox-clearance', action='store_true',
                        help='Only the ten known current six-page textbox clearances; no overview redesign or label repair')
    args=parser.parse_args()
    builder = prepare_textbox_clearance if args.textbox_clearance else prepare_readable
    result=builder(args.source,args.output,args.expected_baseline_sha256)
    print(json.dumps({k:result[k] for k in ('status','canvas','changed_files') if k in result}))

if __name__=='__main__':main()
