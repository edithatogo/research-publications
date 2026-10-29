# Review Report: G06 writer, incremental processing and RIMS connection

## Summary

The bounded writer has retained native qualification, and the incremental/RIMS
source changes pass focused checks after two material review fixes; G06 is not
ready for whole-track closure because broader integration and track acceptance
evidence remain incomplete. The fresh incremental delivery/readback/replay and
saved RIMS consumer-output cycle subsequently passed at its bounded scope.

## Verification Checks

- [x] **Plan Compliance**: Partial. Existing writer/readback/recovery proof is
  retained. Incremental source processing and consumer preparation are implemented;
  the actual new delivery cycle, wider mapping and model/cardinality gates are open.
- [x] **Style Compliance**: Pass at the selected scope. Standard-library Python,
  explicit failures, research-specific identities and uncertainty are retained.
  No credentials, tenant identifiers or native row data were added to source.
- [x] **New Tests**: Yes. Source-context mismatch, actual runtime preflight and
  hash-bound baseline preservation tests were added to the existing focused suite.
- [x] **Test Coverage**: Partial. Thirteen Node and twenty-three Python cases pass;
  the retained two-candidate packet passes the stricter source checks. These are
  local checks, not new native processing or M/DAX/rendering acceptance.
- [ ] **Test Results**: Full integration remains failed. The retained isolated
  discovery ran 1,236 tests with 2 failures/11 errors/12 skips. Web-first validation has
  missing source/dependency references and five missing OpenAlex M files; no
  existing runtime hash changed. Project validation passed 454 checks. Unchanged
  broad failures were reused rather than rerun or hidden.

## Findings

### High — Source-context crosswalk could disagree with the submitted relationship — Fixed

- **File**: `scripts/g06_incremental.mjs` (Lines17–20).
- **Context**: The validator checked relationship fields and provenance hash
  syntax, but did not bind the context's registry publication key, PubMed source
  key/URL, ARC source ID/code/URL and registry item ID to that relationship.
  Native source guards could therefore inspect a different source row from the
  proposed target publication. The new regression reproduced a missing exception
  before the fix.
- **Suggestion applied**:

```diff
  require exact relationship fields and source-row hashes
+ require context publication/award crosswalks to match that same relationship
+ reject invalid registry item IDs and blank/padded canonical publication keys
```

All eight mismatched-context cases now reject; the real retained two-candidate
packet passes without being changed or re-admitted.

### High — Local consumer prerequisites were checked after possible native effects — Fixed

- **File**: `scripts/g06_incremental.mjs` (Lines45–66,73–87).
- **Context**: The selected repo-local Python version was not probed before native
  delivery, and optional RIMS baseline hash validation occurred after it. A wrong
  interpreter or stale baseline could be found only after a create. The original
  baseline file could also change before subsequent consumer preparation.
- **Suggestion applied**:

```diff
+ probe the selected repo-local interpreter and require qualified Python 3.15.1
+ verify RIMS baseline hash and type before launching any native adapter
+ freeze the verified baseline in exclusive private evidence before delivery
+ retain a consumer-failure receipt without advancing the processing checkpoint
```

Runtime mismatch, failed probe, baseline drift/type mismatch and immutable prior
bytes are tested without authentication or native requests.

### High — Fresh incremental delivery and consumer-output acceptance was absent — Resolved at bounded scope

- **File**: `handoff/G06_WRITER_QUALIFICATION_20261029.md`.
- **Resolution**: After preservation/release of the orphaned lock and same-client
  SharePoint renewal, one accepted bootstrap and unchanged-input replay completed.
  Both cycles found the two accepted candidates already present: zero creates,
  two preserved rows, current downstream-effects checks passed. The replay reused
  the unchanged source checkpoint. Independent guarded readback preserves every
  business field and native ETag. Both saved RIMS consumer files were hash-checked
  and independently recomputed from their native delivery receipts and frozen
  accepted baseline. Coverage is two candidates, zero confirmed reviewed links;
  identity material is unchanged, so this cycle requires no model identity update.
- **Evidence**: Original checkout's ignored
  `private/ops/2026-10-29-g06-incremental-acceptance/acceptance.json` binds all
  bootstrap/replay receipts, consumer files and independent readback by SHA256.
- **Limits**: This run created no new candidate and does not replace the retained
  writer create/recovery qualification. Saved consumer output is verified;
  live model refresh/rendering and whole-track coverage are not. Publication-source
  pre-create checks were not exercised because no candidate was missing. Broader
  integration failures remain open. No new fixture or native mutation was needed.

## Review Decision

Source review and material fixes are complete. Keep G06 marked in progress; do
not archive it, mark H01/H02/H03 complete, update production status, or treat ARDC
baseline/Activities work as complete. Preserve the separately accepted historical
ARC consumer and bounded writer evidence at their recorded scopes.

## Phase: Review Fixes

- [x] Task: Reproduce and fix source-context crosswalk validation; pass focused regression — `c7c4bba0`.
- [x] Task: Move runtime/baseline checks before native effects and freeze the verified baseline — `c7c4bba0`.
- [x] Task: Review actual retained writer receipts and missing incremental/RIMS native receipts.
- [x] Task: Verify native bootstrap/readback, unchanged-input replay and saved RIMS consumer output at the accepted two-candidate scope.
- [ ] Task: Complete applicable broader integration and track acceptance gates before closeout.

The review commit and current ownership are recorded in the existing owned handoff.

## Final selected-scope disposition — 29 October 2026

The selected ARC writer/incremental/RIMS consumer-output increment is complete,
reviewed and fixed. The selected requirement-to-evidence mapping is:

| Requirement | Accepted evidence |
| --- | --- |
| Candidate-only durable submission, uncertain-outcome refusal | Writer source/tests; native writer recovery acceptance |
| Native create, exact readback, zero-write replay, same-item recovery | Retained writer acceptance and independent final readback |
| Source/context identity and pre-effect runtime/baseline guards | c7c4bba0 and current36 focused passes |
| Incremental bootstrap and unchanged-input checkpoint replay | ece39a07 native receipts: two preserved, zero creates |
| Independent current native rows and ETags | ece39a07 independent guarded readback |
| Saved RIMS consumer and unchanged accepted identity material | ece39a07 hash checks and exact consumer recomputation |
| Applicable model update/refresh | No new identity-material update triggered; historical ARC bridge/cardinality/reader acceptance retained, no fresh refresh claimed |

Repository integration failures remain visible under their existing owners;
no demonstrated dependency makes them a new acceptance gate for this delivered
slice. No release/package gate is waived and no new release is claimed.

The original broader G06 plan retains expanded H01/H02/H03 requirements. They
are genuinely open, rather than further checks on the completed ARC increment.
Whole-track archive is not justified. The exact scope audit is recorded in
`closeout-scope-20261029.md` (bb121286); earlier blanket statements that fresh
model checks prevent selected-slice closeout are superseded by this disposition.
ARDC remains separate and unfinished. No unchanged check was repeated for this
administrative reconciliation.
