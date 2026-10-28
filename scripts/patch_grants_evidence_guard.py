"""Prepare a reviewed importer evidence-identity correction without service I/O."""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy
from scripts.grants_order_guard import find


def patch(definition):
    """Match source evidence across round/key changes when SourceID is present.

    Round-only identities retain their round discriminator because no source ID
    exists to distinguish multiple opportunities sharing one source document.
    """
    result = copy.deepcopy(definition)
    lookup = find(result['actions'], 'SharePoint_Get_source_identity')
    query = lookup['inputs']['parameters']['$filter']
    old = "if(empty(item()?['RoundID']), '(RoundID eq null or RoundID eq '''')', concat('RoundID eq ''', replace(string(item()?['RoundID']), '''', ''''''), ''''))"
    new = "if(empty(item()?['SourceID']), " + old + ", 'SourceID ne null')"
    if query.count(old) != 1 or new in query:
        raise ValueError('Exact existing evidence-identity predicate required')
    lookup['inputs']['parameters']['$filter'] = query.replace(old, new)
    guard = find(result['actions'], 'Condition_OpportunityKey_Present')['expression']['and']
    if len(guard) != 4:
        raise ValueError('Exact existing source-identity guard required')
    # Empty optional SourceID/RoundID remain valid; padded text never is.
    for field in ('OpportunityKey', 'Source', 'SourceID', 'RoundID', 'EvidenceHash'):
        raw = f"@string(coalesce(item()?['{field}'], ''))"
        trimmed = f"@trim(string(coalesce(item()?['{field}'], '')))"
        guard.append({'equals': [raw, trimmed]})
    return result
