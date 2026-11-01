import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
try:
    from openpyxl import Workbook
except ModuleNotFoundError as exc:
    if exc.name != 'openpyxl':
        raise
    raise unittest.SkipTest('Run with the locked artifact dependency environment') from exc
from scripts.grantconnect_history import build


class HistoricalImportTests(unittest.TestCase):
    def test_versioned_awards_and_only_confirmed_go_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);w=Workbook();s=w.active
            for row in [('Date Range','October 2026'),('GA ID','GO ID'),('GA1','GO1'),('GA1-V1','GO1'),('GA2',''),('GA3','GO99')]:s.append(row)
            w.save(p/'awards-test-4.xlsx')
            url='https://www.grants.gov.au/Go/Show?GoUuid=fixture'
            rows=[dict(OpportunityKey=str(i),Title=f'GO{i}: example',URL=url) for i in range(120)]
            (p/'baseline').write_text(json.dumps({'rows':rows}))
            (p/'detail.json').write_text(json.dumps([dict(id='GO1',heading='Archived Grant Opportunity View - GO1',status=200,url=url,fields={'GO ID:':'GO1'})]))
            build(p,p/'baseline',p/'history.db')
            with sqlite3.connect(p/'history.db') as db:
                self.assertEqual(db.execute('select count(*) from closed_opportunities').fetchone(),(1,))
                self.assertEqual(set(db.execute('select * from confirmed_links')),{('GA1','GO1'),('GA1-V1','GO1')})
                self.assertEqual(db.execute('select count(*) from award_observations').fetchone(),(4,))
