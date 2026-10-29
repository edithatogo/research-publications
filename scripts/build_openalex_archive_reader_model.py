"""Prepare the existing isolated model to consume committed OpenAlex history.

Local candidate only. Native archive acceptance, exact model lease/drift guard,
transactional four-table processing and native parity remain deployment gates.
"""
import argparse
import base64
import copy
import hashlib
import json
import os
import re
from pathlib import Path

from extend_openalex_native_bootstrap import validate
from prepare_openalex_retention import private_path, require_ignored

EXPRESSIONS = 'definition/expressions.tmdl'
CHUNKS = 'definition/tables/OpenAlexMetadataChunks.tmdl'
WORKS = 'definition/tables/OpenAlexWorks.tmdl'


def build(baseline_bytes, manifest_bytes, prepared, files, *, expected_baseline_sha256):
    if not isinstance(expected_baseline_sha256, str) or re.fullmatch(r'[0-9a-f]{64}', expected_baseline_sha256) is None:
        raise ValueError('An independently supplied baseline fingerprint is required')
    if hashlib.sha256(baseline_bytes).hexdigest() != expected_baseline_sha256:
        raise ValueError('Exact accepted nine-field native baseline required')
    baseline = json.loads(baseline_bytes)
    parts = baseline['definition']['parts']
    if baseline['definition']['format'] != 'TMDL' or len(parts) != 46 or len({p['path'] for p in parts}) != 46:
        raise ValueError('Accepted unique46-part TMDL baseline required')
    validate(prepared)
    manifest = json.loads(manifest_bytes)
    if (manifest.get('SchemaVersion') != 1 or manifest.get('Status') != 'committed' or
            manifest.get('Validation') != {'Keysets': True, 'Metadata': True, 'RefreshGeneration': True} or
            manifest.get('Preservation') != {'UnchangedSources': ['PubMed', 'DORA'], 'ChangedSources': ['OpenAlex']} or
            len(manifest.get('Sources', [])) != 1):
        raise ValueError('Exact OpenAlex commit contract required')
    source = manifest['Sources'][0]
    if (source.get('Source') != 'OpenAlex' or source.get('ChunkTable') != 'OpenAlexMetadataChunks' or
            source.get('KeyColumn') != 'OpenAlexWorkID' or
            source.get('ExpectedKeys') != sorted(prepared['expected_keys']) or
            source.get('ExpectedRecords') != len(prepared['expected_keys'])):
        raise ValueError('Commit source/work scope differs from accepted raw source')
    entries = manifest['Files']
    expected_names = [f"uncommitted-{manifest['BatchID']}-OpenAlexMetadataChunks-{i}.json" for i in range(source['PageCount'])]
    if [e['name'] for e in entries] != expected_names or set(files) != set(expected_names):
        raise ValueError('Complete exact archive page set required')
    rows = []
    for entry in entries:
        raw = files[entry['name']]
        if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('Archive page fingerprint mismatch')
        page = json.loads(raw)
        if len(page) != entry['rows'] or not page:
            raise ValueError('Archive page row count mismatch')
        rows.extend({k[1:-1]: v for k, v in r.items()} for r in page)
    if rows != sorted(prepared['chunks'], key=lambda r: (r['OpenAlexWorkID'], r['ChunkIndex'])):
        raise ValueError('Archive pages differ from complete accepted envelopes')
    texts = {p['path']: base64.b64decode(p['payload'], validate=True).decode() for p in parts}
    expression = texts[EXPRESSIONS]
    if ('(Files as table, SourceName as text) as table =>' not in expression or
            'expression RetainedArchiveFiles =' not in expression or
            'expression OpenAlexCommittedObservations =' in expression):
        raise ValueError('Exact existing source-scoped reader and archive binding required')
    encoded_manifest = base64.b64encode(manifest_bytes).decode()
    observations = '''let
    Expected=Json.Document(Binary.FromText("MANIFEST_BASE64",BinaryEncoding.Base64)),
    AnchorName="commit-"&Expected[BatchID]&".json",
    Matches=Table.SelectRows(RetainedArchiveFiles,each [Name]=AnchorName),
    Anchor=if Table.RowCount(Matches)=1 then Json.Document(Binary.Buffer(Matches{0}[Content]))
        else error "Missing or duplicate accepted OpenAlex anchor",
    Anchored=Anchor=Expected,
    History=if Anchored then Table.Buffer(fnReadCommittedHistory(RetainedArchiveFiles,"OpenAlex"))
        else error "OpenAlex committed anchor drift",
    Keys=History[SourceID],
    Complete=List.Count(Keys)>0 and List.Count(List.Distinct(Keys))=List.Count(Keys) and
        List.IsEmpty(List.Difference(Expected[Sources]{0}[ExpectedKeys],Keys))
in if Complete then History else error "OpenAlex committed history key loss"'''.replace('MANIFEST_BASE64', encoded_manifest)
    chunks = '''let
    ChunkType=type table [OpenAlexWorkID=text,ChunkIndex=Int64.Type,ChunkCount=Int64.Type,
        MetadataCharacters=Int64.Type,Encoding=text,MetadataChunk=text],
    Groups=List.Transform(Table.ToRecords(OpenAlexCommittedObservations),(R)=>let
        Hex=Text.Upper(Binary.ToText(Text.ToBinary(R[MetadataJSON],TextEncoding.Utf8),BinaryEncoding.Hex)),
        Length=Text.Length(Hex), Count=Number.RoundUp(Length/24000)
        in List.Transform(List.Numbers(0,Count),(I)=>[OpenAlexWorkID=R[SourceID],ChunkIndex=I,
            ChunkCount=Count,MetadataCharacters=Length,Encoding="UTF8-HEX",
            MetadataChunk=Text.Range(Hex,I*24000,List.Min({24000,Length-I*24000}))]))
in Table.FromRecords(List.Combine(Groups),ChunkType)'''
    for name, body in [('OpenAlexCommittedObservations', observations), ('OpenAlexCommittedMetadataChunks', chunks)]:
        expression += '\nexpression ' + name + ' =\n' + '\n'.join('\t\t' + line for line in body.splitlines()) + '\n'
    replacements = {
        CHUNKS: ('source = Table.FromRecords(OpenAlexBootstrapDocument[chunks])',
                 'source = OpenAlexCommittedMetadataChunks'),
        WORKS: ('source = fnProjectRetainedOpenAlexAligned(OpenAlexBootstrapObservations,pOpenAlexAlignedFieldLimits)',
                'source = fnProjectRetainedOpenAlexAligned(OpenAlexCommittedObservations,pOpenAlexAlignedFieldLimits)')}
    changed = {EXPRESSIONS: expression}
    for name, (old, new) in replacements.items():
        if texts[name].count(old) != 1:
            raise ValueError('Exact accepted OpenAlex partition source required')
        changed[name] = texts[name].replace(old, new)
    candidate = copy.deepcopy(baseline)
    for part in candidate['definition']['parts']:
        if part['path'] in changed:
            part['payload'] = base64.b64encode(changed[part['path']].encode()).decode()
    receipt = {'kind': 'openalex_committed_reader_candidate_v1', 'changed_parts': sorted(changed),
               'preserved_parts': 43, 'original_expression_prefix_exact': True,
               'original_columns_and_projectors_exact': True, 'new_tables': 0, 'new_connections': 0,
               'raw_byte_reconstruction_verified': len(prepared['expected_keys']),
               'anchor_manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
               'baseline_sha256': expected_baseline_sha256, 'native_archive_accepted': False,
               'native_written': False, 'deployment_gate': 'Actual archive commit/raw native readback acceptance, '
               'fresh model drift/lease, saved same-ID readback and transactional four-table processing/parity.'}
    return candidate, receipt, {'OpenAlexCommittedObservations': observations, 'OpenAlexCommittedMetadataChunks': chunks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-root', required=True, type=Path)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--baseline-pin', required=True, help='Private file containing the accepted baseline SHA256')
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--prepared', required=True)
    parser.add_argument('--pages-directory', required=True)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    root = args.private_root.resolve()
    if root.name != 'ops' or root.parent.name != 'private' or not root.is_dir():
        raise ValueError('Existing ignored private/ops directory required')
    baseline, pin, manifest, prepared, pages, output = [private_path(getattr(args, key), root) for key in
        ['baseline', 'baseline_pin', 'manifest', 'prepared', 'pages_directory', 'output_directory']]
    require_ignored(root, (baseline, pin, manifest, prepared, pages, output))
    pin_bytes = pin.read_bytes()
    expected_baseline_sha256 = pin_bytes.decode('ascii').strip()
    baseline_bytes = baseline.read_bytes()
    manifest_bytes = manifest.read_bytes()
    prepared_bytes = prepared.read_bytes()
    files = {}
    for entry in json.loads(manifest_bytes)['Files']:
        page = private_path(pages / entry['name'], root)
        if page.parent != pages:
            raise ValueError('Archive page must belong to the exact private page directory')
        require_ignored(root, (page,))
        files[entry['name']] = page.read_bytes()
    candidate, receipt, expressions = build(baseline_bytes, manifest_bytes, json.loads(prepared_bytes), files,
                                           expected_baseline_sha256=expected_baseline_sha256)
    if (baseline.read_bytes() != baseline_bytes or pin.read_bytes() != pin_bytes or
            manifest.read_bytes() != manifest_bytes or prepared.read_bytes() != prepared_bytes or
            any((pages / name).read_bytes() != raw for name, raw in files.items())):
        raise ValueError('Frozen source drift before output')
    output.mkdir(mode=0o700)
    values = {'candidate-native-private.json': json.dumps(candidate, separators=(',', ':')),
              'candidate-receipt-private.json': json.dumps(receipt, indent=2),
              **{name + '-private.m': value for name, value in expressions.items()}}
    for name, value in values.items():
        with os.fdopen(os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            stream.write(value)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
