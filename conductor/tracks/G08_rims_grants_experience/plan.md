# Implementation plan

## Live GrantConnect register and funding views — 1 November 2026

The retained public XML produced 120 distinct opportunities. The guarded Toolkit
writer created 120 Needs Review items in the existing Grants Registry. Power BI
processed only that register table. Native readback reconciled all 120 keys,
source IDs, titles, review states, evidence hashes and blank closing dates.
The existing report now shows opportunity details and calendar OpportunityKey.
The calendar relationship uses Funding Calendar.OpportunityKey (many) and
Grants Registry.OpportunityKey (one). Final live query returned 120 opportunities,
zero confirmed closing dates and zero GrantConnect calendar rows. Both pages
rendered in service preview. Publication dates and dates mentioned in descriptions
were not used as deadlines. This closes the retained snapshot path. Unattended
RSS acquisition remains open on the connector's provider HTTP403; NIH stays deferred.
Private receipts, inverses and journals: private/ops/grantconnect-browser-20261101/.


> Status reconciliation, 24 October 2026: consult
> [current missing outcomes](../../../docs/CURRENT_MISSING_OUTCOMES.md) before
> executing dated next steps or unchecked tasks below. Accepted scoped evidence
> supersedes only mapped outcomes; preserve historical detail and current owners.


## Execution choice and fallback — planning amendment, 23 October 2026

**G08 default:** Existing Invoker-bound flows/Lists web forms → semantic measures → PBIR Service reader.

**Skills:** Power Automate; semantic-model-authoring; powerbi-report-cli. Read the selected skill and installed help/schema at execution;
capability inventory is not authentication, permission or target qualification.

**Fallback / stopping boundary:** Optional app skills apply only to a demonstrated interaction gap; do not migrate platform or enable delivery to complete setup.

**Workflow and agent allocation:** Primary agent by default. Optional explicitly
scoped explorer, worker or independent review must retain disjoint ownership;
no delegation, installation or native effect is performed by this amendment.
Record preparation → saved readback → runtime → web acceptance separately in
existing receipts, with same-ID preimage, drift guard and scoped recovery.
Use the [shared capability guide](#cli-implementation-routes)
for conditional hosted MCP/Fabric IQ/ALM choices and current tool inventory.
Existing task markers, accepted evidence and ownership remain authoritative.



## CLI route selection gate — 23 October 2026

**G08 operation family:** Existing Invoker-bound flows and Lists forms; semantic-model-authoring; PBIR CLI.

**First bounded decision:** Qualify caller-specific persistence and access through the existing web journey before proposing any optional app tooling.

At execution, record the installed help/exposed schema and exact supported
operation in the existing private receipt before selecting a writer. The
[shared tool and evidence contract](#cli-implementation-routes#tool-selection-and-evidence-record--23-october-2026)
applies: available does not mean connected or target-qualified. Primary-agent
execution is the default; optional local delegation needs explicit scope and
existing authority. This is a plan amendment only; no implementation or status
change is made here.


## Execution dispatch contract — planning only, 23 October 2026

**Track G08; start:** `python3 scripts/agent_harness.py context --task grants`;
use `python3 scripts/agent_harness.py resume` instead for an in-flight operation.
This is a later execution instruction, not an implementation performed here.

**Selected path:** Existing Invoker-bound watchlist/calendar/ledger graphs + Lists persistence/security → semantic model/PBIR web reader.

**Dispatch:** Read this plan's track-specific CLI refinement and the
[capability selection contract](#cli-implementation-routes#tool-selection-and-evidence-record--23-october-2026).
Resolve exact private bindings and the current native owner before preparing the
smallest change. Use CLI help/MCP schemas to bind the operation; do not turn a
logical sequence into a guessed command or endpoint. Record tool/version/pin,
skill module, client/resource, input hash, same-object operation handle, saved
readback, representative web/runtime result and recovery pointer in existing
private evidence. A successful invocation alone does not complete this track.

**Capability choice at execution:** Prefer a useful supported newer capability only
when its exact version/schema, qualified client and target are recorded. If it
fails a required behaviour, retain the working route and name the precise gap;
do not add a tooling experiment as a completion prerequisite. The primary agent
implements or reviews by default; optional delegation requires explicit authority
and disjoint ownership. Record local preparation, native save/readback, runtime
outcome and web verification separately. This planning refresh starts none of them.

**Agents and verification:** Primary agent retains semantic and native decisions;
optional explorer/worker/reviewer assignments must have disjoint files and an
explicit handoff. No new chat or native writer is implied. Reuse accepted proof,
run affected checks and Conductor review, and return actual technical defects to
this track. Later due observations go to E08; adoption/cutover stay outside current
technical completion. All existing task statuses and object ownership are retained.


## CLI execution refinement — 23 October 2026

Planning update only; existing accepted increments, unfinished task markers and
native/file ownership remain authoritative. This section refines the 22 October
route; it does not authorise implementation in this planning turn.

**G08 mechanism:** Inspect current watchlist/calendar/subscription bindings → verify per-caller persistence and isolation → complete existing flow/list path → bind canonical semantic measures → PBIR web reader and edit/retry qualification.

**Selected tools and skills:** Existing Invoker-bound cloud flows and Lists web forms; semantic-model-authoring; powerbi-report-cli; optional Canvas/model/code-app skills only for a measured unmet need.

**Required proof / limits:** Opportunity dates and institutional dates stay distinct; protect subscriptions and private selections. No app-platform migration or delivery activation by default.

**Execution exit and cross-track handoff:** Use existing Lists/forms and Invoker-bound flow objects before proposing an app. Prove caller-specific edit/read/retry and privacy, authoritative date semantics and canonical model bindings, then the actual web watchlist/calendar journey. Notifications remain separately authorised.

**Workflow and agents:** Follow the [current capability guide](#cli-implementation-routes#planning-refresh--23-october-2026).
The primary agent owns semantics and native effects. A narrowly scoped explorer,
disjoint local worker or independent reviewer is optional only when delegation
is authorised and useful; specify exact files and never add a second native writer.
Read installed skill/help and exposed schema at execution time; pin any selected
new capability, preserve preimages, check exit code plus receipt before effects,
then reconcile the same run/LRO and complete saved readback. Unsupported optional
tooling uses the established supported route or a precise documented deferral.


## Current CLI/API implementation mechanism — 22 October 2026

**Planning only; implementation remains under the existing task statuses.**
This section takes precedence over conflicting historical tool/route wording;
accepted increments and current implementation receipts remain authoritative.
Follow the [shared capability, workflow and preview contract](#cli-implementation-routes).

**Owner / agents:** Existing grants list/flow/model/report owners by exact object. A disjoint local explorer/worker may prepare
source and a separate reviewer may inspect it; no second native writer.

**Tools / skills:** M365 CLI/REST Lists and Graph only if qualified; Power Automate build/debug; semantic-model-authoring; powerbi-report-cli; native Lists web forms first.

**Reuse:** scripts/prepare_watchlist_lifecycle.py; scripts/prepare_funding_calendar_lifecycle.py; scripts/prepare_funding_ledger_lifecycle.py; scripts/grants_calendar.py.

### Executable handoff contract — planning only, 22 October 2026

**Next implementation unit:** Prepare the existing Invoker-bound watchlist/calendar/ledger lifecycle graphs and Lists web interaction first; bind model and PBIR only after native persistence and user identity are proved.

**Start and discovery:** `python3 scripts/agent_harness.py context --task grants`
(or `resume` for an existing operation), then read the selected skill and installed
CLI help. Resolve targets from existing private S02 manifests. Obtain exact M365
syntax through `m365_search_commands` → `m365_get_command_docs`; inspect exposed
FlowAgent/Fabric schemas rather than inventing calls. The [shared capability guide](#cli-implementation-routes)
records available versus conditional tools and the common gated command sequence.
These are instructions for a later implementation run, not commands executed here.

**Evidence to retain:** Create/edit/remove, stale/concurrent and unauthorised actions, calendar update/cancel, pause/unsubscribe and replay; usable cross-platform web reader rather than empty page headers. Require both successful process exit and structured
receipt before any dependent effect. Preserve the same operation handle, capture
preimages, refuse drift and retain the smallest supported rollback. Run relevant
existing checks, then Conductor review; do not substitute local tests for native proof.

**Agent/workflow choice:** The primary agent owns semantics and the native action.
An explorer may answer one code question; a worker may prepare exact disjoint local
files; an independent reviewer may assess the resulting diff/evidence. Delegate
only when useful and authorised, with explicit ownership and no second native writer.
No agent or connector installation, authentication change, native implementation,
send, schedule, sharing or task completion is performed by this planning update.
### Tool selection decision — planning refinement, 22 October 2026

Lists web forms and existing Invoker-bound flows first; semantic-model-authoring and PBIR follow proven persistence/security. Canvas/code/model-app skills are conditional only for a demonstrated unmet interaction requirement.

Use the [capability qualification and agent rules](#cli-implementation-routes#execution-time-capability-qualification) before selecting a newer transport. Record the exact tool/version, operation schema, target scope, prepared input revision, owner and rollback in the existing private receipt. An unavailable optional tool does not block the established supported route. No additional installation or native action is part of this planning update.

<!-- execution-route-end -->

**Execution sequence for the next authorised implementation:**

1. Read fresh exact schemas/report parts and the existing prepared same-ID Invoker-bound lifecycle graphs. Do not use historical six/seven-page inventory as current state or a visible page as persistence proof.
2. Implement preference/watchlist/date/change/delivery-receipt persistence using server-derived caller identity and server-side per-user access enforcement; preserve ETag/revision, effective dates and policy provenance. Evaluate native Lists forms first, but require backing-service ownership plus revision/field enforcement. Hidden/read-only controls or an editable UserKey are not access enforcement; qualify actual two-user direct-read/write isolation and role-scoped curator access, including attempts that bypass the form. Retain a form only if it meets those requirements; no new app framework solely for styling.
3. Qualify create/edit/remove, stale/concurrent/unauthorised access, calendar update/cancel, pause/unsubscribe and ambiguous-attempt recovery. Bind the existing model/PBIR reader only after real persistence; use the bound model workspace for preview and verify the supported web journey.

**Acceptance / limits:** Existing page presence/local logic does not complete subscriptions or access control. Sending invitations/reminders or enabling recurrence needs its existing separate authority; do not change sharing.


## CLI delivery — 13 October 2026

Follow [the shared execution contract](../../workflow.md#cli-first-execution--13-october-2026).
G08-H01/H02/H04/H06 use qualified API/CLI additive persistence, date-policy and delivery-ledger/flow updates with exact saved schema/binding/access readback. Preserve approved personal access, subscription/cancellation and duplicate suppression semantics. G08-H03 report pages remain last with Power BI presentation. Complete backend prerequisites first; do not enable delivery or expand access from package import alone.


## Historical local implementation and dated native evidence

The checked items below retain prior work; they are not a current completion certificate. Later active tasks supersede contradictory status or fixture-cleanup claims. No unverified native gate is closed by this history.

- [x] Record scope and acceptance requirements.
- [x] Inspect current inputs, dependencies and relevant platform objects. BrowserOS readback confirms the native Funding Opportunities and Funding Calendar & Watchlist pages; their semantic-model binding remains pending.
- [x] Implement: Add local versioned policy validation and stable delivery-event idempotency keys for the future list-backed pages.
- [~] Verify: Local policy/subscription tests pass; native page persistence, per-user access, reminder ledger and calendar change/cancellation remain open.
- [x] Record local and live evidence separately before closure; no report page, subscription, notification or calendar was created.

## Local review extension — 2026-09-20

- [x] Add deterministic iCalendar projection with versioned institutional dates, stable event IDs, tentative review state and explicit cancellation semantics; cover unknown/partial dates and duplicate-safe revisions with tests (f8d0262).

## Hardened completion tasks — 2026-09-24

Apply the [hardened completion contract](../../../docs/PLATFORM_COMPLETION_PLAN.md#hardened-completion-contract). Dependencies below are execution gates, not evidence of completion. Keep raw/native receipts and actual identities in ignored `private/ops/`; reuse current evidence before rerunning a case. Partial/declined scope must be labelled explicitly.

- [ ] **G08-H01 — Reconcile persistence and date policy.** Depends: G03-H01 and archived G01 date contract. Inputs: `docs/RIMS_GRANTS_EXPERIENCE.md`, `scripts/grants_planning.py`, `tests/test_grants_planning.py`, existing native Calendar/Watchlist/Delivery Ledger receipts. Inventory existing lists/flows/internal names and data; record gap-only additive schema, identity mappings, permissions and rollback. Implement version/effective date/holiday-calendar policy plus override history and stale flags. Test unknown/quarter/month/date-only, DST, nonbusiness days, expired policy and changed source anchor; no invented precise deadline. Output: private schema/date readback and sanitised contract reconciliation; approved institutional policy required before presenting derived dates as institutionally accepted.
  Local validator correction (2026-09-28): required policy identity/version fields must be nonblank text without outer whitespace; explicit `EffectiveTo` values must be valid dates rather than silently treated as absent. Eleven planning and 12 calendar tests pass. Native policy persistence, override history, timezone/DST handling and approval remain open.
  Local holiday-calendar guard (2026-09-29): a business-day policy now requires explicit `HolidayDates` containing unique real ISO dates; malformed, duplicated, absent or non-list values fail closed, and direct business-day calculation requires the calendar argument. Calendar-day policies do not require an unused holiday list. All generated local ICS dates are explicitly provisional until authoritative policy/calendar acceptance. Seventeen planning and 15 calendar tests pass, including holiday shifting and provisional labelling. This establishes input shape only; it does not establish authoritative holiday coverage, approved policy persistence, timezone/DST behaviour or G08-H01 acceptance.
  Coverage/provenance guard (2026-09-30): business-day policies now also require verified coverage metadata bound to `HolidayCalendarVersion`, a captured HTTPS source, observation time, interval and evidence hash. Reject version mismatches and omit calculated events outside coverage. Synthetic regression fixtures prove unknown/incomplete evidence cannot produce a business-day projection; real policy remains provisional until its authoritative source capture is reconciled.
  2026-10-03 local implementation: the canonical grants data contract now carries `DeadlineTimezone`, `DeadlineLocalTime`, `DeadlineUTCInstant`, `DeadlineBrisbaneDate`, `DeadlineBrisbaneTime`, and `DeadlineTemporalStatus`. Explicit IANA zones and offsets are reconciled; lowercase machine-source timezone aliases are preserved; conflicting timezone aliases do not resolve by precedence; ambiguous/nonexistent DST wall times produce no UTC instant; date-only/partial values gain no time; a naive local datetime preserves its stated day/time without a fabricated timezone or instant. SharePoint schema, ingestion/review adapters, single-registry M projection, model snapshot/TMDL and reviewed-import flow definition include the fields. Funding Calendar now shows the Brisbane view and source/resolution context. Registry (23), planning (17), calendar (18), schema/page/flow contracts pass their targeted checks (296 grants tests total). The six SharePoint fields were subsequently saved/read back on isolated DEV; see the 2026-10-03 G03 postwrite receipt. Flow save/run, source timezone authority, policy approval and isolated model/report native readback remain open.
  2026-10-03 policy validation hardening: reject unknown/misspelled policy and holiday-coverage fields, malformed HTTPS ports and port zero so typos cannot be silently ignored as verified coverage metadata. Calendar subtraction now returns unknown rather than raising if a valid boundary date would underflow. Focused policy/calendar tests pass (37); the full grants suite passes 298 tests. Synthetic coverage remains structural evidence only; no authoritative holiday calendar or policy approval is implied.
  2026-10-03 evaluation-date guard: calendar projection now requires an explicit valid evaluation date and suppresses events when the policy is future-effective or expired; ICS generation evaluates against its UTC generation date. Calendar/planning focused tests pass (20/19), and the full harness passes (1,259 tests, 446 project checks, Conductor, web-first and tooling preflight). This closes only the local stale-policy projection path; policy approval, override history, native persistence and H01 acceptance remain open.
  2026-10-03 append-only override reconciliation: added `reconcile_institutional_override_history` in `scripts/grants_planning.py`. It requires an exact, complete contiguous revision history with stable typed keys and UTC recorded timestamps; compares stored anchor key/date/precision and policy/version/calculation against current inputs; and marks changed, cancelled, uncertain, future or expired cases stale while preserving every prior value. It reports review status separately and never applies an override or changes the official deadline. Eight focused synthetic cases are covered in the planning suite. This closes the local revision/staleness logic slice only; authorised policy/override decisions, holiday authority, persistence, native readback and H01 acceptance remain open.
  2026-10-03 machine-readable contracts: added `contracts/g08-institutional-date-policy.schema.json` and `contracts/g08-institutional-deadline-override.schema.json`, with schema-validation regressions against the runtime policy/history reconciler. Runtime validation now also rejects malformed optional holiday-coverage metadata on calendar-day policies. The 26-test planning suite and full local harness pass. Schemas describe storage records only; contiguous revisions, derived identity, authoritative review and native persistence remain guarded by runtime/operational checks.
  2026-10-07 current access recheck: a read-only BrowserOS REST GET to the existing isolated `My Funding Watchlist` list returned `System.UnauthorizedAccessException`; no write was attempted. This route-specific denial does not rewrite the 2026-10-05 field/item inventory, which remains a dated observation, and does not establish current persistence or acceptance. Receipt: `private/ops/2026-10-07-g08-watchlist-browseros-rest-readcheck-private.json`. Do not repeat the same GET or change identities to bypass access; resume through the documented authorized route after VS Code access is available. The focused grants harness then passed 358 tests (`PASS_LOCAL_ONLY`); native acceptance remains open.
- [ ] **G08-H02 — Implement secure preference persistence.** Depends: G08-H01. First inventory the existing `My Funding Watchlist` and `Funding Delivery Ledger` objects and any supported embedded/linked form; do not assume a distinct preferences list already exists. Reuse `My Funding Watchlist` only if its verified schema and backing-service access can support server-derived UserKey and isolated per-user reads/writes; otherwise prepare only the smallest justified additive store after exact target/rollback review. Persist scope (opportunity/category/funder), event types, reminder offsets, cadence, channel, timezone, pause and unsubscribe. Reject caller-forged UserKey/recipient values and stale-session writes. Prove two authorized test users cannot read/write each other’s preferences through the actual UI and backing service; report filters or metadata/RLS alone are insufficient. Output: private schema/access/save-reload receipts plus sanitized regressions. Current exact-list read is HTTP 403; see `private/ops/2026-10-03-g08-watchlist-sharepoint-readback-failure-private.json`. No preference store or schema change is authorized until a fresh exact native inventory is available.
  Local matching guard (2026-09-28): candidate matching now rejects malformed category collections, opportunity identities and active preference rows rather than iterating/coercing malformed JSON; overlapping valid matches still deduplicate. The canonical grants normalizer currently exposes neither `CategoryKeys` nor `FunderKey`, so those scopes remain unavailable until an evidence-backed key contract exists. This is not preference persistence, user isolation or delivery acceptance.
- [ ] **G08-H03 — Accept report and model experience.** Depends: G04-H03 and G08-H01; G08-H02 required before claiming personal watchlist. Inputs: `docs/FUNDING_REPORT_BINDING_READINESS.md`, `powerbi/CHHHS Research Publications.SemanticModel/definition/tables/GrantsRegistry.tmdl`, local report `definition/pages/FundingOpportunities`, `FundingCalendar`, `MyFundingWatchlist`, `tests/test_grants_pages.py`. The current isolated report readback has six pages; local PBIP requires seven. The on-disk recovery PBIX is the Sep22 import source and predates Sep24 browser-side report repairs; use it only as the known rollback/import baseline. Before preparing a deployment candidate:
  1. Re-read exact isolated report/model IDs and workspace; prove they remain distinct from the original pair and retain the matching private PBIX checksum/rollback copy.
  2. Obtain the latest isolated report definition through supported Download/Export or authenticated authoring readback. On 2026-09-25 the BrowserOS download waiter timed out after 60 seconds, but the Power BI dialog reported the PBIX ready; the file was recovered from Downloads and its checksum/ZIP integrity verified. The post-slicer service export is `private/ops/2026-09-25-post-edit-isolated-rims-report.pbix`, SHA-256 `fcc4a7c7b134b3ec6f7e656e569ac48313a343627540a3682eb0a2837cc511cc`; offline layout and field reconciliation are in `private/ops/2026-09-25-post-edit-report-artifact-reconciliation.json`. The export records 6 pages/66 visuals versus local 7/85; it is a preserved recovery input, and re-import/restore is untested. The Sep22 PBIX remains historical only. Do not treat its visual queries as current after later browser edits.
  3. Reconcile every page by stable name, and every visual by type, semantic query entities/properties, filter, and purpose. Record which native visuals are unnamed/opaque and inspect their actual query or render; never infer purpose from a hash or container count.
  4. Retain three distinct local experiences: Funding Opportunities, Funding Calendar, and a watchlist preview. Map the native combined Calendar & Watchlist page into the two intended local scopes; establish the personal list/table and registry bindings separately. A combined page is not proof of preference isolation.
  5. Compare publication-page counts, metrics, filters, and bindings as well as funding pages; reject candidate drift in publication scope or the CanonicalKey totals.
  6. Build a local candidate from the current verified base, run PBIP/TMDL and offline binding contracts, fingerprint the exact package, and preserve the latest service export as a recovery input. Re-import/restore has not been tested, so do not call the export a proven rollback checkpoint. The Sep22 PBIX remains a historical recovery baseline. If a future latest report state cannot be exported or read back, stop at a documented candidate gap rather than overwriting from a stale PBIX.
  7. In the isolated target only, apply minimal deltas; save, reload, and verify seven-page scope, useful empty states, reviewed-only semantics, filters, authoritative links, and model bindings. Then prove a terminal refresh and full opportunity-key/publication-total reconciliation using controlled official-source rows. Remove synthetic or unused tables only with scoped model backup and native readback; preserve original report isolation.
  8. Reconcile saved page/visual filter definitions separately from slicer bindings. The post-edit export has a ReviewStatus slicer but no filter definitions on Funding Opportunities; `review_status_saved_reviewed_only` is false. Keep the static reviewed-only claim blocked until an explicit Reviewed predicate is read back or the claim is removed. The parser fails closed for unknown filter shapes; local coverage does not pass the native gate.

Evidence: ignored `private/ops/2026-09-25-post-edit-report-artifact-reconciliation.json` records the verified 6/66 native layout, binding matrix and absent Reviewed filter; `private/ops/2026-09-25-tmdl-view-route-readback.json` records the unresolved model source read. `private/ops/2026-09-25-browseros-powerbi-report-readback.json` records the rendered inventory and `NativeAcceptance=false`; `private/ops/2026-09-22-isolated-pbix-recovery-preflight.json` identifies the historical import baseline. `contracts/dashboard.contract.json` and grants-page/web-first tests keep the seven-page local scope explicit and mark the native page delta update-blocking. Local validation alone does not pass this task.
- [ ] **G08-H04 — Implement event ledger and dry-run matching.** Depends: G08-H02 and G08-H03. Reuse existing ledger and `scripts/grants_planning.py` event keys. Persist event/revision/channel/user identity, pending/succeeded/failed status and provider ID where supported. Dry-run overlapping category/funder/individual follows, deadline changes/cancellation, duplicate triggers, retries after ambiguous provider response, pause/unsubscribe between match and send, and permission loss. Re-read current preferences/access before the delivery boundary; reconcile one eligible event per intended recipient. Output: private dry-run ledger/action receipts; no unapproved send. Recover interrupted attempts without falsely claiming exactly-once delivery unsupported by provider.
- [ ] **G08-H05 — Accept calendars.** Depends: G08-H01, G08-H02, G08-H04. Inputs: `scripts/grants_calendar.py`, `tests/test_grants_calendar.py`. Verify Reviewed-only events, stable UID/revision, date-only all-day encoding, no precise reminder for approximate dates, changed/cancelled deadlines and stale override handling. Choose supported authenticated/revocable personal feed or clearly label one-time ICS export; public feeds contain public reviewed data only. Test unsubscribe token revocation/access denial and client update/cancellation if subscription route is selected. Output: private client/service readback and sanitized calendar fixtures. No credentials or private feed URLs tracked; rollback revokes only scoped test feeds/events.

  2026-09-28 local standards corrections: generated `DTSTAMP` now appears once inside each `VEVENT`, not at `VCALENDAR` level; content lines longer than 75 UTF-8 octets are folded at code-point boundaries; calendar UIDs hash a typed JSON tuple to prevent delimiter aliases. The UID derivation changed before any accepted native feed/client deployment, so no external event IDs were migrated. Multi-event, Unicode fold-length, exact-unfold and UID-collision tests pass. This does not prove calendar-client revision, cancellation propagation, feed security or subscription behavior.
- [ ] **G08-H06 — Activate delivery only after dry-run acceptance.** Depends: G08-H04, G08-H05 and G07-H03. Prepare exact recipients/channel/cadence, content, ledger behaviour and rollback. Perform delivery/sharing/schedule actions only where existing authority covers the exact action; otherwise keep them disabled and deferred, without contacting anyone. For an already-authorized acceptance route, send bounded acceptance events, verify recipient outcome plus ledger reconciliation, prove pause/unsubscribe and cancellation, and restore test preferences/flow state. Closure: every claimed personal/subscription/delivery capability has native evidence and retained rollback; deferred activation leaves that feature inactive and labelled, not complete. G07-H04 owns recurring operational maturity.

Track closure requires all applicable acceptance tasks above, the shared completion contract, and a review recording any explicitly approved exclusions. Local pass, source availability and import success are separate from native and operational acceptance.

## Post-MVP navigation refinement (planning only)

After both MVPs and included data/access gates, [R5.5/R5.6](#post-mvp-sequence) refine G08-H03 with one project/researcher/funding drill-through and reverse lookup. Reuse existing identities/bridges; display evidence, freshness, link uncertainty and role/time. Reader acceptance requires reconciled entity totals, no count/award-amount multiplication and correct opportunity/application/award labels. Optional R6 discovery/conversational search must prove benefit and caller permissions separately. No added report/native implementation is authorised before the gate.

R5.5 quality/coverage refinement displays actionable reconciliation, freshness and explicit unknown-versus-zero alongside reconciled totals. R5.7 supplies evidence-linked researcher discovery before optional R6 search; R5.8 period snapshots extend T14/T15 only after their acceptance. Optional R6.6 suggestions remain separate from accepted data/identity/merge decisions, evaluated before enablement with a usable AI-off path. No performance ranking or automatic AI write is authorised.


## Selected owner-only ARC award-context reader — 17 October 2026

Human-authorised three-lane allocation selects one bounded native reader in the
existing RIMS report over the accepted ARCAwardContext model table. Core owns
`scripts/prepare_arc_award_report_page.py`, `tests/test_arc_award_report_page.py`
and private `2026-10-17-arc-award-reader` evidence, report native writer and final
package integration. Dataset lane owns hosting/permission/prerequisite blockers;
flow lane owns monitoring. No flow helper or hosting/profile changes here.

- [x] Prepare one clearly labelled additive award-context page; preserve all eight
  existing pages, IDs/bindings, accepted model/data/connections/schedule. Awards
  are not opportunities/applications, institutional attribution or performance.
- [x] Native save/reload;34977source-record count;source/status filters and reset;
  representative source link;source/saved-definition reconciliation and rollback.

Use the existing qualified Legacy report route: CLI modern-PBIR pack/unpack does
not support this accepted PBIR-Legacy report. Validate the equivalent added-page
PBIR projection and inspect the actual native render. No format migration or new
report/model is implied. R13c remains immutable until selected lanes settle.

Native acceptance: existing report now has nine pages; original eight sections
and four other parts exact, binding/users/subscriptions preserved. All34977,
Active6774, source/status intersection/reset and award-code1/source-link checks
passed. Six focused tests and local1868/eight skips passed. The source URL
conditional-format projection required MIN at URL-inclusive row grain; source
amounts remain text/unknown and are not summed. See
[reader and lessons](#arc-award-reader). Broader G08 tasks and
hosting/reader/production gates remain open;R13c immutable,successor pending.

## Connected funding views — 1 November 2026

Review fixed the reader builder's rejection of the accepted 71-part model and
exposed OpportunityKey alongside DeadlineKey in the calendar table. Four focused
reader tests passed and the candidate built from the saved 95-part report.
A read-only native query found one registry row, one distinct opportunity key,
zero calendar rows and zero orphan keys. The saved model has no calendar-to-
opportunity relationship. The source candidate is prepared. Native relationship,
report promotion and populated cross-filter verification remain open.

## Personal watchlists — 1 November 2026

Restored the retained Invoker lifecycle preparer and its seven focused tests
to canonical source. Review added SharePoint AuthorId checks before update and
on saved readback, plus explicit rejection of wildcard update versions.
Preparation against the retained native preimage passed. The historical bulk
upsert is separate from the personal subscribe/pause/resume/unsubscribe flow.
Native promotion requires comparing the candidate to the current saved flow
after FlowAgent sign-in. The two-user entry, isolation and readback remain open.

## Notifications and personal calendar subscriptions — 1 November 2026

The private native calendar export can now consume a subscription-context snapshot
through the existing grants_calendar CLI. Active calendar preferences select
reviewed opportunities by opportunity, category or funder. Existing UID,
revision and cancellation semantics apply. The notification planner now excludes
malformed classification objects and category lists before matching recipients.
One focused invocation passed 13 cases. A CLI fixture verification produced one
matching private event and excluded the unrelated deadline. The export is a
snapshot. An authenticated revocable feed, native update/cancel delivery and
a recipient-authorised live notice remain open. No message was sent.

## Confirmed source closing dates — 1 November 2026

All 120 official page identities matched the retained register. SharePoint readback
matched the 85 UTC closing instants and source-local calendar days. All 35 ongoing
records have blank deadlines and no calendar item. Reconciliation after interruption
completed four outstanding writes. The calendar partition accepts committed
GC-CLOSE entries explicitly marked Source confirmed alongside reviewed records.
Exact inverse, run handle and parity receipts are in the existing private capture.

## Native historical reader deployed — 2 November 2026

- [x] Save the three additive historical tables and GrantConnect history page in
  the existing isolated model/report through the existing Fabric CLI.
- [x] Process only those three tables once. The native request completed on its
  first attempt. The snapshot contains 220,124 award versions, 1,072 closed or
  archived opportunities and 100,888 confirmed GA/GO pairs, with nonblank distinct
  keys and 30 source-field samples matched to retained evidence.
- [x] Preserve all 1,344 publication rows and 50 fields, the 70 protected model
  parts, 97 protected report parts, report binding and existing landing page.
- [x] Apply review fixes for visible partial-snapshot wording and entity headings.
  One focused test invocation and the consolidated native verification passed.

See [review and retained receipt pointers](review-history-reader-20261102.md).
The page explicitly identifies last-processed list data as potentially partial.
The existing historical import and its final SharePoint membership comparison are
independent and remain open. No source acquisition, import rerun, new schedule,
business notification or NIH activation occurred. Other G08 features stay open;
CLI definition/data acceptance does not claim visual rendering acceptance.

## Live calendar implementation — 2 November 2026

- [x] Reuse the current operator's existing Outlook calendar, private watchlist
  and delivery ledger. Deploy one serial calendar writer with coalesced
  preference/deadline/classification change signals through FlowAgent.
- [x] Implement confirmed-day matching, stable managed event identity, in-place
  updates, explicit withdrawal, unchanged replay suppression, conditional writes,
  human-edit protection and durable pending-attempt retention. Source or
  classification uncertainty holds rather than fabricating a date/withdrawal.
- [x] Seven focused local tests passed; the added classification signal received
  one affected-test check. The first native qualification failed on unescaped
  marker braces after creating one event. Its corrective continuation updated
  and removed the same event; no duplicate create or invitation occurred.
- [x] Execute the worker's live-reader graph once with an explicit no-opt-in
  guard. It succeeded without source/provider writes. Restore its file-change
  trigger and retain saved-definition readback privately.
- [ ] Full saved-follow/change/ledger/pause/unsubscribe and multi-user acceptance
  remain open. No real follow was created merely to test the feature. The
  current-operator deployment does not close all H05/H06 scope.

See [calendar contract](../../../docs/GRANTS_LIVE_CALENDAR.md) and
[review with applied fixes](review-live-calendar-20261102.md). Native identity,
qualification and readback receipts are private in the feature checkout. The
historical-import writer, original evidence, existing business schedules and
inactive NIH roadmap are unchanged. No scheduled verification was performed.

## Business notification implementation — 2 November 2026

- [x] Bootstrap the retained delivery graph as one fixed-operator unattended
  GrantConnect business sender: opportunity revisions, reviewed deadline changes,
  cancellation and source-day reminders with saved immediate/daily/weekly cadence.
- [x] Preserve source review, current classification and private saved consent.
  Re-read source/preference/deadline versions before send; use claim-before-send,
  no transport retries, exact receipt markers and receipt-only ambiguous recovery.
- [x] Resolve the non-unique ledger-key concurrency risk with explicit source
  ownership. At an idle checkpoint, promote only the existing legacy dispatch
  module and exclude GrantConnect business candidates in its private configuration.
  Preserve the operational worker, schedule, dirty source and earlier journals.
- [x] Run the focused 13-case selection, correct two test-harness errors with
  affected reruns, and apply review fixes. The one native no-send qualification
  succeeded with zero reviewed GrantConnect records and zero due own email rules.
  Final reviewed Started definition, connections and ownership cutover match.
- [ ] Accept an actual business-message receipt from genuinely reviewed source
  evidence and a saved due email preference. Implementation/readback and no-send
  qualification do not establish that receipt or broader multi-user acceptance.

See [business contract](../../../docs/GRANTS_BUSINESS_NOTIFICATIONS.md) and
[review](review-business-notifications-20261102.md). Native scope/receipts are
retained privately in `private/ops/grants-business-notifications-20261102/` in
the feature checkout on `codex/grants-business-notifications`. This lane owns
the new business worker and GrantConnect business source scope only. Existing
operational alerts, calendar/import writers, authentication owners and schedules
remain unchanged. No source refresh, fabricated review or NIH work occurred.
