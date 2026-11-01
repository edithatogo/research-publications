import copy
import unittest

from scripts.grantconnect_rss import FEED, definition, project
from scripts.grants_registry import stable_key


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
        self.assertEqual(result['rows'][0]['OpportunityKey'], stable_key(result['rows'][0]))
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

    def test_rejects_unusable_capture_provenance_and_registry_key_collisions(self):
        for change in ('naive_time', 'bad_time', 'xml_claim', 'http', 'space_url', 'key_collision'):
            with self.subTest(change=change):
                c = self.capture()
                if change == 'naive_time': c['observed_utc'] = '2026-10-31T02:00:00'
                elif change == 'bad_time': c['observed_utc'] = {'not': 'an instant'}
                elif change == 'xml_claim': c['publisher_xml_retained'] = True
                elif change == 'http': c['items'][0]['primaryLink'] = 'http://www.grants.gov.au/Go/1'
                elif change == 'space_url': c['items'][0]['primaryLink'] += '&bad=two words'
                else:
                    other = copy.deepcopy(c['items'][0]); other['id'] = other['id'].upper()
                    c['items'].append(other)
                with self.assertRaises(ValueError): project(c)
        with self.assertRaises(ValueError): project([])

    def test_source_metadata_cannot_assign_review_or_canonical_status(self):
        c = self.capture()
        c['items'][0].update(ReviewStatus='Reviewed', CanonicalAdmission=True, Deadline='2026-12-01')
        result = project(c)
        self.assertEqual(result['rows'][0]['RawItem'], c['items'][0])
        self.assertEqual(result['rows'][0]['ReviewStatus'], 'Needs Review')
        self.assertIsNone(result['rows'][0]['Deadline'])
        self.assertFalse(result['canonical_admission'])

class XMLBootstrapTests(unittest.TestCase):
    def test_integrity_and_publication_date_is_not_deadline(self):
        import base64
        import hashlib
        from scripts.grantconnect_rss import bootstrap
        xml = b'<rss><channel><item><guid>g1</guid><title>Example</title><link>https://www.grants.gov.au/Go/1</link><pubDate>Sun, 01 Nov 2026 01:00:00 GMT</pubDate></item></channel></rss>'
        capture = dict(url=FEED, status=200, utc='2026-11-01T01:00:00Z', size=len(xml),
                       sha=hashlib.sha256(xml).hexdigest(), base64=base64.b64encode(xml).decode())
        row = bootstrap(capture)['rows'][0]
        self.assertEqual(row['SourceID'], 'g1')
        self.assertFalse(row['DeadlineRaw'])
        self.assertEqual(row['ReviewStatus'], 'Needs Review')
        with self.assertRaises(ValueError):
            bootstrap({**capture, 'size':0})
