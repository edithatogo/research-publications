# Publication library appliers: guarded source — 29 October 2026

This packet implements the two exact metadata operators identified in the
[six-file disposition](PUBLICATION_DOCUMENT_LIBRARY_SOURCE_20261029.md), with
offline transport tests. It supplies no native session implementation. Both
direct CLI entries exit with `NATIVE_ENTRY_DISABLED` before SDK import,
authentication/cache access or a service request. Existing-column report metadata
is implemented; the old report `fields` creation mode remains unavailable.

## Qualified-entry dependency

The canonical `scripts/m365-qualified.mjs` and its read-admission/lock contracts
were inspected from `origin/main` at `dced8588ca921af2ee0f164b635d2af5da9c57af`.
Its modes are `read`, `renew` and `change-log-read`. None qualifies a library
metadata mutation. These operators do not call that wrapper, widen its read
authority, import its SDK or modify its lock/bindings. Parent retains the
existing authentication renewal and all native objects.

The exported functions are `applyPaperLibraryMetadata(options)` and
`applyReportLibraryMetadata(options)`. Options contain the existing exact
`target`, prepared `plan`, retained workload `binding`, an injected `session` and
an exclusive real `journalRoot`. The plan pins its snapshot/evidence file and
SHA256. There is no implicit global CLI discovery or `auth.restoreAuth` path.

The trusted owner must implement both session methods:

- `assertQualified()` synchronously asserts the held workload lock and current
  operation qualification without authentication or service I/O. It is called
  before journal admission and every request. It returns the current SDK root and
  version, connection, app/account/tenant, resource, browser/active identity,
  optional pinned object/callback, `sharedLockHeld: true`,
  `interactiveAuth: false`, `retries: 0`, `maxRedirects: 0`,
  `mutationQualified: true`, the exact operation (`paper-library-metadata` or
  `report-library-metadata`) and complete exact `mutationTargets` item URLs.
- `request(options)` performs one qualified request, returning decoded native
  JSON or binary `Uint8Array` and throwing on failure. It must honor zero retries,
  no redirects and no interactive authentication. It must not log credentials or
  acquire another resource/client. This packet implements only fictional in-memory
  transports; no production adapter is supplied or qualified.

Workload fields are checked against a captured copy of the supplied binding on
each request; simultaneous changes to the caller's binding and session cannot
move that copy. Flags without `assertQualified` are refused. The injected owner
remains responsible for verifying actual SDK/session/lock facts. This contract
cannot certify a dishonest or incorrectly implemented transport. Every successful
return explicitly retains `nativeAcceptance: false`.

## Exact scope and preservation

Paper writes are restricted to Title and Description on one exact library item.
The pinned file/item/parent association, linked authoritative parent/manifest,
file path, SHA256, PDF signature, length, checkout, field types and item/file
ETags must agree. An existing human Title or Description preimage is preserved.
The parent is compared again immediately before and after the intended effect.
Qualified same-origin href/entity/tag-whitespace representations are compared
only for rich-text Description; Title remains an exact text comparison.

Report writes use only the ten existing maintained logical properties and their
unambiguous actual native bindings. No Title/Description or field creation is
allowed. The complete selected batch qualifies before its first write. Duplicate
item/file identities, unsafe manifest links, altered pinned evidence, conflicting
human metadata and binding/type drift stop preparation or preflight. Native URL
wrappers are compared by their exact URL and label. The preparer's accepted
generation/revision/template/count provenance remains pinned input; this operator
does not independently discover or approve a generation.

Both operators require exact preimages and conditional item ETags. Before an
effect they read complete version history and retrieve/hash the pinned source
version's bytes, then reread the selected file/item/access/history immediately
before submission. Afterward they verify properties, unchanged file bytes,
stable file/item/path, access, unrelated human fields, all prior history entries
and retrieved prior-version bytes. Known response normalization does not rewrite
the prepared plan, source evidence or historical content ETag.

## Durable recovery

An operation's deterministic scope filename is held under the explicitly supplied
journal root with an exclusive lock directory. Existing locks are never stolen,
waited on or removed. Release checks directory identity. The journal is a private
regular single-link file opened without following symlinks; its scope, plan and
workload hashes must remain unchanged. Truncated journals are preserved and
refused. Preimages and an intent containing the exact body/ETag are flushed to
disk before the one intended POST. Header creation also flushes the directory.

Any recorded intent prohibits another POST for that item, including after a
lost response, HTTP429/503, post-save verification failure or process interruption.
Resumption reads the same operation. Matching saved properties, current/past bytes,
history and journaled protected preimages can reconcile it with zero writes.
A mismatch remains `UNCERTAIN_EFFECT_REQUIRES_READBACK` or a preservation failure;
there is no automatic inverse, resend or journal deletion. Completed items in a
partial batch remain recorded. Later items cannot proceed past an unresolved
preflight. A new journal root is not a retry mechanism: the owner must preserve
this root for the authorized packet and explicitly resolve its terminal state
before assigning another operation.

## Verification and remaining acceptance

Node26.12.1 built-in offline runner: **33 tests pass**. Cases include initial and
mid-operation workload drift, missing active qualification, interactive/read-only
authority, unexpected targets, pinned-evidence drift, human conflicts, byte/history
failures, zero-write replay, partial-batch response loss, throttling with no retry,
existing locks, symlink/truncated journals and disabled CLI entries. A direct
unittest wrapper includes this suite in the normal repository harness.

Repo-local Python3.15.1 full harness: **1,190 tests with25 existing skips**,446
project checks, web-first contracts, Conductor and tooling checks pass. The two
preparer modules retain their28 focused tests and13 subtests. Node syntax checks
and the Python wrapper's Ruff/format checks pass. Evidence and failing-test logs
are ignored under `private/ops/document-library-source/`. These are source and
fictional transport results, not saved tenant state or operational acceptance.

Both original operators retain their exact frozen source hashes from the prior
disposition; no original operator, binding, journal, environment or private native
receipt was edited. Shared contracts/dependencies/model/Conductor are unchanged.
The preferred SharePoint structured-document route and its dated template/repeating
content/output-parity gap retain the prior disposition. No generator is added.

Next native dependency: the parent must qualify an exact operation-specific
session/transport and assign exclusive item scope before any native adoption.
Then actual current preimages, saved readback, byte/version/access preservation,
reader/rendering and unchanged replay remain separate gates. No authentication
retry, field creation, metadata write, provider call, setting, schedule or send
is queued by this source packet.
