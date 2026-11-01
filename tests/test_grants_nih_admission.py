"""The selected read-only POST must never expand into a generic POST client."""
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock

from scripts.grants_sources import qualification_error, source_request_contract
from scripts.grants_source_probe import _probe_row
from scripts.grants_ingestion import ingest_batches

ROOT = Path(__file__).resolve().parents[1]


class NIHAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.row = next(row for row in json.loads(
            (ROOT / "config/grants-sources.json").read_text())
            if row["source_id"] == "us-grants-gov-nih-pa-25-301")

        self.assertFalse(self.row["enabled"])
        # Exercise the archived request contract only with a local fixture.
        self.row = {**self.row, "enabled": True}

    def test_selected_scope_has_complete_admission_evidence(self):
        self.assertIsNone(qualification_error(self.row, require_opportunity=True))
        method, body = source_request_contract(self.row)
        self.assertEqual(method, "POST")
        self.assertEqual(body["oppNum"], "PA-25-301")
        self.assertEqual(set(body["oppStatuses"].split("|")),
                         {"forecasted", "posted", "closed", "archived"})
        body["oppNum"] = "changed"
        self.assertEqual(source_request_contract(self.row)[1]["oppNum"], "PA-25-301")

    def test_changed_or_broadened_request_is_rejected_before_network(self):
        changes = [
            {"request_method": "GET"}, {"request_method": "DELETE"},
            {"api_url": "https://api.grants.gov/v1/api/other"},
            {"request_body": {"oppNum": ""}},
            {"request_body": {**self.row["request_body"], "keyword": "research"}},
            {"reconciliation": None},
        ]
        for change in changes:
            with self.subTest(change=change):
                row = {**copy.deepcopy(self.row), **change}
                opener = Mock(side_effect=AssertionError("network must not be called"))
                with self.assertRaisesRegex(ValueError, "scope must remain exact"):
                    _probe_row(row, opener)
                opener.assert_not_called()

    def test_generic_post_is_not_authorised_by_catalogue_metadata(self):
        row = {**self.row, "source_id": "another-api"}
        with self.assertRaisesRegex(ValueError, "unsupported source request"):
            source_request_contract(row)

    def test_matching_id_does_not_hide_api_query_or_lifecycle_drift(self):
        valid = {"errorcode": 0, "data": {
            "searchParams": copy.deepcopy(self.row["request_body"]),
            "hitCount": 1, "startRecord": 0,
            "oppHits": [{"id": "357812", "number": "PA-25-301", "oppStatus": "posted"}],
        }}
        for change in ("error", "total", "offset", "status", "number", "query"):
            with self.subTest(change=change):
                payload = copy.deepcopy(valid)
                if change == "error": payload["errorcode"] = 1
                if change == "total": payload["data"]["hitCount"] = 2
                if change == "offset": payload["data"]["startRecord"] = 10
                if change == "status": payload["data"]["oppHits"][0]["oppStatus"] = "closed"
                if change == "number": payload["data"]["oppHits"][0]["number"] = "different"
                if change == "query": payload["data"]["searchParams"]["oppNum"] = ""
                response = io.BytesIO(json.dumps(payload).encode())
                response.headers = {"Content-Type": "application/json"}
                response.geturl = lambda: self.row["api_url"]
                response.getcode = lambda: 200
                result = _probe_row(self.row, lambda *args, **kwargs: response)
                self.assertFalse(result["reconciled"])
                self.assertEqual(result["reason"], "selected_nih_query_or_lifecycle_drift")

    def test_independent_ingestion_rejects_request_scope_drift(self):
        row = copy.deepcopy(self.row)
        row["request_body"]["oppNum"] = "another-announcement"
        batch = {"source": row["source_id"], "retrieved_at": "2026-10-24T00:00:00Z",
                 "pagination": {"total_pages": 1, "pages_received": [1], "complete": True},
                 "records": []}
        result = ingest_batches([batch], catalogue=[row])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["health"][0]["error"], "invalid_catalogue_row")

    def test_context_rows_do_not_block_an_independent_opportunity_batch(self):
        # Synthetic record only; no network or native storage is involved.
        catalogue = json.loads((ROOT / "config/grants-sources.json").read_text())
        fixture = copy.deepcopy(self.row)
        fixture.update(source_id="fixture-opportunity", request_method="GET",
                       api_url="https://example.org/api", official_row_hosts=["example.org"])
        fixture.pop("request_body")
        fixture["reconciliation"]["source_id_path"] = "data[].id"
        batch = {"source": "fixture-opportunity", "retrieved_at": "2026-10-24T00:00:00Z",
                 "pagination": {"total_pages": 1, "pages_received": [1], "complete": True},
                 "records": [{"SourceID": "synthetic-1", "Title": "Synthetic opportunity",
                              "URL": "https://example.org/synthetic-1"}]}
        result = ingest_batches([batch], catalogue=[*catalogue, fixture])
        self.assertTrue(result["accepted"], result["health"])
        self.assertEqual(len(result["records"]), 1)


if __name__ == "__main__":
    unittest.main()
