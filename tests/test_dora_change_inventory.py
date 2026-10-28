import unittest
from datetime import datetime, timezone

from scripts.dora_change_inventory import inventory, select_work


class DoRAChangeInventoryTests(unittest.TestCase):
    def xml(self, nodes):
        return '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + nodes + '</urlset>'

    def node(self, key, stamp='2026-10-24T16:00:00Z'):
        return f'<url><loc>https://dora.health.qld.gov.au/qldresearchjspui/handle/1/{key}</loc><lastmod>{stamp}</lastmod></url>'

    def test_scope_gaps_and_opaque_stamp(self):
        result = inventory(self.xml(self.node('1') + self.node('3')), ['1', '2'])
        self.assertEqual(result['missing'], ['2'])
        self.assertEqual(result['versions']['1']['source_stamp'], '2026-10-24T16:00:00Z')
        self.assertFalse(result['utc_cutoff_proven'])

    def test_duplicate_and_entity_rejection(self):
        for xml in [self.xml(self.node('1') * 2), '<!DOCTYPE urlset>' + self.xml(self.node('1'))]:
            with self.assertRaises(ValueError):
                inventory(xml, ['1'])

    def test_no_reuse_without_external_qualification_or_exact_raw_proof(self):
        versions = inventory(self.xml(self.node('1')), ['1'])['versions']
        entry = dict(versions['1'], native_id='id', etag='etag', bytes=10,
                     sha256='a' * 64, archive_folder='/archive', file='raw.html',
                     response_observed_utc='2026-10-24T08:00:00Z')
        bound = dict(now_utc=datetime(2026, 10, 24, 9, tzinfo=timezone.utc), max_age_seconds=3600)
        self.assertEqual(select_work(versions, {'1': entry})['fetch'], ['1'])
        self.assertEqual(len(select_work(versions, {'1': entry}, version_contract_qualified=True, **bound)['reuse']), 1)
        for field in ['native_id', 'etag', 'sha256', 'source_stamp', 'file']:
            bad = dict(entry)
            bad[field] = ''
            self.assertEqual(select_work(versions, {'1': bad}, version_contract_qualified=True, **bound)['fetch'], ['1'])

    def test_changed_missing_stale_future_and_unbounded_records_are_fetched(self):
        versions = inventory(self.xml(self.node('1') + self.node('2')), ['1', '2'])['versions']
        entry = dict(versions['1'], native_id='id', etag='etag', bytes=10,
                     sha256='a' * 64, archive_folder='/old-generation', file='raw.html',
                     response_observed_utc='2026-10-24T08:00:00Z')
        bound = dict(now_utc=datetime(2026, 10, 24, 9, tzinfo=timezone.utc), max_age_seconds=3600)
        good = select_work(versions, {'1': entry}, version_contract_qualified=True, **bound)
        self.assertEqual(good['fetch'], ['2'])
        self.assertEqual(good['reuse'][0]['evidence'], entry)
        self.assertFalse(good['native_deployed'])
        for patch in [{'source_stamp': 'different'}, {'response_observed_utc': '2026-10-24T07:59:59Z'},
                      {'response_observed_utc': '2026-10-24T09:00:01Z'},
                      {'response_observed_utc': '2026-10-24T08:00:00'},
                      {'response_observed_utc': None}, {'sha256': None}, {'native_id': True}]:
            result = select_work(versions, {'1': dict(entry, **patch)}, version_contract_qualified=True, **bound)
            self.assertEqual(result['fetch'], ['1', '2'])
        for missing_bound in [{}, {'now_utc': bound['now_utc']},
                              {'max_age_seconds': 3600}, dict(bound, max_age_seconds=True),
                              dict(bound, max_age_seconds=0), dict(bound, max_age_seconds=-1),
                              dict(bound, now_utc=datetime(2026, 10, 24, 9))]:
            result = select_work(versions, {'1': entry}, version_contract_qualified=True, **missing_bound)
            self.assertEqual(result['fetch'], ['1', '2'])
        self.assertEqual(select_work(versions, {'1': entry}, version_contract_qualified=1, **bound)['fetch'], ['1', '2'])
        self.assertEqual(select_work(versions, {'1': None}, version_contract_qualified=True, **bound)['fetch'], ['1', '2'])
