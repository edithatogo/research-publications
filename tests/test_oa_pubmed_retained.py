import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from oa_pubmed_retained import identifiers, normalize_doi


class RetainedPubMedTest(unittest.TestCase):
    def rows(self):
        def node(kind, value):
            return {
                "Name": "ArticleId",
                "Value": value,
                "Attributes": [{"Name": "IdType", "Value": kind}],
            }

        tree = [
            {
                "Name": "MedlineCitation",
                "Value": [{"Name": "ReferenceList", "Value": [node("pmc", "PMC999")]}],
            },
            {
                "Name": "PubmedData",
                "Value": [
                    {
                        "Name": "ArticleIdList",
                        "Value": [
                            node("pubmed", "123"),
                            node("doi", "10.1234/own"),
                            node("pmc", "PMC123"),
                        ],
                    }
                ],
            },
        ]
        raw = json.dumps(tree).encode().hex()
        return [
            {
                "[PMID]": "123",
                "[ChunkIndex]": 0,
                "[ChunkCount]": 1,
                "[MetadataCharacters]": len(raw),
                "[Encoding]": "UTF8-HEX",
                "[MetadataChunk]": raw,
            }
        ]

    def test_own_article_not_reference(self):
        result = identifiers(self.rows(), "123")
        self.assertEqual(result["PMCID"], "PMC123")
        self.assertEqual(result["DOI"], "10.1234/own")
        self.assertEqual(result["archiving_eligibility"], "not_evaluated")

    def test_partial_or_duplicate_chunks_rejected(self):
        rows = self.rows()
        with self.assertRaises(ValueError):
            identifiers(rows + rows, "123")
        rows[0]["[ChunkCount]"] = 2
        with self.assertRaises(ValueError):
            identifiers(rows, "123")

    def test_parent_identity_mismatch_rejected(self):
        rows = self.rows()
        rows[0]["[PMID]"] = "456"
        with self.assertRaisesRegex(ValueError, "PMID mismatch"):
            identifiers(rows, "456")

    def test_retained_normalization_parity_without_new_prefix_or_percent_decoding(self):
        cases = {
            " 10.1234/OWN(1) ": "10.1234/own(1)",
            "HTTPS://DOI.ORG/10.1234/Own": "10.1234/own",
            "http://dx.doi.org/10.1234/OWN%2FPart": "10.1234/own%2fpart",
            "10.1234/Own%20Part": "10.1234/own%20part",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_doi(raw), expected)
        for raw in (
            "doi:10.1234/own",
            "10.123/own",
            "10.1234/with space",
            "",
            None,
            123,
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                normalize_doi(raw)

    def test_strict_chunk_types_and_positive_ascii_identity(self):
        for key, value in [
            ("[ChunkCount]", True),
            ("[ChunkIndex]", False),
            ("[MetadataCharacters]", True),
            ("[PMID]", 123),
        ]:
            rows = self.rows()
            rows[0][key] = value
            before = copy.deepcopy(rows)
            with self.subTest(key=key), self.assertRaises(ValueError):
                identifiers(rows, "123")
            self.assertEqual(rows, before)
        for pmid in (123, True, "0", "0123", "１２３", " 123"):
            with self.subTest(pmid=pmid), self.assertRaises(ValueError):
                identifiers(self.rows(), pmid)

    def test_complete_multichunk_hash_and_input_order_are_preserved(self):
        raw = bytes.fromhex(self.rows()[0]["[MetadataChunk]"])
        tree = json.loads(raw)
        tree.append({"Name": "FictionalEvidence", "Value": "é" * 22000})
        raw = json.dumps(tree, ensure_ascii=False).encode()
        encoded = raw.hex()
        rows = [
            {
                "[PMID]": "123",
                "[ChunkIndex]": i,
                "[ChunkCount]": (len(encoded) + 19999) // 20000,
                "[MetadataCharacters]": len(encoded),
                "[MetadataChunk]": encoded[i * 20000 : (i + 1) * 20000],
                "[Encoding]": "UTF8-HEX",
            }
            for i in range((len(encoded) + 19999) // 20000)
        ]
        rows.reverse()
        before = copy.deepcopy(rows)
        result = identifiers(rows, "123")
        self.assertEqual(
            result["source_metadata_sha256"], hashlib.sha256(raw).hexdigest()
        )
        self.assertEqual(rows, before)
        self.assertFalse(result["native_projection_applied"])

    def test_malformed_tree_ambiguous_own_identifiers_and_blank_values_fail_closed(
        self,
    ):
        def check(tree):
            encoded = json.dumps(tree).encode().hex()
            row = self.rows()[0]
            row.update(
                {"[MetadataChunk]": encoded, "[MetadataCharacters]": len(encoded)}
            )
            with self.assertRaises(ValueError):
                identifiers([row], "123")

        original = json.loads(bytes.fromhex(self.rows()[0]["[MetadataChunk]"]))
        check({"PubmedData": original[1]})
        for value in ("", "PMC0", "PMC0123", "pmc123"):
            tree = copy.deepcopy(original)
            tree[1]["Value"][0]["Value"][2]["Value"] = value
            check(tree)
        tree = copy.deepcopy(original)
        tree[1]["Value"][0]["Value"][1]["Value"] = ""
        check(tree)
        tree = copy.deepcopy(original)
        tree[1]["Value"][0]["Value"].append(
            {
                "Name": "ArticleId",
                "Value": "PMC456",
                "Attributes": [{"Name": "IdType", "Value": "pmc"}],
            }
        )
        check(tree)
        tree = copy.deepcopy(original)
        tree[1]["Value"][0]["Value"][0]["Attributes"] *= 2
        check(tree)

    def test_cli_create_only_and_failed_input_preserve_existing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "rows.json"
            output = Path(directory) / "result.json"
            source.write_text(json.dumps(self.rows()))
            raw = source.read_bytes()
            command = [
                sys.executable,
                "-m",
                "scripts.oa_pubmed_retained",
                "--rows",
                str(source),
                "--pmid",
                "123",
                "--output",
                str(output),
            ]
            result = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            saved = output.read_bytes()
            self.assertNotEqual(
                subprocess.run(command, capture_output=True, check=False).returncode, 0
            )
            self.assertEqual(output.read_bytes(), saved)
            self.assertEqual(source.read_bytes(), raw)
            command[command.index("--pmid") + 1] = "0"
            command[-1] = str(Path(directory) / "bad.json")
            self.assertNotEqual(
                subprocess.run(command, capture_output=True, check=False).returncode, 0
            )
            self.assertFalse(Path(command[-1]).exists())
            self.assertEqual(source.read_bytes(), raw)
