# SPDX-License-Identifier: Apache-2.0
"""Prepare an offline trigger-only packet for a supplied stopped writer capture.

No capture, authentication, activation, invocation, mutation or retry route is
included. Supplied provenance is not independently authenticated native evidence.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
from uuid import UUID

if __package__:
    from scripts.verify_publication_protected_fields import (VerificationError, identifier,
        fresh, complete, canonical, digest, instant, private_path, read_json, exclusive_json, version_key)
else:
    from verify_publication_protected_fields import (VerificationError, identifier,
        fresh, complete, canonical, digest, instant, private_path, read_json, exclusive_json, version_key)

ROOT=Path(__file__).resolve().parents[1]
TERMINAL_STATUSES={'Succeeded','Failed','Cancelled','Canceled','TimedOut','Skipped'}


def fingerprint(value):return digest(value)


def _guid(value,label):
    identifier(value,label)
    try:valid=str(UUID(value))==value
    except ValueError:valid=False
    if not valid:raise VerificationError(label+' requires an exact canonical UUID')


def prepare(readback,*,flow_id,environment,expected_definition_sha256,now):
    """Change only the supplied recurrence trigger; preserve full restore evidence."""
    _guid(flow_id,'flow_id');identifier(environment,'environment')
    _guid(environment.removeprefix('Default-'),'environment')
    if not isinstance(expected_definition_sha256,str) or not re.fullmatch(r'[a-f0-9]{64}',expected_definition_sha256):
        raise VerificationError('Expected definition fingerprint must be an independent SHA-256')
    canonical(readback);complete(readback)
    observed=fresh(readback.get('observed_at_utc'),now,'fresh flow readback')
    identifier(readback.get('capture_reference'),'flow capture reference')
    revision=identifier(readback.get('saved_revision'),'saved revision')
    kind,separator,value=revision.partition(':')
    if kind=='version':version_key(value)
    elif kind!='etag' or not separator or not value or value=='*' or value!=value.strip() or '/operations/' in value.casefold() or 'operation:' in value.casefold() or value.casefold() in {'fixture','revision','saved-version-or-etag'}:
        raise VerificationError('Saved revision must identify an exact ETag/version, never an operation handle')
    flow=readback.get('flow')
    resource=f'/providers/Microsoft.ProcessSimple/environments/{environment}/flows/{flow_id}'
    if not isinstance(flow,dict) or flow.get('id')!=resource or flow.get('name')!=flow_id:
        raise VerificationError('Native flow identity does not match explicitly supplied target')
    properties=flow.get('properties')
    if not isinstance(properties,dict) or properties.get('state')!='Stopped':
        raise VerificationError('Existing writer must be Stopped; preparation does not stop it')
    history=readback.get('run_history')
    try:complete(history)
    except ValueError:raise VerificationError('complete native run history required') from None
    values=history.get('value')
    if (not isinstance(values,list) or type(history.get('item_count')) is not int
            or history['item_count']!=len(values) or history.get('flow_id')!=flow_id
            or history.get('environment')!=environment):
        raise VerificationError('Complete exact-target count-bound native run history required')
    fresh(history.get('observed_at_utc'),now,'run history capture')
    identifier(history.get('capture_reference'),'history capture reference')
    seen=set()
    for run in values:
        if not isinstance(run,dict) or not isinstance(run.get('properties'),dict):
            raise VerificationError('Resolve nonterminal or malformed run evidence')
        name=identifier(run.get('name'),'run identity')
        if name in seen:raise VerificationError('Repeated native run identity')
        seen.add(name)
        status=run['properties'].get('status')
        if not isinstance(status,str) or status not in TERMINAL_STATUSES:
            raise VerificationError('Resolve every nonterminal or unknown run before preparation')
    definition=properties.get('definition')
    if not isinstance(definition,dict) or fingerprint(definition)!=expected_definition_sha256:
        raise VerificationError('Native definition differs from independently accepted fingerprint')
    refs=properties.get('connectionReferences')
    if not isinstance(definition.get('actions'),dict) or not definition['actions'] or not isinstance(refs,dict) or not refs:
        raise VerificationError('Complete native actions and connection references required')
    parameters=definition.get('parameters')
    if not isinstance(parameters,dict) or not {'$connections','$authentication'}<=parameters.keys():
        raise VerificationError('Existing authentication and connection parameters must be retained')
    triggers=definition.get('triggers')
    if not isinstance(triggers,dict) or len(triggers)!=1:
        raise VerificationError('Exactly one existing recurrence trigger required')
    name,trigger=next(iter(triggers.items()))
    if not isinstance(trigger,dict) or trigger.get('type')!='Recurrence' or not isinstance(trigger.get('recurrence'),dict) or not trigger['recurrence']:
        raise VerificationError('Existing recurrence required for exact restoration')
    if set(trigger)-{'type','recurrence','evaluatedRecurrence','metadata','runtimeConfiguration'}:
        raise VerificationError('Unexpected trigger settings require supported reconciliation')
    manual={k:copy.deepcopy(v) for k,v in trigger.items() if k in {'metadata','runtimeConfiguration'}}
    manual.update(type='Request',kind='Button',inputs={'schema':{'type':'object','additionalProperties':False,'properties':{}}})
    candidate=copy.deepcopy(definition);candidate['triggers']={name:manual}
    return {'kind':'publication_operator_flow_packet_v1','observed_at_utc':readback['observed_at_utc'],
        'evaluated_at_utc':now.astimezone(timezone.utc).isoformat(),'saved_revision':revision,
        'flow_id':flow_id,'environment':environment,'required_state':'Stopped',
        'baseline_definition_sha256':fingerprint(definition),'manual_definition_sha256':fingerprint(candidate),
        'connection_references_sha256':fingerprint(refs),'preimage_sha256':fingerprint(flow),
        'readback_sha256':fingerprint(readback),'capture_reference':readback['capture_reference'],
        'run_history_capture_reference':history['capture_reference'],'run_history_sha256':fingerprint(history),
        'preimage':copy.deepcopy(flow),
        'install':{'properties':{'definition':candidate,'connectionReferences':copy.deepcopy(refs)}},
        'restore':{'properties':{'definition':copy.deepcopy(definition),'connectionReferences':copy.deepcopy(refs)}},
        'changed_scope':'one trigger only; actions, parameters, bindings, names and IDs preserved',
        'native_execution':'NOT_PERFORMED','activation_or_invocation_authority':False,
        'native_acceptance':False,'write_authorized':False,
        'recovery':'Native owner must compare current exact target, saved revision, graph, bindings, state and operation handle before any separately authorized action; uncertain outcomes require reconciliation, never retry.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--readback',required=True,type=Path);parser.add_argument('--flow-id',required=True)
    parser.add_argument('--environment',required=True);parser.add_argument('--expected-definition-sha256',required=True)
    parser.add_argument('--output',required=True,type=Path);parser.add_argument('--as-of')
    args=parser.parse_args(argv)
    try:
        output=private_path(args.output,'output',ROOT,output=True)
        data=read_json(private_path(args.readback,'readback',ROOT))
        now=instant(args.as_of,'evaluation time') if args.as_of else datetime.now(timezone.utc)
        packet=prepare(data,flow_id=args.flow_id,environment=args.environment,
                       expected_definition_sha256=args.expected_definition_sha256,now=now)
        exclusive_json(output,packet);return 0
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        print('Preparation failed; inputs and prior output preserved',file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
