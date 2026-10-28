"""Fictional semantic fixtures; no provider requests or native changes."""
import unittest
from scripts.dashboard_metrics import (citation_summary, collaboration_pairs,
    topic_counts, forecast_baselines, candidate_promotable)

class DashboardMetricsTests(unittest.TestCase):
    def test_citation_provider_missing_and_duplicates(self):
        a=dict(publication_key='a',provider='A',count=0,observed_utc='2026-10-01T00:00:00Z')
        b=dict(publication_key='b',provider='A',count=8,observed_utc='2026-10-01T00:00:00Z')
        r=citation_summary(['a','b','c'],[a,a,b,dict(b,provider='B',count=900)],'A')
        self.assertEqual((r['total'],r['median'],r['unknown'],r['uncited_share']),(8,4,1,.5))
        self.assertEqual(r['collection_h_index'],1)
        with self.assertRaises(ValueError):citation_summary(['a'],[a,dict(a,count=2)],'A')
        self.assertIsNone(citation_summary(['x'],[],'A')['total'])
    def test_collaboration_identity_duplicates_and_reverse_order(self):
        rows=[dict(publication_key=w,entity_key=e,identity_status='Source-supported')
              for w in ['p1','p2'] for e in ['B','A','A']]
        rows.append(dict(publication_key='p1',entity_key='C',identity_status='Unresolved'))
        r=collaboration_pairs(rows)
        self.assertEqual(r['pairs'],[dict(a='A',b='B',publications=['p1','p2'],shared_count=2)])
        self.assertEqual((r['repeat_pairs'],r['unresolved_mentions']),(1,1))
    def test_topics_overlap_not_additive(self):
        r=dict(publication_key='p1',taxonomy='MeSH',status='qualified',source_hash='fixture',observed_utc='fixture')
        result=topic_counts(['p1','p2'],[dict(r,topic_id='A'),dict(r,topic_id='A'),dict(r,topic_id='B')],'MeSH')
        self.assertEqual(result['counts'],{'A':1,'B':1})
        self.assertEqual(result['classified'],1)
        self.assertEqual(result['unknown'],1)
    def test_forecast_suppresses_unknown_coverage_and_sparse_history(self):
        data={y:10 for y in range(2000,2015)}
        self.assertEqual(forecast_baselines(data,[],2014)['status'],'suppressed')
        self.assertEqual(forecast_baselines(data,set(data),2014)['status'],'baseline_evaluated')
        data.pop(2005)
        self.assertEqual(forecast_baselines(data,set(data),2014)['status'],'suppressed')
    def test_forecast_no_future_leakage(self):
        data={y:y-1990 for y in range(2000,2016)}
        a=forecast_baselines(data,set(data),2014)
        data[2015]=999999
        self.assertEqual(a,forecast_baselines(data,set(data),2014))
        cases=a['models']['previous_year']['1']['cases']
        self.assertEqual(len(cases),5)
        self.assertTrue(all(r['training_end'] < r['target_year'] for r in cases))
    def test_candidate_requires_improvement_and_bias(self):
        self.assertTrue(candidate_promotable(9,1,10,1))
        self.assertFalse(candidate_promotable(9,2,10,1))
        self.assertFalse(candidate_promotable(0,0,0,0))
        with self.assertRaises(ValueError):candidate_promotable(float('nan'),0,1,0)

    def test_each_horizon_requires_five_rolling_origins(self):
        data={y:y-1990 for y in range(2000,2015)}
        result=forecast_baselines(data,set(data),2014)
        for model in result['models'].values():
            self.assertEqual(model['1']['status'],'evaluated')
            for horizon in ('2','3'):
                self.assertEqual(model[horizon]['status'],'suppressed')
                self.assertIsNone(model[horizon]['mae'])
                self.assertIsNone(model[horizon]['bias'])
        data.update({2015:25,2016:26})
        result=forecast_baselines(data,set(data),2016)
        for model in result['models'].values():
            self.assertTrue(all(v['status']=='evaluated' for v in model.values()))
            self.assertEqual(len(model['3']['cases']),5)

if __name__ == '__main__':unittest.main()
