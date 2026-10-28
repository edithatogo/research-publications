"""Synthetic workflow rows and in-memory native transport; no service/auth use."""
# SPDX-License-Identifier: Apache-2.0
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest

from scripts.grants_conditional_definition import (
    Binding, FileJournal, prepare_save, rollback_definition, save_definition,
)


def fixture():
    binding = Binding('https://example.crm.dynamics.com', '11111111-1111-4111-8111-111111111111',
                      '22222222-2222-4222-8222-222222222222', 'offline-environment')
    definition = {'parameters': {'EventJSON': {'type': 'String', 'defaultValue': 'old-event'}},
                  'triggers': {'manual': {'type': 'Request'}}, 'actions': {'Keep': {'type': 'Compose', 'inputs': 1}}}
    connections = {'sharepoint': {'connectionName': 'synthetic-existing', 'id': 'synthetic-api'}}
    client = {'properties': {'definition': definition, 'connectionReferences': connections,
                             'other': {'preserve': [None, 'Unicode α', {'future': True}]}},
              'unknown_top_level': ['retained', 7]}
    row = {'workflowid': binding.workflow_id, '@odata.etag': 'W/"before"', 'name': 'Offline only',
           'clientdata': json.dumps(client, ensure_ascii=False, indent=2), 'statecode': 0, 'statuscode': 1,
           'versionnumber': 1, 'modifiedon': '2026-10-29T00:00:00Z', 'unrelated_field': {'keep': True}}
    flow = {'name': binding.flow_id, 'id': binding.flow_url.split('.com', 1)[1], 'properties': {
        'workflowEntityId': binding.workflow_id, 'definition': copy.deepcopy(definition),
        'connectionReferences': copy.deepcopy(connections), 'state': 'Stopped', 'flowFailureAlertSubscribed': False}}
    metadata = {'LogicalName': 'workflow', 'IsOptimisticConcurrencyEnabled': True}
    candidate = copy.deepcopy(definition)
    candidate['parameters']['EventJSON']['defaultValue'] = 'frozen-new-event'
    plan = prepare_save(operation_id='fixed-offline-event', owner='synthetic-exclusive-owner',
                        binding=binding, metadata=metadata, row=row, flow=flow, definition=candidate)
    return binding, row, flow, metadata, candidate, plan


class FakeTransport:
    def __init__(self, fixture_data):
        self.binding, self.row, self.flow, self.metadata, _, _ = copy.deepcopy(fixture_data)
        self.calls = []
        self.patch_fault = None
        self.readback_fault = None
        self.version = 1

    @property
    def patches(self):
        return [call for call in self.calls if call['method'] == 'PATCH']

    def __call__(self, **request):
        self.calls.append(copy.deepcopy(request))
        assert request['max_redirects'] == 0 and request['retries'] == 0 and request['timeout_seconds'] == 30
        assert request['method'] in ['GET', 'PATCH'], 'No invocation/send transport exists'
        url = request['url']
        if request['method'] == 'GET':
            if url == self.binding.metadata_url:
                return {'status': 200, 'body': copy.deepcopy(self.metadata)}
            if url == self.binding.row_url:
                row = copy.deepcopy(self.row)
                if self.patches and self.readback_fault == 'clientdata':
                    value = json.loads(row['clientdata']);value['unknown_top_level'] = ['unexpected'];row['clientdata'] = json.dumps(value)
                return {'status': 200, 'body': row}
            assert url == self.binding.flow_url + '?api-version=2016-11-01'
            flow = copy.deepcopy(self.flow)
            if self.patches and self.readback_fault in ['connections', 'state', 'alerts', 'identity']:
                key = {'connections': 'connectionReferences', 'state': 'state', 'alerts': 'flowFailureAlertSubscribed', 'identity': 'workflowEntityId'}[self.readback_fault]
                flow['properties'][key] = 'unexpected'
            return {'status': 200, 'body': flow}
        assert url == self.binding.row_url
        assert set(request['body']) == {'clientdata'}
        if self.patch_fault == '412':
            return {'status': 412, 'body': {}}
        if self.patch_fault == 'concurrent':
            self.row['@odata.etag'] = 'W/"competitor"'
            self.row['unrelated_field'] = {'other-owner': True}
        if request['headers']['If-Match'] != self.row['@odata.etag']:
            return {'status': 412, 'body': {}}
        self.row['clientdata'] = request['body']['clientdata']
        self.version += 1;self.row['@odata.etag'] = f'W/"revision-{self.version}"'
        self.row['versionnumber'] = self.version
        self.flow['properties']['definition'] = json.loads(self.row['clientdata'])['properties']['definition']
        if self.patch_fault == 'lost':
            raise TimeoutError('Synthetic lost response after server save')
        return {'status': 204, 'body': None}


class ConditionalDefinitionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.journal = FileJournal(self.directory.name)
        self.data = fixture();self.plan = self.data[-1];self.transport = FakeTransport(self.data)

    def save(self):
        return save_definition(self.plan, transport=self.transport, journal=self.journal)

    def rollback(self):
        return rollback_definition(self.plan, transport=self.transport, journal=self.journal)

    def test_exact_conditional_save_preserves_every_non_definition_value(self):
        before = copy.deepcopy(self.data[1]);original_flow = copy.deepcopy(self.data[2])
        result = self.save()
        self.assertEqual(result['status'], 'saved');self.assertFalse(result['invocation_allowed'])
        self.assertEqual(len(self.transport.patches), 1)
        request = self.transport.patches[0]
        self.assertEqual(request['headers']['If-Match'], before['@odata.etag'])
        old_client = json.loads(before['clientdata']);new_client = json.loads(self.transport.row['clientdata'])
        old_client['properties']['definition'] = self.data[4]
        self.assertEqual(old_client, new_client)
        self.assertEqual(self.transport.flow['properties']['connectionReferences'], original_flow['properties']['connectionReferences'])
        self.assertEqual(self.transport.row['statecode'], before['statecode'])
        self.assertEqual(self.data[1], before)
        self.assertTrue(self.journal.contains(self.plan.journal_key, 'save-intent'))

    def test_second_instance_cannot_repeat_a_verified_or_uncertain_intent(self):
        for fault in [None, '412', 'lost']:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                journal = FileJournal(directory);transport = FakeTransport(self.data);transport.patch_fault = fault
                save_definition(self.plan, transport=transport, journal=journal)
                count = len(transport.calls)
                result = save_definition(self.plan, transport=transport, journal=FileJournal(directory))
                self.assertEqual(result['status'], 'quarantined');self.assertEqual(len(transport.patches), 1)
                self.assertEqual(len(transport.calls), count)

    def test_stale_preimage_and_foreign_binding_stop_before_patch(self):
        for field, value in [('@odata.etag', 'W/"newer"'), ('unrelated_field', {'other-owner': True}), ('workflowid', self.data[0].flow_id)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                transport = FakeTransport(self.data);transport.row[field] = value
                result = save_definition(self.plan, transport=transport, journal=FileJournal(directory))
                self.assertEqual(result['status'], 'quarantined');self.assertFalse(transport.patches)

    def test_412_and_concurrent_edit_remain_quarantined_without_unconditional_fallback(self):
        for fault in ['412', 'concurrent']:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                transport = FakeTransport(self.data);transport.patch_fault = fault
                result = save_definition(self.plan, transport=transport, journal=FileJournal(directory))
                self.assertEqual(result['reason'], 'precondition_failed');self.assertFalse(result['invocation_allowed'])
                self.assertEqual(len(transport.patches), 1)
                if fault == 'concurrent':self.assertEqual(transport.row['unrelated_field'], {'other-owner': True})

    def test_lost_response_retains_intent_and_requires_separate_reconciliation(self):
        self.transport.patch_fault = 'lost';result = self.save()
        self.assertEqual(result['reason'], 'save_transport_uncertain')
        self.assertEqual(json.loads(self.transport.row['clientdata']), json.loads(self.plan.candidate_clientdata))
        count = len(self.transport.calls);rollback = self.rollback()
        self.assertEqual(rollback['reason'], 'verified_owned_save_required')
        self.assertEqual(len(self.transport.calls), count)

    def test_row_or_flow_readback_mismatch_never_certifies_definition_or_rollback(self):
        for fault in ['clientdata', 'connections', 'state', 'alerts', 'identity']:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                transport = FakeTransport(self.data);transport.readback_fault = fault;journal = FileJournal(directory)
                result = save_definition(self.plan, transport=transport, journal=journal)
                self.assertEqual(result['status'], 'quarantined');self.assertFalse(result['invocation_allowed'])
                self.assertEqual(rollback_definition(self.plan, transport=transport, journal=journal)['reason'], 'verified_owned_save_required')
                self.assertEqual(len(transport.patches), 1)

    def test_rollback_uses_fresh_etag_and_restores_exact_original_clientdata(self):
        self.assertEqual(self.save()['status'], 'saved')
        self.transport.row['@odata.etag'] = 'W/"fresh-noop-revision"'
        result = self.rollback()
        self.assertEqual(result['status'], 'rolled_back')
        self.assertEqual(self.transport.patches[-1]['headers']['If-Match'], 'W/"fresh-noop-revision"')
        self.assertEqual(self.transport.row['clientdata'], self.data[1]['clientdata'])
        self.assertEqual(self.transport.flow, self.data[2]);self.assertEqual(len(self.transport.patches), 2)
        count = len(self.transport.calls);self.assertEqual(self.rollback()['status'], 'quarantined')
        self.assertEqual(len(self.transport.calls), count)

    def test_rollback_refuses_to_overwrite_concurrent_candidate_edits(self):
        self.assertEqual(self.save()['status'], 'saved')
        client = json.loads(self.transport.row['clientdata']);client['properties']['connectionReferences'] = {'other-owner': {}}
        self.transport.row['clientdata'] = json.dumps(client)
        self.assertEqual(self.rollback()['reason'], 'preimage_changed');self.assertEqual(len(self.transport.patches), 1)

    def test_rollback_race_and_lost_response_have_one_durable_attempt(self):
        for fault in ['concurrent', 'lost']:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                transport = FakeTransport(self.data);journal = FileJournal(directory)
                self.assertEqual(save_definition(self.plan, transport=transport, journal=journal)['status'], 'saved')
                transport.patch_fault = fault
                result = rollback_definition(self.plan, transport=transport, journal=journal)
                self.assertEqual(result['status'], 'quarantined');self.assertEqual(len(transport.patches), 2)
                rollback_definition(self.plan, transport=transport, journal=journal)
                self.assertEqual(len(transport.patches), 2)

    def test_native_prerequisites_and_etag_are_required_without_transport(self):
        binding,row,flow,metadata,definition,_ = self.data
        for bad_metadata in [{}, {**metadata, 'IsOptimisticConcurrencyEnabled': False}, {**metadata, 'IsOptimisticConcurrencyEnabled': 1}]:
            with self.assertRaises(ValueError):prepare_save(operation_id='offline', owner='owner', binding=binding, metadata=bad_metadata, row=row, flow=flow, definition=definition)
        for etag in ['*', '', 'W/"bad\nheader"', 'W/"bad\theader"', None]:
            with self.assertRaises(ValueError):prepare_save(operation_id='offline', owner='owner', binding=binding, metadata=metadata, row={**row,'@odata.etag':etag}, flow=flow, definition=definition)
        self.transport.metadata['IsOptimisticConcurrencyEnabled'] = False
        self.assertEqual(self.save()['reason'], 'preflight_unqualified');self.assertFalse(self.transport.patches)

    def test_corrupt_plan_cannot_modify_non_definition_clientdata(self):
        value = json.loads(self.plan.candidate_clientdata);value['unknown_top_level'] = 'overwrite'
        altered = replace(self.plan, candidate_clientdata=json.dumps(value))
        with self.assertRaises(ValueError):save_definition(altered, transport=self.transport, journal=self.journal)
        self.assertEqual(self.transport.calls, [])

    def test_two_contenders_share_one_exclusive_intent(self):
        barrier = threading.Barrier(2)
        local = threading.local()
        def transport(**request):
            response = self.transport(**request)
            if request['method'] == 'GET' and request['url'].startswith(self.data[0].flow_url) and not getattr(local, 'initial_read', False):
                local.initial_read = True
                barrier.wait(timeout=5)
            return response
        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(save_definition, self.plan, transport=transport,
                                      journal=FileJournal(self.directory.name)) for _ in range(2)]
            results = [f.result(timeout=10) for f in futures]
        self.assertEqual(sorted(r['status'] for r in results), ['quarantined', 'saved'])
        self.assertEqual(len(self.transport.patches), 1)

    def test_failed_readback_and_missing_revision_change_are_quarantined(self):
        for fault in ['readback_unavailable', 'unchanged_etag']:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                fake = FakeTransport(self.data)
                def transport(**request):
                    result = fake(**request)
                    if fake.patches and request['method'] == 'GET' and request['url'] == fake.binding.row_url:
                        if fault == 'readback_unavailable':raise TimeoutError('synthetic read timeout')
                        result['body']['@odata.etag'] = self.data[1]['@odata.etag']
                    return result
                result = save_definition(self.plan, transport=transport, journal=FileJournal(directory))
                self.assertEqual(result['status'], 'quarantined')
                self.assertFalse(result['invocation_allowed']);self.assertEqual(len(fake.patches), 1)

    def test_nondurable_intent_never_reaches_transport_patch(self):
        class BrokenJournal(FileJournal):
            def write_once(self, *args):raise OSError('synthetic disk full')
        with self.assertRaises(OSError):save_definition(self.plan, transport=self.transport, journal=BrokenJournal(self.directory.name))
        self.assertFalse(self.transport.patches)

    def test_outcome_storage_failure_is_quarantined_and_never_replayed(self):
        class BrokenOutcomeJournal(FileJournal):
            def write_once(self, key, label, value):
                if label.endswith('-outcome'):raise OSError('synthetic outcome storage failure')
                return super().write_once(key, label, value)
        journal = BrokenOutcomeJournal(self.directory.name)
        result = save_definition(self.plan, transport=self.transport, journal=journal)
        self.assertEqual(result['reason'], 'receipt_write_failed')
        self.assertEqual(result['status'], 'quarantined')
        count = len(self.transport.calls)
        self.assertEqual(save_definition(self.plan, transport=self.transport, journal=journal)['status'], 'quarantined')
        self.assertEqual(rollback_definition(self.plan, transport=self.transport, journal=journal)['reason'], 'verified_owned_save_required')
        self.assertEqual(len(self.transport.calls), count);self.assertEqual(len(self.transport.patches), 1)

    def test_journal_preserves_an_existing_intent_and_private_file_mode(self):
        self.save();key=self.plan.journal_key
        original=self.journal.read(key,'save-intent')
        with self.assertRaises(FileExistsError):self.journal.write_once(key,'save-intent',{'overwrite':True})
        self.assertEqual(self.journal.read(key,'save-intent'),original)
        file=next(Path(self.directory.name).glob('*-save-intent.json'))
        self.assertEqual(file.stat().st_mode & 0o777,0o600)


if __name__ == '__main__':unittest.main()
