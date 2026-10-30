"""Local study format routing using retained, independently pinned ZIP bytes.

No network or native writes. SPDX-License-Identifier: Apache-2.0
"""
import base64
import copy
import hashlib
import io
import json
import re
import zipfile
import zlib
from scripts.deploy_report_definition import fingerprint, parts, strict
from scripts.prepare_study_archive_path_fix import PATH


def packed(raw):
    c = zlib.compressobj(wbits=-15)
    return base64.b64encode(c.compress(raw) + c.flush()).decode()


def qualify_zip(raw, expected_sha256):
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Archive digest mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or sum(i.file_size for i in z.infolist()) > 100_000_000:
            raise ValueError('Duplicate or excessive archive members')
        if z.testzip() is not None:
            raise ValueError('Corrupt archive')
        m = strict(z.read('source-manifest.json'))
        if m['source'] != 'ClinicalTrials.gov' or m['count'] != len(m['observations']):
            raise ValueError('Wrong archive source/count')
        files = {f['name']: f for f in m['files']}
        if len(files) != len(m['files']) or set(files) != set(names)-{'source-manifest.json'}:
            raise ValueError('Incomplete/duplicate manifest')
        for name, f in files.items():
            b = z.read(name)
            if len(b) != f['bytes'] or hashlib.sha256(b).hexdigest() != f['sha256']:
                raise ValueError('Member digest/length mismatch')
        members = {}
        for o in m['observations']:
            n = o['id']; b = z.read(n + '.json'); body = strict(b)
            if (not re.fullmatch(r'NCT[0-9]{8}', n) or n in members or o['status'] != 200
                    or o['source_url'] != 'https://clinicaltrials.gov/api/v2/studies/' + n
                    or o['sha256'] != hashlib.sha256(b).hexdigest() or o['bytes'] != len(b)
                    or body['protocolSection']['identificationModule']['nctId'] != n):
                raise ValueError('Study identity/provenance mismatch')
            members[n] = {'payload': packed(b), 'sha256': o['sha256']}
        return members


def prepare(model, *, expected_sha256, archive_url, archive_bytes, archive_sha256):
    if fingerprint(model) != expected_sha256:
        raise ValueError('Exact model preimage required')
    if not archive_url.startswith('https://') or not archive_url.endswith('.zip'):
        raise ValueError('Exact ZIP archive URL required')
    members = qualify_zip(archive_bytes, archive_sha256)
    # Reuse the saved model's independently pinned-byte comparison pattern.
    contract = json.dumps({'url': archive_url, 'archive': packed(archive_bytes),
                           'members': members}, separators=(',', ':')).encode()
    literal = packed(contract)
    helper = '''StudyJSONContract=Json.Document(Binary.Decompress(Binary.FromText("PAYLOAD",BinaryEncoding.Base64),Compression.Deflate)),
StudyJSONArchive=let Expected=Binary.Buffer(Binary.Decompress(Binary.FromText(StudyJSONContract[archive],BinaryEncoding.Base64),Compression.Deflate)),Actual=Binary.Buffer(ReadStudy(StudyJSONContract[url])) in if Binary.ToText(Actual,BinaryEncoding.Base64)=Binary.ToText(Expected,BinaryEncoding.Base64) then true else error "Study ZIP differs from pinned archive",
StudyJSONRows=Table.SelectRows(StudyRows,each if Text.StartsWith([SourceKey],"clinicaltrials.gov:") then true else if Text.StartsWith([SourceKey],"anzctr:") then false else error "Unsupported study source namespace"),
StudyJSON=(R as record) as record =>
    if R[SourceKey]<>"clinicaltrials.gov:"&R[NCTId] then error "Study source identity drift"
    else if R[ArchiveFileURL]=StudyJSONContract[url] then let
        Member=Record.FieldOrDefault(StudyJSONContract[members],R[NCTId],null),
        Body=if StudyJSONArchive and Member<>null and Member[sha256]=R[SourcePayloadSHA256] then Json.Document(Binary.Decompress(Binary.FromText(Member[payload],BinaryEncoding.Base64),Compression.Deflate)) else error "Study ZIP member identity or provenance drift"
        in [requested_id=R[NCTId],response=[statusCode=200,body=Body]]
    else if Text.EndsWith(Text.Lower(R[ArchiveFileURL]),".json") then Json.Document(ReadStudy(R[ArchiveFileURL]))
    else error "Unqualified study archive format",
'''.replace('PAYLOAD', literal)
    text = parts(model)[PATH].decode()
    old = 'StudyEvidence=List.Combine(List.Transform(Table.ToRecords(StudyRows),(R)=>let SE=Json.Document(ReadStudy(R[ArchiveFileURL]))'
    if text.count(old) != 1 or 'StudyJSONContract=' in text:
        raise ValueError('Study parser drift')
    pos = text.index(old); prefix = text[text.rfind('\n', 0, pos)+1:pos]
    if prefix.strip():
        raise ValueError('Standalone M expression required')
    replacement = helper.replace('\n', '\n'+prefix) + 'StudyEvidence=List.Combine(List.Transform(Table.ToRecords(StudyJSONRows),(R)=>let SE=StudyJSON(R)'
    changed = text.replace(old, replacement, 1)
    candidate = copy.deepcopy(model)
    for p in candidate['definition']['parts']:
        if p['path'] == PATH:
            p['payload'] = base64.b64encode(changed.encode()).decode()
    return {'candidate': candidate, 'recovery': model, 'changed_paths': [PATH],
            'zip_members': len(members), 'runtime_verified': False,
            'excluded_relationship_source': 'ANZCTR: retained in Study register, not a ClinicalTrials.gov reference payload'}
