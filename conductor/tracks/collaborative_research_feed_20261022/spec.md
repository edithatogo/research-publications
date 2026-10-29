> Reconciled 29 October 2026 from the retained authoring checkout. Dated
> observations below are historical evidence, not refreshed native state.
> Selection follows [completion scope](../../../docs/CURRENT_MISSING_OUTCOMES.md#completion-scope--29-october-2026); optional residuals stay on the roadmap;
> prior bounded acceptance remains valid only for its stated scope.
> Current ownership and authority: [CURRENT_STATE](../../../handoff/CURRENT_STATE.md).
> Cancelled Desktop/Windows routes stay excluded; no new sends or schedules.

# Specification — Collaborative research feed and enrichment

## Overview

Make new research visible while allowing colleagues to improve CHHHS matching and
attribution continuously. Reuse the retained source layer, authoritative register,
existing reconciliation software and Power Automate. Teams is a collaboration
surface; structured records retain accepted data and decision history.

## Feed requirements

- Create one persistent thread in the existing Research channel for each newly
  discovered confirmed or possible CHHHS publication; exclude rejected candidates
  from new posts. Possible status must be visibly distinct from confirmed.
- Determine newness from first discovery by RIMS, separately from publication date.
  Late-discovered older papers and unknown/imprecise dates remain eligible.
- Use committed source/candidate records and stable identity, including plausible
  candidates outside the accepted canonical set. Do not inflate accepted totals.
- Include citation, authors, publication date/uncertainty, source links, current
  CHHHS status, attribution and a structured contribution link.
- Baseline existing records at activation; no historical posting burst. Make the
  backlog available through an existing or additive review view.
- Retain stable publication/message mappings, source revision and delivery receipts.
  Replay must not duplicate posts; reconcile uncertain delivery before retry.
- Preserve discussion and corrections. Update the same thread after classification
  changes; retain references/history when a duplicate is resolved or a match rejected.
- No channel digest by default. Colleagues control native Teams thread/channel
  notifications; do not force subscriptions or duplicate those controls.

## Contributions and curation

- Link each post to a web-accessible SharePoint structured contribution form.
  Discussion replies alone do not automatically mutate accepted dataset fields.
- Collect proposed CHHHS / not CHHHS / uncertain status, specific author attribution,
  department/division/area, supporting source/evidence and rationale.
- Reuse existing organisation keys, hierarchy versions and effective dates. Support
  multiple authors/areas and unknown values; do not assign every coauthor to CHHHS.
- Record authenticated contributor, time, target identity/source revision and proposed
  change. Preserve original source values and conflicting contributions.
- Designated curators accept, amend, reject or leave unresolved. Apply changes only
  through the existing authorised revision-checked update path; stale submissions
  require reconciliation, not last-writer overwrite. Preserve decision history.
- Intake remains automatic. Silence does not confirm membership, block ingestion
  or create a mandatory per-publication approval queue.

## Advisory extraction

Suggest topics, study design, population, locations, affiliations and explicitly
stated trial/grant identifiers from retained metadata/abstracts. Include supporting
excerpts, evidence references, source fingerprint and prompt/version provenance.
Keep source-stated facts, inferred suggestions and human decisions distinguishable.
Reuse the qualified existing advisory AI route only; unavailable/invalid AI must
leave deterministic posting and manual enrichment working. Do not infer person,
organisation, project or award identity from titles/names or shared numeric suffixes.
No automatic model training, unsupported full-text acquisition or new external AI
upload is included.

## Optional digest subscription

- Separate opt-in newly-discovered-research emails from channel discussion and the
  existing publication-date-based editorial digest. Preserve the existing digest's
  selection, freshness, summary validation and delivery authority boundaries.
- Reuse supported existing rendering/delivery components with a distinct edition
  kind. Include thread links, clear confirmed/possible status and source links.
- Offer daily, weekly or off; default weekly. Weekly is Monday 08:00 and daily is
  08:00, Australia/Brisbane. Keep cadence/time configurable without definition edits.
- Use completed first-discovery windows, beginning no earlier than opt-in, with
  idempotent subscriber/edition receipts. Suppress empty editions. Respect opt-out
  before dispatch and existing reader/channel access; no default recipient enrolment.

## Acceptance criteria

Actual web-reader, contribution and curator journeys work on qualified existing
resources. Committed identities, accepted data, source evidence and human edits
are preserved. Duplicate/replay, uncertain delivery, stale/concurrent edits,
permissions, unsubscribing and optional-AI failure are verified. Saved definitions,
runtime results, output/record readback and canonical solution membership have
separate evidence. Documentation is versioned by its existing publisher or handed
off explicitly as pending. Later natural occurrence/adoption evidence belongs to E08.

## Boundaries

Microsoft-hosted runtime and cross-platform web use only. No new collector,
mandatory model/report change, auth client, permissions, licence or channel/site
creation. Reuse the privately recorded exact Research target after fresh readback.
If posting cannot be qualified, retain the SharePoint feed and record the precise
gap; do not silently substitute another destination. No grant/project crosswalk is
invented. Track creation grants no send, activation, sharing or rollout authority.

## Bounded technical delivery note — 25 October 2026

The requirements above remain the broader product target. The current E09
technical track closes against the narrower owner-operated, no-send mode defined
in its [implementation plan](plan.md#bounded-technical-completion-amendment--25-october-2026):
committed-input selection, owner-only contribution/preferences/editions, local
manual curator and advisory fallbacks, deterministic previews, bounded recovery,
and explicit local handoffs. Cross-user self-service, canonical curator writes,
real Teams messages, provider AI, email, schedules, solution membership and native
SharePoint/Loop publication remain separately gated future adoption work. This
note does not claim those product requirements are delivered or relax their
security and authority boundaries.
