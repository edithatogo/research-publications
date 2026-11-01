"""Stage immutable, content-addressed SharePoint input files from a retained history database."""
import argparse
import hashlib
import itertools
import json
import sqlite3
from pathlib import Path


def encode(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def rows(db, entity):
    if entity == 'awards':
        observations = db.execute('SELECT ga_id, source, row_number, fields FROM award_observations ORDER BY ga_id, source, row_number')
        for ga, group in itertools.groupby(observations, key=lambda row: row[0]):
            refs = []
            for _, source, ordinal, fields in group:
                refs.append([source, ordinal])
            yield ga, ga, '', {'fields': json.loads(fields), 'originalRows': refs}
    elif entity == 'closed':
        for go, status, url, _, fields in db.execute('SELECT * FROM closed_opportunities ORDER BY go_id'):
            yield go, '', go, {'status': status, 'url': url, 'fields': json.loads(fields)}
    else:
        for ga, go in db.execute('SELECT ga_id, go_id FROM confirmed_links ORDER BY ga_id, go_id'):
            yield ga + '|' + go, ga, go, {'award': ga, 'opportunity': go}


def stage(database, directory, target):
    directory.mkdir(parents=True, exist_ok=True)
    files = []
    def save(prefix, value):
        data = encode(value)
        digest = hashlib.sha256(data).hexdigest()
        path = directory / f'{prefix}-{digest[:24]}.json'
        path.write_bytes(data)
        return {'name': path.name, 'path': str(path.resolve()), 'sha256': digest}

    db = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
    shards = []
    try:
        for entity in ('closed', 'links', 'awards'):
            for group in itertools.batched(rows(db, entity), 1000):
                records = []
                for key, ga, go, evidence in group:
                    raw = encode(evidence)
                    if len(raw.decode()) > 63000:
                        raise ValueError(f'Source evidence exceeds SharePoint note size for {key}')
                    records.append(dict(Title=key, HistoryKey=key, GAID=ga, GOID=go,
                                        EvidenceHash=hashlib.sha256(raw).hexdigest(), SourceEvidence=raw.decode()))
                file = save('gc-history-data', records)
                files.append(file)
                shards.append(dict(entity=entity, file=file['name'], count=len(records)))
    finally:
        db.close()
    ready = save('grantconnect-ready-history', dict(kind='grantconnect_history_v1', files=shards))
    for name, entries in [('data', files), ('ready', [ready])]:
        (directory / (name + '-upload.json')).write_bytes(encode(target | {'files': entries}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('database', 'directory', 'target_manifest'):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    stage(args.database, args.directory, json.loads(args.target_manifest.read_bytes()))
