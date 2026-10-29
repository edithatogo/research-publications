"""Guarded, exact-target SharePoint probe and byte reads for Activities batches."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlencode, urlsplit

try:
    from scripts.filter_ardc_sharepoint_archive import archive_target
except ModuleNotFoundError:
    from filter_ardc_sharepoint_archive import archive_target

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / 'scripts/m365-qualified.mjs'


def make_archive_io(binding_path, scratch, *, run=subprocess.run):
    """Return (probe, read) callbacks; only an empty exact query means absence.

    Every read uses the retained guarded CLI. A native error, unexpected shape,
    mismatch or duplicate must stop capture rather than mean an absent file.
    This factory and its tests alone do not qualify a live target or permission.
    """
    binding_path, scratch = Path(binding_path), Path(scratch)
    for item in (binding_path, scratch):
        subprocess.run(['git', 'check-ignore', '-q', str(item.resolve())], cwd=ROOT, check=True)
    if scratch.is_symlink() or not scratch.is_dir():
        raise ValueError('Private scratch directory required')
    site, folder = archive_target(json.loads(binding_path.read_bytes()))
    root = site + "/_api/web/GetFolderByServerRelativePath(DecodedUrl='" + urlsplit(site).path + folder + "')"
    folder_verified = False

    def checked_name(name):
        if not isinstance(name, str) or re.fullmatch(r'activities-batch-[0-9]{9}\.json', name) is None:
            raise ValueError('Invalid archive batch name')
        return name

    def invoke(arguments, output):
        result = run(['node', str(GUARD), 'read', str(binding_path), *arguments],
                     cwd=ROOT, capture_output=True, timeout=120)
        if result.returncode or output.is_symlink() or not output.is_file():
            raise ValueError('Guarded archive read failed')
        return output.read_bytes()

    def read(name):
        checked_name(name)
        with tempfile.TemporaryDirectory(prefix='.ardc-batch-read-', dir=scratch) as tmp:
            output = Path(tmp) / name
            return invoke(['spo', 'file', 'get', '--webUrl', site, '--url', folder + '/' + name,
                           '--asFile', '--path', str(output)], output)

    def probe(name):
        nonlocal folder_verified
        checked_name(name)
        query = urlencode({'$select': 'Name', '$filter': "Name eq '" + name + "'"})
        with tempfile.TemporaryDirectory(prefix='.ardc-batch-probe-', dir=scratch) as tmp:
            output = Path(tmp) / 'inventory.json'
            raw = invoke(['request', '--url', root + '/Files?' + query, '--method', 'get',
                          '--filePath', str(output), '--output', 'json'], output)
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise ValueError('Invalid archive inventory') from None
        if not isinstance(data, dict):
            raise ValueError('Invalid archive inventory')
        if '@odata.nextLink' in data or (isinstance(data.get('d'), dict) and '__next' in data['d']):
            raise ValueError('Incomplete archive inventory')
        rows = data.get('value')
        if rows is None and isinstance(data.get('d'), dict):
            rows = data['d'].get('results')
        if not isinstance(rows, list) or len(rows) > 1:
            raise ValueError('Ambiguous archive inventory')
        if not rows:
            # SharePoint can return an empty Files collection for a missing
            # folder. Verify the folder once before interpreting that as absence.
            if not folder_verified:
                with tempfile.TemporaryDirectory(prefix='.ardc-folder-probe-', dir=scratch) as tmp:
                    output = Path(tmp) / 'folder.json'
                    raw = invoke(['request', '--url', root + '?$select=Exists,ServerRelativeUrl',
                                  '--method', 'get', '--filePath', str(output), '--output', 'json'], output)
                try:
                    metadata = json.loads(raw)
                    if isinstance(metadata, dict) and 'd' in metadata:
                        metadata = metadata['d']
                except (ValueError, UnicodeDecodeError):
                    raise ValueError('Invalid archive folder metadata') from None
                if (not isinstance(metadata, dict) or metadata.get('Exists') is not True
                        or metadata.get('ServerRelativeUrl') != urlsplit(site).path + folder):
                    raise ValueError('Archive folder existence or target not verified')
                folder_verified = True
            return None
        if not isinstance(rows[0], dict) or rows[0].get('Name') != name:
            raise ValueError('Archive inventory target mismatch')
        return read(name)
    return probe, read
