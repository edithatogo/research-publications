"""Keep accelerated history ingestion separate from serial live register updates."""
import unittest
from scripts.grantconnect_ready_routes import routes


class ReadyRoutesTest(unittest.TestCase):
    def test_history_batches_preserve_idempotency_and_live_serialisation(self):
        flow = routes('https://example.sharepoint.com/sites/research', 'library',
                      '/Documents/Reporting', 'register', 'calendar',
                      {'awards': 'awards', 'closed': 'closed', 'links': 'links'})
        assert flow['triggers']['Ready_file']['runtimeConfiguration']['concurrency']['runs'] == 1
        history = flow['actions']['Route']['cases']['History']['actions']['History_files']
        assert history['runtimeConfiguration']['concurrency']['repetitions'] == 4
        groups = history['actions']['History_groups']
        assert groups['foreach'] == "@chunk(body('History_rows'),100)"
        assert groups['runtimeConfiguration']['concurrency']['repetitions'] == 1
        assert groups['actions']['Existing_history']['inputs']['retryPolicy'] == {'type': 'fixed', 'count': 4, 'interval': 'PT15S'}
        assert groups['actions']['Pace_history_group']['actions']['Write_cooldown']['inputs']['interval'] == {'count': 50, 'unit': 'Second'}
        writes = groups['actions']['Write_missing']['actions']
        assert writes['Save_history_group']['inputs']['retryPolicy'] == {'type': 'none'}
        assert writes['Read_saved_group']['runAfter'] == {'Save_history_group': ['Succeeded']}
        assert 'intersection' in writes['Guard_saved_group']['inputs']
        live = flow['actions']['Route']['cases']['Live']['actions']['Each_record']
        assert live['runtimeConfiguration']['concurrency']['repetitions'] == 1
