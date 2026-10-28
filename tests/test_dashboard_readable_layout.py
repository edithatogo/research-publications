"""Fictional whole-baseline drift and layout preservation guards."""
import json
from pathlib import Path
import tempfile
import unittest
from scripts.prepare_dashboard_readable_layout import bundle_digest, prepare_readable


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
