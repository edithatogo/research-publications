"""Preserve the study archive reader while matching URL-escaped path segments.

No refresh or archive mutation. SPDX-License-Identifier: Apache-2.0
"""
import base64
import copy
from scripts.deploy_report_definition import fingerprint, parts

PATH='definition/tables/SourceRelationshipEvidence.tmdl'


def prepare(model, *, expected_sha256):
    if fingerprint(model)!=expected_sha256:raise ValueError('Exact model preimage required')
    original=parts(model);text=original[PATH].decode()
    start=text.index('ReadStudy=(URL as text) as binary =>')
    end=text.index('StudyEvidence=',start)
    old=text[start:end]
    changes={
        'Table.SelectRows(T,each [Name]=N)':
        'Table.SelectRows(T,each [Name]=N or Uri.EscapeDataString([Name])=N)',
        'Table.SelectRows(Folder,each [Name]=List.Last(Parts))':
        'Table.SelectRows(Folder,each [Name]=List.Last(Parts) or Uri.EscapeDataString([Name])=List.Last(Parts))',
    }
    new=old
    for before,after in changes.items():
        if old.count(before)!=1:raise ValueError('Study reader drift; reconcile exact lookup before editing')
        new=new.replace(before,after)
    # Keep site identity, exact folder/file cardinality and table/binary type gates.
    updated=text[:start]+new+text[end:]
    candidate=copy.deepcopy(model)
    for part in candidate['definition']['parts']:
        if part['path']==PATH:part['payload']=base64.b64encode(updated.encode()).decode()
    return {'candidate':candidate,'recovery':model,'changed_paths':[PATH],
            'runtime_verified':False,'required_source_evidence':'Retained archive URL uses escaped segments corresponding to actual folder names'}
