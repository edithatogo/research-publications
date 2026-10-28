"""Build a review-gated iCalendar projection for grant opportunities.

The output is a local artifact contract.  It does not subscribe users, send
notifications, or write a calendar.  Only exact source deadlines or valid
institutional dates become events; uncertain dates are omitted rather than
assigned a guessed day.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

from scripts.grants_planning import (
    institutional_deadline,
    institutional_policy_status,
    validate_policy,
)

_ROOT = Path(__file__).resolve().parents[1]


def _escape(value: Any) -> str:
    # RFC 5545 TEXT values must not contain literal line breaks. Normalize
    # CRLF/CR before escaping so source text cannot inject extra properties.
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold_content_line(line: str, *, max_octets: int = 75) -> list[str]:
    """Fold an iCalendar content line on Unicode boundaries (RFC 5545 §3.1)."""
    if type(max_octets) is not int or max_octets < 2:
        raise ValueError("max_octets must be an integer of at least 2")
    physical: list[str] = []
    current = ""
    octets = 0
    for character in line:
        width = len(character.encode("utf-8"))
        if current and octets + width > max_octets:
            physical.append(current)
            current = " "  # The continuation whitespace is part of the 75-octet line.
            octets = 1
        current += character
        octets += width
    physical.append(current)
    return physical


def _date(value: Any) -> str | None:
    raw = str(value or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return None
    try:
        return dt.date.fromisoformat(raw).isoformat()
    except ValueError:
        return None


def event_uid(opportunity_key: str, anchor: str, policy_key: str, policy_version: str) -> str:
    # Version is event metadata, not identity: a policy revision must update
    # the same calendar component so downstream clients can replace/cancel it.
    # A delimiter-joined string can alias distinct tuples when a field contains
    # the delimiter. JSON array serialization preserves the typed boundaries.
    basis = json.dumps(
        [opportunity_key, anchor, policy_key],
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32] + "@chhhs-rims"


def project_event(
    opportunity: dict[str, Any], policy: dict[str, Any], *, as_of: str
) -> dict[str, Any] | None:
    """Project one opportunity to an all-day event, or return None if uncertain."""
    if not validate_policy(policy):
        raise ValueError("invalid institutional policy")
    as_of_date = _date(as_of)
    if as_of_date is None:
        raise ValueError("as_of must be a real YYYY-MM-DD date")
    policy_status = institutional_policy_status(policy, as_of_date)
    if policy_status == "invalid":
        raise ValueError("invalid institutional policy evaluation date")
    if policy_status != "current":
        return None
    if str(opportunity.get("ReviewStatus") or "").strip().casefold() != "reviewed":
        return None
    source_date = _date(opportunity.get("Deadline")) if opportunity.get("DeadlinePrecision") == "day" else None
    anchor = "institutional"
    event_date = institutional_deadline(
        source_date,
        policy["LeadDays"],
        business_days=policy["CalendarOrBusinessDays"] == "business",
        holidays=policy.get("HolidayDates", ()),
    ) if source_date is not None else None
    if event_date is None:
        return None
    if policy["CalendarOrBusinessDays"] == "business":
        coverage = policy["HolidayCoverage"]
        if event_date < coverage["CoverageStart"] or source_date > coverage["CoverageEnd"]:
            return None
    status = str(opportunity.get("Status") or "Unknown")
    cancelled = (opportunity.get("Cancelled") is True
                 or status.strip().casefold() in {"cancelled", "canceled", "withdrawn"})
    event_status = "CANCELLED" if cancelled else "TENTATIVE"
    return {
        "UID": event_uid(str(opportunity["OpportunityKey"]), anchor, str(policy["PolicyKey"]), str(policy["Version"])),
        "Date": event_date,
        "Status": event_status,
        "Anchor": anchor,
        "Title": str(opportunity.get("Title") or "Grant opportunity"),
        "URL": str(opportunity.get("URL") or ""),
        "Source": str(opportunity.get("Source") or ""),
        "OpportunityKey": str(opportunity["OpportunityKey"]),
        "PolicyKey": str(policy["PolicyKey"]),
        "PolicyVersion": str(policy["Version"]),
        "PolicyEvidenceStatus": "provisional",
        "ExternalDeadline": source_date,
    }


def build_icalendar(opportunities: Iterable[dict[str, Any]], policy: dict[str, Any], *, generated_utc: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", generated_utc):
        raise ValueError("generated_utc must be second-precision UTC")
    try:
        dt.datetime.strptime(generated_utc, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("generated_utc must be a real second-precision UTC timestamp") from exc
    rows = list(opportunities)
    reviewed_keys = [str(row.get("OpportunityKey") or "").strip()
                     for row in rows
                     if str(row.get("ReviewStatus") or "").strip().casefold() == "reviewed"]
    if any(not key for key in reviewed_keys) or len(reviewed_keys) != len(set(reviewed_keys)):
        raise ValueError("reviewed opportunities must have unique non-empty OpportunityKey values")
    as_of = generated_utc[:10]
    events = [project_event(item, policy, as_of=as_of) for item in rows]
    events = sorted((item for item in events if item is not None), key=lambda item: (item["Date"], item["UID"]))
    dtstamp = generated_utc.replace("-", "").replace(":", "")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//CHHHS RIMS//Grant Calendar//EN", "CALSCALE:GREGORIAN"]
    for event in events:
        next_day = (dt.date.fromisoformat(event["Date"]) + dt.timedelta(days=1)).strftime("%Y%m%d")
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{event['UID']}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART;VALUE=DATE:{event['Date'].replace('-', '')}",
            f"DTEND;VALUE=DATE:{next_day}",
            f"SUMMARY:{_escape(event['Title'])}",
            f"STATUS:{event['Status']}",
            f"CATEGORIES:{_escape(event['Source']) or 'Grant'}",
            f"DESCRIPTION:{_escape('PROVISIONAL institutional planning date; confirm approved policy and holiday coverage. OpportunityKey: ' + event['OpportunityKey'])}",
            f"URL:{_escape(event['URL'])}",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(physical for line in lines for physical in _fold_content_line(line)) + "\r\n"


def build_native_calendar_export(rows: Iterable[dict[str, Any]], *, generated_utc: str) -> str:
    """One-time private export of committed reviewed native calendar days.

    No institutional offset is calculated. The native DateTime field is never
    used to infer a day. UID follows DeadlineKey; native item version provides
    monotonic SEQUENCE for changed/cancelled snapshots of that same item.
    """
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', generated_utc):
        raise ValueError('second-precision UTC capture time required')
    dt.datetime.strptime(generated_utc, '%Y-%m-%dT%H:%M:%SZ')
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//CHHHS RIMS//Reviewed Calendar Snapshot//EN','CALSCALE:GREGORIAN']
    rows = list(rows)
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError('native calendar rows must be objects')
    seen=set()
    for row in sorted(rows,key=lambda r:str(r.get('DeadlineKey',''))):
        if row.get('ReviewStatus')!='Reviewed' or row.get('RevisionApplied') is not True:
            continue
        key=row.get('DeadlineKey')
        if not isinstance(key,str) or not key or key!=key.strip() or key in seen:
            raise ValueError('unique exact native DeadlineKey required')
        seen.add(key)
        if type(row.get('Cancelled')) is not bool:
            raise ValueError('explicit cancellation state required')
        if row.get('DeadlinePrecision')!='day':
            continue
        day=_date(row.get('Calendar_x0020_day'))
        if day is None:
            raise ValueError('exact source calendar day required; UTC DateTime is not a fallback')
        if ('odata.etag' in row and '@odata.etag' in row
                and row['odata.etag'] != row['@odata.etag']):
            raise ValueError('conflicting native item-version ETags')
        version=re.fullmatch(r'"([1-9]\d*)"',str(row.get('odata.etag') or row.get('@odata.etag') or ''))
        if not version:
            raise ValueError('native JSON item-version ETag required')
        source=row.get('SourceURL');source=source.get('Url') if isinstance(source,dict) else source
        if not isinstance(source,str) or source != source.strip() or any(ord(c)<32 for c in source):
            raise ValueError('safe source URL required')
        url=urlsplit(source)
        if url.scheme!='https' or not url.hostname or url.username or url.password or url.port==0:
            raise ValueError('attributable HTTPS source required')
        title=row.get('Title')
        if not isinstance(title,str) or not title.strip():
            raise ValueError('source title required')
        uid=event_uid(key,'source-calendar-day','native-reviewed-calendar','1')
        end=(dt.date.fromisoformat(day)+dt.timedelta(days=1)).strftime('%Y%m%d')
        # Outlook file import can ignore STATUS:CANCELLED in its display.
        # Keep cancellation unmistakable and grant dates out of free/busy time.
        lines.extend(['BEGIN:VEVENT',f'UID:{uid}',f'SEQUENCE:{int(version[1])}',
            'DTSTAMP:'+generated_utc.replace('-','').replace(':',''),
            'DTSTART;VALUE=DATE:'+day.replace('-',''),'DTEND;VALUE=DATE:'+end,
            'CLASS:PRIVATE','TRANSP:TRANSPARENT',
            'SUMMARY:'+_escape(('CANCELLED: ' if row['Cancelled'] else '')+title),
            'STATUS:'+('CANCELLED' if row['Cancelled'] else 'TENTATIVE'),
            'DESCRIPTION:'+_escape('One-time reviewed source-date snapshot. Confirm the source before acting. DeadlineKey: '+key),
            'URL:'+source,'END:VEVENT'])
    lines.append('END:VCALENDAR')
    return '\r\n'.join(part for line in lines for part in _fold_content_line(line))+'\r\n'


def write_native_calendar_export(out: Path, output: str) -> None:
    """Create a new private snapshot; never replace a prior export or human edit."""
    target = out.absolute()
    parent = target.parent.resolve(strict=True)
    private_root = _ROOT / 'private' / 'ops'
    if target.is_symlink() or parent != target.parent or not parent.is_relative_to(private_root):
        raise ValueError('existing private/ops directory without symlink redirection required')
    subprocess.run(['git', 'check-ignore', '-q', '--', str(target)], cwd=_ROOT,
                   check=True, capture_output=True)
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
        stream.write(output)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("opportunities", type=Path, help="JSON array of canonical opportunity rows")
    parser.add_argument("policy", type=Path, nargs="?", help="versioned institutional date policy JSON")
    parser.add_argument("--native-calendar", action="store_true", help="one-time committed reviewed source-day export; no institutional calculation")
    parser.add_argument("--generated-utc", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(args.opportunities.read_text())
    if args.native_calendar:
        if args.policy is not None:
            parser.error("native calendar export does not take an institutional policy")
        output = build_native_calendar_export(rows, generated_utc=args.generated_utc)
    else:
        if args.policy is None:
            parser.error("institutional projection requires a policy")
        output = build_icalendar(rows, json.loads(args.policy.read_text()), generated_utc=args.generated_utc)
    if args.native_calendar:
        write_native_calendar_export(args.out, output)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8", newline="")


if __name__ == "__main__":
    main()
