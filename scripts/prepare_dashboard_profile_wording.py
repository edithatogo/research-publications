"""Prepare source-specific profile wording against an immutable PBIR baseline.

No native operations. Existing measures/bindings and other pages are preserved.
SPDX-License-Identifier: Apache-2.0
"""
import copy
import json
from pathlib import Path
from scripts.prepare_dashboard_readable_layout import bundle_digest, property_value
from scripts.prepare_dashboard_reader_increment import prepare, sha

TITLES={
 'Open access compliance rate':'Known open share among assessed',
 'Open access publications':'Known open publications',
 'Clinical trial linked papers':'PubMed trial-type publications',
 'Grant-funded publications':'Reviewed publication–funding links',
 'Publications by clinical directorate and specialty':'Retained facility / service attribution',
 'ANZSRC 2020 Field of Research (FoR) division':'Retained provider research field',
 'Open access distribution (Gold / Green / Hybrid / Closed)':'Retained OA status (blank = unknown)',
 'Evidence hierarchy and study designs':'Retained publication-type groupings',
}
CAPTION='Source-supported publication characteristics. Open-access share uses assessed publications; missing evidence is unknown. Trial-type papers and reviewed funding links are distinct relationships.'
FOOTER='Research-field labels retain their provider meaning; no ANZSRC crosswalk is asserted. Open access reflects dated provider evidence, not policy compliance. Retained facility matches do not establish specific-service attribution.'


def prepare_profile(source,output,expected_sha):
    source=Path(source);output=Path(output)
    if bundle_digest(source)!=expected_sha:raise ValueError('Complete report baseline drift')
    root=source/'definition/pages/ReportSection4';changes={};found=set()
    page=json.loads((root/'page.json').read_text())
    if page['displayName'] not in ('Clinical Analytics','Research Profile & Open Access'):
        raise ValueError('Profile label drift')
    page['displayName']='Research Profile & Open Access'
    changes['definition/pages/ReportSection4/page.json']=page
    for path in root.glob('visuals/*/visual.json'):
        document=json.loads(path.read_text());original=copy.deepcopy(document);visual=document['visual']
        if visual['visualType']=='textbox':
            runs=[run for block in visual.get('objects',{}).get('general',[])
                  for paragraph in block['properties'].get('paragraphs',[]) for run in paragraph.get('textRuns',[])]
            text=''.join(run.get('value','') for run in runs)
            replacement=None
            if text.endswith('Clinical Analytics') and text.startswith('CHHHS Research Dashboard'):
                replacement=text[:-len('Clinical Analytics')]+'Research Profile & Open Access';found.add('heading')
            elif text.startswith('Clinical directorate specialty mapping,'):
                replacement=CAPTION;found.add('caption')
            elif text.startswith('Field of Research mapped using ANZSRC'):
                replacement=FOOTER;found.add('footer')
            if replacement is not None:
                if len(runs)!=1:raise ValueError('Rich profile text drift; preserve runs for review')
                runs[0]['value']=replacement
        for title in visual.get('visualContainerObjects',{}).get('title',[]):
            value=title['properties'].get('text',{}).get('expr',{}).get('Literal',{}).get('Value','')
            label=value[1:-1] if value.startswith("'") and value.endswith("'") else ''
            if label in TITLES:
                if label in found:raise ValueError('Duplicate profile visual title')
                found.add(label);property_value(visual['visualContainerObjects'],'title','text',"'"+TITLES[label]+"'")
        if document!=original:changes[path.relative_to(source).as_posix()]=document
    if found!=set(TITLES)|{'heading','caption','footer'}:raise ValueError('Incomplete profile wording preimage')
    receipt=prepare(source,output,sha((source/'definition/report.json').read_bytes()))
    for name,document in changes.items():
        path=output/name;normalized=json.loads(path.read_text())
        if name.endswith('visual.json') and 'query' in normalized['visual']:
            document['visual']['query']=normalized['visual']['query']
        path.write_text(json.dumps(document,indent=2)+'\n')
    receipt.update(status='LOCAL_PROFILE_WORDING_NOT_SAVED',full_baseline_sha256=expected_sha,
                   native_writes=0,wording_changes=list(TITLES.values()),
                   open_gates=['Concurrent editor terminal handoff','Fresh source/measure drift check',
                               'Profile rendering and denominator context cards','Native Save/readback and inverse'])
    receipt['output']={p.relative_to(output).as_posix():sha(p.read_bytes()) for p in output.rglob('*') if p.is_file()}
    receipt['changed_files']=[n for n in receipt['input'] if receipt['input'][n]!=receipt['output'][n]]
    output.with_name(output.name+'.manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt
