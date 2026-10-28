import copy
import unittest
from scripts.reconcile_publication_outcome_views import FIELDS, reconcile, rows


class OutcomeParityTests(unittest.TestCase):
    def setUp(self):
        self.source = [{k: None for k in FIELDS}]
        self.source[0].update(CanonicalKey='PUB:fictional', Title='Fictional',
                              PublicationDatePrecision='unknown')
        self.detail = [{**self.source[0], 'SnapshotID':'current', 'OAOpen':0,
                        'OAClosed':0, 'OAUnknown':1}]
        self.plot = dict(Included=1, Open=0, Closed=0, Unknown=1, UnknownMonth=1,
                         Assessed=0, Rate=None, Coverage=0.0)
        self.views = [dict(SnapshotID='current', Available=True,
            CutoffExclusive='2026-10-01T00:00:00', CapturedUTC='2026-10-24T01:00:00',
            MetricVersion='v1', ModelRevision='m1', ReportRevision='r1', SourceVersions='batch:fictional'),
            dict(SnapshotID='original-unavailable', Available=False)]

    def run_case(self):
        return reconcile(self.source, self.detail, self.plot, self.views)

    def test_missing_evidence_is_unknown_and_rate_is_blank(self):
        self.assertEqual(self.run_case()['metrics']['Unknown'], 1)
        self.assertIsNone(self.run_case()['metrics']['Rate'])

    def test_field_key_and_duplicate_mismatches_fail(self):
        for field in FIELDS:
            before = copy.deepcopy(self.detail)
            self.detail[0][field] = 'different'
            with self.subTest(field=field), self.assertRaises(ValueError): self.run_case()
            self.detail = before
        self.detail.append(copy.deepcopy(self.detail[0]))
        with self.assertRaises(ValueError): self.run_case()

    def test_plot_cannot_hide_unknown_as_zero_or_invent_rate(self):
        for field, value in [('Unknown',0), ('Rate',0), ('Included',True), ('Coverage',float('nan'))]:
            before = self.plot.copy(); self.plot[field]=value
            with self.subTest(field=field), self.assertRaises(ValueError): self.run_case()
            self.plot=before

    def test_invalid_oa_states_fail(self):
        self.detail[0]['OAOpen']=1
        with self.assertRaises(ValueError):self.run_case()

    def test_unavailable_original_and_provenance_cannot_be_fabricated(self):
        self.views[1]['Available']=True
        with self.assertRaises(ValueError):self.run_case()
        self.views[1]['Available']=False
        self.views[0]['SourceVersions']=''
        with self.assertRaises(ValueError):self.run_case()

    def test_failed_query_and_ambiguous_columns_are_rejected(self):
        for d in [{'error':{}}, {'results':[{'error':{'message':'failed'}}]},
                  {'results':[{'tables':[{'rows':[{'T[A]':1,'[A]':2}]}]}]}]:
            with self.subTest(d=d), self.assertRaises(ValueError):rows(d)

    def test_incomplete_or_malformed_capture_is_not_empty_success(self):
        valid={'results':[{'tables':[{'rows':[]}]}]}
        malformed=[{}, {'results':[None]}, {'results':[{'tables':[None]}]},
                   {'results':[{'tables':[{}]}]},
                   {'results':[{'tables':[{'rows':{}}]}]},
                   {'results':[{'tables':[{'rows':[None]}]}]}]
        for level in ('root','result','table'):
            for field,value in [('partial',True),('truncated','false'),('partial',0),('errors',[])]:
                doc=copy.deepcopy(valid)
                node=doc if level=='root' else doc['results'][0]
                if level=='table':node=node['tables'][0]
                node[field]=value;malformed.append(doc)
        for doc in malformed:
            with self.subTest(doc=doc),self.assertRaises(ValueError):rows(doc)
        self.assertEqual(rows(valid),[])
