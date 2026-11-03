# Remaining Conductor track audit

Audit date: 2026-09-21. This is a source and acceptance ledger, not a claim
that the tenant is complete. A track is archivable only when its plan tasks
and its required native acceptance evidence are both complete.

| Track | Current evidence | Remaining gate | Archive decision |
|---|---|---|---|
| S02 | Clean canonical source package reproducibly verified; SharePoint item versioning observed | Isolated native report version/batch display and readback | Keep active |
| G02 | Official NHMRC/MRFF calendars, ARC awards API, Queensland metadata API, conservative source catalogue, and fail-closed row-level evidence/eligibility gate verified | Permitted opportunity feed/API or explicit human-reviewed rows with source links and eligibility | Keep active |
| G03 | Isolated Grants Registry schema and authenticated synthetic create/update/duplicate/concurrency evidence; existing flow updated in place; fresh native export contains `SourceRowURL`, choice mappings and current server timestamp; flow remains Off with Flow Checker 0 errors and 1 inactive-flow warning; synthetic replay cleanup completed and API readback is `ItemCount=0`; existing semantic model readback shows `Grants Registry` table 21 of 27 with 44 columns | Shared organisation-wide target and unattended operation are future extensions outside the current-user scope | Archive after review |
| G04 | RSS/Atom/API-shaped adapters and fresh 13/179 NHMRC/MRFF candidate extraction | Controlled source-to-list cycle and reconciliation | Keep active |
| G05 | University catalogue and access/lead-time evidence | Permitted institutional export/feed or reviewed intake | Keep active |
| G06 | Typed relationship contract and local safeguards; canonical local and native `GrantRelationships` model/query projection; isolated personal DEV list with `RelationshipKey` required/unique/indexed; native synthetic create/read/update/delete round-trip; correlated Publication Registry before/after receipt unchanged at 1,468 rows, 1,265 nonblank/distinct keys, no continuation link and SHA-256 `2b1b81200fe8e816bc15dce02ff80d4013c908925c2b855b777d241c595fe413`; existing semantic model readback shows `Grant Relationships` table 27 of 27 with 30 columns and zero rows | Organisation-wide sharing and unattended delivery are future extensions outside the current-user scope | Archive after review |
| G07 | Fail-closed operational evaluator, exact-key reconciliation, selected-field readback reconciliation and isolated create/update replay | Native monitoring, operational reconciliation, delivery and scheduling | Keep active |
| G08 | Local calendar, institutional-date, current-user subscription, source-preserving calendar-change and delivery-ledger contracts; canonical local PBIP projections for `FundingCalendar`, `FundingCalendarChanges`, `MyFundingWatchlist` and `FundingDeliveryLedger`; exactly one native personal list for each existing surface; dedicated upsert flows each have controlled native evidence and are Off after testing; delivery identity is required/unique/indexed; two report pages and the existing semantic model have native SharePoint tables and saved visuals; all three synthetic test rows were removed through exact-item SharePoint delete confirmations; current native inventory contains exactly one copy of each grant/DoRA flow; native calendar-change copy `e95f2a40-0689-42ec-b35b-b0e5f0440ba2` is saved, Flow Checker-clean and Off | Current-user flow/page binding, subscription isolation, Power BI refresh/reconciliation, controlled change-ledger run/readback and actual calendar/reminder delivery | Keep active |
| T11 | Local PubMed/DoRA preservation and schema/key reconciliation; canonical local `DoraActivityRegistry` model/query projection with all 26 fields; isolated personal `DORA Activity Registry` with required/unique/indexed identity and indexed record/resource IDs; synthetic full-field create/read/delete round-trip; one imported current-user upsert flow with successful controlled create/update/readback and cleanup; existing semantic model readback shows native `DORA Activity Registry` table 28 of 28 with 48 columns and zero rows; saved Clinical Analytics table visual reads back four DORA fields | Retained-history reconciliation, refresh, recurrence, delivery and operational acceptance | Keep active |
| T14 | Complete local exports, monthly generator and failure contracts | Manual native cycle, consecutive-cycle replay and delivery decision | Keep active |
| T15 | Local handover/package and current four-page report audit | Native release/readback; Clinical Analytics model bindings are broken | Keep active |
| E01 | Corrected publication query and successful DEV flow readback; standalone tracked-flow validator and CI gate pass | Manual replay/update, duplicate/failure safety and user-scoped reconciliation | Keep active |
| E04 | Local Fluent/grid/contrast and PBIR-to-TMDL field-binding tests pass; native Clinical Analytics has nine field errors; isolated model view bootstraps the original model and fails in the modeling iframe | Restore a correctly bound isolated authoring route, then repair/read back model/report bindings | Keep active |
| E07 | Local platform acceptance contract and isolated evidence | End-to-end tenant acceptance and release evidence | Keep active |

## Canonical-source invariant

The private GitHub repository has one remote branch, `main`. The synchronized
clean checkout used for this audit is the canonical local reference. The
original authoring checkout remains dirty by design and is not treated as a
second remote version. Conditional T16/T17 fallbacks remain gated and are not
created or activated.

## Review conclusion

Conductor review was applied to the active changes, stale completion claims
were corrected, and review SHAs were recorded in the relevant plans. No track
is archived in this audit because each active track has at least one explicit
native, source-access or operational gate still open.

## Native access recheck — 2026-09-21

Read-only PAC/Azure discovery was attempted after the browser debugger route
remained unavailable. PAC is authenticated to an unrelated Power Platform
environment and its environment query returns an Entra account-deleted
directory error; Azure is authenticated to a different tenant. No credentials
were changed and no tenant mutation was attempted. This confirms the remaining
native gates are externally blocked by tenant/account scope, while local source
and contract work remains synchronised and CI-green.

## Native access recheck — resumed audit — 2026-09-21

The read-only `playwright-cli` check found that neither the `chrome` nor
`login` browser session is open. PAC still reports the unrelated NSW profile
(`<operator-account-redacted>`), and Azure still reports the unrelated
Flinders tenant/account (`<operator-account-redacted>`). No login, tenant switch,
deployment, or write was attempted. The native gates listed above therefore
remain open; this is evidence of unchanged external state, not a completion
receipt.

## Native grants-flow continuation — 2026-09-21

The authenticated current-user route was restored through `playwright-cli`.
The existing flow `CHHHS Research Grants - Reviewed Import Upsert`
(`acf866e4-e4a2-4113-bce4-d2dd9e2f22d6`) was retained as the sole grants flow;
the legacy package importer was tested but offered only `Create as new`, so it
was cancelled and no duplicate was created. The personal DEV SharePoint list
`Grants Registry` received the missing `SourceRowURL` Hyperlink column. The
existing flow editor then persisted and reloaded SourceRowURL and choice
mappings for Create and Update; Create defaults ReviewStatus to `Needs Review`
and Update leaves ReviewStatus untouched. A fresh package export recorded
server modification time `2026-09-21T03:12:53.7725597Z` and contains the
SourceRowURL and choice mappings. Flow Checker reads 0 errors and 1 warning,
where the warning is only that the flow is Off. The flow remains Off and no
new run, schedule, sharing or notification was activated. G03 remains active
for current-user operational acceptance; shared organisation-wide target and
unattended operation remain future extensions.

Native G03 cleanup continuation — 2026-09-21: the remaining synthetic replay
row (`Synthetic G03 replay 20260920 UPDATED`) was deleted from the isolated
personal `Grants Registry` through the authenticated SharePoint UI. The
SharePoint API immediately read back `ItemCount=0`. No production row was
changed and the flow remains Off.

## Native G08 list bootstrap — 2026-09-21

Inventory of the authenticated personal DEV site found no funding watchlist or
calendar list. Exactly one `My Funding Watchlist` list and exactly one `Funding
Calendar` list were therefore created. Authenticated SharePoint REST readback
confirmed the watchlist identity and fields (`OpportunityKey` required and
unique, `Scope`, `TargetKey`, `Active` default false) and the calendar identity
and fields (`DeadlineKey` required and unique, `OpportunityKey`,
`CalculatedDate`, `SourceURL`, `Cancelled` default false, `PolicyKey`,
`ReviewStatus` default `Needs Review`). Both lists read `ItemCount=0`. No
subscription, calendar event, flow, notification, sharing change or report
page was activated; G08 remains active for binding and delivery acceptance.

Controlled calendar persistence evidence: one synthetic deadline item was
created in the personal `Funding Calendar` with an exact calculated date,
source URL, policy key and default `Needs Review` state. All visible values
were read back, the policy key was edited and read back, and the item was
deleted. The list returned to zero rows. This proves current-user list
persistence only; it does not prove report binding, revision-ledger logic,
calendar delivery, notifications or unattended operation.

## Native T11 DORA Activity Registry bootstrap — 2026-09-21

The authenticated personal DEV site had no existing `DORA Activity Registry`,
so exactly one isolated list was created. The canonical 26-field schema was
then bootstrapped and read back through SharePoint REST. `DORAActivityKey` is
required, unique and indexed; `DORARecordID` and `DORAResourceID` are required
and indexed; the remaining fields have the canonical text, note, date/time and
URL types and requiredness. Versioning is enabled and the list initially read
zero items. A synthetic row populated every mapped field, read back all 26
fields and identity values, was deleted, and the API read back `ItemCount=0`.
This proves isolated schema/row persistence only; DoRA flow import, retained
model/report integration and live or unattended operation remain open.

## Native relationship continuation — 2026-09-21

The personal DEV `Grant Relationships` list was read back with all eight
canonical columns. The `RelationshipKey` column editor confirmed required
information and enforced unique values. A synthetic candidate relationship
with an HTTPS evidence URL was created and read back, updated (title and
evidence URL), read back again, and then deleted to the recycle bin. The list
now reads `ItemCount=0`. A read-only SharePoint API check of the personal
`Publication Registry` read `ItemCount=1468`; no publication item was changed
by the relationship test. The correlated before/after key-set reconciliation
and exact-item cleanup were subsequently captured, so G06 was reviewed and
archived for the current-user scope; no shared binding was made.

## Local hardening continuation — 2026-09-21

Since the resumed access recheck, three local review fixes were completed and
synced to the sole remote `main` branch:

- G02 `ec5322c`: source authority/API URLs with surrounding whitespace now
  fail closed before intake validation.
- G08 `a573598`: calendar CR/LF display-field escaping is explicit and tested.
- G07 `1ac3d52`: operational source and opportunity identities with surrounding
  whitespace now fail closed rather than being accepted after comparison-time
  trimming.

The canonical checkout is clean and remote-aligned at `0e67c89`. The full
local suite passes 426 tests with 8 skips; the harness, 438 project checks,
Conductor, web-first, Power Platform, visual and canonical flow validators pass
locally. GitHub Actions run `35552156045` is green. These changes do not close
the native tenant, permitted-feed or unattended-operation gates listed above.

## Platform route recheck — current user — 2026-09-21

The requested move to current-user platform implementation was attempted
read-only. `playwright-cli list` reported no browsers; the CUA Chrome provider
and in-app browser provider were unavailable; attaching to the running native
Chrome app failed with a ScreenCaptureKit stream error. No login, target
switch, platform write, flow activation, sharing change or schedule change was
attempted. The local user-scoped source remains the only synchronised
canonical version until an attachable current-user platform session is
available.

## Native G08 watchlist-flow bootstrap boundary — 2026-09-21

An existing reviewed-grants flow was cloned temporarily to test reuse for the
personal `My Funding Watchlist`. The personal list and its four fields were
resolvable, but the cloned grants trigger/parser lacked the dedicated
`Scope`/`TargetKey` subscription contract. The incomplete copy was discarded.
Power Automate then read back exactly three remaining flows: publications,
reviewed grants and reviewed DoRA. No temporary watchlist flow remains.

## Native DoRA flow continuation — 2026-09-21

The first target-injected DoRA package was rejected by the SharePoint connector
because action parameter keys used display names rather than connector
internal names. The canonical definition and validator now apply the explicit
internal-name map. The rebuilt package imported as exactly one current-user
`CHHHS DoRA Activity Registry - Reviewed Upsert` flow in the isolated personal
DEV target. Controlled create and same-key update runs both succeeded;
SharePoint readback confirmed the mapped identity and updated values, then the
synthetic row was deleted and `ItemCount=0` was confirmed. Flow Checker showed
0 errors and one warning for the flow being Off; it was restored to Off after
testing. Retained-history/report integration, recurrence, notifications,
delivery and production acceptance remain open.

## Native G08 delivery-ledger continuation — 2026-09-21

The personal DEV site then received exactly one `Funding Delivery Ledger` list.
Native field readback confirmed the visible identity, user/opportunity, event,
revision, offset, channel, status, schedule/send and error fields; `Status`
has default `Pending`, versioning is enabled with a 50-major-version limit,
and the list was empty before testing. A SharePoint-only ledger flow was
bootstrapped from the calendar/grants package pattern and imported as the sole
new flow identity. The initial controlled run
`08584116256446744665855863737CU13` failed because an empty optional `SentAt`
value was submitted as `""` to a SharePoint date field. The definition was
repaired to pass null for empty optional date/error values, the same flow was
updated in place, Flow Checker read 0 errors and 0 warnings, and the corrected
same-key run `08584116253756053128213151733CU27` succeeded. SharePoint readback
showed the single row updated to revision `v2`, channel `email`, status `Sent`,
the revised scheduled date and a populated send timestamp. The flow was
restored Off. The synthetic row remains pending explicit UI deletion
confirmation; this is current-user persistence/replay evidence only and does
not prove notification delivery, subscriptions, report binding or unattended
operation.

### G08 calendar-change persistence/import boundary — 2026-09-22 (updated)

- **Local:** the canonical `FundingCalendarChanges` projection, revision-diff
  helper, schema and SharePoint-only upsert contract are implemented and
  focused tests pass.
- **Native:** one isolated personal DEV `Funding Calendar Changes` list exists;
  all 13 canonical fields and defaults read back correctly with zero items.
- **Resolved safely:** three corrected legacy package imports were rejected by
  Power Automate as `MalformedFlowAssetFlowDefinition`; a native Save As copy
  of the existing calendar flow was used instead. The copy is
  `e95f2a40-0689-42ec-b35b-b0e5f0440ba2`, bound to `Funding Calendar Changes`,
  saved with Flow Checker `Errors (0)` and `Warnings (0)`, and remains Off.
- **Decision:** keep G08 open. Controlled run/readback, page binding,
  refresh/reconciliation and actual calendar/reminder delivery remain required.

### G08 calendar-change native execution — 2026-09-22 (current)

- **Native success:** the copied current-user flow
  `e95f2a40-0689-42ec-b35b-b0e5f0440ba2` passed a controlled non-null create
  (`08584115988253175752159968677CU24`) and same-key update
  (`08584115987296857629538066289CU13`). REST readback showed one stable
  SharePoint item, complete mapped field values, the expected revision/date/
  cancellation/URL/review changes and no duplicate.
- **Cleanup/status:** the exact synthetic item was deleted through the native
  SharePoint `Delete?` confirmation; the REST endpoint returned zero items.
  Power Automate details read `Status: Off`; no sharing, schedule or
  notification setting was changed.
- **Residual evidence risk:** two null-`PreviousDate` diagnostics failed at
  the SharePoint date conversion boundary because the connector received an
  empty string. The native optional-date path is therefore not accepted and
  remains an explicit follow-up. Model/page binding, refresh/reconciliation
  and actual calendar/reminder delivery remain open.
- **Native repair readback (2026-09-22):** a fresh authenticated designer
  open exposed the same unquoted property-name expressions in the copied
  `Create item`/`Update item` mappings. Those mappings were corrected in the
  existing flow identity, saved, and Flow Checker again read `Errors (0)` and
  `Warnings (0)`. The tracked local definition already used the quoted form;
  this is a tenant-side correction receipt, not a null-date execution proof.
- **Native null-date recheck (2026-09-22):** the flow was temporarily turned
  on for one controlled synthetic input with `PreviousDate=null`, then run as
  `08584115961596220678423119580CU22`. It reached `SharePoint Get items` and
  failed at `Create item` because the connector received `""` for the
  `PreviousDate` date field (`OpenApiOperationParameterTypeConversionFailed`;
  expected `String/date`). No synthetic SharePoint row was written. The flow
  was turned Off again immediately after the test. This confirms the known
  connector edge rather than acceptance of the optional-date path.
- **Decision:** keep G08 active; the non-null native execution/readback gate
  is evidenced, but the track is not complete or archivable.

### S02 isolated report display — 2026-09-22

- **Native current-user evidence:** the existing semantic model retained the
  `ReleaseMetadata` calculated table after reload. The existing
  `Monthly Publications` report page was saved with a four-column table bound
  to `AcceptedBatchID`, `NativeAcceptance`, `SchemaVersion` and
  `SoftwareVersion`.
- **Readback:** a fresh report reload displayed all four headers and the
  source-only metadata row.
- **Boundary:** this closes S02.3.4 only. Native refresh, report/model
  version-history, rollback, sharing, scheduled delivery and production
  acceptance remain open; no flow was enabled or schedule changed.

### Resumed canonical audit — 2026-09-22

- **Repository:** the clean canonical checkout is synchronised to the sole
  GitHub `main` branch at `111b3c3`; the original authoring checkout remains
  intentionally dirty and is not a second remote version.
- **G08 import evidence:** the authenticated QLD Health browser upload reached
  `generateResourceStorage`; `listImportParameters` returned HTTP 202 and
  its packaging-operation poll returned HTTP 200 with `status: Succeeded`,
  the expected flow resource and SharePoint connection resources. The wizard
  then remained at `Uploading your package` and never exposed mappings or an
  enabled `Import` action. A previously known-good `New` package reproduced
  the same UI handoff failure; no import or duplicate was created.
- **Alternate route:** VUW PAC remains authenticated but its cloud-flow
  inventory is empty; the alternate Chrome/CUA surface was unavailable in
  this session. QLD Health remains the authoritative native target.
- **Local gates:** 444 tests passed with 8 skips, 460 project checks passed,
  and web-first, harness, tooling, Conductor and diff checks passed. These
  are local/structural gates and do not close native acceptance.
- **Decision:** keep all tracks with explicit source-access, tenant,
  refresh, reconciliation or delivery gates active. Do not archive G08 until
  the null-preserving branch is imported into the existing flow identity and
  null/non-null create/update/readback is proven.

### G08 classic-designer continuation — 2026-09-22

- The QLD Health classic Power Automate designer was reached by disabling the
  new-designer switch. It exposes the Control/Condition action and permitted
  an unsaved branch-edit experiment.
- The dynamic-content picker exposed duplicate `PreviousDate` labels from
  prior actions, but did not provide an unambiguous current calendar-row
  token in the attempted condition. The temporary condition was discarded
  through the browser reload confirmation; the canonical flow was not saved
  or changed by this experiment.
- **Decision:** retain the server-side import/parser success and classic
  designer route as evidence, but keep the null-preserving repair open. No
  partial browser edit is a valid implementation receipt.

### G08 classic-designer bootstrap retry — 2026-09-22

- The recovered authenticated session exposed the classic action menus. The
  existing `Create item` action was copied to the designer clipboard and then
  removed inside an unsaved draft so a null-preserving condition could be
  inserted before recreating the action in both branches.
- The action picker became unresponsive before the replacement condition was
  selected. The active tab was reloaded through the headed Chrome UI to
  discard the draft; no Save operation was issued and no tenant flow change
  is claimed. The existing flow identity remains the sole canonical target.

### E04/E07 review recheck — 2026-09-22

- **E04:** local geometry, contrast and PBIR binding contracts remain green;
  the native four-page report still has the previously recorded nine
  `Clinical Analytics` field-binding errors, and the isolated authoring route
  has not yielded a safe repair/readback path. Keep active.
- **E07:** local publication-flow acceptance validators and SharePoint target
  parity remain green; native replay/update, failure-safe batch
  reconciliation, refresh, monitoring and organisation-safe release evidence
  remain incomplete. Keep active.
- **Canonical source:** this recheck was performed from the clean checkout at
  `94ffbc7`; the sole GitHub `main` branch remains the canonical remote.

### G08 classic-designer action-picker retry — 2026-09-22

- The existing flow was reloaded and its original `Create item` action was
  visibly present before the retry. The action was copied using the classic
  designer clipboard, after which the designer stalled before any delete,
  replacement, or Save operation completed.
- The headed Chrome tab was reloaded to discard the unsaved draft. No tenant
  mutation is claimed; the existing flow remains the canonical target and
  native null-date acceptance remains open.

### G08 native refresh retry — 2026-09-22

- The authenticated Power BI semantic-model editor started a fresh `Schema
  and data` refresh after the three grant test lists had read back zero rows.
- The native progress dialog remained at `Processing queries and validating
  semantic model` for approximately 50 seconds. The refresh was cancelled
  through the native `Cancel refresh` confirmation; no refresh success or row
  reconciliation is claimed. G08 remains open for this gate.

### G08 data-only refresh alternative — 2026-09-22

- After the schema-and-data retry stalled, the authenticated model editor was
  used to select the narrower `Data` refresh route. It did not expose a
  terminal success receipt, and the subsequent native refresh-history panel
  stalled while loading.
- The active Power BI tab was reloaded without editing or saving the model.
  No data-only refresh success or row reconciliation is claimed; the refresh
  gate remains open.
- The post-reload notification center separately displayed `Data load was
  successful` for `CHHHS Research Publications`, timestamped `an hour ago`,
  alongside the current model's older refresh errors. Because that receipt is
  not correlated to this attempt's run/request, it is retained as
  non-correlated native evidence and does not close the refresh gate.

### VUW CLI route check — 2026-09-22

- PAC authentication was present for the `<retained-unrelated-profile>` profile
  (`<operator-account-redacted>`) in
  `https://orgd747e711.crm6.dynamics.com/`, but
  `pac power-automate list-cloud-flows` returned an empty inventory.
- No VUW cloud-flow package was therefore available to export. The QLD
  Health authenticated browser route remains the authoritative native path;
  its package parser succeeds but the wizard stalls before Import submission.
- No VUW artefact was promoted, no cross-tenant copy was attempted, and the
  QLD Health flow remains the sole canonical native target.

### Canonical checkout refresh — 2026-09-22

- The clean checkout used for this audit is synchronised to the sole GitHub
  `main` branch at the current canonical commit; the original authoring checkout remains
  intentionally dirty and is not a second remote version.
- Local structural evidence and native tenant evidence remain separate. The
  VUW CLI inventory result and the QLD Health browser import blocker do not
  close any native publication or grants acceptance gate.

### E01 classic-designer expression retry — 2026-09-22

- The QLD Health classic designer permitted an unsaved Condition shell inside
  the existing `Condition Is New Calendar Row` yes branch. The explicit
  current-item null expression was rejected by the expression editor, and the
  dynamic-content panel stalled on retry.
- The browser tab was reloaded to discard the draft. No Save operation,
  enablement, or native mutation was performed. E01 remains active; the local
  null-preserving definition is not a native acceptance receipt.
### E04 native report audit refresh — 2026-09-22

- Authenticated Power BI readback now shows six pages: `CHHHS Publications`,
  `Monthly Publications`, `Source Reconciliation`, `Clinical Analytics`,
  `Funding Opportunities` and `Funding Calendar & Watchlist`.
- `Clinical Analytics` visibly renders the DORA headers
  `DORAActivityKey`, `DORARecordID`, `DORAResourceID` and `DORASourceURL`, but
  nine other visuals still report field-binding errors.
- The receipt is private and read-only at
  `private/ops/2026-09-22-powerbi-e04-native-audit.json`. No shared model or
  report write was attempted; E04 remains active and not archivable.

### T11 native DoRA flow details readback — 2026-09-22

- The authenticated QLD Health Power Automate details page read back the sole
  canonical flow `CHHHS DoRA Activity Registry - Reviewed Upsert`
  (`dd508644-c6d0-40be-aa1e-9b1f4d7c936c`). It is Off, Instant, owned by
  <retained-operator>, uses the QLD Health SharePoint connection, and has no
  run-only users.
- Flow Checker read 0 errors and 1 warning, with the warning being the
  intentional inactive-flow state. Two visible 28-day runs were Succeeded.
  Receipt: ignored `private/ops/2026-09-22-powerautomate-t11-dora-flow-readback.json`.
- This corroborates controlled flow execution and canonicality only. Durable
  history, scheduled/unattended operation, refresh, report reconciliation,
  delivery and production acceptance remain open; T11 stays active.

### Current synchronized audit addendum — 2026-09-22

- The canonical clone is clean at `35549dd`, matching the sole GitHub `main`
  branch. Source-only CI run `35655397495` passed the unit, project,
  web-first, Conductor, Power Platform preflight, visual and canonical-flow
  checks.
- The active review records now use the current 444-test/460-check local
  baseline. This is source/documentation evidence only; it does not promote
  any native gate to complete.
- A fresh `playwright-cli -s=login` route currently resolves to Microsoft
  sign-in rather than an authenticated QLD Health session. VUW PAC still has
  no cloud-flow inventory. The QLD Health null-date repair therefore remains
  unsaved, the canonical flow remains Off, and no track is archivable on this
  evidence alone.
- A read-only PAC profile audit found only `nsw-dylan` and `<retained-unrelated-profile>`; no
  QLD Health PAC profile or QLD Health environment is available locally. The
  active VUW environment is the VUW STAFF default environment, not the QLD
  Health tenant. No profile was changed and no cross-tenant import was
  attempted.

### Browser/CLI route recheck — 2026-09-22

- `playwright-cli -s=login` was directed to the supplied QLD Health Power
  Automate flows URL and resolved to the Microsoft organisational sign-in
  page. No authenticated flow list or import wizard was available in this
  session.
- PAC 2.12.2 remained authenticated as `<operator-account-redacted>`. Read-only
  `pac power-automate list-cloud-flows` checks against the VUW STAFF default
  environment and the other visible VUW environment identifiers returned no
  exportable cloud-flow inventory (or no matching environment for the
  non-default identifiers).
- No VUW export exists to carry into QLD Health, and no QLD Health import was
  submitted. The QLD Health tenant remains the sole canonical native target;
  the local package and source-only GitHub checkout remain the canonical
  implementation artefacts.
- The follow-up PAC environment-name audit reached `VUW-AI-TEST` but its flow
  inventory was empty; `VUW-AI-DEV` returned `Forbidden`, and the remaining
  visible VUW environment selections did not expose an exportable flow. The
  active PAC profile was restored to the VUW STAFF default environment after
  the read-only checks.
