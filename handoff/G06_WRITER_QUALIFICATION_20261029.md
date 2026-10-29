# G06 destination and candidate writer qualification

Owner: chat `01a18664-fb04-7d72-8ef9-bf21b2c81844`, following the user's explicit
handoff after the parent chat stopped. Source worktree:
`/Users/doughnut/.codex/worktrees/rims-retained-candidates/chhhs-research-publications`,
branch `codex/g06-writer-qualification`. Owned source: the G06 candidate submission
module and its focused tests. Earlier ARDC assignments remain historical; no
collector, schedule, sharing or unrelated source scope transfers.

## Verified destination

The exact existing list was added to the retained Toolkit binding, preserving a
private byte preimage and all other binding fields. Same-client SharePoint renewal
and exact guarded readback passed. Complete current reads contain 93 fields,
three views and two candidate rows without paging. Both rows match the earlier
accepted candidate identities, citations, confidence and review state. The unique,
required indexed RelationshipKey, versioning, unique permissions and effective
add/edit/delete permissions pass. No real candidate create is presently required.

Private evidence remains with its existing checkout under
`private/ops/2026-10-29-g06-destination-qualification/`, including
`destination-read-qualification.json`; renewal evidence is under
`private/ops/2026-10-29-g06-destination-renew/`. Do not copy bindings or credentials
into this worktree. These observations do not establish future access or writer
runtime acceptance.

## Writer implementation and acceptance

`scripts/g06_candidate_writer.mjs` persists an exclusive, fsynced per-list/key
intent before invoking a submission callback. A second invocation after an
uncertain send refuses another submission even when the native key is absent.
Existing matching rows retain every value and human review state. Five offline
tests pass for submission ordering, saved readback, zero-write replay,
uncertain-send and post-create readback-failure refusal, conflicting existing
identity preservation and target/candidate rejection.

`scripts/g06_native_qualification.mjs` connects the module to the existing pinned
Toolkit SDK/account/tenant/resource and shared workload lock. It blocks interactive
fallback, validates cached and renewed identity, and uses the SDK's direct transport
with exact URL/method/body guards, one wire attempt, disabled redirects and no
automatic mutation retries. Private bindings and evidence remain in their existing
owner checkout. Its command arguments are private binding, private scope, exclusive
evidence directory, phase (`inspect`, `fixture`, `recover`) and (only for recovery)
the original evidence directory. Never replay an uncertain mutation; reconcile the
exact key or recycle identity and retained intent first.

The exact current downstream-effects gate passed: zero modern rules/Quick Steps,
zero active list email/SMS alerts, operator-only ACL, and one existing Microsoft
list-view push subscription with its exact eleven platform receivers. The existing
qualified notification classifier was reused. No subscription, receiver, rule,
sharing, flow or schedule was changed. Effects evidence:
`private/ops/2026-10-29-g06-effects-qualified/`.

Native qualification passed on one explicitly labelled fictional candidate using
existing award/publication references and an example.invalid evidence URL. One
create was saved/read back, replay submitted zero writes, recycle/restore recovered
the same native item ID and exact fixture values, and final recycle left the two
original relationship rows byte-equivalent at the declared field scope with their
original ETags. Schema and views match their preimages. Four native mutations total:
create, recycle, restore, final recycle; zero automatic retries. The fixture is
retained recoverably in the recycle bin and is absent from the active list.

The first run stopped before cleanup because SharePoint response metadata URI
presentation changed between identical row reads. Review confirmed only
`__metadata` differed and the ETag stayed equal. The comparator now excludes that
response metadata while separately requiring original ETags and every business
field. An explicit recovery phase consumed the original create evidence and
refused any new create. No native creation was retried.

Authoritative acceptance: `private/ops/2026-10-29-g06-writer-recovery/acceptance.json`;
original submission: `private/ops/2026-10-29-g06-writer-native/`; stable intent and
recovery journals: `private/ops/2026-10-29-g06-destination-qualification/writer-journal/`.
An independent final read through the existing `m365-qualified.mjs` entry point
also passes: `independent-final-acceptance.json` in the recovery directory. It
compares every returned business field and separately compares original ETags;
only OData response metadata and verbose deferred-navigation stubs are excluded
when comparing the two native response formats. The active list has exactly its
two original rows, with the qualification fixture absent.
This completes the bounded destination/writer qualification objective. Broader
G06-H01 authoritative mapping, H02 model/cardinality and H03 reviewed-link acceptance
remain open; no confirmed funding relationship, model or report change is claimed.

Validation: five focused Node tests and syntax checks pass; `git diff --check`
passes. The existing qualified owner checkout's Python 3.15.1 ran the required
integration milestone: 3,052 unittest cases (12 optional skips), 454 project checks
and web-first contract validation passed. Its unchanged broader source was not
copied into this worktree; new writer source is separately covered by Node tests
and the exact native receipts. Logs remain in
`private/ops/2026-10-29-g06-integration-checks/`.

## Proposed shared-plan update for integration

Under G06-H02/target, record the bounded destination/writer qualification as passed
with the acceptance path above. Retain H02's unchecked model/cardinality and H03
reviewed-link requirements. Next operation: use this qualified candidate-only
writer for a separately validated new candidate slice; preserve current human
review/history, recheck effects and exact preimages before effects, and retain
the stable per-key journal. Do not repeat the completed fixture or broaden this
receipt to other relationship types or lists.

## G06 review decision — latest direct user step

Current chat/title: `RIMS — G06 — Review and close out`; current worktree is the
standard SSD path recorded below, on `codex/g06-review-closeout`. The review covers
the existing G06 writer, incremental and RIMS source changes and their exact
retained acceptance evidence. No additional native object, authentication or
shared integration scope was taken, and no lock was removed or bypassed.

Two material issues were fixed in the incremental source: source-context
crosswalks now agree with each candidate's exact publication/award identities;
actual Python 3.15.1 and optional baseline integrity are checked before native
effects, with a frozen baseline and failure receipt. The first context regression
failed before the fix; thirteen Node and twenty-three Python cases now pass.
The unchanged real two-candidate packet passes the stricter validator with zero
native calls. Review fixes are committed as `c7c4bba0`. Existing native writer/recovery assertions still pass documentary
readback; incremental completion/native acceptance files remain absent.

Review report: `conductor/tracks/G06_grants_relationships/review-closeout-20261029.md`.
Decision: source review complete, whole G06 closure refused. The prior full-source
integration failures, missing native incremental/RIMS cycle, H01 authoritative
mapping and H02/H03 model/review gates remain explicit. No new API call, native
mutation, schedule/send/sharing change, model refresh or repeated fixture occurred.
ARDC remains separately assigned with the stopped baseline and ready partial
local output described below; this review does not close that work.

## Incremental-processing continuation

Current user assignment: G06 incremental processing, same chat/worktree and exact
relationship list as above. Additional owned files:
`scripts/g06_incremental.mjs`, its focused tests, the `apply` phase in
`scripts/g06_native_qualification.mjs`, and the incremental Conductor leaf. Parent
retains shared AGENTS/workflow/skill and cross-track plan edits. Title was aligned
to `RIMS — G06 — Connect incremental processing` during this step.

Local implementation and ten focused tests pass. The accepted-source native
bootstrap stopped before authentication/request at an existing shared read lock
whose PID74036 is absent. The lock was preserved, no source pin was added, no
native candidate was created and no delivered receipt was produced. Pending work:
specific lock exception, exact publication-source pin/readback, native bootstrap
and unchanged-source replay. Do not label this step delivered from preparation or
unit tests alone. See the incremental leaf for the CLI/job/receipt contract.

ARDC remains separately assigned to this chat by the coordinating chat's corrected
user direction, to resume at the G06 safe checkpoint. Latest actual inspection:
2,452 completed baseline checkpoint pairs; only `weekly-full-reconciliation.json`
exists at the inspected reconciliation glob; no baseline-reader or Activities
pipeline process was found, and there is no reader lock. No current Activities
archive target or persistent Activities journal is pinned. Last local secondary
projection covers66,172activity records with zero alias matches, not full coverage
and not SharePoint delivery. Do not claim collection is running or complete.

ARDC component ownership/next operations (this chat, without transferring shared
authentication or another operation): preserve/reuse the historical accepted
general registry/RIF-CS baseline and weekly collector; reconcile/resume the
stopped current baseline reader from hash-verified pages after the shared-lock
condition resolves; qualify the Activities exact-ID archive target/writer using
the existing tools; save a coverage-labelled secondary candidate/status output
in SharePoint; then connect the existing RIMS consumer and finish scoped review
and material fixes. The historical general registry collector does not establish
any of these newer Activities/filter/consumer exits. No ARDC native continuation
has started in this G06 step.

## Connect RIMS continuation and worktree recovery

The latest direct user assignment is G06 Connect RIMS. Current source owner is
the same chat. The original home-directory worktree disappeared during edits;
Git retained committed source through `9af7a9d8` but marked the checkout prunable.
An exact app-managed replacement operation reported success, but its directory
was also absent and prunable when inspected. No missing worktree was reset,
pruned or cleaned. This turn's own uncommitted edits were reconstructed from
the exact tool patches in a standard Git worktree at the verified repository:
`/Volumes/PortableSSD/GitHub/RIMS/g06-connect-rims-worktree`, branch
`codex/g06-connect-rims`. This is a CLI fallback, not an app-managed checkout.
The shared dirty checkout, private bindings and mutation journals remain in place.

Owned additional source: the processing-receipt adapter in
`scripts/connect_g06_rims.py`, which calls the unchanged
`scripts/prepare_funding_relationship_context.py`, its connection in
`scripts/g06_incremental.mjs`, focused RIMS tests and this scoped documentation.
The source connects only verified native-delivery rows to the established
consumer; no new native object ownership or model-write scope is assumed.
Native-only intermediate receipts cannot advance a processing checkpoint, and
the final receipt is written only after the consumer packet is saved successfully.

Focused verification passes 23 Python and 10 Node cases on explicitly selected local
Python 3.15.1/Node runtimes. New native integration remains unverified: the last
lock check still found the recorded read PID 74036 absent, and no exception to
preserve/release its orphaned lock has been given. It has not been touched.
The exact publication-source pin addition and native bootstrap/replay are pending.
No fresh native request or model/report/list mutation was made for Connect RIMS.

Retained-native preparation output is in this new worktree's ignored
`private/ops/g06-connect-rims-retained/rims-consumer.json`. It hashes the actual
completed writer readback and accepted source packet, preserves its recorded
observation time, yields 2 candidates/0 confirmed and matches the supplied accepted
identity baseline. It explicitly reports no new live refresh or model change.

Next G06 operation is a fresh incremental native delivery plus this consumer
output once the shared-lock condition is resolved, then model/refresh acceptance
only if its actual current material requires an update under the existing
isolation/rollback gates. Broader G06 completion and the separately assigned,
unfinished ARDC Activities/filter delivery are not closed by this source work.

Required broader source checks were attempted in this isolated worktree. Project
validation passes 454 checks. Full unittest discovery ran 1,236 tests with two
failures, eleven errors and twelve skips; diagnostics identify inherited missing
modules, definitions, target templates and optional openpyxl, plus existing harness
and probe inconsistencies. Web-first validation fails on dependency references
and five missing OpenAlex M files required by the frozen baseline. None of the
existing runtime files have changed hashes. The historical baseline was not
repinned, missing dirty source was not copied from another lane, and these broader
gates are not claimed green. Logs are in this worktree's ignored
`private/ops/g06-connect-rims-checks/`.

## ARDC resumed execution after the G06 safe checkpoint

The coordinating chat conveyed the latest direct user assignment to execute ARDC
after preserving the bounded G06 work. G06 source is committed as `24470fbe`;
its live incremental/RIMS cycle remains unaccepted. Current title is
`RIMS — ARDC — Deliver partial candidate output`; the current operational owner
is this chat in the standard SSD worktree recorded above. No other chat was sent
messages and no shared Conductor/AGENTS/workflow/skill file was edited.

Actual ARDC execution resumed: the existing RIF-CS secondary filter processed a
frozen inventory of all 2,452 retained complete page/hash pairs. It verified each
pair, processed 66,172 activity records and produced zero alias matches. The prior
derivative had disappeared with the home-directory worktree, so this was required
reconstruction, without downloading source pages or reacquiring provider data.
4,366 pages are declared by the retained baseline manifest; 1,914 remain unread.
Page coverage is not an activity-level coverage denominator, and zero alias
matches do not establish source irrelevance. This is not an Activities API capture.

Durable ignored output in this worktree:
`private/ops/ardc-delivery-recovery-20261029/` contains the frozen inventory,
candidate projection, processing receipt and concrete publication plan for two
hash-named immutable candidate/coverage artifacts. The plan identifies the exact
existing site/library from retained native evidence and a dedicated proposed
derived-output folder outside the raw generation. Its folder, writer effects and
saved bytes are explicitly NOT native-qualified. No SharePoint output was saved.

The reader is actually stopped: no baseline-reader/Activities-pipeline process
or reader lock was present; only the weekly full reconciliation receipt exists.
The original pre-G06 binding preimage exactly matches the baseline checkpoint's
binding hash; its identity/client/resource fields match the current binding and
its read scope is a subset. Thus a future resume can use those exact retained
pin bytes under a separately named file in the original shared lock directory,
preserving checkpoint anchors, shared profile and current binding. No such file
or native resume has yet been created/submitted.

Native operations remain prevented by the preserved shared read lock for absent
PID 74036. The user's specific exception to preserve/release that orphan was
requested; the user asked why it was locked but has not approved release. The
lock has not been removed, renamed or bypassed. No current Activities archive
target/credential-file/journal binding is present. API key/reuse authority was
already supplied and is not reopened; qualifying its retained private file and
exact native binding is still an execution prerequisite.

This chat owns the following unfinished ARDC follow-through, without changes to
sharing, sends, schedules or another native operation: qualify/publish the ready
partial candidate+coverage output first when the lock condition resolves; resume
the stopped baseline reader from retained pages using the matching pin preimage;
connect the existing exact-ID Activities capture and create-only native archive;
process only newly available/changed pages; then connect RIMS and complete scoped
Conductor review/fixes and full key-set reconciliation. The historically accepted
general registry/RIF-CS baseline and weekly collector remain distinct from each
of those incomplete newer exits. Their present cloud execution state was not read.

Other-source completion is not claimed. The parent's maintained source ledger
`docs/SOURCE_IMPLEMENTATION_STATUS_20261028.md` and current G02/G05 evidence retain
the changed-path runtime, WHO admission/query, GrantConnect/Semantic Scholar and
university-source limits. RGS snapshot replay is not opportunity admission; Lens
and automated ANZCTR remain conditional/deferred rather than new work in this lane.

## Baseline source coverage continuation

Latest direct user step: Complete baseline source coverage. The applicable
remaining baseline is the retained general ARDC RIF-CS archive, not an admitted
current Activities snapshot or a new G06 funding relationship assertion. The
baseline's complete historical manifest and acceptance were passed through the
existing exact-target guard. The manifest declares 436,536 records on 4,366 pages;
the retained hash-verified inventory covers 2,452 pages, whose manifest-declared
record count is 245,200. The 1,914 unread pages account for 191,336 declared source
records. Those declared counts are not a new content reconciliation. The 66,172
filtered activity rows are a separate subset, not the source-record denominator.

The exact saved pre-G06 binding bytes match the reader checkpoint anchor and
retain current SDK/client/account/tenant/resource pins. A private immutable copy
was saved as `binding-ardc-baseline-retained.json` beside the original binding,
so the future reader uses the SAME authentication lock directory. This is
configuration evidence, not credential/cache transfer, authentication renewal,
lock bypass or native reader execution. The current shared selected binding,
checkpoint anchors and both locks were not changed.

This worktree's ignored `private/ops/ardc-baseline-coverage-20261029/` now contains
an exact missing-page inventory and the existing reader's fully bound resume
command, including the accepted historical manifest/receipt and exclusive
completion output. Native execution remains false: the shared orphaned lock
still exists for absent PID 74036 and its specific release exception is unanswered.
No baseline completion receipt exists and no reader is running. No full source
coverage or newer Activities acceptance is claimed.

Provisional SharePoint publication remains independent of completing that read:
the ready partial RIF-CS candidate/coverage packet must use a distinct derived
artifact contract and exact destination. The numbered Activities batch writer
retains its strict raw-response/ID checks; it must not receive candidate/status
JSON. The complete-lineage capture runner cannot substitute for partial-output
bootstrap. First native operations after the lock exception: bounded exact-target
read, qualify/save/read back the ready derived artifacts, and resume the existing
baseline reader from its retained pages. Do not restart from zero, repeat the
unchanged filter or interpret this prepared command as an executed resume.

## Orphaned Microsoft 365 lock resolved — 29 October 2026

The user explicitly requested addressing the orphaned lock. Immediately before
release, PID74036 remained absent, the recorded owner bytes and lock inode were
unchanged, and no matching guarded native operation was running. The entire stale
lock directory was preserved by same-filesystem rename into the original
checkout's ignored `private/ops/2026-10-29-m365-orphan-lock-recovery/orphaned-lock/`.
No credentials, binding, shared source files or native objects were changed.

One bounded exact-list GET through the existing `m365-qualified.mjs` acquired the
lock successfully, then stopped with `INTERACTIVE_AUTH_BLOCKED` for the pinned
SharePoint resource. It removed its own lock on normal exit. The former lock
exception is resolved; the remaining prerequisite is the existing same-client
explicit form_post renewal and exact-target readback. This attempt verifies lock
recovery, not current native access, incremental delivery or RIMS acceptance.
Private preflight, original owner, command output and terminal receipts remain
in that recovery directory. Zero native mutations occurred.

## Preserved ARDC source packet integrated — 29 October 2026

At the user's bounded integration direction relayed by the parent chat, this lane
cherry-picked `a1b90106ad43756e6e347267b049374425dfc8c3` as `5a03e763`.
Immediately preceding integration, on-demand preflight found both checkouts clean,
all30 packet paths absent on target, and no overlaps, staged deletions or warnings.
Ordinary Git hooks remained enabled. All30 resulting committed blobs independently
match the source commit. The two differing harvest files, G06 commits and private
native bindings were preserved; no other original-checkout changes were imported.

The actual repo-local interpreter reports Python3.15.1. All54 Python tests from
the packet and all5 Node bulk-reader tests pass offline; `git diff --check` passes.
These tests exercise fixtures/mock transports and do not prove native acceptance.
The native Python adapters reference `scripts/m365-qualified.mjs`, which remains
absent from this isolated checkout. Its existing original-checkout route and shared
authentication ownership are preserved, rather than copied as an unrelated dirty
source change. A source-preservation packet is therefore integrated, but isolated
native dependency closure, auth renewal and ARDC/G06 operational completion are
not claimed. Previously recorded broader failures were not rerun for this packet.

## SharePoint authentication renewed — 29 October 2026

Following the user's explicit renewal request, the existing guarded wrapper
completed one pinned personal-SharePoint renewal through the retained Toolkit
client and qualified MSAL form_post callback. Selecting the already signed-in
Queensland Health account completed the callback; SDK identity validation passed.
One subsequent guarded GET of the exact existing G06 relationship list succeeded
and produced valid private JSON. Both commands completed and the shared lock is
absent. No native mutation, profile reset, binding change, credential transfer or
new client/consent occurred.

Private acceptance and raw readback remain in the original checkout at
`private/ops/2026-10-29-g06-sharepoint-renewal/acceptance.json` and its sibling
receipts. The prior authentication gate is resolved. This bounded access check
is not incremental delivery, replay, consumer refresh or whole-track acceptance.

## Native incremental/readback/replay and RIMS output accepted — 29 October 2026

At the user's explicit verification direction, the current committed incremental
runner executed through the existing original-checkout binding/SDK/shared lock.
The job retained the hash-bound accepted ARC candidate packet and added the
hash-bound accepted current-consumer baseline. Actual repo-local Python3.15.1
was verified by the runner before native access. Current effects gates passed
for both cycles; no configuration change or notification activation occurred.

Bootstrap completed with two existing candidates preserved and zero creates.
Its native delivery, current rows, saved RIMS consumer and final checkpoint were
written successfully. Unchanged-input replay used that exact final receipt/hash,
reused the unchanged source packet/rule checkpoint, preserved the same two rows
and created zero duplicates. No source removals or context changes were reported.
A subsequent independent guarded exact-list GET preserves all business fields
and separate native ETags. Comparison omits only OData response-format metadata
and verbose deferred-navigation stubs; raw responses remain retained privately.

Both consumer file hashes match their final receipts; recomputing each consumer
from its native-delivery receipt and frozen accepted baseline reproduces the saved
JSON exactly. Both consumer outputs have two native rows/two candidates, zero
confirmed reviewed links and zero unresolved identity. Their rows and identity
material match across replay; identity_update_required=false. Native model
modification and live_refresh_verified remain false. This cycle requires no new
identity-material model write. It does not prove live refresh/rendering or the
broader G06 mapping/cardinality gates. New-candidate pre-create source checks were
not exercised because both accepted keys already existed. The prior bounded
writer create/recovery evidence remains authoritative for that separate operation.

Private original-checkout evidence:
`private/ops/2026-10-29-g06-incremental-acceptance/acceptance.json`, with hash-bound
bootstrap/replay/native receipts, both RIMS consumer files, exclusive job files
and `independent-final-items.json`. All native requests in this cycle were GETs
or semantic-read-only GetAllRules enumeration; zero native mutations occurred.
Another live guarded reader subsequently acquired the shared lock for its own
scope; it was left intact and is not an acceptance failure for this terminal run.
Source worktree remains `/Volumes/PortableSSD/GitHub/RIMS/g06-connect-rims-worktree`;
no bindings/cache/runtime promotion or parent-owned shared track files changed.

## Broader integration repair checkpoint — 29 October 2026

Installed the existing hash-locked requirements-dev.txt into this lane's own
Python3.15.1 environment; no shared environment or dependency lock was changed.
Fresh discovery ran1311 tests:2failures,8errors,12skips. Three prior missing-package
errors are resolved. The remaining missing-source/API/track failures are retained
in `private/ops/g06-integration-resolution/unittest.log`. Project validation still
passes454 checks. G06's23 Python and13 Node focused tests pass.

Restored exactly five absent OpenAlex M files from the original checkout ONLY
AFTER independently matching every byte hash to the existing reviewed runtime
manifest. The entire runtime hash map now matches; no manifest repin or runtime
expression edit occurred. Web-first now reports only E01/G05 missing track
dependencies and Unknown dependency. These shared track/source integration scopes
retain the parent integrator; their dirty originals were not imported wholesale.
Other remaining failures include missing DoRA/report helper modules, reviewed
flow definition, grants experience document, target fixture and incompatible
tracked grants_registry/grants_universities API, plus the hard-coded14-source
probe expectation against the three-row current catalogue. This checkpoint does
not claim that installing packages resolves those source-closure failures.

For the accepted G06 native cycle, both saved current consumers reproduce their
receipts and frozen baseline exactly, retain two candidate keys/zero confirmed
links and identity_update_required=false. The conditional new-identity model
write/refresh is therefore not triggered. Historical targeted bridge refresh
acceptance is retained in core-consumer-20261018.md; no fresh live model refresh,
current-model definition/cardinality readback or rendering proof is claimed.
Broader integration and current-model acceptance remain open pending their exact
source/native ownership handoff. No model mutation or refresh was launched.

## Terminal selected-scope closeout — 29 October 2026

Scope audit bb121286 and the final review mapping close the selected ARC writer,
incremental processing and RIMS consumer-output increment. Existing writer
create/recovery acceptance, ece39a07 bootstrap/readback/replay/consumer receipts
and36 focused passes are reused unchanged. No identity-material delta exists;
therefore no additional model write/refresh is triggered for this increment.
Historical ARC bridge/cardinality/reader acceptance is retained without claiming
a fresh refresh. Repository-wide failures retain their integration owner and do
not become new selected-slice gates; no release gate is waived.

Whole G06 remains open for the original plan's expanded H01 authoritative identity
reconciliation, H02 additive bridge/key-set/cardinality acceptance and H03 reviewed
links/correction/withdrawal proof. Its original untracked plan/spec and shared
registry were left intact. No whole-track archive or ARDC completion is claimed.
See the final mapping in review-closeout-20261029.md and exact expanded scope in
closeout-scope-20261029.md. This is a terminal documentation handoff, not a request
to repeat accepted ARC/native fixtures or start another source acquisition.
