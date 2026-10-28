"""Full-source offline proofs; no provider, native operation or review mutation."""

import copy
import hashlib
import json
import unittest
import xml.etree.ElementTree as ET

from scripts.build_native_commit_package import validate_retained_typed_archive
from scripts.publication_xml_metadata import article_metadata, compare_metadata
from scripts.reconcile_pubmed_source_cycle import prepare_offline_typed_candidate


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def article(key="1", title="Old", extra=""):
    return f'<PubmedArticle><MedlineCitation Owner="NLM"><PMID Version="1">{key}</PMID><Article><Journal><Title>Journal</Title><JournalIssue><PubDate><Year>2026</Year><Month>Oct</Month></PubDate></JournalIssue></Journal><ArticleTitle>{title}</ArticleTitle><AuthorList><Author><LastName>Person</LastName><ForeName>A</ForeName><AffiliationInfo><Affiliation>First</Affiliation></AffiliationInfo><AffiliationInfo><Affiliation>Second</Affiliation></AffiliationInfo></Author><Author><CollectiveName>Group</CollectiveName></Author></AuthorList><Abstract><AbstractText Label="BACKGROUND">Text &amp; data.</AbstractText></Abstract></Article>{extra}</MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1234/example</ArticleId></ArticleIdList></PubmedData></PubmedArticle>'


def inputs():
    old_article = article()
    metadata = article_metadata(ET.fromstring(old_article))["MetadataJSON"]
    wire = metadata.encode().hex().upper()
    chunks = [
        {
            "[PMID]": "1",
            "[ChunkIndex]": 0,
            "[ChunkCount]": 1,
            "[MetadataCharacters]": len(wire),
            "[Encoding]": "UTF8-HEX",
            "[MetadataChunk]": wire,
        }
    ]
    summary = [
        {
            "[PMID]": "1",
            "[Title]": "Reviewer title",
            "[ReviewNotes]": "Preserve reviewer note",
        }
    ]
    authors = [
        {
            "[PMID]": "1",
            "[AuthorIndex]": 1,
            "[AffiliationIndex]": 1,
            "[AuthorName]": "A Person",
            "[AffiliationText]": "First",
            "[EvidenceKind]": "Prior evidence",
        }
    ]
    tables = {
        "PubMedPublications": summary,
        "PubMedMetadataChunks": chunks,
        "PubMedAuthorEvidence": authors,
    }
    pages = {
        "generation": "prior",
        "model_id": "fixture-model",
        "request_id": "fixture-request",
        "sources": {},
    }
    files, entries = {}, []
    for table, rows in tables.items():
        query = "EVALUATE " + table
        pages["sources"][table] = {
            "page_size": 100,
            "pages": [
                {
                    "page_number": number,
                    "http": 200,
                    "query": query,
                    "query_sha256": hashlib.sha256(query.encode()).hexdigest(),
                    "body": {"results": [{"tables": [{"rows": current}]}]},
                }
                for number, current in enumerate((rows, []))
            ],
        }
        name = table + ".json"
        content = encoded(rows)
        files[name] = content
        entries.append(
            {
                "table": table,
                "name": name,
                "rows": len(rows),
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    source_bytes = encoded(pages)
    receipt = {
        "batch_id": "fixture-batch",
        "capture_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "reconstruction_equal": True,
        "files": entries,
        "file_count": len(entries),
        "totals": {table: len(rows) for table, rows in tables.items()},
    }
    payload = [["1", hashlib.sha256(metadata.encode()).hexdigest()]]
    commit = {
        "SchemaVersion": 1,
        "Status": "committed",
        "BatchID": "fixture-batch",
        "Generation": "prior",
        "ModelID": "fixture-model",
        "RefreshRequestID": "fixture-request",
        "Sources": [{"Source": "PubMed", "ExpectedRecords": 1, "ExpectedKeys": ["1"]}],
        "SourceExtraction": {
            "MetadataPayloadSHA256": hashlib.sha256(encoded(payload)).hexdigest(),
            "MetadataPayloadCharacters": len(wire),
        },
    }
    key_hash = hashlib.sha256(encoded(["1"])).hexdigest()
    commit["SourceExtraction"].update(
        MetadataChunkCount=1,
        AuthorEvidenceRowCount=1,
        PublicationKeySHA256=key_hash,
        MetadataKeySHA256=key_hash,
        AuthorEvidenceKeySHA256=hashlib.sha256(encoded([["1", 1, 1]])).hexdigest(),
    )
    raw = (
        "<PubmedArticleSet>"
        + article(
            title="New <i>title</i>",
            extra='<Unknown Attribute="kept">Full source</Unknown>',
        )
        + article("2", "New identity")
        + "</PubmedArticleSet>"
    ).encode()
    manifest = {
        "format": "rims-pubmed-full-hedge-commit-v1",
        "source": "pubmed",
        "complete": True,
        "count": 2,
        "pmids": ["1", "2"],
        "files": [{"file": "raw.xml", "ids": ["1", "2"], "saved_readback_equal": True}],
    }
    readback = {
        "status": "PASS_CACHED_PUBMED_XML_IDENTITIES",
        "records": 2,
        "files": [
            {
                "file": "raw.xml",
                "records": 2,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        ],
    }
    return manifest, readback, commit, {"raw.xml": raw}, receipt, source_bytes, files


class OfflineTypedCandidateTests(unittest.TestCase):
    def test_complete_candidate_preserves_unknown_metadata_attributes_and_review_context(
        self,
    ):
        args = inputs()
        before = copy.deepcopy(args)
        candidate, receipt, changes = prepare_offline_typed_candidate(*args)
        self.assertEqual(args, before)
        self.assertEqual(receipt["counts"]["source_rows"], 2)
        self.assertEqual(receipt["counts"]["author_evidence_rows"], 6)
        self.assertEqual(receipt["counts"]["metadata_kinds"]["new_source_identity"], 1)
        self.assertIn("Unknown", candidate["records"]["1"]["MetadataJSON"])
        self.assertIn("Attribute", candidate["records"]["1"]["ArticleXML"])
        self.assertEqual(
            candidate["records"]["1"]["PreservedPriorSummaryContext"]["[ReviewNotes]"],
            "Preserve reviewer note",
        )
        self.assertEqual(candidate["source_rows"][0]["Title"], "New title")
        self.assertTrue(
            any(
                row["AffiliationText"] is None and row["AuthorName"] == "Group"
                for row in candidate["author_evidence"]
            )
        )
        self.assertFalse(receipt["native_admission_accepted"])
        self.assertFalse(candidate["registry_reviews_changed"])
        self.assertTrue(changes[0]["metadata"]["differences"])
        self.assertEqual(prepare_offline_typed_candidate(*args)[1], receipt)

    def test_typed_byte_capture_payload_and_generation_drift_rejected(self):
        for defect in ("file", "capture", "payload", "generation", "file-coverage"):
            args = list(inputs())
            if defect == "file":
                args[6]["PubMedPublications.json"] += b" "
            elif defect == "capture":
                args[5] += b" "
            elif defect == "payload":
                args[2]["SourceExtraction"]["MetadataPayloadSHA256"] = "drift"
            elif defect == "generation":
                args[2]["Generation"] = "different"
            else:
                args[6]["unbound.json"] = b"[]"
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                prepare_offline_typed_candidate(*args)

    def test_nested_error_cannot_be_rebound_as_a_valid_typed_capture(self):
        args = list(inputs())
        pages = json.loads(args[5])
        pages["sources"]["PubMedPublications"]["pages"][0]["body"]["results"][0][
            "tables"
        ][0]["error"] = {}
        args[5] = encoded(pages)
        args[4]["capture_sha256"] = hashlib.sha256(args[5]).hexdigest()
        with self.assertRaisesRegex(ValueError, "envelope"):
            validate_retained_typed_archive(args[2], args[4], args[5], args[6])

    def test_full_metadata_attribute_and_unknown_leaf_changes_are_visible(self):
        previous = json.loads(
            article_metadata(
                ET.fromstring(article(extra='<Unknown Flag="old">Value</Unknown>'))
            )["MetadataJSON"]
        )
        current = json.loads(
            article_metadata(
                ET.fromstring(article(extra='<Unknown Flag="new">Changed</Unknown>'))
            )["MetadataJSON"]
        )
        delta = compare_metadata(previous, current)
        self.assertEqual(delta["kind"], "metadata_difference_preserved")
        self.assertTrue(any("@{}Flag" in row["path"] for row in delta["differences"]))
        self.assertTrue(
            any(row["current"] == "Changed" for row in delta["differences"])
        )

    def test_mixed_markup_normalization_is_explicit_and_never_drops_differences(self):
        previous = [
            {
                "Name": "ArticleTitle",
                "Namespace": "",
                "Attributes": [],
                "Value": 'A <i x="1" y="2">word</i> tail',
            }
        ]
        current = copy.deepcopy(previous)
        current[0]["Value"] = 'A <i y="2" x="1">word</i> tail'
        delta = compare_metadata(previous, current)
        self.assertEqual(delta["kind"], "xml_serialization_representation_only")
        self.assertEqual(len(delta["differences"]), 1)
        current[0]["Value"] = 'A <i y="2" x="1">different</i> tail'
        self.assertEqual(
            compare_metadata(previous, current)["kind"], "metadata_difference_preserved"
        )

    def test_duplicate_attributes_and_non_xml_value_types_fail_closed(self):
        node = {"Name": "X", "Namespace": "", "Attributes": [], "Value": "v"}
        for defect in ("value", "attribute"):
            changed = copy.deepcopy(node)
            if defect == "value":
                changed["Value"] = True
            else:
                changed["Attributes"] = [
                    {"Name": "A", "Namespace": "", "Value": "1"}
                ] * 2
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                compare_metadata([node], [changed])

    def test_entities_empty_elements_and_inline_markup_have_bounded_representation_parity(
        self,
    ):
        prior = [
            {"Name": "Text", "Namespace": "", "Attributes": [], "Value": "A &#38; B"},
            {"Name": "Empty", "Namespace": "", "Attributes": [], "Value": []},
        ]
        current = copy.deepcopy(prior)
        current[0]["Value"] = "A &amp; B"
        current[1]["Value"] = ""
        self.assertEqual(
            compare_metadata(prior, current)["kind"],
            "xml_serialization_representation_only",
        )
        # Literal encoded tags must not become actual formatted elements.
        current[0]["Value"] = "&lt;i&gt;word&lt;/i&gt;"
        prior[0]["Value"] = "<i>word</i>"
        self.assertEqual(
            compare_metadata(prior, current)["kind"], "metadata_difference_preserved"
        )

    def test_missing_terminal_page_is_not_repaired_by_rehashing_capture(self):
        args = list(inputs())
        pages = json.loads(args[5])
        pages["sources"]["PubMedMetadataChunks"]["pages"].pop()
        args[5] = encoded(pages)
        args[4]["capture_sha256"] = hashlib.sha256(args[5]).hexdigest()
        with self.assertRaisesRegex(ValueError, "terminal"):
            validate_retained_typed_archive(args[2], args[4], args[5], args[6])

    def test_root_attributes_and_nested_unknown_source_elements_remain_in_capture(self):
        source = ET.fromstring(
            article(extra='<Unknown><Nested X="1">Unmapped</Nested></Unknown>')
        )
        source.set("FutureAttribute", "retained")
        captured = article_metadata(source)
        self.assertIn('FutureAttribute="retained"', captured["ArticleXML"])
        self.assertIn("Nested", captured["MetadataJSON"])
        self.assertEqual(
            hashlib.sha256(captured["ArticleXML"].encode()).hexdigest(),
            captured["ArticleXMLSHA256"],
        )

    def test_partial_flag_and_committed_author_digest_fail_closed(self):
        for defect in ("partial", "author_digest", "author_count"):
            args = list(inputs())
            if defect == "partial":
                pages = json.loads(args[5])
                pages["sources"]["PubMedPublications"]["pages"][0]["body"][
                    "partial"
                ] = True
                args[5] = encoded(pages)
                args[4]["capture_sha256"] = hashlib.sha256(args[5]).hexdigest()
            elif defect == "author_digest":
                args[2]["SourceExtraction"]["AuthorEvidenceKeySHA256"] = "drift"
            else:
                args[2]["SourceExtraction"]["AuthorEvidenceRowCount"] = True
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                validate_retained_typed_archive(args[2], args[4], args[5], args[6])
