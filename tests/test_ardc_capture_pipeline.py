import json
import unittest

from scripts.ardc_capture_pipeline import capture_and_filter


class CapturePipelineTests(unittest.TestCase):
    def test_capture_readback_precedes_filter_and_output_preserves_provenance(self):
        rows = [{'id': '10', 'key': 'source-10'}, {'id': '11', 'key': 'source-11'}]
        records = [{**rows[0], 'title': 'CHHHS study'}, {**rows[1], 'title': 'Unrelated'}]
        overlay = {'generation_lineage_verified': True, 'activities': rows,
                   'baseline_manifest_sha256': 'a' * 64, 'incremental_manifest_sha256': 'b' * 64}
        aliases = json.dumps({'units': [{'OrganisationKey': 'chhhs', 'Aliases': ['CHHHS']}]}).encode()
        saved, outputs, events = {}, {}, []
        def fetch(batch):
            selected = [r for r in records if r['id'] in {item['id'] for item in batch}]
            return json.dumps({'status': 'OK', 'code': 200, 'data': {'numFound': len(selected),
                                                                      'offset': 0, 'records': selected}}).encode()
        def put(name, data):
            events.append('put')
            saved[name] = data
        def read(name):
            events.append('read')
            return saved[name]
        def save_receipt(receipt):
            events.append('receipt')
            outputs['receipt'] = receipt
        def save_projection(projection):
            events.append('projection')
            outputs['projection'] = projection
        def save_partial(name, projection):
            events.append('partial')
            outputs['partial'] = (name, projection)
        result = capture_and_filter(overlay, b'secret-key', aliases, read_total=lambda: 2,
                                    fetch_batch=fetch, probe=saved.get, put=put, read=read,
                                    save_receipt=save_receipt, save_projection=save_projection, save_partial=save_partial)
        self.assertEqual(events[0], 'put')
        self.assertLess(events.index('read'), events.index('partial'))
        self.assertLess(events.index('partial'), events.index('receipt'))
        self.assertFalse(outputs['partial'][1]['source_complete_verified'])
        self.assertLess(events.index('receipt'), events.index('projection'))
        self.assertEqual(outputs['projection']['candidates'][0]['activity_id'], '10')
        self.assertFalse(result['current_provider_snapshot_verified'])
        self.assertFalse(outputs['projection']['affiliation_confirmed'])

    def test_receipt_is_saved_before_projection_failure(self):
        row = {'id': '10', 'key': 'source-10'}
        overlay = {'generation_lineage_verified': True, 'activities': [row],
                   'baseline_manifest_sha256': 'a' * 64, 'incremental_manifest_sha256': 'b' * 64}
        raw = json.dumps({'status': 'OK', 'code': 200, 'data': {'numFound': 1, 'offset': 0, 'records': [row]}}).encode()
        saved, receipts = {}, []
        with self.assertRaises(ValueError):
            capture_and_filter(overlay, b'secret-key', b'invalid', read_total=lambda: 1,
                               fetch_batch=lambda _: raw, probe=saved.get, put=saved.__setitem__, read=saved.__getitem__,
                               save_receipt=receipts.append, save_projection=lambda _: self.fail('must not save'))
        self.assertEqual(len(receipts), 1)

    def test_uncertain_write_is_reused_after_exact_readback(self):
        row = {'id': '10', 'key': 'source-10', 'title': 'CHHHS study'}
        overlay = {'generation_lineage_verified': True, 'activities': [{'id': '10', 'key': 'source-10'}],
                   'baseline_manifest_sha256': 'a' * 64, 'incremental_manifest_sha256': 'b' * 64}
        raw = json.dumps({'status': 'OK', 'code': 200,
                          'data': {'numFound': 1, 'offset': 0, 'records': [row]}}).encode()
        aliases = json.dumps({'units': [{'OrganisationKey': 'chhhs', 'Aliases': ['CHHHS']}]}).encode()
        saved, writes, receipts, projections = {}, [], [], []
        def lost_ack(name, payload):
            writes.append(name)
            saved[name] = payload
            raise RuntimeError('uncertain')
        common = dict(read_total=lambda: 1, fetch_batch=lambda _: raw, probe=saved.get,
                      read=saved.__getitem__, save_receipt=receipts.append,
                      save_projection=projections.append)
        with self.assertRaisesRegex(RuntimeError, 'uncertain'):
            capture_and_filter(overlay, b'secret-key', aliases, put=lost_ack, **common)
        self.assertEqual(receipts, [])
        capture_and_filter(overlay, b'secret-key', aliases, put=lambda *_: self.fail('second write'), **common)
        self.assertEqual(len(writes), 1)
        self.assertTrue(receipts[0]['batches'][0]['reused'])
        self.assertEqual(projections[0]['candidates'][0]['activity_id'], '10')
