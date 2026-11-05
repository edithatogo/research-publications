import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import grants_mrff_download as source
from scripts.grants_mrff_download import _resource_kind
from tests.test_capture_official_workbooks import workbook


class MrffResourceKindTests(unittest.TestCase):
    def test_classifies_current_resource_filenames(self):
        cases = {
            "medical-research-future-fund-mrff-grant-recipients_0.xlsx": "awarded_grant_recipients",
            "medical_research_future_fund_grant_recipients_-_summary_as_at_10_july_2026.xlsx": "awarded_grants_summary",
            "medical_research_future_fund_funded_rates_as_at_10_july_2026.xlsx": "opportunity_funded_rates_summary",
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                self.assertEqual(_resource_kind("generic Excel attachment", f"https://www.health.gov.au/{filename}"), expected)

    def test_rejects_unrecognized_attachment(self):
        with self.assertRaisesRegex(ValueError, "unrecognized MRFF Excel attachment"):
            _resource_kind("generic Excel attachment", "https://www.health.gov.au/unknown.xlsx")


class BrowserRetentionTests(unittest.TestCase):
    def setUp(self):
        source.PRIVATE_OPS.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=source.PRIVATE_OPS)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / 'browser'
        self.input.mkdir()
        self.urls = ['https://www.health.gov.au/sites/default/files/' + name for name in
                     ['grant-recipients.xlsx', 'grant-recipients-summary.xlsx', 'funded_rates.xlsx']]
        page = '<p>correct as at 10 July 2026</p><p>Publication date: 27 August 2026</p>'
        page += ''.join('<a href="' + url + '">Excel</a>' for url in self.urls)
        (self.input / 'source-page.html').write_text(page)
        (self.input / 'copyright-page.html').write_text(
            '<p>Download in unaltered form for internal use within your organisation.</p>')
        self.raw = workbook()
        downloads = []
        for index, url in enumerate(self.urls):
            path = self.input / ('download-' + str(index) + '.xlsx')
            path.write_bytes(self.raw)
            downloads.append({'url': url, 'path': str(path)})
        self.observation = {'sourcePage': source.SOURCE_PAGE, 'rightsPage': source.COPYRIGHT_PAGE,
            'route': 'Codex internal browser; synthetic offline fixture',
            'sourceStatus': 200, 'rightsStatus': 200, 'internalUnalteredUseObserved': True,
            'observedAt': '2026-11-05T00:00:00Z', 'sourceRepresentation': 'Browser response body',
            'linksBefore': [{'href': url} for url in self.urls],
            'linksAfter': self.urls, 'downloads': downloads}
        self.path = self.input / 'browser-observation.json'
        self.output = self.root / 'retained'
        self.prior = self.root / 'last-good.bin'
        self.prior.write_bytes(b'Prior accepted source')

    def save(self):
        self.path.write_text(json.dumps(self.observation))

    def test_originals_and_notices_retained_without_network_or_native_claims(self):
        self.save()
        with patch.object(source, '_fetch') as fetch:
            result = source.retain_browser_capture(self.path, self.output)
        fetch.assert_not_called()
        self.assertEqual(len(result['resources']), 3)
        self.assertTrue(result['manual_browser_only'])
        self.assertFalse(result['native_admission'])
        self.assertFalse(result['cloud_http_access_verified'])
        self.assertFalse(result['last_good_selector_changed'])
        for row in result['resources']:
            self.assertEqual((self.output / row['path']).read_bytes(), self.raw)
            self.assertEqual(row['sha256'], hashlib.sha256(self.raw).hexdigest())
            self.assertFalse(row['response_headers_observed'])
        for name in ['source-page.html', 'copyright-page.html', 'browser-observation.json']:
            self.assertEqual((self.output / name).read_bytes(), (self.input / name).read_bytes())
        self.assertEqual(self.prior.read_bytes(), b'Prior accepted source')
        with self.assertRaises(ValueError):
            source.retain_browser_capture(self.path, self.output)

    def test_partial_changed_or_foreign_inventory_refused_before_output(self):
        for change in ['partial', 'changed', 'foreign']:
            original = json.loads(json.dumps(self.observation))
            if change == 'partial':
                self.observation['downloads'].pop()
            elif change == 'changed':
                self.observation['linksAfter'] = []
            else:
                self.observation['downloads'][0]['url'] = 'https://other.invalid/book.xlsx'
            self.save()
            with self.subTest(change=change), self.assertRaises(ValueError):
                source.retain_browser_capture(self.path, self.output)
            self.assertFalse(self.output.exists())
            self.observation = original

    def test_challenge_invalid_binary_and_missing_rights_preserve_prior(self):
        self.save()
        good_page = (self.input / 'source-page.html').read_bytes()
        (self.input / 'source-page.html').write_text('<script>triggerInterstitialChallenge()</script>')
        with self.assertRaisesRegex(ValueError, 'SOURCE_ACCESS_BLOCKED'):
            source.retain_browser_capture(self.path, self.output)
        (self.input / 'source-page.html').write_bytes(good_page)
        download = Path(self.observation['downloads'][0]['path'])
        download.write_bytes(b'Not an Excel file')
        with self.assertRaises(zipfile.BadZipFile):
            source.retain_browser_capture(self.path, self.output)
        download.write_bytes(self.raw)
        (self.input / 'copyright-page.html').write_text('<p>No evidenced permission</p>')
        with self.assertRaisesRegex(ValueError, 'internal-use evidence'):
            source.retain_browser_capture(self.path, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.prior.read_bytes(), b'Prior accepted source')


if __name__ == "__main__":
    unittest.main()
