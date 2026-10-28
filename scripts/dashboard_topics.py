"""Build separate topic memberships from fingerprinted retained evidence.

No acquisition or native writes. Names never resolve identities. Missing catalogue
entries and conflicting assertions remain diagnostics rather than guessed groups.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime


def retained_work(envelope):
    if (envelope.get('kind') != 'openalex_retained_observation_v1'
            or envelope.get('source') != 'OpenAlex' or envelope.get('http_status') != 200):
        raise ValueError('Successful retained OpenAlex observation required')
    raw = base64.b64decode(envelope['raw_response_base64'], validate=True)
    if (len(raw) != envelope['raw_byte_count']
            or hashlib.sha256(raw).hexdigest() != envelope['raw_response_sha256']):
        raise ValueError('Raw response fingerprint mismatch')
    observed = envelope['observed_utc']
    stamp = datetime.fromisoformat(observed.replace('Z', '+00:00'))
    if stamp.utcoffset() is None:
        raise ValueError('Observation timestamp needs timezone')
    payload = json.loads(raw)
    if payload.get('id') != envelope['work_id']:
        raise ValueError('Provider work identity mismatch')
    return payload


def objects(payload, name):
    value = payload.get(name)
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(x, dict) for x in value):
        raise ValueError('Unexpected structured field: ' + name)
    return value


def mesh_catalogue(records, edition):
    """NLM descriptor catalogue supplied as retained, versioned structured records."""
    if not edition:
        raise ValueError('Explicit NLM catalogue edition required')
    result = {}
    for row in records:
        key = row.get('descriptor_id')
        if (not isinstance(key, str) or not re.fullmatch(r'D[0-9]+', key)
                or row.get('edition') != edition or not row.get('label')
                or not re.fullmatch(r'[0-9a-f]{64}', row.get('source_hash', ''))):
            raise ValueError('Versioned NLM descriptor identity/provenance required')
        trees = row.get('tree_positions')
        if (not isinstance(trees, list) or not trees
                or any(not isinstance(t, str) or not re.fullmatch(r'[A-Z][0-9]{2}(?:\.[0-9]{1,3})*', t)
                       for t in trees)):
            raise ValueError('Explicit NLM tree positions required')
        normalized = dict(row, tree_positions=sorted(set(trees)))
        if key in result and result[key] != normalized:
            raise ValueError('Conflicting descriptor catalogue records')
        result[key] = normalized
    return result


def mesh_xml_catalogue(path, edition, expected_source_sha256):
    """Read the retained NLM annual descriptor XML/gzip, with no network access.

    Edition is pinned by the acquisition manifest, never inferred from a label.
    Descriptors lacking tree positions remain absent from the hierarchy catalogue.
    """
    from pathlib import Path
    path=Path(path)
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    if digest.hexdigest()!=expected_source_sha256:
        raise ValueError('NLM catalogue fingerprint mismatch')
    opener=gzip.open if path.suffix=='.gz' else open
    records=[]
    with opener(path,'rb') as stream:
        for _,element in ET.iterparse(stream,events=('end',)):
            if element.tag!='DescriptorRecord':continue
            trees=[x.text for x in element.findall('TreeNumberList/TreeNumber') if x.text]
            if trees:
                records.append(dict(descriptor_id=element.findtext('DescriptorUI'),
                                    label=element.findtext('DescriptorName/String'),
                                    tree_positions=trees,edition=edition,source_hash=expected_source_sha256))
            element.clear()
    return records


def build_topics(publication_keys, observations, crosswalk, catalogue, mesh_edition):
    """Crosswalk maps exact provider work IDs to canonical keys, never DOI/name guesses.

    Each observation is one immutable selected snapshot. Multiple differing
    snapshots for a work fail closed so the caller must select a dated generation.
    """
    keys = set(publication_keys)
    if any(not isinstance(k, str) or not k for k in keys):
        raise ValueError('Canonical publication keys required')
    catalog = mesh_catalogue(catalogue, mesh_edition)
    second_level_labels={tree:entry['label'] for entry in catalog.values()
                         for tree in entry['tree_positions'] if '.' not in tree}
    memberships = {}; diagnostics = []; selected = {}
    def retain(identity, row):
        # The snapshot table currently carries one provenance record per membership.
        # Never let a later provider assertion silently replace an earlier record.
        existing = memberships.get(identity)
        if existing is not None and existing != row:
            raise ValueError('Conflicting membership assertions require explicit reconciliation')
        memberships[identity] = row
    for envelope in observations:
        work = retained_work(envelope)
        work_id = work['id']; fingerprint = envelope['raw_response_sha256']
        identity = (fingerprint, envelope['observed_utc'])
        if work_id in selected and selected[work_id] != identity:
            raise ValueError('Select one dated provider snapshot per work')
        selected[work_id] = identity
        mapped = crosswalk.get(work_id, [])
        if not isinstance(mapped, list) or any(k not in keys for k in mapped):
            raise ValueError('Crosswalk contains noncanonical publication keys')
        if not mapped:
            diagnostics.append(dict(work_id=work_id, reason='unmapped_provider_work'))
            continue
        provenance = dict(source='OpenAlex', provider_work_id=work_id,
                          observed_utc=envelope['observed_utc'], source_hash=fingerprint)
        topics = objects(work, 'topics')
        primary = work.get('primary_topic')
        if primary is not None and not isinstance(primary, dict):
            raise ValueError('Unexpected primary topic schema')
        # Retain a primary assignment even when the provider omitted it from topics[].
        assertions = [(t, False) for t in topics] + ([(primary, True)] if primary else [])
        topic_definitions = {}
        primary_id = primary.get('id') if primary else None
        for topic, is_primary in assertions:
            topic_id = topic.get('id'); subfield = topic.get('subfield')
            if (not isinstance(topic_id, str) or not re.fullmatch(r'https://openalex.org/T[0-9]+', topic_id)
                    or not topic.get('display_name') or not isinstance(subfield, dict)
                    or not subfield.get('id') or not subfield.get('display_name')):
                diagnostics.append(dict(work_id=work_id, reason='incomplete_openalex_topic', topic_id=topic_id))
                continue
            definition = (topic['display_name'], json.dumps(subfield, sort_keys=True),
                          json.dumps(topic.get('field'), sort_keys=True),
                          json.dumps(topic.get('domain'), sort_keys=True))
            if topic_id in topic_definitions and topic_definitions[topic_id] != definition:
                raise ValueError('Conflicting topic hierarchy within one snapshot')
            topic_definitions[topic_id] = definition
            for key in set(mapped):
                membership = dict(provenance, publication_key=key, taxonomy='OpenAlex',
                                  topic_id=topic_id, label=topic['display_name'],
                                  hierarchy={'subfield': subfield, 'field': topic.get('field'), 'domain': topic.get('domain')},
                                  primary=is_primary or topic_id == primary_id,
                                  classification_version='provider_snapshot:' + fingerprint, status='qualified')
                retain(('OpenAlex', key, topic_id), membership)
        for mesh in objects(work, 'mesh'):
            descriptor = mesh.get('descriptor_ui')
            entry = catalog.get(descriptor)
            if entry is None:
                diagnostics.append(dict(work_id=work_id, reason='mesh_descriptor_not_in_versioned_catalogue',
                                        descriptor_id=descriptor, source_label=mesh.get('descriptor_name')))
                continue
            for key in set(mapped):
                # Distinct membership, with all hierarchy positions preserved in one row.
                retain(('MeSH', key, descriptor), dict(provenance,
                    publication_key=key, taxonomy='MeSH', topic_id=descriptor, label=entry['label'],
                    hierarchy={'tree_positions': entry['tree_positions'],
                               # NLM letter category (A) followed by two digits
                               # (A01) defines the second-level group here.
                               'second_level_groups': sorted({t.split('.')[0] for t in entry['tree_positions']}),
                               'second_level_group_labels': {t:second_level_labels.get(t) for t in sorted({x.split('.')[0] for x in entry['tree_positions']})}},
                    classification_version=mesh_edition, catalogue_hash=entry['source_hash'], status='qualified'))
    rows = [memberships[k] for k in sorted(memberships)]
    coverage = {taxonomy: len({r['publication_key'] for r in rows if r['taxonomy'] == taxonomy})
                for taxonomy in ('MeSH', 'OpenAlex')}
    return dict(memberships=rows, diagnostics=diagnostics,
                coverage={t:dict(included=len(keys), classified=n, unknown=len(keys)-n) for t,n in coverage.items()},
                native_acceptance=False, canonical_mutation=False, additive=False)
