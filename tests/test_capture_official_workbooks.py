import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import ClassVar
from unittest.mock import Mock

from scripts import capture_official_workbooks as source
from scripts.source_capture_receipt import PRIVATE_ROOT


class Response(io.BytesIO):
    status = 200
    headers: ClassVar[dict] = {}


def workbook():
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        archive.writestr('xl/workbook.xml', '<workbook/>')
        archive.writestr('xl/worksheets/sheet1.xml', '<worksheet><data>Complete original</data></worksheet>')
    return raw.getvalue()


class WorkbookCaptureTests(unittest.TestCase):
    def page(self, filenames=('prior.xlsx', 'current.xlsx')):
        return ''.join(f'<a href="/sites/default/files/{name}">Workbook</a>' for name in filenames).encode()

    def test_captures_every_advertised_vintage_and_original_bytes(self):
        raw = workbook(); page = self.page()
        opener = Mock(side_effect=[Response(v) for v in [page, b'Copyright guidance', raw, raw, raw, raw, page]])
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / 'capture'
            result = source.capture('nhmrc', output, opener=opener, sleep=lambda _: None)
            self.assertEqual(result['count'], 2)
            self.assertFalse(result['accepted'])
            self.assertFalse(result['opportunity_admission'])
            inventory = json.loads((output / 'workbooks.json').read_bytes())
            self.assertEqual({v['original_filename'] for v in inventory}, {'prior.xlsx', 'current.xlsx'})
            self.assertTrue(all((output / v['retained_file']).read_bytes() == raw for v in inventory))
            self.assertEqual(len(result['files']), 7)

    def test_refuses_external_and_unsupported_tabular_links(self):
        page_url = source.SOURCES['nhmrc'][0]
        for page in [b'<a href="https://other.invalid/sites/default/files/a.xlsx">x</a>',
                     b'<a href="/sites/default/files/a.csv">x</a>', b'<p>No workbook</p>']:
            with self.subTest(page=page), self.assertRaises(ValueError): source.discover(page, page_url)
        result = source.discover(b'<a href="//www.nhmrc.gov.au/sites/default/files/a.xlsx?x=1&amp;y=2#here">x</a>', page_url)
        self.assertEqual(result, ['https://www.nhmrc.gov.au/sites/default/files/a.xlsx?x=1&y=2'])

    def test_changed_inventory_changed_bytes_and_invalid_binary_preserve_failure(self):
        raw = workbook(); page = self.page(('current.xlsx',))
        for values in ([page, b'rights', b'not-a-workbook'],
                       [page, b'rights', raw, raw + b'drift'],
                       [page, b'rights', raw, raw, self.page(('new.xlsx',))]):
            with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
                output = Path(directory) / 'capture'
                with self.assertRaises((ValueError, zipfile.BadZipFile)):
                    source.capture('mrff', output, opener=Mock(side_effect=[Response(v) for v in values]), sleep=lambda _: None)
                self.assertFalse((output / 'manifest.json').exists())
                self.assertTrue((output / 'failed-generation.json').exists())

    def test_unknown_source_rejected_without_network_or_output(self):
        opener = Mock()
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            output = Path(directory) / 'capture'
            with self.assertRaises(ValueError): source.capture('unknown', output, opener=opener)
            opener.assert_not_called()
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
