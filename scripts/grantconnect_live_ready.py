"""Make content-addressed live ready files using the accepted register and confirmed dates."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.grantconnect_history_ready import encode


def stage(register, closings, directory):
    by_key = {r['OpportunityKey']: r for r in register['rows']}
    dates = []
    for date in closings['dates']:
        row = by_key[date['OpportunityKey']]
        if row['URL'] != date['SourceURL'] or not date['DeadlineUTCInstant']:
            raise ValueError('Closing identity conflict')
        key = 'GC-CLOSE:' + hashlib.sha256(row['OpportunityKey'].encode()).hexdigest()[:32]
        revision = hashlib.sha256(json.dumps([key, date['DeadlineUTCInstant'], row['URL']], separators=(',', ':')).encode()).hexdigest()
        dates.append(date | dict(RegistrySourceID=row['SourceID'], Title=row['Title'], DeadlineKey=key, Revision=revision))
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in [('register', register), ('dates', dict(kind='grantconnect_closings_v1', dates=dates))]:
        raw = encode(data)
        digest = hashlib.sha256(raw).hexdigest()
        (directory / f'grantconnect-ready-{name}-{digest[:24]}.json').write_bytes(raw)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('register', 'closings', 'directory'):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    stage(json.loads(args.register.read_bytes()), json.loads(args.closings.read_bytes()), args.directory)
