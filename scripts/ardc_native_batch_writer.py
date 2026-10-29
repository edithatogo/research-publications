"""Prepare strict batch plans and invoke the guarded ARDC create-only adapter.

The caller owns archive probes, exact readbacks and recovery. A writer failure
is uncertain and must never be retried without reconciling the existing target
and retained one-send journal. No schedule or collector is activated here.
"""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import re
import subprocess
from uuid import uuid4

try:
    from scripts.ardc_activity_batch import validate_batch
    from scripts.ardc_archive_upload_contract import qualify_upload
    from scripts.filter_ardc_sharepoint_archive import archive_target
except ModuleNotFoundError:
    from ardc_activity_batch import validate_batch
    from ardc_archive_upload_contract import qualify_upload
    from filter_ardc_sharepoint_archive import archive_target

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / 'scripts/ardc_archive_create_only.mjs'


def make_writer(overlay, credential, binding_path, workdir, *, batch_size=32, run=subprocess.run):
    """Return a capture-compatible put callback for an exact private binding.

    Calling the callback invokes a native mutation. It is deliberately separate
    from archive existence checks; the caller must use a qualified probe and
    subsequently verify the exact stored bytes. Every attempt has an immutable
    local plan and separate evidence directory, plus the adapter's stable journal.
    """
    binding_path, workdir = Path(binding_path), Path(workdir)
    for path in (binding_path, workdir):
        subprocess.run(['git', 'check-ignore', '-q', str(path.resolve())], cwd=ROOT, check=True)
    if workdir.is_symlink() or not workdir.is_dir():
        raise ValueError('Private working directory required')
    binding = json.loads(binding_path.read_bytes())
    site, folder = archive_target(binding)
    rows = overlay.get('activities') if isinstance(overlay, dict) else None
    if (not isinstance(rows, list) or not rows or type(batch_size) is not int
            or not 1 <= batch_size <= 32 or not isinstance(credential, bytes) or not credential):
        raise ValueError('Invalid capture identities or credential')
    if overlay.get('generation_lineage_verified') is not True:
        raise ValueError('Verified generation lineage required')

    pending = {}

    def put(name, raw):
        if not isinstance(name, str) or re.fullmatch(r'activities-batch-[0-9]{9}\.json', name) is None:
            raise ValueError('Invalid batch filename')
        offset = int(name[17:26])
        if offset % batch_size or offset >= len(rows):
            raise ValueError('Invalid batch offset')
        identities = rows[offset:offset + batch_size]
        validate_batch(raw, identities, credential)
        digest = hashlib.sha256(raw).hexdigest()
        plan = {'format': 'rims-ardc-activities-upload-v1', 'site': site, 'folder': folder,
                'name': name, 'local': name, 'bytes': len(raw), 'sha256': digest, 'identities': identities}
        qualify_upload(binding, plan, raw)
        attempt = workdir / ('attempt-' + uuid4().hex)
        attempt.mkdir(mode=0o700)
        def save(name_, data):
            fd = os.open(attempt / name_, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
        save(name, raw)
        save('plan.json', (json.dumps(plan, ensure_ascii=False, indent=2) + '\n').encode())
        pending[name] = attempt / name
        result = run(['node', str(WRITER), str(binding_path), str(attempt / 'plan.json'), name,
                      str(attempt / 'evidence')], cwd=ROOT, capture_output=True)
        if result.returncode:
            raise RuntimeError('Native upload failed or uncertain; reconcile its retained journal and target')

    def cleanup_verified(name, raw):
        """Remove only this attempt's staged bytes after exact archive readback."""
        staged = pending.get(name)
        if staged is None:
            return  # A matching existing batch was reused; no new stage exists.
        if staged.is_symlink() or not staged.is_file() or staged.read_bytes() != raw:
            raise ValueError('Staged payload differs; preserve it for recovery')
        staged.unlink()
        del pending[name]

    put.cleanup_verified = cleanup_verified
    return put
