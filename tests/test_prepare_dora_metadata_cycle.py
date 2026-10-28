"""Synthetic same-generation source/replay cases; no native acceptance claim."""

import copy
import hashlib
import json
import unittest

from scripts.prepare_dora_metadata_cycle import (
    DORA_CHECKS,
    current_validation_query,
    prepare,
)
from scripts.publication_retained_cycle import retain
from scripts.publication_source_metadata_contract import page_query
from scripts.verify_retained_canary_metadata_values import _dora

URL = "https://dora.health.qld.gov.au/qldresearchjspui/handle/1/123"


def fields(url=URL, rss=False):
    result = [
        {"Field": "dc.identifier.uri", "Value": url},
        {"Field": "dc.title", "Value": "Title"},
        {"Field": "dc.contributor.author", "Value": "Author"},
    ]
    return result + (
        [
            {"Field": "rims.source.format", "Value": "dora_rss_v1"},
            {"Field": "rims.rss.pubDate", "Value": "2026-10-11"},
        ]
        if rss
        else [
            {"Field": "dc.date.issued", "Value": "2020"},
            {"Field": "dc.description.abstract", "Value": "Rich abstract"},
            {"Field": "dc.identifier.doi", "Value": "10.1234/retained"},
        ]
    )


def record(metadata):
    url = next(f["Value"] for f in metadata if f["Field"] == "dc.identifier.uri")
    return {
        "DORAKey": "DORA:" + url,
        "DORAURL": url,
        "PublicationDate": None,
        **_dora(metadata),
        "MetadataJSON": json.dumps(metadata),
    }


class DoraMetadataCycleTests(unittest.TestCase):
    def setUp(self):
        self.state = retain(
            None,
            [("42", {"Title": "PubMed old", "MetadataJSON": "[]"})],
            generation="seed-pubmed",
            observed_at="2020-01-01T00:00:00Z",
            source="PubMed",
            complete=True,
        )
        self.state = retain(
            self.state,
            [("DORA:" + URL, record(fields()))],
            generation="seed-dora",
            observed_at="2020-01-01T00:00:00Z",
            source="DORA",
            complete=True,
        )
        self.generation = {
            "generation": "new-generation",
            "modelId": "fixture-model",
            "refreshRequestId": "fixture-request",
            "refreshStatus": "Completed",
            "refreshComplete": True,
            "extractionComplete": True,
            "refreshCompletedAtUTC": "2026-10-11T01:00:00Z",
        }

    def inputs(self, metadata=None):
        metadata = (
            [fields(), fields(URL.replace("/123", "/456"), True)]
            if metadata is None
            else metadata
        )
        summaries, chunks = [], []
        for doc in metadata:
            rec = record(doc)
            key = rec["DORAKey"]
            summaries.append(
                {f"[{k}]": v for k, v in rec.items() if k != "MetadataJSON"}
            )
            hex_value = rec["MetadataJSON"].encode().hex()
            chunks.append(
                {
                    "[DORAKey]": key,
                    "[ChunkIndex]": 0,
                    "[ChunkCount]": 1,
                    "[MetadataCharacters]": len(hex_value),
                    "[MetadataChunk]": hex_value,
                    "[Encoding]": "UTF8-HEX",
                }
            )
        sources = {}
        for table, rows, key_fields in [
            ("DoraPublications", summaries, ("DORAKey",)),
            ("DoraMetadataChunks", chunks, ("DORAKey", "ChunkIndex")),
        ]:
            rows.sort(key=lambda r: tuple(r[f"[{k}]"] for k in key_fields))
            cursor = None
            pages = []
            for batch in [rows, []]:
                query = page_query(table, cursor)
                pages.append(
                    {
                        "page_number": len(pages),
                        "http": 200,
                        "query": query,
                        "query_sha256": hashlib.sha256(query.encode()).hexdigest(),
                        "body": {"results": [{"tables": [{"rows": batch}]}]},
                    }
                )
                if batch:
                    cursor = [batch[-1][f"[{k}]"] for k in key_fields]
            sources[table] = {"page_size": 100, "pages": pages}
        receipt = {
            "kind": "native_source_page_extraction_v1",
            "model_id": "fixture-model",
            "request_id": "fixture-request",
            "generation": "new-generation",
            "refresh_status": "Completed",
            "latest_request_before": "fixture-request",
            "latest_request_after": "fixture-request",
            "refreshed_tables": [
                "DoraPublications",
                "DoraMetadataChunks",
                "DoraIngestionAudit",
            ],
            "sources": sources,
        }
        values = {
            "CurrentRows": len(summaries),
            "DistinctCurrentKeys": len(summaries),
            "MetadataRows": len(chunks),
            "MetadataCharacters": sum(len(c["[MetadataChunk]"]) for c in chunks),
            "DistinctMetadataKeys": len(summaries),
            "MissingMetadataKeys": 0,
            "UnexpectedMetadataKeys": 0,
            "AuditRows": len(DORA_CHECKS),
            "AuditCheckCount": len(DORA_CHECKS),
            "AuditFailures": 0,
            "AuditNullCount": 0,
            "CurrentKeysJSON": json.dumps(
                sorted(r["[DORAKey]"] for r in summaries), separators=(",", ":")
            ),
            "AuditCheckNamesJSON": json.dumps(
                sorted(DORA_CHECKS), separators=(",", ":")
            ),
        }
        validation = {
            "kind": "native_dora_current_validation_v1",
            "http": 200,
            "model_id": "fixture-model",
            "request_id": "fixture-request",
            "refresh_status": "Completed",
            "query_sha256": hashlib.sha256(
                current_validation_query().encode()
            ).hexdigest(),
            "body": {
                "results": [
                    {"tables": [{"rows": [{f"[{k}]": v for k, v in values.items()}]}]}
                ]
            },
        }
        return receipt, validation

    def test_engine_display_normalization_preserves_raw_metadata_and_rejects_substantive_change(
        self,
    ):
        pages, validation = self.inputs()
        row = pages["sources"]["DoraPublications"]["pages"][0]["body"]["results"][0][
            "tables"
        ][0]["rows"][0]
        row["[Title]"] = "title "
        candidate, _ = prepare(pages, self.generation, validation, self.state)
        self.assertTrue(
            any(
                '"Value": "Title"' in version["Record"]["MetadataJSON"]
                for version in candidate["versions"]
            )
        )
        row["[Title]"] = "Unrelated title"
        with self.assertRaisesRegex(ValueError, "summary fields differ"):
            prepare(pages, self.generation, validation, self.state)

    def test_model_collation_order_preserves_exact_audit_identity_coverage(self):
        pages, validation = self.inputs()
        values = validation["body"]["results"][0]["tables"][0]["rows"][0]
        values["[AuditCheckNamesJSON]"] = json.dumps(
            sorted(DORA_CHECKS, key=str.casefold), separators=(",", ":")
        )
        _, receipt = prepare(pages, self.generation, validation, self.state)
        self.assertEqual(receipt["Records"], 2)
        names = json.loads(values["[AuditCheckNamesJSON]"])
        names[-1] = names[0]
        values["[AuditCheckNamesJSON]"] = json.dumps(names)
        with self.assertRaisesRegex(ValueError, "identities differ"):
            prepare(pages, self.generation, validation, self.state)

    def test_new_metadata_appends_existing_two_source_state_and_exact_replay(self):
        pages, validation = self.inputs()
        before = copy.deepcopy(self.state)
        candidate, receipt = prepare(pages, self.generation, validation, self.state)
        self.assertEqual(self.state, before)
        self.assertEqual(
            candidate["versions"][: len(before["versions"])], before["versions"]
        )
        self.assertEqual(
            candidate["latest"]["pubmed:42"], before["latest"]["pubmed:42"]
        )
        self.assertEqual(receipt["Records"], 2)
        self.assertEqual(candidate["cycles"][-1]["BatchID"], receipt["BatchID"])
        self.assertEqual(receipt["SourceDescriptor"]["Source"], "DORA")
        self.assertFalse(receipt["batch_commit_written"])
        self.assertEqual(
            prepare(pages, self.generation, validation, candidate)[0], candidate
        )
        added = candidate["versions"][
            candidate["latest"]["dora:" + URL.replace("/123", "/456")]
        ]["Record"]
        self.assertEqual(
            (added["PublicationDatePrecision"], added["PublicationYear"]),
            ("unknown", None),
        )

    def test_sparse_same_key_cannot_erase_rich_metadata(self):
        pages, validation = self.inputs([fields(rss=True)])
        before = copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError, "Sparse RSS"):
            prepare(pages, self.generation, validation, self.state)
        self.assertEqual(self.state, before)

    def test_missing_history_or_partial_chunks_reject_without_mutation(self):
        pages, validation = self.inputs([fields(URL.replace("/123", "/456"), True)])
        with self.assertRaisesRegex(ValueError, "lost an accepted"):
            prepare(pages, self.generation, validation, self.state)
        pages, validation = self.inputs()
        pages["sources"]["DoraMetadataChunks"]["pages"][0]["body"]["results"][0][
            "tables"
        ][0]["rows"][0]["[ChunkCount]"] = 2
        before = copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            prepare(pages, self.generation, validation, self.state)
        self.assertEqual(self.state, before)

    def test_field_audit_or_generation_mismatch_rejects_candidate(self):
        for kind in ("field", "audit", "generation"):
            pages, validation = self.inputs()
            if kind == "field":
                pages["sources"]["DoraPublications"]["pages"][0]["body"]["results"][0][
                    "tables"
                ][0]["rows"][0]["[Title]"] = "Mismatch"
            elif kind == "audit":
                validation["body"]["results"][0]["tables"][0]["rows"][0][
                    "[AuditRows]"
                ] = 99
            else:
                pages["latest_request_after"] = "other-request"
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                prepare(pages, self.generation, validation, self.state)

    def test_changed_content_under_same_generation_refuses_replay(self):
        pages, validation = self.inputs()
        candidate, _ = prepare(pages, self.generation, validation, self.state)
        revised = fields()
        revised.append(
            {"Field": "dc.identifier.journaltitle", "Value": "New full-source journal"}
        )
        pages, validation = self.inputs(
            [revised, fields(URL.replace("/123", "/456"), True)]
        )
        with self.assertRaisesRegex(ValueError, "Replayed generation"):
            prepare(pages, self.generation, validation, candidate)

    def test_existing_batch_identity_cannot_be_reassigned(self):
        pages, validation = self.inputs()
        candidate, _ = prepare(pages, self.generation, validation, self.state)
        candidate["cycles"][-1]["BatchID"] = "another-batch"
        with self.assertRaisesRegex(ValueError, "another immutable batch"):
            prepare(pages, self.generation, validation, candidate)


if __name__ == "__main__":
    unittest.main()
