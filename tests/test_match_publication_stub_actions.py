import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.match_publication_stub_actions import correlate


class ActionCorrelationTests(unittest.TestCase):
    def setUp(self):
        self.candidates = {"candidate_count": 2, "items": [{"id": 7}, {"id": 8}]}
        self.actions = {"schema_version": "publication-create-action-outputs/v1", "actions": [
            {"run_id": "run-1", "action_id": "create-1", "status": "Succeeded",
             "created_item_id": 7, "evidence_ref": "private-run#action-1"},
        ]}

    def test_exact_action_id_only(self):
        result = correlate(self.candidates, self.actions)
        self.assertEqual(result["exact_match_count"], 1)
        self.assertEqual(result["items"][0]["grade"], "direct_action_id_match")
        self.assertEqual(result["items"][1]["grade"], "unmatched")
        self.assertFalse(result["disposition_decided"])
        self.assertFalse(result["restore_ready"])

    def test_timestamp_or_cohort_cannot_substitute_for_output_id(self):
        self.actions["actions"][0].pop("created_item_id")
        self.actions["actions"][0]["created_at"] = "2026-09-20T20:00:00Z"
        with self.assertRaisesRegex(ValueError, "item ID"):
            correlate(self.candidates, self.actions)

    def test_duplicate_item_claims_fail(self):
        self.actions["actions"].append({"run_id": "run-2", "action_id": "create-2",
            "status": "Succeeded", "created_item_id": 7, "evidence_ref": "private-run#action-2"})
        with self.assertRaisesRegex(ValueError, "multiple Create outputs"):
            correlate(self.candidates, self.actions)

    def test_noncandidate_outputs_still_require_traceable_unique_evidence(self):
        outside = {"run_id": "run-2", "action_id": "create-2", "status": "Succeeded",
                   "created_item_id": 99, "evidence_ref": "private-run#action-2"}
        self.actions["actions"].append(outside)
        result = correlate(self.candidates, self.actions)
        self.assertEqual(result["noncandidate_action_output_count"], 1)
        self.assertEqual(result["exact_match_count"], 1)
        outside.pop("evidence_ref")
        with self.assertRaisesRegex(ValueError, "evidence reference"):
            correlate(self.candidates, self.actions)
        outside["evidence_ref"] = "private-run#action-2"
        self.actions["actions"].append({**outside, "run_id": "run-3", "action_id": "create-3"})
        with self.assertRaisesRegex(ValueError, "multiple Create outputs"):
            correlate(self.candidates, self.actions)

    def test_failed_action_and_missing_reference_fail(self):
        self.actions["actions"][0]["status"] = "Failed"
        with self.assertRaisesRegex(ValueError, "succeeded"):
            correlate(self.candidates, self.actions)
        self.actions["actions"][0]["status"] = "Succeeded"
        self.actions["actions"][0].pop("evidence_ref")
        with self.assertRaisesRegex(ValueError, "evidence reference"):
            correlate(self.candidates, self.actions)

    def test_cli_rejects_public_output_and_input_overwrite(self):
        repo = Path(__file__).resolve().parent.parent
        private_ops = repo / "private" / "ops"
        private_ops.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_ops) as directory:
            folder = Path(directory)
            candidates = folder / "candidates.json"
            actions = folder / "actions.json"
            candidates.write_text(json.dumps(self.candidates), encoding="utf-8")
            actions.write_text(json.dumps(self.actions), encoding="utf-8")
            command = [sys.executable, str(repo / "scripts" / "match_publication_stub_actions.py"),
                       "--candidates", str(candidates), "--actions", str(actions), "--output"]
            for output, error in ((repo / "public-correlation.json", "ignored private/ops"),
                                  (candidates, "cannot overwrite an input"),
                                  (actions, "cannot overwrite an input")):
                with self.subTest(output=output):
                    result = subprocess.run(command + [str(output)], capture_output=True,
                                            text=True, cwd=repo, check=False)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(error, result.stderr)
            self.assertEqual(json.loads(candidates.read_text()), self.candidates)
            self.assertEqual(json.loads(actions.read_text()), self.actions)
            self.assertFalse((repo / "public-correlation.json").exists())

    def test_strict_ids_counts_and_padded_provenance(self):
        import copy
        for bad in (True, 7.0, '7', ' 7'):
            actions=copy.deepcopy(self.actions); actions['actions'][0]['created_item_id']=bad
            with self.subTest(value=bad), self.assertRaises(ValueError): correlate(self.candidates,actions)
        candidates={'candidate_count':True,'items':[{'id':7}]}
        with self.assertRaises(ValueError): correlate(candidates,self.actions)
        actions=copy.deepcopy(self.actions); actions['actions'][0]['run_id']=' run-1'
        with self.assertRaises(ValueError): correlate(self.candidates,actions)

    def test_correlation_result_cannot_edit_source_provenance(self):
        result=correlate(self.candidates,self.actions)
        result['items'][0]['action']['action_id']='changed'
        self.assertEqual(self.actions['actions'][0]['action_id'],'create-1')


if __name__ == "__main__":
    unittest.main()
