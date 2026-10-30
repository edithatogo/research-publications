# Local-first outcomes CLI recipe

Current status: [implementation, verification and next action](../conductor/tracks/chhhs_outcomes_powerbi_20261021/plan.md#current-implementation-and-verification--30-october-2026).
That maintained list supersedes historical blocker/missing statements in this
chronological recipe. Source and saved-native implementation are distinct from
runtime, manual visual acceptance and integration. Only necessary changed-behavior
checks after implementation; no monitoring, automatic refresh or scheduled runs.

This increment reuses the outcomes track and existing relationship builders.
Canonical source and the sanitized CareOps module remain separate histories.
The source writer owns only its isolated checkout; native objects, authentication,
shared main and CareOps pins retain their current integrators.

## Prepare and compare locally

Select `.venv/bin/python` and verify Python 3.15.1. Use the `outcomes`,
`relationships`, `projections` or `reader` harness selection for affected work.
The harness remains offline. Existing `check --task all` is the integration gate;
do not repeat it after unrelated documentation edits. Docs need structural/link
checks, not mirrored application tests. Package/unpack only affected solutions.

`outcome_persistence.py` replays exact source bytes and their original reference
snapshots through `outcome_evidence.intake`. It retains explicit human edits and
all revisions. Reporting calls the existing eligibility/redaction projection;
facts and project bridges remain separate, avoiding multiplication of totals.

The initial adapter is a bounded journal in one existing SharePoint item, updated
with an exact ETag. Candidate field mapping is an existing plain multiline-text
field holding the journal; item ID and native ETag are outside that payload.
This is a technical candidate, not a selected/provisioned authoritative register.
An existing register with different semantics needs an explicit mapping adapter;
never replace it with this storage shape automatically. Journal text is capped at
60,000 UTF-16 code units and fails rather than truncating or silently sharding.
This bounded candidate does not implement a scalable cross-domain register.

Read the exact owner-approved list schema, field type/limits, item and ETag before
finalising the mapping. Existing item creation, uniqueness/index changes and
provisioning are separate candidates. Missing item/schema is not an empty store.
Do not copy authentication caches, create fresh clients, or broaden retained read
allowlists to acquire this evidence. No binding or native schema capture exists
in this lane, so its target-bound migration is blocked pending that evidence.

## Apply once, read back, recover

`scripts/outcome_intake.py` accepts a manifest of exact record files, reference
snapshot and reporting context. It validates the whole batch through the existing
revision rules, then prepares one paired-field update. `--apply` submits it through
`m365-qualified.mjs outcome-store`; without that flag it reads and prepares only.
The retained binding must already pin the exact list and include `outcomeTarget`
with `listUrl`, `itemId`, `journalField` and `projectionField`. This code does not
select a different client, renew login, provision a list or edit a binding.

`outcome_store.mjs` reads the current schema and item, requires two writable plain
Note fields, checks the exact preimage and applies one server-enforced `If-Match`
MERGE. Journal and derived projection are committed in the same item update.
Direct same-client requests disable redirects and bypass the SDK retry wrapper.
An exclusive durable send-intent file precedes the request. Lost responses are
reconciled by exact paired-field readback; unknown results never trigger a retry.

Use a new ignored directory per command, keeping records and receipts private:

```sh
.venv/bin/python -m scripts.outcome_intake --binding PRIVATE_BINDING --records RECORD_MANIFEST --references REFERENCES --context CONTEXT --output PRIVATE_NEW_DIRECTORY
# The same command with --apply performs the reviewed conditional update.
.venv/bin/python -m scripts.outcome_intake --binding PRIVATE_BINDING --recover-plan ORIGINAL_PLAN --output PRIVATE_NEW_DIRECTORY
# Recovery also defaults to preparation; --apply requires the candidate still current.
```

The record manifest is a JSON array of objects with `path` (relative to the
manifest) and optional `human_edits`. Context supplies `cutoff_utc`,
`source_snapshot`, `model_revision` and `report_revision`. Recovery restores the
exact original two field values against a fresh postimage ETag and refuses any
intervening field edit. It does not delete history items or roll back a whole list.
Neither a local fixture nor the executable transport proves native operation.

For flows, reuse the existing [same-record deployment helper](FLOW_DEPLOYMENT_HELPER.md)
and accepted SharePoint action examples. Do not guess the connector contract or
add an HTTP/premium connector. Existing stopped/no-send state remains unchanged.
A generated candidate, pack/unpack pass or saved definition is not runtime proof.

## Power BI and manual handoff

Prepare model/report candidates from complete frozen source definitions. Retain
all existing pages, parts and identities. Use the supported definition API only
after the owning client/resource/target and non-premium entitlement are qualified.
The legacy browser-session and saved-token entrypoints now prepare offline packets only. They do not execute a deployment.
No current private target binding/entitlement receipt is available in this lane;
do not claim the API is unavailable globally or infer entitlement from a helper.

If MFA/consent is required, provide the exact supported login step to the user.
For changed report pages provide a manual readability, keyboard, filter/detail
and recovery checklist. If a non-premium authoring API is unavailable, provide
an eligible manual import/edit handoff or record a blocker. No browser automation,
VM, capacity purchase, Copilot or premium feature is a fallback.

## Minimum evidence and reuse

Record source/package hashes, interpreter/dependency identity, exact selectors,
results and changed native inputs in existing private receipts. Reuse unchanged
checks. Native checks cover only changed behaviour: exact saved state/references,
one fictional example, replay and scoped recovery. Keep local, saved-definition,
runtime and visual outcomes separate. Do not add a new evidence registry, global
skill, MCP server or automatic retry/test-selection framework.

## Local commands and implemented reader subset

Run `scripts/outcome_persistence.py --help` for private prepare/project/schema
inputs. `scripts/prepare_outcome_reader.py --help` prepares additive TMDL tables
and an evidence-count/detail page from complete model/report definitions and
accepted card/table templates. It requires an already reviewed OutcomeProjection
M expression; it does not invent a source URL or silently embed fictional data.
The candidate includes explicit project-filter measures, individual-observation
plots and evidence drillthrough. Funding/capacity additions use the separate
builder below. Native filter behaviour and rendering remain unverified.

`scripts/deploy_report_definition.py --help` prepares a complete definition
update/recovery packet, refusing omitted parts, unreviewed changes and binding
changes. `deploy_canonical_report.py` delegates to the same isolated preparation
route. `deploy_measures.py` now prepares its legacy measure text locally and does
not drive a browser editor. A supported same-client native executor remains
blocked on exact target/client/entitlement and no-retry transport qualification;
none of these entrypoints submits a request or reads a token file.

Project-scoped CLI projections now accept repeated `--project-id` values. They filter facts through distinct bridge keys without multiplying records. This does not implement native Power BI filter propagation. Project detail is limited to eligible-linked identities; the complete withdrawal audit remains a separately scoped view.

The retained completion-owner binding was inspected without authentication changes: it pins SharePoint, Graph and ARM resources, not the Fabric/Power BI definition resource. Its absence of an active lock does not transfer ownership or qualify a new resource. Native definition-write qualification remains unresolved; do not broaden this binding.

The quantitative projection now exposes each eligible observation's estimate,
numerator, denominator, explicit value states, indicator/version, unit and cohort
identity. The reader candidate includes an individual-observation table and a
single-observation estimate measure; multiple selected observations produce no
pooled estimate. The chart and drillthrough additions are described below; none has been
verified in the native model.

The funding/capacity CLI projection now implements C01 active/known-led project
counts, C02 distinct evidenced participants and F01 award-start cohorts separated
by currency. It requires explicitly mapped complete inputs; existing ARC text
amounts are not silently parsed or promoted to institutional funding. Unknown
periods/lead evidence are counted, and FTE/training/application success remain
unavailable. The local model/report builder is described below; native source binding remains missing.

`python -m scripts.prepare_funding_capacity_reader --help` prepares additive
funding/capacity tables and a 1920×1080 detail page against a reviewed existing
FundingCapacityProjection expression. It preserves existing report parts and
keeps award currency/start cohorts separate. This implements local detail-page
preparation. The chart extension is described below; native source binding and
acceptance remain open.

The outcome reader now prepares a bar chart and explicit drillthrough/back
buttons using the existing repository visual contracts. Estimates are shown per
observation and suppressed for mixed indicator/version/unit/population/setting
contexts. The detail page carries the observation ID filter. Local structure
checks do not prove DAX execution, filter propagation, rendering or keyboard
behaviour; those native/manual exits remain open.

Funding candidates now include an award-start chart with explicit currency series
and navigation to the exact-decimal detail tables. The chart measure admits only
one currency/cohort, converts its display value without changing retained decimal
text, and returns blank on conversion failure. Native DAX/locale, currency-series
behaviour and rendering still require qualification; no exchange-rate comparison
or cross-currency total is supplied.

`python -m scripts.prepare_outcome_flow --help` now prepares an operator-qualified
frozen journal update for an existing empty isolated manual flow. It preserves
the supplied connection reference and trigger, reuses the standard SharePoint
HTTP action contract, disables retries, enforces an exact ETag, and reads back
after success/failure/timeout. Existing nonempty flows are refused rather than
replaced. This is a bounded pilot candidate, not dynamic untrusted-user intake,
a deployed persistence service or native recovery proof.

Outcome candidates now carry a project selector and explicit TREATAS bridge
measures for eligible counts and individual estimates. No bidirectional model
relationships are added. The evidence audit table remains a separate unfiltered
revision audit, not a project-scoped security surface. Native DAX/filter behaviour
must be checked before this candidate is used operationally. The frozen flow
candidate also passes the existing offline graph validator; connector/runtime
semantics remain unverified.

Relationship revision handling now wraps the existing grants relationship
normalizer with immutable corrections, withdrawal and replay checks. Corrections
retain lineage identity even when evidence changes the normalized key; stale forks
are refused. This does not replace source-key admission or promote candidates.
Dataset/software adapters are described below; native grant and project/output persistence is now implemented as recorded below.

The relationship revision CLI now also retains existing DataCite Dataset/Software
assertions, complete source records, manifest hashes and canonical-match counts.
It refuses promotion flags and cross-family corrections. Upstream source capture
validation/admission remains required; these checks do not authenticate source
bytes or create native relationships. The DataCite storage mapping is now implemented locally; authenticated application is deferred as recorded below.

`python -m scripts.project_output_links --help` prepares explicit project links
to publications, awards, datasets and software using complete supplied canonical
inventories. Candidate/withdrawn links stay in evidence records but not reporting
bridges; reviewed links are deduplicated at project/output grain. Review assertions
are caller-supplied, not certified by the tool. Native project/output storage is implemented below; real source-specific identity/admission remains unresolved.

User-assisted Azure CLI renewal subsequently completed successfully. Exact report
and bound-model reads pass with unchanged account, tenant and selection. The
model reports PremiumFiles storage; this is metadata, not a licensing verdict
or proof that a non-premium definition-write route is available. No write,
refresh or settings change was performed. Authentication expiry is resolved;
operation-specific authoring/entitlement qualification remains open.

## Current finish line

Use the maintained Conductor status linked above. Outcome and project/output
storage, existing-model bindings/report additions, qualified CLI definition saves
and the study path repair are implemented and have saved-state evidence. They are
not missing prerequisites. Native DataCite application, selected flow deployment,
real-source identity/period crosswalks and integration remain separate from the
runtime/manual verification still outstanding. Earlier discovery and renewal
receipts retain their original scope only.

## Bind and package the paired projection

`python -m scripts.prepare_outcome_binding` adds an `OutcomeProjection` expression
from an exact private target to a complete hash-bound model definition. It reuses
the existing model's SharePoint.Tables connector, selects one item, requires a complete projection and
preserves all other definition parts. It refuses to replace an existing expression.
Pass its returned expression hash and candidate to the existing outcome reader
builder. There are no embedded credentials. Power BI source authentication and
native M evaluation remain separate prerequisites.

For the manual-flow route, `prepare_outcome_flow --projection-field FIELD
--item-id ID` accepts the dynamic intake's paired plan. It saves and compares both
fields together using the existing accepted SharePoint action; trigger, connection
reference and recovery preimage remain unchanged. The CLI computes the validated
batch; the flow persists that frozen candidate. No activation or invocation is
implicit, and this is not an automatically scheduled ingestion service.

Storage decision: no native outcome register has been created by this lane.
The user requested reconciliation of existing registers before any new-list
recommendation. See the maintained [register inventory note](SHAREPOINT_LIST_REGISTRY.md#register-evidence-reconciliation--30-october-2026).

Native prerequisite disposition for this batch: the retained Toolkit SharePoint
read was stopped by `INTERACTIVE_AUTH_BLOCKED`; Azure renewal does not renew
that separate client. No fresh register schema is claimed. The bound semantic
model definition returned `EntityNotFound`, and the complete Fabric personal
workspace model inventory did not contain that model identity. Do not substitute
the other model, retry the same operation or infer a licensing denial. A supported
non-premium model-write route remains unqualified. No native writes occurred.

Verification: the implementation milestone passed 2,381 Python tests and 446
project checks plus the existing harness gates. Focused checks after preserving
the native definition `format` property and allowing a reader to use the owner's
original binding passed five Python tests and nineteen Node tests. No further
full suite or package reconstruction was run for this batch. Native end-to-end
qualification and integration/pin promotion remain incomplete.

## Register bootstrap execution — 30 October 2026

Retained Toolkit renewal completed. A fresh complete inventory returned 33 lists.
Fresh DORA Activity Registry, Grant Relationships, Studies and Source assertions
schemas do not implement the paired outcome journal/projection contract. Existing
registers and rows were preserved. The authorized RIMS Outcome Evidence list was
created with versioning, two dedicated plain Note fields and one empty fictional
qualification journal item. Private creation intents/responses and target identity
are retained in `private/ops/local-first-outcomes/register-bootstrap/`.

The selected target can be supplied to the CLI with `--target`; authentication
continues through the original retained binding and its original shared lock.
No credential or cache was copied. The exact source expression is prepared
privately. No tests, manual flow run, scheduled run or monitoring occurred.

Model reconciliation identifies the existing report-bound model as the routine
publication source candidate; the other Fabric-listed model is a different named
model and identity. No rebind or substitution was made. Its complete definition
and eligible write route remain unresolved; the source expression alone is not
a complete model update candidate. Final verification has not started.

### Semantic-model workspace reconciliation

CLI reconciliation supersedes the earlier model-route blocker: the report's
connection and dataset ID match a model in another existing workspace, not its
personal report workspace. The workspace-qualified Fabric definition request was
accepted and its existing read operation is being resolved. No model substitution
or report rebind occurred. The owning workspace reports dedicated capacity; that
metadata alone does not establish a premium dependency or qualify writes. Exact
identities and operation receipts remain private. No tests or runs were started.

The corrected workspace-qualified definition operation subsequently completed:
all 61 model parts are retained privately with their SHA256. An additive outcome
source-binding candidate and complete recovery preimage are prepared against that
exact model. The report remains bound to its original model; no native definition
write, rebind, test or manual run occurred. The actual report supplies a table
visual template but no cardVisual template, so full reader preparation must reuse
an accepted compatible visual rather than fabricate a native template.

## Deployed outcome increment — 30 October 2026

The existing cross-workspace semantic model and existing report now contain the
additive outcome changes. The corrected model operation and corrected report
operation both reached Succeeded. All 59 unrelated model parts and 73 unrelated
report parts are byte-identical to their preimages. Changed report JSON matches
semantically; changed TMDL matches after the server's object ordering/indentation
normalization. Complete raw preimages and conditional recovery inputs remain
private. Existing report/model identities and connection are preserved.

Native import exposed three concrete serialization issues, now corrected: measure
names must be model-wide unique; new pages need the accepted page schema; and the
exported server-managed linguisticSchemaSyncVersion property must be omitted from
report write/recovery payloads. Raw original exports remain intact. Existing table
visuals supply the summary style; no guessed card template is used.

The final source batch passed 2,381 Python cases, 446 project checks, 30 Node cases
and the remaining existing harness gates. No further test suites are planned.
The single fictional intake committed journal and projection together with one
write and exact readback. One standard manual model refresh was submitted with
NoNotification; its exact request is retained privately and must reach terminal
state before reporting runtime acceptance. No replay, recovery drill, schedule
change, notification, separate flow invocation or background monitoring was added.
CLI persistence and manual model refresh form this selected scenario; no cloud-flow
runtime proof or visual/keyboard acceptance is claimed.

### User-directed closeout — no monitoring

The user subsequently directed: “Don't monitor. Just implement then move on.”
Stop polling the submitted manual refresh; do not cancel, resubmit, query outputs
or install follow-ups. Implementation and saved-definition acceptance are complete
for this increment. The single intake is persisted; refresh terminal status and
end-to-end runtime acceptance remain unverified. Earlier next-action wording to
continue tracking that request is superseded. Resume runtime verification only
on a new explicit request. No further test suites or package rebuilds are needed
for this closeout.

## Project-output link revisions

The existing `python -m scripts.project_output_links --input INPUT --output OUTPUT`
command keeps its legacy snapshot payload. Use `operation: "revise"` with `history`,
`record`, `inventories`, `complete`, `revision_id`, `supersedes` and `reason` to append
a revision and emit current bridges. The first revision uses `supersedes: null`;
later revisions name the current predecessor. Use the existing `status: "withdrawn"`
record disposition to retain history while removing its reviewed bridge. Reusing
a revision ID with identical input is a no-op; conflicting reuse and stale forks
fail. Every revision retains its exact reference inventory and hash.

Use `operation: "project-history"` with `history`, current `inventories` and
`complete` to rebuild the current view. Missing current canonical identities fail
explicitly; old evidence is not rewritten. Outputs remain private and exclusively
created. This implements local revision-aware intake/projection, not native
relationship storage or independent approval of caller-supplied review assertions.

### Native typed relationship persistence — 30 October 2026

The existing Grant Relationships register is the target for the four accepted
G06 relationship types. The bounded native read found two existing candidate award
links, versioning enabled, and a unique indexed RelationshipKey. Both existing
records remain untouched. This lane owns only its additive RelationshipHistory
field candidate and explicitly fictional qualification row, not those legacy rows.

`scripts/relationship_intake.py` extends the existing immutable revision ledger.
It prepares one typed item plus its full history atomically, preserves URL
annotations and refuses human-edited projections, stale predecessors, history
replacement and new confirmed admission. Corrections retain native item identity;
withdrawal retains history and removes confirmed/reviewed projection status.
Legacy rows without a ledger require explicit adoption and are refused by default.
DataCite source assertions and project/output links retain their separate contracts;
they are not silently admitted to the four-type grants register.

CLI recipe (all arguments below are ignored private files/directories):

1. Prepare `{"operation":"schema"}` and an exact existing target containing
   `listUrl` and `title: "Grant Relationships"`. The schema operation adds only
   the optional plain Note field RelationshipHistory; it does not create a list.
2. Run `node scripts/m365-qualified.mjs relationship-store BINDING TARGET PLAN NEW_RECEIPTS`.
3. Read a lineage with a plan containing `operation: "read"`, `item_id` (null for
   initial key lookup), and its normalized `key`. Preserve the returned snapshot.
4. Prepare input `{snapshot, revision}` with the existing ledger arguments using
   `.venv/bin/python -m scripts.relationship_intake --input INPUT --output PLAN`.
5. Apply with the same guarded command once. New items require the unique key to
   be absent; updates require the exact preimage and ETag. Readback reconciles an
   uncertain response without resending. Never reuse a receipt directory.
6. Recovery is a reviewed compensating revision through the same conditional
   route, using retained before/after evidence. Do not erase history or delete a
   field containing records. An uncertain result requires exact read reconciliation
   before any further write; no automatic recovery drill is performed.

The wrapper retains the original client's authentication and lock, disables write
retries/redirects, and validates the complete domain plan with repository Python
3.15.1 before authentication. Only the bound typed fields and history are updated;
Title and unrelated fields are preserved on update. Receipts become invalid for
an unchanged-candidate claim when target identity, schema, preimage/ETag, domain
plan or relevant source inputs change.

**Native blocker:** the first adapter metadata GET returned HTTP429 before any
mutation. No schema field or fictional row was created, and no retry was sent.
The exact candidate and receipt are retained under
`private/ops/local-first-outcomes/relationship-persistence/`. Next action is one
explicit resumption of the same pinned target after throttling clears, then the
single fictional create/readback. No polling, scheduled run, refresh or flow run
is part of this increment. Native correction/replay/recovery are not claimed.

**Native continuation accepted — 30 October 2026:** after the user completed the
retained Toolkit renewal, the additive history field and fictional candidate were
each applied once to the existing Grant Relationships register. Exact schema and
candidate readback passed. Both pre-existing records retained all prior fields,
GUIDs, ETags and timestamps; only the response-generated `odata.id` annotation
varied. Three rows are now present. The previous native blocker is resolved for
this create/readback scope. Private receipts are in `relationship-persistence/`
(`acceptance.json`, `schema-authenticated-once/`, `candidate-authenticated-once/`).
No tests were rerun, and no monitoring, scheduled runs, refreshes, replay or
recovery drills occurred. This does not admit real relationships or qualify the
separate project/output and source-assertion families.

### Project/output native persistence — 30 October 2026

The existing RIMS Outcome Evidence item now has dedicated plain Note fields
`ProjectLinkJournal` and `ProjectLinkProjection`. This reuses the bounded paired
journal design without changing OutcomeJournal/OutcomeProjection or extending
Grant Relationships' four grant-specific types. No new register or item was
created. Project-link revisions and retained canonical inventories share one
conditional item update; only current reviewed assertions enter derived bridges.
The existing project/output contract remains authoritative for publication, award,
dataset and software links. Review labels are caller assertions, not independent
business approval or source admission.

`scripts/project_link_intake.py` reuses `project_output_links.py` and the qualified
`outcome-store` transport. It rejects altered stored projections, incomplete
inventories, unresolved identities, conflicting revisions, stale predecessors and
field-capacity overflow before mutation. The transport refuses stale ETags and
preserves other fields; uncertain writes are reconciled by readback without resend.

CLI recipe, with all targets/inputs/receipts in ignored private paths:

- Bootstrap the two dedicated fields on the existing versioned outcome register:
  `node scripts/m365-qualified.mjs project-link-schema BINDING TARGET INITIAL_PAIR NEW_RECEIPTS`.
  Initial pair must be the empty project-history envelope and its matching
  projection. Existing nonempty fields are preserved; never reuse a send directory.
- Prepare, or apply once with `--apply`:
  `.venv/bin/python -m scripts.project_link_intake --binding BINDING --target TARGET --input REVISION --output NEW_RECEIPTS --apply`.
  Target carries the existing list/item and the two dedicated field names.
  Revision uses existing `append_revision` inputs, including complete typed
  inventories, explicit predecessor and reason. Default is read/prepare only.
- Recover business state with a compensating revision against a fresh snapshot;
  retain history. Exact preimages and intents support separate conditional recovery
  where authorized. No automatic deletion, history erasure or recovery drill.
  Schema errors stop the batch; read saved intents and reconcile actual fields
  before resuming. Target/schema/preimage/input changes invalidate prior receipts.

Native qualification completed with one clearly fictional project-publication
candidate. Two fields were added, then initialized together; the candidate was
saved once and read back exactly. Existing outcome journal and projection remain
byte-identical. Grant Relationships was not mutated. The candidate creates no
reviewed reporting bridge. Private evidence:
`private/ops/local-first-outcomes/project-link-persistence/acceptance.json`,
`schema-once/`, `intake-once/`, and `outcome-preservation-read/`.

Four focused planner tests passed after implementation, covering all four output
kinds, unchanged replay, corrections/withdrawal, human-edit refusal, stale and
conflicting revisions and incomplete inventories. Native scope is the single
fictional create/readback only; other kinds and correction/replay/recovery have
local evidence only. No model/report deployment, refresh, flow invocation,
monitoring or scheduled run was performed.

### Project/output semantic model and report candidate — 30 October 2026

`scripts/prepare_project_link_reader.py` adds a ProjectLinkProjection expression
using the accepted SharePoint.Tables source route and the exact persisted item.
ProjectOutputLink retains all current dispositions and evidence identities;
ProjectOutputBridge imports only the persisted reviewed bridges and deduplicates
project/kind/output triples. ProjectLinkProject filters both through explicit
single-direction model relationships. The new report page contains a project
selector, reviewed-link count, reviewed links and current evidence audit. Existing
model tables, report pages, default active page and binding identities are preserved.
No filtering of other existing report pages is implied by the new selector.

Prepare through `.venv/bin/python -m scripts.prepare_project_link_reader --model
MODEL --report REPORT --target TARGET --model-sha256 HASH --report-sha256 HASH
--output PRIVATE_CANDIDATE` (one command). Use the existing definition packet and
same-client one-send deployment route. Fresh complete preimages, semantic part
deltas and API-compatible recovery packets are retained privately under
`private/ops/local-first-outcomes/project-link-report/`. Reconcile any intervening
definition change before reusing the candidate; never overwrite a newer preimage.

**Native blocker:** the single model update reached terminal Failed with
`Dataset_Import_FailedToImportDataset`: “Can't deploy as target because model is
refreshing”. Complete definition readback confirmed every preimage part remained
byte-identical. The dependent report update was not submitted. No refresh status
was inspected, no refresh was cancelled/resubmitted, and no monitoring or scheduled
work was started. Resume only on a new authorized continuation when the model is
available; capture/reconcile fresh definitions first. Saved definitions, refreshed
runtime data and manual visual acceptance remain separate claims.

The focused additive-builder check passed after implementation, covering preserved
parts and identities, exact target binding, current-review bridge source, model
column construction and collision refusal. Existing persistence tests were reused.

**Project/output definitions deployed — 30 October 2026:** the explicitly requested
single history check established that the prior refresh finished Failed because
`Study archive folder missing or duplicated`; four attempts were internal to Power BI.
No new refresh was started. After reconciling fresh complete definitions, the model
and report additions were each saved once and read back successfully. All 64
unrelated model parts and 83 unrelated report parts are byte-identical. Changed
TMDL matches after service formatting/declaration-order normalization; changed
report JSON matches structurally. The previous deployment blocker is resolved.
The study-source failure remains a runtime blocker; refreshed data and manual
rendering are not claimed. Other RIMS completion/integration chats were inactive;
no overlapping active native writer was found. Evidence and recovery packets are
under `project-link-report/after-refresh/`; no monitoring or scheduled run was added.

### Study archive path compatibility correction — 30 October 2026

The retained failed refresh reported a missing/duplicate study archive folder.
A bounded complete read of the 171 Studies registry path references found two
URL conventions: six literal-space paths and 165 percent-escaped paths. The
sampled escaped URL resolves to an existing exact archive file; its parent folder
names were independently read from the existing Documents library. The model's
ReadStudy function compared decoded SharePoint Name values directly with escaped
URL segments, so the latter could not match.

`scripts/prepare_study_archive_path_fix.py` changes only the folder and filename
predicates inside SourceRelationshipEvidence.ReadStudy: accept the literal name
or Uri.EscapeDataString(Name). The existing site gate, exactly-one-match checks,
folder/file type checks and study identity/content validation remain intact.
Ambiguous matches still fail; no missing-source suppression, archive copying,
register rewriting or alternate source was introduced. The existing register-read
CLI guard now also permits bounded GET items queries on GUID-addressed lists on
the already-pinned site, using the same auth owner and fixed query-option guards.

The fresh complete model preimage, candidate, single-send receipt and recovery
packet are retained in `private/ops/local-first-outcomes/study-folder-fix/`.
The focused changed-behavior check passed after implementation. No report change,
new refresh, monitoring, scheduled run or source-record mutation was performed.
A future separately authorized refresh is needed to establish end-to-end runtime
success; saved definitions alone do not provide that evidence.

Post-terminal native readback matches the complete candidate byte-for-byte; all
69 unrelated model parts are preserved. The existing project/output additions
and report remain intact. Saved-state acceptance is recorded in the private
`study-folder-fix/acceptance.json`; runtime confirmation remains unverified.

### DataCite source-assertion persistence — local preparation

`scripts/source_assertion_persistence.py` maps retained Dataset/Software reference
assertions into the existing Source Assertions fields. SourceKey is a stable
namespaced digest of the original evidence lineage; SourceID/RelatedID retain
current source identities. SourceProjectionJSON holds the current active assertion
(or an empty assertion list after withdrawal). SourceProvenanceJSON holds the full
immutable revision history, original SourceRecord objects, source snapshot/manifest
identities and history hash. The existing relationship revision validator remains
authoritative. This mapping does not authenticate source captures or promote any
identity, canonical, mutation or grant-admission flags; upstream capture validation
and review remain separate. SourceURL remains blank rather than inventing an
archive/source URL absent from the input contract.

All fields already exist in the retained Source Assertions schema. No new list or
column is proposed. Title is supplied only for a new row; updates never include
Title, OperatorNotes or unrelated columns. Legacy rows without this adapter's
provenance format require separate explicit adoption. Changed human-managed
projection/summary values, stale ETags, conflicting source keys, revision forks,
family changes and field-capacity overflow refuse a write candidate.

Offline CLI:

```sh
.venv/bin/python -m scripts.source_assertion_persistence \
  --input private/ops/INPUT.json \
  --schema private/ops/RETAINED_SCHEMA.json \
  --output private/ops/NEW_CANDIDATE.json
```

Input is `{snapshot, revision}`. Snapshot is null for creation or exact
`{item_id, etag, fields}` for updates; fields contains only the nine mapped columns.
Revision uses the existing relationship ledger's record/revision_id/supersedes/
state/reason contract. Output is exclusive and private, with schema check outcomes
and native_ready=false. `request(plan,current)` produces a bounded create/MERGE
request only after exact preimage reconciliation; identical replay produces no
write. `reconcile(plan,current)` classifies uncertain effects without authorizing
resubmission. The guarded executor below now reuses these offline functions.

Before a later authorized native application: qualify the exact register, versioning,
complete unique SourceKey lookup, writable plain Note fields and unique indexed
SourceKey. The executor binds the prepared request to the existing same-client
one-send transport with durable intent and exact readback. No schema constraints are changed
implicitly. Unknown retained-schema properties remain unverified. A fresh candidate
or schema/preimage change invalidates prior native assumptions. Recovery is an
explicit compensating revision; never erase history or silently adopt another
producer's row.

Local evidence: five focused tests passed; fictional Dataset and Software candidate
packets were generated against the retained schema (10 pass, 7 unverified property
checks). Private receipt: `private/ops/local-first-outcomes/datacite-persistence-local/`.
No live authentication, tenant read/write, refresh check or monitoring occurred.
Native application remains deferred while the refresh may consume existing source
assertions; local preparation is not native completion.

Guarded executor wiring is implemented locally in `scripts/source_assertion_store.mjs`
and `scripts/source_assertion_executor_policy.py`. Future authorized invocation:

```sh
node scripts/m365-qualified.mjs source-assertion-store \
  PRIVATE_BINDING PRIVATE_TARGET PRIVATE_CANDIDATE NEW_PRIVATE_RECEIPTS
```

Target JSON contains exact `listUrl` and `title` for the existing Source Assertions
register on the retained site. Candidate accepts the prepared packet or its plan.
The wrapper validates private paths and domain policy before authentication, then
uses its existing client and lock. Fresh metadata, schema and identity checks must
pass before a durable exclusive send intent precedes one write. It performs one
postimage read; uncertain effects prohibit resubmission. Replay performs no write.
No schema constraints or authentication bindings are changed automatically.

Five fake-transport tests cover create/lost-response reconciliation, conditional
update and human-field preservation, replay/concurrency/schema refusal, durable
intent failure and uncertain readback, plus target/domain rejection. These and
the five domain tests passed after implementation. The relationships harness
selection includes the executor tests. No authenticated executor invocation,
SharePoint access or refresh check was performed.

### Real source intake proposal mapping — 30 October 2026

`scripts/prepare_real_research_intake.py` maps complete retained DoRA activity and
Award context snapshots to proposed funding_capacity contract records and explicit
candidate project/output award links. It does not admit them into reporting tables.
Original source rows, native identities and per-row hashes remain in private output.
DoRA Project ID is namespaced as a proposed project key; repeated IDs stay ambiguous
rather than being merged across sites or observations. PI name/email fields produce
source-supported role assertions with unresolved person identity and participation
periods; project dates are not substituted for participation dates. Missing finish
dates are unknown, not evidence of an ongoing project. No institutional leadership,
currency, Excel serial-date conversion or attribution is inferred. Only an explicit
unique project_id in award RelatedIdentifiersJSON can propose an award link; titles,
organisation names and PI names do not establish relationships. Candidate links use
the existing project_output_links field contract and never acquire reviewed status.

CLI: `.venv/bin/python -m scripts.prepare_real_research_intake --projects PROJECTS_JSON
--awards AWARDS_JSON --output PRIVATE_NEW_JSON` (one command). Inputs are complete
native collection envelopes; continuation markers are refused. Output contains
projects, awards, participation, proposed_links, unmatched and ambiguous records.
These are proposals with unresolved gaps, not approved canonical inventories or
inputs ready for metrics. A future canonical-person/source reconciliation is needed
before admitting participation; duplicated project IDs need explicit resolution.

The bounded native read captured 442 activity records and 2,217 award-context
records, with no continuation. Private proposals contain 442 project candidates,
2,217 award candidates, 442 unresolved PI assertions, zero proposed award links,
2,659 unmatched cases and 92 ambiguous source rows (not 92 distinct projects).
No exact project association was supplied by the inspected award source contract.
Evidence: `private/ops/local-first-outcomes/real-intake/{projects,awards,proposals}.json`.
Two focused source tests passed after implementation. No register write, approval,
model change, refresh check or monitoring occurred.
