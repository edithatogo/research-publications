"""E09 Phase 2 no-send post content and thread mapping (local preparation).

Renders the readable first-discovery post content for one selected thread
candidate, as local preparation for the later cloud-flow authoring. The module
is deliberately narrow:

* content is composed only from fields the committed selection module produced
  (`scripts/e09_first_discovery.py`) plus the documented registry ``Title``
  field (`docs/SHAREPOINT_LIST_REGISTRY.md`); every other input field fails
  closed. This prevents extra-field copying; sensitive text inside an allowed
  title still requires source qualification;
* excluded (``rejected`` tier) candidates never receive post content;
* thread identity reuses ``scripts.e09_feed_contracts.stable_thread_id``
  (``thread:{registry SourceKey}``) — no new key family and no recomputation;
* the rendered text is deterministic and contains no generated timestamp:
  identical inputs render identical content, so interrupted or repeated runs
  reconcile byte-for-byte with a stored postimage;
* nothing is sent, posted or persisted by this module; an actual Teams post
  stays behind the recorded delivery-authority boundary and the Phase 1
  message-route gap (`ChannelMessage.Read.All` denied 2026-10-23).
"""

from __future__ import annotations

import html
import re
from typing import Any

from scripts.e09_feed_contracts import _required_text, stable_thread_id, _full_iso_date, publication_source_key
from scripts.e09_first_discovery import _canonical_key, STATUS_TIERS

TIER_WORDING = {
    "confirmed": "A CHHHS research publication",
    "possible": "A possible CHHHS research publication (needs review)",
}

RECORD_FIELDS = {
    "publication_key", "canonical_key", "tier", "review_status",
    "discovered_on", "suggested_trigger",
}
OPTIONAL_FIELDS = {"Title", "PublicationMonth"}

POST_BODY_FIELDS = {"thread_id", "subject", "body", "plain_text"}


def _no_send_record(record: Any) -> dict[str, Any]:
    """Fail-closed parse of one selection record plus the registry Title."""
    if not isinstance(record, dict):
        raise ValueError("post record must be an object")
    unknown = set(record) - RECORD_FIELDS - OPTIONAL_FIELDS
    if unknown:
        raise ValueError(f"post record has fields outside the no-send allowlist: {sorted(unknown)}")
    missing = RECORD_FIELDS - set(record)
    if missing:
        raise ValueError(f"post record is missing selection fields: {sorted(missing)}")
    if record["tier"] == "rejected":
        raise ValueError("excluded (rejected) records never open threads or receive post content")
    if not isinstance(record["tier"], str) or record["tier"] not in TIER_WORDING:
        raise ValueError(f"tier {record['tier']!r} has no approved wording")
    if not isinstance(record['review_status'], str) or STATUS_TIERS.get(record['review_status']) != record['tier']:
        raise ValueError('Review status and tier disagree')
    _canonical_key(record['canonical_key'])
    _full_iso_date(record['discovered_on'], 'discovered_on')
    suggested_trigger = record["suggested_trigger"]
    if not isinstance(suggested_trigger, str) or suggested_trigger not in {"first_discovery", "catch_up"}:
        raise ValueError("suggested_trigger must be 'first_discovery' or 'catch_up' from the selection module")
    title = record.get("Title")
    title = _required_text(title, "Title") if title is not None else None
    publication_month = record.get("PublicationMonth")
    if publication_month is not None:
        publication_month = _required_text(publication_month, "PublicationMonth")
        if not re.fullmatch(r'[0-9]{4}-(?:0[1-9]|1[0-2])', publication_month):
            raise ValueError('PublicationMonth must be a qualified YYYY-MM value')
    return {
        "publication_key": publication_source_key(record["publication_key"]),
        "canonical_key": _required_text(record["canonical_key"], "canonical_key"),
        "tier": record["tier"],
        "review_status": _required_text(record["review_status"], "review_status"),
        "discovered_on": _required_text(record["discovered_on"], "discovered_on"),
        "suggested_trigger": suggested_trigger,
        "Title": title,
        "PublicationMonth": publication_month,
    }


def render_post_body(record: Any) -> dict[str, Any]:
    """Render one deterministic, replay-stable no-send post body.

    Returns the derived thread identity, the Graph chatMessage-shaped HTML body,
    and a plain-text rendering of the same lines. Raises on excluded records and
    any field outside the selection/registry allowlist.
    """
    parsed = _no_send_record(record)
    thread_id = stable_thread_id(parsed["publication_key"])
    heading = parsed["Title"] if parsed["Title"] else parsed["canonical_key"]
    opening = TIER_WORDING[parsed["tier"]]

    lines = [
        opening,
        heading,
    ]
    lines.append(f"First observed in the Publication Registry: {parsed['discovered_on']} (UTC register processing first-seen)")
    lines.append(f"Source key: {parsed['publication_key']}")
    lines.append(f"Canonical key: {parsed['canonical_key']}")
    if parsed["PublicationMonth"]:
        lines.append(f"Publication month (verified): {parsed['PublicationMonth']}")
    trigger_note = "Selected in catch-up backfill" if parsed["suggested_trigger"] == "catch_up" else "First discovery"
    lines.append(f"{trigger_note}; publication tier: {parsed['review_status']}")
    lines.append(
        "The Publication Registry remains the record; this thread is an additive "
        "surface for evidence-backed contributions resolved by curators. Do not post "
        "clinical, personal or sensitive research data."
    )

    plain = "\n".join(lines)
    html_lines = [
        html.escape(line, quote=False) for line in lines[:-1]
    ] + [
        "<em>" + html.escape(lines[-1], quote=False) + "</em>",
    ]
    html_content = "".join(f"<p>{line}</p>" for line in html_lines)
    return {
        "thread_id": thread_id,
        "subject": heading,
        "body": {"contentType": "html", "content": html_content},
        "plain_text": plain,
    }
