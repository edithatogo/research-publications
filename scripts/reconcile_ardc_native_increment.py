"""Read and reconcile an existing ARDC incremental SharePoint archive.

Only the repository's pinned M365 read entry point is used. Temporary raw page
bytes are kept privately for interrupted-read recovery and removed after a
successful receipt. No SharePoint content, collector or schedule is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4
from urllib.parse import urlsplit

try:
    from scripts.ardc_activities_archive import extract_archive_page, reconcile_archive
    from scripts.ardc_native_archive_target import validate_target
except ModuleNotFoundError:
    from ardc_activities_archive import extract_archive_page, reconcile_archive
    from ardc_native_archive_target import validate_target


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_new(path: Path, raw: bytes) -> None:
    with path.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def verify_accepted_target(marker: bytes, folder_manifest: bytes, accepted_raw: bytes, receipt_raw: bytes) -> dict:
    """Bind native readback to a separately retained accepted manifest."""
    accepted = json.loads(receipt_raw)
    historical = json.loads(accepted_raw)
    if (not isinstance(accepted, dict) or not isinstance(historical, dict)
            or accepted.get('status') != 'PASS_COMPLETE_NATIVE_PUBLIC_ARDC_REGISTRY_BASELINE'
            or _sha(accepted_raw) != accepted.get('manifest_sha256')):
        raise ValueError('Accepted source manifest does not match acceptance receipt')
    return validate_target(marker, folder_manifest, expected_sha256=accepted['manifest_sha256'],
                           expected_folder=historical.get('archive_folder'))


def verify_with_checkpoint(manifest_raw: bytes, read_remote, checkpoint: Path) -> dict:
    """Reuse only hash-verified pages belonging to this exact manifest."""
    manifest_hash = _sha(manifest_raw)
    checkpoint.mkdir(mode=0o700, parents=False, exist_ok=True)
    if checkpoint.is_symlink() or not checkpoint.is_dir():
        raise ValueError('Invalid checkpoint directory')
    anchor = checkpoint / 'manifest-sha256.txt'
    if anchor.exists():
        if anchor.is_symlink() or anchor.read_text() != manifest_hash:
            raise ValueError('Checkpoint belongs to a different manifest')
    else:
        _write_new(anchor, manifest_hash.encode())

    def read(name: str) -> bytes:
        if not name.startswith('page-') or not name.endswith('.xml') or not name[5:-4].isdigit():
            raise ValueError('Unexpected page name')
        page, digest = checkpoint / name, checkpoint / (name + '.sha256')
        if page.exists() or digest.exists():
            if not page.is_file() or page.is_symlink() or not digest.is_file() or digest.is_symlink():
                raise ValueError('Incomplete checkpoint page; inspect before recovery')
            raw = page.read_bytes()
            if digest.read_text() != _sha(raw):
                raise ValueError('Checkpoint page hash mismatch')
            return raw
        raw = read_remote(name)
        extract_archive_page(raw)
        _write_new(page, raw)
        _write_new(digest, _sha(raw).encode())
        return raw

    result = reconcile_archive(manifest_raw, manifest_hash, read, allow_incremental=True)
    result['temporary_checkpoint_used'] = True
    result['current_sharepoint_page_immutability_verified'] = False
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--marker', type=Path, required=True)
    parser.add_argument('--folder-manifest', type=Path, required=True)
    parser.add_argument('--accepted-manifest', type=Path, required=True)
    parser.add_argument('--acceptance', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for path in (args.binding, args.marker, args.folder_manifest, args.accepted_manifest,
                 args.acceptance, args.checkpoint, args.output):
        subprocess.run(['git', 'check-ignore', '-q', str(path.resolve())], check=True)
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Existing output must be preserved')
    marker = args.marker.read_bytes()
    accepted_raw = args.accepted_manifest.read_bytes()
    verify_accepted_target(marker, args.folder_manifest.read_bytes(), accepted_raw, args.acceptance.read_bytes())
    manifest = json.loads(marker)
    binding_raw = args.binding.read_bytes()
    binding = json.loads(binding_raw)
    sites = set()
    for prefix in binding.get('readUrlPrefixes', []):
        u = urlsplit(prefix)
        parts = u.path.split('/')
        if len(parts) > 2 and parts[1] == 'personal':
            sites.add(u.scheme + '://' + u.netloc + '/' + parts[1] + '/' + parts[2])
    folder = manifest.get('archive_folder', '')
    if (len(sites) != 1 or not isinstance(folder, str) or not folder.startswith('/Documents/')
            or any(c in folder for c in "'?#%\\") or '..' in folder.split('/')):
        raise ValueError('Exact existing archive target is not qualified')
    site = sites.pop()
    target = urlsplit(site).path + folder
    args.checkpoint.mkdir(mode=0o700, parents=False, exist_ok=True)
    if args.checkpoint.is_symlink():
        raise ValueError('Checkpoint must not be a symlink')
    new_reads = 0

    def read_remote(name: str) -> bytes:
        nonlocal new_reads
        for attempt in (0, 1):
            nonce = uuid4().hex
            wire = args.checkpoint / f'{name}.wire-{nonce}'
            cmd = ['node', 'scripts/m365-qualified.mjs', 'read', str(args.binding),
                   'spo', 'file', 'get', '--webUrl', site, '--url', target + '/' + name,
                   '--asFile', '--path', str(wire)]
            outcome = subprocess.run(cmd, capture_output=True, text=True)
            if outcome.returncode == 0:
                if wire.is_symlink() or not wire.is_file():
                    raise ValueError('Missing native readback')
                raw = wire.read_bytes()
                wire.unlink()
                new_reads += 1
                if new_reads % 20 == 0:
                    print(f'New native page reads: {new_reads}', flush=True)
                return raw
            error = args.checkpoint / f'{name}.error-{nonce}.txt'
            _write_new(error, outcome.stderr.encode())
            if attempt == 0 and 'ECONNRESET' in outcome.stderr:
                print(f'Read-only connection reset on {name}; one bounded retry', flush=True)
                continue
            raise ValueError('Native read stopped; inspect private error receipt')
        raise ValueError('Native read failed')

    lock = args.checkpoint / '.reader-lock'
    lock.mkdir(mode=0o700)  # Never remove or supersede another reader's lock.
    try:
        binding_anchor = args.checkpoint / 'binding-sha256.txt'
        if binding_anchor.exists():
            if binding_anchor.is_symlink() or binding_anchor.read_text() != _sha(binding_raw):
                raise ValueError('Checkpoint belongs to a different private binding')
        else:
            _write_new(binding_anchor, _sha(binding_raw).encode())
        result = verify_with_checkpoint(marker, read_remote, args.checkpoint)
        _write_new(args.output, (json.dumps(result, indent=2) + '\n').encode())
        # Only files created and hash-checked by this operation are removed.
        for page in result['pages']:
            raw_path = args.checkpoint / page['file']
            digest_path = args.checkpoint / (page['file'] + '.sha256')
            if raw_path.is_symlink() or digest_path.is_symlink() or _sha(raw_path.read_bytes()) != page['sha256']:
                raise ValueError('Checkpoint cleanup refused after drift')
            raw_path.unlink()
            digest_path.unlink()
    finally:
        lock.rmdir()
    print(f"Reconciled {result['records']} records across {len(result['pages'])} pages", flush=True)


if __name__ == '__main__':
    main()
