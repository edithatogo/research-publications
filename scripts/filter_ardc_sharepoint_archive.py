"""Filter specifically pinned SharePoint Activities batches using guarded CLI reads.

The source receipt and organisation reference are local inputs. This performs
read-only retrieval and writes a private local candidate projection; publication
of the projection is a separate operation.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit

try:
    from scripts.ardc_secondary_filter import filter_archived_batches
except ModuleNotFoundError:
    from ardc_secondary_filter import filter_archived_batches

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / 'scripts/m365-qualified.mjs'


def archive_target(binding):
    if not isinstance(binding, dict) or not isinstance(binding.get('ardcActivitiesArchiveTarget'), dict):
        raise ValueError('Pinned Activities archive target required')
    target = binding['ardcActivitiesArchiveTarget']
    site, folder = target.get('site'), target.get('folder')
    if not isinstance(site, str) or not isinstance(folder, str):
        raise ValueError('Invalid archive target')
    parsed = urlsplit(site)
    origin = f'{parsed.scheme}://{parsed.netloc}'
    if (parsed.scheme != 'https' or not re.fullmatch(r'[A-Za-z0-9-]+\.sharepoint\.com', parsed.netloc)
            or not re.fullmatch(r'/(personal|sites)/[A-Za-z0-9_-]+', parsed.path)
            or parsed.query or parsed.fragment or origin not in binding.get('resources', [])
            or not folder.startswith('/Documents/') or any(c in folder for c in "'?#%\\")
            or any(p in ('', '.', '..') for p in folder.split('/')[1:])):
        raise ValueError('Invalid or unpinned archive target')
    return site, folder


def read_filter(receipt, binding, aliases_raw, read_file):
    site, folder = archive_target(binding)
    return filter_archived_batches(receipt, lambda name: read_file(site, folder, name), aliases_raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--aliases', type=Path, default=ROOT / 'config/organisation-hierarchy.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for item in (args.binding, args.receipt, args.output):
        subprocess.run(['git', 'check-ignore', '-q', str(item.resolve())], cwd=ROOT, check=True)
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('New private projection required')
    receipt = json.loads(args.receipt.read_bytes())
    # Share the same qualified Toolkit lock and identity as the baseline lane.
    try:
        from scripts.run_ardc_capture_pipeline import verify_shared_binding
    except ModuleNotFoundError:
        from run_ardc_capture_pipeline import verify_shared_binding
    binding = verify_shared_binding(args.binding)
    # The temporary directory is owned by this invocation; the guard must create
    # each destination itself. No source file or prior checkpoint is removed.
    with tempfile.TemporaryDirectory(prefix='.ardc-filter-', dir=args.output.parent) as temp:
        def read_file(site, folder, name):
            destination = Path(temp) / name
            proc = subprocess.run(['node', str(GUARD), 'read', str(args.binding), 'spo', 'file', 'get',
                                   '--webUrl', site, '--url', folder + '/' + name, '--asFile', '--path', str(destination)],
                                  cwd=ROOT, capture_output=True, timeout=120)
            if proc.returncode or destination.is_symlink() or not destination.is_file():
                raise ValueError('Guarded archive read failed')
            return destination.read_bytes()
        result = read_filter(receipt, binding, args.aliases.read_bytes(), read_file)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        json.dump(result, out, ensure_ascii=False, indent=2)
        out.write('\n')
    print(json.dumps({'input_records': result['input_records'], 'candidates': len(result['candidates']),
                      'native_read_performed': True, 'source_complete_verified': False}))


if __name__ == '__main__':
    main()
