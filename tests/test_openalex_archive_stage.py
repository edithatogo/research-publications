import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from prepare_openalex_archive_stage import build, build_stage_fragment, build_candidate
from prepare_openalex_retention import build as retain
import test_openalex_retention as retention_fixture


class ArchiveStage(unittest.TestCase):
    def setUp(self):
        fixture = retention_fixture.OpenAlexRetention()
        fixture.setUp()
        self.prepared = retain(fixture.frozen, fixture.candidate)
        self.records = json.loads(fixture.frozen) + [{'DOI': '10.1000/not-requested'}]

    def test_pages_reconstruct_all_original_chunks_without_commit_marker(self):
        files, receipt = build(self.prepared, self.records, 'openalex-fixed')
        restored = [{k[1:-1]: v for k, v in row.items()}
                    for raw in files.values() for row in json.loads(raw)]
        self.assertEqual(restored, self.prepared['chunks'])
        self.assertTrue(all(len(json.loads(raw)) <= 2 for raw in files.values()))
        self.assertFalse(any(name.startswith('commit-') for name in files))
        self.assertFalse(receipt['accepted_commit'])
        self.assertEqual(receipt['remaining_doi_batches'], [['10.1000/not-requested']])

    def test_foreign_source_and_failed_pass_cannot_enter_archive(self):
        with self.assertRaises(ValueError):
            build(self.prepared, [{'DOI': '10.1000/foreign'}], 'openalex-fixed')
        self.prepared['attempt_statuses'].append({'RequestedDOI': '10.1000/not-requested',
                                                 'Status': 'unavailable'})
        with self.assertRaises(ValueError):
            build(self.prepared, self.records, 'openalex-fixed')

    def test_cli_requires_ignored_paths_before_read_or_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo=Path(temporary)
            subprocess.run(['git','init','--quiet',str(repo)],check=True)
            root=repo/'private'/'ops';root.mkdir(parents=True)
            prepared=root/'prepared.json';records=root/'records.json';output=root/'stage'
            prepared.write_text(json.dumps(self.prepared));records.write_text(json.dumps(self.records))
            script=Path(__file__).resolve().parents[1]/'scripts'/'prepare_openalex_archive_stage.py'
            command=[sys.executable,str(script),'--private-root',str(root),'--prepared',str(prepared),
                     '--records',str(records),'--output-directory',str(output),'--batch-id','test']
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('must be ignored',result.stderr)
            self.assertFalse(output.exists())
            (repo/'.gitignore').write_text('private/\n')
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((output/'stage-receipt-private.json').is_file())

    def test_fragment_reuses_connection_and_keeps_manifest_and_commit_gates(self):
        import copy
        host = {'connectionName': 'shared_onedriveforbusiness', 'apiId': 'existing'}
        flow = {'properties': {'definition': {
            'triggers': {'manual': {'inputs': {'schema': {'required': ['text']}}}},
            'actions': {
                'Compose': {'inputs': 'text'},
                'Read': {'type': 'OpenApiConnection', 'inputs': {
                    'host': {**host, 'operationId': 'GetFileContentByPath'},
                    'parameters': {'path': 'old', 'inferContentType': True}}},
                'Write': {'type': 'OpenApiConnection', 'inputs': {
                    'host': {**host, 'operationId': 'CreateFile'},
                    'parameters': {'folderPath': '/DEV/01 Source archive'}}}}}}}
        original = copy.deepcopy(flow)
        files, receipt = build(self.prepared, self.records, 'openalex-fixed')
        fragment = build_stage_fragment(flow, files, receipt)
        self.assertEqual(flow, original)
        self.assertFalse(fragment['commit_marker_emitted'])
        loop = fragment['actions']['OpenAlex_Archive_Pages']
        self.assertEqual(loop['runtimeConfiguration']['concurrency']['repetitions'], 1)
        self.assertEqual(loop['runAfter'], {'OpenAlex_Page_payloads': ['Succeeded']})
        self.assertEqual(fragment['actions']['OpenAlex_Page_payloads']['runAfter'],
                         {'Require_OpenAlex_generation': ['Succeeded']})
        self.assertIn('404', loop['actions']['OpenAlex_Page_Exists']['else']['actions']
                      ['Require_OpenAlex_page_absent']['inputs'])
        self.assertIn('ARCHIVE_CONFLICT', loop['actions']['Require_OpenAlex_page_exact']['inputs'])
        flow['properties']['definition']['triggers']['manual']['inputs']['schema']['required'] = []
        with self.assertRaises(ValueError):
            build_stage_fragment(flow, files, receipt)

    def test_candidate_keeps_old_path_and_gates_every_page_and_marker(self):
        import copy
        read = {'type': 'OpenApiConnection', 'runAfter': {}, 'inputs': {
            'host': {'connectionName': 'shared_onedriveforbusiness', 'operationId': 'GetFileContentByPath'},
            'parameters': {'path': '/DEV/01 Source archive/commit-old.json'}}}
        write = copy.deepcopy(read)
        write['inputs']['host']['operationId'] = 'CreateFile'
        write['inputs']['parameters'] = {'folderPath': '/DEV/01 Source archive', 'name': 'commit-old.json',
                                         'body': "@string(outputs('Manifest'))"}
        write['runAfter'] = {'Require_commit_marker_absent': ['Succeeded']}
        actions = {
            'Read_current_validation': {'type': 'OpenApiConnection', 'runAfter': {}, 'inputs': {
                'host': {'connectionName': 'shared_powerbi', 'operationId': 'ExecuteDatasetQuery'},
                'parameters': {'datasetid': 'fixture-model', 'groupid': 'fixture-workspace'}}},
            'Expected_manifest': {'inputs': {'BatchID': 'old'}},
            'Get_existing_commit_marker': {**read, 'runAfter': {
                'Require_validation': ['Succeeded'], 'Require_archive_persisted': ['Succeeded']}},
            'Condition_commit_marker': {'type': 'If', 'runAfter': {'Get_existing_commit_marker': ['Succeeded', 'Failed']},
                'actions': {}, 'else': {'actions': {
                    'Require_commit_marker_absent': {'type': 'Compose', 'runAfter': {}, 'inputs': '404 guard'},
                    'Create_file': write}}},
            'Get_file_content_using_path': {**read, 'runAfter': {'Condition_commit_marker': ['Succeeded']}},
            'Verify_commit_readback': {'type': 'Compose', 'runAfter': {'Get_file_content_using_path': ['Succeeded']},
                                      'inputs': "@string(outputs('Manifest'))"}}
        flow = {'name': 'fixture-existing', 'properties': {'state': 'Started', 'connectionReferences': {'existing': {}},
                'definition': {'triggers': {'manual': {'inputs': {'schema': {'required': ['text']}}}}, 'actions': actions}}}
        original = copy.deepcopy(flow)
        files, receipt = build(self.prepared, self.records, 'openalex-fixed')
        generation = {'status': 'PASS', 'refresh_request_id': '11111111-1111-1111-1111-111111111111',
                      'native_definition_sha256': 'a' * 64, 'complete_successful_raw_bytes_sha256_schema_verified': 1,
                      'raw_chunk_rows': len(self.prepared['chunks']), 'canonical_rows': 2, 'context_rows': 1}
        candidate, manifest, proof = build_candidate(flow, files, receipt, generation)
        self.assertEqual(flow, original)
        self.assertEqual(candidate['properties']['definition']['triggers'], original['properties']['definition']['triggers'])
        branch = candidate['properties']['definition']['actions'].pop('Condition_OpenAlex_archive')['actions']
        candidate['properties']['definition']['actions']['Read_current_validation']['runAfter'] = {}
        self.assertEqual(candidate, original)
        nested = branch['OpenAlex_Archive_Pages']['actions']
        self.assertIn('Read_OpenAlex_source_page', nested)
        self.assertEqual(nested['OpenAlex_Page_Existing']['runAfter'], {'Require_OpenAlex_source_page_exact': ['Succeeded']})
        self.assertEqual(set(branch['Get_OpenAlex_commit_marker']['runAfter']),
                         {'Require_OpenAlex_generation', 'Require_OpenAlex_archive_persisted'})
        self.assertEqual(manifest['Sources'][0]['ExpectedKeys'], self.prepared['expected_keys'])
        self.assertFalse(proof['native_written'])
        generation['status'] = 'PREPARED'
        with self.assertRaises(ValueError):
            build_candidate(flow, files, receipt, generation)


if __name__ == '__main__':
    unittest.main()
