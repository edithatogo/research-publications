"""Prepare an immutable, reversible local reader candidate from an exact PBIR export.

No API calls, native writes, publication, or fabricated model objects. The manifest
records the complete input/output file set; native preview is a separate gate.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def literal(value):
    return {'expr': {'Literal': {'Value': value}}}


def projection_labels(document):
    result=copy.deepcopy(document)
    changes=0
    for role in result.get('visual',{}).get('query',{}).get('queryState',{}).values():
        for projection in role.get('projections',[]):
            if projection.get('nativeQueryRef'):
                continue
            field=projection.get('field',{})
            # Only direct fields have a mechanically supported label mapping.
            if len(field)!=1 or not set(field) <= {'Column','Measure'}:
                raise ValueError('Unresolved projection: do not infer aggregate labels')
            binding=next(iter(field.values()))
            property_name=binding.get('Property')
            entity=binding.get('Expression',{}).get('SourceRef',{}).get('Entity')
            if not entity or not property_name or projection.get('queryRef') != entity+'.'+property_name:
                raise ValueError('Projection reference is not an exact direct-field binding')
            projection['nativeQueryRef']=property_name
            changes+=1
    return result,changes


def prepare(source, destination, expected_definition_sha, reader_controls=False):
    if Path(source).is_symlink():
        raise ValueError("Symbolic source is not accepted")
    source=Path(source).resolve();destination=Path(destination).resolve()
    receipt=destination.with_name(destination.name+".manifest.json")
    if receipt.exists():
        raise ValueError("Manifest path already exists")
    if destination.exists() or destination == source or source in destination.parents:
        raise ValueError('Use a new output directory outside the source')
    if source.is_symlink() or any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('Symbolic links are not accepted in native baseline')
    files={str(p.relative_to(source)):p.read_bytes() for p in source.rglob('*') if p.is_file()}
    if 'definition/report.json' not in files or 'definition/pages/pages.json' not in files:
        raise ValueError('Complete PBIR definition required')
    if sha(files['definition/report.json']) != expected_definition_sha:
        raise ValueError('Exact report definition hash mismatch')
    updates={}; labels=0
    for path, content in files.items():
        if path.endswith('/visual.json'):
            original=json.loads(content);new,count=projection_labels(original);labels+=count
            if reader_controls and path=='definition/pages/ReportSection3/visuals/year-filter/visual.json':
                visual=new['visual']
                projections=visual['query']['queryState']['Values']['projections']
                if len(projections)!=1 or projections[0]['queryRef']!='Publication.PublicationYear':
                    raise ValueError('Year slicer binding drift')
                props=visual['objects']['data'][0]['properties']
                if props.get('mode') != literal("'Dropdown'"):
                    raise ValueError('Year slicer preimage drift')
                props['mode']=literal("'Between'")
                # Reserve original footprint: final sizing/native behavior gate remains open.
            if reader_controls and path=='definition/pages/ReportSection3/visuals/annual-trajectory/visual.json':
                if new['visual']['visualType']!='lineChart':raise ValueError('Trajectory type drift')
                styles=new['visual'].setdefault('objects',{}).setdefault('lineStyles',[])
                defaults=[style for style in styles if 'selector' not in style]
                if len(defaults)>1:
                    raise ValueError('Ambiguous default line style')
                if not defaults:
                    defaults=[{'properties':{}}];styles.append(defaults[0])
                defaults[0].setdefault('properties',{})['lineChartType']=literal("'linear'")
            if new != original:updates[path]=json.dumps(new,indent=2).encode()+b'\n'
        if reader_controls and path=='definition/pages/ReportSection4/page.json':
            doc=json.loads(content)
            if doc.get('displayName')!='Clinical Analytics':raise ValueError('Profile page preimage drift')
            doc['displayName']='Research Profile & Open Access'
            updates[path]=json.dumps(doc,indent=2).encode()+b'\n'
    # Validate everything before creating any output.
    destination.mkdir(parents=True,exist_ok=False)
    for name,content in files.items():
        p=destination/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(updates.get(name,content))
    manifest={'schema_version':1,'status':'LOCAL_CANDIDATE_NOT_RENDERED_OR_DEPLOYED',
              'native_writes':0,'projection_labels_added':labels,'reader_controls':reader_controls,
              'input':{k:sha(v) for k,v in sorted(files.items())},
              'output':{k:sha(updates.get(k,v)) for k,v in sorted(files.items())},
              'changed_files':sorted(updates),
              'recovery':'Revert only changed files to exact source bytes after output-hash comparison; preserve source directory',
              'open_gates':['Fresh native baseline','Numeric year type/native range behavior','Slicer sizing','All-page preview for label normalization','Full source portability','Native save and inverse']}
    receipt=destination.with_name(destination.name+'.manifest.json')
    if receipt.exists():
        raise ValueError('Manifest path already exists; output retained for inspection')
    receipt.write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--expected-definition-sha256',required=True)
    parser.add_argument('--reader-controls',action='store_true')
    args=parser.parse_args()
    result=prepare(args.source,args.output,args.expected_definition_sha256,args.reader_controls)
    print(json.dumps({k:result[k] for k in ('status','projection_labels_added','changed_files')}))

if __name__=='__main__':main()
