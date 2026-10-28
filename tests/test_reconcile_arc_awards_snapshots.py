import json
import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.reconcile_arc_awards_snapshots import private_output_path, reconcile as raw_reconcile, fingerprint


def reconcile(baseline, current):
    return raw_reconcile(baseline,current,baseline_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),
                         current_sha256=hashlib.sha256(current.read_bytes()).hexdigest())


def snapshot(records):
    return {
        "source": "arc",
        "record_kind": "awards_only",
        "snapshot_complete": True,
        "source_total": len(records),
        "retrieved_utc": "2026-09-01T00:00:00+00:00",
        "snapshot_hash": fingerprint(records),
        "next_links": [],
        "records": records,
    }


class ReconcileArcAwardsSnapshotsTests(unittest.TestCase):
    def test_strict_saved_bytes_digest_counts_pagination_and_unknowns(self):
        from scripts.reconcile_arc_awards_snapshots import _load_snapshot
        good=snapshot([{'SourceID':'A','AwardCode':'CODE-A','Amount':None,'StartDate':None}])
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'saved.json'
            for mode in ('hash','bool','next','records','numeric','duplicate','nonfinite','overflow','error'):
                data=json.loads(json.dumps(good))
                if mode=='bool': data['source_total']=True
                elif mode=='next': data['next_links']=['more']
                elif mode=='records': data['snapshot_hash']='f'*64
                elif mode=='numeric': data['records'][0]['Amount']=0
                elif mode=='error': data['records'][0]['error']='provider failed'
                raw=json.dumps(data).encode()
                if mode=='duplicate':raw=b'{"source":"arc","source":"other"}'
                elif mode=='nonfinite':raw=b'{"x":NaN}'
                elif mode=='overflow':raw=b'{"x":1e999}'
                path.write_bytes(raw)
                sha='0'*64 if mode=='hash' else hashlib.sha256(raw).hexdigest()
                with self.subTest(mode=mode),self.assertRaises(ValueError):_load_snapshot(path,sha)
            raw=json.dumps(good).encode();path.write_bytes(raw)
            result,sha,_=_load_snapshot(path,hashlib.sha256(raw).hexdigest())
            self.assertIsNone(result['records'][0]['Amount'])
            self.assertIsNone(result['records'][0]['StartDate'])
            self.assertEqual(path.read_bytes(),raw)

    def test_missing_and_null_are_distinct_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            old,new=Path(temp)/'old',Path(temp)/'new'
            old.write_text(json.dumps(snapshot([{'SourceID':'A','AwardCode':'CODE-A'}])))
            new.write_text(json.dumps(snapshot([{'SourceID':'A','AwardCode':'CODE-A','Date':None}])))
            self.assertEqual(reconcile(old,new)['changed_field_counts'],{'Date':1})

    def test_exclusive_atomic_output_rejects_symlink_and_serialization_failure(self):
        from scripts.reconcile_arc_awards_snapshots import write_new
        private=Path(__file__).resolve().parents[1]/'private/ops';private.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private) as temp:
            root=Path(temp);source=root/'source.json';source.write_bytes(b'protected')
            link=root/'link.json';link.symlink_to(source)
            with self.assertRaises(ValueError):write_new(link,{},[source])
            out=root/'new.json'
            with self.assertRaises(ValueError):write_new(out,{'bad':float('nan')},[source])
            self.assertFalse(out.exists());self.assertEqual(source.read_bytes(),b'protected')
            self.assertEqual(sorted(p.name for p in root.iterdir()),['link.json','source.json'])

    def test_private_output_rejects_paths_outside_private_ops(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "under private/ops"):
                private_output_path(Path(directory) / "public-reconciliation.json")

    def test_private_output_rejects_overwrite(self):
        private_ops = Path(__file__).resolve().parent.parent / "private/ops"
        private_ops.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=private_ops, suffix=".json") as existing:
            with self.assertRaisesRegex(ValueError, "overwrite"):
                private_output_path(Path(existing.name))

    def test_reports_id_and_field_differences_without_promoting_opportunities(self):
        old = snapshot([
            {"SourceID": "A", "AwardCode": "CODE-A", "Amount": "", "Status": "Awarded", "RetrievedUTC": "old"},
            {"SourceID": "B", "AwardCode": "CODE-B", "Amount": "5", "Status": "Awarded"},
        ])
        new = snapshot([
            {"SourceID": "A", "AwardCode": "CODE-A", "Amount": "0.0", "Status": "Awarded", "RetrievedUTC": "new"},
            {"SourceID": "C", "AwardCode": "CODE-C", "Amount": "2", "Status": "Awarded"},
        ])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, current = root / "old.json", root / "new.json"
            baseline.write_text(json.dumps(old))
            current.write_text(json.dumps(new))
            result = reconcile(baseline, current)
        self.assertEqual(result["added_source_ids"], ["C"])
        self.assertEqual(result["removed_source_ids"], ["B"])
        self.assertEqual(result["changed_record_count"], 1)
        self.assertEqual(result["changed_field_counts"], {"Amount": 1})
        self.assertEqual(result["amount_transition_counts"], {"blank_to_zero": 1})
        self.assertFalse(result["award_code_mapping"]["same_source_id_set"])
        self.assertFalse(result["award_code_mapping"]["same_award_code_set"])
        self.assertFalse(result["award_code_mapping"]["same_one_to_one_sourceid_awardcode_mapping"])
        self.assertFalse(result["canonical_opportunity_admission"])
        self.assertFalse(result["authoritative_lifecycle_semantics_proven"])

    def test_reports_same_mapping_across_complete_captures_without_claiming_identity_authority(self):
        old = snapshot([{"SourceID": "A", "AwardCode": "CODE-A", "Amount": "1"}])
        new = snapshot([{"SourceID": "A", "AwardCode": "CODE-A", "Amount": "2"}])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, current = root / "old.json", root / "new.json"
            baseline.write_text(json.dumps(old))
            current.write_text(json.dumps(new))
            result = reconcile(baseline, current)
        mapping = result["award_code_mapping"]
        self.assertTrue(mapping["same_source_id_set"])
        self.assertTrue(mapping["same_award_code_set"])
        self.assertTrue(mapping["same_one_to_one_sourceid_awardcode_mapping"])
        self.assertEqual(mapping["baseline_pairing_sha256"], mapping["current_pairing_sha256"])
        self.assertFalse(mapping["identity_or_lifecycle_semantics_proven"])

    def test_detects_pairing_drift_even_when_both_identity_sets_match(self):
        old = snapshot([
            {"SourceID": "A", "AwardCode": "CODE-A"},
            {"SourceID": "B", "AwardCode": "CODE-B"},
        ])
        new = snapshot([
            {"SourceID": "A", "AwardCode": "CODE-B"},
            {"SourceID": "B", "AwardCode": "CODE-A"},
        ])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, current = root / "old.json", root / "new.json"
            baseline.write_text(json.dumps(old))
            current.write_text(json.dumps(new))
            mapping = reconcile(baseline, current)["award_code_mapping"]
        self.assertTrue(mapping["same_source_id_set"])
        self.assertTrue(mapping["same_award_code_set"])
        self.assertFalse(mapping["same_one_to_one_sourceid_awardcode_mapping"])

    def test_rejects_duplicate_award_codes(self):
        duplicate = snapshot([
            {"SourceID": "A", "AwardCode": "CODE-X"},
            {"SourceID": "B", "AwardCode": "CODE-X"},
        ])
        clean = snapshot([{"SourceID": "A", "AwardCode": "CODE-A"}])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, current = root / "old.json", root / "new.json"
            baseline.write_text(json.dumps(duplicate))
            current.write_text(json.dumps(clean))
            with self.assertRaisesRegex(ValueError, "duplicate AwardCode"):
                reconcile(baseline, current)

    def test_rejects_blank_or_padded_award_codes(self):
        for invalid_code in ("", " ", " CODE-A", "CODE-A "):
            with self.subTest(invalid_code=invalid_code), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                baseline, current = root / "old.json", root / "new.json"
                baseline.write_text(json.dumps(snapshot([{"SourceID": "A", "AwardCode": invalid_code}])))
                current.write_text(json.dumps(snapshot([{"SourceID": "A", "AwardCode": "CODE-A"}])))
                with self.assertRaisesRegex(ValueError, "AwardCode must be nonblank and unpadded"):
                    reconcile(baseline, current)

    def test_rejects_duplicate_source_ids(self):
        duplicate = snapshot([{"SourceID": "A", "AwardCode": "CODE-A"}, {"SourceID": "A", "AwardCode": "CODE-B"}])
        clean = snapshot([{"SourceID": "A", "AwardCode": "CODE-A"}])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, current = root / "old.json", root / "new.json"
            baseline.write_text(json.dumps(duplicate))
            current.write_text(json.dumps(clean))
            with self.assertRaisesRegex(ValueError, "duplicate SourceID"):
                reconcile(baseline, current)

    def test_rejects_incomplete_snapshot(self):
        incomplete = snapshot([])
        incomplete["snapshot_complete"] = False
        clean = snapshot([])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, current = root / "old.json", root / "new.json"
            baseline.write_text(json.dumps(incomplete))
            current.write_text(json.dumps(clean))
            with self.assertRaisesRegex(ValueError, "must be complete"):
                reconcile(baseline, current)


if __name__ == "__main__":
    unittest.main()
