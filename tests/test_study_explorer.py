"""Fictional local study-discovery and identity boundary tests."""
import copy
import hashlib
import json
import unittest

from scripts.study_explorer import explore, render


def record(nct, kind='INTERVENTIONAL'):
    return {'protocolSection': {
        'identificationModule': {'nctId': nct, 'briefTitle': '<script>fictional</script> diabetes'},
        'designModule': {'studyType': kind},
        'statusModule': {'overallStatus': 'RECRUITING'},
        'conditionsModule': {'conditions': ['Diabetes']},
        'contactsLocationsModule': {'locations': [{'facility': 'CHHHS', 'country': 'Australia'}]}}}


class StudyExplorerTests(unittest.TestCase):
    def setUp(self):
        self.body = {'studies': [record('NCT00000001'), record('NCT00000002', 'OBSERVATIONAL')]}
        self.link = {'source_key': 'clinicaltrials.gov:NCT00000002', 'review_status': 'Reviewed',
                     'involvement': 'investigator_affiliation', 'evidence_url': 'https://example.org/review',
                     'ppg_evidence_urls': ['https://example.org/evidence']}

    def run_query(self, body=None, **kwargs):
        raw = json.dumps(body or self.body).encode()
        return explore(raw, hashlib.sha256(raw).hexdigest(), observed_at='2026-11-06T00:00:00Z',
                       associations=kwargs.pop('associations', [self.link]), **kwargs)

    def test_location_does_not_confirm_chhhs_and_observational_studies_remain(self):
        result = self.run_query()
        local = result['views']['chhhs_associated']
        self.assertEqual(len(local), 1)
        self.assertFalse(local[0]['IsInterventionalTrial'])
        self.assertEqual(local[0]['CHHHSInvolvement']['involvement'], 'investigator_affiliation')
        self.assertEqual(len(result['views']['external_discovery']), 1)

    def test_filter_intersection_and_zero_results(self):
        result = self.run_query(query='DIABETES', country='australia', study_type='INTERVENTIONAL')
        self.assertEqual(len(result['views']['external_discovery']), 1)
        self.assertEqual(result['views']['chhhs_associated'], [])
        self.assertEqual(self.run_query(status='COMPLETED')['views'],
                         {'chhhs_associated': [], 'external_discovery': []})

    def test_hash_partial_capture_duplicate_and_missing_association_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'hash'):
            explore(b'{}', '0'*64, observed_at='2026-11-06T00:00:00Z', associations=[])
        for body in ({'studies': [], 'nextPageToken': 'more'},
                     {'studies': [record('NCT00000001')]*2},
                     {'studies': [record('NCT00000001')]}):
            with self.assertRaises(ValueError):
                self.run_query(body)

    def test_unreviewed_or_unsafe_evidence_cannot_promote(self):
        for field, value in [('review_status', 'Candidate'), ('evidence_url', 'javascript:alert(1)'),
                             ('involvement', 'title_match'), ('ppg_evidence_urls', ['https://u:p@example.org'])]:
            link = copy.deepcopy(self.link)
            link[field] = value
            with self.assertRaises(ValueError):
                self.run_query(associations=[link])

    def test_html_escapes_source_text_and_retains_evidence_links(self):
        document = render(self.run_query())
        self.assertNotIn('<script>', document)
        self.assertIn('&lt;script&gt;', document)
        self.assertIn('https://example.org/evidence', document)
        self.assertIn('not a complete registry', document)

    def test_cli_accepts_existing_zip_contract_and_refuses_output_reuse(self):
        import io
        import subprocess
        import sys
        import tempfile
        import zipfile
        from pathlib import Path
        from scripts.source_capture_receipt import PRIVATE_ROOT
        study = record('NCT00000001')
        content = json.dumps(study).encode()
        digest = hashlib.sha256(content).hexdigest()
        manifest = {'source': 'ClinicalTrials.gov', 'count': 1,
                    'observations': [{'id': 'NCT00000001', 'status': 200,
                       'source_url': 'https://clinicaltrials.gov/api/v2/studies/NCT00000001',
                       'sha256': digest, 'bytes': len(content)}],
                    'files': [{'name': 'NCT00000001.json', 'sha256': digest, 'bytes': len(content)}]}
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as archive:
            archive.writestr('source-manifest.json', json.dumps(manifest))
            archive.writestr('NCT00000001.json', content)
        PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as folder:
            root = Path(folder)
            source = root/'capture.zip'
            source.write_bytes(buf.getvalue())
            output = root/'output'
            command = [sys.executable, '-m', 'scripts.study_explorer', '--archive', str(source),
                       '--sha256', hashlib.sha256(buf.getvalue()).hexdigest(),
                       '--observed-at', '2026-11-06T00:00:00Z', '--output', str(output)]
            completed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((output/'study-explorer.json').read_text())
            self.assertEqual(result['archive_sha256'], hashlib.sha256(buf.getvalue()).hexdigest())
            before = (output/'study-explorer.html').read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual((output/'study-explorer.html').read_bytes(), before)

    def test_malformed_identity_is_structured_and_counts_distinguish_selection(self):
        with self.assertRaisesRegex(ValueError, 'Trial identification'):
            self.run_query({'studies': [{}]}, associations=[])
        result = self.run_query(study_type='INTERVENTIONAL')
        self.assertEqual(result['capture_records'], 2)
        self.assertEqual(result['selected_records'], 1)

    def test_association_order_does_not_change_semantic_digest(self):
        first = copy.deepcopy(self.link)
        first['source_key'] = 'clinicaltrials.gov:NCT00000001'
        left = self.run_query(associations=[first, self.link])
        right = self.run_query(associations=[self.link, first])
        self.assertEqual(left['associations_sha256'], right['associations_sha256'])
