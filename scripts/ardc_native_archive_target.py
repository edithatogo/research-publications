"""Bind an ARDC archive read to an independently accepted native target."""
from __future__ import annotations

import hashlib
import json
import re


def validate_target(marker: bytes, folder_manifest: bytes, *, expected_sha256: str,
                    expected_folder: str) -> dict:
    """Validate marker identity and the exact private folder before any read.

    The caller must obtain the expected hash and folder from independently
    accepted evidence. This function performs no native request or mutation.
    """
    if (not isinstance(marker, bytes) or not isinstance(folder_manifest, bytes)
            or marker != folder_manifest or not isinstance(expected_sha256, str)
            or re.fullmatch(r'[0-9a-f]{64}', expected_sha256) is None
            or hashlib.sha256(marker).hexdigest() != expected_sha256):
        raise ValueError('Marker does not match the accepted manifest')
    try:
        document = json.loads(marker)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('Invalid archive marker') from None
    if (not isinstance(document, dict) or document.get('source') != 'ardc'
            or document.get('format') != 'rims-ardc-public-registry-v1'
            or document.get('complete') is not True):
        raise ValueError('Unqualified ARDC archive')
    folder = document.get('archive_folder')
    if (not isinstance(folder, str) or folder != expected_folder or not folder.startswith('/Documents/')
            or any(c in folder for c in "'?#%\\") or any(p in ('.', '..', '') for p in folder.split('/')[1:])):
        raise ValueError('Archive folder differs from the exact accepted target')
    return {'manifest_sha256': expected_sha256, 'archive_folder': folder,
            'exact_target_validated': True, 'native_read_performed': False}
