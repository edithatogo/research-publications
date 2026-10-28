import base64
import hashlib
import json
from pathlib import Path
import sys
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_publication_reporting_snapshot import (
    BASELINE, FACT, VIEW, FIELDS, META_FIELDS, METRIC_VERSION,
    baseline_tmdl, make_baseline, prepare, _columns,
)


class PublicationReportingSnapshotTests(unittest.TestCase):
    def test_each_date_column_has_one_format_declaration(self):
        for name in ('CapturedUTC','PublicationDate','CutoffExclusive'):
            text=_columns({name:'dateTime'})
            self.assertEqual(text.count('formatString:'),1)

    def test_duplicate_native_parts_cannot_silently_replace_preimage(self):
        definition=json.loads(self.preimage())
        definition['definition']['parts'].append(definition['definition']['parts'][0])
        raw=json.dumps(definition).encode()
        with self.assertRaisesRegex(ValueError,'Duplicate native definition parts'):
            prepare(raw,hashlib.sha256(raw).hexdigest(),make_baseline(*self.inputs()))

    def inputs(self):
        common = dict(Title="A publication", SourceSet="PubMed", AttributionStatus="Source evidence pending review", PublicationDateRaw="2025 Jan",
                      PublicationDatePrecision="month", PublicationDate="2025-01-01T00:00:00",
                      PublicationMonth="2025-01", PublicationYear=2025, PubMedURL="https://pubmed.ncbi.nlm.nih.gov/1/", DORAURL=None)
        rows = [dict(common, CanonicalKey="PMID:1"), dict(common, CanonicalKey="PMID:2", PublicationDatePrecision="year", PublicationMonth=None)]
        oa = [dict(CanonicalKey="PMID:1", Status="gold", ObservedUTC="2026-10-01T01:02:03Z", RawResponseSHA256="a" * 64)]
        facilities = [dict(CanonicalKey="PMID:1", FacilityKey="cairns"), dict(CanonicalKey="PMID:1", FacilityKey="hhs"), dict(CanonicalKey="PMID:2", FacilityKey="atherton")]
        metadata = dict(SnapshotID="technical-fixture-1", ViewLabel="Technical baseline (not issued)", CutoffExclusive="2026-10-01",
                        CapturedUTC="2026-10-21T17:54:59Z", MetricVersion=METRIC_VERSION, ModelRevision="fixture-model-1", ReportRevision="fixture-report-1", SourceVersions="PubMed:fixture-committed-batch", Issued=False)
        return rows, oa, facilities, metadata

    def preimage(self):
        def part(path, text):
            return dict(path=path, payloadType="InlineBase64", payload=base64.b64encode(text.encode()).decode())
        parts = [
            part("definition/model.tmdl", "model Model\n\nculture: en-AU\n\nref table Publication\n"),
            part("definition/tables/Publication.tmdl", "table Publication\n\tmeasure 'K02 Known open publications' = 1\n\tmeasure 'K02 Known closed publications' = 0\n\tmeasure 'K02 Unknown OA publications' = 1\n\tannotation RIMSMetricVersion = " + METRIC_VERSION),
            part("definition/relationships.tmdl", "relationship preserved-fixture\n"),
            part("definition/tables/PublicationComparison.tmdl", "table PublicationComparison\n\tpartition PublicationComparison = calculated\n\t\tsource = {(\"Facility\",NAMEOF(Facility[FacilityName]),0),(\"Source\",NAMEOF(Publication[SourceSet]),1)}\n"),
            part("definition/tables/RetainedPubMedPublications.tmdl", "table RetainedPubMedPublications\n\tcolumn RefreshedAtUTC\n\t\tdataType: dateTime\n\t\tlineageTag: preserved-observation\n\t\tsourceColumn: RefreshedAtUTC\n"),
        ]
        for table, columns in {"PublicationFacility": ["CanonicalKey", "FacilityKey"],
                               "Facility": ["FacilityKey"], "Date": ["Date"],
                               "ReportingWindow": ["ReportMonthEndExclusive"],
                               "RetainedHistoryKeys": ["Source", "LastBatchID"],
                               "OpenAlexPublicationContext": ["CanonicalKey", "RawResponseSHA256"]}.items():
            parts.append(part(f"definition/tables/{table}.tmdl", "table " + table + "\n" + "\n".join("\tcolumn " + c for c in columns) + "\n"))
        return json.dumps({"definition": {"parts": parts}}).encode()

    def test_freezes_uncertainty_facets_hashes_and_exact_versions_without_issuing(self):
        args = self.inputs()
        frozen = make_baseline(*args)
        self.assertEqual(len(frozen), 2)
        self.assertEqual(set(frozen[0]), set(FIELDS | META_FIELDS))
        self.assertEqual((frozen[0]["OAOpen"], frozen[0]["OAClosed"], frozen[0]["OAUnknown"]), (1, 0, 0))
        self.assertEqual((frozen[1]["OAOpen"], frozen[1]["OAClosed"], frozen[1]["OAUnknown"]), (0, 0, 1))
        self.assertEqual(frozen[0]["FacilityKeys"], "|cairns|hhs|")
        self.assertEqual(frozen[0]["OAHashes"], "a" * 64)
        self.assertIsNone(frozen[1]["PublicationMonth"])
        self.assertEqual(frozen[1]["PublicationDatePrecision"], "year")
        self.assertEqual(frozen[0]["ModelRevision"], "fixture-model-1")
        self.assertEqual(frozen[0]["CapturedUTC"], args[3]["CapturedUTC"])
        # The native embedded artifact must reconstruct every frozen value.
        text = baseline_tmdl(frozen)
        self.assertIn("\tcolumn CapturedUTC\n\t\tdataType: dateTime\n\t\tsummarizeBy: none\n\t\tformatString: yyyy-MM-dd HH:mm:ss", text)
        import re
        encoded = re.search(r'Binary.FromText\("([A-Za-z0-9+/=]+)"', text)[1]
        self.assertEqual(json.loads(zlib.decompress(base64.b64decode(encoded), -15)), frozen)
        args[0][0]["Title"] = "A later edit"
        self.assertEqual(frozen[0]["Title"], "A publication")

    def test_refuses_duplicate_unknown_bridge_issuance_undated_capture_and_missing_hash(self):
        rows, oa, facilities, meta = self.inputs()
        for values in [
            (rows + rows[:1], oa, facilities, meta),
            (rows, oa, facilities + [dict(CanonicalKey="PMID:999", FacilityKey="cairns")], meta),
            (rows, oa, facilities + [dict(CanonicalKey="PMID:1", FacilityKey="cairns|other")], meta),
            (rows, oa, facilities, dict(meta, Issued=True)),
            (rows, oa, facilities, dict(meta, CapturedUTC="2026-10-21T17:54:59")),
            (rows, [dict(oa[0], RawResponseSHA256=None)], facilities, meta),
        ]:
            with self.assertRaises(ValueError):
                make_baseline(*values)

    def test_additive_preparation_retains_all_existing_members_and_rejects_drift_security_or_reuse(self):
        raw = self.preimage()
        sha = hashlib.sha256(raw).hexdigest()
        baseline = make_baseline(*self.inputs())
        result = prepare(raw, sha, baseline)
        original = json.loads(raw)["definition"]["parts"]
        for old, new in zip(original[1:], result["parts"][1:len(original)]):
            if old["path"] not in {"definition/tables/Date.tmdl", "definition/tables/PublicationComparison.tmdl", "definition/tables/RetainedPubMedPublications.tmdl"}:
                self.assertEqual(new, old)
        retained = base64.b64decode(next(p for p in result["parts"] if p["path"] == "definition/tables/RetainedPubMedPublications.tmdl")["payload"]).decode()
        self.assertIn("formatString: yyyy-MM-dd HH:mm:ss", retained)
        self.assertIn("lineageTag: preserved-observation", retained)
        date_part = next(p for p in result["parts"] if p["path"] == "definition/tables/Date.tmdl")
        date_text = base64.b64decode(date_part["payload"]).decode()
        self.assertIn("\tcolumn Date\n", date_text)
        self.assertIn("column MonthStart = DATE(YEAR('Date'[Date]), MONTH('Date'[Date]), 1)", date_text)
        comparison = next(p for p in result["parts"] if p["path"] == "definition/tables/PublicationComparison.tmdl")
        self.assertIn("NAMEOF(Facility[FacilityName])", base64.b64decode(comparison["payload"]).decode())
        self.assertIn("NAMEOF(PublicationOutcomeVersionFact[SourceSet])", base64.b64decode(comparison["payload"]).decode())
        self.assertEqual(len(result["parts"]), len(original) + 3)
        paths = {p["path"] for p in result["parts"]}
        self.assertTrue({f"definition/tables/{x}.tmdl" for x in [BASELINE, FACT, VIEW]} <= paths)
        fact = base64.b64decode(next(p for p in result["parts"] if p["path"] == f"definition/tables/{FACT}.tmdl")["payload"]).decode()
        for url in ("PubMedURL", "DORAURL"):
            definition = fact.split("\tcolumn " + url + "\n", 1)[1].split("\tcolumn ", 1)[0]
            self.assertIn("dataCategory: WebUrl", definition)
        model = base64.b64decode(result["parts"][0]["payload"]).decode()
        self.assertIn("ref table Publication\n", model)
        self.assertIn("ref table " + FACT, model)
        with self.assertRaises(ValueError):
            prepare(raw, "0" * 64, baseline)
        reused = json.dumps({"definition": result}).encode()
        with self.assertRaises(ValueError):
            prepare(reused, hashlib.sha256(reused).hexdigest(), baseline)
        guarded = json.loads(raw)
        guarded["definition"]["parts"].append(dict(path="definition/roles/Restricted.tmdl", payloadType="InlineBase64", payload=""))
        secure = json.dumps(guarded).encode()
        with self.assertRaisesRegex(ValueError, "RLS/OLS"):
            prepare(secure, hashlib.sha256(secure).hexdigest(), baseline)


if __name__ == "__main__":
    unittest.main()
