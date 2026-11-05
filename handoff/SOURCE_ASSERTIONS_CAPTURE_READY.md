# Source Assertions capture: reviewed offline handoff

This lane reviewed the private draft and supplies
`scripts/capture_source_assertions.mjs` with synthetic contract tests. It is ready
for a qualified read session; no live capture or authentication recovery was
performed during this review. The existing native/authentication owner retains
execution. The integrator owns shared handoff updates and consumer code.

## Prerequisite

Resolve authentication ownership and use the retained verified Toolkit workload
route. Keep its exact client/account/tenant/resource pins, normal credential
persistence and internal-browser requirement. The driver invokes only
`scripts/m365-qualified.mjs read`; it cannot renew authentication, launch a
browser, change profiles or run a flow. A guarded expiry/identity/permission
failure stops the capture. No automatic retries or alternate-client fallback.

Use the existing private Source Assertions target and exact-list read binding.
The driver requires the binding to contain that exact list URL. Supply absolute
paths for the guard checkout, private binding and a new ignored output directory.
Do not pass authentication data through CLI arguments. The original private
draft is retained as history; this reviewed driver is the proposed replacement
once the integrator accepts it.

## Execution by the native owner

From the checkout containing the reviewed script, with placeholders resolved
from existing private bindings:

```sh
node scripts/capture_source_assertions.mjs --live \
  "$GUARD_CHECKOUT" "$PRIVATE_BINDING" "$EXACT_LIST_URL" "$NEW_PRIVATE_OUTPUT"
```

`GUARD_CHECKOUT` is the existing checkout containing the qualified wrapper, not a
new runtime. `NEW_PRIVATE_OUTPUT` must be ignored by that checkout and must not
already exist. The wrapper owns serialization and exact-request guards. Retain
any partial output after failure; inspect the failure before a new attempt.

The driver reads metadata, all schema pages, all unfiltered item pages and
metadata again. It preserves original JSON response files and continuation
URLs/timestamps. Continuations are restricted to the same HTTPS list collection;
foreign paths, filters, conflicting links, loops and unknown envelopes fail.
Every item must have a unique positive ID and nonblank source key, all nine
managed text/null fields, protected Title/OperatorNotes, system dates/version
and an explicit REST ETag. No raw field is discarded. Missing schema property
flags remain missing; downstream schema assessment retains its unverified state.

Metadata must identify the expected versioned list; title, count, identity and
versioning must remain stable, and the assembled count must match ItemCount.
An actual empty list requires a successful empty response and stable zero count.
Equal metadata is not atomic-snapshot proof: later writes still require fresh
item/preimage/ETag checks.

## Return and consumption

Return the absolute private output path and `hashes.json` to the integrator.
Success requires `receipt.json` with `PASS_COMPLETE_READ_ONLY_CAPTURE`, exhausted
continuations, raw metadata/schema/item pages, `capture.json` exactly
`{metadata,response}` and `schema.json` containing the complete field array.
On failure, return `failure.json`, raw partial pages and hashes; do not treat a
partial inventory as empty or complete. Do not consume a standalone capture file
without its successful receipt and verified hashes.

The capture format was consumed directly by the integrator's current
`bind_inventory` and `schema_requirements` functions using synthetic data and
repo-local Python 3.15.1. This establishes format compatibility, not permission,
live completeness, schema suitability or consumer deployment readiness.

## Offline verification

```sh
SOURCE_CONTRACT_REPO="$EXISTING_CONSUMER_CHECKOUT" \
  node --test tests/test_capture_source_assertions.mjs
```

All 17 tests passed with zero skips, including actual consumption by the existing
adapter. Cases include two-page items and schema, protected fields and ETags,
missing schema flags, stable empty inventory, metadata/count drift, duplicate
IDs/keys, missing/non-text fields, absent protected notes/ETags, foreign/filtered/
looping/conflicting continuation and unsupported envelopes. Failure cases emit
no assembled capture. The consumer test reads the existing checkout but does
not change its code, environment, private inputs or authentication.
