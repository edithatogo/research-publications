# Executable plan

Owner: current publication-source-coverage chat. Source worktree: `/Volumes/PortableSSD/GitHub/RIMS/publication-source-coverage`, branch `codex/publication-source-coverage`. Private native bindings/journals remain in the original checkout. This scoped track/register delta is a source packet for the repository integrator; it does not alter another checkout or claim a main merge.

Legend: `[x]` accepted evidence, `[~]` active implementation/wait with a live process, `[ ]` outstanding. Every native task needs its own receipt; do not infer completion from a prepared script.

## A. Freeze and reconcile accepted work

- [x] **P01 — Verify worktree, source ownership and Python3.15.1.** `git worktree list`, scoped status, `.venv/bin/python --version`; retain original dirty checkout and other lanes.
- [x] **P02 — Bind the frozen denominator and native preimages.** Reuse canonical1,344, monthly14, export18, existing model79-part definition and flow preimages. Evidence: accepted checkpoint; revalidate drift at P12/P14 before writing.
- [x] **P03 — Reconcile accepted Europe PMC/OpenAlex delivery.** Europe PMC1,286 matches/58 missing identifiers; OpenAlex1,284 matches/57 missing/3 no-match. Preserve closed Crossref and accepted OpenCitations scope.
- [x] **P04 — Reconcile saved Semantic Scholar native delivery.** 1,266 matches,19 no-match,12 missing,2 ambiguous,45 deferred;45 populated field paths,20 requested parent fields. Native81-page byte proof,4,032 unique source/publication pairs and successful ingestion run accepted; quota-limited only.
- [x] **P05 — Record and verify baseline invariants.** All1,344 canonical keys and18 export values exact; monthly14 exact;1,348 registry source keys unique; zero admission candidates; original recurrence and Stopped state restored.

## B. Recover collection and finish retained-evidence review

- [x] **P06 — Reconcile own stale locks.** Verify recorded collector/continuation PIDs absent; preserve both lock directories and owners before clearing. Evidence: `private/ops/2026-11-03-semantic-scholar-recovery/lock-recovery-receipt.json` in original checkout. No authentication/native locks touched.
- [x] **P07 — Execute one cache-resuming collection attempt.** Existing collector command below; one provider request returned429 on3November. Retain complete response/header/stop receipt and all previously completed cache responses.
- [x] **P08 — Review the14 identifier exceptions without API calls.** Compare frozen rows with retained Europe PMC/OpenAlex and Semantic Scholar evidence. Preserve12 missing/invalid identifier records (including one title in the DOI cell) and2 DOI/PMID conflicts; no safe automatic correction is supported. Evidence: private `identifier-review.json`. Do not treat these as45 deferred lookups.
- [~] **P09 — Resume the collector after conservative backoff.** Existing `private/no-login-sources/resume-single-controller.py`, session85856 at recovery; verify PID/handle before any restart. Three-second pacing, cache-first, one-hour repeated429 backoff, longer provider delay honoured. Status must be refreshed from live process and cache, not this dated session alone.
- [ ] **P10 — Finish45 deferred exact-identifier lookups.** Dependency P09/provider availability. Done only when cache coverage has zero deferred, with retained200/verified404 receipts or another evidence-backed terminal disposition. Never infer a no-match from429.
- [~] **P11 — Retain one native continuation waiting on P10.** Existing `private/ops/2026-11-03-semantic-scholar-complete/continue-after-collection.py`, recovery session44465. Preserve one owner; verify actual process before restart. Waiting is not native completion.

## C. Promote the changed generation once

These commands run automatically in order through P11; use them manually only after proving no live owner and inspecting any existing intent/receipt. `OPS` means the original checkout's ignored `private/ops/2026-11-03-semantic-scholar-complete`; use the lane's `.venv/bin/python`.

- [ ] **P12 — Freeze changed coverage and qualify exact-target drift.** `python "$OPS/prepare-full-generation.py"`; default rejects deferred coverage. New `native-complete-stage` directory, full20-parent/nested-field counts, source hashes and combined denominator. Native uploader checks current model/flow against accepted preimages before mutation; a drift mismatch stops the pass.
- [ ] **P13 — Upload changed pages with bounded manual batches.** `python "$OPS/direct-upload-batches.py"`. Skip unchanged filename/hash pairs; preserve solution connection map. Each bounded batch verifies manual trigger, runs once, reads terminal success and stops the flow. Save all intents and restore pre-upload flow afterward. No duplicate writes/retries.
- [ ] **P14 — Import only four source-reader parts.** `python "$OPS/finish-model.py"` invokes `deploy-model.py`, checks exact current79-part model, sends once, polls accepted import to success and verifies exact saved definition. Preserve `MissingField.UseNull` heterogeneous-row fix and all other model parts.
- [ ] **P15 — Complete transactional refresh.** Same model driver invokes `send-refresh.py`, refreshes only four source tables with retryCount0 and waits for Completed.202 alone is not acceptance.
- [ ] **P16 — Reconcile native source bytes and field coverage.** Model driver invokes `reconcile-native-bytes.py` and `reconcile-model.py`. Prove all81 pages by SHA256,4,032 unique source/publication pairs, every source-specific field-presence count and explicit missing/ambiguous/no-match dispositions.
- [ ] **P17 — Reconcile canonical and monthly contracts.** Same model reconciliation must prove all1,344 keys and18 values unchanged, plus exact14-key retained monthly set. Stop promotion/restore affected target from verified preimage on corruption; inspect uncertain writes before retry.
- [ ] **P18 — Run the bounded native ingestion flow once.** `python "$OPS/finish-flow.py"`; exact preimage guard, temporary manual trigger, existing qualified CLI route, one run, terminalSucceeded receipt.
- [ ] **P19 — Verify admissions and deduplication.** Read actual run action content: expected evidence counts, zero unintended admission candidates and all1,348 existing registry source keys unique. Do not collapse distinct canonical publications to deduplicate provider requests.
- [ ] **P20 — Restore and independently read native state.** Flow driver disables and restores original recurrence and valid connection-reference map; exact stored definition and runtimeStopped readback. No schedule activation.
- [ ] **P21 — Accept the complete generation.** `python "$OPS/verify-final-flow.py"`; require `PASS_COMPLETE_FROZEN_LOOKUP_SET`, collectionComplete true, zero deferred, accepted model/byte/run/restoration receipts. Prepared scripts or a quota checkpoint cannot close this task.

## D. Close out without repeating accepted checks

- [ ] **P22 — Write the final coverage/report.** Include source dispositions, all20 requested-field counts, field paths, identifier decisions, provider receipts and exact remaining dependencies. Update the dated source handoff; preserve old bootstrap/quota reports as history.
- [ ] **P23 — Reconcile this plan, metadata and register.** Close only evidence-backed tasks. Keep native documentation publication explicit as pending unless versioned SharePoint/Loop save/readback actually occurs; no login or wider publication is implied. Preserve existing broader T11/E01 acceptance limits.
- [x] **P24 — Run relevant structural checks and commit this owned source packet.** Conductor links/metadata/status checks for documentation; reuse accepted source unit/project/web-first receipts because no collector/source behavior changed. If source code changes later, run its focused test before native use. This packet passed the24-task/link/metadata check and446 project checks; unchanged source/unit/web-first receipts were reused. Required broad integration checks remain at their actual release milestone. Final generation edits need their own affected checks.

## Exact collection command

From the source worktree, the existing controller invokes:

```sh
.venv/bin/python scripts/collect_semantic_scholar_publications.py \
  --transport single --interval 3 --max-throttle-retries 0 \
  --bootstrap private/no-login-sources/semantic-scholar-probe.json \
  --canonical ../chhhs-research-publications/private/ops/2026-10-29-essential-registry-capture/canonical-export-envelope.json \
  --output private/no-login-sources/semantic-scholar-single
```

Do not run a second copy while P09 owns the cache. The controller state records the next allowedUTC request time; ignored files are not shipped with source commits. First inspect current handles/locks/receipts after an interruption, then resume the uncompleted operation only.
