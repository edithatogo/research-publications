# Specification: complete the selected publication-source lane

## Scope

Complete the frozen 1,344-publication free-API enrichment pass using retained Europe PMC/OpenAlex and anonymous Semantic Scholar results. Reuse the existing SharePoint reporting folder, existing isolated Power BI model's four source tables and existing ingestion flow. CLI first; no new login, provider key or paid service. Preserve reviewed values, source-specific disagreements, observation dates and exact retained response evidence.

The existing quota checkpoint is accepted, but does not complete the 45 deferred lookups. The 19 verified no-matches, 12 missing/invalid identifiers and two identifier conflicts are legitimate separate dispositions, not invented matches. Review retained evidence for identifiers; do not guess or rewrite canonical values to obtain a match. A title stored in one DOI cell is recorded as invalid source data and preserved in the frozen baseline.

## Completion requirements

1. Recover only this lane's stale process locks after verifying their PIDs are absent; retain lock/preimage history and exact ownership.
2. Register granular executable Conductor tasks, distinguishing accepted work, active processes, provider deferral and unexecuted native work.
3. Resume the immutable cache with three-second pacing, at most one bounded request after a cooldown and conservative hourly backoff on repeated429; honour longer Retry-After. Never count429 as no-match or change endpoint/client to bypass a limit.
4. Every frozen publication has a disposition for each of the three selected sources; no Semantic Scholar lookup remains unattempted because of a recoverable interrupted operation. Missing identifiers and ambiguous matches remain visible with supporting decisions.
5. Preserve all returned data within the 20 selected parent fields and every nested returned field, raw response bytes/hash, source and observation date. Report requested-field absence separately from lookup coverage.
6. On changed collection, stage a new immutable generation; skip unchanged content-addressed pages. Check exact model/flow preimages before any write. Preserve source-specific field values and isolate uncertain candidates.
7. Verify exact SharePoint input bytes through native model readback, all publication/source pairs, field presence and all 18 export values for 1,344 canonical publications and the retained14-key monthly set.
8. Execute the bounded native ingestion flow, verify admission count and source-key uniqueness, and restore the original recurrence and Stopped state with readback. Never retry an uncertain mutation without inspecting its target.
9. Update the coverage/handoff and Conductor tasks to evidence-backed terminal states; commit only owned changes. Native completion requires an actual completed run and downstream readback.

## Exclusions and gates

No Scopus, Web of Science, Lens or Dimensions onboarding; no standalone Semantic Scholar draft activation; no new agreements, login, schedules, sharing, report layout or capacity changes. Broader grants, author and canonical-data repair lanes remain with their owners. Existing accepted source tests and required milestone receipts are reused; documentation-only changes receive link/structure checks, and changed source behavior receives only its focused test. If a genuine provider/authentication limit persists, keep dependent tasks incomplete and retain the exact resume point.
