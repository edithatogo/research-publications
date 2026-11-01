"""Reconcile official GO detail-page close fields against a retained RSS register."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.reconcile_arc_awards_snapshots import write_new


def confirmed(register, pages):
    records = {row['OpportunityKey']: row for row in register['rows']}
    seen, dates, unknown = set(), [], []
    for page in pages:
        key = page['key']
        row = records[key]
        if key in seen or page['url'] != row['URL']:
            raise ValueError('Duplicate or mismatched source observation')
        seen.add(key)
        go = row['Title'].partition(':')[0].strip()
        if (page.get('status') != 200 or page.get('ids') != [go]
                or len(page.get('close', [])) != 1):
            unknown.append(key)
            continue
        raw = ' '.join(page['close'][0].split())
        match = re.fullmatch(r'(\d{1,2}-[A-Za-z]{3}-\d{4} \d{1,2}:\d{2} [ap]m) \(ACT Local Time\)(?: Show close time for other time zones)?', raw, re.I)
        if not match:
            unknown.append(key)
            continue
        local = datetime.strptime(match[1], '%d-%b-%Y %I:%M %p').replace(tzinfo=ZoneInfo('Australia/Sydney'))
        if local.replace(fold=1).utcoffset() != local.utcoffset():
            unknown.append(key)
            continue
        dates.append(dict(OpportunityKey=key, SourceID=go, SourceURL=row['URL'], DeadlineRaw=raw,
                          DeadlineSourceDate=local.date().isoformat(), DeadlineUTCInstant=local.astimezone(timezone.utc).isoformat(),
                          DeadlineBrisbaneDate=local.astimezone(ZoneInfo('Australia/Brisbane')).date().isoformat(),
                          ObservedUTC=page['at']))
    if seen != set(records) or len(records) != register['count']:
        raise ValueError('Incomplete source coverage')
    return dict(dates=dates, unresolved=unknown)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('register', 'pages', 'output'):
        parser.add_argument(name, type=Path)
    a = parser.parse_args()
    result = confirmed(json.loads(a.register.read_bytes()), json.loads(a.pages.read_bytes()))
    write_new(a.output, result, [a.register, a.pages])
    print(f"{len(result['dates'])} confirmed, {len(result['unresolved'])} unresolved")
