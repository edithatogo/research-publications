import copy
import hashlib
import unittest

from scripts.publication_current_generation_gap import reconcile


class CurrentGenerationGapTests(unittest.TestCase):
    def inputs(self):
        raw = b"<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>1</PMID><Article><ArticleTitle>One</ArticleTitle></Article></MedlineCitation></PubmedArticle><PubmedArticle><MedlineCitation><PMID>2</PMID><Article><ArticleTitle>Two</ArticleTitle></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"
        manifest = {
            "format": "rims-pubmed-full-hedge-commit-v1",
            "source": "pubmed",
            "complete": True,
            "count": 2,
            "pmids": ["1", "2"],
            "files": [
                {
                    "file": "/Retained/page.xml",
                    "ids": ["1", "2"],
                    "saved_readback_equal": True,
                }
            ],
        }
        readback = {
            "status": "PASS_CACHED_PUBMED_XML_IDENTITIES",
            "records": 2,
            "files": [
                {
                    "file": "page.xml",
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "records": 2,
                }
            ],
        }
        commit = {
            "SchemaVersion": 1,
            "Status": "committed",
            "Sources": [
                {"Source": "PubMed", "ExpectedKeys": ["1"], "ExpectedRecords": 1}
            ],
        }
        return manifest, readback, commit, {"page.xml": raw}

    def test_complete_bytes_reconcile_gap_without_admitting_or_claiming_parity(self):
        values = self.inputs()
        before = copy.deepcopy(values)
        result = reconcile(*values)
        self.assertEqual(result["current_keys_missing_from_typed_generation"], ["2"])
        self.assertEqual(result["typed_keys_absent_from_current_raw"], [])
        self.assertFalse(result["typed_metadata_for_new_keys_accepted"])
        self.assertFalse(result["overlapping_metadata_parity_accepted"])
        self.assertEqual(values, before)

    def test_partial_changed_duplicate_or_unbound_evidence_rejected(self):
        for defect in (
            "bytes",
            "order",
            "duplicate",
            "missing",
            "extra",
            "count",
            "commit",
            "proof",
        ):
            manifest, readback, commit, documents = self.inputs()
            if defect == "bytes":
                documents["page.xml"] += b" "
            elif defect == "order":
                manifest["files"][0]["ids"].reverse()
            elif defect == "duplicate":
                manifest["files"].append(copy.deepcopy(manifest["files"][0]))
            elif defect == "missing":
                documents.clear()
            elif defect == "extra":
                documents["other.xml"] = b"other"
            elif defect == "count":
                commit["Sources"][0]["ExpectedRecords"] = True
            elif defect == "commit":
                commit["Status"] = "prepared"
            else:
                readback["files"][0]["sha256"] = "unbound"
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                reconcile(manifest, readback, commit, documents)

    def test_empty_complete_envelope_is_not_a_retained_generation(self):
        manifest, readback, commit, documents = self.inputs()
        raw = b"<PubmedArticleSet />"
        manifest.update(count=0, pmids=[])
        manifest["files"][0]["ids"] = []
        readback.update(records=0)
        readback["files"][0].update(
            bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), records=0
        )
        documents["page.xml"] = raw
        with self.assertRaisesRegex(ValueError, "Nonempty"):
            reconcile(manifest, readback, commit, documents)
