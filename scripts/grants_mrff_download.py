"""Retain the official MRFF grant-recipient workbook set without transforming it.

The command discovers the three current Excel resources from the Department's
public dataset page, validates the official host and XLSX payloads, and stores
the originals with private source and copyright evidence. It does not admit
award rows or funded-rate summaries to opportunity intake.

Use --from-browser to seal already downloaded internal-browser originals without
making a machine request, transferring cookies or changing native flow state.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import urllib.error
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

try:
    from scripts.grants_nhmrc_download import _Links, _fetch, _workbook_inventory
except ImportError:
    from grants_nhmrc_download import _Links, _fetch, _workbook_inventory

REPO_ROOT = Path(__file__).resolve().parents[1]
PRIVATE_OPS = REPO_ROOT / "private" / "ops"
SOURCE_PAGE = (
    "https://www.health.gov.au/resources/publications/"
    "medical-research-future-fund-mrff-grant-recipients?language=en"
)
COPYRIGHT_PAGE = "https://www.health.gov.au/using-our-websites/copyright"
OFFICIAL_HOST = "www.health.gov.au"
MAX_PAGE_BYTES = 5_000_000
MAX_WORKBOOK_BYTES = 20_000_000
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _filename(url: str) -> str:
    name = Path(unquote(urlsplit(url).path)).name
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name) or "mrff-resource.xlsx"


def _resource_kind(label: str, url: str) -> str:
    # The publisher exposes the same visible link label for every Excel
    # attachment; distinguish the resource type using the official filename.
    folded = (label + " " + urlsplit(url).path).casefold()
    if "funded rates" in folded or "funded_rates" in folded or "funded-rates" in folded:
        return "opportunity_funded_rates_summary"
    if "summary" in folded:
        return "awarded_grants_summary"
    if "recipient" in folded or "grant recipients" in folded:
        return "awarded_grant_recipients"
    raise ValueError("unrecognized MRFF Excel attachment; refusing source misclassification")


def acquire(destination: Path) -> dict[str, object]:
    destination = destination.resolve()
    try:
        destination.relative_to(PRIVATE_OPS.resolve())
    except ValueError as exc:
        raise ValueError("output must be inside this repository's ignored private/ops directory") from exc
    if destination.exists():
        raise FileExistsError("output directory already exists; use a new evidence path")

    page, page_headers, page_final = _fetch(SOURCE_PAGE, MAX_PAGE_BYTES, OFFICIAL_HOST)
    parser = _Links()
    parser.feed(page.decode("utf-8", "replace"))
    resources: list[dict[str, str]] = []
    for link in parser.links:
        label = " ".join(link["text"].split())
        url = urljoin(page_final, link["href"])
        parsed = urlsplit(url)
        if ".xlsx" not in parsed.path.casefold():
            continue
        if "medical research future fund" not in label.casefold() or "excel" not in label.casefold():
            continue
        if parsed.scheme != "https" or parsed.hostname != OFFICIAL_HOST:
            raise ValueError("selected workbook link is outside the official Department host")
        resources.append({"label": label, "url": url, "kind": _resource_kind(label, url)})
    kinds = [row["kind"] for row in resources]
    expected = {"awarded_grant_recipients", "awarded_grants_summary", "opportunity_funded_rates_summary"}
    if len(resources) != 3 or set(kinds) != expected or len(set(kinds)) != 3:
        raise ValueError("expected exactly one recipients, award-summary and funded-rates workbook")

    text = _Text()
    text.feed(page.decode("utf-8", "replace"))
    page_text = " ".join(" ".join(text.parts).split())
    as_of = re.search(r"correct as at\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})", page_text, re.I)
    published = re.search(r"Publication date:\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})", page_text, re.I)
    if not as_of or not published:
        raise ValueError("official dataset page did not expose its data-as-of and publication dates")

    captured: list[dict[str, object]] = []
    payloads: list[tuple[str, bytes]] = []
    for resource in resources:
        body, headers, final_url = _fetch(resource["url"], MAX_WORKBOOK_BYTES, OFFICIAL_HOST)
        content_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != XLSX_MIME:
            raise ValueError(f"{resource['kind']} response did not have the XLSX media type")
        inventory = _workbook_inventory(body)
        basename = _filename(resource["url"])
        payloads.append((basename, body))
        captured.append({
            "resource_kind": resource["kind"],
            "record_kind": resource["kind"],
            "label": resource["label"],
            "url": resource["url"],
            "final_url": final_url,
            "content_type": content_type,
            "last_modified": headers.get("last-modified"),
            "etag": headers.get("etag"),
            "path": basename,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "zip_integrity": "passed",
            "sheet_inventory": inventory,
        })

    copyright_body, copyright_headers, copyright_final = _fetch(
        COPYRIGHT_PAGE, MAX_PAGE_BYTES, OFFICIAL_HOST
    )
    if "text/html" not in copyright_headers.get("content-type", "").lower():
        raise ValueError("Department copyright guidance response was not HTML")
    observed_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    destination.mkdir(parents=True)
    (destination / "source-page.html").write_bytes(page)
    (destination / "copyright-page.html").write_bytes(copyright_body)
    for name, body in payloads:
        (destination / name).write_bytes(body)

    receipt: dict[str, object] = {
        "status": "acquired_unmodified_official_sources",
        "observed_at": observed_at,
        "source_page": SOURCE_PAGE,
        "source_page_final_url": page_final,
        "source_page_last_modified": page_headers.get("last-modified"),
        "source_page_sha256": hashlib.sha256(page).hexdigest(),
        "data_correct_as_at": as_of.group(1),
        "publication_date": published.group(1),
        "audience": "General public",
        "resources": captured,
        "copyright": {
            "policy_page": COPYRIGHT_PAGE,
            "policy_final_url": copyright_final,
            "policy_page_sha256": hashlib.sha256(copyright_body).hexdigest(),
            "policy_capture": "copyright-page.html",
            "basis": "Department guidance permits unaltered download and reproduction for internal organisational use unless otherwise indicated, with copyright and disclaimer notices retained.",
            "item_specific_exception_check": "The dataset page exposes no separate licence notice in its metadata; the original resources and page are retained unaltered for internal use.",
            "adaptation_or_external_redistribution": "not performed or authorised",
        },
        "opportunity_admission": False,
        "identity_limit": "Recipients file includes Grant ID; this acquisition does not qualify stable round identity, lifecycle semantics or a canonical RIMS OpportunityKey mapping.",
        "recovery": "Repeat to a new private/ops directory; this command refuses an existing output directory.",
    }
    (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def retain_browser_capture(observation_path: Path, destination: Path) -> dict[str, object]:
    """Validate and retain an observed browser download; never fetch or admit data.

    The observation is supporting operator evidence, not a cryptographic proof
    of browser origin or authority for unattended/native admission.
    """
    from scripts.capture_official_workbooks import discover, verify_workbook

    destination = destination.resolve()
    if not destination.is_relative_to(PRIVATE_OPS.resolve()) or destination.exists():
        raise ValueError('A new private/ops destination is required')
    observation_path = observation_path.resolve()
    observation = json.loads(observation_path.read_text(encoding='utf-8'))
    if (observation.get('sourcePage') != SOURCE_PAGE
            or observation.get('rightsPage') != COPYRIGHT_PAGE
            or observation.get('sourceStatus') != 200
            or observation.get('rightsStatus') != 200
            or observation.get('internalUnalteredUseObserved') is not True
            or not str(observation.get('route', '')).startswith('Codex internal browser')):
        raise ValueError('Exact successful internal-browser source/copyright evidence required')
    observed = dt.datetime.fromisoformat(observation['observedAt'].replace('Z', '+00:00'))
    if observed.utcoffset() is None:
        raise ValueError('Timezone-aware browser observation required')
    page = (observation_path.parent / 'source-page.html').read_bytes()
    copyright_body = (observation_path.parent / 'copyright-page.html').read_bytes()
    if max(len(page), len(copyright_body)) > MAX_PAGE_BYTES:
        raise ValueError('Browser page exceeds source byte cap')
    urls = discover(page, SOURCE_PAGE)
    downloads = observation.get('downloads', [])
    if (len(urls) != 3 or len(downloads) != 3
            or sorted(item['url'] for item in downloads) != urls
            or sorted(item['href'] for item in observation['linksBefore']) != urls
            or sorted(observation['linksAfter']) != urls):
        raise ValueError('Complete stable browser workbook inventory required')
    text = _Text(); text.feed(page.decode('utf-8'))
    page_text = ' '.join(' '.join(text.parts).split())
    as_of = re.search(r'correct as at\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})', page_text, re.I)
    published = re.search(r'Publication date:\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})', page_text, re.I)
    rights = _Text(); rights.feed(copyright_body.decode('utf-8'))
    rights_text = ' '.join(' '.join(rights.parts).split()).casefold()
    if (not as_of or not published or 'unaltered form' not in rights_text
            or 'internal use within your organisation' not in rights_text):
        raise ValueError('Publisher dates and unaltered internal-use evidence required')
    resources, payloads = [], []
    for item in sorted(downloads, key=lambda row: row['url']):
        path = Path(item['path'])
        if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_WORKBOOK_BYTES:
            raise ValueError('Complete bounded browser download required')
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('Download changed during verification')
        proof = verify_workbook(raw)
        name = _filename(item['url'])
        payloads.append((name, raw))
        resources.append({'resource_kind': _resource_kind('', item['url']),
                          'url': item['url'], 'path': name, **proof,
                          'response_headers_observed': False})
    if {row['resource_kind'] for row in resources} != {
            'awarded_grant_recipients', 'awarded_grants_summary', 'opportunity_funded_rates_summary'}:
        raise ValueError('Exactly three distinct official resource roles required')
    receipt = {'status': 'verified_internal_browser_capture', 'complete': True,
               'observed_at': observation['observedAt'], 'source_page': SOURCE_PAGE,
               'source_page_sha256': hashlib.sha256(page).hexdigest(),
               'source_page_representation': observation.get('sourceRepresentation'),
               'copyright_page_sha256': hashlib.sha256(copyright_body).hexdigest(),
               'data_correct_as_at': as_of.group(1), 'publication_date': published.group(1),
               'resources': resources, 'manual_browser_only': True,
               'machine_source_requests': 0, 'flow_invocations': 0,
               'native_admission': False, 'opportunity_admission': False,
               'external_redistribution': False,
               'copyright_basis': 'Publisher notice retained; unaltered internal use only',
               'origin_limit': 'Retained browser/session evidence required; JSON alone is not origin proof',
               'cloud_http_access_verified': False, 'last_good_selector_changed': False}
    destination.mkdir(parents=True, mode=0o700)
    for name, raw in [('source-page.html', page), ('copyright-page.html', copyright_body),
                      ('browser-observation.json', observation_path.read_bytes()), *payloads]:
        with (destination / name).open('xb') as stream:
            stream.write(raw)
        (destination / name).chmod(0o600)
        if (destination / name).read_bytes() != raw:
            raise ValueError('Retained browser bytes differ')
    with (destination / 'receipt.json').open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    (destination / 'receipt.json').chmod(0o600)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    transport = parser.add_mutually_exclusive_group(required=True)
    transport.add_argument("--fetch", action="store_true", help="legacy explicit HTTP route; not browser access proof")
    transport.add_argument("--from-browser", type=Path, help="seal existing internal-browser observation/downloads without fetching")
    parser.add_argument("--out", type=Path, help="new directory under ignored private/ops/ for raw files and receipt")
    args = parser.parse_args()
    if args.out is None:
        parser.error("--out is required for private evidence retention")
    try:
        receipt = retain_browser_capture(args.from_browser, args.out) if args.from_browser else acquire(args.out)
    except (OSError, ValueError, urllib.error.URLError, zipfile.BadZipFile, KeyError):
        parser.error("MRFF acquisition failed; inspect the official page, host, licence, and workbook response")
    print(json.dumps({
        "status": receipt["status"],
        "observed_at": receipt["observed_at"],
        "data_correct_as_at": receipt["data_correct_as_at"],
        "publication_date": receipt["publication_date"],
        "resource_count": len(receipt["resources"]),
        "total_bytes": sum(item["bytes"] for item in receipt["resources"]),
        "opportunity_admission": False,
    }, indent=2))


if __name__ == "__main__":
    main()
