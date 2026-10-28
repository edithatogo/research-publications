# Worktree reconciliation — 29 October 2026

The main source of friction is two divergent source baselines and stale ownership
and status text. The many old branch names mostly represent delivered work.
Keep one integrator and canonical source base; retire duplicate execution from
the backlog without deleting its evidence or restarting archived chats.

## Verified Git state

The canonical source base is `origin/main` at `76d42f84` (PR55). The existing
GitHub repository is currently public; older handoffs calling it private are
historical. This reconciliation changes no visibility or sharing setting.

Of 53 pre-existing local branch refs, 20 tips are ancestors of main and another
29 have merged PRs. Squash merges explain why those 29 tips can still appear
ahead/behind. Their merged heads match28 tips; the remaining grants tip has one extra patch
identical to `455c4830`, already in main through PR20. They need no second merge. The complete branch/PR mapping is in
[the aggregate inventory](../audit/worktree-reconciliation-20261029.json).
There were no open PRs at entry.

| Remaining ref | Disposition |
|---|---|
| `codex/pubmed-dora-runtime-qualification` at `ae9217db` | One commit directly on current main. Fast-forward integrated here: explicit response-age bounds reject stale/future/invalid DoRA cache reuse, with tests and scoped handover. Native reuse remains disabled/unqualified. |
| `codex/conductor-goal-source` at `266d1819` | Its exact standalone forecast dependency record is integrated here. The worktree-specific CURRENT_STATE addition is superseded by this chat's assignment. No weights, inference, deployment, shared dependency promotion or scientific acceptance is claimed. |
| `implementation/webui-first-v040` at `cde439c0` | Preserved authoring/native-evidence checkout. Its history has no common ancestor with canonical main. Never use an unrelated-history merge or blanket staging to import it. |
| Local `main` at `92c1d0e0` | Preserved older history, also unrelated to canonical main. It is not the current source integration target. No force reset, rename or history replacement performed. |

There were two registered worktrees before this reconciliation: original authoring
and the clean DoRA checkout. A third, app-managed integration worktree now provides
the sole writing lane. The archived forecast checkout path is no longer registered;
its committed branch remains recoverable. Old branch refs are retained as evidence,
not dispatched as active work. No custom ref/index workaround or hook bypass.

## Original checkout disposition

The original checkout had 236 modified tracked entries, 55 unstaged deletions and
718 untracked status entries (1,027 individual untracked paths). Its index was
empty. Every deletion has a corresponding file under `conductor/archive`;
30 retain exact old bytes and 25 include later edits. They are archive moves with
preserved counterparts, not 55 unexplained lost files. Nothing was staged here.

An exact-byte inventory across tracked and individual untracked paths finds
390 files identical to canonical main, 298 differing at the same path, 1,632
authoring-only files, and 66 missing/symlink entries. These are file counts, not
unfinished features: archives, documentation, generated artifacts, tests and
private tooling account for much of the volume. Authoring-only files are not
automatically safe or useful for canonical publication.

The raw status, per-path blob fingerprints and archive counterpart inventory are
retained only in this worktree's ignored
`private/ops/2026-10-29-integration/`. No tenant snapshots, credentials, source
records, private bindings or mutation journals were imported. The original
checkout, index and environment remain in place; a grants-monitor process was
observed there. Chat archival is not a process stop or native-operation release.

## Additional authoring packet integrated

The retained `publication_batch_contract.py` and its15-test module are integrated
with exact source bytes. Before the repair, those tests produced11 failures and
three errors against canonical main. Afterward all15 pass: malformed inputs,
empty error envelopes, invalid partial flags, cursor cycles, missing terminal
pages and untrimmed/non-text keys fail closed. Valid positive complete batches
and explicit null initial cursors remain supported. This local contract has no
native invocation path and does not prove live pagination or writer acceptance.

## Actual remaining work

This table reconciles saved source/receipts; it is not a new live tenant audit.
Later original-checkout evidence is labelled explicitly rather than copied into
main as an acceptance claim. Historical receipts remain with their existing owner.

| Work | Current position | Next meaningful exit |
|---|---|---|
| Source consolidation | Three small source packets integrated; large original-checkout delta preserved and inventoried. This is the main repository debt. | Migrate reviewed dependency-closed packets with their tests and receipt references, starting with G07 observer/worker source, remaining publication validators and metadata comparators, then report/source-generator work. Reconcile licence/NOTICE packaging and current setup instructions within those packets. Avoid bulk-copying generated/private tooling or replacing canonical-only fixes. |
| G07 reliable operation | Main already contains PR35 original-retention and PR51 scheduled NIH chain/recovery acceptance. Later authoring evidence reports hourly local monitoring, own-notification activation and natural/expiry-recovery observations. | Integrate that later source/receipt handover. Preserve the live job and one-send journal. Real reviewed notice/changed deadline, sustained operation and retention/credential-disaster limits remain distinct; current Needs Review is not an implementation defect. Do not rerun mail or change schedules for Git reconciliation. |
| Publication acquisition/current admission | Main contains selected saved-generation key/metadata/export/preservation closeout (PR53/55). Original-checkout records compare 1,279 retained PubMed IDs against 1,277 consumed and account for DoRA metadata. | Integrate the current validators/comparators and determine the genuinely missing current typed-admission/runtime delta from frozen receipts. Historical full-generation accounting is complete. Archived E01/T11 broader runtime/recovery scope must not be silently recommissioned. Crossref retained-operation state needs its existing terminal receipt before a new operation. |
| E04 dashboard and forecast | Original-checkout 28 October review says P00 complete, P01–P12 whole exits open and native writer held local-only. Forecast dependency/import slice is retained here exactly. | Integrate the scoped report/metric/topic/researcher sources and coverage contracts, then finish the selected local work. Scientific baseline/rolling-origin evaluation, weights/inference and native rendered/accessibility acceptance remain separate. Preserve the writer hold. |
| T18 outcome evaluation | Original track describes an accepted first native model/report slice and reader recovery; later slices are deferred. | Integrate exact slice source and references, then identify missing end-to-end reader, accessibility/performance exits. Do not rebuild the accepted slice or expand deferred scope. |
| E10 runtime | This worktree runs Python 3.15.1 with existing hash locks. Source/CI qualification is accepted; later authoring record has a qualified candidate native-read probe. | Complete supported shared Fabric helper-host terminal handover and final active-use audit. Do not replace another session's host/environment. The old runtime compatibility exception is superseded in AGENTS.md. |
| T14 unattended monthly output | Full/monthly historical exports and recovery are accepted. Archived dataset chat records first automatic export/monitor observation due 1 November 2026 after 12:05 Australia/Brisbane. | Inspect the same scheduled handles and outputs after the occurrence. This is waiting for operational evidence, not new implementation. Confirm the retained schedule receipt before any action. |
| Release and optional expansion | Historical packages/versions remain valid at their declared scope; broader grants mappings/sources and source access remain limited. | Cut a new source package only at a coherent integrated milestone with clean-extraction proof. Optional providers, production, wider access/delivery and native activation remain separately selected scopes. No new common framework or duplicate preparation lane. |

## Evidence reused instead of repeated

[Whole-system closeout](WHOLE_SYSTEM_CLOSEOUT.md) accepts the selected historical
six-stage lineage, all 14 shared metadata fields, 18 exported fields and registry
preservation. The 144 semantic uncertainties remain explicit. It needs no repeat
harvest, refresh or export just to close stale checkboxes.

[Original retention](GRANTS_ORIGINAL_RETENTION.md) and
[scheduled grants chain](GRANTS_UNATTENDED_CHAIN.md) supersede the old missing
handover/chain rows in CURRENT_MISSING_OUTCOMES. Bounded scheduled qualification
does not prove long-term operation or broaden notification authority.

## Verification of this integration

Fresh worktree-local Python reports 3.15.1; dependencies use the existing exact
hash lock. Full unittest discovery after both code repairs: 1,008 tests, 25 capability skips, no failures.
Project validator: 446 checks pass. Web-first contracts pass with native acceptance
false. These checks qualify local source integration only. Existing private
native receipts are consumed by reference; no provider harvest, native mutation,
mail, authentication recovery or schedule operation was submitted.
