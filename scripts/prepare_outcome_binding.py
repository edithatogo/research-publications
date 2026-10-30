"""Bind OutcomeProjection to the exact paired-field SharePoint item.

Additive offline TMDL preparation; credentials stay in Power BI's existing source
connection. Native credentials, refresh and rendering require separate evidence.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import base64
import copy
import hashlib
import re
from pathlib import Path
from urllib.parse import urlsplit
from scripts.deploy_report_definition import parts, fingerprint, strict
from scripts.outcome_intake import ROOT, save


def expression(target):
    if set(target) != {'listUrl','itemId','journalField','projectionField'}:
        raise ValueError('Exact paired-field target required')
    url = target['listUrl']; parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.query or parsed.fragment
            or not re.fullmatch(r".*?/_api/web/lists\(guid'[0-9a-f-]{36}'\)", parsed.path)
            or '%' in parsed.path or not parsed.hostname or parsed.port):
        raise ValueError('Exact HTTPS SharePoint list URL required')
    if type(target['itemId']) is not int or target['itemId'] < 1:
        raise ValueError('Exact existing item required')
    fields = [target['journalField'],target['projectionField']]
    if len(set(fields)) != 2 or any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,31}', f) for f in fields):
        raise ValueError('Distinct exact field names required')
    def literal(value):
        # M escapes quotes and literal # before escape introducers.
        return '"'+value.replace('#', '#(#)').replace('"', '""')+'"'
    endpoint = url+'/items?$select=Id,'+target['projectionField']+'&$filter=Id%20eq%20'+str(target['itemId'])
    return '\n'.join([
        'expression OutcomeProjection =', '\tlet',
        '\t\tRows = OData.Feed('+literal(endpoint)+', null, [Implementation = "2.0", ODataVersion = 3, Concurrent = false]),',
        '\t\tRow = if Table.RowCount(Rows) = 1 then Rows{0} else error "Exact outcome item missing or ambiguous",',
        '\t\tPayload = Record.Field(Row, '+literal(target['projectionField'])+'),',
        '\t\tParsed = if Value.Is(Payload, type text) then Json.Document(Payload) else error "Outcome projection is not text",',
        '\t\tRequired = {"journal_sha256", "context", "OutcomeProject", "TranslationEvent", "OutcomeObservation", "EventProject", "ObservationProject", "OutcomeEvidenceDetail"},',
        '\t\tValidated = if Record.HasFields(Parsed, Required) then Payload else error "Incomplete outcome projection"',
        '\tin Validated', ''])


def prepare(model, target, *, expected_sha256):
    if fingerprint(model) != expected_sha256:
        raise ValueError('Complete exact model preimage required')
    original = parts(model)
    path = 'definition/expressions.tmdl'
    existing = original.get(path, b'').decode()
    if re.search(r"(?m)^expression (?:OutcomeProjection|'OutcomeProjection')\s*=", existing):
        raise ValueError('Existing outcome binding requires explicit reconciliation')
    addition = expression(target)
    candidate = copy.deepcopy(model)
    payload = base64.b64encode((existing+'\n'+addition).encode()).decode()
    part = next((p for p in candidate['definition']['parts'] if p['path'] == path), None)
    if part is None:
        candidate['definition']['parts'].append({'path':path,'payloadType':'InlineBase64','payload':payload})
    else:
        part['payload'] = payload
    return {'candidate':candidate,'recovery':model,'expression_sha256':hashlib.sha256((existing+'\n'+addition).encode()).hexdigest(),
            'native_ready':False,'source_target':target,'changed_paths':[path]}


def main(argv=None):
    import subprocess
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('model','target','expected-sha256','output'): parser.add_argument('--'+name,required=True)
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    if not output.is_relative_to(ROOT/'private/ops'): raise ValueError('Private output required')
    subprocess.run(['git','check-ignore','-q',str(output)],cwd=ROOT,check=True)
    packet = prepare(strict(Path(args.model).read_bytes()),strict(Path(args.target).read_bytes()),expected_sha256=args.expected_sha256)
    save(output,packet)
    print('Prepared source binding; native credentials and refresh unverified')


if __name__ == '__main__': main()
