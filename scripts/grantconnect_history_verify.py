"""Compare the final SharePoint history lists with all retained ready manifests in one pass."""
import argparse
import json
import subprocess
from pathlib import Path
from urllib.parse import urlencode, quote
from uuid import UUID


def verify(binding, site, lists, manifests, receipt):
    receipt.mkdir(parents=True, exist_ok=False)
    expected = {entity: {} for entity in ('awards', 'closed', 'links')}
    for path in manifests:
        for shard in json.loads(path.read_bytes())['files']:
            records = json.loads((path.parent / shard['file']).read_bytes())
            if len(records) != shard['count']:
                raise ValueError('Staged shard count changed')
            keys = expected[shard['entity']]
            for row in records:
                if keys.setdefault(row['HistoryKey'], row['EvidenceHash']) != row['EvidenceHash']:
                    raise ValueError('Conflicting staged evidence')
    def read(root, query, path):
        url = root + '?' + urlencode(query, quote_via=quote, safe='$,')
        subprocess.run(['node', 'scripts/m365-qualified.mjs', 'register-read', str(binding), 'request',
                        '--url', url, '--method', 'get', '--output', 'json', '--accept',
                        'application/json;odata=minimalmetadata', '--filePath', str(path)], check=True)
        return json.loads(path.read_bytes())['value']

    inventory = read(site + '/_api/web/lists', {'$select': 'Id,ItemCount',
                     '$filter': ' or '.join("Id eq guid'" + str(UUID(lists[k])) + "'" for k in expected)},
                     receipt / 'counts.json')
    counts = {row['Id'].lower(): row['ItemCount'] for row in inventory}
    result = {}
    for entity, keys in expected.items():
        root = site + "/_api/web/lists(guid'" + str(UUID(lists[entity])) + "')/items"
        total = counts[lists[entity].lower()]
        if total != len(keys):
            raise ValueError(f"{entity} has {total} native rows, expected {len(keys)}")
        last = count = 0
        while count < total:
            # Bounded indexed ID ranges avoid skipping rows or relying on default sort order.
            query = {'$select': 'Id,HistoryKey,EvidenceHash', '$filter': f'Id gt {last} and Id le {last + 5000}', '$top': '5000'}
            path = receipt / f'{entity}-{last}.json'
            for row in read(root, query, path):
                if keys.pop(row['HistoryKey'], None) != row['EvidenceHash']:
                    raise ValueError(f'Unexpected or changed {entity} record')
                count += 1
            last += 5000
            if last > 10 * total + 50000 and count < total:
                raise ValueError('Native item IDs exceed the expected range')
        if keys:
            raise ValueError(f'{entity} missing {len(keys)} records')
        result[entity] = count
    (receipt / 'acceptance.json').write_text(json.dumps(result, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('binding', 'target_manifest', 'lists', 'receipt'):
        parser.add_argument(key, type=Path)
    parser.add_argument('manifests', type=Path, nargs='+')
    a = parser.parse_args()
    verify(a.binding, json.loads(a.target_manifest.read_bytes())['site_url'],
           json.loads(a.lists.read_bytes()), a.manifests, a.receipt)
