"""Export pinned candidate relationship evidence locally, without native effects.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prepare_source_relationship_model import (
    COLUMNS, ROOT, document_hash, fingerprint, prepare as prepare_model, project_rows,
    strict_json_loads,
)
from scripts.plan_publication_stub_restore import private_output


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def csv_cell(value):
    """A literal apostrophe precedes every JSON scalar, including null/empty text.

    The apostrophe prevents formula interpretation; JSON preserves text and types.
    Decoding removes exactly one apostrophe and parses the remaining JSON scalar.
    """
    return "'" + json.dumps(value, ensure_ascii=False, allow_nan=False)


def decode_csv(raw):
    reader = csv.reader(io.StringIO(raw.decode('utf-8'), newline=''))
    if next(reader, None) != COLUMNS:
        raise ValueError('CSV field inventory drift')
    rows = []
    for cells in reader:
        if len(cells) != len(COLUMNS) or any(not c.startswith("'") for c in cells):
            raise ValueError('CSV display encoding drift')
        values = [strict_json_loads(c[1:]) for c in cells]
        if any(isinstance(v, (dict, list)) for v in values):
            raise ValueError('CSV scalar required')
        rows.append(dict(zip(COLUMNS, values)))
    return rows


def build(*, model_inputs, model_packet, model_packet_sha256, rows_sha256,
          publications_sha256, typed_rows_sha256):
    """Rebuild through the frozen preparer; supplied capability claims stay claims."""
    if fingerprint(model_inputs['rows']) != rows_sha256:
        raise ValueError('Independent producer rows pin mismatch')
    if fingerprint(model_inputs['publications']) != publications_sha256:
        raise ValueError('Independent canonical snapshot pin mismatch')
    if fingerprint(model_packet) != model_packet_sha256:
        raise ValueError('Independent model packet pin mismatch')
    expected = prepare_model(**model_inputs)
    if expected['status'] != 'prepared' or json_bytes(expected) != json_bytes(model_packet):
        raise ValueError('Model packet differs from exact frozen preparation')
    rows = project_rows(model_inputs['rows'], model_inputs['publications'],
                        model_inputs['producer_context'])
    if fingerprint(rows) != typed_rows_sha256 or model_packet['typedRowsSHA256'] != typed_rows_sha256:
        raise ValueError('Independent typed-row pin mismatch')
    # Keep input order and every occurrence/revision; never collapse to canonical grain.
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\r\n')
    writer.writerow(COLUMNS)
    writer.writerows([csv_cell(row[c]) for c in COLUMNS] for row in rows)
    files = {'evidence.json': json_bytes(rows), 'evidence.csv': stream.getvalue().encode('utf-8')}
    if fingerprint(strict_json_loads(files['evidence.json'])) != typed_rows_sha256 or fingerprint(decode_csv(files['evidence.csv'])) != typed_rows_sha256:
        raise ValueError('Export serialization parity failed')
    manifest = dict(format='rims-source-relationship-candidate-export-v1',
        status='candidate_only', rowCount=len(rows), fields=COLUMNS,
        assertionRevisionKeys=[r['AssertionRevisionKey'] for r in rows],
        evidenceKeys=[r['EvidenceKey'] for r in rows],
        canonicalKeys=sorted({r['CanonicalKey'] for r in rows if r['CanonicalKey']}),
        rowsSHA256=rows_sha256, publicationsSHA256=publications_sha256,
        typedRowsSHA256=typed_rows_sha256, modelPacketSHA256=model_packet_sha256,
        inputModelSHA256=model_packet['inputModelSHA256'],
        outputModelSHA256=document_hash(model_packet['modelDefinition']),
        producerContextSHA256=model_packet['producerContextSHA256'],
        csvEncoding='apostrophe-prefixed JSON scalar in every cell; remove one apostrophe then JSON-decode',
        files={name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
        nativeAcceptance=False, nativeSaveSubmitted=False, mutationAuthorized=False,
        canonicalAdmission=False, identityQualified=False,
        nativeDependencies=['exact producer/model/report binding', 'M/DAX engine and filter parity',
            'native import and inverse', 'rendering/access/export parity',
            'correction/withdrawal persistence and recovery'])
    files['manifest.json'] = json_bytes(manifest)
    return files


def prepare(output, **inputs):
    """Create a private bundle exclusively; manifest is the final commit marker.

    Failures leave incomplete owned output for inspection; never overwrite or clean.
    Consumers must require a complete manifest and matching file hashes.
    """
    files = build(**inputs)
    output = Path(output)
    private_output(output, [], root=ROOT)
    if any(p.is_symlink() for p in [output, *output.parents]):
        raise ValueError('Nonsymlink output path required')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()  # Atomic exclusive reservation, including empty exports.
    for name, raw in files.items():
        with (output / name).open('xb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if (output / name).read_bytes() != raw:
            raise ValueError('Export file readback drift')
    if set(p.name for p in output.iterdir()) != set(files):
        raise ValueError('Unexpected bundle member')
    # Reconcile semantic JSON/CSV readback as well as bytes before returning success.
    expected = inputs['typed_rows_sha256']
    if fingerprint(strict_json_loads((output / 'evidence.json').read_bytes())) != expected or fingerprint(decode_csv((output / 'evidence.csv').read_bytes())) != expected:
        raise ValueError('Export typed readback drift')
    return strict_json_loads((output / 'manifest.json').read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--input-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.input_sha256:
        raise ValueError('Input file bytes differ from independent pin')
    # Snapshot the once-read bytes; there is no second read of mutable source files.
    inputs = strict_json_loads(raw)
    private_output(args.output, [args.input], root=ROOT)
    result = prepare(args.output, **inputs)
    print(json.dumps(dict(status=result['status'], rowCount=result['rowCount'], nativeAcceptance=False)))


if __name__ == '__main__':
    main()
