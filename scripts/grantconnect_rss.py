"""Manual GrantConnect RSS bootstrap using the existing standard RSS connector.

No schedule, publisher-page scraping, deadline inference or reviewed admission.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import copy
import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_grants_flow_package import DEFAULT_DEFINITION
from scripts.consume_retained_pubmed import pinned
from scripts.reconcile_arc_awards_snapshots import write_new

FEED = 'https://www.grants.gov.au/public_data/rss/rss.xml'
NAME = 'CHHHS RIMS - GrantConnect RSS - Manual Bootstrap'


def definition():
    """Reuse the canonical manual-flow envelope and the qualified RSS operation."""
    seed = json.loads(DEFAULT_DEFINITION.read_bytes())
    source = seed['properties']['definition']
    result = {k: copy.deepcopy(source[k]) for k in ('$schema', 'contentVersion', 'parameters')}
    result['triggers'] = {'manual': {'type': 'Request', 'kind': 'Button',
        'inputs': {'schema': {'type': 'object', 'additionalProperties': False, 'properties': {}}}}}
    result['actions'] = {
        'Read_GrantConnect_RSS': {'type': 'OpenApiConnection', 'runAfter': {}, 'inputs': {
            'host': {'apiId': '/providers/Microsoft.PowerApps/apis/shared_rss',
                     'connectionName': 'shared_rss', 'operationId': 'ListFeedItems'},
            'parameters': {'feedUrl': FEED}, 'retryPolicy': {'type': 'none'}}},
        'Capture_complete_feed': {'type': 'Compose', 'runAfter': {'Read_GrantConnect_RSS': ['Succeeded']},
            'inputs': {'kind': 'grantconnect_rss_connector_capture_v1', 'source_url': FEED,
                       'observed_utc': '@utcNow()', 'coverage': 'returned_current_feed_only',
                       'publisher_xml_retained': False,
                       'items': "@body('Read_GrantConnect_RSS')"}}
    }
    return result


def project(capture):
    """Preserve all returned fields; only explicit feed identity/title/link map."""
    if (capture.get('kind') != 'grantconnect_rss_connector_capture_v1'
            or capture.get('source_url') != FEED or not capture.get('observed_utc')
            or capture.get('coverage') != 'returned_current_feed_only'
            or not isinstance(capture.get('items'), list)):
        raise ValueError('Complete exact connector capture required')
    rows, seen = [], set()
    for item in capture['items']:
        if not isinstance(item, dict):
            raise ValueError('RSS record required')
        identity, title, link = (item.get(k) for k in ('id', 'title', 'primaryLink'))
        if any(not isinstance(x, str) or not x or x != x.strip() for x in (identity, title, link)):
            raise ValueError('Exact RSS identity, title and link required')
        parsed = urlsplit(link)
        if (parsed.scheme not in ('http', 'https') or parsed.hostname not in ('grants.gov.au', 'www.grants.gov.au')
                or parsed.username or parsed.password or parsed.port not in (None, 80, 443)):
            raise ValueError('Official GrantConnect record link required')
        if identity in seen:
            raise ValueError('Duplicate feed identity; preserve capture before admission')
        seen.add(identity)
        raw = json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
        rows.append({'Source': 'GrantConnectRSS', 'SourceID': identity, 'Title': title,
                     'URL': link, 'RetrievedUTC': capture['observed_utc'],
                     'PublishedRaw': item.get('publishDate'), 'UpdatedRaw': item.get('updatedOn'),
                     'Deadline': None, 'Status': 'Unknown', 'ReviewStatus': 'Needs Review',
                     'RawItem': copy.deepcopy(item), 'RawItemSHA256': hashlib.sha256(raw.encode()).hexdigest()})
    return {'kind': 'grantconnect_rss_candidate_rows_v1', 'source_url': FEED,
            'coverage': capture['coverage'], 'count': len(rows), 'rows': rows,
            'canonical_admission': False, 'absence_means_withdrawn': False,
            'publisher_xml_retained': capture.get('publisher_xml_retained') is True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['definition', 'project'])
    parser.add_argument('--input', type=Path)
    parser.add_argument('--input-sha256')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.operation == 'project':
        if args.input is None or not args.input_sha256:
            parser.error('project requires --input and --input-sha256')
        result = project(pinned(args.input, args.input_sha256))
    else:
        if args.input is not None or args.input_sha256:
            parser.error('definition takes no capture input')
        result = definition()
    write_new(args.output, result, [args.input] if args.input else [])
    print('prepared locally; no native execution or admission')


if __name__ == '__main__':
    main()
