# Plan — Publication monthly follow-up and monitoring

## Phase 1 — Natural monthly occurrence and correlated observer

- [x] **PM-F01 — Observe and reconcile the first natural monthly export.**
  **Reconciled: MISSED; delivery acceptance failed.** Transferred from E08-F01
  on 24 October 2026. Original observation instructions: after
  1 November 2026 07:00 Australia/Brisbane, use the qualified read-only CLI route
  to inspect the existing 07:00 scheduled occurrence. Verify trigger origin,
  terminal status, period/generation, source/query/refresh lineage, complete
  CSV/index/parts/manifest, count/key-set/content reconciliation and existing
  access/history. Do not resubmit. Phase verification: retain the actual run,
  output evidence and explicit pass/failure disposition in existing ignored
  operational records; update this task only when observation is reconciled.
  **2 November final readback:** complete run and trigger collections show no
  1 November occurrence; the complete reporting-folder read has no publication
  artifact created on that Brisbane date. The saved native schedule is 07:00,
  superseding the historical 09:00 assumption for this inspection. Latest source
  success predates the occurrence. No scheduled November generation exists to reconcile
  counts, key sets, parts or refresh lineage. This closes the observation with
  a failure handoff, not successful export acceptance. See
  [reconciliation](reconciliation-20261102.md).
- [x] **PM-F02 — Observe and reconcile the independent observer.**
  **Reconciled: MISSED FIRST OCCURRENCE; later missing-delivery detection
  verified.** Transferred from E08-F02 on 24 October 2026. Original instructions: after
  1 November 2026 07:45 Australia/Brisbane, inspect the existing naturally
  triggered observer and stored result through qualified read-only CLI access.
  Correlate the intended PM-F01 occurrence and verify the reported healthy,
  missing or failed status against actual evidence. Reuse existing commissioning
  receipts; no new monitor, fault injection, schedule or send. Phase checkpoint:
  record both task outcomes and any owner-directed defect handoff, preserving
  private evidence and distinct technical/operational acceptance statements.
  **2 November final readback:** no 1 November run/trigger is retained. The saved
  native observer schedule is 07:45. Its actual 2 November 07:45 natural run
  terminated Failed after saving, reading and verifying the independently
  downloaded `MISSING_DELIVERY_EVIDENCE` receipt. That receipt references the
  expected 1 November 07:00 export and 10:00 deadline, with no export run,
  manifest, health receipt or failure receipt. This later detection does not
  substitute for the missed first-day observation. No healthy status is claimed.

## Observation handoff — superseded by the later repair assignment

The selected observation work is complete with failure dispositions. Preserve
the last good export and existing native state. The existing implementation
lane must investigate the missing first occurrences and the observer's 07:45
schedule preceding its own 10:00 deadline under separate repair authority;
execution of those repairs is currently unassigned. No replay, definition or
schedule repair is authorised by this read-only handoff. No automatic wake-up
or recurring automation was created. Other E08 tasks retain their own scope.

## Phase 2 — Existing-flow repair, authorised 2 November 2026

- [x] **PM-R01 — Investigate and repair the existing schedules.** Fresh native
  scheduler metadata and the published first-slot lead-time constraint identify
  the exporter's future-start configuration risk. The observer's retrospective
  first-slot cause remains unproven; its 07:45 versus 10:00 mismatch is confirmed.
  Both existing triggers now use a past anchor. Export remains monthly day 1
  07:00; observer moves to daily 10:05, after its unchanged three-hour deadline.
  Exact-rowversion saves, frozen preimages, unchanged connections/actions and
  final enabled/Started readbacks are verified. No flow was created.
- [x] **PM-R02 — Verify the two existing flows with native evidence.** One
  guarded exporter invocation succeeded. All 1,344 full and seven October
  records reconcile across 18 fields, native keys/counts/CSV/HTML/manifest and
  five independent CLI stored-file downloads. One guarded observer invocation
  verified the register CSV/index/all parts and retained the correct correlated
  late-delivery failure. Both failure-email subscriptions are now false; no
  email was sent. This is controlled execution, not a post-repair natural tick.

## Current terminal handoff

See [repair evidence](repair-20261102.md). The native service reports the next
observer tick as 3 November 10:05 and the next exporter tick as 1 December 07:00,
Brisbane. No new observation job or automation was created. Preserve the earlier
missed-occurrence dispositions. Native SharePoint/Loop documentation is verified at the
[scoped preservation boundary](documentation-20261102.md); source integration
uses an isolated canonical-main worktree. No other source, model, flow or chat scope transfers.

## RMD continuation — evidence mapping, 2 November 2026

The source packet `864bce0ecbd26d027edae19ce272ac9e26396d10` predates this lane's
completed repair receipts. It is reconciled here without cherry-picking its
distinct authoring history or repeating a mutation. See the
[mapping, policy reconciliation and inverse boundary](remediation-mapping-20261102.md).

| Packet item | Existing evidence and disposition |
| --- | --- |
| RMD-01 | PM-R01 and native before/trigger receipts satisfy the narrowed-diagnosis exit. Monthly first-slot risk is documented; exact observer historical cause remains unproven. |
| RMD-02 | PM-R01 selected repair retains the native three-hour deadline: export 07:00, deadline 10:00, observer 10:05 Brisbane. The packet's noon/12:05 recommendation does not override the newer repair. |
| RMD-03 | Exact semantic diff, preserved before/candidate hashes, passing focused checks and a diagnostic-only inverse template are retained. Inverse roundtrip is locally exact; native inverse execution is not claimed. |
| RMD-04 | PM-R01 exact-rowversion saves and independent full definition/connection/state readbacks complete the bounded repair. No second save or rollback test was performed for this mapping. |
| RMD-04R | PM-R02 already recovered October's seven records and 1,344 full records across 18 fields through the earlier directly authorised verification episode. Recovery is controlled/manual, not natural success. |
| RMD-06 / RMD-07 | Not assigned to this lane. Preserve active grants import files, batches, cooldowns, journals and owner, and the separate relationship scope. |

- [ ] **RMD-05 — Qualify the next natural operating path.** Retained native
  scheduler metadata gives the next observer tick as 3 November 2026 10:05
  Brisbane; its existing daily occurrence can supply a first post-repair natural
  observer receipt. Full natural monthly qualification awaits the exporter on
  1 December 07:00 and that day's observer at 10:05, subject to the actual saved
  schedule at inspection. Keep those two evidence levels separate. Do not create
  a new reminder, monitor, flow or recurring chat job; do not poll before due.

Current owner is chat `01a19b8d-d2e7-7c62-b9e5-32b2c308a57c`, isolated source lane
`/Volumes/PortableSSD/GitHub/RIMS/monthly-observation-20261102`. This continuation
performed no native operation and holds no shared authentication recovery lease.
The original November MISSED dispositions and successful controlled repair remain
closed; this track stays in progress solely for the pending natural qualification
not an active native mutation.

The canonical31October plan retained a noon delivery recommendation and a07:50
app follow-up. Those are preserved historical planning assumptions. The newer
native repair retains its actual three-hour10:00 deadline; no new follow-up
automation was installed. See the policy mapping before any later change.

## RMD-05 eligible natural observer read — 3 November 2026

- [x] Inspect the first eligible natural observer occurrence using the guarded CLI.
  Recurrence succeeded about 10:05 Brisbane; run failed with
  LATE_DELIVERY_TRIGGER_ORIGIN_UNVERIFIED. Evidence reads and observation save/
  verification succeeded. See [review](rmd05-review-20261103.md).
- [ ] Successful natural monthly exporter and correlated observer qualification
  remains pending the next eligible December 1 occurrence. This natural observer
  failure does not close RMD-05 or undo the accepted controlled repair.

## Expected-failure diagnosis recorded —3November2026

- [x] Correlate the independently downloaded November3 observation to the exact
  November2 recovery export and saved decision rules. The late/unverified-origin
  failure is expected; no new observer defect is established. See
  [diagnosis](rmd05-diagnosis-20261103.md).
- [ ] RMD-05 remains pending actual1December07:00 exporter,10:00 deadline and
  10:05 observer evidence. No replay, new monitor or email.

- [x] Record the diagnosis in the versioned SharePoint repair guide and additive
  field-guide/catalogue notes, preserving accepted content and history.
- [x] Add and reopen-verify the same diagnosis in the existing Loop page; prior
  text and component identities remain preserved. RMD-05 stays pending for
  the actual December1 natural monthly path.
