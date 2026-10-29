# G06 incremental candidate delivery — 29 October 2026

Scope: connect the existing accepted ARC publication/award candidate packet to the
qualified owner-only relationship writer. The broader G06 track remains in
progress. This leaf adds no source admission, confirmed funding, schedule or model
refresh authority.

- [x] Hash-bound explicit source jobs and source/rule checkpoints.
- [x] Reuse unchanged packet transformations; validate changed packets and their
  exact keys, row hashes, candidate state and source context.
- [x] Retain source/context provenance, missing-source labels and changed-context
  keys; missing evidence never produces native delete or review updates.
- [x] Connect the retained Toolkit CLI writer with current publication source
  guards for newly missing native candidates, durable per-key intent, current
  native review preservation and final list readback.
- [x] Refuse checkpoint advancement without native acceptance; preserve previous
  receipts and uncertain mutation journals.
- [x] Focused source/checkpoint and existing writer tests (10 cases).
- [x] Actual accepted-source bootstrap and unchanged-source native replay — verified `ece39a07`; two existing candidates preserved, zero writes.

Entry point: `node scripts/g06_incremental.mjs PRIVATE_BINDING PRIVATE_JOB
NEW_PRIVATE_DIRECTORY`. A job has kind `g06-incremental-job-v1`, the qualified
private `scope`, explicit `sources` (each has `id`, `path`, `sha256`) and optionally
`previous` (`path`, `sha256`) pointing to a completed delivered receipt. Scope
retains the exact list URL, stable journal root and publication source list URL.
Only existing exact native read pins are used. The producer remains
`prepare_funding_relationship_context.py`; this worker consumes its validated
candidate output rather than rebuilding or reacquiring unchanged raw sources.

Outputs are `prepared.json`, hash-bound native submission scope, native current
rows/results and (only after verified readback) `receipt.json`. A failed delivery
retains preparation and a failure diagnostic without a completed checkpoint.
Subsequent jobs reuse only a `g06-incremental-delivered-v1` receipt with
`native_verified=true`. Processing still reconciles against the current native
list; a cached source is never authoritative for current human review.

The first real job is prepared from the accepted two-candidate ARC packet under
ignored `private/ops/2026-10-29-g06-incremental/` in the retained owner checkout.
Its first native attempt stopped before authentication or any request at the
shared workload lock. Recorded PID74036 was absent on inspection; the lock was
preserved. No new native candidate was submitted and no processing checkpoint
advanced. The exact publication source read-pin addition also stopped before
changing the binding. A specific lock-release exception is pending under the
user's prohibition on removing another process's lock.

Next: resolve that orphaned-lock exception, add/read back the known exact
publication source pin, run the accepted-source bootstrap, and pass its completed
receipt to an unchanged-input replay. Reuse the completed writer qualification;
do not repeat native fixture creation or expand relationship types.

Evidence/ownership details and the separate unfinished ARDC assignment are in
`handoff/G06_WRITER_QUALIFICATION_20261029.md`.

## Terminal scope reconciliation — 29 October 2026

The historical lock/next-operation paragraphs above are superseded by accepted
bootstrap/replay and independent readback in `ece39a07`. This incremental ARC
delivery increment is complete and reviewed. No new source or broader H01-H03
acceptance is inferred. See `closeout-scope-20261029.md`.
