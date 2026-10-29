# SPDX-License-Identifier: Apache-2.0
"""Synthetic offline writer diagnostics; no activation or capture."""
import copy
import json
from pathlib import Path
import unittest
from scripts import preflight_publication_flow_activation as preflight
from scripts import prepare_publication_registry_bootstrap as core
from tests.test_prepare_publication_registry_bootstrap import metadata_snapshot,guid


def target():
    s=metadata_snapshot()
    return dict(site_url=s['site_url'],list_id=s['list_id'],model_id=guid(501),workspace_id=guid(502),flow_id=guid(503),environment=guid(504))


def writer_fixture():
    t=target();document=json.loads((Path(__file__).parents[1]/'config/flows/publication-registry-upsert.definition.json').read_bytes())
    def visit(node):
        if not isinstance(node,dict):return
        inputs=node.get('inputs',{})
        if isinstance(inputs,dict):
            params=inputs.get('parameters',{});host=inputs.get('host',{})
            if host.get('apiId','').endswith('shared_sharepointonline'):
                if 'dataset' in params:params['dataset']=t['site_url']
                if 'table' in params:params['table']=t['list_id']
            for key,value in (('datasetid',t['model_id']),('groupid',t['workspace_id'])):
                if key in params:params[key]=value
        for value in node.values():
            if isinstance(value,dict):visit(value)
    definition=document['properties']['definition'];visit(definition)
    document.update(id=f"/providers/Microsoft.ProcessSimple/environments/{t['environment']}/flows/{t['flow_id']}",name=t['flow_id'])
    document['properties'].update(state='Stopped',connectionReferences={'fixture':{'connectionName':'fictional'}})
    return dict(complete=True,capture_reference='fixture:writer',observed_at_utc='2026-10-29T00:00:00Z',saved_revision='version:1.0',flow=document,
        run_history=dict(complete=True,capture_reference='fixture:run-history',observed_at_utc='2026-10-29T00:00:00Z',item_count=0,value=[],flow_id=t['flow_id'],environment=t['environment']))


class PreflightTests(unittest.TestCase):
    def assess(self,w=None,s=None):
        w=writer_fixture() if w is None else w;s=metadata_snapshot() if s is None else s
        return preflight.assess(w,s,target(),expected_writer_sha256=core.sha(w))

    def test_canonical_pilot_gaps_are_explicit_despite_structural_success(self):
        result=self.assess();self.assertEqual(result['structural_errors'],[])
        required={'pilot_topn_100','missing_rows_coalesced_to_empty','inferred_dora_source_key','missing_complete_batch_guard','missing_full_title_protection','missing_conditional_etag_protection','legacy_needs_review_policy'}
        self.assertTrue(required<=set(result['blockers']));self.assertFalse(result['writer_ready']);self.assertFalse(result['write_authorized']);self.assertFalse(result['native_acceptance'])

    def test_changed_preimage_target_or_nonterminal_writer_is_rejected(self):
        for fault in ('pin','target','state','run','revision','partial'):
            w=writer_fixture();s=metadata_snapshot();pin=core.sha(w)
            if fault=='pin':w['capture_reference']='changed'
            elif fault=='target':w['flow']['properties']['definition']['actions']['Run_publication_rows_query']['inputs']['parameters']['datasetid']=guid(999)
            elif fault=='state':w['flow']['properties']['state']='Started'
            elif fault=='run':w['run_history'].update(item_count=1,value=[dict(name='run',properties={'status':'Running'})])
            elif fault=='revision':w['saved_revision']='etag:*'
            else:w['complete']=False
            if fault!='pin':pin=core.sha(w)
            with self.subTest(fault=fault),self.assertRaises(ValueError):preflight.assess(w,s,target(),expected_writer_sha256=pin)

    def test_guard_names_and_policy_literal_cannot_imply_qualified_semantics(self):
        w=writer_fixture();a=w['flow']['properties']['definition']['actions'];a['Condition_Publication_Row_Count']={'type':'Compose','inputs':'unqualified'};a['Condition_Invalid_SourceKeys']={'type':'Compose','inputs':'unqualified'};a['Apply_to_each_Publication']['actions']['Compose_SourceKey_Required']={'type':'Compose','inputs':'unqualified'}
        a['Apply_to_each_Publication']['actions']['Condition_Is_New_Publication']['actions']['SharePoint_Create_item']['inputs']['parameters']['item/field_17']='Included'
        result=self.assess(w);self.assertFalse(result['writer_ready']);self.assertIn('complete_batch_semantics_unqualified',result['blockers']);self.assertIn('writer_profile_not_qualified',result['blockers'])

    def test_assessment_preserves_every_supplied_property(self):
        w=writer_fixture();s=metadata_snapshot();original=copy.deepcopy((w,s));self.assess(w,s);self.assertEqual((w,s),original)

    def test_cli_exclusive_strict_private_readback_and_hashes(self):
        import contextlib,io,tempfile
        from unittest.mock import patch
        w=writer_fixture();s=metadata_snapshot()
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stderr(io.StringIO()):
            root=Path(directory).resolve();private=root/'private';private.mkdir()
            for name,value in dict(writer=w,registry=s,target=target()).items():(private/(name+'.json')).write_text(json.dumps(value))
            args=[v for name in ('writer','registry','target') for v in ('--'+name,str(private/(name+'.json')))]+['--expected-writer-sha256',core.sha(w),'--output',str(private/'report.json')]
            with patch.object(preflight,'ROOT',root):
                self.assertEqual(preflight.main(args),0);out=private/'report.json';raw=out.read_bytes();report=json.loads(raw)
                self.assertFalse(report['result']['writer_ready']);self.assertEqual(report['source_files_sha256']['writer'],core.bytes_sha((private/'writer.json').read_bytes()))
                self.assertEqual(preflight.main(args),2);self.assertEqual(out.read_bytes(),raw)
                args[-1]=str(private/'other.json');(private/'writer.json').write_text('{"complete":true,"complete":false}')
                self.assertEqual(preflight.main(args),2);self.assertFalse((private/'other.json').exists())

    def test_malformed_headers_missing_bindings_and_history_capture_fail_closed(self):
        for fault in ('headers','table','history','status'):
            w=writer_fixture();a=w['flow']['properties']['definition']['actions'];p=a['Apply_to_each_Publication']['actions']['SharePoint_Get_items']['inputs']['parameters']
            if fault=='headers':p['parameters/headers']=[]
            elif fault=='table':p.pop('table')
            elif fault=='history':w['run_history'].pop('capture_reference')
            else:w['run_history'].update(item_count=1,value=[dict(name='run',properties={'status':[]})])
            with self.subTest(fault=fault),self.assertRaises(ValueError):self.assess(w)


def standard_fixture():
    w = writer_fixture(); props = w['flow']['properties']; definition = props['definition']
    bi = '/providers/Microsoft.PowerApps/apis/shared_powerbi'
    sp = '/providers/Microsoft.PowerApps/apis/shared_sharepointonline'
    props['connectionReferences'] = {
        'shared_powerbi': dict(id=bi, connectionName='fictional-bi'),
        'shared_sharepointonline': dict(id=sp, connectionName='fictional-sp')}
    definition['actions']['Run_publication_rows_query']['inputs']['host']['apiId'] = bi
    loop = ['actions', 'Apply_to_each_Publication', 'actions']
    new = loop + ['Condition_Is_New_Publication']
    paths = [
        ['triggers', 'Recurrence'], ['actions', 'Run_a_query_against_a_dataset'],
        ['actions', 'Run_publication_rows_query'], ['actions', 'Apply_to_each_Publication'],
        loop + ['SharePoint_Get_items'], loop + ['Condition_Duplicate_SourceKey'],
        loop + ['Condition_Duplicate_SourceKey', 'actions', 'Compose_Duplicate_SourceKey_Failure'],
        new, new + ['actions', 'SharePoint_Create_item'],
        new + ['else', 'actions', 'Condition_Exactly_One_Publication'],
        new + ['else', 'actions', 'Condition_Exactly_One_Publication', 'actions', 'SharePoint_Update_item']]
    inventory = []
    for path in sorted(paths):
        node = definition
        for segment in path: node = node[segment]
        inputs = node.get('inputs'); host = inputs.get('host', {}) if isinstance(inputs, dict) else {}
        inventory.append(dict(path=path, node_type=node['type'], api_id=host.get('apiId'),
            operation_id=host.get('operationId'), connection_reference=host.get('connectionName'),
            node_sha256=core.sha(node)))
    policy = dict(kind='publication_standard_workload_policy_v1', version='fixture:v1',
        reference='fixture:human-no-premium', power_automate_premium=False,
        power_bi_entitlement='not_power_automate_evidence', custom_connectors_allowed=False,
        allowed_classes=['BuiltIn', 'Standard'])
    classifications = [dict(operation=copy.deepcopy(row), classification='Standard' if row['api_id'] else 'BuiltIn',
        version='fixture:catalog-v1', reference='fixture:classification-not-authenticated',
        source_sha256='a' * 64, operation_schema_sha256='b' * 64) for row in inventory]
    evidence = dict(kind='publication_standard_connector_evidence_v1', complete=True,
        scope=dict(writer_sha256=core.sha(w), target_sha256=core.sha(target()),
            saved_revision=w['saved_revision'], connection_references_sha256=core.sha(props['connectionReferences'])),
        policy=policy, inventory=inventory, classifications=classifications)
    return w, evidence


def evidence_pins(w, evidence):
    return dict(evidence=core.sha(evidence), writer=core.sha(w), target=core.sha(target()),
        revision=core.sha(w['saved_revision']),
        connection_references=core.sha(w['flow']['properties']['connectionReferences']),
        policy=core.sha(evidence['policy']), inventory=core.sha(evidence['inventory']),
        classifications=core.sha(evidence['classifications']))


def assess_standard(w, evidence, pins=None):
    return preflight.assess(w, metadata_snapshot(), target(), expected_writer_sha256=core.sha(w),
        standard_evidence=evidence, standard_pins=evidence_pins(w, evidence) if pins is None else pins)


class StandardEvidenceTests(unittest.TestCase):
    def test_default_frozen_receipt_is_unchanged(self):
        w = writer_fixture()
        result = preflight.assess(w, metadata_snapshot(), target(), expected_writer_sha256=core.sha(w))
        # Frozen receipt from verified PR72's original implementation and fixture.
        self.assertEqual(core.sha(result), 'd8e6c8b2bb7150cb5acd1e6ba0869791d400d1d423fe104d1e34a1db1202ec4a')

    def test_complete_supplied_standard_evidence_preserves_existing_blockers_and_no_authority(self):
        w, evidence = standard_fixture(); before = copy.deepcopy((w, evidence))
        baseline = preflight.assess(w, metadata_snapshot(), target(), expected_writer_sha256=core.sha(w))
        try: result = assess_standard(w, evidence)
        except TypeError as exc: self.fail('Supplied Standard evidence profile is missing: ' + str(exc))
        self.assertEqual((w, evidence), before)
        self.assertTrue(set(baseline['blockers']) <= set(result['blockers']))
        for flag in ('writer_ready', 'activation_permitted', 'diagnostic_run_permitted', 'write_authorized', 'native_acceptance'):
            self.assertIs(result[flag], False)
        supplied = result['standard_connector_evidence']
        self.assertEqual(supplied['policy_blockers'], [])
        self.assertEqual(len(supplied['operations']), 11)
        self.assertFalse(supplied['claims_authenticated'])
        self.assertFalse(supplied['licensing_qualified'])
        self.assertEqual(supplied['supplied_evidence'], evidence)
        self.assertEqual(result, assess_standard(w, evidence))

    def test_every_independent_pin_and_target_revision_scope_is_enforced(self):
        w, evidence = standard_fixture()
        for name in evidence_pins(w, evidence):
            pins = evidence_pins(w, evidence); pins[name] = '0' * 64
            with self.subTest(pin=name), self.assertRaisesRegex(ValueError, 'pin differs'):
                assess_standard(w, evidence, pins)
        for name in evidence['scope']:
            w, evidence = standard_fixture(); evidence['scope'][name] = 'rebound'
            with self.subTest(scope=name), self.assertRaisesRegex(ValueError, 'scope differs'):
                assess_standard(w, evidence)

    def test_premium_custom_unknown_and_missing_classifications_stay_blocking(self):
        for classification in ('Premium', 'Custom', 'Unknown', None):
            w, evidence = standard_fixture()
            entry = next(e for e in evidence['classifications'] if e['operation']['operation_id'] == 'PostItem')
            if classification is None:evidence['classifications'].remove(entry)
            else:entry['classification'] = classification
            result = assess_standard(w, evidence)
            rows = result['standard_connector_evidence']['operations']
            row = next(r for r in rows if r['operation']['operation_id'] == 'PostItem')
            expected = 'Unknown' if classification is None else classification
            self.assertEqual(row['classification'], expected)
            self.assertIn('disallowed_classification:' + expected, row['blockers'])
            if classification is None:self.assertIn('missing_classification', row['blockers'])
            self.assertFalse(result['activation_permitted'])

    def test_connection_rebinding_unknown_and_unused_references_do_not_qualify(self):
        for fault in ('api', 'missing', 'name', 'name_type', 'name_expression', 'name_placeholder', 'unused'):
            w, evidence = standard_fixture(); refs = w['flow']['properties']['connectionReferences']
            if fault == 'api':refs['shared_powerbi']['id'] = '/other/providers/shared_powerbi'
            elif fault == 'missing':refs.pop('shared_powerbi')
            elif fault == 'name':refs['shared_powerbi']['connectionName'] = ''
            elif fault == 'name_type':refs['shared_powerbi']['connectionName'] = ['not a static identity']
            elif fault == 'name_expression':refs['shared_powerbi']['connectionName'] = '@parameters("connection")'
            elif fault == 'name_placeholder':refs['shared_powerbi']['connectionName'] = '{{CONNECTION_NAME}}'
            else:refs['unused'] = dict(id='/fixture/unknown', connectionName='unqualified')
            evidence['scope'].update(writer_sha256=core.sha(w), connection_references_sha256=core.sha(refs))
            result = assess_standard(w, evidence)['standard_connector_evidence']
            expected = 'unused_connection_reference' if fault == 'unused' else 'unresolved_connection_reference'
            self.assertIn(expected, result['policy_blockers'])
            self.assertEqual({r['reference']:r['captured'] for r in result['connections']}, refs)

    def test_incomplete_duplicate_extra_and_rebound_operation_coverage_rejects(self):
        for fault in ('inventory', 'trigger', 'duplicate_path', 'extra_path', 'binding', 'hash', 'ambiguous_host'):
            w, evidence = standard_fixture()
            if fault == 'inventory':evidence['inventory'].pop()
            elif fault == 'trigger':
                evidence['inventory'] = [r for r in evidence['inventory'] if r['path'][0] != 'triggers']
            elif fault == 'duplicate_path':evidence['classifications'].append(copy.deepcopy(evidence['classifications'][0]))
            elif fault == 'extra_path':evidence['classifications'][0]['operation']['path'] = ['actions', 'absent']
            elif fault == 'binding':evidence['classifications'][0]['operation']['operation_id'] = 'other'
            elif fault == 'hash':evidence['classifications'][0]['operation']['node_sha256'] = '0' * 64
            else:
                w['flow']['properties']['definition']['actions']['Run_publication_rows_query']['inputs']['host']['connectionReferenceName'] = 'other'
                evidence['scope']['writer_sha256'] = core.sha(w)
            with self.subTest(fault=fault), self.assertRaises(ValueError):assess_standard(w, evidence)

    def test_power_bi_or_relaxed_policy_cannot_replace_no_premium_policy(self):
        for name, value in (('power_automate_premium', True), ('power_automate_premium', 0),
                ('custom_connectors_allowed', True), ('power_bi_entitlement', 'Premium'),
                ('allowed_classes', ['BuiltIn', 'Standard', 'Premium'])):
            w, evidence = standard_fixture(); evidence['policy'][name] = value
            with self.subTest(name=name, value=value), self.assertRaisesRegex(ValueError, 'no-Premium'):
                assess_standard(w, evidence)

    def test_inconsistent_tiers_and_connector_claimed_builtin_are_not_silently_resolved(self):
        w, evidence = standard_fixture()
        queries = [e for e in evidence['classifications'] if e['operation']['operation_id'] == 'ExecuteDatasetQuery']
        queries[0]['classification'] = 'Premium'
        diagnostic = assess_standard(w, evidence)['standard_connector_evidence']
        self.assertEqual(sum('inconsistent_classification' in r['blockers'] for r in diagnostic['operations']), 2)
        self.assertEqual([e['classification'] for e in diagnostic['supplied_evidence']['classifications'] if e['operation']['operation_id'] == 'ExecuteDatasetQuery'], ['Premium', 'Standard'])
        w, evidence = standard_fixture()
        next(e for e in evidence['classifications'] if e['operation']['operation_id'] == 'PostItem')['classification'] = 'BuiltIn'
        self.assertIn('connector_claimed_builtin', assess_standard(w, evidence)['standard_connector_evidence']['policy_blockers'])

    def test_malformed_partial_unversioned_evidence_and_unpaired_inputs_fail_closed(self):
        for fault in ('partial', 'version', 'source', 'schema', 'classification', 'kind', 'extra'):
            w, evidence = standard_fixture(); entry = evidence['classifications'][0]
            if fault == 'partial':evidence['complete'] = False
            elif fault == 'version':entry['version'] = ''
            elif fault == 'source':entry['source_sha256'] = 'unretained'
            elif fault == 'schema':entry['operation_schema_sha256'] = None
            elif fault == 'classification':entry['classification'] = 'probably standard'
            elif fault == 'kind':evidence['kind'] = 'unknown'
            else:evidence['writer_ready'] = True
            with self.subTest(fault=fault), self.assertRaises(ValueError):assess_standard(w, evidence)
        w, evidence = standard_fixture()
        with self.assertRaises(ValueError):assess_standard(w, evidence, {})
        with self.assertRaises(ValueError):
            preflight.assess(w, metadata_snapshot(), target(), expected_writer_sha256=core.sha(w), standard_pins={})

    def test_all_nested_branches_and_connector_triggers_keep_reused_names_distinct(self):
        w, evidence = standard_fixture(); definition = w['flow']['properties']['definition']
        repeat = dict(type='Compose', inputs='fictional')
        definition['actions']['Envelope'] = dict(type='Scope', actions={
            'Choose': dict(type='Switch', cases={'case/one': dict(case='one', actions={'Repeat': repeat})},
                default=dict(actions={'Repeat': copy.deepcopy(repeat)})),
            'Decide': dict(type='If', actions={'Repeat': copy.deepcopy(repeat)},
                **{'else': dict(actions={'Repeat': copy.deepcopy(repeat)})})})
        definition['triggers']['Repeat'] = dict(type='OpenApiConnectionWebhook', inputs=dict(host=dict(
            apiId='/providers/Microsoft.PowerApps/apis/shared_sharepointonline',
            operationId='OnChange', connectionReferenceName='shared_sharepointonline')))
        root = ['actions', 'Envelope']
        paths = [root, root + ['actions', 'Choose'], root + ['actions', 'Decide'],
            root + ['actions', 'Choose', 'cases', 'case/one', 'actions', 'Repeat'],
            root + ['actions', 'Choose', 'default', 'actions', 'Repeat'],
            root + ['actions', 'Decide', 'actions', 'Repeat'],
            root + ['actions', 'Decide', 'else', 'actions', 'Repeat'], ['triggers', 'Repeat']]
        for path in paths:
            node = definition
            for segment in path:node = node[segment]
            inputs = node.get('inputs'); host = inputs.get('host', {}) if isinstance(inputs, dict) else {}
            row = dict(path=path, node_type=node['type'], api_id=host.get('apiId'),
                operation_id=host.get('operationId'), connection_reference=host.get('connectionReferenceName'),
                node_sha256=core.sha(node))
            evidence['inventory'].append(row)
            evidence['classifications'].append(dict(operation=copy.deepcopy(row),
                classification='Standard' if path[0] == 'triggers' else 'BuiltIn',
                version='fixture:v2', reference='fixture:nested-source', source_sha256='c' * 64,
                operation_schema_sha256='d' * 64))
        evidence['inventory'].sort(key=lambda r:r['path']); evidence['scope']['writer_sha256'] = core.sha(w)
        diagnostic = assess_standard(w, evidence)['standard_connector_evidence']
        self.assertEqual(len(diagnostic['operations']), 19)
        repeats = [r for r in diagnostic['operations'] if r['operation']['path'][-1] == 'Repeat']
        self.assertEqual(len(repeats), 5)
        self.assertEqual(diagnostic['policy_blockers'], [])
        trigger = next(e for e in evidence['classifications'] if e['operation']['path'] == ['triggers', 'Repeat'])
        evidence['classifications'].remove(trigger)
        missing = assess_standard(w, evidence)['standard_connector_evidence']
        row = next(r for r in missing['operations'] if r['operation']['path'] == ['triggers', 'Repeat'])
        self.assertIn('missing_classification', row['blockers'])

    def test_ambiguous_native_connection_name_is_blocking_even_with_matching_reference_keys(self):
        w, evidence = standard_fixture(); refs = w['flow']['properties']['connectionReferences']
        for value in refs.values():value['connectionName'] = 'fictional-same-name'
        evidence['scope'].update(writer_sha256=core.sha(w), connection_references_sha256=core.sha(refs))
        self.assertIn('ambiguous_connection_identity', assess_standard(w, evidence)['standard_connector_evidence']['policy_blockers'])

    def test_classification_cannot_hide_missing_connector_bindings_or_suppress_unknowns(self):
        w, evidence = standard_fixture()
        recurrence = next(e for e in evidence['classifications'] if e['operation']['path'] == ['triggers', 'Recurrence'])
        recurrence['classification'] = 'Standard'
        self.assertIn('standard_claim_without_connector_binding', assess_standard(w, evidence)['standard_connector_evidence']['policy_blockers'])
        w, evidence = standard_fixture()
        evidence['classifications'] = []
        result = assess_standard(w, evidence)
        self.assertEqual(len(result['standard_connector_evidence']['operations']), 11)
        self.assertTrue(all(r['classification'] == 'Unknown' for r in result['standard_connector_evidence']['operations']))
        self.assertIn('standard_evidence_claims_unauthenticated', result['blockers'])

    def test_malformed_nested_branches_and_absent_triggers_reject_incomplete_coverage(self):
        for fault in ('branch', 'cases', 'triggers', 'host'):
            w, evidence = standard_fixture(); definition = w['flow']['properties']['definition']
            if fault == 'branch':definition['actions']['Apply_to_each_Publication']['else'] = {}
            elif fault == 'cases':definition['actions']['Apply_to_each_Publication']['cases'] = {'unknown': {}}
            elif fault == 'triggers':definition.pop('triggers')
            else:definition['triggers']['Recurrence']['inputs'] = {'host': []}
            evidence['scope']['writer_sha256'] = core.sha(w)
            with self.subTest(fault=fault), self.assertRaises(ValueError):assess_standard(w, evidence)

    def test_cli_opt_in_evidence_is_private_pinned_and_exclusive(self):
        import contextlib, io, tempfile
        from unittest.mock import patch
        w, evidence = standard_fixture()
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stderr(io.StringIO()):
            root = Path(directory).resolve(); private = root / 'private'; private.mkdir()
            docs = dict(writer=w, registry=metadata_snapshot(), target=target(),
                standard_evidence=evidence, standard_pins=evidence_pins(w, evidence))
            args = []
            for name, value in docs.items():
                path = private / (name + '.json'); path.write_text(json.dumps(value), encoding='utf-8')
                args.extend(['--' + name.replace('_', '-'), str(path)])
            output = private / 'result.json'
            args += ['--expected-writer-sha256', core.sha(w), '--output', str(output)]
            with patch.object(preflight, 'ROOT', root):
                try:code = preflight.main(args)
                except SystemExit as exc:self.fail('Standard evidence CLI is missing: ' + str(exc))
                self.assertEqual(code, 0)
                saved = output.read_bytes(); result = json.loads(saved)
                self.assertFalse(result['result']['activation_permitted'])
                self.assertIn('standard_evidence', result['source_files_sha256'])
                self.assertEqual(preflight.main(args), 2); self.assertEqual(output.read_bytes(), saved)
                output.unlink(); (private / 'standard_pins.json').write_text('{}', encoding='utf-8')
                self.assertEqual(preflight.main(args), 2); self.assertFalse(output.exists())
                no_pin = args.copy(); i = no_pin.index('--standard-pins'); del no_pin[i:i+2]
                self.assertEqual(preflight.main(no_pin), 2); self.assertFalse(output.exists())
