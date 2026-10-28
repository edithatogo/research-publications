"""Prepare two additive year-context measures from a complete native definition.

Local preparation only. Query-scoped DAX qualification is separate from a saved
model write. The complete source envelope is the exact rollback artifact.
SPDX-License-Identifier: Apache-2.0
"""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path

UNKNOWN_YEAR='CALCULATE([Publications], REMOVEFILTERS(Publication[PublicationYear]), ISBLANK(Publication[PublicationYear]))'
YEAR_CONTEXT='VAR _Min = MIN(Publication[PublicationYear]) VAR _Max = MAX(Publication[PublicationYear]) RETURN IF(ISBLANK(_Min), "No known-year publications in selection", FORMAT(_Min,"0") & " to " & FORMAT(_Max,"0"))'
MEASURES={
 'Dashboard publications without known year':(UNKNOWN_YEAR,'#,0','Unknown-year publication count independent of the year-range filter; other source/facility scope remains.'),
 'Dashboard selected year context':(YEAR_CONTEXT,'@','Observed minimum/maximum publication year in the current selection; this is not acquisition-coverage assurance.'),
}


def prepare_metrics(definition):
    result=copy.deepcopy(definition)
    d=result.get('definition',{})
    parts=d.get('parts',[])
    if d.get('format')!='TMDL' or len({p['path'] for p in parts})!=len(parts):
        raise ValueError('Complete, unique TMDL parts required')
    required={'definition/model.tmdl','definition/tables/Publication.tmdl'}
    if not required <= {p['path'] for p in parts}:raise ValueError('Native Publication model required')
    part=next(p for p in parts if p['path']=='definition/tables/Publication.tmdl')
    text=base64.b64decode(part['payload'],validate=True).decode('utf-8')
    if not text.startswith('table Publication\n') or '\n\tmeasure Publications =' not in text:
        raise ValueError('Publication table/measure preimage drift')
    additions=[]
    for name,(dax,fmt,description) in MEASURES.items():
        if name in text:raise ValueError('Candidate measure already exists; reconcile rather than duplicate')
        additions.append(f"\t/// {description}\n\tmeasure '{name}' = {dax}\n\t\tformatString: {fmt}\n\t\tdisplayFolder: Dashboard context\n")
    index=text.index('\n\tmeasure Publications =')
    text=text[:index]+'\n\n'+'\n'.join(additions)+text[index:]
    part['payload']=base64.b64encode(text.encode()).decode()
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--definition',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--expected-sha256',required=True)
    args=parser.parse_args()
    raw=args.definition.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=args.expected_sha256:raise ValueError('Complete definition hash drift')
    if args.output.exists():raise ValueError('Output already exists')
    receipt=args.output.with_suffix(args.output.suffix+'.manifest.json')
    if receipt.exists():raise ValueError('Manifest already exists')
    candidate=prepare_metrics(json.loads(raw))
    args.output.write_text(json.dumps(candidate,indent=2)+'\n')
    receipt.write_text(json.dumps(dict(status='LOCAL_ADDITIVE_CANDIDATE',native_writes=0,
        source_sha256=args.expected_sha256,output_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
        changed_parts=['definition/tables/Publication.tmdl'],measures=list(MEASURES),
        open_gates=['Fresh isolated target ownership and full preimage','Native saved authoring/readback',
                    'Bounded inverse and exact canonical-key reconciliation','Concurrent report editor handoff']),indent=2)+'\n')

if __name__=='__main__':main()
