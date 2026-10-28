> Reconciled 29 October 2026 from the retained authoring checkout. Dated
> observations below are historical evidence, not refreshed native state.
> The current entire-roadmap direction reopens unfinished requirements;
> prior bounded acceptance remains valid only for its stated scope.
> Current ownership and authority: [CURRENT_STATE](../../../handoff/CURRENT_STATE.md).
> Cancelled Desktop/Windows routes stay excluded; no new sends or schedules.

# Core outcome and indicator catalogue

All entries below are proposed evaluation definitions, not claims of native availability or endorsed targets. Core means every domain is represented with an honest evidence state; absent operational data remains unavailable. “Existing” means local source observed on 21 October 2026, not refreshed tenant proof.

| ID / stage | Proposed indicator and calculation | Grain / source readiness | Framework / presentation |
| --- | --- | --- | --- |
| K01 output | Distinct included canonical publications by complete publication period; expose unknown month and uncertain affiliation separately | Publication; existing [Publications], date precision and source reconciliation | Knowledge; publication trend and priority small multiples |
| K02 output/reach | Known OA works / works with assessed OA status; also show assessed / all included works and unknown count. Preserve existing [Open Access Rate] denominator and introduce distinct names for the assessed-status measure | Publication/status observation; existing OA fields, eligibility semantics need qualification | Knowledge; 100% stacked status bars and trend |
| K03 reach proxy | Citation distribution within declared field/year/type and observation window; normalised metric only if comparator coverage/formula available | Work × snapshot; optional enrichment, not core impact proof | Knowledge; scatter/distribution, no author ranking |
| C01 activity | Distinct active projects at period end; separately count CHHHS-led projects / projects with known lead, with unknown lead count | Project dates/status and explicit lead evidence; project source mapping pending current owner | CHHHS capacity; trend and facility small multiples |
| C02 capacity | Distinct researchers with evidenced participation; protected research FTE and training completion only when workforce denominators/records available | Person-project-role and effective period; explicit identifiers, workforce extension unqualified | CHHHS capacity; role comparisons, never infer workforce from authorship |
| F01 input | Unique awarded amount by currency and award-start cohort; CHHHS share only when evidenced; expenditure separately | Award; reuse canonical Award where present; opportunities in GrantsRegistry are not awards | Economic inputs; award cohort bars |
| F02 process | Successful final applications / eligible final decided applications in the same round/cohort; withdrawn/pending shown separately | Application-round; denominator currently unqualified | Funding process; outcome stacked bars, BLANK when unavailable |
| P01 relationship | Distinct projects with external partnership / projects with assessed partnership; distinct partners separately | Project-organisation-role bridge, effective dates, known-status denominator | Social/capacity; partner/facility bars, category totals non-additive |
| T01 outcome | Distinct verified practice/policy adoption events; projects with ≥1 verified adoption / eligible completed projects with sufficient prespecified follow-up | TranslationEvent plus eligibility and evidence records; new authoritative structured inputs required | Health/social translation; event trends and domain bars |
| H01 impact | Approved patient/service indicator estimate by cohort/time with numerator, denominator, comparator, uncertainty and observation lag; difference only under compatible definitions | OutcomeObservation; authorised aggregate clinical/evaluation data absent from publication model | Health; comparator trend and native uncertainty display; no causal claim from simple pre/post |
| E01 impact | Verified incremental cost/resource change versus comparator with price year, perspective, currency and uncertainty; do not monetise publications or equate grants with savings | Evaluation observations; economic evidence/cost inputs not yet qualified | Economic; cost/resource trend or scatter with detail methods |
| S01 outcome | Projects with documented consumer/community co-design / projects assessed for co-design; separately verified community benefit | Project-evidence and outcome observation; not inferred from topic tags | Social; status proportions and benefit-domain bars |
| Q01 cross-cutting | Priority-aligned projects/publications; separately governed First Nations partnership/leadership and equity outcome differences with appropriate denominators | Versioned priority bridge; topic fields partially present, governance and population evidence pending | All four CHHHS priorities; small multiples with unknown categories |
| D01 evidence quality | Classified records / eligible records, source freshness by expected cadence, unresolved identity count, outcomes with evidence / recorded outcomes | Existing SearchAudit/ReportingWindow and retained provenance; outcome evidence extension pending | Trust/context; missingness and freshness plots |

## Operationalising evaluation

For each row lock the metric definition/version, accountable custodian, authorised source fields, expected update cadence, cohort/denominator, completeness rule, baseline period, comparator and follow-up horizon before implementation. Establish descriptive baselines from accepted data first. Targets and clinically meaningful differences remain unset until approved evidence supplies them. Monthly output/process reporting and quarterly outcome/evidence review are proposed cadences, not new scheduled automation. Use annual strategy mapping review and preserve prior definitions for reproducibility.

Translation follow-up must allow a justified lag rather than classify recently completed projects as failures. Report attrition, missing follow-up and evidence maturity. Retain project-to-outcome contribution links and separate jointly delivered impacts to avoid double counting across projects. Statistical estimates, adjustment models and uncertainty originate in a qualified evaluation method; semantic measures transparently aggregate/display them without inventing patient-level inference.

## Known semantic issues to resolve

Local Publication.tmdl has a measure named [Clinical Trials Count] that counts publications with a nonempty trial ID. Preserve its consumers while introducing an accurately named “Publications linked to trials” and a separately normalised distinct-trial measure only after parsing/identity qualification. [Funded Publications] describes funding metadata on works, not awarded grants or successful applications. [First Nations Health Publications] is a topic flag, not evidence of First Nations participation, leadership, benefit or community approval.

## Initial delivery-readiness register

Readiness below reflects inspected local definitions and planned dependencies, not current tenant certification. Confirm exact fields against the current owner's manifest before implementation. Split composite catalogue rows so an unavailable subindicator cannot block an available one.

| Indicator/subindicator | Initial category | Missing work / next operation | Delivery slice |
| --- | --- | --- | --- |
| K01 distinct publications | Available now in local definitions | Reconcile canonical keys, date precision and coverage on exact native model | 1 |
| K02 existing OA count/rate | Available now in local definitions | Verify current semantics; preserve existing denominator contract | 1 |
| K02 assessed-status rate/unknown coverage | Derivable from existing data, subject to status qualification | Define explicit known-status mapping; ambiguous fields remain unknown | 1 |
| D01 existing source freshness/reconciliation | Available now in local definitions | Map SearchAudit/ReportingWindow to bounded source coverage | 1 |
| C01 active/led projects | Derivable subject to existing project-field qualification | Confirm date/status/lead fields; missing lead evidence remains unknown | 2 |
| F01 award totals | Derivable subject to canonical Award qualification | Confirm award identity, currency and share; absence moves affected measure to new evidence | 2 |
| P01 partnership; C02 evidenced participation | Derivable only where explicit role/identity records exist | Qualify bridges/effective dates; do not infer workforce or project partnership from coauthorship | 2, otherwise deferred |
| C02 FTE/training; F02 application success | Dependent on new evidence | Workforce/training and complete application-cohort sources/custodians not established | Deferred |
| T01 adoption; H01 health; E01 economic; S01 co-design/benefit | Dependent on new evidence | Configure intake contract; connect authorised evaluation records and defined denominators | 3 |
| Q01 topic/priority mapping | Derivable for evidenced topic fields | Map versioned classifications with unknown bucket | 1 or 2 as fields qualify |
| Q01 leadership/equity benefit | Dependent on new evidence | Governed identity, community and population evidence; no topic-based inference | 3 |
| D01 outcome-evidence coverage | Dependent on new evidence | Uses outcome-intake records; separate from existing source-quality measures | 3 |
| K03 citation distribution/normalisation | Derivable only if retained snapshots and comparator fields qualify; otherwise new evidence | Confirm window, field/year/type comparator and coverage before admission | Optional after slice 1 |

At implementation, record per row the exact source/field mapping, named existing custodian (or unresolved), blocking input, verification date and native receipt in the current operational records. Unknown source availability must be resolved by a bounded read, not assumed from a local field name. Readiness is separate from evidence verification status and technical implementation status.

## Publications slice 1 readiness and reader contract — verified 23 October 2026

This readiness is specific to the current v48 model and isolated DEV reader, not
certification of every catalogue row or production availability. Native model
`[private identifier retained in original receipt]` is bound to report
`[private identifier retained in original receipt]` in workspace
`[private identifier retained in original receipt]`. Calculation and saved-reader receipts are
in `private/ops/2026-10-22-publications-slice1/`.

| Indicator | Confirmed category for this slice | Date role and consumer/page contract | Remaining boundary |
| --- | --- | --- | --- |
| K01 publication volume | Available and natively queried for the retained v48 snapshot | Publication date with source precision; complete-month trend uses Date.MonthStart. Reuse existing Publications, complete-month and unusable-month measures. Overview answers volume, trend and date coverage; detail retains canonical keys and source links. | Current/native key and period result is accepted; current-reader accessibility, all-page appearance and performance remain separate. |
| K02 OA status and coverage | Derivable from authorised retained OA observations; six saved measures and four independent cohorts reconcile | Publication/status-observation grain. A recognised, dated, noncontradictory status is assessed; absence/conflict is unknown. Overview pairs assessed-status rate with assessment coverage and counts. Six distinct `K02 ...` measures do not replace the existing `[Open Access Rate]` denominator or consumers. | Filtered Cairns evidence export reconciles to reader; complete unfiltered export and independent filtered DAX parity remain outstanding. |
| D01 existing source quality | Available for the existing SearchAudit/ReportingWindow subset | Reporting-window evaluation time and source provenance are not provider freshness. Displayed evidence distinguishes capture time, source batches/hashes and exclusive outcome cutoff. | Outcome-evidence coverage depends on future authorised outcome-intake records (slice 3); do not infer it from source freshness. |
| T01/H01/E01/S01 and D01 outcome evidence | Dependent on new evidence | No publication page substitutes activity for adoption, patient/service outcomes, economic effects, co-design or outcome-evidence coverage. | New authorised evidence and denominators are outside slice 1. |

### Page decision and measure-change contracts

The Publications overview is for comparing output volume, complete-period trend,
OA status/coverage and existing-source quality. It must keep unknown dates and OA
states visible and must not score clinical or economic impact. The Publication
version evidence page traces a selected cohort/work to canonical identity,
provenance, date precision, OA classification and source record. A selected
comparison datapoint carries its filter context to that page; Back returns to the
prior overview context. Source links are a data alternative to chart-only
interpretation.

Each result is keyed by exclusive reporting cutoff, retained source batches/input
hashes, metric version, model revision and report revision. Current/restated and
technical-baseline values are distinct. “As originally reported” remains
unavailable where no issued snapshot exists; the technical baseline must not be
renamed or presented as an issued original.

Existing measures remain stable while consumers exist. A changed definition gets
a new versioned measure name; first enumerate report, export and downstream
consumers, then reconcile native DAX, key sets and export results under each
consumer's filter context. Mark the old measure deprecated only after the
replacement is saved/read back and consumer parity passes; remove it only after
all consumers migrate. For this slice, six `K02` measures are additive and
`[Open Access Rate]` remains unchanged. No consumer migration or old-measure
removal is claimed.

## Strategy crosswalk and metric dictionary

This is a classification crosswalk, not a scorecard or target-setting decision.
Priority mappings are versioned when authoritative definitions and effective
dates are qualified. Unknown and unclassified remain visible; a topic label does
not establish identity, leadership, participation or benefit.

| Framework/domain | Current catalogue mapping | Stage/interpretation |
| --- | --- | --- |
| CHHHS Aboriginal and Torres Strait Islander health | Q01 topic mapping only where an evidenced classification exists; governed leadership, partnership and equity outcomes require authorised records | Priority alignment is not First Nations identity, leadership, community governance or benefit evidence. |
| CHHHS tropical health and medicine | Q01 priority mapping on qualified publication/project fields | Topic and geography are classifications, not outcome evidence. |
| CHHHS health service research | K01 output plus C01 activity when project source fields qualify; H01 remains unavailable without authorised outcome observations | Publications/projects are outputs and activity, not patient or service impact. |
| CHHHS equity of access | Q01 only with governed population and eligible-denominator evidence | Do not infer population identity or access outcomes from publication topics or author names. |
| NHMRC Knowledge | K01 output, K02 access/reach, optional K03 citation distribution | Output/reach measures are not quality or health benefit. |
| NHMRC Health | T01 verified adoption and H01 service/patient outcomes | Requires evidence, comparator, population, follow-up and method; absent values stay unavailable. |
| NHMRC Economic | F01 awarded inputs; E01 measured cost/resource outcomes | Grants are not savings; no publication monetisation. |
| NHMRC Social | P01 evidenced partnership, S01 co-design/benefit, governed Q01 outcomes | Coauthorship/topic labels do not prove partnership or community benefit. |
| NHMRC logic model / Queensland Health Research Strategy 2032 | F01 inputs; C01/C02 capacity/activity; K01/K02 outputs/reach; T01/P01/S01 outcomes; H01/E01 impacts | The strategy supplies organizing categories, not interchangeable measures, approved targets or causal inference. |

Metric dictionary rules for all rows above: keep the stable indicator ID and
definition version; state grain and authorised source; enumerate inclusion,
exclusion and eligibility; define numerator, denominator, units, period/date role,
null/zero/missing/suppressed handling, aggregation, refresh expectation, owner and
caveat before adding a measure. Ratios use numerator and eligible denominator
totals, expose unknown/incomplete counts, and return blank for absent/zero
denominators. For slice 1, K01 counts included canonical works and keeps source
date precision/unknown-month work separate; K02 has assessed/open/closed/unknown
states with distinct assessed-status and coverage denominators; D01 source freshness
is measured against expected source cadence and is separate from outcome-evidence
coverage. `T18-publications-1` identifies the slice's metric snapshot lineage; it
does not silently change legacy measure meaning. The full per-indicator formulas and
readiness remain in the catalogue and spec above.

## Outcome-evidence intake instructions — technical setup handoff

No outcome record or new intake store is authorised by these instructions. Before
configuring intake, identify the existing authoritative project/activity/evidence
register and its named custodian; verify its stable IDs, access rules, edit/history
behavior and permitted evidence references. Reuse it where it supports the
required grain. If it does not, record the exact missing behavior and wait for an
authorised supported structure decision; do not make Power BI the entry system.

For a TranslationEvent, retain a stable event ID, linked canonical project IDs,
event type/description, affected setting/population, date and precision, evidence
reference/source version, contributor and recorded time, verification state,
verifier/date when verified, revision ID and superseded revision. For an
OutcomeObservation, retain stable observation and indicator/version IDs, linked
event/project, population/cohort/setting, period and follow-up horizon, estimate
and unit, numerator/denominator where relevant, comparator/baseline, uncertainty
and method reference, evidence reference/version, contribution explanation and
limitations, contributor, verification fields and revision history. Record an
explicit not-applicable reason for fields that do not apply; missing required
evidence remains unavailable.

At technical qualification, use one authorised or clearly fictional record to
prove save/readback, valid canonical references, duplicate-safe replay, preserved
human edits and evidence links, revision supersession without loss, and disputed or
withdrawn evidence excluded from verified measures while its history remains
traceable. This proves workflow behavior only; it is not impact assessment or
approval. Keep sensitive evidence in its existing access-controlled source and
project only authorised aggregates into reporting.

## SharePoint structured document generation route check — 23 October 2026

Microsoft Learn describes SharePoint document generation as merging values from a
submitted form into a `.docx` template and creating a new document in a configured
library folder. Content managers need an assigned Copilot license and Edit access
to the library. The Power Automate trigger/actions are marked Preview in the
current documentation. The route is a candidate for repeated form-driven
narratives, but it is not a live data-bound renderer for this version-controlled
indicator catalogue. No exact SharePoint library, maintained template, assigned
Copilot entitlement or qualified form/action binding to the T18 source was
verified through an existing accepted target readback. Do not create a form,
change access/licensing, or move this source document. Keep these existing
version-controlled Markdown pages as the maintained documentation; reconsider
SharePoint generation for a selected recurring narrative after its actual template,
source, edit/history and output behavior qualify.

Reference: [Generate structured documents in a SharePoint document library —
Microsoft Learn](https://learn.microsoft.com/en-us/sharepoint/copilot-in-sharepoint-structured-document-generation).
