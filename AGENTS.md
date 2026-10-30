# Agent instructions

Project-owned code uses Apache-2.0; retain the complete LICENSE and NOTICE in
source packages. Preserve upstream terms and attribution. The code licence grants
no redistribution rights over external documents, datasets or private evidence.

## Serial integration — 29 October 2026

Read the current integration assignment at the top of `handoff/CURRENT_STATE.md`
and the [worktree reconciliation](docs/WORKTREE_RECONCILIATION_20261029.md).
Inspect the actual checkout, ownership and native operations before writing.
Use one source writer per checkout and one integrator for main, shared handoffs,
contracts, dependencies, runtimes, hooks and submodule pins. Supporting work stays
in separate worktrees with scoped commits and one terminal handoff. Preserve
prior assignments as history; chat archival does not stop a scheduled service
or transfer a native object, authentication renewal or one-send journal.

Keep ordinary Git hooks enabled. Never remove another process's lock, reset or
clean a shared checkout, replace an active environment, or use custom index/ref
scripts to bypass competing writers. Prefer managed worktrees; after an exact
managed-tool failure caused by a non-Git project parent, a standard Git worktree
at the verified repository is the recorded CLI fallback. Do not merge the
unrelated private-authoring history into the canonical source history.

## Runtime and dependency compatibility — 24 October 2026

The user's 29 October direction supersedes the earlier compatibility exception:
every active repository Python use must use Python 3.15 at the newest qualified
patch release, currently 3.15.1. Select a repo-local interpreter and verify its
actual version. Align development, tests, build, CI, automation and helpers;
report unsupported dependencies as blockers rather than downgrading Python.
Historical evidence and deliberate version-handling fixtures remain unchanged.

Select the repo-local interpreter explicitly for repository checks. Preserve
working latest-version environments and in-flight operations; do not downgrade
or rebuild unnecessarily. Follow setup instructions and exact hash locks for the
selected environment. Installation or a manifest alone is not qualification.
Keep security, functionality, ownership and private-evidence gates. No emails or
external messages are authorised by a runtime change. Historical evidence and
synthetic version-handling fixtures remain unchanged.

## Current route precedence — 13 October 2026

Follow the [shared-data delivery contract](docs/PLATFORM_COMPLETION_PLAN.md#shared-data-delivery-contract--13-october-2026): CLI/API-first on qualified exact targets, existing archive bootstrap, complete raw payload/schema retention before vertical filtering, and one writer per file/object. Historical browser-first/no-CLI statements and dated completion claims do not override this direction. Preserve current source scope, permissions, isolation, rollback and explicit activation/delivery gates. The publications chat retains its current objects and checkpoint; shared-data work requires disjoint scope or explicit handoff.


Solo-repository harness: after the required entry documents, read `handoff/CURRENT_STATE.md`. Run `.venv/bin/python scripts/agent_harness.py context --task grants` (or publications/organisation/platform) for targeted context. See `docs/SOLO_AGENT_WORKFLOW.md`. Use existing Conductor plans; keep one short checkpoint and avoid extra approval or project-management layers. `.venv/bin/python scripts/agent_harness.py check --task all` runs the three required checks with the active interpreter and preserves failures. Local success never proves tenant acceptance.

Read conductor/index.md and handoff/POWERBI_PLUGIN_START_HERE.md first. Use the existing Git history and the user's existing Power BI report, not a new Fabric project.

Primary route: supported CLI/API operations qualified on the exact target, with BrowserOS neo fallback under shared-UI ownership. Reuse established discovery/isolation evidence unless inputs changed. Data querying is not authoring; T16/T17 remain conditional.

No shared/original model writes without an approved isolation/rollback path. No blind rename of old fields. Preserve source/date uncertainty. Full canonical bibliography and monthly exports must reconcile to model key sets. Synthetic fixtures are never live data.

Validation cadence: use changed-behavior tests and affected structural checks. Documentation-only changes need structural/link checks, not new mirror tests. Run `.venv/bin/python scripts/agent_harness.py check --task all` at integration/release milestones or broad shared-contract changes. Native M/DAX, report rendering, live refresh and scheduled delivery remain separate gates.

Keep actual tenant IDs, screenshots, auth tokens, raw API snapshots and caches in ignored private paths. Do not copy old workforce row data to this repository or an unapproved third-party plugin. Do not change sharing, publish, enable schedules, purchase capacity or change an existing VM without the specific approval gate.

## Concurrent execution checkpoints

Use [bounded implementation and lane resume](docs/EXECUTION_EFFICIENCY.md) for
concurrent chats. Each owner keeps its own ignored compact checkpoint and explicit
finish line; `scripts/lane_resume.py --lane <lane>` reads it without executing
prose. Preserve in-flight operations. Reuse unchanged verification, distinguish
deployment/runtime/activation/scheduled proof, and record a changed hypothesis
before retrying a failed native operation. Consolidate qualified deployment helpers
at terminal handover rather than replacing an active owner's route.

## Power Platform authoring assurance — 30 October 2026

Identify authoritative source and its generator, inspect the relevant schema and
accepted connector example, edit parsed JSON, run focused validation, review the
semantic delta, then pack affected solution releases. Preserve tested generators;
structural changes use parsed objects regardless of line count. Never replace a
working flow with guessed connector fields. Preserve unknown properties.

Use the installed qualified PAC/CLI route and already-exposed Power Platform MCP
tools. Tool visibility and local help do not qualify native permissions. Retain
workload identity pins, guarded M365 entry points and authentication ownership.
Use native UI only for a specific missing capability, rendering or human login.

The offline power-automate-profile.json is a project-owned structural profile,
with the source WDL URL/hash and explicit Power Automate extension limits. It is
not a full expression compiler. Reports distinguish pass/fail/unverified/
not_applicable and never imply native deployment readiness. Preserve exact
connection references; parameter names alone do not prove environment variables.

Keep native inputs, component maps and pack outputs private. Public maps use
sanitized sources only. Read relevant dependency XML; ignore-file conventions are
search hints, not confidentiality controls. Sync an active Canvas authoring
session before local edits and use its supported current source route, not the
retired experimental Canvas unpack format.

Do not add blanket pack/check runs to every edit. Pack affected solution releases
and compare unpacked source; cloud Solution Checker is a separate authorized
operation. Keep output/replay/recovery evidence separate from all local checks.

## Local-first outcomes increment — 30 October 2026

Follow [the local-first recipe](docs/LOCAL_FIRST_OUTCOMES.md) and the existing
outcomes track. Prepare and compare locally before native writes. Automation is
CLI-only, standard-feature-only, without Copilot; unsupported UI steps receive a
manual handoff. Use focused harness selections during edits and existing full
gates at integration. Reuse accepted native evidence unless relevant inputs
change. This lane does not acquire another lane's authentication or native scope.
