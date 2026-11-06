"""Fictional DoRA-to-study projection: identity, missingness and data minimisation."""
import copy
import hashlib
import json
import unittest

from scripts.collect_pubmed import canonical_json
from scripts.dora_activity import SOURCE_FIELDS
from scripts.dora_study_projection import project_dora
from scripts.study_explorer import explore_dora, render


def envelope():
    records = []
    for number, flag in [(1, 'Yes'), (2, 'No'), (3, 'Unknown')]:
        row = {field: None for field in SOURCE_FIELDS}
        row.update({'_id': number, 'Project ID': 'same-id', 'Full Project Title': 'Fictional study',
                    'Clinical Trial (Yes/No)': flag, 'Site Name': 'CHHHS',
                    'PI Email': 'private@example.invalid', 'HREC (Ethics) Reference Number': 'excluded',
                    'Start Date': 2020, 'Disease Category': 'Diabetes'})
        records.append(row)
    return {'schema_version': 'dora-activity-v1', 'status': 'succeeded',
            'expected_count': 3, 'retrieved_count': 3, 'observed_at': '2026-11-06T00:00:00Z',
            'source_payload': {'resource': {'id': 'fixture-resource', 'name': 'Fictional resource',
                                          'url': 'https://example.invalid/dora.csv'}},
            'records': records, 'records_sha256': hashlib.sha256(canonical_json(records).encode()).hexdigest(),
            'record_id_sha256': hashlib.sha256(canonical_json(['1', '2', '3']).encode()).hexdigest()}


class DoraStudyProjectionTests(unittest.TestCase):
    def project(self, value):
        raw = json.dumps(value).encode()
        return project_dora(raw, hashlib.sha256(raw).hexdigest())

    def test_resource_row_keys_survive_duplicate_project_ids_and_sensitive_fields_drop(self):
        rows, observed = self.project(envelope())
        self.assertEqual(len({row['SourceKey'] for row in rows}), 3)
        self.assertEqual({row['SourceProjectID'] for row in rows}, {'same-id'})
        self.assertEqual([row['IsClinicalTrial'] for row in rows], [True, False, None])
        self.assertTrue(all(row['IsInterventionalTrial'] is None for row in rows))
        self.assertTrue(all(row['OverallStatus'] is None for row in rows))
        self.assertTrue(all(row['StartDate'] == 2020 for row in rows))
        self.assertNotIn('private@example.invalid', json.dumps(rows))
        self.assertNotIn('excluded', json.dumps(rows))
        self.assertEqual(observed, '2026-11-06T00:00:00Z')

    def test_failed_partial_changed_and_unpinned_inputs_are_rejected(self):
        for field, value in [('status', 'failed'), ('retrieved_count', 2),
                             ('records_sha256', None), ('record_id_sha256', '0'*64)]:
            data = envelope()
            data[field] = value
            with self.assertRaises(ValueError):
                self.project(data)
        data = envelope()
        data['records'][0]['Full Project Title'] = 'changed'
        with self.assertRaises(ValueError):
            self.project(data)
        with self.assertRaises(ValueError):
            project_dora(b'{}', '0'*64)

    def test_site_strings_do_not_confirm_association_or_link_to_trial(self):
        raw = json.dumps(envelope()).encode()
        digest = hashlib.sha256(raw).hexdigest()
        result = explore_dora(raw, digest, associations=[], query='diabetes')
        self.assertEqual(result['views']['chhhs_associated'], [])
        self.assertEqual(len(result['views']['external_discovery']), 3)
        self.assertIn('dora-activity:fixture-resource:1', render(result))
        link = {'source_key': 'dora-activity:fixture-resource:1', 'review_status': 'Reviewed',
                'involvement': 'conducting_site', 'evidence_url': 'https://example.invalid/review',
                'ppg_evidence_urls': ['https://example.invalid/ppg']}
        result = explore_dora(raw, digest, associations=[link], study_type='Clinical trial')
        self.assertEqual(len(result['views']['chhhs_associated']), 1)
        self.assertEqual(result['views']['external_discovery'], [])
        self.assertIn('https://example.invalid/ppg', render(result))

    def test_existing_directory_cli_verifies_receipt_and_records_without_copying_contacts(self):
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        from scripts.source_capture_receipt import PRIVATE_ROOT
        PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as folder:
            source = Path(folder)
            data = envelope()
            records = data.pop('records')
            receipt = json.dumps(data).encode()
            (source/'receipt.json').write_bytes(receipt)
            (source/'records.json').write_text(json.dumps(records))
            command = [sys.executable, '-m', 'scripts.study_explorer', '--dora-directory', str(source),
                       '--sha256', hashlib.sha256(receipt).hexdigest(), '--output', str(source/'output')]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            output = json.loads((source/'output/study-explorer.json').read_text())
            self.assertEqual(output['capture_records'], 3)
            self.assertNotIn('private@example.invalid', json.dumps(output))
            records[0]['Project ID'] = 'changed'
            (source/'records.json').write_text(json.dumps(records))
            command[-1] = str(source/'changed-output')
            self.assertNotEqual(subprocess.run(command,capture_output=True).returncode, 0)
            self.assertFalse((source/'changed-output').exists())
