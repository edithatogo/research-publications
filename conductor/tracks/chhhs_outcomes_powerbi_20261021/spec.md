> Reconciled 29 October 2026 from the retained authoring checkout. Dated
> observations below are historical evidence, not refreshed native state.
> The current entire-roadmap direction reopens unfinished requirements;
> prior bounded acceptance remains valid only for its stated scope.
> Current ownership and authority: [CURRENT_STATE](../../../handoff/CURRENT_STATE.md).
> Cancelled Desktop/Windows routes stay excluded; no new sends or schedules.

# T18 — Specification: CHHHS outcomes and Power BI presentation

## Purpose and scope

Enable CHHHS research leaders, programme leads and analysts to evaluate research contribution transparently across publications, projects/activity, researchers, funding, partnerships and translation. Extend the existing RIMS semantic model and report; do not create a new Fabric project. This track plans the implementation and installs official source dependencies. It does not perform research assessment, assign impact judgements, publish reports or transfer native ownership.

## Evaluation framework

Use CHHHS Research Excellence Plan 2024–2029 priorities as a versioned local strategy dimension: Aboriginal and Torres Strait Islander health; tropical health and medicine; health service research; equity of access. Map measures to NHMRC's knowledge, health, economic and social impact domains and its inputs → activities → outputs → outcomes → impacts logic model. Align translation/capacity measures with Queensland Health Research Strategy 2032. These frameworks supply classifications and evaluation structure, not interchangeable institutional benchmarks or a mandated scoring algorithm. Sources and retrieval date are in [tooling](tooling.md).

The [outcome catalogue](outcomes.md) defines the minimum portfolio. Explicitly distinguish activity/output proxies from observed outcomes. No composite impact score, journal prestige proxy for research quality, inferred clinical benefit from citations, or researcher league table. Record contribution, evidence strength, observation lag, plausible alternative explanations and the population affected. A before/after change alone is not causal attribution. Targets, material differences and comparison populations require an authoritative source and effective dates; no invented threshold or traffic-light success.

## Semantic-layer contract

Reuse existing canonical identities, Publication, Date, Facility, PublicationFacility, ReportingWindow, SearchAudit and GrantsRegistry. Inspect the current owner's latest retained/native schema before extending local source: the checked-in model is not automatically the current deployed model. Preserve [Publications] and existing report/export count contracts. Add separate names for changed semantics until dependent consumers are migrated and reconciled.

Model separate fact grains for Publication (canonical work), Project/Study (canonical project), Award (award and currency), Application (application-round), Participation (person-project-role-effective period), TranslationEvent (verified change event) and OutcomeObservation (indicator, population, setting, period, comparator, evidence version). Do not flatten these facts into a multiplying join. Reuse existing project/award identities where available. Award totals, annual allocation and expenditure are separate facts; never sum multi-year award totals for each year.

Use conformed Date, Organisation/Facility, ResearchPriority, FrameworkDomain, EvidenceStatus and IndicatorDefinition dimensions. Version strategy/indicator mappings and organisation membership by effective dates. Use explicit bridges for publication-project, project-award and entity-priority mappings; document full versus fractional counting and non-additive category totals. Default to single-direction dimension-to-fact filtering; intentional bridge traversal belongs in documented measures, not implicit bidirectional ambiguity. Publication, award, application, outcome and snapshot dates have explicit date roles. Retain unknown dates and date precision rather than assigning artificial January dates.

IndicatorDefinition must contain stable metric ID/version, label, purpose, framework mapping, grain, inclusion/exclusion rules, numerator, denominator/eligibility, units, direction, period/date role, null/zero policy, aggregation, population, source lineage, evidence status, refresh expectation, owner and caveat. Store model descriptions/display folders and source-controlled DAX/TMDL alongside a human-readable dictionary. Row-level evidence remains in its authoritative retained source; the model computes reusable analytical meaning, not approval or identity resolution.

Every ratio exposes numerator, eligible denominator and unknown/incomplete count. DIVIDE returns BLANK for absent/zero denominator; missing evidence is not zero impact. Separate confirmed zero, missing, not applicable, not yet observable and suppressed. Time intelligence uses ReportingWindow and complete periods, Australia/Brisbane business boundaries, calendar and Australian financial-year views; historical metrics use appropriate as-of snapshots. Prior-period comparison requires equal coverage and a nonzero valid base. Rates recompute from totals, never average row percentages.

Reusable explicit measures, dynamic format strings and field parameters drive all plots; no visual-only business calculations or text-formatted numeric measures. Calculation groups are optional only where precedence and format behaviour are tested. Document dependencies, hidden technical keys, formats and reusable perspectives. RLS/OLS and small-number suppression must propagate to drillthrough, tooltips and exports; complementary disclosure is considered. No inference of First Nations identity from names, affiliations or subject keywords. Indigenous research topic, participant identity, leadership and community governance are distinct concepts with appropriate authorised evidence.

## Plot-first design contract

Output Enhanced PBIR in the existing PBIP, with modular source JSON themes and one validated merged theme per variant. Preserve stable page/visual identities when migrating. Use 1920×1080 canvas. Coordinates and visual sizes follow an 8px grid, with 16px gutters/padding. The 1080 height is divisible by 8; 16px spacing remains the default where it fits.

Theme owns colour/font literals: foreground, backgroundLight, dataColors, textClasses and supported visualStyles. Light canvas #F3F2F1, containers #FFFFFF; dark canvas #1B1A19, containers #252423. Request 8px corners, no harsh border, 16px internal spacing and subtle black shadow equivalent to #00000014 with 8px blur. Use supported theme defaults and schema-valid theme expressions; Power BI is not a CSS variable engine. Do not insert arbitrary token strings or eight-digit CSS colour values into PBIR. Where a property cannot inherit, record the precise capability gap and choose a supported themed alternative; do not silently hardcode hex/font sizes in visual.json.

Callouts 24–28pt maximum; labels/titles/subtitles 10–12pt Segoe UI Semibold, subject to readable rendering at normal viewing scale. Default trends request smooth curves, 2px stroke, 20% opacity muted area gradients where native schema/host supports them. Preserve actual observations and gaps; use straight segments or points for discrete counts, stepped processes or where smoothing would imply unobserved behaviour. Record such analytical exceptions explicitly.

Primary canvases contain plots and compact native controls, with no Tables, Matrices or multiline text boxes. Necessary titles, axes/units, data labels, selected period, coverage and accessible names remain: “zero-text” means no prose/table landing view, not unlabeled plots. Do not hide axes if units or comparison meaning would become unclear.

Prefer native cardVisual with reference labels, variance accents and sparkline where supported; otherwise pair a themed native line chart within the KPI area. Use advancedSlicerVisual or qualified native List Slicer as pills or a bookmark slide-out; preserve filter state and keyboard focus. Use native combo charts, small multiples, stacked bars and scatter plots. Avoid dual axes unless units/scales are explicit. Counts start at zero in bars; show unknown/suppressed states without presenting them as zero.

Granular text and styled matrices with bars/icons belong in report-page tooltips and drillthrough pages. Provide a keyboard-accessible drillthrough button/back path, not hover/right-click alone. Metric/dimension field parameters reduce duplicate plots; dynamic formats retain numeric types. Alt text, tab order, focus, contrast and non-colour cues are required. Verify light/dark variants and no-data, single-point, large-label, suppressed and partial-period states.

## Page plan

| Surface | Primary question and plots | Detail route |
| --- | --- | --- |
| Research overview | What is changing? Four restrained KPI areas (outputs, active projects, verified translation, evidence coverage); complete-period trend; priority small multiples | Indicator definition/evidence tooltip; selected portfolio drillthrough |
| Knowledge and reach | What research is produced and accessible? Publication trend; OA known/unknown stacked bars; collaboration comparison; optional field/year-normalised citation scatter only with qualified denominators | Bibliography, source reconciliation, attribution and citation-window details |
| Capacity and funding | What supports research? Distinct projects/leadership trend; awards by start period; applications and awards shown separately; role/facility small multiples | Project/award/participation details; no application success rate without full eligible applications |
| Translation and outcomes | What changed in practice and for whom? Verified adoption events by domain/time; outcome and comparator trends with native uncertainty display where supported | Evidence, methods, lag, contribution and limitations |
| Equity and partnerships | Who participates and benefits? Priority/setting small multiples; evidence-backed collaboration and co-design proportions with unknown segments | Population definitions, community governance and disaggregation caveats |
| Evidence quality | How much can be trusted? Freshness/coverage trend, missingness bars, identity/reconciliation exception plots | Source/batch/definition history and permitted records |

These are page roles: map onto the existing report before adding pages. Preserve existing CHHHS Publications, Monthly Publications, Source Reconciliation and bibliography/export access. Move detail to drillthrough only after parity and navigation verification; no loss of working outputs. Do not expose an empty clinical-impact panel as a scored failure; show unavailable coverage and its detail reason.

## Acceptance and exclusions

All core catalogue rows have source mappings or an explicit unavailable reason and acquisition dependency. No unsupported clinical/economic effect is reported. All live measures reconcile to authorised source keys and denominators; bridges cannot inflate totals. Native DAX, relationship/security behaviour, rendered PBIR, theme cascade and reader journeys must pass on the exact target. Local JSON validity alone is insufficient. Test unchanged replay, human-edit preservation, exact-ID rollback and affected export parity. Record source, model, theme, report and dependency revisions together.

No new permissions, capacity, external uploads, shared authentication changes, automatic MCP activation, publication or schedules are implied. Desktop Bridge, Desktop/Windows/VM assessment and desktop-dependent delivery are out of scope. Qualify requested capabilities through supported web/API routes and verify Power BI Service rendering across platforms; use a web alternative or defer unsupported features. Structured narrative outputs first evaluate SharePoint structured document generation against the same semantic definitions, with actual output/edit/retry parity before replacement. Business acceptance and observed long-term impact remain later operational work.

## Delivery slices and readiness

Deliver each slice end to end: source mapping → reusable semantic measures → plot → detail navigation → native verification → bounded handover. Do not wait for all facts, measures or pages to exist before verifying the first usable result. The first slice is K01 publications, K02 open-access status/coverage and the existing-source subset of D01 evidence quality on one overview page with drillthrough. Projects/funding follow; translation and measured outcomes follow their evidence dependencies. Each slice inherits the full preservation/security contract but only implements its needed objects.

Every indicator/subindicator has one readiness category: available now in local definitions (native verification still required), derivable from existing authorised data (mapping/calculation needed), or dependent on new evidence. Record readiness, blocking field/source, custodian, next operation and verification date in the outcome catalogue. Core means included in the evaluation portfolio, not necessarily ready to display. Missing clinical or economic evidence cannot block the publication slice or become a zero-valued performance score.

## Outcome-evidence intake contract

First inspect existing project, activity and evidence registers for a suitable authoritative home. Reuse their identities and editing/history workflows; add a supported structured list only if the required grain cannot be represented and existing authority covers it. Power BI consumes these records; it is not the evidence-entry or review system. No new per-publication approval queue is introduced.

Minimum TranslationEvent record: stable event ID, linked canonical project ID(s), event type, change description, affected setting/population, event date and precision, evidence reference and source version, contributor, recorded timestamp, verification status, verifier/date when verified, revision ID and superseded revision. Multiple project contributions use a bridge to one event, not duplicated events. Verification states are unverified, verified, disputed and withdrawn; do not automatically advance status from an upload or successful flow.

Minimum OutcomeObservation record: stable observation ID, indicator ID/version, linked event/project, population/cohort and setting, observation period, follow-up horizon, estimate and unit, numerator/denominator where relevant, comparator and baseline, uncertainty/method reference, evidence reference/version, contribution explanation and limitations, contributor, verification fields and revision history. Fields that do not apply must carry an explicit not-applicable reason; absent required evidence leaves the observation unavailable for verified-impact measures. Store only authorised aggregates in reporting projections; sensitive evidence retains existing access controls.

Technical intake acceptance: save/read back one representative authorised or clearly fictional record, preserve human edits and evidence links, reject invalid references, replay without duplication, supersede a revision without losing history and verify that withdrawn/disputed evidence drops out of verified measures while remaining traceable. This establishes workflow behaviour, not a real impact judgement. Configure the path without requiring staff to undertake substantive evaluation during system setup.

## Reproducibility and reuse

Each reported result identifies reporting cutoff, source snapshot/batch, indicator-definition version, model revision and report revision. “As originally reported” uses the preserved cutoff, source evidence and metric version; “restated” uses an explicitly selected newer definition/evidence snapshot. Never silently replace issued historical values. Detail views explain the restatement reason and affected periods. If original evidence cannot be reconstructed, mark that view unavailable rather than approximating it from current data.

Implement only the affected slice's necessary snapshot/version projection, using retained history. Version analytical definitions independently of report appearance. One governed explicit measure supplies each metric across pages and downstream consumers; field parameters select measures rather than copy formulas. Document consumer dependencies before changing names or semantics. Introduce a replacement measure/version, reconcile consumers, mark the old measure deprecated, and remove it only after those consumers migrate. Where an export cannot query the semantic model through a qualified route, retain its authoritative calculation and require demonstrable parity; do not invent a new runtime to force reuse.

## Page decision and interpretation contracts

| Page role / audience | Decision supported | Required comparison | Interpretation boundary |
| --- | --- | --- | --- |
| Overview / research leadership | Identify areas needing investigation or support | Complete periods with coverage and definition stability | Output change may reflect acquisition/attribution change; it does not establish impact |
| Knowledge / research leads and analysts | Identify dissemination and access gaps | OA eligible/assessed/unknown populations; like-for-like output cohorts | Citations/access are reach proxies, not quality or clinical benefit |
| Capacity/funding / programme leads | Understand evidenced capacity and funding distribution | Comparable project cohorts, known leadership and award-start periods | Opportunity counts are not awards; publication authors are not the workforce denominator |
| Translation/outcomes / evaluation leads | Investigate verified change and evidence gaps | Baseline/comparator, follow-up, uncertainty and evidence maturity | Association or adoption does not alone establish attributable patient benefit |
| Equity/partnerships / programme and community governance users | Identify representation and benefit questions for appropriate review | Relevant eligible populations and missingness, with approved disaggregation | Research topic does not establish identity, leadership or equitable benefit |
| Evidence quality / data stewards | Prioritise specific data repairs | Expected source cadence, completeness and unresolved identities over time | Missing evidence is a data limitation, not poor research performance |

Bind each implemented visual to a metric ID, comparison and interpretation boundary. Put explanatory detail on accessible drillthrough/tooltips while retaining concise units, period and coverage labels on the main canvas.

## Measurable visual acceptance

Keep the requested 1920×1080 authoring canvas. Test it in the actual Power BI reader viewport and a representative 1366×768 laptop display at normal browser zoom, recording browser, viewport, zoom and fit mode. No clipped titles/units, overlapping labels or inaccessible controls; a reader must identify value, unit, period, coverage and comparison without zooming. Adjust theme typography or density when 10–12pt authoring labels become unreadable after scaling. Screen-reader names and keyboard paths must reach each slicer, drillthrough and back control without hover/right-click dependence. Provide an accessible data/detail alternative while keeping the landing page graphical. Check text contrast at least 4.5:1 for normal text and 3:1 for large text, and meaningful non-text indicators at least 3:1; colour is never the only signal.

Use initial engineering budgets of ≤5 seconds to first usable overview and ≤2 seconds for a warm slicer/metric change on the representative reader host. These are proposed product targets, not Microsoft guarantees. Record five repeated observations per journey, median and maximum, separating first-load/cache conditions and recording dataset size/filter context. Compare against the existing report on the same host. A budget failure requires a specific repair or documented target revision based on measured constraints before acceptance; it must not be hidden behind a valid PBIR file. Recheck only changed or failed journeys. Native capability/readability/performance acceptance is separate from local preview.

Use smoothing only where it preserves the underlying time-series interpretation and show actual observation gaps. Hide axes only where direct labels retain units, scale and comparisons. Preserve native uncertainty indicators where supported and use accessible detail for exact intervals when needed. Validate these decisions on the first slice before applying the theme throughout the report.
