"""Fictional whole-baseline drift and layout preservation guards."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.prepare_dashboard_readable_layout import (
    TEXTBOX_PAGES, TEXTBOX_TARGETS, bundle_digest, prepare_readable,
    prepare_textbox_clearance,
)


def textbox_fixture(root):
    """Fictional six-page geometry; no service definitions or record values."""
    def write(path, doc):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc)+'\n')
    write(root/'definition/pages/pages.json', {'pageOrder': sorted(TEXTBOX_PAGES),
                                             'activePageName': 'ReportSection2'})
    write(root/'definition/report.json', {'linguisticSchemaSyncVersion': 2,
                                         'unchanged': 'No import stripping'})
    write(root/'definition.pbir', {'datasetReference': {'unchanged': 'model'}})
    for page in sorted(TEXTBOX_PAGES):
        write(root/f'definition/pages/{page}/page.json',
              {'displayName': page, 'width': 1920, 'height': 1296})
        for _, name in sorted(t for t in TEXTBOX_TARGETS if t[0] == page):
            y, height = (16, 48) if name == 'heading' else (64, 40) if name == 'caption' else (1016, 32) if page == 'ReportSection2' else (960, 40)
            write(root/f'definition/pages/{page}/visuals/{name}/visual.json', {
                'name': name, 'position': {'x': 32, 'y': y, 'width': 1856,
                    'height': height, 'z': 4, 'tabOrder': 10},
                'filterConfig': {'filters': ['Preserve source uncertainty']},
                'visual': {'visualType': 'textbox', 'query': {'preserved': 'query'},
                    'objects': {'general': [{'properties': {'paragraphs': [
                        {'textRuns': [{'value': 'Fictional source caveat',
                                      'textStyle': {'fontSize': '36px' if name == 'heading' else '22px'}}]}]}}]},
                    'visualContainerObjects': {'padding': [{'properties': {
                        side: {'expr': {'Literal': {'Value': '8D'}}}
                        for side in ('top', 'bottom', 'left', 'right')}}]}}})
        write(root/f'definition/pages/{page}/visuals/unchanged-card/visual.json', {
            'name': 'unchanged-card', 'position': {'x': 32, 'y': 112, 'width': 440, 'height': 96},
            'visual': {'visualType': 'card', 'query': {'doNotNormalize': True}}})
    (root/'opaque-resource.bin').write_bytes(b'\x00\xffuntouched')


class TextboxClearanceTests(unittest.TestCase):
    def test_only_allowlisted_geometry_and_vertical_padding_change(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'source'; textbox_fixture(source)
            original = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
            output = Path(temp)/'candidate'
            receipt = prepare_textbox_clearance(source, output, bundle_digest(source))
            self.assertEqual(len(receipt['changed_files']), 10)
            self.assertEqual(receipt['native_writes'], 0)
            for path, raw in original.items():
                self.assertEqual((source/path).read_bytes(), raw)
                if path.as_posix() not in receipt['changed_files']:
                    self.assertEqual((output/path).read_bytes(), raw)
                    continue
                old = json.loads(raw); new = json.loads((output/path).read_bytes())
                restored = copy.deepcopy(new)
                restored['position'] = old['position']
                restored['visual']['visualContainerObjects']['padding'] = old['visual']['visualContainerObjects']['padding']
                self.assertEqual(restored, old)  # Text, fonts, queries, filters, identities unchanged.
                self.assertEqual({k: new['position'][k] for k in ('x', 'width', 'z', 'tabOrder')},
                                 {k: old['position'][k] for k in ('x', 'width', 'z', 'tabOrder')})
                for side in ('left', 'right'):
                    self.assertEqual(new['visual']['visualContainerObjects']['padding'][0]['properties'][side],
                                     old['visual']['visualContainerObjects']['padding'][0]['properties'][side])
            # Repeating against the result creates an unchanged candidate, never reserializing untouched files.
            second = prepare_textbox_clearance(output, Path(temp)/'second', bundle_digest(output))
            self.assertEqual(second['changed_files'], [])

    def test_content_or_inventory_drift_refused_before_output(self):
        for mutation, message in [('missing', 'identity missing'), ('font', 'typography drift'),
                                  ('selector', 'Selector-specific'), ('extra-page', 'six-page')]:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                source = Path(temp)/'source'; textbox_fixture(source)
                path = source/'definition/pages/ReportSection/visuals/heading/visual.json'
                doc = json.loads(path.read_text())
                if mutation == 'missing': path.unlink()
                elif mutation == 'font':
                    doc['visual']['objects']['general'][0]['properties']['paragraphs'][0]['textRuns'][0]['textStyle']['fontSize'] = '72px'
                    path.write_text(json.dumps(doc))
                elif mutation == 'selector':
                    doc['visual']['visualContainerObjects']['padding'][0]['selector'] = {'id': 'responsive'}
                    path.write_text(json.dumps(doc))
                else:
                    page = source/'definition/pages/extra/page.json'; page.parent.mkdir(); page.write_text('{}')
                output = Path(temp)/'candidate'
                with self.assertRaisesRegex(ValueError, message):
                    prepare_textbox_clearance(source, output, bundle_digest(source))
                self.assertFalse(output.exists())

    def test_overlap_overflow_and_nonfinite_geometry_refused(self):
        for mutation, message in [('overlap', 'overlaps'), ('overflow', 'overflow'), ('nan', 'Non-finite')]:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                source = Path(temp)/'source'; textbox_fixture(source)
                name = 'unchanged-card' if mutation == 'overlap' else 'caption'
                path = source/f'definition/pages/ReportSection/visuals/{name}/visual.json'
                doc = json.loads(path.read_text())
                doc['position']['y' if mutation == 'overlap' else 'x'] = 0 if mutation == 'overlap' else 2000 if mutation == 'overflow' else float('nan')
                path.write_text(json.dumps(doc)); output = Path(temp)/'candidate'
                with self.assertRaisesRegex(ValueError, message):
                    prepare_textbox_clearance(source, output, bundle_digest(source))
                self.assertFalse(output.exists())

    def test_full_digest_and_existing_manifest_guards(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'source'; textbox_fixture(source)
            digest = bundle_digest(source); (source/'opaque-resource.bin').write_bytes(b'changed')
            output = Path(temp)/'candidate'
            with self.assertRaisesRegex(ValueError, 'digest drift'):
                prepare_textbox_clearance(source, output, digest)
            output.with_name(output.name+'.manifest.json').write_text('existing evidence')
            with self.assertRaisesRegex(ValueError, 'new output and manifest'):
                prepare_textbox_clearance(source, output, bundle_digest(source))
            self.assertFalse(output.exists())

    def test_drift_during_capture_refused_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'source'; textbox_fixture(source)
            digest = bundle_digest(source)
            def concurrent_change(_):
                (source/'opaque-resource.bin').write_bytes(b'other writer')
                return digest
            output = Path(temp)/'candidate'
            with patch('scripts.prepare_dashboard_readable_layout.bundle_digest', side_effect=concurrent_change):
                with self.assertRaisesRegex(ValueError, 'drift during capture'):
                    prepare_textbox_clearance(source, output, digest)
            self.assertFalse(output.exists())

    def test_implicit_horizontal_padding_stays_implicit(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'source'; textbox_fixture(source)
            path = Path('definition/pages/ReportSection/visuals/heading/visual.json')
            doc = json.loads((source/path).read_text())
            del doc['visual']['visualContainerObjects']['padding']
            (source/path).write_text(json.dumps(doc))
            output = Path(temp)/'candidate'
            prepare_textbox_clearance(source, output, bundle_digest(source))
            padding = json.loads((output/path).read_text())['visual']['visualContainerObjects']['padding']
            self.assertEqual(padding, [{'properties': {
                side: {'expr': {'Literal': {'Value': '0D'}}} for side in ('top', 'bottom')}}])


class ReadableLayoutTests(unittest.TestCase):
    def test_other_page_edit_invalidates_whole_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source';source.mkdir();(source/'other-page.json').write_text('{}')
            expected=bundle_digest(source);(source/'other-page.json').write_text('{"changed":true}')
            output=Path(temp)/'output'
            with self.assertRaisesRegex(ValueError,'Full baseline digest drift'):
                prepare_readable(source,output,expected)
            self.assertFalse(output.exists())

    def test_incomplete_or_extra_overview_inventory_does_not_create_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source';page=source/'definition/pages/ReportSection3'
            (page/'visuals/new-editor-visual').mkdir(parents=True)
            (page/'page.json').write_text('{}')
            (page/'visuals/new-editor-visual/visual.json').write_text('{}')
            output=Path(temp)/'output'
            with self.assertRaisesRegex(ValueError,'visual inventory drift'):
                prepare_readable(source,output,bundle_digest(source))
            self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
