import hashlib
import json
import unittest

from scripts.ardc_native_archive_target import validate_target


class ArchiveTargetTests(unittest.TestCase):
    def test_accepts_exact_hash_and_folder(self):
        raw = json.dumps({'source': 'ardc', 'format': 'rims-ardc-public-registry-v1',
                          'complete': True, 'archive_folder': '/Documents/Archive/run'}).encode()
        result = validate_target(raw, raw, expected_sha256=hashlib.sha256(raw).hexdigest(),
                                 expected_folder='/Documents/Archive/run')
        self.assertTrue(result['exact_target_validated'])
        self.assertFalse(result['native_read_performed'])

    def test_rejects_self_consistent_unaccepted_marker_and_different_folder(self):
        raw = json.dumps({'source': 'ardc', 'format': 'rims-ardc-public-registry-v1',
                          'complete': True, 'archive_folder': '/Documents/Other/run'}).encode()
        with self.assertRaisesRegex(ValueError, 'accepted manifest'):
            validate_target(raw, raw, expected_sha256='0' * 64, expected_folder='/Documents/Other/run')
        with self.assertRaisesRegex(ValueError, 'folder'):
            validate_target(raw, raw, expected_sha256=hashlib.sha256(raw).hexdigest(),
                            expected_folder='/Documents/Archive/run')


if __name__ == '__main__':
    unittest.main()
