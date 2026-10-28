"""Pure, provider-scoped reference calculations for dashboard metric qualification.

These functions neither acquire data nor write native models. Native DAX must be
compared to these results before the corresponding metric is accepted.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from math import isfinite
from statistics import mean, median


def citation_summary(publication_keys, observations, provider):
    """One explicit snapshot/provider. Conflicting duplicates fail closed."""
    keys = set(publication_keys)
    if not provider:
        raise ValueError('An explicit provider is required')
    observed = {}
    for row in observations:
        if row['provider'] != provider or row['publication_key'] not in keys:
            continue
        count = row['count']
        if count is None:
            continue
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError('Citation counts must be non-negative integers')
        if not row.get('observed_utc'):
            raise ValueError('Citation observation date required')
        key = row['publication_key']
        value = (count, row['observed_utc'])
        if key in observed and observed[key] != value:
            raise ValueError('Select one qualified observation per publication')
        observed[key] = value
    values = [x[0] for x in observed.values()]
    h = 0
    for rank, count in enumerate(sorted(values, reverse=True), 1):
        if count >= rank:
            h = rank
    return dict(provider=provider, included=len(keys), assessed=len(values),
                unknown=len(keys)-len(values), coverage=len(values)/len(keys) if keys else None,
                total=sum(values) if values else None, median=median(values) if values else None,
                uncited_share=values.count(0)/len(values) if values else None,
                collection_h_index=h if values else None,
                observed_dates=sorted({v[1] for v in observed.values()}))


def collaboration_pairs(authorships):
    """Input: publication_key, entity_key, identity_status; never name matching."""
    works = defaultdict(set)
    unresolved = 0
    for row in authorships:
        if row.get('identity_status') != 'Source-supported' or not row.get('entity_key'):
            unresolved += 1
            continue
        if not row.get('publication_key'):
            raise ValueError('Canonical publication key required')
        works[row['publication_key']].add(row['entity_key'])
    pairs = defaultdict(set)
    for work, entities in works.items():
        for pair in combinations(sorted(entities), 2):
            pairs[pair].add(work)
    rows = [dict(a=a, b=b, publications=sorted(pubs), shared_count=len(pubs))
            for (a, b), pubs in sorted(pairs.items())]
    return dict(pairs=rows, repeat_pairs=sum(r['shared_count'] >= 2 for r in rows),
                unresolved_mentions=unresolved)


def topic_counts(publication_keys, memberships, taxonomy):
    """Count distinct work/topic memberships separately within one taxonomy."""
    keys = set(publication_keys)
    grouped = defaultdict(set)
    covered = set()
    for row in memberships:
        if row['taxonomy'] != taxonomy or row['publication_key'] not in keys:
            continue
        if row.get('status') != 'qualified':
            continue
        if not all(row.get(k) for k in ('topic_id', 'source_hash', 'observed_utc')):
            raise ValueError('Qualified topic membership lacks provenance')
        grouped[row['topic_id']].add(row['publication_key'])
        covered.add(row['publication_key'])
    return dict(included=len(keys), classified=len(covered), unknown=len(keys-covered),
                coverage=len(covered)/len(keys) if keys else None,
                counts={k:len(v) for k,v in sorted(grouped.items())}, additive=False)


def forecast_baselines(year_counts, covered_years, last_complete_year):
    """Backtest contiguous qualified years; no filling missing years with zero."""
    if isinstance(last_complete_year, bool) or not isinstance(last_complete_year, int):
        raise ValueError('Integer complete-year cutoff required')
    for y, c in year_counts.items():
        if isinstance(y, bool) or not isinstance(y, int):
            raise ValueError('Integer years required')
        if isinstance(c, bool) or not isinstance(c, int) or c < 0:
            raise ValueError('Non-negative integer annual counts required')
    covered_years=set(covered_years)
    if any(isinstance(y, bool) or not isinstance(y, int) for y in covered_years):
        raise ValueError('Integer coverage years required')
    eligible = {y:c for y,c in year_counts.items() if y <= last_complete_year}
    years = sorted(eligible)
    if (not years or years != list(range(years[0], years[-1]+1))
            or not set(years) <= set(covered_years) or years[-1] != last_complete_year):
        return dict(status='suppressed', reason='Unqualified or discontinuous annual coverage')
    if len(years) < 15:
        return dict(status='suppressed', reason='Need ten training years and five rolling origins')
    outcomes = {}
    counts = [eligible[y] for y in years]
    for model in ('previous_year', 'trailing_three_year_mean'):
        horizons = {}
        for horizon in (1, 2, 3):
            cases=[]
            for end in range(10, len(counts)-horizon+1):
                training=counts[:end]
                prediction=training[-1] if model == 'previous_year' else mean(training[-3:])
                actual=counts[end+horizon-1]
                cases.append(dict(training_end=years[end-1], target_year=years[end+horizon-1],
                                  prediction=prediction, actual=actual, error=prediction-actual))
            errors=[r['error'] for r in cases]
            qualified = len(cases) >= 5
            horizons[str(horizon)]=dict(
                status='evaluated' if qualified else 'suppressed', cases=cases,
                reason=None if qualified else 'Need five rolling origins for this horizon',
                mae=mean(map(abs, errors)) if qualified else None,
                bias=mean(errors) if qualified else None)
        outcomes[model]=horizons
    winner=min(outcomes, key=lambda m:(outcomes[m]['1']['mae'], abs(outcomes[m]['1']['bias']), m))
    return dict(status='baseline_evaluated', models=outcomes, best_baseline=winner,
                native_display_qualified=False, interval_qualified=False)


def candidate_promotable(candidate_mae, candidate_bias, baseline_mae, baseline_bias):
    values=(candidate_mae,candidate_bias,baseline_mae,baseline_bias)
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v) for v in values):
        raise ValueError('Finite benchmark values required')
    if candidate_mae < 0 or baseline_mae < 0:
        raise ValueError('MAE cannot be negative')
    # Cannot improve a perfect baseline by ten percent.
    return (baseline_mae > 0 and candidate_mae <= .9*baseline_mae
            and abs(candidate_bias) <= abs(baseline_bias))
