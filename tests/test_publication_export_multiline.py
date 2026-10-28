"""Focused regressions for readable multiline bibliography citations."""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.export_publication_register import render_exports

ROOT = Path(__file__).resolve().parents[1]


class PublicationExportMultilineTests(unittest.TestCase):
    def test_visible_citation_preserves_linebreaks_and_escapes_text(self):
        envelope = json.loads(
            (ROOT / "tests/fixtures/webfirst-export-synthetic.json").read_text()
        )
        row = envelope["records"][0]
        row["Authors"] = "First author & co\n<Second author>"
        row["Title"] = "First title line\nSecond title line"
        row["Journal"] = "Journal line one\nJournal line two"

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "export"
            render_exports(envelope, output)
            html = (output / "publications.html").read_text(encoding="utf-8")

        self.assertIn("First author &amp; co<br>&lt;Second author&gt;", html)
        self.assertIn("First title line<br>Second title line", html)
        self.assertIn("Journal line one<br>Journal line two", html)


if __name__ == "__main__":
    unittest.main()


class ExportMultilineRoundtripTests(unittest.TestCase):
    def test_csv_roundtrip_preserves_multiline_unicode_quotes_and_unknown_dates(self):
        import csv
        import io

        envelope = json.loads(
            (ROOT / "tests/fixtures/webfirst-export-synthetic.json").read_text()
        )
        row = envelope["records"][0]
        row.update(
            Authors='First, "Quoted" author\r\nSecond β author',
            Title="Line one\nLine two & <literal>",
            Journal="Journal\rline",
            PublicationDateRaw="2001-2003",
            PublicationDatePrecision="range",
            PublicationMonth=None,
            PublicationYear=None,
        )
        before = json.loads(json.dumps(envelope))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "export"
            render_exports(envelope, output)
            decoded = list(
                csv.DictReader(
                    io.StringIO(
                        (output / "publications.csv").read_bytes().decode("utf-8-sig"),
                        newline="",
                    )
                )
            )
            actual = next(
                item for item in decoded if item["CanonicalKey"] == row["CanonicalKey"]
            )
            for name in (
                "Authors",
                "Title",
                "Journal",
                "PublicationDateRaw",
                "PublicationDatePrecision",
            ):
                self.assertEqual(actual[name], row[name])
            self.assertEqual(actual["PublicationMonth"], "")
            self.assertEqual(actual["PublicationYear"], "")
            html = (output / "publications.html").read_text()
            self.assertIn("Second β author", html)
            self.assertIn("2001-2003", html)
            self.assertIn("[range]", html)
            self.assertIn("&amp; &lt;literal&gt;", html)
            with self.assertRaises(FileExistsError):
                render_exports(envelope, output)
        self.assertEqual(envelope, before)

    def test_multiline_formula_guard_changes_only_spreadsheet_interpretation(self):
        import csv
        import io

        envelope = json.loads(
            (ROOT / "tests/fixtures/webfirst-export-synthetic.json").read_text()
        )
        row = envelope["records"][0]
        row["Title"] = "=Literal title\nSecond line"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "export"
            render_exports(envelope, output)
            decoded = list(
                csv.DictReader(
                    io.StringIO(
                        (output / "publications.csv").read_bytes().decode("utf-8-sig"),
                        newline="",
                    )
                )
            )
            actual = next(
                item for item in decoded if item["CanonicalKey"] == row["CanonicalKey"]
            )
            self.assertEqual(actual["Title"], "'" + row["Title"])
            self.assertIn(
                "=Literal title<br>Second line",
                (output / "publications.html").read_text(),
            )
        self.assertEqual(row["Title"], "=Literal title\nSecond line")


if __name__ == "__main__":
    unittest.main()
