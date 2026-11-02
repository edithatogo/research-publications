"""Prepare a single manual FlowAgent append for an evidence-bound policy version."""
import argparse
import base64
import json
from pathlib import Path
from uuid import UUID

from scripts.grants_internal_deadlines import approved_policy, canonical
from scripts.prepare_live_grants_calendar import branch, compose, envelope, guard, manual, spo


def prepare(context, record, organisation, evidence):
    policy = approved_policy(record, organisation=organisation, evidence_files=evidence)
    if policy is None:
        return {'disposition': 'held', 'reason': 'approved_policy_missing'}
    version = record['PolicyVersionKey']
    fields = {'Title': version, 'PolicyVersionKey': version, 'PolicyJson': canonical(policy)}
    encoded = base64.b64encode(canonical(fields).encode()).decode()
    items = "_api/web/lists(guid'" + str(UUID(context['policy_id'])) + "')/items"
    lookup = items + "?$select=PolicyVersionKey,PolicyJson&$top=2&$filter=PolicyVersionKey eq '" + version + "'"
    actions = {
        'Payload': compose("@json(base64ToString('" + encoded + "'))"),
        'Existing': spo(context, 'GET', lookup, 'Payload'),
        'Append': branch("@empty(body('Existing')?['value'])",
                         {'Create': spo(context, 'POST', items, body="@outputs('Payload')")},
                         previous='Existing'),
        'Saved': spo(context, 'GET', lookup, 'Append'),
        'Exact': guard("and(equals(length(body('Saved')?['value']),1),equals(first(body('Saved')?['value'])?['PolicyJson'],outputs('Payload')?['PolicyJson']))", 'Saved')}
    refs = {'shared_sharepointonline': {'id': '/providers/Microsoft.PowerApps/apis/shared_sharepointonline',
            'connectionName': context['sharepoint_connection'], 'source': 'Embedded'}}
    return {'definition': envelope(actions, manual()), 'connectionReferences': refs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('context', 'record', 'organisation', 'evidence', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    private = Path(__file__).resolve().parents[1] / 'private/ops'
    def path(value):
        target = Path(value).resolve()
        if not target.is_relative_to(private):
            raise ValueError('Private occurrence path required')
        return target
    def read(value):
        return json.loads(path(value).read_bytes())
    result = prepare(read(args.context), read(args.record), args.organisation, read(args.evidence))
    with path(args.output).open('x') as output:
        json.dump(result, output)


if __name__ == '__main__':
    main()
