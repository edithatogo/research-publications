import base64
import copy
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.prepare_source_archive_stage import (
    archive_binding,
    bind_workbook_consumer,
    inspect_archive,
    prepare,
)
from scripts.source_capture_receipt import PRIVATE_ROOT


class ArchiveStageTests(unittest.TestCase):
    def document(self):
        return {'properties': {'connectionReferences': {'shared_sharepointonline': {'pin': 'fixture'}},
            'definition': {'triggers': {'Recurrence': {'type': 'Recurrence'}}, 'actions': {
                'Run_folder': {'type': 'Compose', 'inputs': "@concat('/Documents/Fixture/01 Source archive/source-',workflow()?['run']?['name'])"},
                'Read': {'type': 'OpenApiConnection', 'inputs': {
                    'host': {'apiId': '/providers/Microsoft.PowerApps/apis/shared_sharepointonline',
                             'connectionName': 'shared_sharepointonline', 'operationId': 'GetFileContentByPath'},
                    'parameters': {'dataset': 'https://fixture.sharepoint.com/sites/source'}}}}}}}

    def bundle(self, root, name='original.xlsx'):
        p = root / 'raw.zip'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr(name, b'original fixture bytes')
            z.writestr('provenance.json', b'{"captured":"historical"}')
        return p, {'source': 'nhmrc', 'raw_asset_preparation_ready': True,
            'package_sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
            'inventory': [{'name': 'original.xlsx', 'bytes': 22,
                           'sha256': hashlib.sha256(b'original fixture bytes').hexdigest()}]}

    def test_preserves_bytes_preimage_and_manifest_without_admission(self):
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            root = Path(directory); archive, receipt = self.bundle(root)
            before = self.document(); original = copy.deepcopy(before)
            plan = prepare(archive, receipt, before, root / 'stage')
            self.assertEqual(before, original)
            self.assertEqual((root / 'stage/raw/original.xlsx').read_bytes(), b'original fixture bytes')
            self.assertFalse(plan['deployment_ready'])
            self.assertFalse(plan['completion_marker_emitted'])
            self.assertEqual(json.loads((root / 'stage/collector-preimage.json').read_text()), before)
            with self.assertRaises(FileExistsError):
                prepare(archive, receipt, before, root / 'stage')

    def test_tamper_missing_asset_and_path_traversal_refused(self):
        for variant in ('hash', 'member', 'missing', 'path'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
                archive, receipt = self.bundle(Path(directory), '../escape.xlsx' if variant == 'path' else 'original.xlsx')
                if variant == 'hash': receipt['package_sha256'] = '0' * 64
                elif variant == 'member': receipt['inventory'][0]['bytes'] = 1
                elif variant == 'missing': receipt['inventory'][0]['name'] = 'absent.xlsx'
                with self.assertRaises(ValueError): inspect_archive(archive, receipt)

    def test_saved_consumer_must_bind_exact_original_and_existing_reference(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as workbook:
            workbook.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Grants" sheetId="1" r:id="rId1"/></sheets></workbook>')
            workbook.writestr('xl/_rels/workbook.xml.rels', '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
            workbook.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:A2"/><sheetData><row r="1"><c r="A1"><v>1</v></c></row></sheetData></worksheet>')
        content = raw.getvalue()
        with tempfile.TemporaryDirectory(dir=PRIVATE_ROOT) as directory:
            root = Path(directory); archive = root / 'bundle.zip'
            with zipfile.ZipFile(archive, 'w') as z: z.writestr('original.xlsx', content)
            receipt = {'source': 'nhmrc', 'raw_asset_preparation_ready': True,
                'package_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'inventory': [{'name': 'original.xlsx', 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}]}
            prepare(archive, receipt, self.document(), root / 'stage')
            folder = '/Documents/Fixture/01 Source archive/nhmrc-workbooks-retained'
            manifest = {'source': 'nhmrc', 'complete': True, 'archive_folder': folder,
                'files': [{'name': 'old-name.xlsx', 'saved_readback_equal': True, 'stored_bytes': len(content), 'source_url': 'https://example.test/original.xlsx'}]}
            packet = {'format': 'rims-nhmrc-workbook-verified-v1', 'workbook_name': 'old-name.xlsx',
                'archive_folder': folder, 'workbook_base64': base64.b64encode(content).decode(),
                'manifest_base64': base64.b64encode(json.dumps(manifest).encode()).decode(),
                'workbook_sha256': hashlib.sha256(content).hexdigest(), 'sheet': 'Grants', 'count': 1,
                'source_url': 'https://example.test/original.xlsx'}
            result = bind_workbook_consumer(root / 'stage', packet, self.document())
            self.assertEqual(result['local_original']['name'], 'original.xlsx')
            self.assertFalse(result['native_runtime_verified'])
            for field, value in [('workbook_sha256', '0'*64), ('sheet', 'Missing'), ('archive_folder', folder+'-other'), ('source_url', 'https://other.test')]:
                changed = {**packet, field: value}
                with self.subTest(field=field), self.assertRaises(ValueError):
                    bind_workbook_consumer(root / 'stage', changed, self.document())
            consumer = self.document(); consumer['properties']['connectionReferences']['shared_sharepointonline'] = {'pin': 'other'}
            with self.assertRaises(ValueError): bind_workbook_consumer(root / 'stage', packet, consumer)

    def test_ambiguous_or_dynamic_target_refused(self):
        for variant in ('root', 'site', 'connection'):
            d = self.document(); a = d['properties']['definition']['actions']
            if variant == 'root': a['Other'] = {'inputs': '/Documents/Other/01 Source archive'}
            elif variant == 'site': a['Read']['inputs']['parameters']['dataset'] = '@variables(\'site\')'
            else: a['Read']['inputs']['host']['connection'] = {}
            with self.subTest(variant=variant), self.assertRaises(ValueError): archive_binding(d)
