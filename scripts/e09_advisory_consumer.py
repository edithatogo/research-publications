# SPDX-License-Identifier: Apache-2.0
"""E09 Phase 4 advisory suggestions — local bounded consumer (no AI route).

Local preparation for the later evidence-linked advisory extraction: this
module owns the bounded schema for advisory outputs and the fail-closed
consumer that accepts or falls back. It never calls a model. A qualified
advisory AI route is a separate, later qualification gate named in the track
plan; this consumer only validates what that route would eventually produce
and keeps manual operation the fallback.

Semantics encoded here, fail-closed:

* bounded schema: advisory outputs carry at most 20 evidence URLs and 20
  suggested keywords, all evidence via HTTPS, exact fields only — nothing
  broader can enter, so an unqualified model output cannot smuggle extra
  fields into the feed;
* revision binding: every advisory output must name the source revision and
  prompt revision it was generated against; a mismatch against the expected
  revisions is a recorded ``stale_advisory`` fallback, never a silent accept;
* invalid output and AI outage fall back to an explicit failure record with
  ``manual_operation_required`` true — malformed output cannot become a
  suggestion, and no automatic retry loop is implied;
* valid suggestions stay advisory-only and structurally ``authoritative ==
  false``, exactly like contributions: model output never becomes a record by
  itself; a curator decision record remains the only route that can raise
  authority. This module holds no write path at all;
* thread identity reuses ``stable_thread_id`` — the additive
  ``thread:{registry SourceKey}`` convention, no new key family.

Unsafe text handling: this consumer never echoes hostile text into structured
fields — payloads contain links, keywords and identifiers validated shape-wise;
records contain no free narration beyond the explicit failure-detail text.
"""

from __future__ import annotations

from typing import Any

from scripts.e09_feed_contracts import (
    _full_iso_date,
    _positive_int,
    _required_identifier,
    _required_text,
    _string_list,
    publication_source_key,
    stable_thread_id,
)

ADVISORY_KIND = "evidence_linked_suggestion"
MAX_EVIDENCE_URLS = 20
MAX_KEYWORDS = 20

ADVISORY_FIELDS = {
    "advisory_id", "publication_key", "thread_id", "advisory_kind",
    "prompt_revision", "source_revision", "generated_on",
    "evidence_urls", "suggested_keywords", "authoritative",
}

FAILURE_FIELDS = {
    "advisory_id", "publication_key", "thread_id", "advisory_kind",
    "prompt_revision", "source_revision", "failure_on",
    "failure_reason", "failure_detail", "manual_operation_required",
    "authoritative",
}

FAILURE_REASONS = {"invalid_output", "ai_outage", "stale_advisory", "source_unavailable"}


def _thread_identity(record: dict[str, Any], context: str) -> tuple[str, str]:
    publication_key = publication_source_key(record["publication_key"], f"{context} publication_key")
    thread_id = _required_identifier(record.get("thread_id"), "thread_id")
    if thread_id != stable_thread_id(publication_key):
        raise ValueError("thread_id must derive exactly from publication_key")
    return publication_key, thread_id


def validate_advisory_suggestion(record: Any) -> dict[str, Any]:
    """Validate one advisory output against the bounded local schema."""
    if not isinstance(record, dict):
        raise ValueError("advisory suggestion must be an object")
    if any(not isinstance(key, str) for key in record):
        raise ValueError("advisory suggestion field names must be text")
    unknown = set(record) - ADVISORY_FIELDS
    if unknown:
        raise ValueError(f"advisory suggestion has fields outside the bounded schema: {sorted(unknown)}")
    missing = ADVISORY_FIELDS - set(record)
    if missing:
        raise ValueError(f"advisory suggestion is missing required fields: {sorted(missing)}")
    advisory_id = _required_identifier(record["advisory_id"], "advisory_id")
    publication_key, thread_id = _thread_identity(record, "advisory suggestion")
    kind = record.get("advisory_kind", ADVISORY_KIND)
    if kind != ADVISORY_KIND:
        raise ValueError(f"advisory_kind must be {ADVISORY_KIND!r}")
    prompt_revision = _positive_int(record["prompt_revision"], "prompt_revision")
    source_revision = _positive_int(record["source_revision"], "source_revision")
    generated_on = _full_iso_date(record["generated_on"], "generated_on")
    evidence_urls = _string_list(record["evidence_urls"], "evidence_urls")
    if not evidence_urls:
        raise ValueError("advisory suggestions must be evidence-linked (at least one HTTPS evidence URL)")
    if len(evidence_urls) > MAX_EVIDENCE_URLS:
        raise ValueError(f"advisory suggestions are bounded to {MAX_EVIDENCE_URLS} evidence URLs")
    for index, url in enumerate(evidence_urls):
        if not url.startswith("https://"):
            raise ValueError(f"evidence_urls[{index}] must use HTTPS")
    keywords = _string_list(record["suggested_keywords"], "suggested_keywords")
    if len(keywords) > MAX_KEYWORDS:
        raise ValueError(f"advisory suggestions are bounded to {MAX_KEYWORDS} suggested keywords")
    for index, keyword in enumerate(keywords):
        if not keyword.strip():
            raise ValueError(f"suggested_keywords[{index}] must be non-empty")
    if _boolean_strict(record.get("authoritative")) is not False:
        raise ValueError("authoritative must be false; advisory output never becomes a record by itself")
    return {
        "advisory_id": advisory_id,
        "publication_key": publication_key,
        "thread_id": thread_id,
        "advisory_kind": kind,
        "prompt_revision": prompt_revision,
        "source_revision": source_revision,
        "generated_on": generated_on.isoformat(),
        "evidence_urls": evidence_urls,
        "suggested_keywords": keywords,
        "authoritative": False,
    }


def record_advisory_failure(record: Any) -> dict[str, Any]:
    """Validate one explicit fallback record for a failed or unqualified advisory attempt."""
    if not isinstance(record, dict):
        raise ValueError("advisory failure must be an object")
    if any(not isinstance(key, str) for key in record):
        raise ValueError("advisory failure field names must be text")
    unknown = set(record) - FAILURE_FIELDS
    if unknown:
        raise ValueError(f"advisory failure has fields outside the bounded schema: {sorted(unknown)}")
    missing = FAILURE_FIELDS - set(record)
    if missing:
        raise ValueError(f"advisory failure is missing required fields: {sorted(missing)}")
    advisory_id = _required_identifier(record["advisory_id"], "advisory_id")
    publication_key, thread_id = _thread_identity(record, "advisory failure")
    kind = record.get("advisory_kind", ADVISORY_KIND)
    if kind != ADVISORY_KIND:
        raise ValueError(f"advisory_kind must be {ADVISORY_KIND!r}")
    prompt_revision = record.get("prompt_revision")
    if prompt_revision is not None:
        prompt_revision = _positive_int(prompt_revision, "prompt_revision")
    source_revision = record.get("source_revision")
    if source_revision is not None:
        source_revision = _positive_int(source_revision, "source_revision")
    reason = _required_identifier(record["failure_reason"], "failure_reason")
    if reason not in FAILURE_REASONS:
        raise ValueError(f"failure_reason must be one of {sorted(FAILURE_REASONS)}")
    _required_text(record["failure_detail"], "failure_detail")
    _full_iso_date(record["failure_on"], "failure_on")
    if _boolean_strict(record.get("manual_operation_required")) is not True:
        raise ValueError("manual_operation_required must be true; fallback keeps manual operation")
    if _boolean_strict(record.get("authoritative")) is not False:
        raise ValueError("authoritative must be false on advisory failures")
    return {
        "advisory_id": advisory_id,
        "publication_key": publication_key,
        "thread_id": thread_id,
        "advisory_kind": kind,
        "prompt_revision": prompt_revision,
        "source_revision": source_revision,
        "failure_on": record["failure_on"],
        "failure_reason": reason,
        "failure_detail": record["failure_detail"],
        "manual_operation_required": True,
        "authoritative": False,
    }


def _boolean_strict(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise ValueError("boolean fields must be real booleans")


def consume_advisory_output(
    payload: Any,
    *,
    expected_prompt_revision: int,
    expected_source_revision: int,
    advisory_id: str,
    publication_key: str,
    failure_on: str,
) -> dict[str, Any]:
    """Accept or fall back for one advisory output against expected revisions.

    ``payload`` must already satisfy the bounded advisory schema fields (the
    caller may pre-annotate outage/supplier failures as a failure record with
    ``failure_reason`` set). Returns:

    * ``{"outcome": "advisory_only", ...}`` when the payload is a valid
      suggestion bound to the expected revisions — it keeps ``authoritative``
      false and requires a downstream curator decision, so manual operation
      is retained in every path;
    * ``{"outcome": "fallback_manual", ...}`` with a validated failure record
      otherwise (malformed payload, or revision/request identity mismatch).

    Invalid caller identities, revisions or fallback dates raise ValueError before
    consuming output. Supplied failures are also bound to the current request;
    null outage revisions remain unknown. Invalid supplier text is not copied
    into generated fallback diagnostics.
    """
    identity_seed = {
        "publication_key": publication_source_key(publication_key, "publication_key"),
    }
    # Caller controls must be valid even when the supplied result is an outage
    # or success; they are not facts inferred from supplier/model output.
    advisory_id = _required_identifier(advisory_id, "advisory_id")
    _full_iso_date(failure_on, "failure_on")
    expected_prompt_revision = _positive_int(expected_prompt_revision, "expected_prompt_revision")
    expected_source_revision = _positive_int(expected_source_revision, "expected_source_revision")

    def failure(reason: str, detail: str, prompt_revision: int | None,
                source_revision: int | None) -> dict[str, Any]:
        return record_advisory_failure({
            "advisory_id": advisory_id,
            "publication_key": identity_seed["publication_key"],
            "thread_id": stable_thread_id(identity_seed["publication_key"]),
            "advisory_kind": ADVISORY_KIND,
            "prompt_revision": prompt_revision,
            "source_revision": source_revision,
            "failure_on": failure_on,
            "failure_reason": reason,
            "failure_detail": detail,
            "manual_operation_required": True,
            "authoritative": False,
        })

    if not isinstance(payload, dict) or payload.get("failure_reason") is not None:
        if isinstance(payload, dict) and payload.get("failure_reason") is not None:
            try:
                parsed_failure = record_advisory_failure(payload)
            except ValueError:
                return {"outcome": "fallback_manual", "record": failure(
                    "invalid_output", "Invalid supplied failure record; manual operation retained",
                    expected_prompt_revision, expected_source_revision)}
            if (parsed_failure["publication_key"] != identity_seed["publication_key"]
                    or parsed_failure["advisory_id"] != advisory_id
                    or any(parsed_failure[field] is not None and parsed_failure[field] != expected
                           for field, expected in (("prompt_revision", expected_prompt_revision),
                                                   ("source_revision", expected_source_revision)))):
                return {"outcome": "fallback_manual", "record": failure(
                    "stale_advisory", "Supplied failure identity/revision differs from current request",
                    expected_prompt_revision, expected_source_revision)}
            return {"outcome": "fallback_manual", "record": parsed_failure}
        return {
            "outcome": "fallback_manual",
            "record": failure(
                "invalid_output",
                "advisory payload was not a structured bounded-schema suggestion",
                None, None,
            ),
        }

    try:
        parsed = validate_advisory_suggestion(payload)
    except ValueError:
        return {
            "outcome": "fallback_manual",
            "record": failure(
                "invalid_output",
                "Advisory payload failed the bounded schema; manual operation retained",
                _safe_revision(payload.get("prompt_revision")),
                _safe_revision(payload.get("source_revision")),
            ),
        }

    if parsed["prompt_revision"] != expected_prompt_revision:
        return {
            "outcome": "fallback_manual",
            "record": failure(
                "stale_advisory",
                f"prompt_revision {parsed['prompt_revision']} does not match expected {expected_prompt_revision}",
                parsed["prompt_revision"], parsed["source_revision"],
            ),
        }
    if parsed["source_revision"] != expected_source_revision:
        return {
            "outcome": "fallback_manual",
            "record": failure(
                "stale_advisory",
                f"source_revision {parsed['source_revision']} does not match expected {expected_source_revision}",
                parsed["prompt_revision"], parsed["source_revision"],
            ),
        }
    if (parsed["publication_key"] != identity_seed["publication_key"]
            or parsed["advisory_id"] != advisory_id):
        return {
            "outcome": "fallback_manual",
            "record": failure(
                "stale_advisory",
                "advisory payload names a different publication or advisory request",
                parsed["prompt_revision"], parsed["source_revision"],
            ),
        }
    return {
        "outcome": "advisory_only",
        "record": parsed,
        "curator_decision_required": True,
        "manual_operation_required": True,
    }


def _safe_revision(value: Any) -> int | None:
    try:
        return _positive_int(value, "revision") if value is not None else None
    except ValueError:
        return None
