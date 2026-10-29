# SPDX-License-Identifier: Apache-2.0
"""Connect a verified G06 delivery to the existing RIMS consumer contract."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prepare_funding_relationship_context import prepare_consumer, digest


def consumer_from_delivery(receipt, baseline=None):
    """Connect verified delivery rows to the existing RIMS preparation contract."""
    if (receipt.get('kind') not in {'g06-incremental-delivered-v1', 'g06-native-delivery-verified-v1'}
            or receipt.get('native_verified') is not True
            or receipt.get('native', {}).get('native_verified') is not True):
        raise ValueError('Completed native-verified incremental delivery required')
    sources = receipt.get('state', {}).get('sources')
    rows = receipt['native'].get('current_rows')
    if not isinstance(sources, dict) or not sources or not isinstance(rows, list):
        raise ValueError('Source provenance and complete native rows required')
    contexts, seen, provenance = [], set(), []
    for source, entry in sources.items():
        packet = entry.get('packet', {})
        if (packet.get('kind') != 'retained_arc_publication_relationship_candidates_v1'
                or not isinstance(packet.get('context'), list)
                or not isinstance(entry.get('sha256'), str) or len(entry['sha256']) != 64):
            raise ValueError('Accepted ARC source context required')
        for context in packet['context']:
            context_hash = digest(context)
            provenance.append({'source': source, 'packet_sha256': entry['sha256'],
                               'relationship_key': context['RelationshipKey'],
                               'context_sha256': context_hash})
            if context_hash not in seen:
                seen.add(context_hash); contexts.append(context)
    snapshot = {'complete': True, 'list': {'ItemCount': len(rows)}, 'items': rows,
                'observedAtUTC': receipt['native'].get('at')}
    result = prepare_consumer(snapshot, {'context': contexts})
    if len(result['rows']) != len(rows):
        raise ValueError('Consumer changed the native relationship denominator')
    if baseline is not None and (baseline.get('kind') != result['kind']
                                 or not isinstance(baseline.get('identity_material'), list)):
        raise ValueError('Accepted consumer identity baseline required')
    order = lambda material: sorted(material, key=lambda r: (r['RelationshipKey'], digest(r)))
    changed = (order(result['identity_material']) != order(baseline['identity_material'])
               if baseline is not None else None)
    result.update(processing_receipt_sha256=digest(receipt), source_provenance=provenance,
                  processing_coverage=receipt.get('coverage'), native_model_modified=False,
                  identity_update_required=changed, live_refresh_verified=False,
                  source_snapshot_verified=True,
                  identity_baseline_sha256=digest(baseline) if baseline is not None else None,
                  integration_requirement='Read current native review state through the existing bridge; apply changed identity material only with qualified model isolation/rollback and targeted refresh/cardinality verification')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--processing-receipt', type=Path, required=True)
    parser.add_argument('--baseline-consumer', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = consumer_from_delivery(json.loads(args.processing_receipt.read_text()),
                json.loads(args.baseline_consumer.read_text()) if args.baseline_consumer else None)
    if not args.output.resolve().is_relative_to((Path.cwd() / 'private/ops').resolve()):
        raise ValueError('Private consumer output required')
    subprocess.run(['git', 'check-ignore', '-q', str(args.output.resolve())], check=True)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        json.dump(result, out, ensure_ascii=False, indent=2); out.write('\n')
    print(json.dumps({'coverage': result['coverage'],
                      'identity_update_required': result['identity_update_required'],
                      'native_model_modified': False}))


if __name__ == '__main__':
    main()
