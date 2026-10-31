# Implementation plan

## Grants intake priority — GrantConnect, 31 October 2026

GrantConnect is the first grants intake priority. Use the existing source
catalogue, CLI tooling and retained captures first. Qualify the exact permitted
source/access route, terms, reuse rights and lifecycle handling (new, amended,
closed/withdrawn opportunities, dates and versions) before integration. Record
actual API/feed/export availability; none is presumed qualified. Integrate with
the existing protected register/model only if that supported route is established.
No new consent, credential scope, access bypass or provider request is implied
by this documentation update.

NIH expansion, first-time NIH admission and further NIH chain work are removed
from the near-term plan and retained only on the long-term roadmap. Preserve
existing NIH data, configurations and accepted chain/recovery evidence; do not
stop/delete services or change schedules. The selected 169-edge PubMed candidate
grant-reference model/report connection is separate and remains selected; it is
not an NIH grants collector or admission task. All other optional deferrals and
the existing 1 November verification/promotion boundary remain unchanged.

## Execution choice and fallback — planning amendment, 23 October 2026

**G04 default:** Native cloud flow archives originals, creates an Excel processing copy and writes the existing register.

**Skills:** Power Automate build/debug/diagnose; M365 file readback. Read the selected skill and installed help/schema at execution;
capability inventory is not authentication, permission or target qualification.

**Fallback / stopping boundary:** Unknown workbook shapes preserve originals and last-good data; a local parser is an oracle, not the hosted replacement.

**Workflow and agent allocation:** Primary agent by default. Optional explicitly
scoped explorer, worker or independent review must retain disjoint ownership;
no delegation, installation or native effect is performed by this amendment.
Record preparation → saved readback → runtime → web acceptance separately in
existing receipts, with same-ID preimage, drift guard and scoped recovery.
Use the [shared capability guide](#cli-implementation-routes)
for conditional hosted MCP/Fabric IQ/ALM choices and current tool inventory.
Existing task markers, accepted evidence and ownership remain authoritative.



## CLI route selection gate — 23 October 2026

**G04 operation family:** Power Automate Excel/SharePoint connectors; maintained workbook adapters; M365 bytes readback.

**First bounded decision:** Use the Microsoft processing-copy path for runtime; compare complete keys and original bytes, not a local parser result alone.

At execution, record the installed help/exposed schema and exact supported
operation in the existing private receipt before selecting a writer. The
[shared tool and evidence contract](#cli-implementation-routes#tool-selection-and-evidence-record--23-october-2026)
applies: available does not mean connected or target-qualified. Primary-agent
execution is the default; optional local delegation needs explicit scope and
existing authority. This is a plan amendment only; no implementation or status
change is made here.


## Execution dispatch contract — planning only, 23 October 2026

**Track G04; start:** `python3 scripts/agent_harness.py context --task grants`;
use `python3 scripts/agent_harness.py resume` instead for an in-flight operation.
This is a later execution instruction, not an implementation performed here.

**Selected path:** Dynamic original workbook archive → native Excel processing copy → SharePoint/register/model; full keys and replay.

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

**G04 mechanism:** Archive original dynamic workbook/API payload → create processing copy → discover actual tables/ranges via qualified connector → upsert typed register by durable source key → reconcile full key sets and replay.

**Selected tools and skills:** Power Automate build/debug/diagnose; existing native Excel/SharePoint connectors; M365 file/row readback; maintained source adapters.

**Required proof / limits:** Original bytes and all raw fields survive; local parsing is preparation, not a hosted runtime. Unknown workbook shape fails without losing last-good data.

**Execution exit and cross-track handoff:** Consume admitted G02/G05 inputs and accepted G03 fields. Prove complete original retention, shape discovery, typed import, exact full-key reconciliation and unchanged replay on Microsoft runtime. Keep last-good records and processing-copy provenance when an unfamiliar workbook fails.

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

**Owner / agents:** Existing grants collector/import owners; consume G02 admission and G03 schema. A disjoint local explorer/worker may prepare
source and a separate reviewer may inspect it; no second native writer.

**Tools / skills:** Power Automate build/debug; qualified Flow API; M365 SharePoint/Excel connectors; PAC ALM; local source builders as preparation only.

**Reuse:** scripts/prepare_funding_workbook_collection.py; scripts/prepare_funding_register_refresh.py; scripts/project_funding_workbooks.py.

### Executable handoff contract — planning only, 22 October 2026

**Next implementation unit:** Prepare the existing workbook collection/register-refresh definitions, retaining the original workbook and a native Excel processing copy; deploy only the affected admitted-source graph after G03 schema qualification.

**Start and discovery:** `python3 scripts/agent_harness.py context --task grants`
(or `resume` for an existing operation), then read the selected skill and installed
CLI help. Resolve targets from existing private S02 manifests. Obtain exact M365
syntax through `m365_search_commands` → `m365_get_command_docs`; inspect exposed
FlowAgent/Fabric schemas rather than inventing calls. The [shared capability guide](#cli-implementation-routes)
records available versus conditional tools and the common gated command sequence.
These are instructions for a later implementation run, not commands executed here.

**Evidence to retain:** Complete source keys and fields, original/processing-copy linkage, native Excel actions and persisted rows/model reconciliation; unchanged replay and partial-failure recovery. Require both successful process exit and structured
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

Existing raw workbook archive and supported native Excel/cloud-flow processing. Local scripts prepare definitions and reconciliation only; they are not the deployed ingestion runtime.

Use the [capability qualification and agent rules](#cli-implementation-routes#execution-time-capability-qualification) before selecting a newer transport. Record the exact tool/version, operation schema, target scope, prepared input revision, owner and rollback in the existing private receipt. An unavailable optional tool does not block the established supported route. No additional installation or native action is part of this planning update.

<!-- execution-route-end -->

**Execution sequence for the next authorised implementation:**

1. Reuse dynamic official NHMRC/MRFF original-workbook discovery/retention; read current collection receipts and complete originals before choosing the next missing source/projection.
2. Build the native Excel processing-copy→SharePoint projection with existing explicit connector/drive/list bindings. Preserve archived originals, workbook/source/revision identities, dates/nulls and generic source-key handling.
3. Guarded same-ID deployment then one correlated native source/archive/register/model cycle and unchanged replay must reconcile complete keys/fields, review preservation and failed-source last-good state. Return affected semantic integration to the model owner.

**Acceptance / limits:** Local workbook parsing is an oracle, not hosted ingestion. No replacement runtime or recurrence activation; natural observations move to E08.


Current source expansion follows the [CLI-only delivery queue](#post-mvp-sequence#cli-only-source-delivery-queue--18-october-2026). Reuse existing components; no browser/headless/manual-upload fallback. Deliver one source end to end and skip conditional blockers. This overrides conflicting historical route/order wording below.

## Selected funding source increment complete — 18 October 2026

NHMRC302 and MRFF1,915 native archive→SharePoint consumers have terminal success,
full source fidelity and zero-write replay. MRFF replay preserved all2,217 item
ETags/notes/IDs and the original workbook hash; both sources' collectors/consumers
are saved Stopped/read back. Full scope/evidence/lessons are in the current source
queue. Canonical solution migration/export is specifically blocked by admin-route
preflight403; no mutation. This closes the selected operator-run funding-source
increment, not wider G04 automation or business assessment. Historical repair
steps below remain evidence, not outstanding dispatch.

## MRFF native acquisition increment — 18 October 2026

The MRFF collector passed a native run. All three original XLSX files plus the
landing page/manifest passed download/hash verification; workbook hashes match
prior originals. Collector final saved state is Stopped. The consumer is deployed
on its existing stable ID. First failure: an existing publisher table overlapped
CreateTable; same-ID repair reuses MRFF_Grants on a processing copy. Second run
updated1,912rows; three newline-containing IDs were missed by OData URL lookup,
while unique SourceKey prevented duplicates. Direct API proves original IDs are
correct; no identity repair effects occurred. CLI formatted JSON adds misleading
backslashes before linefeeds, so use exact API/file bytes for fidelity.

Historical recovery used a bounded full-list JSON snapshot, exact in-flow key
matching, ETag-guarded source-only updates and numeric-ID readback. Its saved
native definition matched; recovery and replay now Succeeded. Full1,915field
fidelity/zero ETag changes across2,217items/final Stopped are verified. Canonical
solution/export remains blocked by the separately recorded403.
Retain all original sheets/footers/formatting, mixed IDs and source date text.
No research/funding judgement. Evidence: private source-expansion mrff-exact-key-*
and mrff-identity-repair-receipt.json (zero effects).

## NHMRC native register increment — 18 October 2026

The maintained database is the native SharePoint award-context list; Excel is only
the external source format and a separate processing copy. All 302 source records
passed native Excel extraction, source-owned updates and exact field readback.
Amounts match original decimal values; dates retain verified Excel1900 serials;
workbook hash, sheet and row provenance match. All stable IDs/operator notes and
1,915 MRFF rows were preserved. Same-packet replay changed zero item ETags across
all 2,217 list rows. The original workbook hash remained unchanged. Both NHMRC
flows are saved Stopped. Canonical solution/export integration remains pending.
Evidence: private source-expansion `nhmrc-native-consumer-verification.json`,
`nhmrc-native-replay-verification.json`, `nhmrc-consumer-final-stopped.json`.

Improvement applied: native array staging took 0.175 seconds versus 75.843 seconds
for the same 302-row per-item staging stage. This compares staging only, not the
full first-write run against a no-write replay. Carry array staging into MRFF.
Reuse the existing Excel connection and processing-copy route; create-table native
parameters are `table/Range` and `table/TableName`. Retain structured service errors
when a generic CLI HTTP400 hides the failing parameter. Preserve the original
source bytes and use indexed/unique SourceKey plus exact ETags for list updates.
MRFF's prepared adapter preserves every source ID format (including numeric IDs),
excludes only the declared trailing footers, and escapes OData keys. Next: deploy
MRFF collection, then native award refresh/replay. No research or funding judgement.

## Native NHMRC collection increment — 18 October 2026

The existing prepared collector was saved and run through M365 CLI/API. Its run
succeeded; all 14 original XLSX files plus the page/manifest were downloaded. Every
workbook SHA-256 matches its complete retained CLI original. Final native state is
Stopped. Native evidence: private source-expansion `nhmrc-native-run-verification.json`
and `nhmrc-final-stopped.json`. Next: native award-context consumer refresh/replay
preserving operator notes, reusing the qualified archive packet/upsert pattern;
then MRFF. Acquisition alone does not close G04 or imply funding assessment.

## Bronze funding retention — 18 October 2026

- [x] Reuse the existing Microsoft archive/orchestrator to retrieve original NHMRC and MRFF workbooks automatically, retaining all sheets, hashes, schema, publication/as-of dates and complete snapshot manifests; reuse existing ARC snapshots. Native acquisition/readback receipts: nhmrc-native-run-verification.json and mrff-native-run-verification.json (all originals retained; collectors Stopped).
- [ ] Commit complete source generations with replay and last-good recovery. Keep raw retention independent of opportunity/award admission and optional vertical filters.
- [ ] Build the selected typed award projection only after retention; verify one native source-to-archive-to-consumer path, source keys and replay using existing checks.

Details: [medallion source plan](../../../docs/FUTURE_SOURCE_ENRICHMENT.md#australian-funding-sources-and-medallion-retention--18-october-2026). These are implementation tasks, not completed native ingestion.


## Parallel adapter preparation — 13 October 2026

Use the [parallel assignments](../../../docs/PLATFORM_COMPLETION_PLAN.md#parallel-delivery-assignments--13-october-2026).
A funding helper may prepare a single source-specific adapter/mapping plus focused
checks from the selected G02 source; existing common normalizer, registry schema,
flow definition and package builder remain integration-owned. Official award
workbooks/API responses must retain full fields and source vintage in the shared
raw convention, with separate award projections and funder-scoped identities;
they must not be coerced into the opportunity schema. If the accepted award
consumer contract is missing, return its smallest proposed change for integration
rather than inventing a second registry or collector. H02/H03 native integration
waits for source qualification and current object ownership. Local preparation
does not close intake, replay, unattended operation or relationship acceptance.

## CLI delivery — 13 October 2026

Follow [the shared execution contract](../../workflow.md#cli-first-execution--13-october-2026).
G04-H02/H03/H04 deploy the smallest existing adapter/upsert diff using current source contracts and stable solution flow IDs. Consume committed full source evidence, then apply typed opportunity admission downstream. Preserve exact-zero/one/multiple-match branches, source-null values, reviewed fields and replay. Verify actual runtime adoption/run and source/list keys. No new hosted Python collector or per-opportunity approval queue.


## Historical local implementation and dated native evidence

The checked items below retain prior work; they are not a current completion certificate. Later active tasks supersede contradictory status or fixture-cleanup claims. No unverified native gate is closed by this history.

- [x] Record scope and acceptance requirements.
- [x] Inspect current inputs, dependencies and relevant platform objects. Reused the canonical normalizer and kept SharePoint/native objects out of the local adapter.
- [x] Implement: Implement independently testable adapters and one canonical ingestion workflow.
- [x] Verify: XML/API-shaped fixtures, malformed/incomplete batches, changed deadlines, archived rounds and failed-source isolation are covered locally; live source cycles remain open.
- [x] Record local and live evidence separately before closure; no unattended flow or schedule was activated.

## Historical review fixes — 2026-09-20

The HTML-calendar extraction route is retired. These commits remain historical evidence and must not be reinstated as automated intake.

- [x] Task: Apply review suggestion: hash the complete source row and reject duplicate calendar identities before candidate emission (03733b8).
- [x] Task: Apply review suggestion: suppress repeated calendar headers before candidate emission (f16c297).

## Hardened completion tasks — 2026-09-24

Apply the [hardened completion contract](../../../docs/PLATFORM_COMPLETION_PLAN.md#hardened-completion-contract). Dependencies below are execution gates, not evidence of completion. Keep raw/native receipts and actual identities in ignored `private/ops/`; reuse current evidence before rerunning a case. Partial/declined scope must be labelled explicitly.

- [x] **G04-H01 — Harden the admitted adapter boundary (local contract complete 2026-09-28).** Depends: G02-H01 and archived G01 baseline. Inputs: `scripts/grants_ingestion.py`, `scripts/grants_reviewed_import.py`, `scripts/grants_registry.py`, `tests/test_grants_sources_ingestion.py`, `tests/test_grants_reviewed_import.py`. Automated batches require catalogue admission, opportunity entity semantics, official row hosts, complete pagination, valid source identity/observation, and unique keys; malformed snapshots fail closed with diagnostics and failed iterators discard partial rows. Reviewed imports require stable source identity, official row URL, observed time and explicit review notes; the separate review path preserves evidence while machine feeds cannot set review fields. RSS/Atom/API normalization and merged source-observation history are covered. Focused source/ingestion, reviewed-import, flow-contract and registry suites pass 28/24/7/11 tests. This closes only local adapter contracts; no current opportunity source is admitted and native intake/readback remains open.

  Local trust-boundary subcheck: API-shaped rows use an explicit source-owned-field allowlist, so `ReviewStatus`, `ReviewNotes` and `CHHHSRelevance` are reset to canonical unreviewed defaults. The separately validated reviewed-import route admits review evidence. This does not admit a live source or close native intake gates.
  A supplied `OpportunityKey` in a reviewed-import row is now checked against the canonical source identity; mismatched and non-text keys fail closed instead of being silently replaced during normalization. Focused reviewed-import tests cover matching, mismatched and malformed keys.
  2026-09-28 local subcheck: direct batch and RSS/Atom parser calls reject coerced source identities/timestamps, and direct catalogue input must have text identity/intake, official host strings and a valid reconciliation shape.
  2026-10-03 cross-track identity-path tightening: G02's endpoint probe and G04's RSS/Atom parser now reuse `scripts/grants_source_identity.py`; feed identity comes from the configured structural path, and catalogue/ingestion reject path syntax that conflicts with `api`, `rss` or `atom`. Six catalogue, 33 ingestion and 16 probe tests pass. This makes no current feed eligible and does not close the native intake gate.
  2026-10-03 source-key preservation: canonical registry normalization, direct source batches, API identities, XML feed entries and in-memory catalogue IDs/hosts now reject padded stable identity values rather than trimming them into a different source/key. The focused suites pass: ingestion (37), registry (24), source probe (17), reviewed import (27). This closes only local boundary normalization risk; no source admission, list write or native intake acceptance is implied.
  2026-10-03 key-integrity hardening: delimiter-bearing `(Source, SourceID, RoundID)` tuples now use a JSON-encoded `GRANTX:` key basis, preventing aliases caused by the legacy `:` and `|round:` separators; delimiter-free identities keep their existing `GRANT:` keys. The reviewed-import path round-trips distinct `GRANTX:` rows and rejects the old delimiter key as a mismatch. Registry (15) and reviewed-import (26) tests pass. Any pre-existing tenant rows containing these delimiters require explicit old/new reconciliation before import; do not silently rekey them. This is local contract evidence only.
  2026-10-03 reviewed-import output boundary: the CLI now prints counts only; raw source rows, contact fields, review notes, exact keys and content fingerprints are omitted from stdout. Optional full receipts are restricted to ignored `private/ops/` and refuse overwrite. The focused reviewed-import suite passes 30 tests. This changes reporting/storage of local validation only; it does not admit records or alter the native flow.
  2026-09-28 iterator-boundary subcheck: catalogue enumeration failures return a fail-closed diagnostic; a batch iterator that raises after yielding data rejects and clears the entire partial snapshot. Focused ingestion tests cover both paths. This does not admit a source or prove native commit gating.
  2026-09-28 reviewed-import iterator subcheck: if a reviewed-row stream raises after yielding rows, the importer discards partial materialization and emits a stable contract error without leaking exception text.
- [~] **G04-H02 — Prepare a minimal executable native adapter/upsert.** Depends: G04-H01; G02-H02 applies to automated sources. On 2026-10-23, the existing reviewed-import flow was read back from its exact environment and flow ID, and its full definition, bindings, list identity, fields/indexes, rows and Stopped state were compared with the current local definition and retained preimage. The native graph matches the local reviewed-import graph after only site/list binding, existing authentication binding and platform metadata normalization; FlowAgent validation and preflight pass, with the existing SharePoint reference Connected. Its serial loop, blank identity and source conflict guards, duplicate/zero/one branches, ISO text serialization, update-time preservation of reviewer fields, stale-time ordering and fail-closed diagnostics are present. G03-H02 contains the correlated native runtime cases for create/replay/update, identity conflict, blank key, stale input and reviewer preservation. No native definition change was needed. The offline S0242 candidate remains excluded because its source hash is stale and its connector reference is missing; the mapping was resolved through the current native logical reference and installed connection readback. The exact current G03 readback is the rollback preimage; the older 07:24 FlowAgent backup differs and is not a rollback source. Private receipts: `private/ops/2026-10-23-g04-h02-native-adapter-private/`.
  2026-10-23 Conductor review reopened H02: fresh read-only native definition/bindings match the retained H02 preimage and flow state is Stopped, but the shared local/native graph permits equal-time conflicting source facts to update and rejects round-only identities accepted by the reviewed-import contract. The existing 84 focused checks pass without covering these gaps. Correct both native guards, preserve same-ID bindings and rollback, and capture focused runtime evidence before restoring H02 completion. Findings and exact private receipts are in `conductor/tracks/G04_grants_ingestion/review.md`; no native mutation or fixture submission occurred during review.
  2026-10-23 review fixes saved: the RoundID-only guard/lookup and equal-time source-fact conflict guard are corrected locally and saved to the same native workflow through ETag-guarded Dataverse clientdata PATCH. A response timeout was reconciled without resubmission; direct Dataverse plus FlowAgent readback match the candidate, preserve references/name/identity and confirm Stopped. The grants harness now passes 411 tests (2 optional skips). Exact receipts and documentation-pending handoff are in the existing G04 review. H02 remains partial pending native runtime proof of both fixes; H03/H04 remain open.
- [ ] **G04-H03 — Prove a complete intake cycle.** Depends: G04-H02, G03-H02 and G02-H02 for automated sources. Run one selected official source or evidenced reviewed batch through native flow, registry and isolated model refresh. Reconcile accepted/rejected/input key sets and row hashes, changed deadline history and untouched reviewer fields. Test truncated/empty/failed secondary source without loss of last-good rows. Output: private source/run/list/model receipts with exact counts and differences, plus public acceptance summary in `docs/GRANTS_DELIVERY_REVIEW.md`. A reviewed batch satisfies reviewed intake only, not automatic feed operation. Current blocker: G02-H02 has not admitted an official opportunity source and the existing evidence set contains no evidenced reviewed batch; the synthetic G03-H02 fixtures do not qualify. Do not submit a source batch or refresh the model until that input and the exact isolated model target are evidenced.
  2026-10-23 H03 gate check: G02's current qualification inventory still has zero admitted opportunity sources, and retained GrantConnect/Queensland Health/local discovery evidence contains no row-reviewed batch receipt. NHMRC/MRFF files are award/outcome data, ARC/RGS are award context, QGIP is candidate-only, and Grants Finder is metadata-only; none is eligible input. The private G04-H02 readback identifies the isolated list/flow but does not establish an exact isolated semantic-model target or nonempty last-good registry/model preimage. Therefore the G02-H02, G03-H02 and G04-H03 entry gates are not all met: no native flow submission, registry mutation, model refresh, or empty/truncated/failure injection was made. The unrelated Crossref CU21 refresh remains owned by its existing operation; it was not queried or touched. Resume only when an already-authorized official source is fully admitted or a row-reviewed batch with source/round identity and reuse evidence is retained, G03-H02's remaining duplicate-match limitation is resolved or explicitly bounded for the selected intake, and the exact isolated model plus nonempty last-good/rollback state are evidenced.
  2026-10-23 03:07Z execution check: `python3 scripts/grants_sources.py config/grants-sources.json` validated four rows, all currently `context_only`, `metadata_only`, or `candidate_only`; none is an admitted opportunity route. No evidenced reviewed batch is available in the current source/receipt set. The same-day native runtime receipt in `private/ops/2026-10-23-h02-s02-takeover/grants-runtime-acceptance.json` is synthetic create/replay/update evidence (fixture items recycled; final row count 0), not source intake or a last-good preservation test. The newer flow-definition candidate in `private/ops/2026-10-23-s0242/grants-reviewed-import-source-update-candidate-receipt.json` was not imported and its receipt explicitly says runtime verification is false. At this early checkpoint G04-H02, G03-H02 and G02-H02 remained open; the later G04-H02 native adapter readback below supersedes only G04-H02. No source batch was submitted and no model refresh was started. Resume H03 only after an admitted official source or evidenced reviewed batch and the exact isolated model/list target are ready; then retain last-good preimages and test the empty/truncated/failed path against nonempty accepted rows.

### 2026-10-23 isolated-model candidate readback

The existing recovery canary was opened read-only in the authenticated in-app browser. Its native Grants Registry partition points to the exact isolated registry list and contains 44 columns, but all six deadline-time fields are missing and the table is marked as containing no data. Twenty displayed refresh-history rows are terminal; the latest completed 9 October. No model mutation or refresh was submitted. Receipt: `private/ops/2026-10-23-g02-canary-target-readback/native-web-receipt.json`. This supersedes the absence of any candidate target identity, not the missing current rollback/consumer-isolation proof, schema parity or nonempty accepted last-good baseline. Those remain H03 prerequisites.

### 2026-10-23 G04-H02 native adapter readback

- The exact native flow remains `Stopped`; its solution connection reference resolves to the already-connected installed SharePoint connection. The current Grants Registry remains empty with versioning enabled (50 major versions), and `OpportunityKey` remains required/indexed/unique while `SourceID` is indexed/non-unique. No native definition, connection, target identity or schedule was changed.
- The current saved action graph and bindings match the retained G03-H02 readback exactly. Compared with the current local reviewed-import definition, all action semantics match after applying only exact site/list values, the existing authentication token expression and the platform-generated trigger metadata. The FlowAgent validator returns valid and preflight returns ready with 1/1 existing references connected. The 2026-10-23 S0242 offline candidate's source snapshot no longer matches the current local file and has a null connector reference; it was not imported. The native `installedConnectionReferences` readback supplies the qualified existing mapping.
- The `>1` existing-match failure branch is present in the saved graph but remains static-only: the list's required unique key prevents representing that state without weakening the live invariant. Keep this as the existing G03-H02 runtime gap; it was not treated as a tested runtime case here.
- The current FlowAgent backup captured at 07:24 does not match today's saved native definition and must not be used to restore it. The exact current definition/binding preimage and its same-ID reapply route are retained in the G03-H02 receipt and copied into the private G04-H02 pre/post evidence directory. The adapter already covers the reviewed-import shape, so no native update was necessary. G04-H03 remains blocked on an admitted opportunity source or evidenced reviewed batch and an exact isolated model target.
- [ ] **G04-H04 — Reconcile and hand over intake.** Depends: G04-H03. Export saved definition and compare with local intended action graph; record source-specific last-good restore and fixture cleanup; run `python3 -m unittest discover -s tests -p 'test_grants_sources_ingestion.py' -v` and reviewed-import/flow contract suites. Closure: every enabled adapter has accepted provenance/key parity and a recovery procedure; deferred adapters remain explicitly disabled. Two-cycle operational acceptance belongs to G07-H01.
  2026-10-23 dependency gate: G04-H03 is still not accepted (see the H03 checkpoint above and `docs/GRANTS_DELIVERY_REVIEW.md`). Therefore H04's post-acceptance native export/comparison, source-specific last-good restore reconciliation, fixture cleanup reconciliation and focused checks were not run. The last retained native readback is G04-H02's private pre/post evidence at `private/ops/2026-10-23-g04-h02-native-adapter-private/`: the reviewed-import flow was `Stopped`, its definition matched the intended graph after exact target binding normalization, and the isolated registry had zero rows. This is the last evidenced state, not a fresh H04 readback; no H04 handover or final-state claim is made. Exclusions remain: no admitted opportunity source or evidenced reviewed batch, no exact isolated model target/nonempty last-good model preimage, and the G03-H02 `>1` existing-match runtime branch remains unproved. Keep G04-H04 and G04 open until H03 passes and the H04 evidence is captured.

Track closure requires all applicable acceptance tasks above, the shared completion contract, and a review recording any explicitly approved exclusions. Local pass, source availability and import success are separate from native and operational acceptance.

## Original retention progress — 18 October 2026

CLI acquired all fourteen currently linked NHMRC annual outcome workbooks and
three MRFF detailed/summary/funding-rate workbooks. Original bytes, source pages,
source URLs/headers, hashes and every workbook sheet name are retained. Microsoft
archive retention passed exact CLI download/hash comparison for all originals and
manifest-last commits. CT.gov six full records and projection are retained too.
Receipt: `private/ops/2026-10-18-source-expansion/progress-receipt.json`.

Three manual native collectors are prepared but not deployed. Workbook collectors
compare the current complete official XLSX link set with the frozen source scope;
changed coverage fails before a commit. Native runs, typed funding projections,
study-list updates and replay remain open. NHMRC transformation conditions remain
unresolved; original retention does not admit typed rows. Six focused source capture
checks passed, including source-host restriction, duplicate identity rejection,
unknown-field retention and no partial commit after failed acquisition.

Lesson: preserve useful original data through a working CLI while the exact VS Code
recovery is unavailable; do not confuse retained files with deployed acquisition.
Reuse complete source lists, and retain source product/as-of distinctions before
linking grants. VS Code −3812 is a UI transport failure, not a new access requirement.

## Award fact bootstrap readback — 18 October 2026

- [x] Retain all 14 currently linked NHMRC original annual workbooks and three MRFF originals, all sheets and raw notices intact; verify Microsoft stored bytes/hashes.
- [x] Prepare the current detailed-sheet factual metadata projection: 302 NHMRC and 1,915 MRFF rows. Keep source scope/vintage and original provenance; exclude only two explicit MRFF footer rows. Do not infer active status, currency, eligibility or institutional attribution.
- [x] Create separate DEV award-context register, versioning/inherited access/unique SourceKey, source-only fields and protected OperatorNotes. Exact readback and replay both passed (0 inserts; 302/1,915 unchanged).
- [ ] Deploy/run the prepared native workbook collectors; connect repeatable native projection/consumer refresh with edit preservation and recovery. Bootstrap CLI parsing/import is local artifact/verification tooling, not a hosted runtime.

The factual bootstrap above supersedes earlier 'no typed rows admitted' statements
for this declared current-sheet scope only. No research use, narrative adaptation,
redistribution, whole funding-universe coverage or business acceptance is implied.
Evidence: `private/ops/2026-10-18-source-expansion/progress-receipt.json`.

## Isolated implementation recovery — 24 October 2026

See [recovery and validation](recovery-20261024.md). Existing task statuses remain unchanged; local recovered implementation is not native acceptance.

## NIH bounded native intake — 24 October 2026

See [bounded import evidence](../../../docs/NIH_BOUNDED_IMPORT.md). One real opportunity now exists in SharePoint: 32 registry fields, seven nominal occurrences and four byte-verified complete source response attachments. An empty optional URI defect was repaired and verified natively. The flow is Off. Attachment retention was an operator step; unattended collection, replay/recovery and model refresh are not closed by this unit.

Native same-input replay is now verified for this one NIH record: create skipped, update succeeded, one item before/after with the same ID, temporary multiline review note preserved exactly, original note restored with ETag protection, and review status/source fields/schedule/attachments unchanged. An empty-date substring guard defect was repaired and verified natively. This closes the bounded same-input replay check only; changed-source failure recovery, unattended archival and model refresh remain open. See the replay section of the same evidence document.

See [changed-deadline and last-good acceptance](../../../docs/GRANTS_LAST_GOOD_ACCEPTANCE.md): seven native synthetic fixture cases verify a newer deadline update, older/same-time conflicting rejection, incomplete identity, malformed JSON and empty-input preservation. Three local source-admission failures produce no eligible records. Real NIH fields/version/attachments remained unchanged through every snapshot; the exact fixture was recycled and the active list restored to its baseline. Flow Off. Multirow transactional rollback/concurrent writers and unattended source-to-model recovery remain outside this bounded result.

See [isolated-model refresh reconciliation](../../../docs/GRANTS_MODEL_REFRESH_ACCEPTANCE.md): native transactional Full refresh completed for only the existing canary's two grants partitions. One grant/32 fields and seven unique occurrences/11 fields each reconcile to SharePoint; source occurrence JSON and relationships pass, zero orphans/synthetic rows. Other 27 table counts and all 37 definition parts unchanged; SharePoint unchanged; no reports bound and schedule disabled. This closes the selected NIH isolated-model refresh gate, not unattended collection/archival/scheduling or main-report replacement.

See [final export and documentation reconciliation](../../../docs/GRANTS_SOLUTION_RECONCILIATION.md). Fresh canonical unmanaged solution version 1.0.0.0 contains 35 workflows and six connection references; all prior 34 workflow members are preserved. The grants export matches a fresh native graph and the portable source after exact target/generated-ID normalization; four repository auth expressions now match accepted native invoker semantics. A byte-identical grants addendum is saved at native document version 1.0 with inherited access; all 325 existing library files retain their identities/version metadata. Shared historical diagram generation and other owners' components are preserved. No import, reference rebinding, activation or overall release acceptance is claimed.


### Recurring NIH qualification increment — 24 October 2026

See [recurring qualification](../../../docs/NIH_RECURRING_QUALIFICATION.md). A disjoint native qualifier has actual recurring acquisition/archival proof, including four complete API JSON representations, the current original attachment ZIP, two attachment-capable successful ticks, injected failure receipts and scheduled recovery. Independently downloaded generations reconcile to source admission and ZIP membership/CRC. The qualifier is Stopped with a disabled daily candidate and faults removed; existing reviewed-import identity/bindings and register/model data are preserved. This is not full G04 or end-to-end acceptance: native projection/version-conditional register commits, durable scoped model refresh authentication, delivered failure alerts and canonical promotion remain open. Default owner failure subscription is not sufficient alert proof.
