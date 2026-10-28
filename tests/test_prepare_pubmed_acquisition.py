import copy
import hashlib
import json
import unittest

from scripts.prepare_pubmed_acquisition import build, with_daily_updates


class PubMedAcquisitionTests(unittest.TestCase):
    def fixture(self):
        c = {
            "facility_query_version": "test",
            "pubmed": {"enabled": True, "query": '"Example Hospital"[Affiliation]'},
        }
        return build(
            "https://example.sharepoint.com/sites/dev",
            "/Documents/Archive",
            {
                "id": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
                "source": "Embedded",
                "connectionName": "existing",
                "connectionReferenceLogicalName": "existing",
            },
            c,
            {"source": "pubmed"},
        )

    def test_long_hedge_uses_post_and_refuses_truncated_id_list(self):
        a = self.fixture()["properties"]["definition"]["actions"]
        self.assertEqual(a["Search_Before"]["inputs"]["method"], "POST")
        self.assertNotIn("?", a["Search_Before"]["inputs"]["uri"])
        self.assertIn("uriComponent", a["Search_Before"]["inputs"]["body"])
        self.assertIn("['count']", a["Guard_search_Before"]["inputs"])
        self.assertIn("9999", a["Guard_search_Before"]["inputs"])

    def test_complete_xml_saved_before_both_article_and_book_ids_are_reconciled(self):
        a = self.fixture()["properties"]["definition"]["actions"]
        p = a["For_each_batch"]["actions"]
        self.assertEqual(
            p["XML_for_identity"]["runAfter"], {"Verify_xml": ["Succeeded"]}
        )
        self.assertEqual(
            p["Fetched_ids"]["runAfter"], {"XML_for_identity": ["Succeeded"]}
        )
        self.assertEqual(p["Raw_xml"]["inputs"], "@string(body('Fetch_xml'))")
        self.assertIn("PubmedBookArticle", p["Fetched_ids"]["inputs"])
        self.assertEqual(p["Guard_batch"]["runAfter"], {"Fetched_ids": ["Succeeded"]})
        self.assertFalse(a["Manifest"]["inputs"]["downstream_selection_applied"])
        self.assertEqual(a["Manifest"]["runAfter"], {"Guard_complete": ["Succeeded"]})

    def test_daily_full_scope_refetch_preserves_original(self):
        d = self.fixture()
        before = copy.deepcopy(d)
        with self.assertRaisesRegex(ValueError, "manual"):
            with_daily_updates(d)
        self.assertEqual(d, before)
        self.assertEqual(
            d["properties"]["definition"]["actions"]["Manifest"]["inputs"][
                "update_strategy"
            ],
            "full_selected_scope_reconciliation",
        )

    def test_producer_dois_exclude_cited_references_and_checkpoint_follows_manifest(
        self,
    ):
        import xml.etree.ElementTree as ET

        a = self.fixture()["properties"]["definition"]["actions"]
        p = a["For_each_batch"]["actions"]
        expression = p["Own_doi_values"]["inputs"]
        xpath = expression.split(",'", 1)[1].rsplit("')", 1)[0]
        root = ET.fromstring(
            '<PubmedArticleSet><PubmedArticle><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1000/own</ArticleId></ArticleIdList><ReferenceList><Reference><ArticleIdList><ArticleId IdType="doi">10.1000/cited</ArticleId></ArticleIdList></Reference></ReferenceList></PubmedData></PubmedArticle></PubmedArticleSet>'
        )
        found = []
        for branch in xpath.split(" | "):
            path = branch.removeprefix("/PubmedArticleSet/").removesuffix("/text()")
            found.extend(n.text for n in root.findall(path))
        self.assertEqual(found, ["10.1000/own"])
        self.assertEqual(
            a["Save_complete_checkpoint"]["runAfter"],
            {"Verify_manifest": ["Succeeded"]},
        )
        self.assertEqual(
            a["Read_complete_checkpoint"]["runAfter"],
            {"Save_complete_checkpoint": ["Succeeded"]},
        )

    def test_output_scope_cannot_modify_caller_policy_or_collector(self):
        collector = {
            "facility_query_version": "fixture",
            "pubmed": {"enabled": True, "query": '"Example"[Affiliation]'},
        }
        policy = {"source": "pubmed", "nested": {"fixture": True}}
        before = copy.deepcopy((collector, policy))
        result = build(
            "https://example.sharepoint.com/sites/dev",
            "/Documents/archive",
            {
                "id": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
                "source": "Embedded",
                "connectionName": "existing",
                "connectionReferenceLogicalName": "existing",
            },
            collector,
            policy,
        )
        scope = result["properties"]["definition"]["actions"]["Scope"]["inputs"]
        scope["policy"]["nested"]["fixture"] = False
        scope["pubmed"]["query"] = "changed"
        self.assertEqual((collector, policy), before)


class PubMedBoundedRecoveryTests(unittest.TestCase):
    def fixture(self):
        d = PubMedAcquisitionTests().fixture()
        d["properties"]["definition"]["actions"]["Observe_failed_generation"] = {
            "type": "Scope",
            "runAfter": {
                "Verify_complete_checkpoint": ["Failed", "TimedOut", "Skipped"]
            },
            "actions": {
                "Fictional_supplied_scope": {
                    "type": "Compose",
                    "inputs": "fictional preimage only; not native durability evidence",
                }
            },
        }
        return d

    def prepare(self, d, **overrides):
        from scripts.patch_clinicaltrials_read_retries import definition_sha256
        from scripts.prepare_pubmed_acquisition import (
            READ_PATHS,
            with_bounded_read_recovery,
        )

        raw = json.dumps(
            d["properties"]["definition"]["actions"].get("Observe_failed_generation")
        ).encode()
        options = {
            "expected_definition_sha256": definition_sha256(
                d["properties"]["definition"]
            ),
            "selected_paths": READ_PATHS,
            "observer_preimage_bytes": raw,
            "expected_observer_sha256": hashlib.sha256(raw).hexdigest(),
        }
        options.update(overrides)
        return with_bounded_read_recovery(d, **options)

    def test_only_three_read_policy_leaves_change_and_input_is_immutable(self):
        from scripts.patch_clinicaltrials_read_retries import POLICY

        d = self.fixture()
        before = copy.deepcopy(d)
        result = self.prepare(d)
        self.assertEqual(d, before)
        a = result["properties"]["definition"]["actions"]
        for node in [
            a["Search_Before"],
            a["Search_After"],
            a["For_each_batch"]["actions"]["Fetch_xml"],
        ]:
            self.assertEqual(node["inputs"]["retryPolicy"], POLICY)
            node["inputs"]["retryPolicy"] = {"type": "none"}
        self.assertEqual(result, d)

    def test_refuses_drift_and_already_recovered_graph(self):
        from scripts.prepare_pubmed_acquisition import with_bounded_read_recovery

        with self.assertRaisesRegex(ValueError, "drift"):
            with_bounded_read_recovery(
                self.fixture(), expected_definition_sha256="0" * 64
            )
        with self.assertRaisesRegex(ValueError, "preimage"):
            self.prepare(self.prepare(self.fixture()))

    def test_refuses_other_hosts_or_write_payload(self):
        for change in ["uri", "body", "method"]:
            d = self.fixture()
            n = d["properties"]["definition"]["actions"]["Search_Before"]["inputs"]
            n[change] = {
                "uri": "https://example.org/esearch.fcgi",
                "body": "write=record",
                "method": "DELETE",
            }[change]
            with (
                self.subTest(change=change),
                self.assertRaisesRegex(ValueError, "preimage"),
            ):
                self.prepare(d)

    def test_requires_existing_failure_scope_and_source_contract(self):
        d = self.fixture()
        del d["properties"]["definition"]["actions"]["Observe_failed_generation"]
        with self.assertRaisesRegex(ValueError, "failed-generation"):
            self.prepare(d)

    def test_explicit_observer_bytes_and_selection_required(self):
        from scripts.patch_clinicaltrials_read_retries import definition_sha256
        from scripts.prepare_pubmed_acquisition import with_bounded_read_recovery

        d = self.fixture()
        before = copy.deepcopy(d)
        with self.assertRaises(ValueError):
            with_bounded_read_recovery(
                d,
                expected_definition_sha256=definition_sha256(
                    d["properties"]["definition"]
                ),
            )
        self.assertEqual(d, before)

    def test_search_body_suffix_and_unexpected_input_are_not_retryable(self):
        for field, value in [
            ("body", "@concat('db=pubmed&retmode=json&write=record')"),
            (
                "headers",
                {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "text/plain",
                },
            ),
            ("authentication", "invented"),
        ]:
            d = self.fixture()
            node = d["properties"]["definition"]["actions"]["Search_Before"]["inputs"]
            node[field] = value
            before = copy.deepcopy(d)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.prepare(d)
            self.assertEqual(d, before)

    def test_selected_read_and_observer_hash_do_not_expand_or_fabricate_scope(self):
        d = self.fixture()
        before = copy.deepcopy(d)
        new = self.prepare(d, selected_paths=(("Search_Before",),))
        self.assertEqual(
            new["properties"]["definition"]["actions"]["Search_After"],
            before["properties"]["definition"]["actions"]["Search_After"],
        )
        self.assertEqual(
            new["properties"]["definition"]["actions"]["Observe_failed_generation"],
            before["properties"]["definition"]["actions"]["Observe_failed_generation"],
        )
        for overrides in (
            {"expected_observer_sha256": "0" * 64},
            {
                "observer_preimage_bytes": b"{}",
                "expected_observer_sha256": hashlib.sha256(b"{}").hexdigest(),
            },
            {"selected_paths": (("Save_complete_checkpoint",),)},
        ):
            with self.subTest(overrides=list(overrides)), self.assertRaises(ValueError):
                self.prepare(d, **overrides)
            self.assertEqual(d, before)
        d = self.fixture()
        d["properties"]["definition"]["actions"]["Manifest"]["inputs"]["source"] = (
            "other"
        )
        with self.assertRaisesRegex(ValueError, "PubMed"):
            self.prepare(d)
