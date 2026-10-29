"""Run the ARDC Activities batch capture and local secondary projection.

Uses an independently reconciled baseline/increment lineage and an exact
private native binding. The caller must establish archive ownership, target
and permissions before invocation. No flow or schedule is activated.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

try:
    from scripts.ardc_activities_archive import activities_fetcher, decode_page
    from scripts.ardc_activity_batch import lookup_batch
    from scripts.ardc_capture_pipeline import capture_and_filter
    from scripts.ardc_generation_lineage import overlay_verified_lineage
    from scripts.ardc_native_batch_reader import make_archive_io
    from scripts.ardc_native_batch_writer import make_writer
    from scripts.filter_ardc_sharepoint_archive import archive_target
except ModuleNotFoundError:
    from ardc_activities_archive import activities_fetcher, decode_page
    from ardc_activity_batch import lookup_batch
    from ardc_capture_pipeline import capture_and_filter
    from ardc_generation_lineage import overlay_verified_lineage
    from ardc_native_batch_reader import make_archive_io
    from ardc_native_batch_writer import make_writer
    from filter_ardc_sharepoint_archive import archive_target

ROOT = Path(__file__).resolve().parents[1]
SHARED_BINDING = ROOT / 'private/ops/2026-10-26-toolkit-auth-guard/binding.json'


def verify_shared_binding(binding: Path) -> dict:
    """Keep a derived archive pin on the existing account and lock path."""
    shared = SHARED_BINDING.resolve(strict=True)
    selected = binding.resolve(strict=True)
    if selected.parent != shared.parent or binding.is_symlink():
        raise ValueError('Archive binding must share the qualified Toolkit lock directory')
    current, base = json.loads(selected.read_bytes()), json.loads(shared.read_bytes())
    fields = ('sdkRoot', 'sdkVersion', 'connectionName', 'appId', 'tenantId', 'username',
              'resources', 'objectId')
    if any(current.get(field) != base.get(field) for field in fields):
        raise ValueError('Archive binding changes the qualified Toolkit identity or read scope')
    if current.get('readUrlPrefixes') != base.get('readUrlPrefixes'):
        site, folder = archive_target(current)
        exact = site + "/_api/web/GetFolderByServerRelativePath(DecodedUrl='" + urlsplit(site).path + folder + "')"
        original, selected_prefixes = base.get('readUrlPrefixes'), current.get('readUrlPrefixes')
        if (not isinstance(original, list) or not isinstance(selected_prefixes, list)
                or any(not isinstance(p, str) for p in original + selected_prefixes)
                or set(selected_prefixes) != set(original) | {exact}):
            raise ValueError('Archive binding changes the qualified Toolkit read scope')
    return current


def run_capture(*, baseline, incremental, baseline_manifest, incremental_manifest,
                credential, binding, workdir, aliases):
    """Execute the explicitly targeted pipeline, saving private result files."""
    private = (baseline, incremental, baseline_manifest, incremental_manifest, credential, binding, workdir)
    for path in private:
        subprocess.run(['git', 'check-ignore', '-q', str(path.resolve())], cwd=ROOT, check=True)
    if workdir.exists() or workdir.is_symlink():
        raise ValueError('New private work directory required')
    pin = verify_shared_binding(binding)
    if Path(pin.get('ardcActivitiesCredentialFile', '')).resolve() != credential.resolve():
        raise ValueError('Credential differs from private binding')
    key = credential.read_bytes().strip()
    if not key:
        raise ValueError('Empty credential')
    overlay = overlay_verified_lineage(json.loads(baseline.read_bytes()), json.loads(incremental.read_bytes()),
                                       baseline_manifest.read_bytes(), incremental_manifest.read_bytes())
    alias_bytes = aliases.read_bytes()
    workdir.mkdir(mode=0o700)
    (workdir / 'partial-projections').mkdir(mode=0o700)
    probe, read = make_archive_io(binding, workdir)
    put = make_writer(overlay, key, binding, workdir)
    total_fetch = activities_fetcher(key)
    def read_total():
        return decode_page(total_fetch(0, 1), 0, 1)[0]
    def save(name, value):
        fd = os.open(workdir / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=False, indent=2)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
    result = capture_and_filter(overlay, key, alias_bytes, read_total=read_total,
                                fetch_batch=lambda batch: lookup_batch(batch, key), probe=probe,
                                put=put, read=read,
                                save_receipt=lambda value: save('capture-receipt.json', value),
                                save_projection=lambda value: save('candidate-projection.json', value),
                                save_partial=lambda name, value: save('partial-projections/' + name, value),
                                cleanup_verified=getattr(put, 'cleanup_verified', None))
    return {'records': result['receipt']['records'], 'candidates': len(result['projection']['candidates']),
            'source_complete_verified': False, 'native_completion_marker': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('baseline', 'incremental', 'baseline-manifest', 'incremental-manifest',
                  'credential', 'binding', 'workdir'):
        parser.add_argument('--' + field, required=True, type=Path)
    parser.add_argument('--aliases', type=Path, default=ROOT / 'config/organisation-hierarchy.json')
    args = parser.parse_args()
    print(json.dumps(run_capture(**vars(args))))


if __name__ == '__main__':
    main()
