# SPDX-License-Identifier: Apache-2.0
"""Compare supplied complete logical registry captures; no native operation.

Logical Id is exact positive decimal text. Native GUID/integer exports use the
separate protected-field verifier; neither helper invents a projection or key.
"""
from __future__ import annotations
import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

if __package__:
    from scripts.publication_batch_contract import PROTECTED_MANUAL_FIELDS
    from scripts.verify_publication_protected_fields import (VerificationError, snapshot, versions,
        preserve_history, identifier, instant, expected_keys as key_set, same, digest,
        private_path, read_json, exclusive_json)
else:
    from publication_batch_contract import PROTECTED_MANUAL_FIELDS
    from verify_publication_protected_fields import (VerificationError, snapshot, versions,
        preserve_history, identifier, instant, expected_keys as key_set, same, digest,
        private_path, read_json, exclusive_json)

ROOT=Path(__file__).resolve().parents[1]
FIELDS=PROTECTED_MANUAL_FIELDS | {'Id','PMID','LastObservedUTC'}


def _export(payload,label,now):
    rows,stamp=snapshot(payload,'rows',now)
    if not rows:raise VerificationError(label+': nonempty rows array required')
    indexed={}
    for row in rows:
        if not isinstance(row,dict) or any(k not in row for k in FIELDS):
            raise VerificationError(label+': missing fields or invalid rows')
        identity=row['Id']
        if not isinstance(identity,str) or not re.fullmatch(r'[1-9][0-9]*',identity):
            raise VerificationError('Exact positive decimal text item ID required')
        if identity in indexed:raise VerificationError('duplicate item ID')
        for field in ('SourceKey','CanonicalKey'):
            if row[field] not in (None,''):identifier(row[field],field)
        if row['PMID'] not in (None,'') and (not isinstance(row['PMID'],str) or not re.fullmatch(r'[1-9][0-9]*',row['PMID'])):
            raise VerificationError('Exact positive ASCII PMID text required')
        versions(row);indexed[identity]=row
    return indexed,stamp


def _keys(rows):return Counter(row['SourceKey'] for row in rows.values() if row['SourceKey'] not in (None,''))


def verify(before,after,expected_keys,*,now=None):
    now=now or datetime.now(timezone.utc);expected=key_set(expected_keys)
    old,before_time=_export(before,'before',now);new,after_time=_export(after,'after',now)
    if not same(before['target'],after['target']) or after_time<before_time:
        raise VerificationError('Capture target or chronology differs')
    old_keys,new_keys=_keys(old),_keys(new)
    old_blank={k for k,r in old.items() if r['SourceKey'] in (None,'')}
    new_blank={k for k,r in new.items() if r['SourceKey'] in (None,'')}
    changes=[];advanced=[]
    for identity in sorted(old.keys() & new.keys()):
        prior,current=old[identity],new[identity]
        preserve_history(prior,current)
        for field in sorted(PROTECTED_MANUAL_FIELDS | {'PMID'}):
            if not same(prior[field],current[field]):changes.append({'Id':identity,'field':field})
        try:
            first_old=instant(prior['FirstObservedUTC'],'FirstObservedUTC')
            first_new=instant(current['FirstObservedUTC'],'FirstObservedUTC')
            last_old=instant(prior['LastObservedUTC'],'LastObservedUTC')
            last_new=instant(current['LastObservedUTC'],'LastObservedUTC')
        except ValueError:
            changes.append({'Id':identity,'field':'observation_timestamp','issue':'unknown_or_unqualified_instant'})
            continue
        if first_old!=first_new or last_new<last_old or last_old<first_old or last_new<first_new or last_new>after_time or last_old>before_time:
            changes.append({'Id':identity,'field':'observation_order'})
        if current['SourceKey'] in expected and last_new>last_old:
            if not before_time<=last_new<=after_time:
                changes.append({'Id':identity,'field':'observation_outside_replay_capture_window'})
            elif len(current['versions'])<=len(prior['versions']):
                changes.append({'Id':identity,'field':'version_history_not_advanced'})
            else:advanced.append(current['SourceKey'])
    mismatched={r['SourceKey'] for r in new.values() if isinstance(r['SourceKey'],str)
                and r['SourceKey'].startswith('pubmed:') and r['PMID']!=r['SourceKey'].split(':',1)[1]}
    issues={'added_item_ids':sorted(new.keys()-old.keys()),'removed_item_ids':sorted(old.keys()-new.keys()),
        'added_keys':sorted(new_keys.keys()-old_keys.keys()),'removed_keys':sorted(old_keys.keys()-new_keys.keys()),
        'duplicate_keys_before':sorted(k for k,c in old_keys.items() if c!=1),
        'duplicate_keys_after':sorted(k for k,c in new_keys.items() if c!=1),
        'blank_item_ids_added':sorted(new_blank-old_blank),'blank_item_ids_removed':sorted(old_blank-new_blank),
        'expected_missing_before':sorted(expected-old_keys.keys()),'expected_missing_after':sorted(expected-new_keys.keys()),
        'expected_last_observed_not_advanced':sorted(expected-set(advanced)),
        'pmid_mismatches_after':sorted(mismatched),'preservation_or_timestamp_changes':changes}
    return {**issues,'pass':not any(issues.values()),'before_rows':len(old),'after_rows':len(new),
        'expected_keys':len(expected),'native_acceptance':False,'write_authorized':False,'native_field_contract_qualified':False,
        'protected_fields_checked':sorted(PROTECTED_MANUAL_FIELDS),'before_export_sha256':digest(before),
        'after_export_sha256':digest(after),'target':copy.deepcopy(before['target']),
        'evaluated_at_utc':now.astimezone(timezone.utc).isoformat(),
        'capture_references':[before['capture_reference'],after['capture_reference']]}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('before','after','expected-keys','output'):parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--as-of');args=parser.parse_args(argv)
    try:
        output=private_path(args.output,'output',ROOT,output=True)
        before=read_json(private_path(args.before,'before',ROOT));after=read_json(private_path(args.after,'after',ROOT))
        keys=read_json(private_path(args.expected_keys,'expected keys',ROOT))
        now=instant(args.as_of,'evaluation time') if args.as_of else datetime.now(timezone.utc)
        result=verify(before,after,keys,now=now)
        exclusive_json(output,result)
        return 0 if result['pass'] else 1
    except (OSError,ValueError,TypeError,KeyError):
        print('Replay verification failed; inputs and prior output preserved',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
