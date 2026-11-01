"""Reconcile official monthly exports and stage only previously unsubmitted identities."""
import argparse
import hashlib
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from scripts.grantconnect_history_ready import stage


def reconcile(months, previous, supplement, target, output):
    output.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect((output / 'reconciliation.sqlite').resolve().as_uri(), uri=True)
    db.execute('ATTACH DATABASE ? AS retained', (previous.resolve().as_uri() + '?mode=ro',))
    db.execute('ATTACH DATABASE ? AS extra', (supplement.resolve().as_uri() + '?mode=ro',))
    db.executescript("""
        CREATE TABLE observed(ga_id TEXT PRIMARY KEY, month TEXT);
        CREATE TABLE award_observations(source TEXT, row_number INTEGER, ga_id TEXT PRIMARY KEY,
                                       reported_go_id TEXT, fields TEXT);
        CREATE TABLE confirmed_links(ga_id TEXT, go_id TEXT, PRIMARY KEY(ga_id,go_id));
        CREATE TABLE closed_opportunities(go_id TEXT,status TEXT,url TEXT,baseline_key TEXT,evidence TEXT);
    """)
    report, originals = [], []
    for receipt in (months / 'receipts.txt').read_text().splitlines():
        month, count, digest = receipt.split()
        path = months / (month + '.xlsx')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Original workbook changed for {month}')
        name = f'grantconnect-original-{digest[:16]}.xlsx'
        originals.append(dict(name=name, path=str(path.resolve()), sha256=digest))
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            rows = iter(workbook.active.values)
            headers = next(row for row in rows if row[0] == 'GA ID' and 'GO ID' in row)
            ids = set()
            for ordinal, row in enumerate(rows, 1):
                if all(value is None for value in row):
                    continue
                fields = {key: value for key, value in zip(headers, row) if key}
                ga, go = fields['GA ID'], fields['GO ID'] or ''
                if not re.fullmatch(r'GA\d+(?:-V\d+)?', ga) or str(fields['Publish Date'])[:7] != month[:7]:
                    raise ValueError(f'Unexpected award or publication month in {month}')
                ids.add(ga)
                db.execute("INSERT OR IGNORE INTO observed VALUES(?,?)", (ga, month[:7]))
                db.execute('INSERT OR IGNORE INTO award_observations SELECT ?,?,?,?,? WHERE NOT EXISTS (SELECT 1 FROM retained.award_observations WHERE ga_id=?)',
                           (name, ordinal, ga, go, json.dumps(fields, default=str), ga))
            report.append(dict(month=month, expected=int(count), distinct=len(ids)))
        finally:
            workbook.close()
    db.execute("""INSERT INTO confirmed_links SELECT a.ga_id,a.reported_go_id FROM award_observations a
                  WHERE a.reported_go_id IN (SELECT go_id FROM retained.opportunities UNION SELECT go_id FROM extra.opportunities)""")
    windows = []
    for source, period, expected in db.execute('SELECT source,period,search_total FROM retained.exports'):
        start, end = [datetime.strptime(day, '%d-%b-%Y').strftime('%Y-%m') for day in period.split(' to ')]
        if start in ('2021-01', '2026-10'):
            continue
        # October already has an accepted complete export. Include its identities only once.
        actual, = db.execute("""
            SELECT COUNT(*) FROM (
              SELECT ga_id FROM observed WHERE month BETWEEN ? AND ?
              UNION SELECT ga_id FROM retained.award_observations WHERE source='october.xlsx' AND ?='2026-10'
            )""", (start, end, end)).fetchone()
        windows.append(dict(period=period, expected=expected, actual=actual))
    (output / 'windows.json').write_text(json.dumps(windows, indent=2))
    db.commit()
    db.close()
    (output / 'coverage.json').write_text(json.dumps(report, indent=2))
    (output / 'originals-upload.json').write_text(json.dumps(target | {'files': originals}))
    if len(windows) != 11 or any(w['actual'] != w['expected'] for w in windows):
        raise ValueError('Award export coverage remains incomplete. Retain originals and inspect windows.json.')
    stage(output / 'reconciliation.sqlite', output, target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('months', 'previous', 'supplement', 'target', 'output'):
        parser.add_argument(arg, type=Path)
    a = parser.parse_args()
    reconcile(a.months, a.previous, a.supplement, json.loads(a.target.read_bytes()), a.output)
