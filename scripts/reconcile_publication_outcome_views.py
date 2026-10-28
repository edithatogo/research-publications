"""Independent local reconciliation of captured native T18 source/detail/plot rows.

No queries, writes or rendering. A passing capture proves only the supplied
snapshot and selected metrics, never browser accessibility/performance or impact.

SPDX-License-Identifier: Apache-2.0
"""
from datetime import date
from math import isclose

FIELDS = ('CanonicalKey', 'Title', 'SourceSet', 'AttributionStatus',
          'PublicationDateRaw', 'PublicationDatePrecision', 'PublicationDate',
          'PublicationMonth', 'PublicationYear', 'PubMedURL', 'DORAURL')
PROVENANCE = ('CutoffExclusive', 'CapturedUTC', 'MetricVersion', 'ModelRevision',
              'ReportRevision', 'SourceVersions')


def rows(document):
    def complete(value):
        if (not isinstance(value, dict) or 'error' in value or 'errors' in value
                or any(k in value and value[k] is not False for k in ('partial','truncated'))):
            raise ValueError('Failed or incomplete query is not empty evidence')
    complete(document)
    results = document.get('results')
    if not isinstance(results, list) or len(results) != 1:
        raise ValueError('One complete query result required')
    complete(results[0])
    tables = results[0].get('tables')
    if not isinstance(tables, list) or len(tables) != 1:
        raise ValueError('One complete result table required')
    complete(tables[0])
    records=tables[0].get('rows')
    if not isinstance(records,list) or any(not isinstance(r,dict) for r in records):
        raise ValueError('Explicit captured row list required')
    result = []
    for row in records:
        normalized = {}
        for field, value in row.items():
            if not isinstance(field,str) or not field:
                raise ValueError('Text query field required')
            name = field.split('[', 1)[-1].removesuffix(']')
            if name in normalized:
                raise ValueError('Duplicate normalized field')
            normalized[name] = value
        result.append(normalized)
    return result


def _index(records):
    out = {}
    for row in records:
        key = row.get('CanonicalKey')
        if not isinstance(key, str) or not key or key in out:
            raise ValueError('Complete unique canonical keys required')
        out[key] = row
    return out


def reconcile(source, detail, plot, views):
    source, detail = _index(source), _index(detail)
    if not source or source.keys() != detail.keys():
        raise ValueError('Source/detail complete nonempty key sets must match')
    totals = {'Included': len(source), 'Open': 0, 'Closed': 0, 'Unknown': 0,
              'UnknownMonth': 0}
    for key, original in source.items():
        row = detail[key]
        if row.get('SnapshotID') != 'current':
            raise ValueError('Only current snapshot belongs in this comparison')
        for field in FIELDS:
            if field not in original or field not in row or original[field] != row[field]:
                raise ValueError('Source/detail field mismatch: ' + field)
        flags = [row.get('OAOpen'), row.get('OAClosed'), row.get('OAUnknown')]
        if any(type(v) is not int or v not in (0, 1) for v in flags) or sum(flags) != 1:
            raise ValueError('Exactly one OA evidence state required')
        for label, flag in zip(('Open', 'Closed', 'Unknown'), flags):
            totals[label] += flag
        month = row['PublicationMonth']
        usable = row['PublicationDatePrecision'] in {'day', 'month'} and bool(month)
        if usable:
            try:
                parsed = date.fromisoformat(month + '-01')
                usable = len(month) == 7 and parsed.strftime('%Y-%m') == month
            except (ValueError, TypeError):
                usable = False
        totals['UnknownMonth'] += not usable
    totals['Assessed'] = totals['Open'] + totals['Closed']
    totals['Rate'] = totals['Open'] / totals['Assessed'] if totals['Assessed'] else None
    totals['Coverage'] = totals['Assessed'] / totals['Included']
    if set(plot) != set(totals):
        raise ValueError('Exact selected plot metric set required')
    for metric, expected in totals.items():
        actual = plot[metric]
        if expected is None:
            valid = actual is None
        elif metric in {'Rate', 'Coverage'}:
            valid = type(actual) in (int, float) and isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
        else:
            valid = type(actual) is int and actual == expected
        if not valid:
            raise ValueError('Independent plot mismatch: ' + metric)
    current = [v for v in views if v.get('SnapshotID') == 'current']
    unavailable = [v for v in views if v.get('SnapshotID') == 'original-unavailable']
    if len(current) != 1 or current[0].get('Available') is not True:
        raise ValueError('One available current view required')
    if len(unavailable) != 1 or unavailable[0].get('Available') is not False:
        raise ValueError('Absent issued evidence must remain unavailable')
    if any(not isinstance(current[0].get(k), str) or not current[0][k].strip() for k in PROVENANCE):
        raise ValueError('Current metric/date/source provenance required')
    cutoff = date.fromisoformat(current[0]['CutoffExclusive'][:10])
    if cutoff.day != 1:
        raise ValueError('Complete-month cutoff must begin a month')
    return {'status': 'PASS_CAPTURED_CURRENT_ONLY', 'keys': len(source),
            'fields_per_key': len(FIELDS), 'metrics': totals,
            'provenance': {k: current[0][k] for k in PROVENANCE},
            'native_rendering_verified': False, 'impact_judgement': False}


def main():
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'detail', 'plot', 'views', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    captured = {name: rows(json.loads(getattr(args, name).read_text()))
                for name in ('source', 'detail', 'plot', 'views')}
    if len(captured['plot']) != 1:
        raise ValueError('Exactly one plot metric row required')
    result = reconcile(captured['source'], captured['detail'], captured['plot'][0], captured['views'])
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(result['status'])


if __name__ == '__main__':
    main()
