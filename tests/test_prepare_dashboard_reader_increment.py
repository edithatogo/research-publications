"""Fictional PBIR preparation guards; source bytes must survive every operation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from scripts.prepare_dashboard_reader_increment import projection_labels, prepare, sha

class DashboardReaderTests(unittest.TestCase):
    def test_direct_field_labels_preserve_binding(self):
        projection={'field':{'Column':{'Expression':{'SourceRef':{'Entity':'Publication'}},'Property':'Year'}},'queryRef':'Publication.Year'}
        original={'visual':{'query':{'queryState':{'Values':{'projections':[projection]}}}}}
        frozen=copy.deepcopy(original)
        result,count=projection_labels(original)
        self.assertEqual(original,frozen)
        self.assertEqual(count,1)
        p=result['visual']['query']['queryState']['Values']['projections'][0]
        self.assertEqual(p['nativeQueryRef'],'Year')
        del p['nativeQueryRef'];self.assertEqual(p,projection)
    def test_complex_missing_label_is_not_guessed(self):
        with self.assertRaises(ValueError):
            projection_labels({'visual':{'query':{'queryState':{'Y':{'projections':[{'field':{'Aggregation':{}},'queryRef':'Sum.X'}]}}}}})
    def test_hash_drift_and_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';(source/'definition/pages').mkdir(parents=True)
            (source/'definition/report.json').write_text('{}')
            (source/'definition/pages/pages.json').write_text('{"pageOrder":[]}')
            with self.assertRaises(ValueError):prepare(source,root/'bad','bad')
            self.assertFalse((root/'bad').exists())
            result=prepare(source,root/'good',sha(b'{}'))
            self.assertEqual(result['input'],result['output'])
            with self.assertRaises(ValueError):prepare(source,root/'good',sha(b'{}'))

    def test_reader_trend_preserves_series_styles(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';(source/'definition/pages').mkdir(parents=True)
            (source/'definition/report.json').write_text('{}')
            (source/'definition/pages/pages.json').write_text('{}')
            path='definition/pages/ReportSection3/visuals/annual-trajectory/visual.json'
            file=source/path;file.parent.mkdir(parents=True)
            styles=[{'properties':{'strokeWidth':{'expr':{'Literal':{'Value':'2D'}}}}},
                    {'selector':{'id':'series'},'properties':{'color':'retained'}}]
            original={'visual':{'visualType':'lineChart','objects':{'lineStyles':styles}}}
            file.write_text(json.dumps(original));frozen=file.read_bytes()
            prepare(source,root/'output',sha(b'{}'),reader_controls=True)
            changed=json.loads((root/'output'/path).read_text())['visual']['objects']['lineStyles']
            self.assertEqual(changed[1],styles[1])
            self.assertEqual(changed[0]['properties']['strokeWidth'],styles[0]['properties']['strokeWidth'])
            self.assertEqual(file.read_bytes(),frozen)

if __name__=='__main__':unittest.main()
