# MRFF workbook discovery and source access — 5 November 2026

The failed 2 November 06:00 Brisbane collection received an HTTP-200 browser
verification interstitial from the official source. Its saved response contains
the interstitial verification endpoint and challenge function, with no workbook
links. The existing coverage guard correctly prevented workbook and completion
writes, but reported the generic `QGIP_SOURCE_GUARD_FAILED` expression error.
This was blocked source access, not evidence that the official inventory became
empty or that the XLSX link parser stopped recognising the source files.

The official page was inspected in the Codex internal browser on 5 November.
It still displays the same three workbook links as the retained successful page.
Offline discovery of that real successful response returns exactly those three
URLs. The real failed response now raises `SOURCE_ACCESS_BLOCKED` in the local
capture helper. No fresh machine request to the provider was submitted.

## Saved repair

The existing MRFF collector now has an explicit `Guard_source_access` after
each verified saved-page read, including the final inventory-stability read.
A recognised challenge terminates with `MRFF_SOURCE_ACCESS_BLOCKED` before
link discovery or completion can proceed. A normal page continues through
the existing parser and all existing completeness/integrity gates.

The exact native preview and independent saved readback establish:

- Two added guard actions and two changed parser `runAfter` dependencies.
- All other 39 original top-level actions unchanged.
- Source requests, retry policies, workbook discovery, known-file context,
  inventory checks, archive writes and completion naming unchanged.
- Connection references, Started state and weekly Monday 06:00 Brisbane
  recurrence unchanged.
- Recent run history unchanged; no new invocation, replay, cancellation or
  archive write was performed by this repair.

The preimage and the last successful completion response are retained privately.
The patch neither overwrites the prior archive nor substitutes its dated URLs
for a fresh complete live inventory. It does not solve challenges, forward
browser cookies/tokens, alter client identity or weaken the nonempty guard.

## Verification and remaining boundary

Nine focused tests pass, covering real capture behavior, preservation on failure,
challenge rejection even when links are present, ordinary-page handling and
exact candidate preservation/refusal. Separate offline checks use the retained
real good and failed responses. The service saved the candidate; independent
readback exactly matches its definition, connections, state and trigger.
The complete local suite passes 2,525 tests with 19 existing capability skips;
all 446 project checks and web-first contract validation pass. The earlier
interrupted invocation produced no terminal suite result; the resumed complete
invocation supplies this evidence.

The non-executing flow preflight passes on an authoring view and reports the
existing connection Connected. Direct validation of service readback initially
rejects its engine-injected authentication fields. The validation-only view
omits those 11 unchanged generated parameter references, also present in the
preimage; persisted definition/authentication fields were not changed. This
normalization is not a second save, runtime test or permission grant.

**Post-save runtime and successful unattended source access remain unverified.**
No native execution was submitted. A future unchanged natural occurrence can
establish actual runtime behavior. If the provider again serves a challenge,
the collector must fail explicitly and preserve the last good archive; a
provider-supported access route is required before claiming restored acquisition.
Browser availability does not prove that the cloud HTTP action has that access.

RMD-05 remains pending for the separate 1 December monthly exporter/observer.
No monthly plan, other flow, schedule, preference, recipient or shared
authentication selection changed.

## Evidence, ownership and documentation

Exact targets, complete preimage/candidate/readback, one-save intent, preview,
retained page/completion responses and offline/native reconciliation are in the
original checkout's ignored `private/ops/2026-11-05-mrff-discovery-repair/`.
The new source builder is pure and performs no network or native writes.
Definition rollback must use that preimage with a fresh concurrency preview;
no rollback or archive restoration was required or attempted.

Current owner is chat `01a1a569-bccc-7181-93bf-010e7dfdadde`, branch
`codex/mrff-discovery-repair-20261105`, standard Git worktree
`/Volumes/PortableSSD/GitHub/RIMS/integrate-pmf-readback-20261105`.
Owned native scope is the existing MRFF collector's four scoped action changes.
Other source/native/authentication owners retain their objects and evidence.

**Native guide/diagram publication pending:** the shared Toolkit profile differs
from the pinned workload; it was preserved and no shared documentation object was
edited. The MRFF lane retains this documentary follow-up: use the existing exact
guide/catalogue/Loop bindings and qualified identity, preserve current preimages
and human edits, publish the two-guard change and verify current/prior versions.
Source deployment does not establish native documentation parity.
