import unittest
from scripts.prepare_real_research_intake import prepare

class RealIntakeTests(unittest.TestCase):
    def test_exact_link_candidate_and_unqualified_people(self):
        p={'Project_x0020_ID':'1','Id':1,'DORAActivityKey':'source:1','PI_x0020_Name':'Fictional person'}
        a={'SourceKey':'award:1','RelatedIdentifiersJSON':'{"project_id":"1"}','ReportedAmountSource':'20.50'}
        result=prepare({'value':[p]},{'value':[a]})
        self.assertEqual(result['proposed_links'][0]['status'],'candidate')
        self.assertIsNone(result['participation'][0]['candidate']['person_id'])
        self.assertIsNone(result['awards'][0]['candidate']['currency'])
        result=prepare({'value':[p,p]},{'value':[a]})
        self.assertEqual(result['proposed_links'],[]);self.assertTrue(result['ambiguous'])
    def test_no_title_join_or_date_guess(self):
        r=prepare({'value':[{'Project_x0020_ID':'1','Start_x0020_Date':'01/02/2026','Title':'Same'}]},{'value':[{'SourceKey':'award:1','Title':'Same','SourceDatesJSON':'{"start":"46023"}'}]})
        self.assertEqual(r['proposed_links'],[]);self.assertIsNone(r['projects'][0]['candidate']['start_date'])
        with self.assertRaises(ValueError):prepare({'value':[],'odata.nextLink':'more'},{'value':[]})
