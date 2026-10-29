# Publication policy and cycle closure — 29 October 2026

## Current native model-to-output verification

The completion chat captured the complete registry (1,651 items, 143 fields,
eight views) and the exact stopped writer. A repeated registry read matched all
item IDs, ETags and values except the response `odata.id` annotation. Exact PMID
or DoRA URL joins map all 1,344 current model publications uniquely to retained
registry items, with zero missing or ambiguous joins. Existing source/canonical
keys and the 303 blank-key legacy rows remain unchanged; comparing canonical
strings alone incorrectly suggests missing records.

The stored Dataverse writer query executes successfully against the existing
model. Readiness reports 1,277 retained PubMed rows, 709 DoRA rows, 1,986 history
rows and 1,344 canonical publications. Independent key queries reconcile the
complete current-generation export and September 2026's 14 records. The existing
exporter generated CSV and HTML for both scopes and read back every field.
These are local output files from live model reads, not new SharePoint uploads,
scheduled delivery or admission of the later 1,279-record raw PubMed candidate.

The CLI-rendered flow capture inserted backslashes before query line breaks;
executing that capture failed with an invalid-token error. Authoritative Dataverse
clientdata contains normal line breaks and exactly matches the successfully
executed query. No native query change is needed or was made. A source validator
now rejects shell-style line continuations so an invalid captured query cannot
silently pass its contract. Focused checks: 24 tests, eight absent-private-package
skips. The first run lacked the documented private test directory; provisioning
that empty directory resolved the fixture error.

Evidence and generated outputs remain under the original checkout's ignored
`private/ops/2026-10-29-essential-registry-capture/`. No flow invocation, model
refresh, registry mutation, send or schedule change occurred. The newer raw-source
admission and associated native processing remain unfinished.

The [PubMed offline continuation](PUBMED_OFFLINE_TYPED_CANDIDATE_20261029.md)
subsequently closes complete offline reconstruction/comparison. Native admission
and notification prerequisites below remain separate.

This source-only continuation follows the [first consolidation packet](PUBLICATION_SOURCE_CONSOLIDATION_20261029.md),
based on `32c204de1b7ee017e8baa9e9716688c6433a63f6` in the same app-managed
`fa70/chhhs-research-publications` worktree and `codex/rims-publications-roadmap`
branch. Delivery chat `01a1831e-449a-7693-af1a-08bb23391c76` owns the publication
source/test paths below; integrator chat `01a182f2-fd8e-7953-9bd2-f9b8002664a6`
retains shared files and native-object assignment. No native scope is assigned.
Original authoring source, operations, journals, bindings and environments remain
read only. No authentication renewal, acquisition, run, send or native save occurs.

## Dependency-closed source

| Source | Behavior and retained-source disposition |
|---|---|
| `publication_policy.py` | Retained permissive inclusion and notice labels. The retained affiliation matching functions are scoped inside this policy so that reviewed attribution survives, `AffiliationsRaw` is recognized and dated aliases require a supported publication interval. Existing shared enrichment/configuration is untouched. |
| `publication_retained_cycle.py` | Pure append-only retention, replay and last-good projection. Missing records remain retained. State validation additionally rejects missing/reassigned cycles and malformed empty generations. Shared PubMed extraction, archive seeding and its CLI are excluded rather than stubbed. |
| `publication_source_metadata_contract.py` | Retained page/cursor/query and UTF8-HEX chunk validation, limited explicitly to the two existing DoRA metadata page templates. Templates match retained source bytes. Error envelopes at every level, incomplete pages and duplicate keys fail closed. No PubMed projection or native writer is included. |
| `prepare_dora_metadata_cycle.py` | Retained same-generation complete metadata reconstruction, summary-field parity, historical preservation, sparse-RSS refusal and deterministic candidate batch identity. Imports use the scoped contract above; nested audit errors also fail closed. Outputs explicitly say no batch commit or native DoRA writer occurred. |
| `prepare_reconciliation_review_flow.py` and `publication_metadata_conflicts.py` | Restore the retained metadata review-flow builder with its actual renderer/cache dependency. Snapshot guards precede frozen review cases; metadata slices require zero new predictions. Existing values remain proposals for human review. This is definition preparation only, with no deployment, connector or AI authority. |
| `publication_current_generation_gap.py` | New read-only validator verifies retained raw XML bytes, exact per-file identity order and complete file/key coverage against the consumed typed marker. It reports typed key gaps while refusing to infer metadata parity on overlapping identities. |

Corresponding tests are included. The two retained PubMed `prepare` tests are
outside this slice with their unimported adapter; pure retention tests remain.
Policy alias tests supply an actual publication date because canonical reference
validity dates differ from the original authoring configuration. No retained
reference configuration is substituted to make the tests pass. Existing reviewed
values, uncertain dates, correction/retraction notices and separate source
identities remain explicit.

## Current frozen metadata gap

The new validator rechecks all 13 retained PubMed XML files, exact saved hashes
and byte lengths, per-file ordered IDs and manifest-wide completeness. It finds
1,279 raw records against 1,277 consumed typed records: two raw-only identities,
zero typed identities absent from raw, and 1,277 overlapping identities.
Complete original XML for the two additions is retained. No reacquisition is
needed merely to recover their original metadata. Their typed/full-metadata
admission remains unaccepted; full metadata parity for the overlapping cohort
is also unproved. Private detail remains private.

The consumed marker's processing-chain model/workspace matches all saved writer
query bindings. This resolves which saved generation the writer consumes; it
does not establish a new processed generation or grant run authority. DoRA's
709-key continuity remains the earlier frozen finding, not new metadata parity.

## Exact native evidence references and rollback limits

All paths below are relative to the preserved original checkout
`/Volumes/PortableSSD/GitHub/RIMS/chhhs-research-publications/`. They are existing
frozen receipts, not current native readback or portable credentials.

| Purpose | Existing reference |
|---|---|
| Writer identity, complete definition, connections and three model query bindings | `private/ops/2026-10-28-e01-t11-cli-implementation/native-read/publication-register-writer.json` |
| Exact saved model-query binding | `private/ops/2026-10-28-e01-t11-cli-implementation/writer-complete-rows-binding.json` |
| Consumed PubMed typed marker/processing chain | `private/ops/2026-10-28-e01-t11-cli-implementation/source-marker-readback/commit.json` |
| Consumed DoRA typed marker | `private/ops/2026-10-28-e01-t11-cli-implementation/cached-source-cycle/dora-consumed-commit.json` |
| Complete registry values/identity baseline | `private/ops/2026-10-28-e01-t11-cli-implementation/registry-full-identity/` |
| Collector Dataverse definition/connection preimage | `private/ops/2026-10-28-source-completion/adoption/pubmed-20261028T081317753856/dataverse-preimage.json` |
| Collector independent saved-definition readback | `private/ops/2026-10-28-source-completion/native/pubmed-post-save-independent.json` |
| Retained model definition before the accepted repair refresh | `private/ops/2026-10-26-runtime-repair/followup-0956/routine-model-fresh-definition.json` |
| Retained postrefresh model definition | `private/ops/2026-10-26-runtime-repair/followup-0956/model-postrefresh-definition.json` |
| Accepted current report binding | `private/ops/2026-10-26-runtime-repair/followup-0956/final-report-binding-readback.json` |
| Historical report rollback readback | `private/ops/2026-10-26-runtime-repair/followup-0956/canonical-report-rollback-readback.json` |

Both retained model-definition responses are HTTP 200 with 61 parts. Legacy
36/42-part guards are not qualified for that baseline. The collector preimage
is for the collector; the report rollback is for the report. Neither is a tested
rollback for a new typed-generation/model/registry admission operation. That
operation still requires an assigned exact target, fresh complete preimage,
defined field scope and recovery proof preserving accepted history and reviews.

### Automatic failure mail is an unresolved native prerequisite

The saved writer and the separate business publication digest are both Stopped,
but both snapshots show `flowFailureAlertSubscribed=true`. The latter snapshot is
`private/ops/2026-10-28-e01-t11-cli-implementation/native-read/publication-weekly-digest.json`.
The account's Power Automate weekly **failure** digest is a separate notification
preference. No current independent receipt showing that preference disabled was
identified in the bounded evidence reviewed here. A stopped business digest
does not prove service failure mail is suppressed.

Before a controlled native failure test, the assigned native owner must qualify
and read back both per-run failure-alert suppression for the exact tested flow
and account-level weekly failure-digest suppression. Preserve original settings
and approved recovery scope. This packet neither changes notification settings
nor invokes a flow. Successful source tests or alert-free action graphs do not
close this automatic-mail path.

## Remaining dependency-specific acceptance gaps

1. PubMed current-cycle preparation depends on retained functions missing from
   canonical `build_native_commit_package.py`, plus
   `reconcile_pubmed_source_cycle.py`, `capture_report_bound_source_union.py` and
   their shared query-projection/raw-capture helpers. Review their pure contract
   closure with the shared owner; do not replace the canonical builder wholesale.
2. The optional acquisition-health adapter is still not dependency-closed. Static
   inspection finds missing `MAX_READ_ATTEMPTS` and `TRANSIENT_HTTP_STATUSES` in
   the current DoRA collector, and absent `source_http_retry`, `crossref_source`,
   `datacite_source` and `clinicaltrials_source` modules. These broader provider
   sources were not copied or stubbed. Runtime and provider qualification remain.
3. New DoRA candidate state needs an assigned exact existing commit sink,
   operation-specific permission, preimage/rollback, definition readback and
   full output proof. Preparation does not turn the PubMed-only writer into a
   DoRA publisher. H03 reviewed-field and H04 failure/recovery remain separate.
4. Current PubMed metadata admission must preserve both raw-only identities and
   all overlapping records while verifying the full metadata/author payloads.
   The saved writer binding and raw key proof do not establish that processing.

The ignored lane directory `private/ops/publications-cycle-closure/` contains
source dispositions, frozen metadata-gap replay, static adapter dependency gaps,
hash-bound native prerequisite references and local verification. Bindings and
credentials remain at their original owner paths. Shared records, configuration,
dependency locks, runtime, hooks and workflows were not changed.

## Verification

The existing repo-local interpreter remains Python 3.15.1 with its existing
locked dependencies. Focused pytest: 51 tests and 55 subtests pass. All 13 affected
source/test files pass Ruff and formatting checks. Final full harness: 1,087 tests,
25 capability skips, 446 passing project checks, passing web-first contracts,
Conductor structure and tooling preflight. The earlier import-cleanup failure
log is preserved; restored-import failure-only and final full checks pass.
No skip, retry plugin or dependency was introduced. These are local checks;
they establish no native execution, notification suppression or acceptance.
