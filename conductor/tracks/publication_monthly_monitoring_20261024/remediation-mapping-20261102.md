> Later same-day update: [native documentation verified](documentation-20261102.md).
> Earlier pending documentation/integration notes below are retained checkpoints.
> RMD-05 remains pending actual natural-run evidence.

# RMD continuation mapped to the completed PM repair

Source packet: `864bce0ecbd26d027edae19ce272ac9e26396d10`, branch
`codex/rims-delivery-remediation-plan-20261102`, canonical planning worktree
`/Volumes/PortableSSD/codex-plans/rims-gaps-20261102`, based on `65ce985d`.
Its "repair not started" and "executor unassigned" text is a planning checkpoint,
superseded for these two flows by [repair commit 480e771d](repair-20261102.md).
The packet was read and mapped, not cherry-picked into this distinct history.

This continuation performed **zero native operations**. It did not patch, invoke,
disable an alert, refresh a provider/model, modify grants, send a notification or
create a monitor/job. Completed receipts are reused. The original failed November
occurrences remain failed observations; the successful recovery remains controlled.

## RMD-01 — Diagnosis at its actual evidence level

The frozen definitions, connections, states, target identities, histories and
native scheduler metadata are in the earlier repair receipt. Runtime flow IDs
and Dataverse workflow IDs are separately reconciled. Native failure/suspension
metadata, the UUID-validation limitation and supported raw GET route were already
inspected. No unchanged collection or read is repeated here.

The monthly future-start definition was saved on 30 October for 1 November, less
than the documented month of setup lead time; the native scheduler had advanced
to 1 December without the November run. That is the supported first-slot
explanation, not an audited service event establishing causality. The observer's
07:45-before-10:00 mismatch is confirmed, but its exact missing first trigger
cause is **unproven**. Started now is not proof of uninterrupted prior enablement.

This satisfies RMD-01's explicitly permitted narrowed-diagnosis exit. The missing
diagnostic is the historical per-trigger scheduling decision or enablement/service
event covering the first observer slot. The retained run/trigger metadata does
not contain it. A future investigation may consume an already-authorised retained
audit/service record if available; this mapping does not broaden access, request
permissions or start an unchanged-blocker loop.

## RMD-02 — Source/noon versus native/10:00 reconciliation

| Evidence or decision | Export | Deadline | Observer |
| --- | --- | --- | --- |
| Canonical planning base `65ce985d`, verified source helper | 07:00 day 1 | 12:00 | Packet recommends 12:05 |
| Pre-repair native definition/receipt | 07:00 day 1 | 10:00, three hours later | 07:45 daily, too early |
| Older observation instructions | Originally 09:00 | 12:00 | 12:05 |
| Selected and saved repair under this chat's direct fix-timing instruction | 07:00 day 1 | 10:00, preserving the deployed three-hour rule | 10:05 daily |

The user's direct instruction authorised fixing the cause and observer timing;
it did not explicitly name 10:05. This lane chose 10:05 as the smallest repair
that respects the existing native deadline, and aligned its local policy helper.
The later planning handoff explicitly preserves that already-authorised newer
repair. Noon/12:05 is a different proposal, not permission to change the saved
service again or silently extend its grace period from three to five hours.

Brisbane is UTC+10: day 1 07:00 corresponds to the preceding UTC date at 21:00;
day 1 10:00 and 10:05 correspond to 00:00 and 00:05 UTC. The stored recovery
observation is explicitly as-of 2 November, references the expected 1 November
07:00 export and 10:00 deadline, and correctly reports lateness. Its occurrence
identity is not inferred from completion time. October is the reporting month
for the November occurrence; September's prior 14-record output is not substituted.

## RMD-03 — Exact candidate, checks and inverse

The [semantic diff](repair-semantic-diff-20261102.json) is reconstructed from the
frozen stored preimages and actually applied candidates, using only the already
qualified annotation/host-key normalization. It contains one exporter change
(past anchor) and four observer paths (past anchor, hour, minute and Due expression).
No action, connection or unknown field is silently dropped. The injected read-only
description difference was reconciled before the successful save.

Private `rmd-mapping/semantic-diff-and-inverse.json` records before/candidate hashes
and proves that applying each inverse delta restores the exact normalized stored
preimage. Each private inverse template is **diagnostic-only**, not directly
executable repair authority. It requires a fresh exact current definition, current
rowversion, ownership check and new one-send journal at any future restoration.
It cannot reuse the old ETag or consumed journal, re-enable failure emails, remove
outputs, rewind pointers or overwrite human edits. Native inverse execution has
**not** been performed or claimed. Reversibility evidence is preserved without
an unnecessary second native mutation.

Qualification reuses the 27 passing Python3.15.1 focused tests, eight unchanged
CAS guard tests and the earlier single-submission guard check. One new focused
regression verifies year and short-month anchor rollover; it passes on the same
version-verified repo-local interpreter. No dependency/environment replacement or
broad testing against another writer's dirty checkout occurred.

## RMD-04 and RMD-04R — Completed bounded repair and recovery

RMD-04 maps to the two HTTP204 exact-rowversion saves and independent final
definition/reference/state/trigger readbacks in `native-repair-acceptance.json`.
Both flows remain Started/Enabled, with alert emails off. The inverse is prepared;
the planning packet must not be read as proof of a native rollback rehearsal.

RMD-04R maps to the earlier directly authorised verification episode, not authority
from this handoff to invoke again. One exporter run succeeded with 1,344 full and
seven October records across 18 fields. Native rows, separate key/count queries,
CSV/HTML/manifest and five independently downloaded files reconcile. The register
snapshot is a distinct 1,348-row population with 68 report parts. One observer
read all required content and saved the correlated late-delivery failure. No
provider/model refresh, deferred-identity admission or additional replay was used.
Creation/replay safeguards and prior output history were preserved at the scope
recorded in the native repair receipt. This is useful recovery, not natural success.

## RMD-05 and preserved independent scopes

RMD-05 remains **pending**. The smallest next native evidence step is a bounded
read of the existing observer's 3 November 10:05 Brisbane natural occurrence,
after it is eligible. That daily result alone cannot close natural monthly
qualification. The stored next exporter slot is 1 December 07:00, followed by
the existing observer at 10:05; verify actual saved schedule/origin and complete
correlated output at that time. No new wake-up, recurring chat or monitor exists.

RMD-06 belongs to the existing grants import owner. Its active files, batches,
cooldowns, native objects, journals and authentication selection are untouched.
RMD-07 remains with the relationship scope. This lane claims neither progress
nor a new assignment for either. No grants/relationship check is repeated merely
to acknowledge the planning packet.

Current owner is chat `01a19b8d-d2e7-7c62-b9e5-32b2c308a57c`, source worktree
`/Volumes/PortableSSD/GitHub/RIMS/monthly-observation-20261102`, branch
`codex/monthly-observation-20261102`. Private mapping/ownership receipts are under
the original repository's ignored `private/ops/2026-11-02-monthly-repair/rmd-mapping/`.
Shared CURRENT_STATE, authentication and other native scopes are not edited by
this no-mutation continuation. Source integration and SharePoint/Loop repair-note
publication remain explicitly pending; no broader completion is implied.
