"""Prepare a complete additive researcher-measure definition; never save a model.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'config/researcher-evidence-measures.json'


def contract() -> dict:
    value = json.loads(CONTRACT.read_text(encoding='utf-8'))
    names = [m['name'] for m in value['measures']]
    if len(names) != len({name.casefold() for name in names}) or not names:
        raise ValueError('Distinct measure names required')
    for measure in value['measures']:
        if any('\n' in measure[k] or '\r' in measure[k]
               for k in ('name', 'expression', 'description', 'formatString')):
            raise ValueError('Single-line measure contract required')
    return value


def query_definitions() -> str:
    value = contract()
    table = value['table'].replace("'", "''")
    return 'DEFINE\n' + '\n'.join(
        f"MEASURE '{table}'[{m['name'].replace(']', ']]')}] = {m['expression']}"
        for m in value['measures']) + '\n'


def prepare(preimage: Path, output: Path, expected_sha256: str) -> dict:
    raw = preimage.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Exact native preimage fingerprint required')
    if output.exists():
        raise ValueError('New output required')
    doc = json.loads(raw)
    doc = doc.get('text', doc)
    if isinstance(doc, str):
        doc = json.loads(doc)
    original = doc['definition']
    definition = copy.deepcopy(original)
    parts = definition['parts']
    if len({p['path'] for p in parts}) != len(parts):
        raise ValueError('Duplicate definition part paths')
    spec = contract()
    target = f"definition/tables/{spec['table']}.tmdl"
    selected = next((p for p in parts if p['path'] == target), None)
    if selected is None:
        raise ValueError('Expected researcher table absent')
    existing = set()
    for part in parts:
        if part['path'].endswith('.tmdl'):
            source = base64.b64decode(part['payload'], validate=True).decode('utf-8')
            for quoted, plain in re.findall(r"^\tmeasure\s+(?:'((?:[^']|'')+)'|([^=\n]+?))\s*=", source, re.M):
                existing.add((quoted.replace("''", "'") or plain).casefold())
    if any(m['name'].casefold() in existing for m in spec['measures']):
        raise ValueError('Existing measure name collision; reconcile rather than overwrite')
    publication = next((p for p in parts if p['path'] == 'definition/tables/Publication.tmdl'), None)
    if publication is None:
        raise ValueError('Canonical publication table required')
    canonical = base64.b64decode(publication['payload'], validate=True).decode('utf-8')
    key = re.search(r'\n\tcolumn CanonicalKey\n(.*?)(?=\n\t(?:column|partition|measure|hierarchy) |\Z)',
                    canonical, re.S)
    if key is None or '\t\tdataType: string\n' not in key[1]:
        raise ValueError('Canonical publication key type drift')
    source = base64.b64decode(selected['payload'], validate=True).decode('utf-8')
    required_types = {'CanonicalKey': 'string', 'NameGroupKey': 'string',
                      'IsFirstListed': 'boolean', 'IsLastListed': 'boolean'}
    for name, kind in required_types.items():
        block = re.search(r'\n\tcolumn ' + re.escape(name) +
                          r'\n(.*?)(?=\n\t(?:column|partition|measure|hierarchy) |\Z)',
                          source, re.S)
        if block is None or f'\t\tdataType: {kind}\n' not in block[1]:
            raise ValueError('Required researcher column type drift: ' + name)
    modified = source
    hidden_added = []
    for name in spec['hiddenAggregateKeys']:
        declaration = f'\n\tcolumn {name}\n'
        start = modified.index(declaration) + len(declaration)
        end = modified.find('\n\tcolumn ', start)
        if end < 0:
            end = modified.find('\n\tpartition ', start)
        if end < 0:
            raise ValueError('Unbounded key column block')
        if '\t\tisHidden' not in modified[start:end]:
            modified = modified[:start] + '\t\tisHidden\n' + modified[start:]
            hidden_added.append(name)
    blocks = []
    for measure in spec['measures']:
        name = measure['name'].replace("'", "''")
        blocks.append(
            f"\t/// {measure['description']}\n"
            f"\tmeasure '{name}' = {measure['expression']}\n"
            f"\t\tformatString: {measure['formatString']}\n"
            f"\t\tdisplayFolder: {spec['displayFolder']}\n\n")
    insertion = modified.index('\n\tcolumn ') + 1
    added = ''.join(blocks)
    modified = modified[:insertion] + added + modified[insertion:]
    # Reverse the entire intended delta to prove existing definitions survived.
    restored = modified.replace(added, '', 1)
    for name in hidden_added:
        restored = restored.replace(f'\n\tcolumn {name}\n\t\tisHidden\n',
                                    f'\n\tcolumn {name}\n', 1)
    if restored != source:
        raise ValueError('Existing table definition changed unexpectedly')
    selected['payload'] = base64.b64encode(modified.encode('utf-8')).decode('ascii')
    changed = [a['path'] for a, b in zip(parts, original['parts']) if a != b]
    if changed != [target]:
        raise ValueError('Unexpected definition delta')
    if preimage.read_bytes() != raw:
        raise ValueError('Native preimage file changed during preparation')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents an existing prepared input from being replaced.
    with output.open('x', encoding='utf-8') as stream:
        json.dump({'definition': definition}, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    return {'sourceSHA256': expected_sha256,
            'candidateSHA256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'contractSHA256': hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
            'partCount': len(parts), 'changedParts': changed,
            'addedMeasures': [m['name'] for m in spec['measures']],
            'aggregateKeysHidden': hidden_added,
            'existingTableDefinitionReversiblyPreserved': True,
            'modelSaveSubmitted': False, 'refreshSubmitted': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preimage', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.preimage, args.output, args.expected_sha256), indent=2))
