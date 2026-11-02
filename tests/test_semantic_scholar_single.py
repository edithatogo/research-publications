import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import collect_semantic_scholar_publications as collector
from export_publication_register import key_hash


class Response(io.BytesIO):
    status = 200


class SingleCollectionTests(unittest.TestCase):
    def options(self, root):
        rows = [{"CanonicalKey": "PMID:42", "PMID": "42", "DOI": "10.1234/abc"}]
        canonical = root / "canonical.json"
        canonical.write_text(
            json.dumps(
                {
                    "records": rows,
                    "expected_canonical_count": 1,
                    "expected_key_sha256": key_hash(rows),
                }
            )
        )
        return SimpleNamespace(
            canonical=canonical,
            output=root / "cache",
            bootstrap=None,
            replay_only=False,
            transport="single",
            interval=2,
            max_throttle_retries=2,
        )

    def test_throttle_wait_and_verified_cache_replay(self):
        error = HTTPError(
            "https://api.semanticscholar.org/",
            429,
            "Limited",
            {"Retry-After": "90"},
            io.BytesIO(b"{}"),
        )
        paper = {
            "paperId": "synthetic",
            "externalIds": {"DOI": "10.1234/abc", "PubMed": "42"},
        }
        with tempfile.TemporaryDirectory() as temp:
            options = self.options(Path(temp))
            with (
                patch.object(
                    collector,
                    "urlopen",
                    side_effect=[error, Response(json.dumps(paper).encode())],
                ) as network,
                patch.object(collector, "wait_for_cooldown") as wait,
            ):
                collector.collect(options)
                self.assertEqual(network.call_count, 2)
                self.assertEqual(
                    network.call_args.args[0].full_url,
                    "https://api.semanticscholar.org/graph/v1/paper/DOI:10.1234/abc?fields=" + collector.FIELDS,
                )
                self.assertIn(90, [call.args[0] for call in wait.call_args_list])
            result = json.loads((options.output / "coverage.json").read_bytes())
            self.assertEqual(result["counts"], {"matched": 1})
            options.replay_only = True
            with patch.object(collector, "urlopen") as network:
                collector.collect(options)
                network.assert_not_called()
            self.assertEqual(
                json.loads((options.output / "coverage.json").read_bytes())[
                    "observations"
                ],
                result["observations"],
            )

    def test_not_found_is_cached_but_wrong_identity_is_ambiguous(self):
        for status in (404, 200):
            with tempfile.TemporaryDirectory() as temp:
                options = self.options(Path(temp))
                response = (
                    HTTPError(
                        "https://api.semanticscholar.org/",
                        404,
                        "Missing",
                        {},
                        io.BytesIO(
                            b'{"error":"Paper with id DOI:10.1234/abc not found"}'
                        ),
                    )
                    if status == 404
                    else Response(
                        b'{"paperId":"synthetic","externalIds":{"DOI":"10.1234/other"}}'
                    )
                )
                with (
                    patch.object(collector, "urlopen", side_effect=[response])
                    if status == 404
                    else patch.object(collector, "urlopen", return_value=response)
                ):
                    collector.collect(options)
                result = json.loads((options.output / "coverage.json").read_bytes())
                self.assertEqual(
                    result["counts"], {"no match" if status == 404 else "ambiguous": 1}
                )
                self.assertFalse(result["field_presence"])
