import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.grantconnect_history_verify import verify


class HistoryVerificationTests(unittest.TestCase):
    def test_empty_manifests_cannot_certify_empty_native_lists(self):
        with tempfile.TemporaryDirectory() as tmp, patch('subprocess.run') as run:
            root = Path(tmp)
            manifest = root / 'ready.json'
            manifest.write_text(json.dumps({'files': []}))
            with self.assertRaisesRegex(ValueError, 'nonempty'):
                verify(root / 'binding', 'https://example.invalid', {}, [manifest], root / 'receipt')
            run.assert_not_called()
            self.assertFalse((root / 'receipt/acceptance.json').exists())

    def test_native_continuation_cannot_be_ignored(self):
        for continuation in ('@odata.nextLink', 'odata.nextLink', '__next', None):
            with self.subTest(continuation=continuation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                shards = []
                lists = {}
                for index, entity in enumerate(('awards', 'closed', 'links'), start=1):
                    lists[entity] = f'00000000-0000-0000-0000-{index:012d}'
                    evidence = '{}'
                    row = dict(HistoryKey=entity, Title=entity, GAID='', GOID='',
                               EvidenceHash=hashlib.sha256(evidence.encode()).hexdigest(),
                               SourceEvidence=evidence)
                    (root / f'{entity}.json').write_text(json.dumps([row]))
                    shards.append(dict(entity=entity, file=f'{entity}.json', count=1))
                manifest = root / 'ready.json'
                manifest.write_text(json.dumps({'files': shards}))

                def respond(command, **kwargs):
                    output = Path(command[command.index('--filePath') + 1])
                    if continuation:
                        payload = {'value': [], continuation: 'https://example.invalid/next'}
                    elif output.name == 'counts.json':
                        payload = {'value': [{'Id': identity, 'ItemCount': 1} for identity in lists.values()]}
                    else:
                        entity = output.stem.split('-')[0]
                        rows = json.loads((root / f'{entity}.json').read_text())
                        payload = {'value': [dict(rows[0], Id=1)]}
                    output.write_text(json.dumps(payload))

                with patch('subprocess.run', side_effect=respond):
                    if continuation:
                        with self.assertRaisesRegex(ValueError, 'Incomplete paged'):
                            verify(root / 'binding', 'https://example.invalid', lists, [manifest], root / 'receipt')
                    else:
                        verify(root / 'binding', 'https://example.invalid', lists, [manifest], root / 'receipt')
                acceptance = root / 'receipt/acceptance.json'
                if continuation:
                    self.assertFalse(acceptance.exists())
                else:
                    self.assertEqual(json.loads(acceptance.read_text()), {'awards': 1, 'closed': 1, 'links': 1})
