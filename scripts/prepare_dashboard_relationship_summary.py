"""Append typed relationship consumers locally; never infer links or adjudicate rows.

Amended from retained source. Current model contracts and original report parts
remain authoritative; labels, facility matches and source project IDs are not joins.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from scripts.dashboard_reader_source import (add_page, capture, dependencies, direct,
    model_contract, require, visual, words, write_candidate)
from scripts.prepare_dashboard_overview import literal

PAGE = 'ResearchRelationships'
TYPED_FIELDS = ('RelationshipKey', 'RelationshipType', 'FromKey', 'ToKey', 'EvidenceURL',
                'Confidence', 'ReviewStatusRaw', 'PublicationCanonicalKey', 'AwardSourceID',
                'TypedAdmissionState', 'AdmissionState')
REQUIRED = [('Funding Relationship Context', name, {'string'}) for name in TYPED_FIELDS]
REQUIRED += [('Funding Relationship Context', name, {'int64'}) for name in
             ('IdentityMatchCount', 'TypedBindingCount', 'NativeKeyCount')]
REQUIRED += [('Publication', 'CanonicalKey', {'string'}), ('ARCAwardContext', 'SourceID', {'string'}),
             ('Publication', 'AuthorCount', {'int64'}), ('Publication', 'FacilityMatchCount', {'int64'})]
MEASURES = [('Funding Relationship Context', name) for name in (
    'Candidate links', 'Confirmed reviewed links', 'Unclassified or unresolved links', 'Current relationship rows')]
MEASURES += [('Publication', 'Publications')]


def qualified_links(links, allowed_hosts):
    if links is None:
        return {}  # Explicitly unavailable, never guessed from source keys.
    if not isinstance(links, dict) or set(links) != {'publications', 'candidate_links', 'confirmed_links'}:
        raise ValueError('Complete three-link contract required')
    if (not isinstance(allowed_hosts, (list, tuple, set, frozenset)) or not allowed_hosts or
            any(not isinstance(h, str) or h != h.lower() or not h.endswith('.sharepoint.com') for h in allowed_hosts)):
        raise ValueError('Exact qualified SharePoint host allowlist required')
    for url in links.values():
        if not isinstance(url, str) or not url or any(c.isspace() for c in url):
            raise ValueError('Invalid view URL')
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or parsed.hostname not in allowed_hosts or parsed.username or
                parsed.password or parsed.port or parsed.fragment or not parsed.path.endswith('.aspx')):
            raise ValueError('Expected exact-host HTTPS SharePoint view')
    return links.copy()


def prepare(source, output, links=None, *, expected_sha, model_definition,
            expected_model_sha, allowed_hosts=()):
    files = capture(source, expected_sha)
    contract = model_contract(model_definition, expected_model_sha)
    require(contract, REQUIRED, MEASURES)  # Missing typed keys/review evidence cannot become confirmed counts.
    links = qualified_links(links, allowed_hosts)
    items = []
    def add(name, kind, rect, title, **kwargs):
        item = visual(files, name, kind, rect, title, **kwargs); items.append(item); return item
    add('relationships-heading', 'textbox', (32, 8, 1856, 64), 'Research relationships',
        text='RESEARCH RELATIONSHIPS | Explicit evidence and coverage')
    add('relationships-guidance', 'textbox', (32, 88, 1856, 112), 'Evidence meaning',
        text='Existing governed measures consume explicit typed publication and award keys, relationship type, evidence, review and admission state. Candidate and confirmed reviewed states remain separate. This reader creates no links and makes no review decision. Blank means unavailable in this scope; zero does not prove no funding. Visual interactions remain unverified.')
    for index, (name, field, title) in enumerate([
        ('candidates', 'Candidate links', 'Candidate funding-link rows'),
        ('confirmed', 'Confirmed reviewed links', 'Confirmed reviewed funding-link rows'),
        ('unresolved', 'Unclassified or unresolved links', 'Unresolved relationship rows')]):
        add(name, 'card', (32+index*472, 224, 440, 136), title,
            roles={'Values': [direct('Funding Relationship Context', field, measure=True)]})
    activity = dependencies(contract, [('DORA Activity Registry', 'DORAActivityKey', {'string'})])
    if activity:
        add('source-activities', 'textbox', (1448, 224, 440, 136), 'Source activities unavailable',
            text='Source activity counts unavailable: no qualified DORA activity key field.')
    else:
        add('source-activities', 'card', (1448, 224, 440, 136), 'Nonblank source activity-key rows',
            roles={'Values': [direct('DORA Activity Registry', 'DORAActivityKey', count=True)]})
    for name, field, x, title in [('author-pattern', 'AuthorCount', 32, 'Publications by source author count'),
                                 ('facility-pattern', 'FacilityMatchCount', 976, 'Publications by facility-match count')]:
        add(name, 'barChart', (x, 400, 912, 336), title,
            roles={'Category': [direct('Publication', field)],
                   'Y': [direct('Publication', 'Publications', measure=True)]})
    add('relationship-state', 'barChart', (32, 776, 912, 280), 'Relationship rows by existing admitted state',
        roles={'Category': [direct('Funding Relationship Context', 'AdmissionState')],
               'Y': [direct('Funding Relationship Context', 'Current relationship rows', measure=True)]})
    add('relationship-limits', 'textbox', (976, 776, 912, 280), 'Identity and grain limits',
        text='Author counts and facility matches are source patterns, not verified collaborators or people. Project IDs are not assumed unique. No accepted publication-project crosswalk is supplied here. Relationship rows, activities, publications and awards have separate grains. No name match, funded-publication inference, combined research total or monetary sum is calculated.')
    for index, (key, title) in enumerate([('publications', 'Publication register'),
                                          ('candidate_links', 'Candidate funding links'),
                                          ('confirmed_links', 'Confirmed reviewed links')]):
        item = add('link-'+key, 'textbox', (32+index*632, 1104, 592, 96), title,
                   text=title+(': supplied view; access/existence unverified' if key in links else ': unavailable; no qualified view supplied'))
        if key in links:
            item['visual']['visualType'] = 'actionButton'
            item['visual']['objects'] = {'text': [{'properties': {'show': literal('true')}},
                {'selector': {'id': 'default'}, 'properties': {'text': words(title), 'fontSize': literal('16D')}}],
                'icon': [{'properties': {'show': literal('false')}}]}
            item['visual']['visualContainerObjects']['visualLink'] = [{'properties': {
                'show': literal('true'), 'type': words('WebUrl'), 'webUrl': words(links[key])}}]
    add('relationships-footer', 'textbox', (32, 1240, 1856, 112), 'Evidence boundary',
        text='Key existence and field types do not prove data completeness or admission correctness. Existing model review rules and source provenance remain authoritative. Model observation time is not provider freshness. No new key crosswalk, filter relationship, source approval, notification or sharing change is made.')
    updates = add_page(files, PAGE, 'Research relationships', 1400, items)
    return write_candidate(source, output, files, updates, contract,
                           'LOCAL_TYPED_RELATIONSHIP_READER_NOT_SAVED', missing=activity)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--expected-sha', required=True); p.add_argument('--model', type=Path, required=True)
    p.add_argument('--expected-model-sha', required=True); p.add_argument('--links', type=Path)
    p.add_argument('--allowed-host', action='append', default=[])
    a = p.parse_args()
    print(json.dumps(prepare(a.source, a.output, json.loads(a.links.read_text()) if a.links else None,
        expected_sha=a.expected_sha, model_definition=a.model.read_bytes(),
        expected_model_sha=a.expected_model_sha, allowed_hosts=a.allowed_host), indent=2))


if __name__ == '__main__': main()
