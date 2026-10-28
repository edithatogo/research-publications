import copy
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.reconcile_publication_stub_version_pagination import ROOT, private_path, reconcile


class VersionPaginationReconcileTests(unittest.TestCase):
    def setUp(self):
        self.export = {"complete": True, "next_links": [], "items": [
            {"Id": 2, "versions": [{"VersionLabel": "1.0", "IsCurrentVersion":True}]},
            {"Id": 3, "versions": [{"VersionLabel": "1.0", "IsCurrentVersion":True}]},
        ]}
        self.readback = {"expected_item_ids": [2, 3], "requested_item_count": 2,
                         "returned_item_count": 2, "tenant_mutation_performed": False,
                         "observed_at_utc": "2026-09-25T00:00:00Z",
                         "items": [{"id": i, "status": 200, "count": 1,
                                    "next": None, "labels": ["1.0"]} for i in (2, 3)]}

    def test_exact_complete_readback_marks_only_reconciled_items(self):
        result = reconcile(self.export, self.readback)
        self.assertTrue(all(row["version_history_complete"] and
                            row["version_next_links"] == [] for row in result["items"]))
        self.assertNotIn("version_history_complete", self.export["items"][0])

    def test_missing_id_or_next_link_fails_closed(self):
        for change in ("missing", "next", "label", "status"):
            with self.subTest(change=change):
                receipt = copy.deepcopy(self.readback)
                if change == "missing":
                    receipt["items"].pop()
                elif change == "next":
                    receipt["items"][0]["next"] = "next-page"
                elif change == "label":
                    receipt["items"][0]["labels"] = ["2.0"]
                else:
                    receipt["items"][0]["status"] = 401
                with self.assertRaises(ValueError):
                    reconcile(self.export, receipt)

    def test_failure_does_not_print_tenant_item_id(self):
        receipt = copy.deepcopy(self.readback)
        receipt["items"][0]["labels"] = ["changed"]
        with self.assertRaises(ValueError) as caught:
            reconcile(self.export, receipt)
        self.assertNotIn("item 2", str(caught.exception))

    def test_private_path_rejects_lookalike_and_symlink_escape(self):
        valid = ROOT / "private/ops/version-evidence.json"
        self.assertEqual(private_path(valid), valid.resolve())
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root=Path(temp); (root/'private/ops').mkdir(parents=True)
            with patch('scripts.reconcile_publication_stub_version_pagination.ROOT',root):
                with self.assertRaisesRegex(ValueError, 'under private/ops'):
                    private_path(Path(outside)/'private/ops/output.json')
                link=root/'private/ops/escape'; link.symlink_to(outside,target_is_directory=True)
                with self.assertRaisesRegex(ValueError, 'under private/ops'):
                    private_path(link/'output.json')

    def test_duplicates_boolean_counts_and_current_markers_cannot_certify_history(self):
        for mode in ('saved-duplicate','live-duplicate','bool-id','bool-count','marker','label'):
            old,live=copy.deepcopy((self.export,self.readback))
            if mode=='saved-duplicate': old['items'].append(copy.deepcopy(old['items'][0]))
            elif mode=='live-duplicate':
                live['items'].append(copy.deepcopy(live['items'][0]));live['returned_item_count']=3
            elif mode=='bool-id': old['items'][0]['Id']=True
            elif mode=='bool-count': live['items'][0]['count']=True
            elif mode=='marker': old['items'][0]['versions'][0]['IsCurrentVersion']=1
            else: old['items'][0]['versions'][0]['VersionLabel']=' 1.0'
            with self.subTest(mode=mode), self.assertRaises(ValueError): reconcile(old,live)

    def test_result_has_no_mutable_alias_to_original_versions(self):
        result=reconcile(self.export,self.readback)
        result['items'][0]['versions'][0]['VersionLabel']='changed'
        self.assertEqual(self.export['items'][0]['versions'][0]['VersionLabel'],'1.0')



if __name__ == "__main__":
    unittest.main()
