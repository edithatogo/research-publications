"""Evaluate saved grants collector evidence without service calls or effects.

This is an operator diagnostic, not a scheduler, SLA or native acceptance grant.
"""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

SOURCES = {'nhmrc': (5, 14), 'mrff': (6, 3)}
BRISBANE = ZoneInfo('Australia/Brisbane')


def instant(value):
    if not isinstance(value, str):
        raise ValueError('Explicit offset-bearing timestamp required')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError('Invalid timestamp') from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('Explicit offset-bearing timestamp required')
    return result.astimezone(timezone.utc)


def verify_archive(source, run_id, generations, archive_root):
    """Hash actual saved bytes and bind the native manifest to this exact run."""
    if (not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', run_id)
            or any(not isinstance(g, dict) for g in generations)):
        return False
    matches = [g for g in generations if g.get('source') == source and g.get('run') == run_id]
    if len(matches) != 1 or archive_root is None:
        return False
    g = matches[0]
    if g.get('manifest_exact_run') is not True or not isinstance(g.get('files'), list):
        return False
    expected = {f'{source}-{i:02d}-original.xlsx' for i in range(1, SOURCES[source][1] + 1)}
    expected |= {'manifest.json', 'source-page.html', 'source-page-after.html'}
    files = g['files']
    if any(not isinstance(f, dict) or not isinstance(f.get('name'), str) for f in files):
        return False
    if len(files) != len(expected) or {f.get('name') for f in files} != expected:
        return False
    root = Path(archive_root).resolve()
    folder = (root / (source + '-' + run_id)).resolve()
    if not folder.is_relative_to(root):
        return False
    try:
        for f in files:
            target = (folder / f['name']).resolve()
            if (not target.is_relative_to(folder) or type(f.get('bytes')) is not int
                    or f['bytes'] < 1 or not re.fullmatch(r'[a-f0-9]{64}', f.get('sha256', ''))):
                return False
            raw = target.read_bytes()
            if len(raw) != f['bytes'] or hashlib.sha256(raw).hexdigest() != f['sha256']:
                return False
        manifest = json.loads((folder / 'manifest.json').read_text())
        originals = manifest['files']
        by_name = {f['name']: f for f in files}
        names = {f'{source}-{i:02d}-original.xlsx' for i in range(1, SOURCES[source][1] + 1)}
        return (manifest.get('run') == run_id and manifest.get('source') == source
                and manifest.get('complete') is True
                and len(originals) == len(names) and {f['name'] for f in originals} == names
                and all(f.get('saved_readback_equal') is True
                        and type(f.get('stored_bytes')) is int
                        and f['stored_bytes'] == by_name[f['name']]['bytes'] for f in originals))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def evaluate(source, flow, history, generations, *, as_of, history_from,
             history_through, history_complete=False, reads_verified=False, archive_root=None, due_by=None):
    if source not in SOURCES:
        raise ValueError('Only the qualified NHMRC/MRFF archive collectors are supported')
    now, begin, end = map(instant, (as_of, history_from, history_through))
    if begin > end:
        raise ValueError('History window is reversed')
    if not isinstance(history, list) or not isinstance(generations, list):
        raise ValueError('Complete native run array and generation array required')
    local = now.astimezone(BRISBANE)
    slot = (local - timedelta(days=local.weekday())).replace(
        hour=SOURCES[source][0], minute=0, second=0, microsecond=0)
    if slot > local:
        slot -= timedelta(days=7)
    deadline = instant(due_by) if due_by is not None else None
    if deadline is not None and deadline < slot.astimezone(timezone.utc):
        raise ValueError('Explicit deadline precedes the expected occurrence')
    result = {'source': source, 'as_of': as_of, 'expected_occurrence': slot.isoformat(),
              'next_occurrence': (slot + timedelta(days=7)).isoformat(),
              'status': 'UNKNOWN', 'reasons': [], 'native_acceptance': False,
              'outbound_actions': 0, 'schedule_changes': 0,
              'limitation': 'Evaluates supplied saved evidence; does not obtain fresh reads or establish an SLA.'}
    reasons = result['reasons']
    props = flow.get('properties', {})
    triggers = props.get('definition', {}).get('triggers', {})
    expected = {'frequency': 'Week', 'interval': 1, 'timeZone': 'E. Australia Standard Time',
                'schedule': {'weekDays': ['Monday'], 'hours': [SOURCES[source][0]], 'minutes': [0]}}
    if (len(triggers) != 1 or next(iter(triggers.values()), {}).get('type') != 'Recurrence'
            or next(iter(triggers.values()), {}).get('recurrence') != expected
            or type(next(iter(triggers.values()), {}).get('recurrence', {}).get('interval')) is not int):
        reasons.append('saved_schedule_not_qualified')
        return result
    fid, flow_path = flow.get('name'), flow.get('id')
    if (not isinstance(fid, str) or not isinstance(flow_path, str)
            or not flow_path.endswith('/flows/' + fid)):
        raise ValueError('Exact native flow identity required')
    complete = (history_complete is True and reads_verified is True
                and begin <= slot.astimezone(timezone.utc) and end >= now)
    candidates, names = [], set()
    for run in history:
        if not isinstance(run, dict) or not isinstance(run.get('name'), str):
            raise ValueError('Malformed native run')
        rid = run['name']
        if rid in names or run.get('id') != flow_path + '/runs/' + rid:
            raise ValueError('Duplicate run or wrong flow identity')
        names.add(rid)
        rp = run.get('properties', {})
        trigger = rp.get('trigger', {})
        scheduled = trigger.get('scheduledTime')
        if not scheduled:
            continue
        scheduled = instant(scheduled)
        scheduled_local = scheduled.astimezone(BRISBANE)
        if scheduled_local.replace(second=0, microsecond=0) != slot or scheduled > now:
            if (scheduled <= now and scheduled_local.date() == slot.date()
                    and scheduled_local > slot and trigger.get('name') in triggers):
                reasons.append('later_recurrence_origin_needs_slot_reconciliation')
            continue
        if (trigger.get('name') not in triggers or trigger.get('originHistoryName') != rid
                or trigger.get('correlation', {}).get('clientTrackingId') != rid):
            reasons.append('trigger_origin_uncertain')
            continue
        start = instant(rp.get('startTime'))
        if start < scheduled or start > now:
            raise ValueError('Run timing contradicts the selected occurrence')
        if rp.get('endTime'):
            finished = instant(rp['endTime'])
            if finished < start or finished > now:
                raise ValueError('Run end contradicts the observation window')
        candidates.append(run)
    if props.get('state') != 'Started':
        result['status'] = 'STOPPED' if props.get('state') == 'Stopped' else 'UNKNOWN'
        reasons.append('collector_not_started')
    elif len(candidates) > 1:
        reasons.append('multiple_runs_in_expected_slot')
    elif not candidates:
        result['status'] = 'MISSED' if complete and not reasons and deadline is not None and now >= deadline else 'UNKNOWN'
        if deadline is None:
            reasons.append('no_operator_deadline_supplied')
        reasons.append('no_correlated_expected_occurrence')
    else:
        run = candidates[0]; rp = run['properties']; status = rp.get('status')
        result['run_id'] = run['name']
        result['terminal_status'] = status
        if status in {'Failed', 'TimedOut', 'Cancelled'}:
            result['status'] = 'FAILED'
            reasons.append('inspect_exact_failed_actions_then_reconcile_effects_before_retry')
        elif status in {'Running', 'Waiting', 'InProgress'}:
            result['status'] = 'IN_PROGRESS'
            reasons.append('no_timeout_sla_inferred')
        elif status == 'Succeeded' and not rp.get('endTime'):
            reasons.append('successful_run_missing_terminal_time')
        elif status == 'Succeeded':
            valid = verify_archive(source, run['name'], generations, archive_root)
            result['archive_integrity_verified'] = valid
            result['status'] = 'VERIFIED_SAVED_OCCURRENCE' if valid and complete and not reasons else 'UNKNOWN'
            if not valid:
                reasons.append('exact_generation_integrity_missing_or_failed')
        else:
            reasons.append('unknown_native_run_status')
    if not complete:
        reasons.append('history_or_read_coverage_unverified')
    return result
