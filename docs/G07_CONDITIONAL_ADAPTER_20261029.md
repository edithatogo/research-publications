# Conditional definition adapter source handoff — 29 October 2026

This bounded source packet implements the adapter proposed in the
[qualified CLI closure](G07_CLI_CLOSURE_20261029.md). It does not connect that
adapter to MailWorker, the monitor, authentication or any service. Earlier
proposal/deployment statements remain historical; source implementation here
is not native qualification.

Delivery chat `01a1831e-cc6d-7371-9d57-021a339b708a` remains in the app-managed
checkout `/Users/doughnut/.codex/worktrees/ef45/chhhs-research-publications`,
branch `codex/rims-grants-roadmap`, under sole integrator
`01a182f2-fd8e-7953-9bd2-f9b8002664a6`. Packet base:
`190c5685424de7c6a2850aba7c4e0931c0b68bb2`. Native scope is empty. Current
private bindings, original jobs, journals, services and authentication owners
retain their scope. Shared handoff/track/runtime files are unchanged.

## Implemented contract

`scripts/grants_conditional_definition.py` uses Python standard libraries and
an injected transport. It imports no HTTP client, authentication provider or
worker code, and has no command-line execution path. Its only native methods
would be GET and PATCH through a future caller-owned qualified transport.

- `prepare_save` freezes the complete workflow-row and Flow preimages. It
  requires a distinct definition, canonical workflow/flow IDs, the exact
  management `workflowEntityId` mapping and observed workflow metadata with
  `IsOptimisticConcurrencyEnabled` exactly true. An explicit operation ID and
  exclusive owner are required; their strings do not prove ownership or access.
- Every non-definition clientdata value is retained, including unknown top-level
  and nested properties and complete connection references. The rollback payload
  retains the original clientdata string exactly. Preparation rejects disagreement
  between the Dataverse and Flow definition/connection preimages.
- Before PATCH, fresh metadata, exact workflow row and same-identity Flow GETs
  must match the owned preimage. The save ETag must equal the frozen preimage.
  Only `@odata.etag`, `versionnumber` and `modifiedon` are treated as service-owned
  row revision/time fields; every other row/clientdata change stops the operation.
- The file journal creates an exclusive intent containing target, exact ETag,
  body, complete preimage/plan and fingerprint; it fsyncs the mode0600 file and
  directory before the one PATCH. The caller must supply an existing owned,
  ignored private storage boundary. No credential/receipt directory is selected
  automatically. A failed durable intent prevents transport submission.
- A stable operation ID and the same journal directory are mandatory across
  retries/processes. Existing intent or outcome stops all further transport for
  that operation. Two contending instances can claim only one native intent.
  The adapter never invents a fresh operation ID to evade quarantine.
- PATCH changes only clientdata, includes the exact non-wildcard If-Match ETag
  and sets injected transport requirements `retries=0`, `max_redirects=0`,
  `timeout_seconds=30`. There is no retry or unconditional fallback. The future
  qualified transport must actually honour those requirements; a Python callable
  alone cannot establish its native behavior or authentication authority.
- HTTP412, unexpected response, lost response, unsuccessful readback or mismatched
  state/connections/definition remain quarantined. HTTP200/204 alone is never
  acceptance. Fresh complete Dataverse and Flow readbacks plus a changed opaque
  ETag are required for `saved`. No ETag ordering is inferred.
- Rollback requires the matching recorded verified save/intent and a fresh row
  still equal to the owned candidate. It sends the original clientdata under the
  freshly read ETag, then independently verifies both restored representations.
  A concurrent edit, HTTP412 or lost response stays quarantined. A lost-response
  save cannot be rolled back merely because a subsequent row happens to match
  the candidate; its uncertain ownership/effect needs separate reconciliation.

Every result keeps `invocation_allowed=false`. Even `saved`/`rolled_back` is an
adapter result, not permission to invoke, send, enable, schedule or promote.
No live MailWorker code was modified, and no real transport implementation,
authentication adapter, native mutation or mailbox capability is added here.

## Offline monitor compatibility validator

`scripts/grants_monitor_compatibility.mjs` reuses `m365_read_guard.mjs` to admit
configured Flow reads, configured metadata/field/item reads, and optional frozen
SharePoint archive command vectors. It reads files/metadata and checks Git-ignore
admission, without importing the SDK, restoring auth, creating locks or writing
a probe/output file. It emits labels/reasons without target URLs/IDs.

```sh
node scripts/grants_monitor_compatibility.mjs \
  PRIVATE_MONITOR_CONFIG PRIVATE_BINDING NEW_IGNORED_OUTPUT_PROBE_PATH \
  OPTIONAL_PRIVATE_FROZEN_ARCHIVE_COMMANDS_JSON
```

The probe's parent must already exist. The optional archive JSON maps source
labels `nhmrc`/`mrff` to argument arrays without `--output json`; the validator
appends that fixed output pair. Frozen command admission is not a policy for
future generation paths. Exit0 means compatible frozen command admission only;
incomplete/incompatible/input failures exit2. `whole_monitor_qualified` is always
false. Account/client/resource auth, notification worker, host/schedule and the
actually deployed wrapper remain outside the check.

A bounded read-only check of the retained monitor config/binding reports:

| Check | Source-admission result |
| --- | --- |
| Installed SDK package/version versus retained pin | Match; package metadata only, no SDK import or session check |
| NHMRC/MRFF Flow get and history commands | Four rejections: exact collector roots absent from stricter read pins |
| Archive command generations | Two unknowns: frozen commands not supplied; no binding edit or inferred prefix scope |
| Five configured stores, metadata/fields/items | All15 admissions pass; no actual store read submitted |

Overall result is incompatible with the proposed stricter wrapper. The original
running configuration is preserved. This confirms the existing adoption gap and
is not an operational failure claim about its current native job.

## Exact remaining native qualification

The integrator must assign a labelled isolated DEV workflow row/Flow pair, a
single native writer and the qualified existing Dataverse read/PATCH workload.
Then obtain authoritative mapping/full preimages and exact workflow-table
optimistic-concurrency metadata. Unknown/false support or an identity/permission
denial is a scoped blocker; do not try another client or unconditional Flow save.

Qualify the transport's no-retry/no-redirect behavior and private durable journal
location. Prove a successful conditional save, actual stale-ETag412 after an
owned competing test edit, full non-definition/state/connection preservation,
readback gating and fresh-ETag rollback on that isolated object, with no send or
invocation. Current service annotations may require explicitly reviewed handling;
the source's exact comparisons deliberately reject unqualified differences.
The retained stopped-flow conditional receipts are precedent, not acceptance of
this new adapter or the live worker. See [Microsoft's Dataverse conditional
operations](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/perform-conditional-operations-using-web-api)
for the documented concurrency prerequisite and row ETag semantics.

Only after that separate proof could the integrator consider a bounded
MailWorker integration. No native assignment, activation, schedule change, shared
auth renewal, send or integration into the live worker is implied by this packet.
Local rollback is a scoped source revert; native rollback is not claimed here.

## Local verification

- Python3.15.1 selected explicitly; existing locked dependencies pass pip check.
- 29 focused Python tests pass:16 adapter tests plus existing monitor, delivery
  planner and worker-builder regressions. They cover success/preservation,
  input/prerequisite rejection, stale preimage,412/concurrent edit, lost response,
  failed/mismatched readbacks, frozen-plan corruption, nondurable intent/outcome,
  two-writer contention, replay suppression and fresh-ETag rollback.
- 24 Node tests pass, zero skips, including four new compatibility tests and the
  unchanged guarded-wrapper/lock/change-log selection. Log:
  `/Volumes/PortableSSD/tmp/rims-grants-ef45-adapter-node.log`.
- 446 project checks, web-first local validation and Conductor structure pass.
  Changed-behavior checks are fresh; the prior broad-suite receipt is reused.
- Relative handoff links resolve and `git diff --check` passes. No release,
  clean-package, native execution or operational acceptance is claimed.
