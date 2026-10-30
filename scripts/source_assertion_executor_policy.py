"""Offline domain-policy bridge for the guarded Node executor (no authentication)."""
# SPDX-License-Identifier: Apache-2.0
import sys
import json
from scripts.deploy_report_definition import strict
from scripts.source_assertion_persistence import validate, schema_requirements, request, reconcile


def main():
    if sys.version_info[:3] != (3,15,1):raise RuntimeError('Repository Python 3.15.1 required')
    payload=strict(sys.stdin.buffer.read());operation=sys.argv[1]
    if operation=='validate':
        plan=payload['plan'] if 'plan' in payload else payload
        result=validate(plan)
    elif operation=='schema':
        result=schema_requirements(payload)
        if any(x['outcome']!='pass' for x in result):raise ValueError('Fresh schema requirements not satisfied')
    elif operation=='request':result=request(payload['plan'],payload['current'])
    elif operation=='reconcile':result=reconcile(payload['plan'],payload['current'])
    else:raise ValueError('Unknown policy operation')
    print(json.dumps(result,allow_nan=False))


if __name__=='__main__':main()
