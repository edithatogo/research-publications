# Workflow

Current selection: the user-authorised [GrantConnect-first plan](../docs/GRANTS_CLI_COMPLETION_PLAN_20261031.md), with one test/verification per changed feature, no scheduled checks and NIH expansion deferred. The single RSS run has a provider HTTP403 blocker recorded in CURRENT_STATE. Earlier essential scope remains accepted. Historical selection: [completion scope](../docs/CURRENT_MISSING_OUTCOMES.md#completion-scope--29-october-2026). Follow its three essential exits and [execution cadence](../docs/SOLO_AGENT_WORKFLOW.md#completion-cadence--29-october-2026). Historical discovery, expansion and fallback instructions below do not reopen accepted work or deferred features.

## Current route precedence — 13 October 2026

Follow the [shared-data delivery contract](../docs/PLATFORM_COMPLETION_PLAN.md#shared-data-delivery-contract--13-october-2026): CLI/API-first on qualified exact targets, existing archive bootstrap, complete raw payload/schema retention before vertical filtering, and one writer per file/object. Historical browser-first/no-CLI statements and dated completion claims do not override this direction. Preserve current source scope, permissions, isolation, rollback and explicit activation/delivery gates. The publications chat retains its current objects and checkpoint; shared-data work requires disjoint scope or explicit handoff.


1. Read conductor/index.md, product, technology, code standards and the dependency-satisfied track's spec/plan. Use actual observed state and preserve unrelated work.
2. Prefer the qualified exact-target CLI/API operation; inspect installed help or MCP schemas. Use BrowserOS neo only for a named unsupported/failed operation under shared-UI ownership. Missing tools alone do not establish a tenant denial or justify VM fallback.
3. Before model writes, identify exact tenant/workspace/report/model IDs, inventory consumers, preserve recoverable definitions and prove an isolated development model with a reversible canary write/read-back/rollback. A copied report can still use the original model.
4. Prepare one bounded, reviewable candidate containing related queries, measures, model changes or visuals. Avoid a native save/test cycle for each individual edit. Recheck the baseline revision before a write. Record before/after and native read-back privately. Stop on concurrent changes or unauthorised scope.
5. Run focused changed-behavior tests and affected structural checks. Documentation-only edits require relevant structural/link checks. Reuse unchanged accepted evidence; full integration checks run at integration/release or broad-contract milestones. Native execution/readback remains separate.
6. Update source code, generated definitions and reviewed contracts together. Do not automatically regenerate the frozen expected manifest to make an unreviewed difference pass. Each contract change needs an outcome-linked reason in the track review.
7. Evidence gates fail closed: do not distribute incomplete/stale output, treat absent optional metadata as missing, retain ambiguous records, and preserve the last good archive. Never silently drop DORA-only rows or report API failures as zero publications.
8. Close only completed tasks with evidence references and commit `type(scope): subject`. Completion of local T09 does not close any live track. Archive native tracks only after actual accepted execution.
9. No public publishing, sharing/permission/RLS changes, production rebind, mail send, flow activation, license/capacity purchase or remote repository creation without the corresponding explicit approval. Keep secrets, real tenant evidence and cached data in ignored private storage.
10. T16/T17 remain cancelled. Use the existing qualified operating path; an unavailable authoring route does not commission a Windows/VM fallback.

Full integration commands (integration/release milestones or broad shared changes):
```
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_project.py
.venv/bin/python scripts/webfirst_contracts.py validate
```

Conductor plugin checkout: populated at the revision pinned by the `.agents/plugins/conductor` Git submodule. Repository skills in `.agents/skills/` link to its upstream skills. After cloning, run `git submodule update --init .agents/plugins/conductor` to populate them. Antigravity (`agy`) loads workspace skills from `.agents/skills/` and global skills from `~/.gemini/config/skills/`; legacy Codex skills were installed in `~/.codex/skills/`. See [AGY_HANDOVER.md](../AGY_HANDOVER.md). Installation does not assert that any project workflow or native Power BI gate has been executed.

## Local-first lane cadence

Use the [local-first recipe](../docs/LOCAL_FIRST_OUTCOMES.md). An explicitly
selected user task needs no repeated track confirmation. Update status with the
meaningful implementation commit, not a status-only commit. Resume from the
owner checkpoint and selected harness context, not a full historical reread.
Do not request a second automatic review after the required checks/review pass.
Keep implementation missing, implemented locally, native verification pending
and blocked distinct in task evidence. Record a changed hypothesis before
retrying a failed native operation; never automatically retry a write.
Project instructions take precedence over generic Conductor skill conventions.
