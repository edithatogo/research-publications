"""Reconstruct a retained report topic snapshot without OA intake dependencies.

Source slice: prepare_oa_openalex_handoff.py reconstruct; no provider I/O.
SPDX-License-Identifier: Apache-2.0
"""
import base64
import hashlib
import json


def reconstruct(rows, work):
    selected = [r for r in rows if r.get('[OpenAlexWorkID]') == work]
    if any(type(r.get('[ChunkIndex]')) is not int for r in selected):
        raise ValueError('Integer chunk indices required')
    selected.sort(key=lambda r: r['[ChunkIndex]'])
    if not selected:
        raise ValueError('Work absent from committed chunks')
    count = selected[0]['[ChunkCount]']
    chars = selected[0]['[MetadataCharacters]']
    if (type(count) is not int or count < 1 or type(chars) is not int or chars < 1 or
            [r['[ChunkIndex]'] for r in selected] != list(range(count)) or
            any(type(r['[ChunkCount]']) is not int or type(r['[MetadataCharacters]']) is not int
                or r['[ChunkCount]'] != count or r['[MetadataCharacters]'] != chars or
                not isinstance(r['[MetadataChunk]'],str) or
                r['[Encoding]'] != 'UTF8-HEX' for r in selected)):
        raise ValueError('Incomplete or conflicting committed chunks')
    text = ''.join(r['[MetadataChunk]'] for r in selected)
    if len(text) != chars:
        raise ValueError('Committed character count differs')
    envelope = json.loads(bytes.fromhex(text))
    if (envelope.get('kind') != 'openalex_retained_observation_v1' or
            envelope.get('source') != 'OpenAlex' or envelope.get('http_status') != 200 or
            envelope.get('work_id') != work):
        raise ValueError('Unqualified retained work envelope')
    raw = base64.b64decode(envelope['raw_response_base64'], validate=True)
    if (len(raw) != envelope['raw_byte_count'] or
            hashlib.sha256(raw).hexdigest() != envelope['raw_response_sha256'] or
            json.loads(raw).get('id') != work):
        raise ValueError('Original payload fingerprint/identity differs')
    return envelope, raw
