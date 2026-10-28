import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_publication_outcome_reader import MAIN, fingerprint, prepare as initial, projection, read, write
from prepare_publication_reporting_snapshot import FACT, VIEW, MEASURES
from prepare_publication_versioned_reader import EVIDENCE, prepare, version_bindings
from tests import test_publication_outcome_reader as reader_fixture


class VersionedReaderTests(unittest.TestCase):
    def reader(self, root):
        source = reader_fixture.PublicationReaderTests().fixture(root)
        current = root / "current.Report"
        initial(source, current, fingerprint(source))
        # The accepted reader's canonical attribution axis and positive-work
        # filter must move together to the retained fact, not current-only data.
        p = current / "definition/pages" / MAIN / "visuals/attribution-breakdown/visual.json"
        value = read(p)
        value["visual"]["query"] = {"queryState": {
            "Category": {"projections": [projection("Publication", "AttributionStatus")]},
            "Y": {"projections": [projection("Publication", "Publications", True)]}}}
        write(p, value)
        return current

    def test_versioned_fields_metrics_and_drill_context_preserve_existing_reader(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.reader(root)
            original = fingerprint(source)
            output = root / "versioned.Report"
            prepare(source, output, original)
            self.assertEqual(fingerprint(source), original)
            order = read(output / "definition/pages/pages.json")
            self.assertEqual(order["activePageName"], MAIN)
            self.assertEqual(order["landingPageName"], MAIN)
            self.assertEqual(read(source / "definition/pages/pages.json")["activePageName"], "Monthly")
            old = {p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file()}
            self.assertTrue(old <= {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()})
            main = output / "definition/pages" / MAIN
            chart = read(main / "visuals/attribution-breakdown/visual.json")
            query = chart["visual"]["query"]["queryState"]
            self.assertEqual(query["Category"]["projections"][0]["field"]["Column"]["Expression"]["SourceRef"]["Entity"], FACT)
            self.assertEqual(query["Y"]["projections"][0]["field"]["Measure"]["Property"], "V01 Included publications")
            trend = read(main / "visuals/annual-trajectory/visual.json")
            self.assertEqual(trend["visual"]["query"]["queryState"]["Category"]["projections"][0]["field"]["Column"]["Property"], "MonthStart")
            page = read(output / "definition/pages" / EVIDENCE / "page.json")
            entities = {p["fieldExpr"]["Column"]["Expression"]["SourceRef"]["Entity"] for p in page["pageBinding"]["parameters"]}
            self.assertEqual(entities, {"Facility", VIEW, FACT})
            evidence = read(output / "definition/pages" / EVIDENCE / "visuals/t18-version-works/visual.json")
            self.assertEqual(evidence["filterConfig"]["filters"][0]["filter"]["From"][0]["Entity"], FACT)
            for item in evidence["visual"]["query"]["queryState"]["Values"]["projections"]:
                self.assertTrue(item["active"])
                if "Measure" in item["field"]:
                    m = item["field"]["Measure"]
                    self.assertEqual(m["Expression"]["SourceRef"]["Entity"], FACT)
                    self.assertIn(m["Property"], MEASURES)
            for relative in old:
                if not relative.startswith("definition/pages/" + MAIN + "/") and relative != "definition/pages/pages.json":
                    self.assertEqual((source / relative).read_bytes(), (output / relative).read_bytes())

    def test_unretained_field_or_metric_and_drift_are_refused(self):
        for field in [projection("Publication", "Unretained"), projection("Publication", "Unqualified metric", True)]:
            with self.assertRaises(ValueError):
                version_bindings(field)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.reader(root)
            with self.assertRaises(ValueError):
                prepare(source, root / "out.Report", "wrong preimage")

    def test_positive_filter_metric_and_alias_change_together(self):
        from prepare_publication_outcome_reader import positive_publication_filter
        value = version_bindings(positive_publication_filter("work"))
        self.assertEqual(value["filter"]["From"][0]["Entity"], FACT)
        expr = value["filter"]["Where"][0]["Condition"]["Comparison"]
        self.assertEqual(expr["ComparisonKind"], 1)
        self.assertEqual(expr["Left"]["Measure"]["Property"], "V01 Included publications")


if __name__ == "__main__":
    unittest.main()
