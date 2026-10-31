import copy
import unittest

from scripts.grantconnect_rss import FEED, definition, project


class GrantConnectRSSBootstrapTests(unittest.TestCase):
    def capture(self):
        return dict(kind='grantconnect_rss_connector_capture_v1', source_url=FEED,
                    observed_utc='2026-10-31T02:00:00Z', coverage='returned_current_feed_only',
                    publisher_xml_retained=False, items=[dict(id='fixture-go-id', title='Fictional opportunity',
                    primaryLink='https://www.grants.gov.au/Go/Show?GoUuid=fixture',
                    publishDate='2026-10-01', categories=['Research'], unknown={'preserve': True})])

    def test_manual_only_exact_supported_action_and_no_retry(self):
        d = definition()
        self.assertEqual(len(d['triggers']), 1)
        self.assertEqual(d['triggers']['manual']['kind'], 'Button')
        self.assertEqual(d['actions']['Read_GrantConnect_RSS']['inputs']['parameters'], {'feedUrl': FEED})
        self.assertEqual(d['actions']['Read_GrantConnect_RSS']['inputs']['retryPolicy'], {'type': 'none'})
        self.assertNotIn('authentication', d['actions']['Read_GrantConnect_RSS']['inputs'])
        self.assertEqual(set(d['actions']), {'Read_GrantConnect_RSS', 'Capture_complete_feed'})

    def test_lossless_candidates_unknown_dates_and_no_false_admission(self):
        c = self.capture(); before = copy.deepcopy(c); result = project(c)
        self.assertEqual(c, before)
        self.assertEqual(result['rows'][0]['RawItem'], c['items'][0])
        self.assertIsNone(result['rows'][0]['Deadline'])
        self.assertEqual(result['rows'][0]['Status'], 'Unknown')
        self.assertFalse(result['canonical_admission'])
        self.assertFalse(result['absence_means_withdrawn'])
        self.assertFalse(result['publisher_xml_retained'])

    def test_rejects_wrong_source_duplicates_and_nonofficial_links(self):
        for kind in ('source', 'duplicate', 'link'):
            with self.subTest(kind=kind):
                c = self.capture()
                if kind == 'source': c['source_url'] = 'https://example.invalid/feed'
                elif kind == 'duplicate': c['items'].append(copy.deepcopy(c['items'][0]))
                else: c['items'][0]['primaryLink'] = 'https://grants.gov.au.example.invalid/Go/1'
                with self.assertRaises(ValueError): project(c)
