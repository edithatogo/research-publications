# Track register

## Current execution authority — 29 October 2026

The approved entire-roadmap implementation and guarded isolated DEV/no-send
scope in [CURRENT_STATE](../handoff/CURRENT_STATE.md) supersede historical
priority/deferral paragraphs. Three isolated lanes deliver scoped packets to one
integrator. Blocked requirements remain open. T16/T17 are cancelled and excluded,
despite their historical conditional labels below. Accepted receipts are reused.

Canonical source milestones PR57, PR58 and PR59 are merged with main quality and
security checks passing. These do not close native/operational track exits.
Current evidence and residual requirements are consolidated in the
[publication cycle](../docs/PUBLICATION_CYCLE_CLOSURE_20261029.md),
[complete PubMed candidate](../docs/PUBMED_OFFLINE_TYPED_CANDIDATE_20261029.md),
[grants source disposition](../docs/G08_SOURCE_RECONCILIATION_20261029.md),
[relationship compatibility](../docs/G06_RELATIONSHIP_GUARDS_20261029.md),
[classification closure](../docs/G07_CLASSIFICATION_SOURCE_20261029.md), and
[E04/T18 reader handoff](../docs/E04_T18_SOURCE_PACKET_20261029.md).
S02 clean-source extraction passes at56ac7d92 with NativeAcceptance=false;
E10 shared-host promotion, current native recovery/rendering and the post-1November
natural monthly observation remain open. No accepted historical route is reopened
merely to reproduce unchanged evidence.

## Publication stabilisation before grants implementation

Execution order and boundaries: [detailed handoff](PUBLICATION_STABILISATION.md). Existing T11, T14, T15, E01 and E07 own live acceptance; their execution runbooks refine the existing plans.

- [~] [S02_release_versioning: reproducible versions and recovery](tracks/S02_release_versioning/plan.md) — source versioning and isolated native version/batch display are verified; native rollback/version-history remains gated.

## Grants extension of CHHHS RIMS

- [~] [G02_grants_sources: Verified federal and Queensland sources](tracks/G02_grants_sources/plan.md) — catalogue implemented; endpoint/feed verification remains open.
- [~] [G04_grants_ingestion: Grant source ingestion](tracks/G04_grants_ingestion/plan.md) — local adapters and fail-closed batch handling implemented; live source/list/flow acceptance remains open.
- [~] [G05_grants_universities: University and specialist coverage](tracks/G05_grants_universities/plan.md) — JCU/UQ/QUT/Griffith source/access catalogue implemented; portal/feed verification remains open.
- [~] [G07_grants_operations: Grant operational acceptance](tracks/G07_grants_operations/plan.md) — local fail-closed evaluator and controlled DEV create/update replay implemented; current-user manual monitoring/reconciliation remains open; cross-user delivery is a future extension.
- [~] [G08_rims_grants_experience: RIMS grant pages, dates and subscriptions](tracks/G08_rims_grants_experience/plan.md) — local policy and current-user native pages/list/flow/model bindings are evidenced; refresh/reconciliation and delivery remain open; shared delivery is a future extension.

## Current web-first implementation

- [~] [T11_sources_and_reconciliation: Repair and prove PubMed plus DORA ingestion](tracks/T11_sources_and_reconciliation/plan.md) — current-user native list/model/flow readback is evidenced; retained-history, refresh, recurrence, delivery and production acceptance remain open (2026-09-22 audit).
- [~] [T14_complete_exports_monthly: Export every citation and stage the monthly workflow](tracks/T14_complete_exports_monthly/plan.md) — implementation exists; native/operational acceptance remains open (2026-09-20 audit).
- [~] [T15_web_acceptance_release: Verify the live web implementation and hand over](tracks/T15_web_acceptance_release/plan.md) — implementation exists; native/operational acceptance remains open (2026-09-20 audit).
- [ ] [T16_utm_windows_fallback: Finish the existing UTM Windows VM only if needed](tracks/T16_utm_windows_fallback/plan.md) — gated (conditional fallback)
- [ ] [T17_desktop_fallback_acceptance: Author and save a native PBIX in the Windows VM](tracks/T17_desktop_fallback_acceptance/plan.md) — gated (conditional fallback)

## Historical local implementation
- [x] [T01 legacy audit](tracks/T01_legacy_audit/plan.md)
- [x] [T02 source model](tracks/T02_research_model/plan.md)
- [x] [T03 initial report definitions](tracks/T03_research_report/plan.md) — later superseded by three-page scope.
- [x] [T04 local regression/handover](tracks/T04_regression_handover/plan.md)
- [x] [T06 two-source definitions](tracks/T06_browser_two_source/plan.md) — local source only; runtime defects remain.

## Superseded routes, not completed deployments
[T05 native acceptance](tracks/T05_native_acceptance/plan.md) is consolidated into conditional T17.
[T07 Fabric Git acceptance](tracks/T07_fabric_live_acceptance/plan.md) is retired.

## Multi-source enrichment extension
- [x] [Multi-source enrichment and deduplication](../docs/FUTURE_SOURCE_ENRICHMENT.md) — completed (OpenAlex, Crossref, Dimensions, Scopus, Web of Science, ARDC RLA integrated into registry, enrichment pipeline, and seed datasets).
- [x] [Keyless & Token-Free Enrichment Plan](../docs/KEYLESS_ENRICHMENT_PLAN.md) — active policy (strict zero-key/zero-token rule; only OpenAlex polite-pool, Crossref polite-pool, PubMed E-Utilities, and internal deterministic governance classifiers; proprietary paywalled APIs excluded).

## Platform completion roadmap (separation of concerns)
- [x] [Phase 1: Central Research Data Persistence & Review (SharePoint List)](../docs/PLATFORM_COMPLETION_PLAN.md#phase-1-sharepoint-publication-registry-highest-value) — **Highest Value** (historical synchronization evidence; live readback and current reconciliation remain gated)
- [x] [Phase 2: Automated Cloud Ingestion & Daily Enrichment (Power Automate)](../docs/PLATFORM_COMPLETION_PLAN.md#phase-2-power-automate-daily-ingestion--enrichment-high-value) — **High Value** (flow package and target identity prepared; end-to-end replay, concurrency, and unattended acceptance remain gated)
- [~] [Phase 3: Executive Monthly Word Reporting (Automation & On-Demand)](../docs/PLATFORM_COMPLETION_PLAN.md#phase-3-executive-monthly-word-reporting-medium-high-value) — **Medium-High Value** (Queensland Health branded monthly executive digests, KPI cards, hospital breakdowns) — local artifacts complete; current native cycle, reconciliation and delivery remain open
- [~] [Phase 4: Research Semantic Model & Visual Dashboards (Power BI)](../docs/PLATFORM_COMPLETION_PLAN.md#phase-4-power-bi-semantic-model--research-dashboards-medium-value) — **Medium Value** (TMDL model, DAX reconciliation query check, research visual suite) — local model/report definitions exist; current deployed Clinical Analytics bindings remain open

## Canonical evolution tracks
- [~] [E01_flow_automation: Power Automate Ingestion Canonicalization and Recurrence Scheduling](tracks/E01_flow_automation/plan.md) — implementation exists; native/operational acceptance remains open (2026-09-20 audit).
- [~] [E04_fluent_visual_polish: Microsoft Fluent 2 Visual Polishing and IBCS Standards](tracks/E04_fluent_visual_polish/plan.md) — local geometry/contrast tests pass; six-page native inventory is evidenced, but nine Clinical Analytics field-binding errors and visual acceptance remain open
- [~] [E07_publication_platform_acceptance: Publication platform hardening and live evidence](tracks/E07_publication_platform_acceptance/plan.md) — local acceptance contract added; tenant readback and end-to-end replay remain gated

- [~] [E10_python315_migration: Python3.15 migration and qualification](tracks/E10_python315_migration/index.md) — PR9/main implementation accepted; safe attached-helper handover and final full-scope audit pending. Existing unfinished E01 goal preserved; no separate E10 goal armed.
