"""Validate an exact immutable Activities archive upload plan without network I/O."""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit


def qualify_upload(binding: dict, plan: dict, raw: bytes) -> dict:
    """Bind one numbered capture batch to the independently pinned target.

    This is local preparation only. It does not establish permissions, perform
    a write, publish a completion marker, or verify native stored bytes.
    """
    if not isinstance(binding, dict) or not isinstance(plan, dict) or not isinstance(raw, bytes):
        raise ValueError('Invalid upload inputs')
    target = binding.get('ardcActivitiesArchiveTarget')
    if (not isinstance(target, dict) or plan.get('format') != 'rims-ardc-activities-upload-v1'
            or plan.get('site') != target.get('site') or plan.get('folder') != target.get('folder')):
        raise ValueError('Upload target differs from pinned target')
    try:
        site = urlsplit(target['site'])
        folder = target['folder']
    except (KeyError, TypeError, ValueError):
        raise ValueError('Invalid pinned target') from None
    if (site.scheme != 'https' or not site.hostname or not site.hostname.endswith('.sharepoint.com')
            or site.username or site.password or site.port is not None or site.query or site.fragment
            or not re.fullmatch(r'/(?:personal|sites)/[A-Za-z0-9_-]+', site.path)
            or site.geturl() != target['site'] or site.scheme + '://' + site.netloc not in binding.get('resources', [])
            or not isinstance(folder, str) or not folder.startswith('/Documents/')
            or any(c in folder for c in "'?#%\\") or any(p in ('', '.', '..') for p in folder.split('/')[1:])):
        raise ValueError('Unsafe or unpinned target')
    digest = hashlib.sha256(raw).hexdigest()
    if (not raw or len(raw) > 20_000_000 or plan.get('bytes') != len(raw)
            or plan.get('sha256') != digest or not isinstance(plan.get('name'), str)
            or re.fullmatch(r'activities-batch-[0-9]{9}\.json', plan['name']) is None):
        raise ValueError('Payload differs from immutable upload plan')
    return {'site': target['site'], 'folder': folder, 'name': plan['name'], 'bytes': len(raw),
            'sha256': digest, 'native_write_performed': False, 'native_readback_verified': False}
