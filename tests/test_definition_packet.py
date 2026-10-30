import base64
import copy
import unittest
from scripts.deploy_report_definition import prepare, fingerprint


def definition(**parts):
    return {'definition': {'parts': [{'path': p, 'payload': base64.b64encode(v.encode()).decode(), 'payloadType': 'InlineBase64'} for p, v in parts.items()]}}


class PacketTests(unittest.TestCase):
    def packet(self, before, candidate, changed):
        return prepare(before, candidate, expected_sha256=fingerprint(before), changed_paths=changed,
                       workspace_id='00000000-0000-0000-0000-000000000001', item_id='00000000-0000-0000-0000-000000000002', kind='reports', scope='isolated')
    def test_preserves_unknown_parts_and_recovery(self):
        before = definition(**{'definition/report.json': 'old', 'unknown/future.json': 'retained'})
        candidate = copy.deepcopy(before); candidate['definition']['parts'][0]['payload'] = base64.b64encode(b'new').decode()
        packet = self.packet(before, candidate, ['definition/report.json'])
        self.assertEqual(packet['recovery'], before); self.assertFalse(packet['native_ready'])
        self.assertEqual(candidate['definition']['parts'][1], before['definition']['parts'][1])
    def test_omission_unreviewed_change_duplicate_and_binding_change_refused(self):
        before = definition(**{'definition/report.json': 'old', 'definition.pbir': 'binding'})
        candidates = [definition(**{'definition/report.json': 'new'}), definition(**{'definition/report.json': 'new', 'definition.pbir': 'changed'})]
        for candidate in candidates:
            with self.assertRaises(ValueError): self.packet(before, candidate, ['definition/report.json'])
        duplicate = copy.deepcopy(before); duplicate['definition']['parts'].append(duplicate['definition']['parts'][0])
        with self.assertRaises(ValueError): self.packet(before, duplicate, [])
