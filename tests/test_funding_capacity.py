import unittest
from scripts.funding_capacity import project


class FundingCapacityTests(unittest.TestCase):
    def test_grains_currency_cohorts_and_unknowns(self):
        projects = [dict(project_id='FIC-P1',start_date='2025-01-01',end_date=None,end_date_known=True,chhhs_led=True),dict(project_id='FIC-P2',start_date=None,end_date_known=False)]
        awards = [dict(award_id='FIC-A1',record_kind='Award',currency='AUD',start_date='2025-01-01',amount='10.25'),dict(award_id='FIC-A2',record_kind='Award',currency='USD',start_date='2025-01-01',amount='20.10')]
        roles = [dict(participation_id='FIC-R'+str(i),project_id='FIC-P1',person_id='FIC-PERSON',role=role,start_date='2025-01-01',end_date=None,end_date_known=True) for i,role in enumerate(['lead','researcher'])]
        result = project(projects,awards,roles,period_end='2026-01-01',complete=True)
        self.assertEqual(result['active_projects'],1); self.assertEqual(result['unknown_project_periods'],1)
        self.assertEqual(result['evidenced_researchers'],1)
        self.assertEqual([r['amount'] for r in result['award_cohorts']],['10.25','20.10'])
        self.assertIsNone(result['fte'])
    def test_opportunities_duplicates_and_incomplete_snapshot_refused(self):
        with self.assertRaises(ValueError): project([],[],[],period_end='2026-01-01',complete=False)
        with self.assertRaises(ValueError): project([], [{'award_id':'FIC-A','record_kind':'Opportunity'}],[],period_end='2026-01-01',complete=True)
        with self.assertRaises(ValueError): project([{'project_id':'FIC-P'},{'project_id':'FIC-P'}],[],[],period_end='2026-01-01',complete=True)
