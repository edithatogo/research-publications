"""Prepare an additive frozen-model connection; never deploy or refresh.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import base64
import copy
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.consume_retained_pubmed import sha, pinned
from scripts.reconcile_arc_awards_snapshots import fingerprint, preimage, write_new

TABLE = 'RetainedGrantReferences'
TABLE_PATH = 'definition/tables/' + TABLE + '.tmdl'
ROOT = 'definition/model.tmdl'
RELS = 'definition/relationships.tmdl'
LOGICAL = {'CandidateEligible', 'CanonicalAdmission', 'IdentityQualified',
           'MutationAuthorized', 'SourceRetracted'}


def mtext(value):
    return '"' + value.replace('#', '#(#)').replace('"', '""') + '"'


def prepare(model, artifact_content, upload, target, *, model_sha256, artifact_sha256, artifact_bytes):
    if fingerprint(model) != model_sha256:
        raise ValueError('Frozen model preimage drift')
    raw = artifact_content.encode('utf-8')
    if len(raw) != artifact_bytes or sha(raw) != artifact_sha256:
        raise ValueError('Exact accepted artifact bytes required')
    artifact = json.loads(raw)
    definition = model['definition']
    paths = [p['path'] for p in definition['parts']]
    preimage(definition, fingerprint(definition), paths)
    parts = {p['path']: p for p in definition['parts']}
    if (definition.get('format') != 'TMDL' or TABLE_PATH in parts
            or not {ROOT, RELS, 'definition/tables/Publication.tmdl', 'definition/expressions.tmdl'} <= set(parts)):
        raise ValueError('Exact additive model dependencies required')
    text = lambda path: base64.b64decode(parts[path]['payload'], validate=True).decode('utf-8-sig')
    if not re.search(r'^\tcolumn CanonicalKey\s*$', text('definition/tables/Publication.tmdl'), re.M):
        raise ValueError('Publication key dependency missing')
    if TABLE in text(ROOT) or TABLE in text(RELS):
        raise ValueError('Existing relationship/table requires reconciliation')
    files = upload.get('files', [])
    if (upload.get('status') != 'PASS_COMPLETE' or len(files) != 1
            or files[0].get('sha256') != artifact_sha256 or files[0].get('action') != 'create'
            or not files[0].get('UniqueId') or not files[0].get('ETag')):
        raise ValueError('Accepted immutable cloud byte receipt required')
    site, folder = target['site_url'], target['folder']
    if site not in text('definition/expressions.tmdl'):
        raise ValueError('Reuse an existing model source; no new credential scope')
    url = urlsplit(site)
    relative = folder.removeprefix(url.path + '/')
    if (url.scheme != 'https' or not url.hostname or not url.hostname.endswith('.sharepoint.com')
            or not folder.startswith(url.path + '/') or url.query or url.fragment
            or any(x in ('', '.', '..') for x in relative.split('/'))):
        raise ValueError('Exact existing cloud folder required')
    name = files[0]['name']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', name):
        raise ValueError('Exact immutable filename required')
    edges = artifact['edges']
    keys = [r['EvidenceKey'] for r in edges]
    if (artifact.get('kind') != 'retained_pubmed_grant_references_v1' or not edges
            or len(edges) != artifact['edge_count'] or len(set(keys)) != len(keys)
            or artifact.get('confirmed_relationship_count') != 0
            or any(r['RelationshipKind'] != 'publication_grant_reference'
                   or r['CanonicalAdmission'] is not False or r['MutationAuthorized'] is not False
                   or r['IdentityQualified'] is not False for r in edges)):
        raise ValueError('Complete unique candidate grant-reference artifact required')
    columns = sorted(edges[0])
    if any(set(r) != set(columns) for r in edges):
        raise ValueError('Complete edge schema parity required')
    field_list = '{' + ','.join(mtext(c) for c in columns) + '}'
    key_list = '{' + ','.join(mtext(k) for k in sorted(keys)) + '}'
    segments = '{' + ','.join(mtext(x) for x in relative.split('/')) + '}'
    wire = base64.b64encode(raw).decode('ascii')
    expected_bytes = 'Text.Combine({' + ','.join(mtext(wire[i:i+16384]) for i in range(0, len(wire), 16384)) + '})'
    source = '\n'.join([
        'let',
        '    Root = SharePoint.Contents(' + mtext(site) + ', [ApiVersion=15]),',
        '    Folder = List.Accumulate(' + segments + ', Root, (Current, Segment) =>',
        '        let Matches=Table.SelectRows(Current, each [Name]=Segment)',
        '        in if Table.RowCount(Matches)=1 then Matches{0}[Content] else error "Folder identity drift"),',
        '    Matches = Table.SelectRows(Folder, each [Name]=' + mtext(name) + '),',
        '    Bytes = if Table.RowCount(Matches)=1 then Binary.Buffer(Matches{0}[Content]) else error "Artifact identity drift",',
        '    ExpectedBytes = ' + expected_bytes + ',',
        '    Payload = if Binary.Length(Bytes)=' + str(artifact_bytes) + ' and Binary.ToText(Bytes, BinaryEncoding.Base64)=ExpectedBytes',
        '        then Json.Document(Bytes) else error "Artifact byte drift",',
        '    Rows = if Payload[kind]="retained_pubmed_grant_references_v1" and Payload[confirmed_relationship_count]=0',
        '        and Payload[edge_count]=' + str(len(edges)) + ' and Payload[publication_count]=' + str(artifact['publication_count']),
        '        then Payload[edges] else error "Artifact scope drift",',
        '    Keys = List.Transform(Rows, each [EvidenceKey]),',
        '    Checked = if List.Count(Keys)=' + str(len(edges)) + ' and List.Sort(Keys)=' + key_list,
        '        and List.Count(List.Distinct(Keys))=List.Count(Keys)',
        '        and List.AllTrue(List.Transform(Rows, each [CanonicalAdmission]=false and [MutationAuthorized]=false and [IdentityQualified]=false))',
        '        then Rows else error "Candidate key or admission drift",',
        '    Result = Table.FromRecords(Checked, ' + field_list + ', MissingField.Error),',
        '    Paths = Table.TransformColumns(Result, {{"SourcePaths", each Text.FromBinary(Json.FromValue(_), TextEncoding.Utf8), type text}})',
        'in Paths'])
    lines = ['/// Candidate source references; no confirmed funding or identity inference.', 'table ' + TABLE]
    for c in columns:
        dtype = 'boolean' if c in LOGICAL else 'int64' if c == 'CanonicalMatchCount' else 'string'
        lines.extend(['\tcolumn ' + c, '\t\tdataType: ' + dtype, '\t\tsummarizeBy: none', '\t\tsourceColumn: ' + c])
    lines.extend(['\tpartition ' + TABLE + ' = m', '\t\tmode: import', '\t\tsource =',
                  *['\t\t\t\t' + line for line in source.splitlines()]])
    candidate = copy.deepcopy(model)
    by = {p['path']: p for p in candidate['definition']['parts']}
    relationship = ('\nrelationship rimsRetainedGrantReferencesPublication\n'
                    '\tfromColumn: RetainedGrantReferences.CanonicalKey\n'
                    '\ttoColumn: Publication.CanonicalKey\n\tfromCardinality: many\n'
                    '\ttoCardinality: one\n\tcrossFilteringBehavior: oneDirection\n')
    for path, addition in [(ROOT, '\nref table ' + TABLE + '\n'), (RELS, relationship)]:
        by[path]['payload'] = base64.b64encode(base64.b64decode(parts[path]['payload']) + addition.encode()).decode()
    candidate['definition']['parts'].append(dict(path=TABLE_PATH, payloadType='InlineBase64',
        payload=base64.b64encode(('\n'.join(lines) + '\n').encode()).decode()))
    return dict(status='prepared_not_deployable', modelDefinition=candidate, inverse=model,
                frozenModelSHA256=model_sha256, artifactSHA256=artifact_sha256,
                artifactIdentity=files[0], changedParts=[ROOT, RELS, TABLE_PATH],
                preservedPartCount=len(parts)-2, sourceRows=len(edges),
                nativeSaveSubmitted=False, nativeDeploymentReady=False,
                blockers=['current_exact_target_preimage_and_write_inverse',
                          'native_artifact_identity_and_complete_byte_hash_guard',
                          'current_Publication_key_and_field_parity',
                          'native_M_execution_and_relationship_filter_parity'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--input-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    data = pinned(a.input, a.input_sha256)
    result = prepare(**data)
    write_new(a.output, result, [a.input])
    print(result['status'] + '; no native save or refresh')


if __name__ == '__main__':
    main()
