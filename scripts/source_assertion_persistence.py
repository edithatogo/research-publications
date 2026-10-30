"""Offline DataCite persistence adapter for the existing Source Assertions register.

Prepare and reconcile bounded write candidates; this CLI has no native transport.
SPDX-License-Identifier: Apache-2.0
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path
from scripts.deploy_report_definition import strict
from scripts.relationship_revisions import append, validate_history
from scripts.outcome_persistence import digest
from scripts.outcome_intake import ROOT, save

FORMAT = 'datacite-source-assertion-v1'
FIELDS = {'SourceKey':'Text','Source':'Text','ContextKind':'Text','SourceID':'Text',
          'RelatedID':'Text','SourceURL':'Text','FullSummary':'Note',
          'SourceProjectionJSON':'Note','SourceProvenanceJSON':'Note'}


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def project(history):
    heads = validate_history(history)
    if len(heads) != 1: raise ValueError('Exactly one source assertion lineage per item')
    kinds = set()
    for entry in history:
        record = entry['record']
        if record.get('RelationshipKind') != 'datacite_output_reference':
            raise ValueError('Only retained DataCite references; no grants or diagnostics')
        kinds.add(record['ResourceTypeGeneralRaw'])
        if any(not isinstance(k,str) or not k or k != k.strip() for k in record['CanonicalKeys']):
            raise ValueError('Exact canonical keys required')
    if len(kinds) != 1: raise ValueError('Dataset/software family cannot change through correction')
    head = history[-1]; record = head['record']
    projection = {'format':FORMAT,'state':head['state'],'revision_id':head['revision_id'],
                  'assertions':[record] if head['state']=='active' else [],
                  'history_sha256':digest(history),'native_admission':False}
    provenance = {'format':FORMAT,'history':history,'history_sha256':digest(history)}
    fields = {'SourceKey':'datacite-assertion:'+digest(history[0]['identity']),
              'Source':'DataCite','ContextKind':'datacite_output_reference',
              'SourceID':record['FromKey'],'RelatedID':record['ToKey'],'SourceURL':'',
              'FullSummary':f"{record['ResourceTypeGeneralRaw']} source assertion ({head['state']}; not reviewed): {record['FromKey']} -> {record['ToKey']}",
              'SourceProjectionJSON':encode(projection),'SourceProvenanceJSON':encode(provenance)}
    for field,kind in FIELDS.items():
        maximum=255 if kind=='Text' else 60000
        if len(fields[field].encode('utf-16-le'))//2 > maximum:
            raise ValueError('Field capacity exceeded: '+field)
    return fields


def history_from(fields):
    if set(fields) != set(FIELDS): raise ValueError('Exact managed-field preimage required')
    provenance = strict(fields['SourceProvenanceJSON'].encode())
    if not isinstance(provenance,dict) or provenance.get('format') != FORMAT:
        raise ValueError('Legacy or other producer row; explicit adoption required')
    history=provenance['history']
    if project(history) != fields: raise ValueError('History/projection or human-edit drift; reconcile first')
    return history


def prepare(snapshot, revision):
    before = copy.deepcopy(snapshot['fields']) if snapshot else None
    history = history_from(before) if before is not None else []
    updated = append(history, **revision)
    fields = project(updated)
    plan = {'format':FORMAT,'operation':'create' if snapshot is None else 'update',
            'item_id':None if snapshot is None else snapshot['item_id'],
            'etag':None if snapshot is None else snapshot['etag'],
            'before':before,'after':fields}
    validate(plan)
    return plan


def validate(plan):
    if set(plan) != {'format','operation','item_id','etag','before','after'} or plan['format']!=FORMAT:
        raise ValueError('Exact persistence envelope required')
    history=history_from(plan['after'])
    if plan['operation']=='create':
        if plan['before'] is not None or plan['item_id'] is not None or plan['etag'] is not None or len(history)!=1:
            raise ValueError('Create needs one initial revision and no existing item')
    elif plan['operation']=='update':
        if type(plan['item_id']) is not int or plan['item_id']<1 or not isinstance(plan['etag'],str) or not re.fullmatch(r'(?:W/)?"[^"\r\n]+"',plan['etag']):
            raise ValueError('Exact item identity and ETag required')
        old=history_from(plan['before'])
        if len(history) not in {len(old),len(old)+1} or history[:len(old)]!=old:
            raise ValueError('Append at most one revision; preserve immutable history')
        if plan['after']['SourceKey']!=plan['before']['SourceKey']:raise ValueError('Stable lineage key required')
    else:raise ValueError('Unsupported operation')
    return plan


def schema_requirements(schema):
    """Report only known retained-schema compatibility; never manufacture live proof."""
    fields={f['InternalName']:f for f in schema}
    if len(fields)!=len(schema):raise ValueError('Duplicate schema identities')
    result=[]
    for name,kind in FIELDS.items():
        field=fields.get(name,{})
        if field.get('TypeAsString')!=kind:raise ValueError('Missing/incompatible existing field: '+name)
        required={'ReadOnlyField':False}
        if kind=='Note':required.update(RichText=False,AppendOnly=False)
        if name=='SourceKey':required.update(Indexed=True,EnforceUniqueValues=True)
        for prop,value in required.items():
            outcome='unverified' if prop not in field else 'pass' if field[prop]==value else 'fail'
            result.append({'field':name,'check':prop,'outcome':outcome,'scope':'supplied schema snapshot'})
    return result


def request(plan, current):
    """Build one HTTP write only after exact native identity/preimage reconciliation.

    current is null or {item_id,etag,fields}; caller must provide a complete unique
    SourceKey lookup for creation, or an exact item read for updates.
    """
    validate(plan)
    if current and current['fields']==plan['after']:
        if plan['operation']=='update' and current['item_id']!=plan['item_id']:raise ValueError('Item identity drift')
        return {'outcome':'unchanged_replay','write':None}
    if plan['operation']=='create':
        if current is not None:raise ValueError('Existing SourceKey collision; no overwrite')
        return {'outcome':'prepared','write':{'method':'POST','path':'/items',
                'headers':{'Content-Type':'application/json;odata=nometadata'},
                'body':{**plan['after'],'Title':'DataCite source assertion'},'retries':0,'redirects':0}}
    if current is None or current['item_id']!=plan['item_id'] or current['etag']!=plan['etag'] or current['fields']!=plan['before']:
        raise ValueError('Concurrent edit; no write')
    return {'outcome':'prepared','write':{'method':'POST','path':f"/items({plan['item_id']})",
            'headers':{'Content-Type':'application/json;odata=nometadata','IF-MATCH':plan['etag'],'X-HTTP-Method':'MERGE'},
            'body':plan['after'],'retries':0,'redirects':0}}


def reconcile(plan, current):
    """Classify one post-write read; never suggest resending an uncertain write."""
    validate(plan)
    if current and current['fields']==plan['after']:
        if plan['operation']=='update' and current['item_id']!=plan['item_id']:
            return {'outcome':'conflict','retry_allowed':False}
        return {'outcome':'candidate_present','retry_allowed':False}
    unchanged = current is None if plan['operation']=='create' else current is not None and current['item_id']==plan['item_id'] and current['etag']==plan['etag'] and current['fields']==plan['before']
    return {'outcome':'preimage_present' if unchanged else 'conflict','retry_allowed':False}


def main():
    if sys.version_info[:3]!=(3,15,1):raise RuntimeError('Use repository Python 3.15.1')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True);parser.add_argument('--schema',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();inputs=strict(Path(args.input).read_bytes());schema=strict(Path(args.schema).read_bytes())
    plan=prepare(**inputs);checks=schema_requirements(schema['value'] if isinstance(schema,dict) else schema)
    output=Path(args.output).resolve()
    if not output.is_relative_to(ROOT/'private/ops'):raise ValueError('Private output required')
    save(output,{'plan':plan,'schema_checks':checks,'native_ready':False,
                 'required_before_apply':['fresh exact register identity/versioning and schema','unique complete SourceKey lookup or exact item preimage','qualified same-client one-send executor and durable mutation journal','exact readback; preserve OperatorNotes, Title and unrelated fields'],
                 'apply_deferred':True})
    print('Prepared locally; no authentication, network or tenant mutation')


if __name__=='__main__':main()
