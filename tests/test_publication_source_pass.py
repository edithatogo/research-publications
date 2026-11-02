import io
import json
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publication_source_pass as enrich


class Response(io.BytesIO):
    def __init__(self, raw):
        super().__init__(raw)
        self.headers = {"x-ratelimit-remaining-usd": "0.09"}


class EnrichmentTests(unittest.TestCase):
    def test_deduplicated_queries_and_complete_replay(self):
        rows = [
            {"DOI": "10.1234/A"},
            {"DOI": "https://doi.org/10.1234/a"},
            {"DOI": "10.1234/b"},
        ]
        work = {"doi": "10.1234/a", "id": "W1", "nested": [{"value": 0}]}
        data = {"meta": {"count": 1}, "results": [work]}
        with tempfile.TemporaryDirectory() as temp:
            for replay in (False, True):
                retained = defaultdict(dict)
                with patch.object(
                    enrich, "urlopen", return_value=Response(json.dumps(data).encode())
                ) as request:
                    statuses = enrich.collect_openalex(rows, retained, Path(temp))
                    self.assertEqual(request.call_count, 0 if replay else 1)
                self.assertEqual(
                    statuses, {"10.1234/a": "fresh", "10.1234/b": "no match"}
                )
                self.assertEqual(retained["10.1234/a"]["W1"]["record"], work)
                self.assertIn("nested[].value", set(enrich.field_paths(work)))

    def test_mismatched_doi_never_joins(self):
        data = {"meta": {"count": 1}, "results": [{"doi": "10.1234/other"}]}
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(
                enrich, "urlopen", return_value=Response(json.dumps(data).encode())
            ),
        ):
            retained = defaultdict(dict)
            self.assertEqual(
                enrich.collect_openalex([{"DOI": "10.1234/a"}], retained, Path(temp)),
                {"10.1234/a": "failed"},
            )
            self.assertFalse(retained)

    def test_quota_stop_then_resume_from_first_unfinished_batch(self):
        rows = [{"DOI": f"10.1234/{i:02d}"} for i in range(26)]
        empty = json.dumps({"meta": {"count": 0}, "results": []}).encode()
        first = Response(empty)
        first.headers = {"x-ratelimit-remaining-usd": "0"}
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(enrich, "urlopen", return_value=first) as request:
                self.assertEqual(len(enrich.collect_openalex(rows, {}, Path(temp))), 25)
                self.assertEqual(request.call_count, 1)
            with patch.object(
                enrich, "urlopen", return_value=Response(empty)
            ) as request:
                self.assertEqual(len(enrich.collect_openalex(rows, {}, Path(temp))), 26)
                self.assertEqual(request.call_count, 1)
