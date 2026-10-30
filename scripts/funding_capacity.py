"""Pure C01/C02/F01 projections from explicitly mapped authoritative records.

No source discovery, identity inference, currency conversion or native writes.
Opportunities and applications are never admitted as awards.
SPDX-License-Identifier: Apache-2.0
"""
from datetime import date
from decimal import Decimal, InvalidOperation


def project(projects, awards, participation, *, period_end, complete):
    if complete is not True:
        raise ValueError('Complete selected source snapshots required')
    end = date.fromisoformat(period_end)
    def unique(rows, key):
        seen = set()
        for row in rows:
            value = row.get(key)
            if not isinstance(value, str) or not value or value != value.strip() or value in seen:
                raise ValueError('Missing or duplicate canonical identity: '+key)
            seen.add(value)
        return seen
    project_ids = unique(projects, 'project_id')
    unique(awards, 'award_id'); unique(participation, 'participation_id')
    active, unknown = [], []
    for row in projects:
        if row.get('start_date') is None or row.get('end_date_known') is not True:
            unknown.append(row['project_id']); continue
        start = date.fromisoformat(row['start_date'])
        finish = date.fromisoformat(row['end_date']) if row.get('end_date') else None
        if finish and finish < start: raise ValueError('Project dates reversed')
        lead = row.get('chhhs_led')
        if lead is not None and type(lead) is not bool: raise ValueError('Explicit lead evidence required')
        if start <= end and (finish is None or end <= finish): active.append(row)
    researchers = set(); unknown_roles = 0
    for row in participation:
        if row.get('project_id') not in project_ids: raise ValueError('Unresolved project link')
        if not row.get('person_id') or not row.get('role') or not row.get('start_date') or row.get('end_date_known') is not True:
            unknown_roles += 1; continue
        start = date.fromisoformat(row['start_date'])
        finish = date.fromisoformat(row['end_date']) if row.get('end_date') else None
        if finish and finish < start: raise ValueError('Participation dates reversed')
        if start <= end and (finish is None or end <= finish): researchers.add(row['person_id'])
    totals = {}; missing_awards = []
    for row in awards:
        if row.get('record_kind') != 'Award': raise ValueError('Only canonical awards admitted')
        currency, start, amount = row.get('currency'), row.get('start_date'), row.get('amount')
        if currency is None or start is None or amount is None:
            missing_awards.append(row['award_id']); continue
        if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha() or currency != currency.upper():
            raise ValueError('Explicit currency code required')
        if not isinstance(amount, str): raise ValueError('Exact decimal amount text required')
        try: value = Decimal(amount)
        except InvalidOperation as exc: raise ValueError('Invalid award amount') from exc
        if not value.is_finite() or value < 0: raise ValueError('Nonnegative finite award amount required')
        started = date.fromisoformat(start)
        if started > end: continue
        key = (currency, started.year)
        totals[key] = totals.get(key, Decimal(0)) + value
    return {'period_end': period_end,
            'active_projects': len(active), 'unknown_project_periods': len(unknown),
            'led_projects': sum(r.get('chhhs_led') is True for r in active),
            'known_lead_projects': sum(r.get('chhhs_led') is not None for r in active),
            'unknown_lead_projects': sum(r.get('chhhs_led') is None for r in active),
            'evidenced_researchers': len(researchers), 'incomplete_participation': unknown_roles,
            'award_cohorts': [{'currency': c, 'start_year': y, 'amount': str(v)} for (c,y),v in sorted(totals.items())],
            'incomplete_awards': missing_awards,
            'fte': None, 'training_completion': None, 'application_success': None,
            'native_acceptance': False}


def main(argv=None):
    import argparse, json, os, subprocess, sys
    from pathlib import Path
    if not __package__: sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.deploy_report_definition import strict
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    inputs = strict(Path(args.input).read_bytes())
    result = project(**inputs)
    root = Path(__file__).resolve().parents[1]; output = Path(args.output).resolve()
    if not output.is_relative_to(root / 'private' / 'ops'): raise ValueError('Private output required')
    subprocess.run(['git','check-ignore','-q',str(output)],cwd=root,check=True)
    with os.fdopen(os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as handle:
        json.dump(result,handle,indent=2,allow_nan=False)
    print('PASS_LOCAL_ONLY; authoritative source mapping and native acceptance remain separate')


if __name__ == '__main__': main()
