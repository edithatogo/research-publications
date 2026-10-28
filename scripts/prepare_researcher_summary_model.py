"""Prepare two additive model views against an exact native definition preimage.

No service calls or deployment. Retains all existing parts byte for byte except
the model's table references. Never replaces an existing researcher table.
The native owner qualifies isolation and handles
same-ID save, targeted processing, query parity and report integration.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import uuid

ROOT = Path(__file__).resolve().parents[1]
TABLES = {
    'ResearcherPublicationMentions': {
        **{n: 'string' for n in ('MentionKey', 'NameGroupKey', 'NameLabel', 'RawAuthorLabel', 'RawAuthorLabelCode', 'CanonicalKey',
                                'Title', 'SourceSet', 'PublicationMonth', 'PublicationDatePrecision',
                                'CHHHSAffiliatedAuthors', 'AttributionStatus', 'AttributionEvidence',
                                'PubMedURL', 'DORAURL', 'IdentityStatus')},
        'AuthorOrder': 'int64', 'PublicationYear': 'int64',
        'IsFirstListed': 'boolean', 'IsLastListed': 'boolean',
    },
    'ResearcherNameSummary': {
        **{n: 'string' for n in ('NameLabel', 'SourceSets', 'IdentityStatus')},
        **{n: 'int64' for n in ('PublicationCount', 'MentionCount', 'FirstListedCount', 'LastListedCount')},
        'NameGroupKey': 'string',
    },
}


def lineage(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'chhhs-research/' + name))


def table_definition(name, columns):
    lines = ['/// Publication evidence only; name labels are not person identities.', f'table {name}',
             f'\tlineageTag: {lineage(name)}', '']
    for column, kind in columns.items():
        if name == 'ResearcherNameSummary' and column == 'NameGroupKey':
            # SUMMARIZE retains source lineage; the service exposes this key
            # through the qualified calculated source column, not [NameGroupKey].
            lines += [f'\tcolumn {column}', '\t\tisNameInferred',
                      '\t\tsourceColumn: ResearcherPublicationMentions[NameGroupKey]', '']
            continue
        lines += [f'\tcolumn {column}', f'\t\tdataType: {kind}',
                  f'\t\tlineageTag: {lineage(name + "/" + column)}']
        if name == 'ResearcherPublicationMentions' and column in ('PubMedURL', 'DORAURL'):
            lines += ['\t\tdataCategory: WebUrl']
        lines += ['\t\tsummarizeBy: none', f'\t\tsourceColumn: [{column}]', '']
    dax = (ROOT / 'dax' / f'{name}.dax').read_text(encoding='utf-8')
    lines += [f'\tpartition {name} = calculated', '\t\tmode: import', '\t\tsource =']
    lines += ['\t\t\t\t' + line for line in dax.splitlines()] + ['']
    return '\n'.join(lines) + '\n'


def prepare(definition):
    result = copy.deepcopy(definition)
    if (not isinstance(result, dict) or not set(result).issubset({'format', 'parts'})
            or not isinstance(result.get('parts'), list)
            or result.get('format', 'TMDL') != 'TMDL'):
        raise ValueError('Supply the native definition object containing parts')
    parts = result['parts']
    paths = [p['path'] for p in parts]
    if len(paths) != len(set(paths)):
        raise ValueError('Duplicate native definition part paths')
    by_path = {p['path']: p for p in parts}
    required = ('definition/model.tmdl', 'definition/expressions.tmdl', 'definition/tables/Publication.tmdl')
    if any(path not in by_path for path in required):
        raise ValueError('Native TMDL model, shared expressions and Publication table required')
    def read(path):
        part = by_path[path]
        if part.get('payloadType') != 'InlineBase64':
            raise ValueError('InlineBase64 native parts required')
        return base64.b64decode(part['payload'], validate=True).decode('utf-8-sig')
    expression_text = read('definition/expressions.tmdl')
    model_text = read('definition/model.tmdl')
    if not re.search(r'^expression CanonicalPublications\s*=', expression_text, re.M):
        raise ValueError('Existing canonical publication query required')
    for name, columns in TABLES.items():
        path = f'definition/tables/{name}.tmdl'
        if path in by_path or re.search(r'^expression\s+[\x27\"]?' + name + r'\b', expression_text, re.M):
            raise ValueError(f'{name} already exists; reconcile native drift before updating')
        if re.search(r'^ref table\s+[\x27\"]?' + name + r'\b', model_text, re.M):
            raise ValueError(f'{name} already referenced')
        model_text += f'\nref table {name}\n'
        parts.append(dict(path=path, payload=base64.b64encode(table_definition(name, columns).encode()).decode(),
                          payloadType='InlineBase64'))
    for path, content in [('definition/model.tmdl', model_text)]:
        by_path[path]['payload'] = base64.b64encode(content.encode()).decode()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--definition', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.definition.read_bytes()
    baseline = json.loads(raw)
    result = ({'definition': prepare(baseline['definition'])}
              if set(baseline) == {'definition'} else prepare(baseline))
    # Exclusive creation prevents replacing a prior prepared generation.
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(dict(preimage_sha256=hashlib.sha256(raw).hexdigest(),
                          tables_added=list(TABLES), deployment_performed=False)))


if __name__ == '__main__':
    main()
