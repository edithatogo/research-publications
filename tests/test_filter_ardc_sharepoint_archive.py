import hashlib
import json
import unittest

from scripts.filter_ardc_sharepoint_archive import read_filter


class SharePointFilterTests(unittest.TestCase):
    def test_exact_bound_target_and_saved_batch(self):
        site = 'https://example.sharepoint.com/sites/Research'
        folder = '/Documents/Archive/Activities'
        binding = {'resources': ['https://example.sharepoint.com'],
                   'ardcActivitiesArchiveTarget': {'site': site, 'folder': folder}}
        data = json.dumps({'status': 'OK', 'code': 200, 'data': {'records': [
            {'id': '10', 'key': 'k', 'title': 'CHHHS project'}]}}).encode()
        name = 'activities-batch-000000000.json'
        receipt = {'source': 'ardc-research-activities', 'records': 1,
                   'batches': [{'name': name, 'sha256': hashlib.sha256(data).hexdigest(), 'count': 1}]}
        aliases = json.dumps({'units': [{'OrganisationKey': 'chhhs', 'Aliases': ['CHHHS']}]}).encode()
        calls = []
        def read(s, f, n):
            calls.append((s, f, n))
            return data
        result = read_filter(receipt, binding, aliases, read)
        self.assertEqual(calls, [(site, folder, name)])
        self.assertEqual(len(result['candidates']), 1)
        self.assertFalse(result['source_complete_verified'])
        with self.assertRaises(ValueError):
            read_filter(receipt, {**binding, 'resources': []}, aliases, read)
        self.assertEqual(len(calls), 1)
