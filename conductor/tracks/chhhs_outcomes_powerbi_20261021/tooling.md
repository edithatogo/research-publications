> Reconciled 29 October 2026 from the retained authoring checkout. Dated
> observations below are historical evidence, not refreshed native state.
> The current entire-roadmap direction reopens unfinished requirements;
> prior bounded acceptance remains valid only for its stated scope.
> Current ownership and authority: [CURRENT_STATE](../../../handoff/CURRENT_STATE.md).
> Cancelled Desktop/Windows routes stay excluded; no new sends or schedules.

# Pinned tools and source mapping

## Current route supplement — 22 October 2026

The suite CLI/API guide (retained authoring reference: `../../cli-implementation-routes-20261022.md`) now controls
current tool selection, installed versions, source pins and agent roles across all
open tracks. Official hosted Authoring MCP is a conditional model-authoring option;
its tenant/client/session/Write prerequisites are not yet qualified here. Local
modeling MCP source remains pinned reference; its documented macOS limitation
precludes treating installation as a working Mac runtime. Fabric IQ is optional
consumption, not authoring. No packages/plugins were installed or upgraded.

The earlier CLI preview 401 is resolved: this report and its bound model live in
different existing workspaces. Use the model workspace for preview and the report
workspace for definition management. CLI 0.5.0 headless/visible service previews
and the saved reader now pass for the monthly-axis repair (retained authoring reference: `../E04_fluent_visual_polish/monthly-axis-repair-20261022.md`).
No tool upgrade, workspace move or authentication change was needed.

Verified 21 October 2026. Official Microsoft repositories are installed as Git submodules; source availability is not runtime activation, host compatibility or tenant access. No external install scripts, MCP registration, package executables, authentication or tenant calls were run.

| Requested resource | Repository implementation / disposition |
| --- | --- |
| [Report skill](https://learn.microsoft.com/en-us/power-bi/developer/agentic/power-bi-report-skill-overview) | `.agents/plugins/skills-for-fabric`, `skills/powerbi-report-cli`; discoverable via `.agents/skills/powerbi-report-cli` symlink |
| [Report design skill](https://learn.microsoft.com/en-us/power-bi/developer/agentic/power-bi-report-design-skill-overview) | Same pinned collection; unified report skill contains design references. Do not install a duplicate obsolete companion solely because an older overview names it separately |
| [Desktop Bridge](https://learn.microsoft.com/en-us/power-bi/developer/agentic/power-bi-desktop-bridge-overview) | Tool/API, not standalone skill. Pinned report skill includes `references/authoring/powerbi-desktop.md`. Desktop Bridge assessment/runtime is cancelled and out of scope by user direction, 21 October 2026. Bundled documentation remains upstream reference only; no install or qualification task remains |
| [MCP overview](https://learn.microsoft.com/en-us/power-bi/developer/mcp/mcp-servers-overview) | `.agents/plugins/powerbi-modeling-mcp` pins official source/documentation. Authoring server runtime remains inactive; hosted endpoints cannot be Git submodules. Consumption/Fabric IQ is not needed for this planning track |
| [Agentic documentation hub](https://learn.microsoft.com/en-us/power-bi/developer/agentic/) | Documentation index, not a package. Official collection also supplies `semantic-model-authoring`, discoverable through `.agents/skills/semantic-model-authoring` |

Pins:

- `https://github.com/microsoft/skills-for-fabric.git` — `bc42aaf734771bf752c1d7082dd91e5a6ca72b9f`
- `https://github.com/microsoft/powerbi-modeling-mcp.git` — `2b25defb975169ffb573195cc0ff8006835b8a6e`

Restore with `git submodule update --init .agents/plugins/skills-for-fabric .agents/plugins/powerbi-modeling-mcp`. These are pinned gitlinks, not moving branch dependencies. Update intentionally: review upstream changes, resolve exact candidate commit, qualify affected behaviour, retain old SHA for rollback, then update the gitlink. Do not auto-update or recursively initialise unrelated tooling. On hosts that do not support symlink discovery, invoke the canonical submodule SKILL.md explicitly. Reload the agent catalogue when convenient; this planning deliverable does not require a restart.

Repository constraints override upstream generic workspace enumeration, telemetry, authentication, publishing and runtime setup recipes. Use existing exact target manifests, assigned native owner and qualified route. A source submodule is not a bundled executable, enabled plugin or deployment receipt. The two new skills were linked for future use, not invoked to perform report/model authoring in this task.

## Standards and evidence sources

- [CHHHS Research Excellence Plan](https://www.cairns-hinterland.health.qld.gov.au/research/research-excellence-plan): four local priority domains used as strategy mappings, not quantitative targets.
- [CHHHS plan 2024–2029](https://www.cairns-hinterland.health.qld.gov.au/_media/research/chhhs-research-excellence-plan-2024-2029.pdf): capacity, partnership, community involvement and translation inform the proposed portfolio.
- [NHMRC Research Impact Position Statement](https://www.nhmrc.gov.au/research-policy/research-translation-and-impact/research-impact): four impact domains and logic-model stages. The catalogue is a proposed local operationalisation, not an NHMRC-certified scoring instrument.
- [Queensland Health Research Strategy 2032](https://www.health.qld.gov.au/system-governance/strategic-direction/plans/research-strategy-2032): state alignment for research capacity and translation; lock applicable strategy version during implementation.
- [Queensland Health Performance and Accountability Framework](https://www.health.qld.gov.au/system-governance/performance/queensland-health-performance-and-accountability-framework): crosswalk only if clinical/service outcome data is later authorised; no claim that RIMS implements statutory performance reporting.

Documentation was checked live on 21 October 2026. Official pages can describe different release generations: resolve exact pinned skill, CLI, PBIR/theme schema and target host before implementation. Confirm requested Fluent-style properties against native schemas/rendering; do not treat CSS terminology as a supported Power BI property contract.

## Local verification

Submodule commit resolution, clean upstream worktrees, skill-link targets and Conductor structure are checked. Native DAX execution through qualified service APIs, relevant MCP operation, Power BI Service rendering and operational outcome evaluation remain unverified implementation tasks. Desktop Bridge is excluded, not a pending qualification task.
