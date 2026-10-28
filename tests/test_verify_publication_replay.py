# SPDX-License-Identifier: Apache-2.0
import copy
from datetime import timedelta
import unittest

from scripts.verify_publication_replay import verify
from tests.test_verify_publication_protected_fields import NOW, snapshot, versioned, advance
from scripts.publication_batch_contract import PROTECTED_MANUAL_FIELDS


def item(item_id, key, pmid=""):
    return versioned({"Id": str(item_id), "SourceKey": key, "PMID": pmid,
            "ReviewStatus": "Included" if key else "Needs Review", "ReviewNotes": "curated" if key else "",
            "FirstObservedUTC": "2026-09-20T01:00:00Z", "LastObservedUTC": "2026-09-21T01:00:00Z",
            "CanonicalKey":"PUB:"+str(item_id),"Title":"FICTIONAL title","Authors":"A",
            "Journal":"Fixture","PublicationYear":None,"PublicationMonth":None})


def export(rows):
    return {**snapshot(rows,'rows'),"next_links":[]}


class ReplayVerificationTests(unittest.TestCase):
    def setUp(self):
        self.before = export([item(1, "pubmed:123", "123"), item(2, "", "")])
        self.before['observed_at_utc']=(NOW-timedelta(minutes=1)).isoformat()
        self.after = copy.deepcopy(self.before)
        self.after['observed_at_utc']=NOW.isoformat()
        self.after["rows"][0]["LastObservedUTC"] = NOW.isoformat()
        advance(self.after["rows"][0])

    def test_identical_batch_replay_preserves_identity_review_and_advances_observation(self):
        self.assertTrue(verify(self.before, self.after, ["pubmed:123"],now=NOW)["pass"])

    def test_created_or_removed_items_fail(self):
        self.after["rows"].append(item(3, "pubmed:456", "456"))
        self.after["item_count"]=3
        report = verify(self.before, self.after, ["pubmed:123"],now=NOW)
        self.assertFalse(report["pass"])
        self.assertEqual(report["added_item_ids"], ["3"])

    def test_review_and_first_observed_changes_fail(self):
        self.after["rows"][0]["ReviewNotes"] = ""
        self.after["rows"][0]["FirstObservedUTC"] = "2026-09-22T01:00:00Z"
        self.assertFalse(verify(self.before, self.after, ["pubmed:123"],now=NOW)["pass"])

    def test_unchanged_or_regressed_last_observed_fails(self):
        self.after["rows"][0]["LastObservedUTC"] = self.before["rows"][0]["LastObservedUTC"]
        self.assertEqual(verify(self.before, self.after, ["pubmed:123"],now=NOW)["expected_last_observed_not_advanced"], ["pubmed:123"])

    def test_blank_stub_identity_change_fails(self):
        self.after["rows"][1]["SourceKey"] = "pubmed:456"
        self.after["rows"][1]["PMID"] = "456"
        self.assertFalse(verify(self.before, self.after, ["pubmed:123"],now=NOW)["pass"])

    def test_duplicate_and_pmid_mismatch_fail(self):
        self.after["rows"][1]["SourceKey"] = "pubmed:123"
        report = verify(self.before, self.after, ["pubmed:123"],now=NOW)
        self.assertEqual(report["duplicate_keys_after"], ["pubmed:123"])
        self.assertEqual(report["pmid_mismatches_after"], ["pubmed:123"])
        self.assertFalse(report["pass"])

    def test_incomplete_or_missing_field_export_rejected(self):
        self.after["complete"] = False
        with self.assertRaisesRegex(ValueError, "complete=true"):
            verify(self.before, self.after, ["pubmed:123"],now=NOW)
        self.after["complete"] = True
        del self.after["rows"][0]["ReviewNotes"]
        with self.assertRaisesRegex(ValueError, "missing fields"):
            verify(self.before, self.after, ["pubmed:123"],now=NOW)

    def test_duplicate_expected_or_item_id_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate expected"):
            verify(self.before, self.after, ["pubmed:123", "pubmed:123"],now=NOW)
        self.after["rows"].append(item(1, "pubmed:456", "456"))
        self.after["item_count"]=3
        with self.assertRaisesRegex(ValueError, "duplicate item ID"):
            verify(self.before, self.after, ["pubmed:123"],now=NOW)

    def test_exact_item_and_expected_key_types_are_not_normalized(self):
        for value in [True,1,None,' 1','01','0']:
            old=copy.deepcopy(self.after);self.after['rows'][0]['Id']=value
            with self.subTest(value=value),self.assertRaises(ValueError):verify(self.before,self.after,['pubmed:123'],now=NOW)
            self.after=old
        for keys in ['pubmed:123',['pubmed:0'],['pubmed:01'],['pubmed:１２３'],[None],[]]:
            with self.subTest(keys=keys),self.assertRaises(ValueError):verify(self.before,self.after,keys,now=NOW)

    def test_all_policy_fields_and_prior_version_evidence_are_protected(self):
        for field in PROTECTED_MANUAL_FIELDS:
            old=copy.deepcopy(self.after);self.after['rows'][0][field]='changed'
            with self.subTest(field=field):self.assertFalse(verify(self.before,self.after,['pubmed:123'],now=NOW)['pass'])
            self.after=old
        self.after['rows'][0]['versions'][0]['capture_reference']='lost history'
        with self.assertRaisesRegex(ValueError,'history'):verify(self.before,self.after,['pubmed:123'],now=NOW)

    def test_capture_scope_freshness_errors_and_history_completeness_fail_closed(self):
        for changes in [{'item_count':True},{'partial':{}},{'error':{}},{'odata.nextLink':'more'},
                        {'history_complete':False},{'observed_at_utc':'unknown'},
                        {'capture_reference':''},{'target':{}}]:
            old=copy.deepcopy(self.after);self.after.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):verify(self.before,self.after,['pubmed:123'],now=NOW)
            self.after=old

    def test_unknown_row_dates_remain_explicit_uncertainty_without_invented_instants(self):
        for value in [None,'','10/29/2026 00:00:00','2026-10-29T00:00:00-00:00']:
            old=copy.deepcopy(self.after);self.after['rows'][0]['LastObservedUTC']=value
            before=copy.deepcopy(self.after);result=verify(self.before,self.after,['pubmed:123'],now=NOW)
            self.assertFalse(result['pass']);self.assertTrue(result['preservation_or_timestamp_changes'])
            self.assertEqual(self.after,before);self.after=old

    def test_cli_is_portable_exclusive_and_invalid_inputs_leave_no_final_report(self):
        from scripts import verify_publication_replay as module
        from contextlib import redirect_stderr
        import io,json,tempfile,sys,subprocess
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();private=root/'private';private.mkdir()
            a,b,keys,out=[private/n for n in ['a.json','b.json','keys.json','out.json']]
            for path,value in [(a,self.before),(b,self.after),(keys,['pubmed:123'])]:path.write_text(json.dumps(value))
            args=['--before',str(a),'--after',str(b),'--expected-keys',str(keys),'--output',str(out),'--as-of',NOW.isoformat()]
            with mock.patch.object(module,'ROOT',root),redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(args),0);saved=out.read_bytes()
                self.assertNotEqual(module.main(args),0);self.assertEqual(out.read_bytes(),saved)
                out.unlink();b.write_text('{}');self.assertNotEqual(module.main(args),0);self.assertFalse(out.exists())
            run=subprocess.run([sys.executable,'-S','-B',str(Path(module.__file__).resolve()),'--help'],cwd=root,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)

    def test_advanced_but_stale_processing_stamp_cannot_prove_current_replay(self):
        self.after['rows'][0]['LastObservedUTC']='2026-09-22T01:00:00Z'
        result=verify(self.before,self.after,['pubmed:123'],now=NOW)
        self.assertFalse(result['pass'])
        self.assertEqual(result['expected_last_observed_not_advanced'],['pubmed:123'])


if __name__ == "__main__":
    unittest.main()
