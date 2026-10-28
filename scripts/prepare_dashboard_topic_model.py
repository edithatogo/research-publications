"""Prepare additive taxonomy tables for isolated, frozen-snapshot qualification.

No service calls. This versioned local snapshot is rebuilt from retained evidence;
it is not an unattended ingestion route or a native acceptance certificate.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import base64
import copy
import gzip
import json
import uuid

TABLES=('Publication MeSH subjects','Publication OpenAlex topics')


def encode(text):return base64.b64encode(text.encode()).decode()


def table_text(name,rows,columns):
    payload=base64.b64encode(gzip.compress(json.dumps(rows,ensure_ascii=False).encode(),mtime=0)).decode()
    metric='MeSH subject publications' if name==TABLES[0] else 'OpenAlex topic publications'
    lines=[f"/// Frozen retained taxonomy snapshot; distinct publication membership, non-additive across topics.\ntable '{name}'",
           f"\tmeasure '{metric}' = DISTINCTCOUNT('{name}'[CanonicalKey]) + 0\n\t\tformatString: #,0\n\t\tdisplayFolder: Topic coverage"]
    for column in columns:
        data_type='boolean' if column=='PrimaryTopic' else 'string'
        hidden='\n\t\tisHidden' if column in {'CanonicalKey','TopicID','SubfieldID','FieldID','DomainID','ProviderWorkID','SourceHash','CatalogueHash'} else ''
        lines.append(f"\tcolumn {column}\n\t\tdataType: {data_type}{hidden}\n\t\tsummarizeBy: none\n\t\tsourceColumn: {column}")
    types=', '.join(c+' = '+('logical' if c=='PrimaryTopic' else 'text') for c in columns)
    m=f'let Rows = Json.Document(Binary.Decompress(Binary.FromText("{payload}", BinaryEncoding.Base64), Compression.GZip)) in Table.FromRecords(Rows, type table [{types}], MissingField.Error)'
    lines.append(f"\tpartition '{name}' = m\n\t\tmode: import\n\t\tsource =\n\t\t\t{m}")
    return '\n\n'.join(lines)+'\n'


def prepare_topic_model(definition,bridge,canonical_keys):
    result=copy.deepcopy(definition);parts=result.get('definition',{}).get('parts',[])
    if result.get('definition',{}).get('format')!='TMDL':raise ValueError('Complete TMDL required')
    decoded={p['path']:base64.b64decode(p['payload'],validate=True).decode() for p in parts}
    if len(decoded)!=len(parts):raise ValueError('Duplicate model part')
    model=decoded.get('definition/model.tmdl');relationships=decoded.get('definition/relationships.tmdl')
    if model is None or relationships is None or 'definition/tables/Publication.tmdl' not in decoded:
        raise ValueError('Publication model and relationship preimage required')
    if any(f"ref table '{name}'" in model or f'definition/tables/{name}.tmdl' in decoded for name in TABLES):
        raise ValueError('Topic tables already exist; reconcile rather than duplicate')
    keys=set(canonical_keys);rows={name:[] for name in TABLES}
    seen=set()
    for item in bridge['memberships']:
        if item['publication_key'] not in keys or item['status']!='qualified':
            raise ValueError('Unqualified or noncanonical topic membership')
        identity=(item['taxonomy'],item['publication_key'],item['topic_id'])
        if identity in seen:raise ValueError('Duplicate topic membership')
        seen.add(identity)
        shared=dict(CanonicalKey=item['publication_key'],ProviderWorkID=item['provider_work_id'],
                    Source=item['source'],SourceObservedUTC=item['observed_utc'],SourceHash=item['source_hash'],
                    ClassificationVersion=item['classification_version'])
        if item['taxonomy']=='MeSH':
            for tree in item['hierarchy']['tree_positions']:
                group=tree.split('.')[0]
                rows[TABLES[0]].append(dict(shared,DescriptorID=item['topic_id'],DescriptorLabel=item['label'],
                    TreePosition=tree,SecondLevelGroup=group,
                    SecondLevelGroupLabel=item['hierarchy']['second_level_group_labels'].get(group) or group,
                    CatalogueHash=item['catalogue_hash']))
        elif item['taxonomy']=='OpenAlex':
            sub=item['hierarchy']['subfield']
            rows[TABLES[1]].append(dict(shared,TopicID=item['topic_id'],TopicLabel=item['label'],
                SubfieldID=sub['id'],SubfieldLabel=sub['display_name'],PrimaryTopic=item['primary'],
                FieldID=(item['hierarchy'].get('field') or {}).get('id',''),
                FieldLabel=(item['hierarchy'].get('field') or {}).get('display_name',''),
                DomainID=(item['hierarchy'].get('domain') or {}).get('id',''),
                DomainLabel=(item['hierarchy'].get('domain') or {}).get('display_name','')))
        else:raise ValueError('Taxonomy cannot be merged or relabelled')
    columns={
      TABLES[0]:['CanonicalKey','DescriptorID','DescriptorLabel','TreePosition','SecondLevelGroup','SecondLevelGroupLabel',
                 'ProviderWorkID','Source','SourceObservedUTC','SourceHash','ClassificationVersion','CatalogueHash'],
      TABLES[1]:['CanonicalKey','TopicID','TopicLabel','SubfieldID','SubfieldLabel','PrimaryTopic','FieldID','FieldLabel',
                 'DomainID','DomainLabel','ProviderWorkID','Source','SourceObservedUTC','SourceHash','ClassificationVersion']}
    for name in TABLES:
        path=f'definition/tables/{name}.tmdl'
        parts.append(dict(path=path,payload=encode(table_text(name,rows[name],columns[name])),payloadType='InlineBase64'))
        model+=f"\nref table '{name}'\n"
        relation=str(uuid.uuid5(uuid.NAMESPACE_URL,'chhhs-dashboard-topic/'+name))
        if relation in relationships:raise ValueError('Relationship identity already present')
        relationships+=f"\nrelationship {relation}\n\tfromColumn: '{name}'.CanonicalKey\n\ttoColumn: Publication.CanonicalKey\n"
    for part in parts:
        if part['path']=='definition/model.tmdl':part['payload']=encode(model)
        if part['path']=='definition/relationships.tmdl':part['payload']=encode(relationships)
    return result,dict(status='LOCAL_FROZEN_SNAPSHOT_CANDIDATE',native_writes=0,
        table_rows={name:len(values) for name,values in rows.items()},canonical_keys=len(keys),
        changed_existing_parts=['definition/model.tmdl','definition/relationships.tmdl'],
        added_parts=[f'definition/tables/{name}.tmdl' for name in TABLES],
        open_gates=['Isolated native M/DAX authoring','Processing and distinct-key reconciliation',
                    'Topic-to-publication interaction measures','Saved readback and bounded inverse',
                    'Current-target ownership and concurrent editor handoff','Reader rendering and acceptance'])
