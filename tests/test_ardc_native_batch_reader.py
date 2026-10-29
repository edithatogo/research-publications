import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from urllib.parse import parse_qs, urlsplit

from scripts.ardc_native_batch_reader import ROOT, make_archive_io


class NativeBatchReaderTests(unittest.TestCase):
    def test_probe_distinguishes_absence_presence_and_denial(self):
        with tempfile.TemporaryDirectory(prefix='ardc-read-test-', dir=ROOT / 'private/ops') as tmp:
            root = Path(tmp)
            site = 'https://example.sharepoint.com/sites/Research'
            folder = '/Documents/Archive/Activities'
            binding = root / 'binding.json'
            binding.write_text(json.dumps({'resources': ['https://example.sharepoint.com'],
                                           'ardcActivitiesArchiveTarget': {'site': site, 'folder': folder}}))
            name = 'activities-batch-000000000.json'
            state = {'mode': 'absent'}
            def fake(command, **kwargs):
                if state['mode'] == 'denied':
                    return SimpleNamespace(returncode=1)
                if 'request' in command:
                    url = command[command.index('--url') + 1]
                    if '$filter' not in parse_qs(urlsplit(url).query):
                        Path(command[command.index('--filePath') + 1]).write_text(json.dumps({
                            'Exists': state['mode'] != 'missing-folder',
                            'ServerRelativeUrl': urlsplit(site).path + folder}))
                        return SimpleNamespace(returncode=0)
                    self.assertEqual(parse_qs(urlsplit(url).query)['$filter'], ["Name eq '" + name + "'"])
                    path = Path(command[command.index('--filePath') + 1])
                    payload = {'value': [] if state['mode'] in ('absent', 'paged', 'missing-folder') else [{'Name': name}]}
                    if state['mode'] == 'paged':
                        payload['@odata.nextLink'] = 'more'
                    path.write_text(json.dumps(payload))
                else:
                    path = Path(command[command.index('--path') + 1])
                    path.write_bytes(b'saved')
                return SimpleNamespace(returncode=0)
            probe, read = make_archive_io(binding, root, run=fake)
            state['mode'] = 'missing-folder'
            with self.assertRaisesRegex(ValueError, 'folder existence'):
                probe(name)
            state['mode'] = 'absent'
            self.assertIsNone(probe(name))
            state['mode'] = 'present'
            self.assertEqual(probe(name), b'saved')
            self.assertEqual(read(name), b'saved')
            state['mode'] = 'paged'
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                probe(name)
            state['mode'] = 'denied'
            with self.assertRaisesRegex(ValueError, 'read failed'):
                probe(name)
            with self.assertRaises(ValueError):
                read('../other')
