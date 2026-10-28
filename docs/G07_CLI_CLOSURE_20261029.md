# Qualified CLI source closure — 29 October 2026

This is the second source packet from grants delivery chat
`01a1831e-cc6d-7371-9d57-021a339b708a`, under sole integrator
`01a182f2-fd8e-7953-9bd2-f9b8002664a6`. It extends that chat's explicit source
assignment to the shared qualified CLI wrapper, lock and direct helpers. The
app-managed checkout and branch remain those in the
[first source handoff](G07_SOURCE_HANDOFF_20261029.md); this packet starts at
`bb464cf8048d826d7aeda19f0dc77cc313282445`.
Native scope is empty, including shared authentication renewal. No real SDK or
native wrapper invocation was performed. Only installed source and frozen private
receipts/binding field names were read. No private configuration was changed.

## Dependency closure and mode disposition

The retained wrapper dispatches into eleven modes. This bounded source packet
implements three; unsupported modes reject before resolving a binding, acquiring
a lock, importing the SDK or restoring authentication.

| Mode | Source disposition |
| --- | --- |
| `read` | Qualified raw GET, exact named Flow reads and separately pinned SharePoint file commands. Installed SDK remains selected by the unchanged private package/version pin. |
| `renew` | Existing same-client/same-resource form_post adapter, identity validation and private receipt flow retained. Arguments/private destination are now admitted before authentication. Native renewal ownership stays with its existing owner. |
| `change-log-read` | Retained read-only SharePoint GetChanges helper and tests imported. Fixed POST query, pinned exact list/token bounds, no retry and bounded pagination. Partial HTTP responses, malformed rows and incomplete paging cannot certify empty history. |
| `funding-apply`, `page-draft`, `documentation-sync`, `documentation-page` | Explicit MODE_UNAVAILABLE_BEFORE_AUTH. Funding/documentation helpers belong to other lanes; none imported, overwritten or invoked. |
| `isolated-recovery`, `grants-downstream`, `grants-promotion`, `grants-preference-activation` | Explicit MODE_UNAVAILABLE_BEFORE_AUTH. Their wider grants helper/Python/runtime closure is a later packet; no dangling dynamic import remains. |

The only local module dependencies are `m365_read_guard.mjs`,
`m365_workload_lock.mjs` and `sharepoint_change_log_read.mjs`; all are included.
Node built-ins require no package installation. The selected installed M365 SDK
is an external prerequisite, never copied or modified by this packet. Original
working wrapper, private pins, credential store, native jobs and journals remain
in the preserved authoring checkout. Do not replace its active wrapper in place.

## Admission and compatibility limits

Raw GET retains existing `readUrlPrefixes`, resources, client/account/tenant and
SDK pins. It adds canonical URL checks, double-encoded traversal rejection,
physical ignored-output-parent admission, and dangling/existing-output rejection.
Its transport permits only the exact GET, no body and no redirects. All read
transports block mutation verbs and use a 15-second per-request timeout.

Named Flow get/run-list/run-get checks an exact flow root against existing
`readUrlPrefixes`; only complete explicit options and JSON output are supported.
Trigger/action download options are excluded because they may follow separately
returned output links. The installed 12.0.0-beta.f682e10 command schemas/source
establish these argument/endpoint shapes; this is source compatibility evidence,
not current target qualification.

The retained monitor's binding does not pin exact roots for its two collector
Flow reads. Its named SharePoint archive reads also lack the new exact argument
allowlist. Those formerly command-name-only paths now stop before authentication.
Thus this packet closes the source dependency but is deliberately **not a
qualified replacement for the running monitor configuration**. The original job
and its broader retained wrapper are unchanged. The assigned native owner must
qualify exact targets/argument scope before any future adoption, without silently
expanding permissions. No private pins are supplied or auto-generated here.

Named SharePoint file get/list requires a complete string-array invocation in
optional private `readCommandArguments`; absent/nonmatching pins fail before auth.
It is suitable for explicitly frozen reads. Changing per-generation paths requires
new admission by the native owner; a future stable archive-prefix policy needs
its own bounded source design and tests. This packet does not infer library/file
scope from an unrelated list or site prefix.

The installed request adapter recursively retries HTTP429/503. An in-process
response guard preserves those statuses as terminal guarded-read errors without
the response shape that triggers its recursion. The SDK files are untouched.
The GetChanges helper already calls the no-retry low-level transport directly.
A caller can still rerun a read deliberately; no mutation retry is introduced.

The retained lock queues without removing an owner. Bounded finite wait options
are validated. Wrapper cleanup additionally checks the acquired directory's
filesystem identity and preserves a replacement lock. This is a cooperative
process lock; it does not transfer native-object or authentication ownership.

## Conditional worker-definition repair proposal

Do not add a guessed If-Match header to the existing Flow management PATCH.
The installed CLI exposes flow GET/enable/disable/export/remove and run commands,
but no flow-definition update command establishing that PATCH's precondition
semantics. Its generic request transport only sends supplied requests; that is
not proof that a Flow endpoint honours conditional updates.

A supported candidate already used in this project is the Dataverse workflow
row route. Frozen timestamp/acquisition promotion source and acceptance receipts
under `private/ops/2026-10-28-g07-activation/` record conditional `clientdata`
PATCHes with each row's `@odata.etag`, followed by exact Dataverse and Flow API
readback. Those examples concern stopped import/acquisition flows. They do not
qualify mutation of the live delivery worker or establish its workflow row ID.

Microsoft documents row-version concurrency using an exact ETag and advises
checking `EntityMetadata.IsOptimisticConcurrencyEnabled`; ETags are opaque and
must not be ordered or synthesized. See [Dataverse conditional operations](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/perform-conditional-operations-using-web-api).

The concrete source repair, after exact native scope assignment, is:

1. Replace the worker controller's unconditioned definition-save operation with
   a separately qualified Dataverse row adapter. Resolve the worker's existing
   `properties.workflowEntityId` from its frozen exact management binding; never
   equate it with the Flow management ID or create a replacement worker.
2. Require the assigned existing workload's qualified Dataverse operation and
   metadata read showing optimistic concurrency support for the workflow table.
   Preserve the complete row/clientdata, exact non-wildcard ETag, Flow preimage,
   state, connection references and failure-alert setting before any write.
3. Build a candidate changing only the frozen EventJSON/default definition in
   complete preserved clientdata. Store one exclusive native intent and rollback
   preimage. PATCH only `clientdata` at the exact workflow row with its exact ETag,
   no automatic retry and no redirects. HTTP412/uncertain response stops; it
   must never invoke the worker or fall back to an unconditional Flow PATCH.
4. Require complete Dataverse clientdata and same-identity Flow definition,
   connection/state readbacks before any later invocation. A mismatch or uncertain
   save stays quarantined. Rollback uses a fresh comparison/ETag against the owned
   candidate, preserving concurrent changes instead of overwriting them.
5. Offline tests must cover one conditional save, stale ETag/412, concurrent
   clientdata change, lost response, binding drift and blocked invocation on
   readback mismatch. Then a specifically assigned isolated DEV object can prove
   native stale-preimage rejection and rollback with no send. Neither the current
   live worker nor its one-send journal is a test fixture.

If that exact workflow table/operation is unsupported or denied, stop the new
save path and report that scope; retain the running native owner's route. No
alternative client, new consent or unconditional save is authorised. This packet
only proposes the adapter and does not modify `grants_live_delivery.py` or claim
that a conditional save has now been implemented for the worker.

## Verification and next operation

Run `node --test tests/test_m365_qualified.mjs tests/test_m365_workload_lock.mjs
tests/test_sharepoint_change_log_read.mjs`. The synthetic SDK tests use only
ignored disposable fixtures, invented identities and fake transport. They prove
pre-auth rejection, no stock login, exact identity/resource and transport guards,
explicit one-resource renewal, shared-owner serialization, read throttling stop,
and source-closed GetChanges dispatch. They load no real SDK, session or token.

Verification recorded for this packet: 20 Node tests pass with no skips;
24 affected grants Python regressions pass; 446 project checks, web-first local
validation and Conductor structure pass. The unchanged broader Python-suite
result from the first packet is reused, not rerun as new native proof. Node test
log: `/Volumes/PortableSSD/tmp/rims-grants-ef45-wrapper-tests.log`. All tests use
the existing worktree Python3.15.1 environment where Python is involved.

The integrator next reviews this source packet and the intentionally stricter
named-read compatibility boundary. Documentation/funding helpers remain with
their owners. Native adoption, shared auth renewal, monitoring, sending and
schedule changes require their existing distinct assignments and evidence gates.
