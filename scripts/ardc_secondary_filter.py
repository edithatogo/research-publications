"""Select review candidates from retained ARDC Activities response files.

The filter is a secondary projection; it never changes source responses and does
not assert affiliation, complete source coverage, freshness or grant eligibility.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from collections.abc import Iterable

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('institutions', 'managingInstitution', 'funder', 'researchers',
          'principalInvestigator', 'title', 'description')


def _strings(value, path):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, f'{path}[{index}]')
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError('Invalid nested field')
            yield from _strings(item, f'{path}.{key}')
    elif value is not None and not isinstance(value, (int, float, bool)):
        raise ValueError('Invalid field value')


def filter_responses(responses: Iterable[tuple[str, bytes]], aliases_raw: bytes) -> dict:
    """Build candidate records with source file hashes and matched-field paths."""
    try:
        config = json.loads(aliases_raw)
        units = config['units']
    except (ValueError, KeyError, TypeError):
        raise ValueError('Invalid organisation reference') from None
    if not isinstance(units, list):
        raise ValueError('Invalid organisation reference')
    aliases = []
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get('Aliases'), list):
            raise ValueError('Invalid organisation aliases')
        for alias in unit['Aliases']:
            if not isinstance(alias, str) or not alias.strip():
                raise ValueError('Invalid organisation alias')
            aliases.append((unit['OrganisationKey'], alias, re.compile(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', re.IGNORECASE)))
    if not aliases:
        raise ValueError('Aliases and source responses required')
    seen, files, candidates = set(), [], []
    for name, raw in responses:
        if not isinstance(name, str) or not name or not isinstance(raw, bytes):
            raise ValueError('Invalid source reference')
        try:
            doc = json.loads(raw)
            if doc.get('status') != 'OK' or str(doc.get('code')) != '200':
                raise ValueError('Invalid source status')
            data = doc['data']
            records = [] if data == [] else data['records']
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ValueError('Invalid Activities response') from None
        if not isinstance(records, list):
            raise ValueError('Invalid source records')
        digest = hashlib.sha256(raw).hexdigest()
        files.append({'source': name, 'sha256': digest, 'records': len(records)})
        for index, record in enumerate(records):
            if not isinstance(record, dict) or not isinstance(record.get('id'), str) or not record['id'].isascii() or not record['id'].isdigit() or not isinstance(record.get('key'), str) or not record['key'].strip():
                raise ValueError('Invalid activity identity')
            if record['id'] in seen:
                raise ValueError('Duplicate activity ID in projection input')
            seen.add(record['id'])
            matches = []
            for field in FIELDS:
                for field_path, value in _strings(record.get(field), field):
                    for org, alias, pattern in aliases:
                        if pattern.search(value):
                            matches.append({'organisation_key': org, 'alias': alias, 'field': field_path})
            if matches:
                candidates.append({'activity_id': record['id'], 'source_key': record['key'],
                                   'source_file': name, 'source_sha256': digest, 'record_index': index,
                                   'matches': matches, 'disposition': 'review_candidate',
                                   'affiliation_confirmed': False})
    if not files:
        raise ValueError('Aliases and source responses required')
    return {'format': 'rims-ardc-activities-candidates-v1', 'alias_sha256': hashlib.sha256(aliases_raw).hexdigest(),
            'source_files': files, 'input_records': len(seen), 'candidates': candidates,
            'source_complete_verified': False, 'current_snapshot_verified': False,
            'affiliation_confirmed': False}


def filter_archived_batches(receipt: dict, read, aliases_raw: bytes) -> dict:
    """Filter the exact batches named by a capture receipt via its archive reader.

    The callback must read the intended archive; successful local filtering is
    not evidence that the callback used SharePoint or that capture was complete.
    """
    if not isinstance(receipt, dict) or receipt.get('source') != 'ardc-research-activities':
        raise ValueError('Invalid Activities capture receipt')
    batches = receipt.get('batches')
    if not isinstance(batches, list) or not batches:
        raise ValueError('Capture receipt has no batches')
    def responses():
        names = set()
        for batch in batches:
            if not isinstance(batch, dict):
                raise ValueError('Invalid batch receipt')
            name, expected = batch.get('name'), batch.get('sha256')
            if (not isinstance(name, str) or re.fullmatch(r'activities-batch-[0-9]{9}\.json', name) is None
                    or name in names or not isinstance(expected, str) or re.fullmatch(r'[0-9a-f]{64}', expected) is None):
                raise ValueError('Invalid batch identity')
            names.add(name)
            raw = read(name)
            if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError('Stored batch differs from capture receipt')
            try:
                data = json.loads(raw)['data']
                count = 0 if data == [] else len(data['records'])
            except (ValueError, KeyError, TypeError):
                raise ValueError('Invalid batch data') from None
            if type(batch.get('count')) is not int or batch['count'] != count:
                raise ValueError('Batch count differs from capture receipt')
            yield name, raw
    result = filter_responses(responses(), aliases_raw)
    if result['input_records'] != receipt.get('records'):
        raise ValueError('Batch records differ from capture receipt')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aliases', type=Path, default=ROOT / 'config/organisation-hierarchy.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('responses', nargs='+', type=Path)
    args = parser.parse_args()
    for path in [args.output, *args.responses]:
        subprocess.run(['git', 'check-ignore', '-q', str(path.resolve())], cwd=ROOT, check=True)
    if args.output.is_symlink() or args.output.exists():
        raise ValueError('New private output required')
    result = filter_responses([(str(path), path.read_bytes()) for path in args.responses], args.aliases.read_bytes())
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        json.dump(result, out, ensure_ascii=False, indent=2)
        out.write('\n')
    print(json.dumps({'input_records': result['input_records'], 'candidate_count': len(result['candidates']),
                      'source_complete_verified': False}))


if __name__ == '__main__':
    main()
