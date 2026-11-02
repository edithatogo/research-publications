"""One focused feature selection; fixtures never send or access a tenant."""
# SPDX-License-Identifier: Apache-2.0
import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.prepare_grants_business_notifications import build
from scripts.grants_live_delivery import dispatch_snapshot


class BusinessNotificationsTests(unittest.TestCase):
    def context(self):
        c = {'site': 'https://example-my.sharepoint.com/personal/operator',
             'operator_email': 'operator@example.invalid', 'sharepoint_connection': 'retained-spo',
             'mail_connection': 'retained-outlook'}
        for key in ['ledger_id', 'registry_id', 'watchlist_id', 'calendar_id']:
            c[key] = '10000000-0000-4000-8000-000000000001'
        return c

    def actions(self, value):
        if isinstance(value, dict):
            if 'type' in value and ('inputs' in value or 'actions' in value):
                yield value
            for child in value.values():
                yield from self.actions(child)
        elif isinstance(value, list):
            for child in value:
                yield from self.actions(child)

    def test_fixed_recipient_no_retry_and_sequential_dispatch(self):
        d = build(self.context())['definition']
        sends = [a for a in self.actions(d) if a.get('type') == 'OpenApiConnection' and a['inputs']['host']['operationId'] == 'SendEmailV2']
        self.assertEqual(len(sends), 1)
        self.assertEqual(sends[0]['inputs']['parameters']['emailMessage/To'], 'operator@example.invalid')
        self.assertEqual(sends[0]['inputs']['retryPolicy'], {'type': 'none'})
        for a in self.actions(d):
            if a['type'] == 'Foreach':
                self.assertEqual(a['runtimeConfiguration']['concurrency']['repetitions'], 1)
        self.assertEqual(d['triggers']['Due']['runtimeConfiguration']['concurrency']['runs'], 1)

    def test_qualification_cannot_dispatch(self):
        d = build(self.context(), qualification=True)['definition']
        self.assertEqual(d['actions']['Dispatch']['expression'], '@false')
        self.assertEqual(list(d['triggers']), ['manual'])
        self.assertNotIn('EventJSON', d['parameters'])

    def test_review_and_current_consent_guards_twice(self):
        s = json.dumps(build(self.context()))
        for text in ['GrantConnectRSS', 'ClassificationEvidenceJSON', 'AuthorId', 'Australia/Brisbane',
                     'Guard_current_before_send', 'Deadline_before_send', 'PreferenceVersion',
                     'SourceVersion', 'DeadlineVersion', 'Reconcile_if_needed']:
            self.assertIn(text, s)
        self.assertIn("if(equals(item()?['EventType'],'reminder')", s)
        self.assertNotIn('EVENT:WyIzIi', s)  # no template event payload retained

    def test_ledger_claim_precedes_send_and_receipt_has_exact_recipient(self):
        d = build(self.context())['definition']
        sends = [a for a in self.actions(d) if a.get('type') == 'OpenApiConnection' and a['inputs']['host']['operationId'] == 'SendEmailV2']
        self.assertEqual(sends[0]['runAfter'], {'Deadline_before_send': ['Succeeded']})
        s = json.dumps(d)
        self.assertIn("body('Claim_event')?['Id']", s)
        self.assertIn("length(item()?['toRecipients'])", s)
        self.assertIn("['Status'],'succeeded'", s)

    def test_all_scope_action_names_unique_and_dependencies_local(self):
        d = build(self.context())['definition']; seen = set()
        def walk(actions):
            for name, a in actions.items():
                self.assertNotIn(name.lower(), seen); seen.add(name.lower())
                self.assertTrue(set(a.get('runAfter', {})).issubset(actions), name)
                if 'actions' in a:
                    walk(a['actions'])
                if 'else' in a:
                    walk(a['else']['actions'])
        walk(d['actions'])

    def test_legacy_source_exclusion_preserves_operational_path(self):
        with tempfile.TemporaryDirectory() as directory:
            source = {'Source': 'GrantConnectRSS', 'ReviewStatus': 'Reviewed'}
            rows = {'registry': [source], 'calendar': [], 'watchlist': [], 'ledger': []}
            config = {'context': {'operator_email': 'operator@example.invalid'}, 'operator_user_key': '3',
                      'outbox': str(Path(directory) / 'outbox'), 'business_excluded_sources': ['GrantConnectRSS']}
            health = {'healthy': True, 'sources': []}
            with patch('scripts.grants_live_delivery.candidates', return_value=[]) as planner:
                result = dispatch_snapshot(config, rows, lambda *_: None,
                    now=datetime.fromisoformat('2026-11-02T08:00:00+10:00'), directory=directory, health=health)
            self.assertEqual(planner.call_args.args[0], [])
            self.assertEqual(result['eligible_grant_notices'], 0)
            self.assertEqual(result['operational_health_events'], 0)

    def test_invalid_legacy_ownership_config_fails_before_native(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {'context': {'operator_email': 'operator@example.invalid'}, 'operator_user_key': '3',
                      'outbox': str(Path(directory) / 'outbox'), 'business_excluded_sources': 'GrantConnectRSS'}
            with self.assertRaises(ValueError):
                dispatch_snapshot(config, {'registry': []}, lambda *_: None,
                    now=datetime.fromisoformat('2026-11-02T08:00:00+10:00'), directory=directory, health={'healthy': True})
