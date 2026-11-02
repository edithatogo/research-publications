"""Synthetic policy/evidence fixtures; never approve or mutate native records."""
# SPDX-License-Identifier: Apache-2.0
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.grants_internal_deadlines import FORMAT, canonical, key, plan
from scripts.prepare_grants_policy_inspection import build


class InternalDeadlineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        evidence = Path(self.temp.name) / 'fictional-policy.txt'
        evidence.write_text('FICTIONAL TEST ONLY: not an institutional policy')
        self.digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
        self.files = {self.digest: str(evidence)}
        self.policy = {'PolicyKey': 'TEST_ONLY', 'Version': '1', 'OrganisationKey': 'FIXTURE',
            'AnchorKind': 'final', 'LeadDays': 5, 'CalendarOrBusinessDays': 'calendar',
            'HolidayCalendarVersion': 'not-used', 'EffectiveFrom': '2026-01-01'}
        self.authority = {'Status': 'Approved', 'DocumentID': 'FICTIONAL TEST ONLY',
            'DocumentVersion': '1', 'SourceURL': 'https://example.invalid/policy',
            'EvidenceSHA256': self.digest, 'ApprovedBy': 'fictional-curator',
            'ApprovedAtUTC': '2026-01-01T00:00:00Z'}
        self.deadline = 'GC-CLOSE:' + 'a' * 32
        url = {'Url': 'https://www.grants.gov.au/Go/Show?GoUuid=fictional'}
        self.snapshot = {'policies': [], 'overrides': [],
            'registry': [{'OpportunityKey': 'GRANT:fixture', 'Source': 'GrantConnectRSS', 'URL': url, 'EvidenceHash': 'b' * 64}],
            'calendar': [{'DeadlineKey': self.deadline, 'OpportunityKey': 'GRANT:fixture',
                'SourceURL': url, 'RevisionApplied': True, 'ReviewStatus': 'Source confirmed',
                'Calendar_x0020_day': '2026-12-31', 'DeadlinePrecision': 'day', 'Cancelled': False,
                'Revision': 'source-v1', 'odata.etag': '"1"'}]}

    def record(self, **changes):
        p = self.policy | changes
        envelope = {'SchemaVersion': FORMAT, 'Policy': p, 'Authority': self.authority | {
            'PolicySHA256': hashlib.sha256(canonical(p).encode()).hexdigest()},
            'Scope': {'Sources': ['GrantConnectRSS'], 'OpportunityKeys': []}}
        return {'Id': 1, 'PolicyVersionKey': key('POLICY:', [p['PolicyKey'], p['Version']]),
                'PolicyJson': json.dumps(envelope), 'odata.etag': '"1"'}

    def test_policy_append_is_create_only_and_requires_exact_readback(self):
        from scripts.grants_policy_append import prepare
        context = {'policy_id':'00000000-0000-0000-0000-000000000001','site':'https://example.invalid','sharepoint_connection':'fixture'}
        actions = prepare(context,self.record(),'FIXTURE',self.files)['definition']['actions']
        create = actions['Append']['actions']['Create']['inputs']
        self.assertEqual(create['parameters']['parameters/method'],'POST')
        self.assertEqual(create['retryPolicy'],{'type':'none'})
        self.assertFalse(actions['Append']['else']['actions'])
        self.assertIn('PolicyJson',str(actions['Exact']))
        self.assertEqual(prepare(context,{'PolicyJson':'{}'},'FIXTURE',{})['disposition'],'held')

    def run_plan(self):
        return plan(self.snapshot, organisation='FIXTURE', as_of='2026-11-02', evidence_files=self.files)

    def test_missing_legacy_or_unapproved_policy_never_creates_internal_date(self):
        self.assertEqual(self.run_plan()['held'][0]['Reason'], 'approved_policy_missing')
        self.snapshot['policies'] = [{'PolicyVersionKey': 'TEST_ONLY:old', 'PolicyJson': json.dumps(self.policy)}]
        self.assertEqual(self.run_plan()['rows'], [])
        r = self.record(); e = json.loads(r['PolicyJson']); e['Authority']['Status'] = 'Draft'; r['PolicyJson'] = json.dumps(e)
        self.snapshot['policies'] = [r]; self.assertEqual(self.run_plan()['rows'], [])

    def test_calendar_policy_identity_provenance_and_source_immutability(self):
        self.snapshot['policies'] = [self.record()]; before = copy.deepcopy(self.snapshot)
        result = self.run_plan(); row = result['rows'][0]
        self.assertEqual(row['CalculatedDate'], '2026-12-26')
        self.assertEqual(row['EffectiveDate'], '2026-12-26')
        self.assertTrue(row['DeadlineKey'].startswith('INTERNAL:'))
        self.assertEqual(self.snapshot, before)
        self.assertFalse(result['native_submission_allowed'])
        self.snapshot['calendar'][0]['odata.etag'] = '"2"'
        self.snapshot['policies'][0]['odata.etag'] = '"2"'
        self.assertEqual(self.run_plan()['rows'][0]['Revision'], row['Revision'])

    def test_original_evidence_and_rule_binding_cannot_drift(self):
        r = self.record(); self.snapshot['policies'] = [r]
        with self.assertRaises(ValueError):
            plan(self.snapshot, organisation='FIXTURE', as_of='2026-11-02', evidence_files={})
        e = json.loads(r['PolicyJson']); e['Policy']['LeadDays'] = 10; r['PolicyJson'] = json.dumps(e)
        with self.assertRaises(ValueError): self.run_plan()
        self.snapshot['policies'] = [self.record()]
        Path(self.files[self.digest]).write_text('Changed original')
        with self.assertRaises(ValueError): self.run_plan()

    def test_business_holiday_capture_and_coverage_required(self):
        holiday = Path(self.temp.name) / 'fictional-holidays.txt'; holiday.write_text('FICTIONAL: 2026-12-25')
        digest = hashlib.sha256(holiday.read_bytes()).hexdigest(); self.files[digest] = str(holiday)
        self.snapshot['policies'] = [self.record(LeadDays=1, CalendarOrBusinessDays='business',
            HolidayCalendarVersion='fixture-2026', HolidayDates=['2026-12-25'], HolidayCoverage={
                'CalendarVersion': 'fixture-2026', 'SourceID': 'fixture', 'SourceURL': 'https://example.invalid/holidays',
                'ObservedAtUTC': '2026-01-01T00:00:00Z', 'CoverageStart': '2026-01-01',
                'CoverageEnd': '2026-12-31', 'CoverageVerified': True, 'EvidenceSHA256': digest})]
        self.snapshot['calendar'][0]['Calendar_x0020_day'] = '2026-12-28'
        self.assertEqual(self.run_plan()['rows'][0]['CalculatedDate'], '2026-12-24')
        holiday.write_text('changed')
        with self.assertRaises(ValueError): self.run_plan()

    def test_overlapping_expired_and_unknown_source_dates_fail_closed(self):
        self.snapshot['policies'] = [self.record(), self.record(Version='2')]
        with self.assertRaises(ValueError): self.run_plan()
        self.snapshot['policies'] = [self.record(EffectiveTo='2026-10-31')]
        self.assertEqual(self.run_plan()['rows'], [])
        self.snapshot['policies'] = [self.record()]
        self.snapshot['calendar'][0]['DeadlinePrecision'] = 'month'
        self.assertEqual(self.run_plan()['rows'], [])

    def test_stale_override_is_retained_and_effective_date_withheld(self):
        self.snapshot['policies'] = [self.record()]
        basis = json.dumps([self.deadline, 'TEST_ONLY', '1', 1], separators=(',', ':'))
        override = {'OverrideKey': 'OVERRIDE:' + hashlib.sha256(basis.encode()).hexdigest()[:24],
            'OverrideRevision': 1, 'AnchorDeadlineKey': self.deadline, 'AnchorDate': '2026-12-30',
            'AnchorPrecision': 'day', 'PolicyKey': 'TEST_ONLY', 'PolicyVersion': '1',
            'CalculatedDate': '2026-12-25', 'OverrideDate': '2026-12-24',
            'OverrideReason': 'FICTIONAL TEST ONLY', 'ReviewStatus': 'Reviewed', 'RecordedAtUTC': '2026-11-01T00:00:00Z'}
        self.snapshot['overrides'] = [{'OverrideJson': json.dumps(override)}]
        before = copy.deepcopy(self.snapshot); result = self.run_plan()
        self.assertTrue(result['rows'][0]['NeedsOverrideReview'])
        self.assertIsNone(result['rows'][0]['EffectiveDate'])
        self.assertTrue(result['override_assessments'][0]['Stale'])
        self.assertEqual(self.snapshot, before)

    def test_native_inspection_has_no_write_or_scheduled_trigger(self):
        c = {'site': 'https://example-my.sharepoint.com/personal/test', 'operator_email': 'test@example.invalid',
             'sharepoint_connection': 'existing'}
        for k in ['policy_id', 'override_id', 'calendar_id', 'registry_id']:
            c[k] = '10000000-0000-4000-8000-000000000001'
        d = build(c)['definition']; self.assertEqual(list(d['triggers']), ['manual'])
        for action in d['actions'].values():
            if action['type'] == 'OpenApiConnection':
                self.assertEqual(action['inputs']['parameters']['parameters/method'], 'GET')
        self.assertNotIn('SendEmail', json.dumps(d))
