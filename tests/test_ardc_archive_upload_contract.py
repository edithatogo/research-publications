import hashlib
import unittest

from scripts.ardc_archive_upload_contract import qualify_upload


class UploadContractTests(unittest.TestCase):
    def setUp(self):
        self.raw = b'{"source":"ardc"}'
        self.digest = hashlib.sha256(self.raw).hexdigest()
        self.site = 'https://example.sharepoint.com/sites/Research'
        self.folder = '/Documents/Archive/Activities'
        self.binding = {'resources': ['https://example.sharepoint.com'],
                        'ardcActivitiesArchiveTarget': {'site': self.site, 'folder': self.folder}}
        self.plan = {'format': 'rims-ardc-activities-upload-v1', 'site': self.site, 'folder': self.folder,
                     'name': 'activities-batch-000000000.json', 'sha256': self.digest, 'bytes': len(self.raw)}

    def test_exact_payload_and_target_are_local_only(self):
        result = qualify_upload(self.binding, self.plan, self.raw)
        self.assertFalse(result['native_write_performed'])
        self.assertFalse(result['native_readback_verified'])

    def test_rejects_target_and_payload_drift(self):
        for change in ({'folder': '/Documents/Elsewhere'}, {'name': 'batch.json'}, {'bytes': 1}, {'sha256': '0' * 64}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                qualify_upload(self.binding, {**self.plan, **change}, self.raw)
        with self.assertRaises(ValueError):
            qualify_upload(self.binding, self.plan, self.raw + b' ')

    def test_rejects_traversal_even_when_pinned(self):
        folder = '/Documents/Archive/../other'
        binding = {**self.binding, 'ardcActivitiesArchiveTarget': {'site': self.site, 'folder': folder}}
        with self.assertRaises(ValueError):
            qualify_upload(binding, {**self.plan, 'folder': folder}, self.raw)
