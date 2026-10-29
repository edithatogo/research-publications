# G06 RIMS connection — 29 October 2026

User-selected scope: connect G06 incremental results to the existing RIMS consumer.
G06 remains in progress; broader H01/H02/H03 gates are unchanged.

- [x] Reuse the current-list consumer and registered identity-material contract.
- [x] Connect verified native incremental delivery to consumer preparation before
  processing-checkpoint advancement; bind source/row/context hashes.
- [x] Preserve native review, ETags, unknown rows and distinct candidate/confirmed
  admission. Label identity-material changes and absent model baselines explicitly.
- [x] Refuse prepared/failed receipt inputs and intermediate checkpoint reuse.
- [x] Prepare a retained-native comparison: two candidates, zero confirmed,
  unchanged identity material relative to the supplied accepted baseline.
- [x] Focused verification: 23 Python cases plus 10 Node cases, syntax and diff checks.
- [x] Complete fresh incremental delivery and saved consumer output — `ece39a07`; both existing keys preserved, with independent native readback and exact consumer recomputation. New-key publication-source checks were not needed.
- [ ] If new identity material requires a model update, use the existing approved
  isolated model/rollback path, binding readback, targeted refresh and complete
  key-set/cardinality/reader checks. Do not replace an existing bridge or assume
  the historical 52-part builder fits the current model/report.

No native model, report, list, schedule or sharing changes occurred in this step.
The retained output is ignored private evidence, not a delivered RIMS refresh.
See `docs/FUNDING_RELATIONSHIP_CONSUMER.md` for CLI/output semantics and the owned
handoff for exact worktree, ownership and the native dependency.
Project validation passes 454 checks. Broader unittest/web-first checks remain
failed on the inherited source/dependency closure; see the handoff and retained
logs. These failures and the pending native cycle prevent whole-track closure.

## Terminal scope reconciliation — 29 October 2026

This RIMS consumer-output connection is complete and reviewed. The conditional
model identity update is not applicable to this cycle: both verified consumers
match accepted identity material exactly. No fresh model write/refresh is required
solely to close this increment. Earlier pending-lock/native-cycle statements are
superseded by `ece39a07`; live rendering and broader H01-H03 remain separate.
