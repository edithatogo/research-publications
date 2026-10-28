"""Offline field projection from retained EFetch XML; no native/API operations.

This reviewed pure slice excludes the retained module's token, fetch, refresh,
report-binding and live capture paths. Full XML comparison is separate.
"""

import re
import xml.etree.ElementTree as ET

from scripts.verify_retained_canary_metadata_values import _date_parts


def _xml_text(node: ET.Element | None) -> str:
    return "" if node is None else "".join(node.itertext())


def _ncbi_date(node: ET.Element | None) -> str:
    if node is None:
        return ""
    medline = node.findtext("MedlineDate")
    if medline:
        return medline.strip()
    return " ".join(
        value.strip()
        for name in ("Year", "Month", "Day")
        if (value := node.findtext(name))
    )


def _electronic_date(node: ET.Element | None) -> str:
    if node is None:
        return ""
    year, month, day = tuple(
        (node.findtext(name) or "").strip() for name in ("Year", "Month", "Day")
    )
    month_names = (
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    )
    if month.isdigit() and 1 <= int(month) <= 12:
        month = month_names[int(month) - 1]
    if day.isdigit():
        day = str(int(day))
    return " ".join(value for value in (year, month, day) if value)


def project_current_pubmed_efetch(xml_bytes: bytes) -> dict[str, dict]:
    """Project official current EFetch fields used by the model's PubMed table."""
    root = ET.fromstring(xml_bytes)
    if (
        root.tag != "PubmedArticleSet"
        or any(child.tag != "PubmedArticle" for child in root)
        or root.find(".//ERROR") is not None
    ):
        raise ValueError("official EFetch response has an unsupported article shape")
    result = {}
    for article in root.findall("./PubmedArticle"):
        citation = article.find("./MedlineCitation")
        record = article.find("./MedlineCitation/Article")
        journal = None if record is None else record.find("./Journal")
        if citation is None or record is None:
            raise ValueError(
                "official EFetch response omitted required article structure"
            )
        pmid = citation.findtext("./PMID")
        if (
            not isinstance(pmid, str)
            or re.fullmatch(r"[1-9][0-9]*", pmid) is None
            or pmid in result
        ):
            raise ValueError("official EFetch returned a blank or duplicate PMID")
        author_names = []
        for author in record.findall("./AuthorList/Author"):
            collective = _xml_text(author.find("./CollectiveName"))
            if collective:
                name = collective
            else:
                first = (
                    author.findtext("./ForeName") or author.findtext("./Initials") or ""
                )
                last = author.findtext("./LastName") or ""
                suffix = author.findtext("./Suffix") or ""
                name = " ".join(
                    part
                    for part in (first.strip(), last.strip(), suffix.strip())
                    if part
                )
            if name:
                author_names.append(name)
        issue_raw = _ncbi_date(
            None if journal is None else journal.find("./JournalIssue/PubDate")
        )
        precision, year = _date_parts(issue_raw)
        if year is not None and year < 1900 and precision in ("day", "month"):
            precision = "outside-model-range"
        online_dates = [
            d
            for d in record.findall("./ArticleDate")
            if d.attrib.get("DateType", "").casefold() == "electronic"
        ]
        online_raw = _electronic_date(online_dates[0]) if online_dates else ""
        result[pmid] = {
            "Title": _xml_text(record.find("./ArticleTitle")),
            "Journal": _xml_text(None if journal is None else journal.find("./Title")),
            "Authors": "; ".join(author_names),
            "Abstract": "\n".join(
                _xml_text(node) for node in record.findall("./Abstract/AbstractText")
            ),
            "PublicationDateRaw": issue_raw,
            "PublicationDatePrecision": precision,
            "PublicationYear": year,
            "OnlineDateRaw": online_raw,
        }
    if not result:
        raise ValueError("official EFetch response contained no PubMed articles")
    return result
