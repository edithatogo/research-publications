import hashlib,json,unittest
from scripts.prepare_funding_capacity_reader import prepare
from scripts.deploy_report_definition import parts,fingerprint
from test_definition_packet import definition

class FundingReaderTests(unittest.TestCase):
    def test_addition_retains_existing_parts_and_currency_grain(self):
        expression='expression FundingCapacityProjection = "FICTIONAL"\n'
        m=definition(**{'definition/model.tmdl':'model Model\n','definition/expressions.tmdl':expression})
        r=definition(**{'definition/pages/pages.json':json.dumps({'pageOrder':['Existing']}),'definition.pbir':'binding','table.json':json.dumps({'visual':{'visualType':'tableEx'}})})
        result=prepare(m,r,model_sha256=fingerprint(m),report_sha256=fingerprint(r),expression_sha256=hashlib.sha256(expression.encode()).hexdigest(),table_template_path='table.json')
        self.assertEqual(parts(result['report'])['definition.pbir'],b'binding')
        cohort=parts(result['model'])['definition/tables/AwardStartCohort.tmdl'].decode()
        self.assertIn('column currency',cohort);self.assertIn('column start_year',cohort)
        self.assertIn('HASONEVALUE(AwardStartCohort[currency])',cohort)
        chart=json.loads(parts(result['report'])['definition/pages/FundingCohortChart/visuals/award-cohorts/visual.json'])
        self.assertIn('Series',chart['visual']['query']['queryState'])
        self.assertNotIn('SUM(',cohort);self.assertFalse(result['native_ready'])
        with self.assertRaises(ValueError): prepare(m,r,model_sha256='stale',report_sha256=fingerprint(r),expression_sha256='',table_template_path='table.json')
