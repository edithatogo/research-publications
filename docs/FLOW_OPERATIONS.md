# Flow operations — 24 October 2026

**15 Started; 26 Stopped across 41 observed RIMS flows.** Of the Started flows,
13 have recurrence triggers and two are manual: source archive commit and funding
calendar upsert. Started is enabled configuration, not evidence of a running or
successful execution. No runtime was started to build this view.

The retained Crossref execution was last reported Running at 04:33 UTC / 14:33
Brisbane; this view refreshed configuration state, not every run history. Monthly
register export and delivery monitoring are Started with saved November start
dates. The main publication writer, ClinicalTrials collector, grants importer and
NIH qualifier are Stopped. Do not describe all configured flows as operating
automatically.

[Machine-readable view](../config/flow-operations-snapshot.json) contains all
fields and source keys. [Missing outcomes](CURRENT_MISSING_OUTCOMES.md) contains
the implementation backlog. This page is an observation, not a live dashboard.

## Current schedule adjustment — 31 October 2026

The user authorised changing the two existing recurrences from 1 November:
monthly register/canonical exporter **07:00 on day 1** and independent delivery
monitor **07:45 daily**, Australia/Brisbane. The existing one-time app verification
moves to **07:50 on 1 November**. Final native readback is accepted in the
[current handoff](../handoff/CURRENT_STATE.md). The 24 October snapshot and old
times below are preserved as history; they are not the current schedule guide.
Natural scheduled delivery remains unproved until the eligible occurrence.

## Coverage and interpretation

Configuration observed at **2026-10-24T05:04:57.790Z** by one read-only FlowAgent
CHHHS name-filtered top50 listing, returning49 rows;41 are RIMS and8 Clinical Hub
rows are excluded. No tenant-wide or canonical-solution completeness claim. The
41 include standalone collectors, qualifiers and tests; they are not a new
canonical solution count (the retained export contains35 workflows). Exact native
IDs/raw listing are private. The public snapshot retains only names and summaries.

State/trigger columns come from that fresh listing. Cadences come from earlier
saved definitions/export (source keys S/X); they were not reread for every flow.
All schedule times below are **Australia/Brisbane**. No inferred next-run date.
“Last accepted runtime” means the latest selected accepted evidence available to
this reconciliation, not necessarily the latest execution in service history.

Owner is the **implementation lane**, not a claim about the native security
principal. Historical/unresolved labels explicitly require handover before edits.
Current owners retain their objects. A runtime evidence gap is not proof of a
failed flow and does not commission a new test.

## Collectors and archive operations

| Flow / purpose | Lane | State | Saved schedule | Last accepted runtime | Remaining blocker / limit |
| --- | --- | --- | --- | --- | --- |
| OpenCitations incoming citation links — Archive incoming citation relationships | E01 | Stopped | Manual; disabled | 24 Oct: 48 responses/344 distinct citation identities verified [O] | Selected tranche complete; canonical admission separate |
| Data spaces / Archived source assertions refresh — Admit archived source assertions | E01 | Stopped | Manual; disabled | 24 Oct: 48 OpenCitations assertions; prior 46 rows preserved [O] | Selected import complete; no automatic admission |
| OpenCitations DOI metadata enrichment — Archive selected DOI metadata | E01 | Stopped | Manual; disabled | 24 Oct: 48 responses; 44 single/3 no-hit/1 multiple match [O] | Multiple match unadjudicated; no automatic rerun |
| OpenCitations DOI count enrichment — Archive citation counts for selected DOI set | E01 | Stopped | Manual; disabled | 24 Oct: 48 DOI identities; 45 new responses and 3 retained [O] | Canonical solution admission separate; tranche complete |
| Crossref isolated batch qualification v1 — Bounded Crossref acquisition qualifier | E01 | Stopped | Manual; disabled | 23 Oct: selected query/13 rows and exact archive proof accepted [C] | Completed qualifier; do not rerun; not permanent worker proof |
| Data spaces / DataCite related output collection — DataCite related outputs | E01 | Started | Thursday 05:00 | 23 Oct: completed-query prefix reuse and second query accepted [C] | Nonempty page-ETag edge and sustained operation separate |
| Data spaces / ClinicalTrials.gov source collection — Australian trial archive | E01 | Stopped | Wednesday 04:00 saved; disabled | 23 Oct: pinned-prefix continuation and matching complete key sets accepted [C] | Stopped; no unattended claim |
| Data spaces / Crossref notice collection — Crossref notice/archive collection | E01 | Started | Daily 03:30 | Retained run Running at 04:33 UTC 24 Oct; 267 markers/364 pages (metadata only) [C] | Terminal reconciliation; optimised continuation gated |
| Data spaces / PubMed source collection — PubMed publications | E01 | Started | Daily 01:30 | 23 Oct: fresh-restart generation accepted; 13 XML batches [C] | Cross-run page resume/shared freshness separate |
| Data spaces / DoRA publication source collection — DoRA publication archive | E01 | Started | Daily 04:30 | Accepted maintained collection and own-DOI checkpoint [I] | Recent scheduled success not selected |
| Data spaces / ARDC identifier collection — ARDC public metadata archive | E01 | Started | Monday 04:00 | Accepted full baseline and incremental catch-up [I] | Natural weekly operation not established here |
| Data spaces / Source archive commit — Commit staged source archives | Publications/archive | Started | Manual; no recurrence | Historical accepted archive snapshot; current run not inspected [I] | No current runtime claim from Started state |
| Data spaces / QGIP source collection — QGIP agency resource archive | E01 | Started | Tuesday 05:00 | Accepted indexed agency resources [I] | Natural weekly operation not established here |
| Data spaces / DoRA source collection — DoRA activity archive | E01 | Started | Daily 02:30 | Accepted complete activity raw archive [I] | Recent scheduled success not selected |
| Data spaces / ARC award source collection — ARC award archive | E01 | Started | Monday 07:00 | Accepted maintained award collection [I] | Natural weekly operation not established here |
| Data spaces / NHMRC workbook collection — NHMRC award workbook archive | E01 | Started | Monday 05:00 | Accepted maintained workbook collection [I] | Natural weekly operation not established here |
| Data spaces / MRFF workbook collection — MRFF award workbook archive | E01 | Started | Monday 06:00 | Accepted maintained workbook collection [I] | Natural weekly operation not established here |
| Data spaces / ROR organisation collection — ROR official releases | E01 | Started | Monthly; explicit day/time unresolved | Accepted full release, unchanged replay and first scheduler run [I] | Future monthly occurrences; exact effective next trigger unknown |
| Data spaces / Test source archive staging — Isolated archive staging test | Publications/archive | Stopped | Manual; disabled | Historical captured graph only in selected inventory [I] | Fresh runtime evidence not selected; do not run merely for view |

## Grants and funding

| Flow / purpose | Lane | State | Saved schedule | Last accepted runtime | Remaining blocker / limit |
| --- | --- | --- | --- | --- | --- |
| Grants / Reviewed import upsert — Retain originals and update admitted grant | Grants | Stopped | Manual; disabled | 24 Oct: exact originals/replay/negative/recovery; original Invoker preserved [G] | Native complete; source integration checkpoint may lag |
| Grants / NIH acquisition qualification — Qualify source-response/ZIP acquisition | Grants | Stopped | Daily candidate saved; disabled | 24 Oct: actual one-minute success/failure/recovery ticks [N] | Daily/full register-model chain and delivered alert unqualified |
| Funding / NHMRC archived award refresh — Refresh retained NHMRC awards | Funding (historical) | Stopped | Manual; disabled | Accepted operator-run refresh/replay snapshot [I] | Current runtime/owner handover not selected |
| Funding / MRFF archived award refresh — Refresh retained MRFF awards | Funding (historical) | Stopped | Manual; disabled | Accepted 1,915 fields and zero-write replay snapshot [I] | Current runtime/owner handover not selected |
| Funding / ARC award context export — Export ARC context for readers | Funding (historical) | Stopped | Manual; disabled | Historical R17b captured graph; latest runtime not selected [I] | Current runtime/owner handover not selected |
| Funding / QGIP candidate export — Export QGIP funding candidates | Funding (historical) | Stopped | Manual; disabled | Historical R17b captured graph; latest runtime not selected [I] | Current runtime/owner handover not selected |
| Funding / Calendar change upsert — Record calendar changes | Funding (historical) | Stopped | Manual; disabled | Historical R17b captured graph; latest runtime not selected [I] | Current runtime/owner handover not selected |
| Funding / Watchlist upsert — Maintain funding watchlist | Funding (historical) | Stopped | Manual; disabled | Historical R17b captured graph; latest runtime not selected [I] | Current runtime/owner handover not selected |
| Funding / Delivery ledger upsert — Maintain funding delivery ledger | Funding (historical) | Stopped | Manual; disabled | Historical R17b captured graph; latest runtime not selected [I] | Current runtime/owner handover not selected |
| Funding / Calendar upsert — Maintain funding calendar | Funding (historical) | Started | Manual; no recurrence | Historical R17b captured graph; latest runtime not selected [I] | Current runtime/owner handover not selected |
| Funding / Test machine endpoints — Probe funding source endpoints | Funding (historical) | Stopped | Manual; disabled | Historical R17b captured graph; latest runtime not selected [I] | Current runtime/owner handover not selected |

## Publication, researcher and project operations

| Flow / purpose | Lane | State | Saved schedule | Last accepted runtime | Remaining blocker / limit |
| --- | --- | --- | --- | --- | --- |
| Publications / Register ingestion and enrichment — Upsert publication registry | E01/publications | Stopped | Daily 06:00 saved (20:00 UTC); disabled | 23 Oct: H04 malformed/failure/interruption/replay preservation accepted [C] | Stopped; end-to-end generation reconciliation separate |
| Publications / Test weekly digest — Compose controlled weekly digest | Digest | Stopped | Manual; disabled | 22–23 Oct: controlled no-send runtime/HTML and wiring readback [C] | Send-authority gate false; delivery not authorised |
| Publications / Test native restore drill 20261023 — Isolated restoration rehearsal | Report/recovery | Stopped | Recurrence trigger; disabled; cadence not inspected | Runtime evidence not selected for this view [L] | Do not infer failure or run a drill from missing evidence |
| Publications / Delivery monitor — Observe publication output/delivery occurrences | Monitoring | Started | Daily 12:05; starts 1 Nov 2026 | Controlled readable-output/missing-delivery cases accepted [I] | Natural unattended occurrence remains unproved |
| Publications / Structured monthly report — Generate structured SharePoint HTML report | Publications/report | Stopped | Manual; disabled | Accepted output/replay/provenance/edit preservation [I] | Automatic DOCX/PDF not qualified; no schedule |
| Publications / Open-access paper archive — Retain eligible paper originals | E01/OA | Stopped | Manual; disabled | Accepted fallback, changed content, integrity, replay/recovery [I] | Selected operator-run scope only |
| Studies / Archived source refresh — Refresh studies from archived trials | Studies (historical) | Stopped | Manual; disabled | Accepted operator-run refresh/replay snapshot [I] | Current source/model generation not rechecked |
| Publications / Register export — Full/monthly register export | Publications | Started | Day 1 monthly 09:00; starts 1 Nov 2026 | Historical export snapshot; no new scheduled success inspected [X] | First future natural occurrence not established |
| Researchers / Export — Export researcher evidence snapshots | Publications/researchers | Stopped | Manual; disabled | Accepted full/replay outputs documented [R] | Operator-run only; no recurrence |
| CHHHS RIMS - Reconciliation Exception Review — Review source reconciliation exceptions | Reconciliation (historical) | Stopped | Manual; disabled | Runtime evidence not selected for this view [L] | Current owner/evidence handover unresolved |
| Projects / DoRA activity register upsert — Upsert activity registry | Projects (historical) | Stopped | Manual; disabled | Historical R17b captured graph; latest runtime not selected [I] | Current runtime/owner handover not selected |

## Evidence and upkeep

- **L:** Private FlowAgent scoped name/state/trigger readback,24 Oct; exact observation timestamp above.
- **S:** Private source-collector-native-setup-20261024.json, captured23 Oct23:42UTC; saved schedules only.
- **I:** Private grants-solution-final/native-inventory.json and solution export,24 Oct; runtime descriptions are accepted historical snapshots.
- **C:** Private E01_HANDOVER, e01 lane checkpoint and e01-current-state accepted runtime receipts; latest checkpoint24 Oct04:33UTC.
- **O:** Private24Oct OpenCitations count/metadata/consumer/citations acceptance and documentation receipts; PR31/32/36/37/38.
- **G:** Private24Oct import-original-retention/acceptance.json and grants lane checkpoint04:54UTC.
- **N:** docs/NIH_RECURRING_QUALIFICATION.md and private24Oct nih-scheduled-observation/acceptance.json.
- **X:** Private24Oct grants-solution-final export recurrence plus fresh state listing; no recent run inferred.
- **R:** docs/RESEARCHER_EXPORT_FLOW.md (exists in private authoring checkout); accepted historical operator-run scope.

Fresh state listing retained at ignored
`private/ops/2026-10-24-flow-operations-view/list-flows.json` in the primary
evidence checkout. Private receipts remain there; do not copy them into Git.
Owners should update accepted runtime/schedule fields from their next terminal
handover, recording observation time and receipt. Do not update timestamps without
new observations or infer live success from an old receipt. If maintaining the
JSON and page, keep one row per exact observed name and reconcile both together.
