"""Explore retained ClinicalTrials.gov records locally; no network or native writes.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
from urllib.parse import urlsplit

from scripts.clinicaltrials_source import project
from scripts.source_capture_receipt import strict_json


def _url(value):
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('Evidence references require HTTPS without credentials')
    return value


def validate_associations(associations):
    if not isinstance(associations, list):
        raise ValueError('Association array required')
    by_key = {}
    for link in associations:
        required = {'source_key', 'review_status', 'involvement', 'evidence_url', 'ppg_evidence_urls'}
        if not isinstance(link, dict) or set(link) != required:
            raise ValueError('Association fields differ from contract')
        if link['source_key'] in by_key or link['review_status'] != 'Reviewed':
            raise ValueError('Unique reviewed associations required')
        if link['involvement'] not in {'conducting_site', 'sponsor', 'investigator_affiliation'}:
            raise ValueError('Explicit involvement role required')
        _url(link['evidence_url'])
        if not isinstance(link['ppg_evidence_urls'], list):
            raise ValueError('PPG evidence link array required')
        for value in link['ppg_evidence_urls']:
            _url(value)
        by_key[link['source_key']] = link
    return by_key


def explore(raw, expected_sha256, *, observed_at, associations, query='', status='',
            study_type='', country=''):
    """Return two explicitly scoped views over one independently pinned local capture.

    Associations are reviewed assertions supplied by the caller, never inferred
    from a name, location or sponsor. PPG references remain links only.
    """
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Capture hash mismatch')
    from datetime import datetime
    when = datetime.fromisoformat(observed_at.replace('Z', '+00:00'))
    if when.tzinfo is None:
        raise ValueError('Timezone-aware observation time required')
    body = strict_json(raw)
    if not isinstance(body, dict) or set(body) != {'studies'} or not isinstance(body['studies'], list):
        raise ValueError('A retained studies array is required; API pagination envelopes are not complete captures')
    by_key = validate_associations(associations)
    result = {'chhhs_associated': [], 'external_discovery': []}
    seen = set()
    for record in body['studies']:
        nct = record['protocolSection']['identificationModule']['nctId']
        row = project(record, nct)
        key = row['SourceKey']
        if key in seen:
            raise ValueError('Duplicate source identity')
        seen.add(key)
        protocol = record['protocolSection']
        conditions = protocol.get('conditionsModule', {}).get('conditions', [])
        interventions = protocol.get('armsInterventionsModule', {}).get('interventions', [])
        locations = protocol.get('contactsLocationsModule', {}).get('locations', [])
        if (not isinstance(conditions, list) or any(not isinstance(x, str) for x in conditions)
                or not isinstance(interventions, list) or not isinstance(locations, list)):
            raise ValueError('Malformed discovery fields')
        intervention_names = [x.get('name', '') for x in interventions]
        countries = [x.get('country', '') for x in locations]
        if any(not isinstance(x, str) for x in intervention_names + countries):
            raise ValueError('Discovery labels must be strings')
        text = ' '.join([row['Title'] or '', nct, *conditions, *intervention_names]).casefold()
        if (query.casefold() not in text or (status and row['OverallStatus'] != status)
                or (study_type and row['StudyType'] != study_type)
                or (country and country.casefold() not in {x.casefold() for x in countries})):
            continue
        association = by_key.get(key)
        row.update({'Conditions': conditions, 'Interventions': intervention_names,
                    'Countries': sorted(set(countries)),
                    'IsInterventionalTrial': {'INTERVENTIONAL': True, 'OBSERVATIONAL': False}.get(row['StudyType']),
                    'CHHHSInvolvement': association, 'SourceObservedUTC': observed_at})
        result['chhhs_associated' if association else 'external_discovery'].append(row)
    if set(by_key) - seen:
        raise ValueError('Association references absent from capture')
    for rows in result.values():
        rows.sort(key=lambda x: x['SourceKey'])
    return {'schema_version': 1, 'capture_sha256': expected_sha256,
            'observed_at': observed_at, 'capture_records': len(seen),
            'scope': 'Selected retained records; not a complete registry or CHHHS census',
            'filters': dict(query=query, status=status, study_type=study_type, country=country),
            'associations_sha256': hashlib.sha256(json.dumps(associations, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest(),
            'views': result}


def explore_dora(raw, expected_sha256, *, associations, query='', status='', study_type='', country=''):
    from scripts.dora_study_projection import project_dora
    rows, observed_at = project_dora(raw, expected_sha256)
    by_key = validate_associations(associations)
    if set(by_key) - {row['SourceKey'] for row in rows}:
        raise ValueError('Association references absent from capture')
    result = {'chhhs_associated': [], 'external_discovery': []}
    for row in rows:
        text = ' '.join([row['Title'] or '', row['SourceKey'], str(row['SourceProjectID']) if row['SourceProjectID'] is not None else '', *row['Conditions']]).casefold()
        if (query.casefold() not in text or (status and row['OverallStatus'] != status)
                or (study_type and row['StudyType'] != study_type)
                or (country and country.casefold() not in {x.casefold() for x in row['Countries']})):
            continue
        link = by_key.get(row['SourceKey'])
        row['CHHHSInvolvement'] = link
        result['chhhs_associated' if link else 'external_discovery'].append(row)
    for selected in result.values():
        selected.sort(key=lambda row: row['SourceKey'])
    return {'schema_version': 1, 'capture_sha256': expected_sha256,
            'observed_at': observed_at, 'capture_records': len(rows),
            'scope': 'Selected retained DoRA activity resource; not a complete registry or CHHHS census',
            'filters': dict(query=query, status=status, study_type=study_type, country=country),
            'associations_sha256': hashlib.sha256(json.dumps(associations, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest(),
            'views': result}


def render(result):
    escape = html.escape
    sections = []
    for name, label in [('chhhs_associated', 'CHHHS-associated studies'),
                        ('external_discovery', 'External discovery candidates')]:
        items = []
        for row in result['views'][name]:
            role = (row['CHHHSInvolvement'] or {}).get('involvement', 'Unconfirmed')
            links = (row['CHHHSInvolvement'] or {}).get('ppg_evidence_urls', [])
            evidence = ' '.join(f'<a href="{escape(u, quote=True)}">PPG evidence {i+1}</a>' for i, u in enumerate(links))
            items.append(f'<li><a href="{escape(row["SourceURL"], quote=True)}">{escape(row["Title"] or row.get("StudyIdentifier", row.get("NCTId", row["SourceKey"])))}</a> '
                         f'— {escape(row.get("StudyIdentifier", row.get("NCTId", row["SourceKey"])))}; {escape(row["StudyType"] or "Unknown type")}; '
                         f'{escape(row["OverallStatus"] or "Unknown status")}; {escape(role)} {evidence}</li>')
        sections.append(f'<h2>{label}</h2><p>{len(items)} selected records.</p><ul>{"".join(items)}</ul>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Study explorer</title>'
            '<h1>Study explorer</h1><p>' + escape(result['scope']) + '</p><p>Observed: '
            + escape(result['observed_at']) + '</p><p>Registry status may be stale. '
            'A CHHHS association does not establish a conducting site, patient eligibility or accreditation.</p>'
            + ''.join(sections) + '</html>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--input', type=Path)
    inputs.add_argument('--dora-directory', type=Path, help='Existing directory containing receipt.json and records.json')
    inputs.add_argument('--dora-capture', type=Path, help='Existing DoRA activity receipt plus records envelope')
    inputs.add_argument('--archive', type=Path, help='Existing qualified exact-ID ClinicalTrials ZIP')
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--observed-at', help='Required for CT; DoRA uses its retained receipt timestamp')
    parser.add_argument('--associations', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    for field in ('query', 'status', 'study-type', 'country'):
        parser.add_argument('--' + field, default='')
    args = parser.parse_args()
    # Reuse the repository's private-output boundary and no-overwrite policy.
    from scripts.source_capture_receipt import create_output
    associations = strict_json(args.associations.read_bytes()) if args.associations else []
    dora_receipt_sha256 = None
    if args.dora_directory:
        receipt_bytes = (args.dora_directory / 'receipt.json').read_bytes()
        dora_receipt_sha256 = hashlib.sha256(receipt_bytes).hexdigest()
        if dora_receipt_sha256 != args.sha256:
            raise ValueError('DoRA receipt hash mismatch')
        envelope = strict_json(receipt_bytes)
        if 'records' in envelope:
            raise ValueError('Directory receipt must not override records.json')
        envelope['records'] = strict_json((args.dora_directory / 'records.json').read_bytes())
        raw = json.dumps(envelope, ensure_ascii=False, allow_nan=False).encode()
    else:
        raw = (args.input or args.archive or args.dora_capture).read_bytes()
    archive_hash = None
    if args.archive:
        import base64
        import zlib
        from scripts.prepare_study_json_reader import qualify_zip
        members = qualify_zip(raw, args.sha256)
        archive_hash = args.sha256
        raw = json.dumps({'studies': [strict_json(zlib.decompress(base64.b64decode(value['payload']), -15))
                                     for value in members.values()]}, ensure_ascii=False, allow_nan=False).encode()
    if args.dora_capture or args.dora_directory:
        if args.observed_at:
            parser.error('DoRA uses its retained observation time; omit --observed-at')
        result = explore_dora(raw, hashlib.sha256(raw).hexdigest() if args.dora_directory else args.sha256, associations=associations, query=args.query,
                              status=args.status, study_type=args.study_type, country=args.country)
    else:
        if not args.observed_at:
            parser.error('--observed-at is required for ClinicalTrials.gov input')
        result = explore(raw, hashlib.sha256(raw).hexdigest() if args.archive else args.sha256, observed_at=args.observed_at,
                         associations=associations, query=args.query, status=args.status,
                         study_type=args.study_type, country=args.country)
    result['archive_sha256'] = archive_hash
    result['dora_receipt_sha256'] = dora_receipt_sha256
    destination = create_output(args.output)
    (destination / 'study-explorer.json').write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + '\n')
    (destination / 'study-explorer.html').write_text(render(result))
    print(json.dumps({'selected': {k: len(v) for k, v in result['views'].items()}, 'native_modified': False}))


if __name__ == '__main__':
    main()
