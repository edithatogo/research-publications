"""Portable command safety and cohort boundaries; native PDF proof is separate."""
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from scripts.build_t18_paginated import NS, build, query


class PaginatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(Path('contracts/t18-outcome-indicators.json').read_text())

    def test_scalar_month_is_validated_before_entering_dax(self):
        root = ET.fromstring(build(self.contract))
        ns = {'r': NS}
        command = root.find('.//r:CommandText', ns).text
        self.assertTrue(command.startswith('=Replace('))
        self.assertIn('Code.MonthLiteral(Parameters!ReportMonth.Value)', command)
        self.assertIsNone(root.find('.//r:QueryParameters', ns))
        code = root.find('r:Code', ns).text
        self.assertIn(r'\A[0-9]{4}-(0[1-9]|1[0-2])\z', code)
        self.assertIn('Throw New System.ArgumentException', code)
        self.assertIn('Chr(34) & value & Chr(34)', code)

    def test_monthly_output_reuses_governed_measure_and_oa_keeps_register_cohort(self):
        dax = query(self.contract)
        self.assertIn('CALCULATE([Selected Month Publications]', dax)
        self.assertIn('PeriodEnd <= MAX(ReportingWindow[ReportMonthEndExclusive])', dax)
        self.assertIn('"Value", \'Publication\'[K02 OA rate among assessed]', dax)
        self.assertIn('"Value", \'Publication\'[K02 OA assessment coverage]', dax)
        self.assertIn('"UnknownCount", [K02 Unknown OA publications]', dax)
        self.assertIn('Whole retained publication register; all publication dates', dax)


if __name__ == '__main__':
    unittest.main()
