# Solo context and harness workflow

## Completion cadence — 29 October 2026

Use the three exits in [current missing outcomes](CURRENT_MISSING_OUTCOMES.md#completion-scope--29-october-2026).
Do not select the first historical unchecked task or expand into the whole roadmap.
Start from the latest relevant receipt and next missing exit, then use the existing
CLI/API and retained bootstrap. Read only the changed inputs and required instructions.
Build another helper only when an existing tool cannot perform that exit.

During code edits, run affected behavior tests. Documentation edits need link and
consistency checks. Run the required full integration and clean-package gates at
one coherent code/release milestone; reuse a successful receipt while its inputs,
environment and scope are unchanged. Keep required hooks and hosted checks.
Do not run the full suite again merely to repeat the same evidence in another chat.

Native changes need exact saved-state and relevant runtime/output proof, with a
recoverable preimage. Reuse existing isolation and accepted cases unless a relevant
change invalidates them. Routine authorised work proceeds without another approval.
Record a genuine blocker once with its exact unblock condition, then work on the
next independent essential outcome. Deferred roadmap work is not the default
substitute for a blocked essential. Finish with one scoped commit/handoff; do not
add a tracking framework, recurring coordinator or extra acceptance document.

## Separate-chat execution — 13 October 2026

Use the [parallel delivery assignments](PLATFORM_COMPLETION_PLAN.md#parallel-delivery-assignments--13-october-2026).
One coordinator owns integration; separate chats may own disjoint local outcomes.
At dispatch specify base commit, required reviewed input snapshot, exact editable
files, output paths, invariants, smallest checks and handoff dependency in the
existing task packet. Reserve new filenames too. A separate worktree/branch
isolates source edits, not native objects, CLI login state or request quotas.
Do not copy the dirty original history or private evidence into a remote branch.

Shared contract/catalogue/manifest/dependency edits return as proposals to the
coordinator. Use unique ignored package/cache paths and preserve in-flight native
operations. Only the current recovery owner may change shared authentication or
control the browser. Helpers return a commit and short handoff; the native owner
keeps CURRENT_STATE and the coordinator merges plan/catalogue updates serially.
No new lease service, recurring monitor or second status ledger is required.

One owner, one Conductor backlog, one canonical platform instance per tool. No mandatory PR, second reviewer, ticket system, bot framework or new hosted service. Git history supplies change history; track plans supply remaining tasks; CURRENT_STATE supplies the short resume point. Avoid duplicating status into additional ledgers.

## Commands

```sh
.venv/bin/python scripts/agent_harness.py context --task grants
.venv/bin/python scripts/agent_harness.py doctor
.venv/bin/python scripts/agent_harness.py check --task grants
.venv/bin/python scripts/agent_harness.py check --task all
```

Other context/test routes: publications, organisation, platform. The harness works from any directory, uses its running interpreter, executes fixed commands without a shell, runs all required checks despite an earlier failure, and returns nonzero if any check fails. It never deploys or marks a track complete. The doctor checks files/test selections, not licences or browser access. Paths route reading; mandatory instructions must still be read completely. The harness does not upload context or include private payloads.

## A task packet for a smaller model

Use this block inside the existing active track plan, not a new system:

```text
Outcome: one observable behaviour
Inputs: exact source/config/fixture paths
Edit scope: files this task may change
Invariants: identity, review state, dates or data that must survive
Cases: normal, missing, conflicting, replay and failure as applicable
Verification: exact commands and expected result
Platform proof: not applicable, or exact readback needed
Rollback: scoped patch revert, or preserved platform definition
Completion: changed behaviour, evidence, remaining work
```

Default to one implementer. Use temporary subagents only for independent research, disjoint adapters or adversarial review. Give each the outcome, file ownership, context pointers and acceptance cases; have one coordinator integrate edits and perform platform writes. Do not introduce permanent agent roles or extra branches merely to use more agents. If no subagent tool is exposed, report that plainly.

## Verification and resumption

Use focused tests during work and the full harness at integration milestones. The all route runs Python tests, project and web-first validation, Conductor structure, tooling preflight and the offline Node CLI guards. Clean-package validation invokes the same harness, so missing Node source dependencies cannot be hidden by Python-only success. The configured Python runner is unittest: test cases must be discoverable TestCase methods. Harness configuration rejects standalone `test_*` functions, which unittest would otherwise silently ignore; this static guard does not replace execution or establish behavior coverage. Tests should exercise user-visible failure modes. A skipped private fixture is a skip, not native proof. Add adversarial cases for same-title/different-round records, invalid dates, changed deadlines, concurrent duplicate creation, and unsubscribe-before-send as relevant features are implemented.

On failure, retain the failing case, fix the cause and rerun affected checks. Do not update a golden manifest solely to turn a failure green. On interruption, update CURRENT_STATE with the exact next action; do not leave a transcript dump. Before completion, inspect the scoped diff and preserve other work. Commit coherent task changes when appropriate; no remote push or forced cleanup is implicit.

Local tests, native execution, visual rendering and delivery each need their own evidence. The harness reports only local results. Existing approval requirements apply to actual gated actions, not to routine authorized local work.
