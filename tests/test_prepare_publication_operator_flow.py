# SPDX-License-Identifier: Apache-2.0
import copy
from datetime import datetime, timedelta, timezone
import unittest

from scripts.prepare_publication_operator_flow import fingerprint, prepare


FLOW = '00000000-0000-4000-8000-000000000001'
ENV = 'Default-00000000-0000-4000-8000-000000000002'
NOW = datetime(2026, 10, 15, 4, tzinfo=timezone.utc)


class OperatorFlowPreparationTests(unittest.TestCase):
    def setUp(self):
        self.definition = {
            'parameters': {'$authentication': {'type': 'SecureObject'},
                           '$connections': {'type': 'Object'}},
            'triggers': {'Recurrence': {
                'type': 'Recurrence', 'recurrence': {'frequency': 'Day', 'interval': 1},
                'evaluatedRecurrence': {'frequency': 'Day', 'interval': 1},
                'metadata': {'operationMetadataId': 'existing-trigger'},
                'runtimeConfiguration': {'concurrency': {'runs': 1}}}},
            'actions': {'Preserved_guard': {'type': 'Compose', 'inputs': '@int(1)'}},
        }
        self.readback = {
            'observed_at_utc': NOW.isoformat(),
            'flow': {'id': f'/providers/Microsoft.ProcessSimple/environments/{ENV}/flows/{FLOW}',
                     'name': FLOW, 'properties': {
                         'state': 'Stopped', 'displayName': 'Existing writer',
                         'definition': copy.deepcopy(self.definition),
                         'connectionReferences': {'sharepoint': {'source': 'Invoker',
                                                               'connectionName': 'existing'}}}},
            'run_history': {'value': [{'name': 'completed', 'properties': {'status': 'Succeeded'}}]},
        }

        self.readback.update(complete=True,capture_reference='fixture:flow-read',saved_revision='etag:"7"')
        self.readback['run_history'].update(complete=True,item_count=1,flow_id=FLOW,environment=ENV,
            observed_at_utc=NOW.isoformat(),capture_reference='fixture:history-read')

    def packet(self):
        return prepare(self.readback, flow_id=FLOW, environment=ENV,
                       expected_definition_sha256=fingerprint(self.definition), now=NOW)

    def test_only_trigger_changes_and_original_restores_exactly(self):
        before = copy.deepcopy(self.readback)
        packet = self.packet()
        manual = copy.deepcopy(packet['install']['properties']['definition'])
        trigger = manual['triggers']['Recurrence']
        self.assertEqual((trigger['type'], trigger['kind']), ('Request', 'Button'))
        self.assertNotIn('recurrence', trigger)
        self.assertNotIn('evaluatedRecurrence', trigger)
        self.assertEqual(trigger['metadata'], self.definition['triggers']['Recurrence']['metadata'])
        self.assertEqual(trigger['runtimeConfiguration'],
                         self.definition['triggers']['Recurrence']['runtimeConfiguration'])
        manual['triggers'] = self.definition['triggers']
        self.assertEqual(manual, self.definition)
        self.assertEqual(packet['restore']['properties']['definition'], self.definition)
        self.assertEqual(packet['install']['properties']['connectionReferences'],
                         before['flow']['properties']['connectionReferences'])
        self.assertEqual(self.readback, before)
        self.assertFalse(packet['activation_or_invocation_authority'])
        packet['install']['properties']['definition']['actions'].clear()
        self.assertEqual(packet['restore']['properties']['definition'], self.definition)

    def test_refuses_changed_accepted_graph(self):
        self.readback['flow']['properties']['definition']['actions']['Preserved_guard']['inputs'] = 0
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            self.packet()

    def test_refuses_wrong_target_and_started_writer(self):
        for change in ('id', 'state'):
            with self.subTest(change=change):
                altered = copy.deepcopy(self.readback)
                if change == 'id':
                    altered['flow']['id'] += '-other'
                else:
                    altered['flow']['properties']['state'] = 'Started'
                with self.assertRaises(ValueError):
                    prepare(altered, flow_id=FLOW, environment=ENV,
                            expected_definition_sha256=fingerprint(self.definition), now=NOW)

    def test_refuses_inflight_or_unknown_run_status(self):
        for status in ('Running', 'Waiting', 'NotStarted', 'Suspended', None):
            with self.subTest(status=status):
                self.readback['run_history']['value'][0]['properties']['status'] = status
                with self.assertRaisesRegex(ValueError, 'nonterminal'):
                    self.packet()

    def test_refuses_incomplete_history(self):
        self.readback['run_history']['@odata.nextLink'] = 'next-page'
        with self.assertRaisesRegex(ValueError, 'complete native run history'):
            self.packet()

    def test_refuses_stale_future_and_naive_evidence(self):
        for stamp in (NOW - timedelta(minutes=16), NOW + timedelta(seconds=1),
                      NOW.replace(tzinfo=None)):
            with self.subTest(stamp=stamp):
                self.readback['observed_at_utc'] = stamp.isoformat()
                with self.assertRaisesRegex(ValueError, 'fresh'):
                    self.packet()

    def test_refuses_missing_authentication_or_unrestorable_trigger(self):
        for change in ('authentication', 'trigger'):
            with self.subTest(change=change):
                altered = copy.deepcopy(self.readback)
                definition = altered['flow']['properties']['definition']
                if change == 'authentication':
                    del definition['parameters']['$authentication']
                else:
                    definition['triggers']['Recurrence']['unexpected'] = 'setting'
                with self.assertRaises(ValueError):
                    prepare(altered, flow_id=FLOW, environment=ENV,
                            expected_definition_sha256=fingerprint(definition), now=NOW)

    def test_malformed_control_identity_revision_and_partial_history_refused(self):
        for changes in [{'saved_revision':'update-operation:123'},{'saved_revision':'etag:*'},{'saved_revision':'etag:UPDATE-OPERATION:123'},
                        {'saved_revision':'etag:fixture'},
                        {'complete':False},{'error':{}},{'capture_reference':''}]:
            old=copy.deepcopy(self.readback);self.readback.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.packet()
            self.readback=old
        for changes in [{'item_count':True},{'item_count':0},{'complete':False},{'flow_id':'other'},
                        {'environment':'other'},{'observed_at_utc':'unknown'},{'partial':[]},
                        {'observed_at_utc':(NOW-timedelta(minutes=16)).isoformat()}]:
            old=copy.deepcopy(self.readback);self.readback['run_history'].update(changes)
            with self.subTest(history=changes),self.assertRaises(ValueError):self.packet()
            self.readback=old
        self.readback['run_history']['value']*=2;self.readback['run_history']['item_count']=2
        with self.assertRaises(ValueError):self.packet()

    def test_expected_fingerprint_and_exact_unpadded_ids_are_controls_not_inferred(self):
        for flow_id,environment,digest in [(FLOW.replace('4000','4ABC'),ENV,fingerprint(self.definition)),
                                        (' '+FLOW,ENV,fingerprint(self.definition)),
                                        (FLOW,ENV,'not-a-sha256')]:
            with self.subTest(flow=flow_id,digest=digest),self.assertRaises(ValueError):
                prepare(self.readback,flow_id=flow_id,environment=environment,expected_definition_sha256=digest,now=NOW)

    def test_cli_preserves_inputs_prior_output_and_is_portable(self):
        from scripts import prepare_publication_operator_flow as module
        from contextlib import redirect_stderr,redirect_stdout
        import io,json,tempfile,subprocess,sys
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();private=root/'private';private.mkdir()
            source=private/'capture.json';output=private/'packet.json';source.write_text(json.dumps(self.readback))
            original=source.read_bytes()
            args=['--readback',str(source),'--flow-id',FLOW,'--environment',ENV,
                  '--expected-definition-sha256',fingerprint(self.definition),'--output',str(output),'--as-of',NOW.isoformat()]
            with mock.patch.object(module,'ROOT',root),redirect_stderr(io.StringIO()),redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(args),0);saved=output.read_bytes()
                self.assertNotEqual(module.main(args),0);self.assertEqual(output.read_bytes(),saved)
                self.assertEqual(source.read_bytes(),original)
                output.unlink();source.write_text('{}');self.assertNotEqual(module.main(args),0);self.assertFalse(output.exists())
            run=subprocess.run([sys.executable,'-S','-B',str(Path(module.__file__).resolve()),'--help'],cwd=root,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)


if __name__ == '__main__':
    unittest.main()
