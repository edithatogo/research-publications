"""Prepare a guarded PAC same-record update and verify saved clientdata offline.

No network, token handling, draft deletion, activation, invocation or retries.
"""
import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime, timezone
from pathlib import Path
from uuid import UUID


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def clientdata(record):
    value = record['clientdata']
    result = json.loads(value) if isinstance(value, str) else value
    props = result['properties']
    if not isinstance(props['definition'], dict) or not isinstance(props['connectionReferences'], dict):
        raise ValueError('Complete definition and connectionReferences required')
    return result


def inspect(snapshot):
    # These attestations must come from complete supported owner readbacks.
    if snapshot.get('draft_checked') is not True or 'draft' not in snapshot or snapshot['draft'] is not None:
        raise ValueError('Unresolved/unknown draft; inspect it, never delete automatically')
    if snapshot.get('runs_complete') is not True or snapshot.get('active_runs') != []:
        raise ValueError('Active/unknown operation history')
    record = snapshot['published']
    UUID(record['workflowid'])
    if type(record.get('statecode')) is not int or record['statecode'] != 0 or not record.get('name'):
        raise ValueError('Expected named stopped/Draft Dataverse record')
    if type(record.get('componentstate')) is not int or record['componentstate'] != 0:
        raise ValueError('Expected published component layer')
    clientdata(record)
    return record


def validate_inputs(candidate, body):
    triggers = candidate['properties']['definition']['triggers']
    if len(triggers) != 1:
        raise ValueError('Select a single manual trigger for input validation')
    trigger = next(iter(triggers.values()))
    if trigger.get('type') != 'Request' or trigger.get('kind') != 'Button':
        raise ValueError('Only qualified manual Button input shape supported')
    schema = trigger.get('inputs', {}).get('schema', {})
    if not isinstance(body, dict) or schema.get('type') != 'object':
        raise ValueError('Object inputs/schema required')
    if set(schema) - {'type', 'properties', 'required', 'description', 'title'}:
        raise ValueError('Unsupported manual schema constraint; qualify separately')
    fields = schema.get('properties', {})
    if any(set(field) - {'type', 'description', 'title'} for field in fields.values()):
        raise ValueError('Unsupported field constraint; qualify separately')
    if set(body) - set(fields) or set(schema.get('required', [])) - set(body):
        raise ValueError('Missing required or unexpected manual inputs')
    for name, value in body.items():
        if fields[name].get('type') != 'string' or not isinstance(value, str):
            raise ValueError('Only qualified string inputs supported; no coercion')
    return {'body_sha256': digest(body), 'transport': 'explicit-owner-qualified-only',
            'invoked': False, 'warning': 'Management run/callback fallback may omit inputs; never use silently'}


def prepare(snapshot, candidate, inputs=None, *, canonical_contract=None):
    before = inspect(snapshot)
    old = clientdata(before)
    props = candidate['properties']
    additive_plan = None
    if canonical_contract is not None:
        # No arbitrary reference exemption: rebuild the entire permitted delta.
        from scripts.prepare_canonical_output import build, deployment_plan
        if set(canonical_contract) != {'writer', 'reporting_month', 'period_policy', 'revision'}:
            raise ValueError('Complete explicit canonical build contract required')
        expected = build(before, **canonical_contract)
        if candidate != expected:
            raise ValueError('Candidate differs from exact canonical rebuild')
        additive_plan = deployment_plan(before, candidate)
        additive_plan['writer_snapshot_sha256'] = digest(canonical_contract['writer'])
    if set(candidate) != set(old) or {k: v for k, v in candidate.items() if k != 'properties'} != {k: v for k, v in old.items() if k != 'properties'}:
        raise ValueError('Unexpected clientdata wrapper change')
    if set(props) != set(old['properties']) or any(props[k] != v for k, v in old['properties'].items() if k != 'definition' and not (additive_plan is not None and k == 'connectionReferences')):
        raise ValueError('Connection/credential mode or non-definition properties changed')
    if not isinstance(props['definition'], dict) or not props['definition'].get('triggers'):
        raise ValueError('Complete candidate definition required')
    def check_hosts(node):
        if isinstance(node, dict):
            host = node.get('host')
            if isinstance(host, dict) and 'connection' in host and 'connectionName' in host:
                raise ValueError('Mixed connector host formats are unsupported')
            for value in node.values():
                check_hosts(value)
        elif isinstance(node, list):
            for value in node:
                check_hosts(value)
    check_hosts(props['definition'])
    raw = before['clientdata']
    if not isinstance(raw, str):
        raise ValueError('Retain exact original clientdata text for guard')
    # Power Fx text escaping uses doubled quotes, not shell escaping.
    quote = lambda s: '"' + s.replace('"', '""') + '"'
    guid = quote(str(UUID(before['workflowid'])))
    lookup = f'LookUp(Processes,workflowid=GUID({guid}))'
    candidate_text = json.dumps(candidate, separators=(',', ':'), ensure_ascii=False)
    formula = (f'If(And({lookup}.statecode=workflow_workflow_statecode.\'0\','
               f'{lookup}.name={quote(before["name"])},{lookup}.clientdata={quote(raw)}),'
               f'Patch(Processes,{lookup},{{clientdata:{quote(candidate_text)}}}),'
               'Error("FLOW_PREIMAGE_CHANGED"))\n')
    plan = {'schema_version': 1, 'workflowid': before['workflowid'], 'name': before['name'],
            'preimage_sha256': digest(before), 'candidate_sha256': digest(candidate),
            'references_sha256': digest(props['connectionReferences']),
            'prepared_at': datetime.now(UTC).isoformat(),
            'atomic_conditional_write': False, 'native_acceptance': False,
            'canonical_addition': additive_plan,
            'input_contract': validate_inputs(candidate, inputs) if inputs is not None else None}
    return plan, formula


def verify(plan, candidate, snapshot):
    record = inspect(snapshot)
    if (record['workflowid'], record['name']) != (plan['workflowid'], plan['name']):
        raise ValueError('Native identity/name changed')
    if digest(candidate) != plan['candidate_sha256'] or digest(clientdata(record)) != plan['candidate_sha256']:
        raise ValueError('Source or saved graph differs; reconcile before retry')
    if digest(clientdata(record)['properties']['connectionReferences']) != plan['references_sha256']:
        raise ValueError('Reference/credential map differs')
    return {'status': 'PASS_SAVED_DEFINITION_COMPARISON', 'native_runtime_proven': False,
            'workflowid': record['workflowid'], 'candidate_sha256': plan['candidate_sha256'],
            'state_preserved': True, 'credential_map_preserved': True}


def private_output(path):
    root = Path(__file__).resolve().parents[1]
    resolved = path.resolve()
    if not resolved.is_relative_to(root / 'private/ops'):
        raise ValueError('Outputs must remain under this checkout private/ops')
    result = subprocess.run(['git', 'check-ignore', '-q', '--', str(resolved)],
                            cwd=root, check=False, capture_output=True)
    if result.returncode != 0:
        raise ValueError('Output must be ignored; never publish native definitions')
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'verify'])
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--inputs', type=Path)
    parser.add_argument('--canonical-contract', type=Path, help='Exact writer snapshot and explicit canonical build options; prepare only')
    args = parser.parse_args()
    read = lambda p: json.loads(p.read_text())
    try:
        args.output = private_output(args.output)
        if args.mode == 'prepare':
            args.plan = private_output(args.plan)
        snapshot, candidate = read(args.snapshot), read(args.candidate)
        if args.mode == 'prepare':
            plan, formula = prepare(snapshot, candidate, read(args.inputs) if args.inputs else None, canonical_contract=read(args.canonical_contract) if args.canonical_contract else None)
            if args.plan.exists() or args.output.exists() or args.plan.resolve() == args.output.resolve():
                raise ValueError('Use distinct new private output paths; never overwrite evidence')
            with args.plan.open('x') as f:
                json.dump(plan, f, indent=2)
            with args.output.open('x') as f:
                f.write(formula)
        else:
            if args.canonical_contract:
                raise ValueError('Canonical contract applies only to prepare')
            result = verify(read(args.plan), candidate, snapshot)
            with args.output.open('x') as f:
                json.dump(result, f, indent=2)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f'FAIL: {exc}\n')


if __name__ == '__main__':
    main()
