"""Import official GrantConnect exports and confirmed opportunity detail observations."""
import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from openpyxl import load_workbook


def load_opportunities(db, folder, baseline):
    keys = {r['Title'].partition(':')[0]:r for r in baseline}
    detail_files = [folder/'detail.json', *sorted(folder.glob('pages-*.json'))]
    for r in (r for file in detail_files for r in json.loads(file.read_bytes())):
        go = r['id']; url = urlsplit(r.get('url','')); m = re.fullmatch(r'(Archived|Closed|Current) Grant Opportunity View - '+re.escape(go),r.get('heading') or '')
        if (not m or r['status'] != 200 or r['fields'].get('GO ID:') != go or
                url.scheme!='https' or url.hostname!='www.grants.gov.au' or url.path.lower()!='/go/show'):
            continue
        row=keys.get(go)
        if row and parse_qs(url.query).get('GoUuid') != parse_qs(urlsplit(row['URL']).query).get('GoUuid'):
            raise ValueError('Baseline GO identity conflict')
        db.execute('INSERT OR IGNORE INTO opportunities VALUES(?,?,?,?,?)',(go,m[1],r['url'],row['OpportunityKey'] if row else None,json.dumps(r['fields'])))


def build(folder, baseline_path, destination):
    if destination.exists():
        raise ValueError('New historical database required')
    baseline = json.loads(baseline_path.read_bytes())['rows']
    if len(baseline) != 120 or len({r['OpportunityKey'] for r in baseline}) != 120:
        raise ValueError('Expected the retained 120-key baseline')
    db = sqlite3.connect(destination)
    try:
        db.executescript("""
        CREATE TABLE opportunities(go_id TEXT PRIMARY KEY, status TEXT, url TEXT, baseline_key TEXT, evidence TEXT);
        CREATE TABLE award_observations(source TEXT, row_number INTEGER, ga_id TEXT, reported_go_id TEXT, fields TEXT, PRIMARY KEY(source,row_number));
        CREATE INDEX award_identity ON award_observations(ga_id);
        CREATE TABLE exports(source TEXT PRIMARY KEY, sha256 TEXT, period TEXT, search_total INTEGER, exported INTEGER);
        CREATE VIEW closed_opportunities AS SELECT * FROM opportunities WHERE status IN ('Closed','Archived');
        CREATE VIEW confirmed_links AS SELECT DISTINCT ga_id,reported_go_id AS go_id FROM award_observations a JOIN opportunities o ON a.reported_go_id=o.go_id WHERE NOT EXISTS (SELECT 1 FROM award_observations b WHERE a.ga_id=b.ga_id AND b.reported_go_id<>a.reported_go_id);
        """)
        load_opportunities(db,folder,baseline)
        for f in sorted(folder.glob('*.xlsx')):
            if f.name=='october.xlsx': total=6398
            else: total=int(f.stem.split('-')[-1])
            wb=load_workbook(f,read_only=True,data_only=True)
            try:
                sheet,=wb.worksheets
                records=iter(sheet.values);period=None
                for record in records:
                    if record[0]=='Date Range':period=record[1]
                    if record[0]=='GA ID' and 'GO ID' in record:break
                else:raise ValueError('Missing awards header')
                if not period:raise ValueError('Missing export coverage')
                headers=record;count=0
                for record in records:
                    if all(v is None for v in record):continue
                    fields={k:v for k,v in zip(headers,record) if k};ga=fields['GA ID']
                    if not isinstance(ga,str) or not re.fullmatch(r'GA\d+(?:-V\d+)?',ga,re.I):raise ValueError(f'Invalid GA identity in {f.name}: {ga!r}')
                    count+=1
                    db.execute('INSERT INTO award_observations VALUES(?,?,?,?,?)',(f.name,count,ga,fields['GO ID'] or '',json.dumps(fields,default=str)))
                db.execute('INSERT INTO exports VALUES(?,?,?,?,?)',(f.name,hashlib.sha256(f.read_bytes()).hexdigest(),period,total,count))
            finally:wb.close()
        db.commit()
    except BaseException:
        db.close();destination.unlink(missing_ok=True);raise
    finally:db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('folder','baseline','output'):parser.add_argument(key,type=Path)
    a=parser.parse_args();build(a.folder,a.baseline,a.output)
