import unittest
from scripts.grantconnect_closings import confirmed

class OfficialClosingTests(unittest.TestCase):
    def test_confirmed_act_date_ongoing_and_wrong_identity(self):
        rows=[dict(OpportunityKey=str(i),Title=f'GO{i}: Test',URL=f'https://www.grants.gov.au/Go/{i}') for i in range(3)]
        pages=[dict(key=str(i),url=r['URL'],status=200,at='2026-11-01T00:00:00Z',ids=[f'GO{i}'],close=['1-Nov-2026 11:00 pm (ACT Local Time)']) for i,r in enumerate(rows)]
        pages[1]['close']=['Ongoing']
        pages[2]['ids']=['GO999']
        got=confirmed(dict(rows=rows,count=3),pages)
        self.assertEqual(got['dates'][0]['DeadlineUTCInstant'],'2026-11-01T12:00:00+00:00')
        self.assertEqual(got['unresolved'],['1','2'])
