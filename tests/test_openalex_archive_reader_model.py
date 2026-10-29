import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_openalex_archive_reader_model import build, EXPRESSIONS, CHUNKS, WORKS
from prepare_openalex_archive_stage import build as stage
from prepare_openalex_retention import build as retain
import test_openalex_retention as fixture_module


class ArchiveReaderModel(unittest.TestCase):
    def setUp(self):
        fixture = fixture_module.OpenAlexRetention()
        fixture.setUp()
        self.prepared = retain(fixture.frozen, fixture.candidate)
        self.files, receipt = stage(self.prepared, json.loads(fixture.frozen), 'fixture-openalex')
        self.manifest = json.dumps({'SchemaVersion': 1, 'Status': 'committed', 'BatchID': 'fixture-openalex',
            'Validation': {'Keysets': True, 'Metadata': True, 'RefreshGeneration': True},
            'Preservation': {'UnchangedSources': ['PubMed', 'DORA'], 'ChangedSources': ['OpenAlex']},
            'Sources': [receipt['source_spec']], 'Files': receipt['files']}).encode()
        texts = {EXPRESSIONS: 'expression RetainedArchiveFiles = fixture\n'
                 'expression fnReadCommittedHistory =\n(Files as table, SourceName as text) as table => fixture\n',
                 CHUNKS: 'column preserved\nsource = Table.FromRecords(OpenAlexBootstrapDocument[chunks])',
                 WORKS: 'column preserved\nsource = fnProjectRetainedOpenAlexAligned(OpenAlexBootstrapObservations,pOpenAlexAlignedFieldLimits)'}
        texts.update({f'definition/fixture-{i}.tmdl': 'preserved fixture' for i in range(43)})
        self.baseline = json.dumps({'definition': {'format': 'TMDL', 'parts': [
            {'path': name, 'payload': base64.b64encode(text.encode()).decode(), 'payloadType': 'InlineBase64'}
            for name, text in texts.items()]}}).encode()
        self.sha = hashlib.sha256(self.baseline).hexdigest()

    def test_only_two_partition_sources_and_append_only_expressions_change(self):
        candidate, receipt, expressions = build(self.baseline, self.manifest, self.prepared, self.files,
                                                expected_baseline_sha256=self.sha)
        original = {p['path']: p for p in json.loads(self.baseline)['definition']['parts']}
        changed = []
        for part in candidate['definition']['parts']:
            if part != original[part['path']]:
                changed.append(part['path'])
        self.assertEqual(set(changed), {EXPRESSIONS, CHUNKS, WORKS})
        appended = base64.b64decode(next(p['payload'] for p in candidate['definition']['parts'] if p['path'] == EXPRESSIONS))
        self.assertTrue(appended.startswith(base64.b64decode(original[EXPRESSIONS]['payload'])))
        self.assertIn('fnReadCommittedHistory(RetainedArchiveFiles,"OpenAlex")', expressions['OpenAlexCommittedObservations'])
        self.assertIn('R[MetadataJSON]', expressions['OpenAlexCommittedMetadataChunks'])
        self.assertNotIn('Json.FromValue', expressions['OpenAlexCommittedMetadataChunks'])
        self.assertFalse(receipt['native_archive_accepted'])

    def test_drifted_baseline_or_incomplete_archive_cannot_switch_consumer(self):
        with self.assertRaises(ValueError):
            build(self.baseline + b' ', self.manifest, self.prepared, self.files, expected_baseline_sha256=self.sha)
        damaged = dict(self.files)
        damaged.pop(next(iter(damaged)))
        with self.assertRaises(ValueError):
            build(self.baseline, self.manifest, self.prepared, damaged, expected_baseline_sha256=self.sha)

    def test_cli_requires_ignored_inputs_and_explicit_exact_baseline_pin(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo=Path(temporary)
            subprocess.run(['git','init','--quiet',str(repo)],check=True)
            root=repo/'private'/'ops';root.mkdir(parents=True)
            baseline=root/'baseline.json';baseline.write_bytes(self.baseline)
            pin=root/'baseline.sha256';pin.write_text(self.sha)
            manifest=root/'manifest.json';manifest.write_bytes(self.manifest)
            prepared=root/'prepared.json';prepared.write_text(json.dumps(self.prepared))
            pages=root/'pages';pages.mkdir()
            for name,raw in self.files.items():(pages/name).write_bytes(raw)
            output=root/'candidate'
            script=Path(__file__).resolve().parents[1]/'scripts'/'build_openalex_archive_reader_model.py'
            cmd=[sys.executable,str(script),'--private-root',str(root),'--baseline',str(baseline),
                 '--baseline-pin',str(pin),'--manifest',str(manifest),'--prepared',str(prepared),
                 '--pages-directory',str(pages),'--output-directory',str(output)]
            denied=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(denied.returncode,0)
            self.assertIn('must be ignored',denied.stderr)
            self.assertFalse(output.exists())
            (repo/'.gitignore').write_text('private/\n')
            pin.write_text('0'*64)
            mismatch=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(mismatch.returncode,0)
            self.assertFalse(output.exists())
            pin.write_text(self.sha)
            allowed=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(allowed.returncode,0,allowed.stderr)
            self.assertTrue((output/'candidate-receipt-private.json').is_file())


if __name__ == '__main__':
    unittest.main()
