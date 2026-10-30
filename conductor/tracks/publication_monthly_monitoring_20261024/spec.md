> Reconciled 29 October 2026 from the retained authoring checkout. Dated
> observations below are historical evidence, not refreshed native state.
> Selection follows [completion scope](../../../docs/CURRENT_MISSING_OUTCOMES.md#completion-scope--29-october-2026); optional residuals stay on the roadmap;
> prior bounded acceptance remains valid only for its stated scope.
> Current ownership and authority: [CURRENT_STATE](../../../handoff/CURRENT_STATE.md).
> Cancelled Desktop/Windows routes stay excluded; no new sends or schedules.

# Specification — Publication monthly follow-up and monitoring

## Purpose

Remove the two future monthly observations from the current publication closeout
scope while preserving their evidence requirements in a dedicated track. Direct
user authority: 24 October 2026, close each item and create a separate follow-up/
monitoring track. E08-F01/F02 are closed by transfer only; neither natural occurrence
is marked passed. Other E08 work and parallel implementation remain untouched.

## Current timing adjustment — 31 October 2026

User-authorised timings from 1 November, all Australia/Brisbane: the existing
exporter runs at **07:00 on day 1 monthly**, the independent observer at **07:45
daily**, and the existing one-time app verification at **07:50 on 1 November**.
Final native schedule readback is accepted in [CURRENT_STATE](../../../handoff/CURRENT_STATE.md).
These times supersede the original timing below; the evidence requirements and
no-run/no-send review boundary remain. Schedule configuration is not proof of a
natural occurrence. The explicit noon delivery deadline remains unchanged; absence at 07:50 is
pending, not a proven missed delivery.

## Original scope and timing — historical

- PM-F01 (formerly E08-F01): first natural monthly publication export on
  1 November 2026, scheduled 09:00 Australia/Brisbane, completion deadline noon.
  Earliest export-only review: 12:00 Brisbane.
- PM-F02 (formerly E08-F02): independent observer occurrence on 1 November 2026,
  eligible after 12:05 Australia/Brisbane. Combined review starts after 12:05.

Use the existing accepted configuration, commissioning and activation receipts in
ignored `private/ops/2026-10-20-consumers-unattended/`:
`final-schedule-audit.json`, `monitor-activation-acceptance.json`,
`monitor-commissioning-acceptance.json` and `monitor-solution-acceptance.json`.
Resolve exact targets through those existing private records; do not publish IDs,
authentication material, raw outputs or screenshots in tracked documents.

## Execution constraints

CLI-first using existing qualified authentication and supported read-only run
history and SharePoint file/list routes. No premium connector, Copilot, new
connection, consent, licence, cloud resource, sharing change or alternative sender.
If CLI cannot retrieve a required fact, use the supported ordinary web UI for that
specific readback when it is available under existing access; record any remaining
access/evidence gap without bypassing it. Local file/key/hash comparisons use the
explicit repo-local Python 3.15.1 environment (or newer qualified 3.15 patch).

Reuse the existing export and independent observer. Do not create/activate a new
flow, reminder, monitor or schedule, change cadence, resubmit a run, or send email.
Do not poll before eligibility or disturb parallel writers/authentication. The
existing one-time app verification is the sole follow-up; create no duplicate.

## Acceptance and failure handling

PM-F01 requires actual natural trigger-origin and terminal-run evidence, exact
period/generation correlation, complete output/CSV/index/parts/manifest, reconciled
publication counts and key sets, source/query/refresh lineage, existing access and
preserved history/human edits. An enabled schedule or successful manual run alone
is insufficient. Keep unknown-date/source limits explicit.

PM-F02 requires the existing observer's natural trigger and stored result, exact
correlation to PM-F01's intended occurrence, and evidence supporting its healthy,
missing or failed classification. Reuse accepted commissioning evidence for other
branches; do not inject failures or rerun the exporter to test the observer.

Each task closes after a reconciled observation and explicit pass/failure
handover. A failed export cannot be labelled healthy; an observer can correctly
report a failed export. Missing, inaccessible or ambiguous evidence remains pending
with its exact gap. Any discovered implementation defect returns to the existing
owner and does not authorise a second native writer or duplicate send.

## Out of scope

Parallel source/reconciliation/model/reader/digest/grants implementation; broader
E08 source histories and longitudinal windows; production/business acceptance;
new distribution authority; template/output migration or a new document runtime.
