"""Capture all advertised NHMRC/MRFF workbooks without Premium flow HTTP.

Retains original pages, copyright guidance and binary workbooks. No award
filtering, register writes, grants-opportunity admission or redistribution.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import uuid
import zipfile
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request

from scripts.source_capture_receipt import (
    commit_generation,
    create_output,
    response_retainer,
    scope_sha256,
    write_failure_receipt,
)
from scripts.source_http_retry import guarded_urlopen, read_response

SOURCES = {
    'nhmrc': ('https://www.nhmrc.gov.au/funding/data-research/outcomes', 'https://www.nhmrc.gov.au/copyright'),
    'mrff': ('https://www.health.gov.au/resources/publications/medical-research-future-fund-mrff-grant-recipients?language=en',
             'https://www.health.gov.au/using-our-websites/copyright'),
}
MAX_FILES = 100
MAX_TOTAL_BYTES = 256_000_000


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(value for key, value in attrs if key == 'href' and isinstance(value, str))


def discover(raw, page_url):
    parser = Links()
    parser.feed(raw.decode('utf-8-sig'))
    parser.close()
    selected = set()
    for link in parser.links:
        parsed = urlsplit(urljoin(page_url, link))
        suffix = Path(unquote(parsed.path)).suffix.lower()
        if suffix in {'.xls', '.xlsm', '.csv', '.ods'}:
            raise ValueError('Unsupported advertised tabular source; do not omit it')
        if suffix != '.xlsx':
            continue
        if (parsed.scheme != 'https' or parsed.netloc != urlsplit(page_url).netloc
                or not parsed.path.startswith('/sites/default/files/')
                or parsed.username or parsed.password or parsed.port not in (None, 443)):
            raise ValueError('Workbook link outside exact official source')
        selected.add(parsed._replace(fragment='').geturl())
    if not 1 <= len(selected) <= MAX_FILES:
        raise ValueError('Complete nonempty bounded workbook inventory required')
    return sorted(selected)


def verify_workbook(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if (len(entries) > 10000 or sum(entry.file_size for entry in entries) > 256_000_000
                or len({entry.filename for entry in entries}) != len(entries)
                or any(entry.flag_bits & 1 or entry.filename.startswith('/')
                       or '..' in Path(entry.filename).parts for entry in entries)
                or not {'[Content_Types].xml', 'xl/workbook.xml'} <= set(archive.namelist())):
            raise ValueError('Unsafe or incomplete workbook ZIP')
        if archive.testzip() is not None:
            raise ValueError('Workbook ZIP integrity failure')
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'zip_integrity': 'passed'}


def capture(source, output, *, opener=None, sleep=time.sleep):
    if source not in SOURCES:
        raise ValueError('Existing official workbook source required')
    page_url, rights_url = SOURCES[source]
    output = Path(output)
    create_output(output)
    scope = {'source': source, 'kind': 'all_advertised_official_workbooks', 'page_url': page_url}
    manifest = {'source': source, 'scope': scope, 'scope_sha256': scope_sha256(scope),
        'generation_id': uuid.uuid4().hex, 'captured_utc': datetime.now(UTC).isoformat(),
        'files': [], 'request_attempts': [], 'max_read_attempts': 1,
        'record_kind': 'awarded_grant_originals', 'opportunity_admission': False,
        'adaptation_or_external_redistribution': False, 'native_admission': False}
    total_bytes = 0
    completed = []
    current = None

    def read(url, name):
        nonlocal total_bytes
        raw, _, _, _ = read_response(Request(url), manifest['request_attempts'],
            opener=opener or guarded_urlopen, max_attempts=1, sleep=sleep,
            retain=response_retainer(output, manifest, {'source_url': url}, name))
        total_bytes += len(raw)
        if total_bytes > MAX_TOTAL_BYTES:
            raise ValueError('Official source combined byte cap exceeded')
        return raw

    try:
        before = discover(read(page_url, 'source-page-before.bin'), page_url)
        read(rights_url, 'copyright-page.bin')
        inventory = []
        for index, url in enumerate(before):
            current = url
            name = f'{source}-{index + 1:02d}-original.bin'
            raw = read(url, name)
            proof = verify_workbook(raw)
            sleep(1)
            repeated = read(url, f'{source}-{index + 1:02d}-repeat.bin')
            if repeated != raw:
                raise ValueError('Official workbook changed across repeated reads')
            inventory.append({'source_url': url, 'retained_file': name,
                              'original_filename': Path(unquote(urlsplit(url).path)).name, **proof})
            completed.append(url)
        if discover(read(page_url, 'source-page-after.bin'), page_url) != before:
            raise ValueError('Official workbook link inventory changed during capture')
        manifest['count'] = len(inventory)
        return commit_generation(output, 'workbooks.json', inventory, manifest)
    except Exception as error:
        write_failure_receipt(output, source=source, scope=scope, files=manifest['files'],
            completed_ids=completed, failed_id=current, error=error,
            generation_id=manifest['generation_id'], request_attempts=manifest['request_attempts'])
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=sorted(SOURCES), required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    if not args.capture:
        print(json.dumps({'source': args.source, 'provider_calls': 0, 'scope': 'all_advertised_official_workbooks'}))
        return
    if args.output is None:
        parser.error('--capture requires private --output')
    result = capture(args.source, args.output)
    print(json.dumps({'complete': result['complete'], 'files': result['count'], 'accepted': False}))


if __name__ == '__main__':
    main()
