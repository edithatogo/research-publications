"""Check baseline/increment lineage before a tentative ARDC activity overlay."""
from __future__ import annotations

import hashlib
import json

try:
    from scripts.ardc_activities_archive import overlay_incremental
except ModuleNotFoundError:
    from ardc_activities_archive import overlay_incremental


def overlay_verified_lineage(baseline_result: dict, incremental_result: dict,
                             baseline_manifest: bytes, incremental_manifest: bytes) -> dict:
    """Verify both manifest hashes and shared baseline lineage before overlay.

    This validates retained-generation identity, not provider freshness,
    complete source coverage or per-record version ordering.
    """
    generations = []
    for result, raw in ((baseline_result, baseline_manifest), (incremental_result, incremental_manifest)):
        if not isinstance(result, dict) or not isinstance(raw, bytes):
            raise ValueError('Reconciled results and manifest bytes required')
        digest = hashlib.sha256(raw).hexdigest()
        if result.get('manifest_sha256') != digest or result.get('stored_generation_reconciled') is not True:
            raise ValueError('Manifest hash or generation verification mismatch')
        try:
            manifest = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise ValueError('Invalid generation manifest') from None
        if not isinstance(manifest, dict) or manifest.get('source') != 'ardc' or manifest.get('complete') is not True:
            raise ValueError('Invalid ARDC generation')
        if manifest.get('full_reconciliation') is not result.get('full_reconciliation') or manifest.get('until') != result.get('until'):
            raise ValueError('Manifest and reconciled generation differ')
        generations.append(manifest)
    base, incremental = generations
    if base.get('full_reconciliation') is not True or incremental.get('full_reconciliation') is not False:
        raise ValueError('Expected baseline followed by incremental generation')
    scope = base.get('scope_sha256')
    if not isinstance(scope, str) or len(scope) != 64 or any(c not in '0123456789abcdef' for c in scope):
        raise ValueError('Missing baseline scope hash')
    if incremental.get('scope_sha256') != scope:
        raise ValueError('Source scopes differ')
    if not base.get('until') or base.get('baseline_completed_at') != base['until'] or incremental.get('baseline_completed_at') != base['until']:
        raise ValueError('Incremental baseline lineage differs')
    result = overlay_incremental(baseline_result, incremental_result)
    result['generation_lineage_verified'] = True
    result['scope_sha256'] = scope
    return result
