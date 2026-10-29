"""Build provisional CHHHS candidates from verified cached RIF-CS archive pages."""
from __future__ import annotations

import hashlib
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from scripts.ardc_activities_archive import OAI, OAI_ID_PREFIX, RIF, extract_archive_page
    from scripts.ardc_secondary_filter import filter_responses
except ModuleNotFoundError:
    from ardc_activities_archive import OAI, OAI_ID_PREFIX, RIF, extract_archive_page
    from ardc_secondary_filter import filter_responses
import json


def filter_cached_pages(checkpoint: Path, pages: list[int], aliases_raw: bytes) -> dict:
    """Read only complete hash-sidecar pairs; do not assert full generation."""
    if not isinstance(pages, list) or not pages or any(type(i) is not int or i < 0 for i in pages) or len(set(pages)) != len(pages):
        raise ValueError('Distinct page numbers required')
    source_hashes, source_positions = {}, {}
    def batches():
        for index in pages:
            path = checkpoint / f'page-{index}.xml'
            digest_path = checkpoint / f'page-{index}.xml.sha256'
            if path.is_symlink() or digest_path.is_symlink() or not path.is_file() or not digest_path.is_file():
                raise ValueError('Complete checkpoint page and hash required')
            raw = path.read_bytes()
            if digest_path.read_text() != hashlib.sha256(raw).hexdigest():
                raise ValueError('Checkpoint page hash mismatch')
            page = extract_archive_page(raw)
            keys = {row['id']: row['key'] for row in page['activities']}
            root = ET.fromstring(raw)
            records = []
            positions = {}
            for position, item in enumerate(root.findall('.//' + OAI + 'record')):
                identity = item.findtext(OAI + 'header/' + OAI + 'identifier', '')
                if not identity.startswith(OAI_ID_PREFIX):
                    continue
                identity = identity[len(OAI_ID_PREFIX):]
                if identity not in keys:
                    continue
                positions[identity] = position
                activity = item.find('./' + OAI + 'metadata/' + RIF + 'registryObjects/' + RIF + 'registryObject/' + RIF + 'activity')
                # Keep XML field names in match paths and expose only text values
                # for detection; source XML is never rewritten or included.
                fields = {}
                for child in activity:
                    tag = child.tag.rsplit('}', 1)[-1]
                    fields.setdefault(tag, []).extend(text.strip() for text in child.itertext() if text.strip())
                records.append({'id': identity, 'key': keys[identity], 'description': fields})
            synthetic = json.dumps({'status': 'OK', 'code': 200, 'data': {'records': records}}, ensure_ascii=False).encode()
            name = f'page-{index}.xml'
            source_hashes[name] = hashlib.sha256(raw).hexdigest()
            source_positions[name] = positions
            yield name, synthetic
    result = filter_responses(batches(), aliases_raw)
    for item in result['candidates']:
        item['source_sha256'] = source_hashes[item['source_file']]
        item['record_index'] = source_positions[item['source_file']][item['activity_id']]
    for item in result['source_files']:
        item['sha256'] = source_hashes[item['source']]
    result.update(format='rims-ardc-rifcs-checkpoint-candidates-v1', source_complete_verified=False,
                  current_snapshot_verified=False, source_is_checkpoint_copy=True)
    return result
