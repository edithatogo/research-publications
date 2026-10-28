# Bounded writer feed and protocol simulation

Source starts at parent-reviewed/local-merged `688bbdf05aff5c711b06a6d01e1e991162672544`.
PR68 hosted verification was pending when the integrator authorised development.
This is not described as verified-main or native acceptance. Writer chat
`01a1831e-cc6d-7371-9d57-021a339b708a` retains its clean existing branch in
`/Users/doughnut/.codex/worktrees/ef45/chhhs-research-publications`.

Only the two new helpers, their two paired tests and this leaf are assigned.
Existing admission/preflight, policy/retention/contracts, package builder, tracked
flow, dependencies/runtime and shared records remain unchanged. Original native
operations, journals, authentication and private bindings retain their owners.

## Implemented boundary

`prepare_publication_writer_feed.build` rebuilds and verifies the independently
pinned admission packet against its complete supplied inputs/raw bytes. It returns
an unpublished manifest and exact UTF-8 candidate-part bytes. This completes the
bounded local feed producer and verification behavior.

`prepare_publication_guarded_writer.prepare` emits a **declarative transition
plan**, preserved source preimage and explicit blockers. It is protocol simulation
and migration intent, not an implemented deployable writer graph. It always
returns `native_definition_candidate=null`, `native_adapter_implemented=false`,
`writer_ready=false`, and false write/native acceptance flags. No WDL or connector
payload is generated. Missing native action/target contracts are listed below;
shared migration/wiring remains with the parent.

The built-in `MemoryTransport` and `simulate` exercise the protocol using only
in-memory fixture data. No arbitrary transport callback, plugin, CLI service,
provider or native adapter can be invoked. Simulated completion is explicitly
labelled and never establishes native runtime, persistence or operational proof.

## Complete immutable candidate feed

The build API takes `inputs`, `raw_files`, `packet`, independent `input_pins` and
`packet_pin`, explicit `as_of`, `max_part_records`, `max_part_bytes` and
`max_manifest_bytes`. It calls the accepted admission verifier's full rebuild;
editing and rehashing a proposal does not qualify it. All inputs remain detached.

The context binds the admission packet hash, all input/config pins, full independent
binding inventory, target and generations, schema qualification, planning clock
and explicit bounds. Its hash supplies the feed ID. The manifest contains the
complete part descriptors, independent record bindings, total counts, record-value
hash, original raw-file proofs, registry/writer pins and retention-candidate hash.
It retains `UNPUBLISHED_CANDIDATE`, false publishing authority, false source/native
acceptance and no assigned native file identities. It cannot become an accepted
source marker by changing its status string.

Each canonical UTF-8 JSON part binds kind, feed ID, sequential number, explicit
before/after cursors, terminal flag and complete logical rows. Descriptors bind
those values plus exact bytes/SHA256, count and SourceKey/CanonicalKey/source/
generation pairs. An explicit final empty part is required, even after the last
full data part. Parts are split only between complete records; oversized records
or manifests fail without truncation. There is no fixed total or silent TOPN cap.

`validate` requires an independent manifest hash and all exact bytes. It checks
closed profiles, every part/byte/count/hash/binding, canonical UTF-8 serialization,
strict JSON, complete ordered cursors and terminal page, exact independent binding
and schema pins, source identity rules and canonical ambiguity. The existing
paged-batch validator is reused. Human values, versions and complete metadata
remain lossless in each logical proposal. Existing changes remain field_20-only;
new records retain Included policy and exact qualified full/display title values.

The producer creates no source authority, publication receipt or native file
identity. Actual accepted producer receipts and immutable/native version-bound
reads remain separately qualified dependencies.

## Declared qualification profiles

Four exact profile names are required before the in-memory protocol can proceed:

| Profile | Required declarations |
|---|---|
| `version_bound_feed_reads` | Accepted producer receipt; exact native file IDs, nonwildcard ETags, byte counts/hashes for every part; same-version content reads; complete terminal inventory |
| `conditional_etag` | Fresh exact full preimage; opaque nonwildcard IF-MATCH; qualified response/header shape; HTTP412 conflict/no retry; field_20-only update and preserved human values |
| `atomic_create_uniqueness` | Atomic source-key reservation; one create containing full title; Included policy; no uncertain resend; exact full-title destination |
| `durable_intent_outcome_journal` | Conditional intent before effect; outcome after readback; uncertainty stops resend; all-record completion gate; stable generation/operation binding |

Each profile has an independently pinned JSON hash, exact name/version,
evidence reference, operation-schema hash, scoped bindings and exact guarantee
inventory. Scope binds target, feed manifest, writer preimage, connection references
and schema qualification. Missing profiles yield explicit `missing_qualification`
blockers and zero simulated effects. Rebound or malformed declarations fail.

These are supplied declarations. Their references and operation-schema hashes are
not authenticated or dereferenced by this packet. A declaration is not an actual
connector action schema or target permission. Even all four declarations leave
native blockers and the null WDL candidate intact. Tests use clearly fictional
references/file identities; none is native qualification.

## Protocol simulation invariants

The complete feed is verified before generation claims or effects. A source
scope/generation is then bound to one manifest, so changed partitioning/planning
cannot use a different operation namespace to resend the same generation.

Per record: check replay -> read exact current preimage -> capture actual simulated
processing clock -> persist intent -> attempt one effect -> verify saved readback
-> persist verified outcome. More records loop through replay; consumer completion
is reachable only when every record is verified. Any failure stops subsequent
effects and prevents consumer completion. No-op records verify the preimage and
record a no-effect outcome.

The model checks fresh identity/full-row equality and opaque ETag before updates.
Only field_20 changes; first-observed, source/canonical identity, human values and
prior history remain preserved. A concurrent edit causes a conditional conflict,
without retry or restoration over that edit. The atomic fake create checks
identity uniqueness again at the effect boundary, including a simulated creator
race, and creates full title and Included policy together. Processing timestamps
use one supplied fake actual-clock instant; source observation evidence and the
packet planning clock retain their separate meanings.

Intent precedes effects. Timeout/readback/outcome failure leaves uncertainty and
blocks automatic resend, including a create that may have succeeded. A done status
alone cannot skip work: replay requires the same feed/proposal binding and exact
verified outcome proof. Verified replay does not send or advance timestamps.
Partial failure retains completed effects/outcomes; there is no fabricated batch
transaction or automatic destructive rollback. Failure of the final completion
record can be reconciled from verified done outcomes without repeating effects.

These guarantees are reference-model behavior only. In-memory state is not a
durable native journal, atomic database reservation, native ETag implementation or
real processing clock.

## Exact missing native capabilities and reusable source shapes

1. **Accepted feed location and version-bound file reads:** no approved native
   producer marker, manifest/part file IDs or current same-version content-response
   schemas are supplied. Existing acquisition builders demonstrate standard
   SharePoint persistence/readback patterns, but their target-specific receipts do
   not qualify this feed. Native WDL SHA256 is not invented; declared hashes cannot
   substitute for computed or qualified same-version byte evidence.
2. **Fresh item read/conditional merge/readback:** the supplied pilot retains its
   SharePoint connection/lookup shape. Retained observation/title helpers contain
   `HttpRequest` GET/MERGE examples. Their broad field sets, numeric ETag assumptions
   and reducers do not qualify this timestamp-only path. Actual opaque ETag response
   shape, header propagation, conflict/timeout/no-retry behavior and saved readback
   need exact current action schemas and target proof.
3. **Atomic creation with Note storage:** existing PostItem source shape is useful
   evidence, but it does not prove atomic source-key reservation or a single create
   retaining SourceFullTitle in the selected Note. No uniqueness setting, new list,
   reservation store or second title-fill mutation is introduced here.
4. **Durable conditional intent/outcome journal:** there is no assigned native
   journal object, permission, revision/response shape or crash-recovery receipt for
   this protocol. Memory persistence does not fill that gap. An uncertain create
   must remain stopped until explicit owner reconciliation, not automatic resend.
5. **Actual clock/fail-fast control flow:** native processing-clock placement,
   action/Until/foreach failure semantics, expression compilation, response/body and
   size limits require runtime qualification. A serial loop alone does not prove
   uniqueness or stopping after a failed effect. No source plan claims those tests.

The retained preimage's identities, triggers, authentication, parameters,
connections and unrelated actions are preserved verbatim. The migration scope
names the three pilot roots for parent review and hashes both their original
contents and unrelated actions. No replacement is installed, no recurrence or
connection reference is invented, and no restore payload is emitted.

Parent-owned next work is exact standard-connector adapter/control-flow wiring,
versioned validator/preflight changes, and consistent package-builder/tracked-flow
production from that one implementation. Existing source authority, typed admission,
native owner/access, recovery, notification suppression and activation gates remain
open. A local feed or simulated result cannot admit or promote a source generation.

## Local CLI and evidence

The feed CLI accepts `--inputs --files --pins --packet --packet-sha256 --as-of
--max-part-records --max-part-bytes --max-manifest-bytes --output`. The files input
maps raw artifact names to explicit private paths. The packet input uses the exact
existing admission envelope. Output `publication_writer_feed_local_v1` contains
manifest, `parts_utf8` and same-read input byte hashes. UTF-8 re-encoding reproduces
the exact candidate parts; no native files are published.

The plan CLI accepts `--writer --feed --profiles --profile-pins --writer-sha256
--manifest-sha256 --output`; output is `publication_guarded_writer_local_v1` with
its source plan and same-read input hashes. A successful CLI exit means a local
artifact was produced, including a blocked plan, never writer readiness.

Both CLIs use strict JSON, existing checkout-private parents, no symlink redirection
and exclusive atomic owner-only output creation. Inputs/prior outputs survive all
failures. No authentication, native requests, external messages, environment or
dependency changes occur.

Actual selected repository Python is 3.15.1. All 28 focused stdlib tests pass:

```text
.venv/bin/python -S -m unittest \
  tests.test_prepare_publication_writer_feed \
  tests.test_prepare_publication_guarded_writer -q
```

Tests cover complete feed rebuild/pins/bounds/terminal records, lossless metadata
and human values, strict/exclusive CLI behavior, both direct `-S` entry points,
profile gaps/rebinding, fail-before-effect guards, conditional conflict, atomic
create race, full-title loss, uncertain outcomes, exact replay proofs, manifest
rebinding of a generation and partial completion preservation. Unchanged admission/
preflight and broad integration/native checks reuse their existing receipts.
