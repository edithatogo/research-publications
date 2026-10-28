"""Fictional end-to-end producer/model/export cases; no native operations.
SPDX-License-Identifier: Apache-2.0
"""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import prepare_source_relationship_export as export
from scripts.prepare_source_relationship_model import prepare as model_prepare, project_rows, fingerprint
from test_prepare_source_relationship_model import fixture


def inputs(modify=None):
    args = fixture()
    if modify:
        modify(args)
    ctx = args['producer_context']
    ctx.update(rows_sha256=fingerprint(args['rows']), row_count=len(args['rows']),
               publications_sha256=fingerprint(args['publications']))
    typed = project_rows(args['rows'], args['publications'], ctx)
    for cap in ctx['capabilities'].values():
        cap['typed_rows_sha256'] = fingerprint(typed)
    args['producer_context_sha256'] = fingerprint(ctx)
    packet = model_prepare(**args)
    return dict(model_inputs=args, model_packet=packet, model_packet_sha256=fingerprint(packet),
                rows_sha256=fingerprint(args['rows']), publications_sha256=fingerprint(args['publications']),
                typed_rows_sha256=fingerprint(typed))


class ExportTests(unittest.TestCase):
    def test_roundtrip_literal_text_null_boolean_integer_and_formula_prefixes(self):
        for value in ('=SUM(A1)', '+cmd', '-1', '@foo', "'literal", '\t=1', '\r\n=2', '', 'é,"quoted"\ntext'):
            data = inputs(lambda a: a['rows'][0].update(ToLabel=value))
            before = copy.deepcopy(data)
            files = export.build(**data)
            rows = json.loads(files['evidence.json'])
            self.assertEqual(rows[0]['ToLabel'], value)
            self.assertEqual(export.decode_csv(files['evidence.csv']), rows)
            self.assertIsNone(rows[0]['ObservedUTC'])
            self.assertIs(rows[0]['CandidateEligible'], True)
            self.assertIs(type(rows[0]['CanonicalMatchCount']), int)
            cells = list(csv.reader(io.StringIO(files['evidence.csv'].decode(), newline='')))[1]
            self.assertTrue(all(c.startswith("'") for c in cells))
            self.assertEqual(data, before)
            self.assertEqual(files, export.build(**data))

    def test_revisions_occurrences_ambiguity_and_retraction_are_preserved(self):
        def modify(a):
            row = a['rows'][0]
            row['SourcePaths'].append('/another/occurrence')
            row.update(CanonicalKey='', CanonicalMatchCount=2)
            other = copy.deepcopy(row)
            other.update(SourceVersion='revision-2', SourceRetracted=True, CandidateEligible=False)
            # Eligibility is per EvidenceKey in frozen context, so use a distinct assertion.
            other['EvidenceKey'] = 'source|authorship|b'
            a['producer_context']['providers'][other['EvidenceKey']] = 'PubMed'
            a['producer_context']['eligibility'][other['EvidenceKey']] = False
            a['rows'].append(other)
        data = inputs(modify)
        files = export.build(**data)
        rows = json.loads(files['evidence.json'])
        manifest = json.loads(files['manifest.json'])
        self.assertEqual(manifest['rowCount'], 2)
        self.assertEqual(manifest['canonicalKeys'], [])
        self.assertEqual(len(set(manifest['assertionRevisionKeys'])), 2)
        self.assertEqual(json.loads(rows[0]['SourcePathsJSON']), ['/MedlineCitation/Article/AuthorList/Author/0', '/another/occurrence'])
        self.assertEqual(json.loads(rows[1]['RawAssertionJSON']), data['model_inputs']['rows'][1])
        self.assertTrue(rows[1]['SourceRetracted'])
        self.assertTrue(all(r['CanonicalMatchCount'] == 2 for r in rows))
        self.assertFalse(manifest['canonicalAdmission'])

    def test_unmapped_and_empty_generations_are_not_dropped_or_promoted(self):
        data = inputs(lambda a: a['rows'][0].update(CanonicalKey='', CanonicalMatchCount=0))
        self.assertEqual(json.loads(export.build(**data)['evidence.json'])[0]['CanonicalMatchCount'], 0)
        def empty(a):
            a['rows'].clear()
            a['producer_context'].update(providers={}, eligibility={})
        files = export.build(**inputs(empty))
        self.assertEqual(json.loads(files['evidence.json']), [])
        self.assertEqual(export.decode_csv(files['evidence.csv']), [])
        self.assertEqual(json.loads(files['manifest.json'])['status'], 'candidate_only')

    def test_distinct_revisions_of_same_evidence_key_survive(self):
        def modify(a):
            row = copy.deepcopy(a['rows'][0]); row['SourceVersion'] = 'later-source-version'
            a['rows'].append(row)
        files = export.build(**inputs(modify))
        manifest = json.loads(files['manifest.json'])
        self.assertEqual(len(set(manifest['evidenceKeys'])), 1)
        self.assertEqual(len(set(manifest['assertionRevisionKeys'])), 2)

    def test_each_independent_pin_is_required(self):
        for key in ('model_packet_sha256', 'rows_sha256', 'publications_sha256', 'typed_rows_sha256'):
            data = inputs(); data[key] = '0' * 64
            with self.subTest(key=key), self.assertRaises(ValueError):
                export.build(**data)

    def test_packet_and_source_drift_cannot_be_hidden_by_repinning_packet(self):
        for mode in ('model', 'context', 'rows', 'canonical', 'packet-status', 'capability', 'table', 'parts'):
            data = inputs(); a = data['model_inputs']
            if mode == 'model': a['document']['definition']['parts'][0]['payload'] = 'Y2hhbmdlZA=='
            elif mode == 'context': a['producer_context']['projection_id'] = 'drift'
            elif mode == 'rows': a['rows'][0]['ToLabel'] = 'changed'
            elif mode == 'canonical': a['publications'][0]['ReviewStatus'] = 'changed'
            elif mode == 'packet-status': data['model_packet']['nativeAcceptance'] = True
            elif mode == 'capability':
                a['producer_context']['capabilities'] = {}; a['producer_context_sha256'] = fingerprint(a['producer_context'])
            elif mode == 'table': data['model_packet']['modelDefinition']['definition']['parts'][-1]['payload'] = 'Y2hhbmdlZA=='
            else: a['expected_parts'].pop()
            data['model_packet_sha256'] = fingerprint(data['model_packet'])
            with self.subTest(mode=mode), self.assertRaises(ValueError): export.build(**data)

    def test_duplicate_revision_and_partial_context_fail(self):
        for mode in ('duplicate', 'partial'):
            data = inputs(); a = data['model_inputs']
            if mode == 'duplicate':
                a['rows'].append(copy.deepcopy(a['rows'][0])); a['producer_context']['row_count'] = 2
                a['producer_context']['rows_sha256'] = fingerprint(a['rows']); data['rows_sha256'] = fingerprint(a['rows'])
            else: a['producer_context']['partial'] = True
            a['producer_context_sha256'] = fingerprint(a['producer_context'])
            with self.subTest(mode=mode), self.assertRaises(ValueError): export.build(**data)

    def test_exclusive_private_output_and_hash_readback(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(export, 'ROOT', Path(tmp).resolve()):
            target = Path(tmp).resolve()/'private/ops/export'
            manifest = export.prepare(target, **inputs())
            for name, sha in manifest['files'].items():
                self.assertEqual(hashlib.sha256((target/name).read_bytes()).hexdigest(), sha)
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            with self.assertRaises(ValueError): export.prepare(target, **inputs())
            self.assertEqual(before, {p.name:p.read_bytes() for p in target.iterdir()})
            with self.assertRaises(ValueError): export.prepare(Path(tmp).resolve()/'public', **inputs())

    def test_symlink_output_refused(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(export, 'ROOT', Path(tmp).resolve()):
            root=Path(tmp).resolve()/'private/ops'; root.mkdir(parents=True)
            (root/'link').symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError): export.prepare(root/'link/export', **inputs())

    def test_failed_write_leaves_no_manifest_and_preserves_existing_bundle(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(export, 'ROOT', Path(tmp).resolve()):
            target = Path(tmp).resolve()/'private/ops/export'
            original = Path.open
            def fail_csv(path, *args, **kwargs):
                if path.name == 'evidence.csv' and args == ('xb',): raise OSError('fictional full disk')
                return original(path, *args, **kwargs)
            with patch.object(Path, 'open', fail_csv), self.assertRaises(OSError): export.prepare(target, **inputs())
            self.assertTrue((target/'evidence.json').exists())
            self.assertFalse((target/'manifest.json').exists())
            with self.assertRaises(ValueError): export.prepare(target, **inputs())

    def test_corrupt_readback_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(export, 'ROOT', Path(tmp).resolve()):
            original = Path.read_bytes
            def corrupt(path):
                raw = original(path)
                return raw + b'corrupt' if path.name == 'evidence.csv' else raw
            with patch.object(Path, 'read_bytes', corrupt), self.assertRaises(ValueError):
                export.prepare(Path(tmp).resolve()/'private/ops/export', **inputs())

    def test_csv_decoder_refuses_unescaped_or_missing_fields(self):
        for raw in (b'wrong\r\n', (','.join(export.COLUMNS)+'\r\n=1\r\n').encode()):
            with self.assertRaises(ValueError): export.decode_csv(raw)

    def test_cli_pins_once_read_private_input_and_rejects_duplicate_json(self):
        root = Path(__file__).resolve().parents[1]
        private = root/'private/ops'
        private.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private, prefix='fictional-export-') as tmp:
            base = Path(tmp)
            source = base/'input.json'
            source.write_bytes(export.json_bytes(inputs()))
            command = [sys.executable, '-B', '-S',
                       str(root/'scripts/prepare_source_relationship_export.py'),
                       '--input', str(source), '--output', str(base/'output'), '--input-sha256']
            bad = subprocess.run(command+['0'*64], capture_output=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertFalse((base/'output').exists())
            good = subprocess.run(command+[hashlib.sha256(source.read_bytes()).hexdigest()], capture_output=True)
            self.assertEqual(good.returncode, 0, good.stderr.decode())
            self.assertEqual(json.loads(good.stdout)['rowCount'], 1)
            source.write_bytes(b'{"model_inputs":{},"model_inputs":{}}')
            duplicate = subprocess.run(command+[hashlib.sha256(source.read_bytes()).hexdigest()], capture_output=True)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn(b'Duplicate JSON object key', duplicate.stderr)
