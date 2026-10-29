import json
import hashlib
import unittest

from scripts.ardc_secondary_filter import filter_archived_batches, filter_responses


def raw(records):
    return json.dumps({'status': 'OK', 'code': 200, 'data': {'records': records}}).encode()


class SecondaryFilterTests(unittest.TestCase):
    def setUp(self):
        self.aliases = json.dumps({'units': [{'OrganisationKey': 'chhhs', 'Aliases': ['CHHHS', 'Cairns Hospital']}]}).encode()

    def test_fields_and_provenance_are_candidates_not_attribution(self):
        records = [{'id': '1', 'key': 'k1', 'institutions': [{'name': 'Cairns Hospital'}]},
                   {'id': '2', 'key': 'k2', 'description': 'CHHHS collaboration'},
                   {'id': '3', 'key': 'k3', 'title': 'NotCHHHSuffix'}]
        result = filter_responses([('batch.json', raw(records))], self.aliases)
        self.assertEqual(result['input_records'], 3)
        self.assertEqual([r['activity_id'] for r in result['candidates']], ['1', '2'])
        self.assertEqual(result['candidates'][0]['matches'][0]['field'], 'institutions[0].name')
        self.assertFalse(result['affiliation_confirmed'])
        self.assertFalse(result['source_complete_verified'])

    def test_duplicate_activity_ids_fail(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            filter_responses([('a', raw([{'id': '1', 'key': 'k'}])),
                              ('b', raw([{'id': '1', 'key': 'k'}]))], self.aliases)

    def test_invalid_source_fails(self):
        with self.assertRaises(ValueError):
            filter_responses([('a', b'{"status":"ERROR"}')], self.aliases)

    def test_receipt_binds_each_archive_batch_to_its_saved_bytes(self):
        content = raw([{'id': '1', 'key': 'k', 'title': 'CHHHS study'}])
        name = 'activities-batch-000000000.json'
        receipt = {'source': 'ardc-research-activities', 'records': 1,
                   'batches': [{'name': name, 'sha256': hashlib.sha256(content).hexdigest(), 'count': 1}]}
        result = filter_archived_batches(receipt, lambda _: content, self.aliases)
        self.assertEqual(len(result['candidates']), 1)
        with self.assertRaisesRegex(ValueError, 'differs'):
            filter_archived_batches(receipt, lambda _: content + b' ', self.aliases)
        with self.assertRaisesRegex(ValueError, 'Batch count'):
            filter_archived_batches({**receipt, 'batches': [{**receipt['batches'][0], 'count': 2}]},
                                    lambda _: content, self.aliases)
        with self.assertRaisesRegex(ValueError, 'records'):
            filter_archived_batches({**receipt, 'records': 2}, lambda _: content, self.aliases)
