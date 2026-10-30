"""Explicit project/output links backed by caller-supplied canonical inventories.

No fuzzy matching, source acquisition, approval or native persistence.
SPDX-License-Identifier: Apache-2.0
"""
import copy
from scripts.outcome_persistence import digest

KINDS={'publication','award','dataset','software'}


def prepare(records, inventories, *, complete):
    if complete is not True or set(inventories)!={'project'}|KINDS:
        raise ValueError('Complete typed canonical inventories required')
    keys={}
    for kind,values in inventories.items():
        if not isinstance(values,list) or any(not isinstance(v,str) or not v or v!=v.strip() for v in values) or len(values)!=len(set(values)):
            raise ValueError('Exact unique canonical keys required')
        keys[kind]=set(values)
    seen=set();result=[]
    for record in records:
        if set(record)!={'project_id','output_kind','output_id','evidence_id','evidence_revision','evidence_sha256','status'}:
            raise ValueError('Complete explicit project link required')
        kind=record['output_kind']
        if kind not in KINDS or record['project_id'] not in keys['project'] or record['output_id'] not in keys[kind]:
            raise ValueError('Unresolved typed canonical link')
        if record['status'] not in {'candidate','reviewed','withdrawn'}: raise ValueError('Explicit link disposition required')
        import re
        if not isinstance(record['evidence_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',record['evidence_sha256']): raise ValueError('Evidence hash required')
        for field in ('evidence_id','evidence_revision'):
            if not isinstance(record[field],str) or not record[field] or record[field]!=record[field].strip():raise ValueError('Exact evidence identity/version required')
        identity=digest([record['project_id'],kind,record['output_id'],record['evidence_id']])
        if identity in seen:raise ValueError('Duplicate link identity; reconcile revisions first')
        seen.add(identity);row=copy.deepcopy(record);row['link_id']=identity;result.append(row)
    # Only explicitly reviewed links enter a reporting bridge. Keeping candidates
    # and withdrawals alongside it preserves their evidence without admission.
    bridges={kind:sorted({(r['project_id'],r['output_id']) for r in result if r['output_kind']==kind and r['status']=='reviewed'}) for kind in sorted(KINDS)}
    return {'records':result,'bridges':{k:[{'project_id':p,'output_id':o} for p,o in v] for k,v in bridges.items()},'inventory_sha256':digest(inventories),'native_acceptance':False}



def append_revision(history, record, inventories, *, complete, revision_id, supersedes=None, reason):
    """Append a complete reviewed/candidate/withdrawn assertion without replacing history.

    Canonical inventories are retained per revision so later catalogue changes do
    not rewrite prior evidence. Review status remains a caller assertion.
    """
    heads = validate_history(history)
    for value in (revision_id, reason):
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError('Exact revision identity and reason required')
    normalized = prepare([record], inventories, complete=complete)['records'][0]
    previous = next((e for e in history if e['revision_id'] == supersedes), None)
    lineage = previous['lineage_id'] if previous else normalized['link_id']
    entry = {'lineage_id': lineage, 'revision_id': revision_id, 'supersedes': supersedes,
             'reason': reason, 'record': copy.deepcopy(record), 'inventories': copy.deepcopy(inventories)}
    entry['sha256'] = digest(entry)
    existing = next((e for e in history if e['revision_id'] == revision_id), None)
    if existing is not None:
        if entry != existing: raise ValueError('Revision identity conflict')
        return copy.deepcopy(history)
    if supersedes != heads.get(lineage): raise ValueError('Stale or missing predecessor')
    if previous and previous['record']['output_kind'] != record['output_kind']:
        raise ValueError('Correction cannot change output kind')
    result = copy.deepcopy(history) + [entry]
    validate_history(result)
    return result


def validate_history(history):
    if not isinstance(history, list): raise ValueError('Complete project-link history required')
    heads = {}; seen = set(); kinds = {}
    required = {'lineage_id','revision_id','supersedes','reason','record','inventories','sha256'}
    for entry in history:
        if not isinstance(entry, dict) or set(entry) != required:
            raise ValueError('Incomplete project-link revision envelope')
        for field in ('lineage_id','revision_id','reason'):
            value = entry[field]
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError('Invalid revision identity or reason')
        revision = entry['revision_id']; lineage = entry['lineage_id']
        if revision in seen: raise ValueError('Duplicate revision identity')
        seen.add(revision)
        normalized = prepare([entry['record']], entry['inventories'], complete=True)['records'][0]
        if entry['sha256'] != digest({k:v for k,v in entry.items() if k != 'sha256'}):
            raise ValueError('Revision hash mismatch')
        if entry['supersedes'] != heads.get(lineage): raise ValueError('Forked revision history')
        if lineage not in heads and lineage != normalized['link_id']:
            raise ValueError('Initial lineage identity mismatch')
        kind = entry['record']['output_kind']
        if lineage in kinds and kinds[lineage] != kind: raise ValueError('History output-kind drift')
        heads[lineage] = revision; kinds[lineage] = kind
    return heads


def project_history(history, inventories, *, complete):
    """Only current reviewed assertions feed bridges; all revisions stay in history."""
    heads = validate_history(history)
    selected = [entry for entry in history if heads[entry['lineage_id']] == entry['revision_id']]
    result = prepare([e['record'] for e in selected], inventories, complete=complete)
    for row, entry in zip(result['records'], selected):
        row['lineage_id'] = entry['lineage_id']
        row['revision_id'] = entry['revision_id']
    result['history'] = copy.deepcopy(history)
    result['history_sha256'] = digest(history)
    return result


def process(inputs):
    """Keep the original snapshot interface; explicit operations opt into revisions."""
    operation = inputs.get('operation')
    if operation is None: return prepare(**inputs)
    if operation == 'revise':
        if set(inputs) != {'operation','history','record','inventories','complete','revision_id','supersedes','reason'}:
            raise ValueError('Complete explicit revision inputs required')
        history = append_revision(**{k:v for k,v in inputs.items() if k != 'operation'})
        return project_history(history, inputs['inventories'], complete=inputs['complete'])
    if operation == 'project-history':
        if set(inputs) != {'operation','history','inventories','complete'}:
            raise ValueError('Complete history projection inputs required')
        return project_history(inputs['history'],inputs['inventories'],complete=inputs['complete'])
    raise ValueError('Unknown project-link operation')


def main(argv=None):
    import argparse,json,os,subprocess
    from pathlib import Path
    from scripts.deploy_report_definition import strict
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv);result=process(strict(Path(args.input).read_bytes()))
    root=Path(__file__).resolve().parents[1];out=Path(args.output).resolve()
    if not out.is_relative_to(root/'private'/'ops'):raise ValueError('Private output required')
    subprocess.run(['git','check-ignore','-q',str(out)],cwd=root,check=True)
    with os.fdopen(os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:json.dump(result,f,indent=2,allow_nan=False)
    print('PASS_LOCAL_ONLY; caller review assertions are not independently certified')


if __name__=='__main__':main()
