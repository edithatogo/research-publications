"""Focused source-day, opt-in and native boundary contract regressions."""
import copy
import json
import unittest

from scripts.prepare_live_grants_calendar import decision, worker, signal_adapter, qualification


class LiveCalendarTests(unittest.TestCase):
    def setUp(self):
        self.source = {'OpportunityKey': 'GC:1', 'Source': 'GrantConnectRSS',
                       'URL': {'Url': 'https://www.grants.gov.au/Go/Show?GoUuid=one'},
                       'ReviewStatus': 'Needs Review'}
        self.day = {'DeadlineKey': 'GC-CLOSE:' + 'a' * 32, 'OpportunityKey': 'GC:1',
                    'SourceURL': self.source['URL'], 'RevisionApplied': True,
                    'ReviewStatus': 'Source confirmed', 'DeadlinePrecision': 'day',
                    'Calendar_x0020_day': '2026-12-31', 'Cancelled': False}
        self.rule = {'UserKey': '7', 'AuthorId': 7, 'Active': True,
                     'SubscriptionState': 'active', 'Channel': 'calendar',
                     'Scope': 'opportunity', 'TargetKey': 'GC:1'}
        self.c = {'site': 'https://example-my.sharepoint.com/personal/operator',
                  'folder': '/Documents/Reporting', 'server_folder': '/personal/operator/Documents/Reporting',
                  'operator_email': 'operator@example.com', 'calendar_id': 'A' * 32,
                  'sharepoint_connection': 'existing-spo', 'outlook_connection': 'existing-outlook'}
        for key in ['registry_id', 'calendar_list_id', 'watchlist_id', 'ledger_id', 'library_id']:
            self.c[key] = '10000000-0000-4000-8000-000000000001'

    def choose(self, row=None, rules=None, source=None):
        return decision(self.day if row is None else row, self.source if source is None else source,
                        [self.rule] if rules is None else rules, user_key='7')

    def test_source_confirmed_explicit_follow_and_overlap(self):
        self.assertEqual(self.choose(), 'upsert')
        self.assertEqual(self.choose(rules=[self.rule, copy.deepcopy(self.rule)]), 'upsert')

    def test_pause_remove_and_wrong_owner_never_admitted(self):
        for change in [{'Active': False}, {'SubscriptionState': 'paused'}, {'AuthorId': 8},
                       {'UserKey': '8'}, {'Channel': 'email'}]:
            self.assertEqual(self.choose(rules=[self.rule | change]), 'remove')
        self.assertEqual(self.choose(rules=[]), 'remove')

    def test_ongoing_cancelled_uncommitted_unknown_dates(self):
        for change in [{'Calendar_x0020_day': None}, {'Calendar_x0020_day': '2026-02-30'},
                       {'Calendar_x0020_day': '2026-12-31T13:00:00Z'}, {'RevisionApplied': False}]:
            self.assertEqual(self.choose(row=self.day | change), 'hold')
        self.assertEqual(self.choose(row=self.day | {'Cancelled': True}), 'remove')
        self.assertEqual(self.choose(row=self.day | {'DeadlinePrecision': 'month'}), 'remove')

    def test_classification_uncertainty_does_not_revoke(self):
        broad = self.rule | {'Scope': 'funder', 'TargetKey': 'F1'}
        self.assertEqual(self.choose(rules=[broad]), 'hold')
        evidence = {'source_evidence_hash': 'abc', 'FunderKey': 'F1', 'CategoryKeys': ['C1']}
        source = self.source | {'ReviewStatus': 'Reviewed', 'EvidenceHash': 'abc', 'FunderKey': 'F1',
                                'CategoryKeysJSON': '["C1"]', 'ClassificationEvidenceJSON': json.dumps(evidence)}
        self.assertEqual(self.choose(rules=[broad], source=source), 'upsert')
        self.assertEqual(self.choose(rules=[broad | {'TargetKey': 'F2'}], source=source), 'remove')

    def test_wrong_source_key_and_url_hold(self):
        self.assertEqual(self.choose(source=self.source | {'Source': 'NIH'}), 'hold')
        self.assertEqual(self.choose(row=self.day | {'DeadlineKey': 'GC-CLOSE:' + 'g' * 32}), 'hold')
        self.assertEqual(self.choose(row=self.day | {'SourceURL': {'Url': 'https://example.com/'}}), 'hold')

    def test_one_serial_writer_no_invites_and_no_blind_retries(self):
        d = worker(self.c)
        self.assertEqual(d['triggers']['Changed']['runtimeConfiguration']['concurrency']['runs'], 1)
        self.assertEqual(d['actions']['Each_deadline']['runtimeConfiguration']['concurrency']['repetitions'], 1)
        serialized = json.dumps(d)
        for protection in ['No_ambiguous_retry', 'Preferences_unchanged', 'Day_unchanged',
                           'Source_unchanged', 'Provider_version', 'Claim_owned', 'Provider_result_matches']:
            self.assertIn(protection, serialized)
        def actions(value):
            if isinstance(value, dict):
                if value.get('type') == 'OpenApiConnection':
                    yield value
                for child in value.values():
                    yield from actions(child)
            elif isinstance(value, list):
                for child in value:
                    yield from actions(child)
        for action in actions(d['actions']):
            self.assertEqual(action['inputs']['retryPolicy'], {'type': 'none'})
            self.assertNotIn('SendEmail', action['inputs']['host']['operationId'])
        provider = [a['inputs']['parameters'] for a in actions(d) if a['inputs']['host']['operationId'] == 'HttpRequest'
                    and 'Uri' in a['inputs']['parameters']]
        self.assertTrue(all('/me/calendars/' in a['Uri'] for a in provider))
        self.assertTrue(all('If-Match:' in a.get('CustomHeader2', '') for a in provider if a['Method'] in ['PATCH', 'DELETE']))
        self.assertIn('%7B52a615fa', serialized)
        self.assertNotIn("id eq 'String {", serialized)

    def test_adapters_only_signal_existing_folder(self):
        for source in ['watchlist_id', 'calendar_list_id', 'registry_id']:
            d = signal_adapter(self.c, source)
            self.assertEqual(list(d['actions']), ['Signal'])
            self.assertIn('Files/Add', d['actions']['Signal']['inputs']['parameters']['parameters/uri'])
            self.assertNotIn('shared_office365', json.dumps(d))
        with self.assertRaises(ValueError):
            signal_adapter(self.c, 'ledger_id')
        self.assertIn('Guard_removed', qualification(self.c)['actions'])
