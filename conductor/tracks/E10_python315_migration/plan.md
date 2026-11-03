## Delivered-work reconciliation — 3 November 2026

PR116/117/119/120 are merged. Final dependency-integration main cc3f55f1 passed source validation, Python3.15.1 locked-dependency and security checks; the four updated pins match the qualified lockfile. E10.6 shared helper handover and E10.7 full-scope audit remain open. Reuse accepted candidate qualification and avoid another dependency rebuild.

See [the cross-track mapping](../../backlog-reconciliation-20261103.md) for remaining exits and CLI prerequisites. Historical requirements below remain evidence at their original scope.

# E10 numbered implementation plan

> Status reconciliation, 24 October 2026: consult
> [current missing outcomes](../../../docs/CURRENT_MISSING_OUTCOMES.md) before
> executing dated next steps or unchecked tasks below. Accepted scoped evidence
> supersedes only mapped outcomes; preserve historical detail and current owners.


Status: in progress. Source/CI qualification is accepted; host handover and final
full-scope audit remain. Reuse accepted evidence, no status-only commits or
routine second review. Each step has an explicit implementation/evidence boundary.

- [x] E10.1 Inventory canonical Python/Node manifests, hash locks and active CI/tool
  targets; verify root `.venv/bin/python` actually3.15.1. No maintained root
  container, pyproject/Pipfile or Node package graph found. Native runtime stays
  Microsoft. Source inventory: PR9 and audit/dependencies.
- [x] E10.2 Resolve newest compatible stable/development direct/transitive local
  dependencies in isolation;40 packages. pip26.2.2/certifi2026.10.19/uv0.13.5,
  lxml7.0.0b1/zizmor1.32.0rc1 retained. Supported PyYAML6.0.3 source build fixed
  missing cp315 Linux wheel without a3.14 fallback. Exact hashes recorded.
- [x] E10.3 Promote source constraints/locks, `.python-version`, active source/tool/
  security CI and current instructions to3.15.1; candidate execution restricted
  to3.15.x. Old compatibility runner removed. RIMS-owned security job retains
  gitleaks/actionlint/pin/security checks. PR9, canonical commit36bbb3f5.
- [x] E10.4 Qualify significant behavior and security:619 tests/12 skips,460
  contracts, full harness, consistency/audit/lint, DOCX/XLSX roundtrips;5 exact-head
  hosted checks pass and post-merge main quality/security/dependency graph pass.
  Qualified/main tree615a10ae679fc7e590548881debb8f619f02f184.
- [x] E10.5 Safely establish working-checkout3.15.1/40 packages after selected
  runtime process inventory; local agent launcher verifies exact interpreter and
  E01 next-run prompt selects it. Existing operations/host environments untouched.
- [ ] E10.6 Finish attached helper-host accounting and terminal handover. Existing
  external Fabric MCP host environment records3.14.6. Inspect actual configured
  launcher/ownership and supported latest package qualification; prepare isolated
  repo-local3.15.1 replacement for a terminal host boundary, preserving native
  bindings/authentication and other consumers. Do not restart the active host.
  External EndNote3.13.13 host is separately owned outside RIMS; exclude with
  evidence, do not alter it. Any genuine unsupported dependency stays explicit.
  - [x] 24October: isolated repo-local3.15.1 MCP0.8.7 candidate with74 locked
    packages, latest compatible FastMCP3.4.11/MCP1.30.0/Azure Identity1.26.0.
    Actual in-memory and stdio initialize/tools-list pass;58 names match attached
    catalogue and input/output schemas agree between transports. No native tool,
    network or auth subprocess call occurred. Dependency check, explicit launcher
    version, syntax and two fail-closed environment selectors pass.
  - [x] Add exact hash lock, repo-local version-checking launcher and staged
    reversible configuration preimage/diff. Shared profile remains unchanged.
  - [ ] Activate only at a proved affected host/native-operation terminal boundary.
    Multiple RIMS and other repository processes share the external launcher;
    archival of G02 does not prove native termination or release global ownership.
    No supported scoped terminal handover/idleness evidence is available. The
    no-contact direction prevents requesting a release or contacting G02. Preserve
    current processes, bindings and Crossref; do not force restart/profile changes.
- [ ] E10.7 Audit all numbered specification requirements against current state,
  complete any remaining in-scope uses/handover and verify current-head/main
  integration of necessary source changes. Do not promote optional host claims
  or infer full qualification from PR9 alone.
  - 24October audit correction: quality/canary jobs still used PATH Python and
    the artifact job installed into the runner system environment. The prepared
    correction creates fresh repository environments from setup-python's exact
    absolute output, verifies actual version/prefix, invokes those interpreters
    explicitly and retains setup-failure receipts without a fallback interpreter.
    Candidate tool behavior runs inside the candidate dependency environment.
    Exact-head and main CI must pass before accepting this correction; the shared
    Fabric host handover remains separate and incomplete.
- [x] E10.8 Inspect durable goal state: unfinished E01 goal remains blocked,
  preserved unchanged. Separate E10 CreateGoal not attempted because no goal
  slot is available; no retry or false rejection/success claim. Registration
  receipt records requested objective and actual goal status. This completed
  inspection is not a claim that E10 has an armed goal.

## Next exact action

Candidate qualification is complete locally. At an actual supported terminal
boundary, reconcile all affected native/MCP handles and exact profile ownership,
then apply only the staged launcher selection for the intended host/session.
Until then retain the active3.14.6 host and report this exact handover boundary;
do not repeat dependency resolution or passing tenant-free checks. Guide:
`docs/FABRIC_MCP_RUNTIME.md`; public evidence:
`audit/dependencies/fabric-mcp-python315-20261024.json`.

## Completion receipts

24October shared-security caller update: both workflow and policy revision use
qualified CareOps main merge5cf006bce6c37c0c15db5d35055e302701a500ad. The prior
PR-only revision is not adopted. Existing RIMS artifact checks are preserved;
actual current-head shared-security execution is required before source promotion.
This caller maintenance does not activate or complete the pending helper-host
handover above, change native operations, or contact another owner.

- Canonical qualification: `audit/dependencies/python315-20261023.json`.
- Current working runtime/main proof: `private/ops/2026-10-23-runtime-upgrade/completion.json`.
- Registration/goal state: `private/ops/2026-10-23-runtime-upgrade/track-registration.json`.
- No separate goal is armed; E01 remains unfinished and must not be overwritten.
