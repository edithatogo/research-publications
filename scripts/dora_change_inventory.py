"""Analyse the published sitemap as opaque version evidence, never UTC coverage."""
import re
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
PREFIX = "https://dora.health.qld.gov.au/qldresearchjspui/handle/1/"


def inventory(xml: str, required: list[str]) -> dict:
    if (len(required) != len(set(required)) or not required
            or any(not re.fullmatch(r"[1-9][0-9]*", key) for key in required)
            or "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper()):
        raise ValueError("Unique canonical handles and entity-free XML required")
    root = ET.fromstring(xml)
    if root.tag != NS + "urlset":
        raise ValueError("Expected the actual published sitemap page")
    selected = {}
    wanted = set(required)
    for node in root.findall(NS + "url"):
        url = node.findtext(NS + "loc", "")
        if not url.startswith(PREFIX):
            continue
        key = url[len(PREFIX):]
        if key not in wanted:
            continue
        if key in selected:
            raise ValueError("Duplicate selected sitemap handle")
        stamp = node.findtext(NS + "lastmod", "")
        if not stamp or stamp != stamp.strip():
            raise ValueError("Missing opaque source version")
        selected[key] = {"source_url": url, "source_stamp": stamp}
    return {"versions": selected, "missing": sorted(wanted - selected.keys()),
            "timestamps_are_opaque": True, "utc_cutoff_proven": False}


def select_work(versions: dict, cache: dict, *, version_contract_qualified=False,
                now_utc: datetime | None = None, max_age_seconds: int | None = None) -> dict:
    """Fail closed until current-source change semantics and cache lineage pass.

    The qualification flag is an external evidence gate, not inferred from a
    stable sitemap, Last-Modified header, elapsed time or this local test.
    A separately qualified freshness bound is mandatory. Age is measured from
    the actual response observation, never the sitemap token or archive recheck.
    No native collector currently invokes this selector.
    """
    bounded = (isinstance(now_utc, datetime) and now_utc.utcoffset() is not None
               and isinstance(max_age_seconds, int) and not isinstance(max_age_seconds, bool)
               and max_age_seconds > 0)
    fetch, reuse = [], []
    for key, version in sorted(versions.items()):
        entry = cache.get(key, {})
        if not isinstance(entry, dict):
            entry = {}
        fresh = False
        if bounded:
            try:
                observed = datetime.fromisoformat(entry.get("response_observed_utc", "").replace("Z", "+00:00"))
                fresh = (observed.utcoffset() is not None
                         and 0 <= (now_utc.astimezone(timezone.utc) - observed).total_seconds() <= max_age_seconds)
            except (ValueError, TypeError, AttributeError):
                pass
        valid = (entry.get("source_stamp") == version["source_stamp"]
                 and entry.get("source_url") == version["source_url"]
                 and isinstance(entry.get("bytes"), int) and not isinstance(entry.get("bytes"), bool)
                 and entry["bytes"] > 0
                 and all(isinstance(entry.get(field), str) and entry[field].strip()
                         for field in ("native_id", "etag", "archive_folder", "file", "sha256"))
                 and re.fullmatch(r"[a-f0-9]{64}", entry.get("sha256", "")))
        if version_contract_qualified is True and valid and fresh:
            reuse.append({"key": key, "evidence": dict(entry)})
        else:
            fetch.append(key)
    return {"fetch": fetch, "reuse": reuse, "native_deployed": False,
            "version_contract_qualified": version_contract_qualified}
