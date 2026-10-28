import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_publication_outcome_reader import DETAIL, KEEP, MAIN, fingerprint, prepare, read, write, inherit_neutral_text_colors, repair_retained_pubmed_observation, repair_declared_evidence_links


class PublicationReaderTests(unittest.TestCase):
    def test_theme_adoption_preserves_data_colours_conditional_formatting_and_query(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            path = folder / "definition/pages/Other/visuals/evidence/visual.json"
            neutral = {"solid": {"color": {"expr": {"Literal": {"Value": "'#172B4D'"}}}}}
            conditional = {"solid": {"color": {"expr": {"Measure": {
                "Expression": {"SourceRef": {"Entity": "Publication"}}, "Property": "Status colour"}}}}}
            original = {"name": "evidence", "visual": {"visualType": "tableEx",
                "query": {"retained": "exact"}, "objects": {
                    "values": [{"properties": {"fontColor": conditional}}],
                    "categoryAxis": [{"properties": {"labelColor": neutral, "titleColor": conditional}}],
                    "dataPoint": [{"properties": {"fillColor": neutral}}]},
                "visualContainerObjects": {"title": [{"properties": {"fontColor": neutral}}]}}}
            write(path, original)
            self.assertEqual(len(inherit_neutral_text_colors(folder)), 1)
            after = read(path)
            self.assertEqual(after["visual"]["query"], original["visual"]["query"])
            for role in ("values", "dataPoint"):
                self.assertEqual(after["visual"]["objects"][role], original["visual"]["objects"][role])
            axis = after["visual"]["objects"]["categoryAxis"][0]["properties"]
            self.assertNotIn("labelColor", axis)
            self.assertEqual(axis["titleColor"], conditional)
            self.assertNotIn("fontColor", after["visual"]["visualContainerObjects"]["title"][0]["properties"])

    def test_freshness_rebind_refuses_drift_without_partial_edit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "definition/pages/SourceFreshness/visuals/observed-0/visual.json"
            note = root / "definition/pages/SourceFreshness/visuals/source-0/visual.json"
            objects = {key: [{"properties": {}}] for key in ("general", "title", "visualHeaderTooltip")}
            value = {"visual": {"visualContainerObjects": objects, "query": {"queryState": {
                "Data": {"projections": [{"field": {"Aggregation": {"Function": 4,
                    "Expression": {"Column": {"Property": "RefreshedAtUTC", "Expression": {
                        "SourceRef": {"Entity": "FreshSearchAudit"}}}}}}}]}}}}}
            write(path, value)
            write(note, {"explanation": "unexpected replacement event"})
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "explanation drift"):
                repair_retained_pubmed_observation(root)
            self.assertEqual(path.read_bytes(), before)
            old = "Search execution observation; not publication or provider update."
            write(note, {"alt": old, "tooltip": old, "paragraph": old})
            repair_retained_pubmed_observation(root)
            projection = read(path)["visual"]["query"]["queryState"]["Data"]["projections"][0]
            self.assertEqual(projection["queryRef"], "Max(RetainedPubMedPublications.RefreshedAtUTC)")
            self.assertIn("retained observation UTC", projection["displayName"])
            self.assertIn("not provider update or complete coverage", read(note)["paragraph"])

    def test_link_contrast_targets_declared_urls_and_preserves_conditional_rules(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "definition/pages/Other/visuals/links/visual.json"
            def projection(table, column):
                return {"queryRef": table + "." + column, "field": {"Aggregation": {"Function": 4,
                    "Expression": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": column}}}}}
            fields = [projection("Study register", "SourceURL"), projection("Other", "SourceURL")]
            value = {"visual": {"visualType": "tableEx", "query": {"queryState": {
                "Values": {"projections": fields}}}}}
            write(path, value)
            repair_declared_evidence_links(root)
            after = read(path)
            self.assertEqual(after["visual"]["query"], value["visual"]["query"])
            formats = after["visual"]["objects"]["columnFormatting"]
            self.assertEqual([x["selector"]["metadata"] for x in formats], ["Study register.SourceURL"])
            self.assertEqual(repair_declared_evidence_links(root), [])
            formats[0]["properties"]["backColor"] = {"conditional": "preserve"}
            write(path, after)
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "Preserve existing"):
                repair_declared_evidence_links(root)
            self.assertEqual(path.read_bytes(), before)

    def fixture(self, root):
        source = root / "source.Report"
        page_root = source / "definition/pages"
        page = {"name": MAIN, "displayName": "CHHHS Publications", "width": 1920, "height": 1488}
        write(page_root / MAIN / "page.json", page)
        names = KEEP | {"heading", "caption", "review-filter", "pubmed", "dora", "overlap", "footer",
                        "overview-activities", "overview-arc", "overview-confirmed", "overview-candidates",
                        "provenance-breakdown", "overview-coverage", "overview-scope"}
        for name in names:
            v = {"$schema": "retained-schema", "name": name, "position": {"x": 0, "y": 0},
                 "visual": {"visualType": "cardVisual" if name == "overview-unknown-month" else "lineChart",
                            "query": {"retainedOriginalBinding": name,
                                      "queryState": {"Category": {"projections": []}, "Y": {"projections": []}}}}}
            if name == "overview-coverage":
                v["caption"] = "Studies and NHMRC/MRFF award registers are not connected to this model."
            if name == "provenance-breakdown":
                v["visual"]["visualType"] = "donutChart"
            if name == "footer":
                v["visual"]["visualContainerObjects"] = {"title": [{"properties": {
                    "text": {"expr": {"Literal": {"Value": "'Last model refresh (UTC)'"}}}}}]}
            write(page_root / MAIN / "visuals" / name / "visual.json", v)
        # Repeated visual names on different pages must remain scoped identities.
        for other in ["Monthly", "OtherVertical"]:
            write(page_root / other / "page.json", {"name": other})
            write(page_root / other / "visuals/heading/visual.json", {
                "name": "heading", "visual": {"query": {"unrelated": other}}})
        write(page_root / "pages.json", {"pageOrder": [MAIN, "Monthly", "OtherVertical"],
                                         "activePageName": "Monthly"})
        write(source / "definition.pbir", {"datasetReference": {"preservedBinding": True}})
        write(source / "definition/report.json", {"themeCollection": {"customTheme": {"name": "old-theme.json"}},
            "resourcePackages": [{"name": "RegisteredResources", "items": [
                {"name": "old-theme.json", "path": "old-theme.json", "type": "CustomTheme"}]}]})
        write(source / "StaticResources/RegisteredResources/old-theme.json", {"name": "old theme"})
        return source

    def test_preserves_scoped_identities_other_verticals_binding_and_start_page(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.fixture(root)
            before = fingerprint(source)
            output = root / "candidate.Report"
            result = prepare(source, output, before)
            self.assertEqual(fingerprint(source), before)
            self.assertEqual(result["originalVisualIDsPreserved"], 24)
            for name in ["definition.pbir", "definition/pages/Monthly/page.json",
                         "definition/pages/OtherVertical/visuals/heading/visual.json",
                         "StaticResources/RegisteredResources/old-theme.json"]:
                self.assertEqual((source / name).read_bytes(), (output / name).read_bytes())
            order = read(output / "definition/pages/pages.json")
            self.assertEqual(order["activePageName"], "Monthly")
            self.assertEqual(order["pageOrder"], [MAIN, DETAIL, "Monthly", "OtherVertical"])
            for name in KEEP:
                self.assertTrue((output / "definition/pages" / MAIN / "visuals" / name / "visual.json").exists())
            self.assertTrue((output / "definition/pages" / DETAIL / "visuals/heading/visual.json").exists())

    def test_primary_is_plot_first_bounded_grid_without_inline_font_or_colour_literals(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.fixture(root)
            output = root / "candidate.Report"
            prepare(source, output, fingerprint(source))
            visuals = [read(p) for p in (output / "definition/pages" / MAIN).glob("visuals/*/visual.json")]
            rectangles = []
            for v in visuals:
                self.assertNotIn(v["visual"]["visualType"], {"textbox", "tableEx", "pivotTable"})
                payload = json.dumps(v)
                self.assertNotIn('"fontSize"', payload)
                self.assertNotIn('"fontColor"', payload)
                self.assertNotRegex(payload, r"#[A-Fa-f0-9]{6}")
                p = v["position"]
                for key in ["x", "y", "width", "height"]:
                    self.assertEqual(p[key] % 8, 0)
                self.assertGreaterEqual(p["x"], 0)
                self.assertGreaterEqual(p["y"], 0)
                self.assertLessEqual(p["x"] + p["width"], 1920)
                self.assertLessEqual(p["y"] + p["height"], 1080)
                rectangles.append((v["name"], p))
            for i, (name, a) in enumerate(rectangles):
                for other, b in rectangles[i + 1:]:
                    overlap = (max(a["x"], b["x"]) < min(a["x"] + a["width"], b["x"] + b["width"])
                               and max(a["y"], b["y"]) < min(a["y"] + a["height"], b["y"] + b["height"]))
                    self.assertFalse(overlap, (name, other))

    def test_drift_overwrite_and_repeated_adoption_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.fixture(root)
            with self.assertRaisesRegex(ValueError, "preimage mismatch"):
                prepare(source, root / "none.Report", "0" * 64)
            output = root / "candidate.Report"
            prepare(source, output, fingerprint(source))
            with self.assertRaises(FileExistsError):
                prepare(source, output, fingerprint(source))
            with self.assertRaisesRegex(ValueError, "already exists"):
                prepare(output, root / "second.Report", fingerprint(output))

    def test_detail_rows_use_facility_aware_measure_and_keep_source_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.fixture(root)
            output = root / "candidate.Report"
            prepare(source, output, fingerprint(source))
            page = read(output / "definition/pages" / DETAIL / "page.json")
            self.assertEqual(page["pageBinding"]["acceptsFilterContext"], "Default")
            table = read(output / "definition/pages" / DETAIL / "visuals/t18-work-evidence/visual.json")
            self.assertEqual(table["filterConfig"]["filters"][0]["field"]["Measure"]["Property"], "Publications")
            comparison = table["filterConfig"]["filters"][0]["filter"]["Where"][0]["Condition"]["Comparison"]
            # Microsoft QueryComparisonKind: 1 is >; 2 admits unrelated zero rows.
            self.assertEqual(comparison["ComparisonKind"], 1)
            self.assertEqual(comparison["Right"]["Literal"]["Value"], "0L")
            self.assertTrue(all(item["active"] for item in table["visual"]["query"]["queryState"]["Values"]["projections"]))
            refs = {v["queryRef"] for v in table["visual"]["query"]["queryState"]["Values"]["projections"]}
            self.assertTrue({"Publication.PubMedURL", "Publication.DORAURL", "Publication.PublicationDatePrecision"} <= refs)
            bar = read(output / "definition/pages" / MAIN / "visuals/facility-breakdown/visual.json")
            category = bar["visual"]["query"]["queryState"]["Category"]
            self.assertEqual(len(category["projections"]), category["fieldParameters"][0]["length"])
            selector = read(output / "definition/pages" / MAIN / "visuals/t18-comparison/visual.json")
            self.assertNotIn("drillFilterOtherVisuals", selector["visual"])
            self.assertEqual(selector["visual"]["query"]["queryState"]["Values"]["projections"][0]["field"],
                             category["fieldParameters"][0]["parameterExpr"])


if __name__ == "__main__":
    unittest.main()
