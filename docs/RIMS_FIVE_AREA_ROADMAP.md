# RIMS five-area roadmap

Planning revision: 6 November 2026. This reorganises the existing backlog; it does not reset accepted work, reopen archived tracks or authorise native dashboard changes. Earlier page inventories are dated: the 3 November reconciliation reports 12 pages, superseding the October six-page inventory. Current live state requires exact-target readback before changes.

## Implementation boundary

Confirmed user boundary: implement dependency-ready local code and plans; include all clinical studies with trials identified; support external discovery and CHHHS-associated views separately. RIMS holds identities and links to PPG-held standards/evidence. Assess restricted APIs and prepare unsent access requests. New online collectors, native flows, services and dashboards remain separately scoped proposals. No purchases, agreements, messages, activation or native report/model writes are included.

## Five areas and reuse

| Area | Existing work to reuse | Remaining outcome | Existing delivery home |
| --- | --- | --- | --- |
| Research Outputs | Canonical publications, bibliography/monthly exports, source enrichment, OA/archive and researcher evidence | Close selected source/register/model/output promotion and timely natural delivery; datasets/software remain conditional extensions | T11/E01, T14, publication-source completion and RMD-05 |
| People & Collaborations | Author-label mentions/groups, searchable exports, prepared measures and identity design | Evidence-backed person resolution, dated roles/affiliations and useful collaboration navigation; preserve unresolved labels | Archived E05 evidence, R1.5/R5.5/R5.7 and E04 |
| Projects & Studies | DoRA activity/raw archive/upsert, ClinicalTrials.gov, ANZCTR manual lane, Studies refresh | CHHHS clinical-study register view, trial discovery and qualified links to outputs/funding and PPG evidence | T11-H03/H04, R5.5, G06 |
| Funding | Award/opportunity registries, source catalogues, internal application tracking, calendar/watchlist and notification workers | Source access/admission, real reviewed lifecycle and delivery; separate opportunities, applications and awards | G02–G08 and current grants reconciliation |
| Organisations & Affiliations | Existing ROR collection, institution/facility evidence and typed organisation relationships | Explicit organisation/unit identities, aliases, hierarchy and dated affiliations; ROR does not identify every local unit | R1.5/R1.6, G06 and E04 |

Research Overview and Sources & Data Quality are cross-cutting views. Calendar & Watchlist belongs under Funding. The Clinical Analytics rename to Research Profile & Open Access remains an E04 presentation proposal; no native rename is performed here. Author Evidence remains the accurate label until person identity is established.

## Priorities and completion boundaries

1. Preserve current owners, source-generation lineage and accepted receipts. Complete only remaining selected admission/promotion, historical-import reconciliation and RMD-05 exits; do not rerun accepted collector qualification. MRFF unattended access and GrantConnect intake retain their scoped external prerequisites.
2. Pin the CERIF source, agree a bounded application profile, map existing fields/relationships and validate a representative export. A vocabulary download alone is not conformance.
3. Deliver a CHHHS Projects & Studies view using already authorised DoRA and Studies data, with explicit source coverage, local site involvement and last-observed status. Reuse identifiers and existing storage before proposing a new list.
4. Deliver trial discovery over accepted registry snapshots first; add online search only after its exact provider/operation/access contract is qualified.
5. Link study records to PPG requirements and evidence through existing keys and access checks. Complete person/organisation crosswalks needed by that outcome.
6. Schedule native report/model changes as separate E04/T15 increments with fresh baseline, isolated rollback, semantic parity and actual rendering. Do not make visual redesign a prerequisite for useful exports/register views.

## Architecture: logical medallion, existing storage

Existing plans define bronze (complete authorised original payloads/files, schema, source scope, timestamps, hashes and commit manifests), silver (typed entities, source assertions and evidence-backed crosswalks), and gold (selected registers, exports, aggregates and semantic/report consumers). Coverage is source-specific and partly qualified; this is not proof every source passes all three layers.

No physical Fabric Lakehouse/OneLake deployment or universal lake is established by the inspected architecture. Existing Microsoft archive/storage, SharePoint and Power BI remain the implementation. Platinum is not currently defined. If useful, a later platinum designation could mean immutable issued-period outputs with source/template/rule versions; it must not imply clinical approval or become another store by default. No lakehouse migration or capacity purchase is proposed.

## CHHHS study register and trial explorer

Confirmed scope is all clinical studies with an explicit clinical-trial subtype. A DoRA view is a starting point, not proof of a complete active-trial census. Retain namespace-qualified project, registry and local site identifiers separately. CHHHS involvement must distinguish conducting site, sponsor, investigator affiliation and candidate text match; location/author strings alone do not confirm site participation. Retain disagreements, dates and their precision, missing status and candidate/reviewed links. Deduplicate cross-registrations only with evidence. Do not copy participant-level or patient data.

The explorer should filter/search condition, intervention, recruitment status, study type/phase, geography/site and registry identifier where supported. Show source links, observation date, stale/unknown states and coverage; export the selected set and its query/snapshot provenance. Separate external discovery candidates from confirmed CHHHS studies. It is research discovery, not patient eligibility, recruitment authorisation or clinical advice. Reuse ClinicalTrials.gov, accepted ANZCTR imports and WHO source work; do not build duplicate collectors or imply WHO/ANZCTR automated access is already qualified.

For PPG, propose study → applicable requirement/version → evidence reference/version → review status. Keep service-level and study-level evidence distinct, preserve caller permissions and history, and never infer accreditation compliance from a registry row or evidence count. Map to the current ACSQHC National Clinical Trials Governance Framework (NCTGF), including Clinical Governance and Partnering with Consumers actions. Verify the exact applicable edition and action IDs before implementing the matrix. DoRA metadata cannot provide all workforce, consent, safety, consumer-partnership and governance evidence.

## Restricted APIs and agreements

Extend existing source catalogues rather than create a parallel procurement register. For each selected provider record: needed gap and alternative; exact product/endpoint; paid/free/unknown; agreement/key/registration requirements; published price/date or quote required; quotas and permitted users; allowed retention, derived use and redistribution; institutional approval/contact; source/version and review date; fallback; qualification case and renewal/termination handling.

Assess existing candidates first: Dimensions and Lens (product-specific terms), Scopus/Web of Science (licensed access), ORCID member-only capabilities versus public access, ANZCTR/WHO access arrangements, and MRFF/GrantConnect publisher-supported machine access. These are assessment candidates, not assertions that every endpoint is paid or contract-bound. Check official terms for the exact operation before classification. A publisher access permission is different from payment. Do not replace working free APIs just for breadth. No key purchase, agreement signature, access-request send or new API integration is authorised by this plan. Unsent request drafts are authorised; existing MRFF/ANZCTR drafts are reused and none may be sent automatically.

## CERIF and PPG source registration

See [crosswalk and draft conformance contract](../contracts/cerif-application-profile.md). The supplied CERIFEntities vocabulary is a technical reference, not a clinical policy or the complete CERIF specification. Capture authoritative source bytes, source URL, time, version/commit, hash and rights notice privately. Register publication, edition and capture using PPG External Publications' existing schema; preserve the issuer's terms and do not apply the repository's Apache licence to it.

The current PPG workbench has an active owning chat. Its documented native CLI permits plan/export only and disables persistence; the source adapter's documented issuer boundary also needs explicit euroCRIS onboarding. Prepare a handoff, then use the current owner's qualified operation and native readback. Do not bypass the disabled writer, alter its allowlist or create a duplicate register. Native catalogue registration remains pending until an exact record and capture are read back.

Sources: https://github.com/EuroCRIS/CERIF-Vocabularies ; https://guidelines.openaire.eu/en/latest/cris/index.html ; https://www.safetyandquality.gov.au/national-standards/national-clinical-trials-governance-framework

## Local implementation checkpoint — 6 November 2026

[Study explorer](STUDY_EXPLORER.md) implements retained ClinicalTrials.gov search and two separate views using the existing projection/ZIP validator. Tests use fictional records; no complete live CHHHS register is claimed. [Restricted API assessment](FUTURE_SOURCE_ENRICHMENT.md#restricted-api-decision-plan--6-november-2026) and [unsent requests](RESTRICTED_API_REQUESTS_UNSENT.md) cover paid, agreement-based and unresolved access. [Machine-readable CERIF mapping draft](../contracts/cerif-profile.json) pins entity identifiers only; conformance/exchange remains pending.

## Selected Projects & Studies view delivered — 6 November 2026

The local reader now consumes reviewed evidence for11 source-reported CHHHS studies in the retained442-row DoRA capture, with one reviewed trial identity link and one unconfirmed candidate. The [reader contract](STUDY_EXPLORER.md#reviewed-evidence-in-the-study-view) binds the review to source hashes and keeps registry/site differences visible. All source rows remain intact. This is a bounded historical local view, not a current clinical-study census, native list admission or dashboard change. Existing Conductor F04/F05 retain the remaining native/operational boundaries.

## Projects & Studies maintenance — 6 November 2026

The [local maintenance route](STUDY_EXPLORER.md#maintain-the-registry-from-dora) reconciles new DoRA observations, reuses only unchanged same-resource reviews and preserves changed/missing/replacement-resource evidence for review. A fresh6November observation retains442 identical source records and11 reviewed local associations. Versioned links to PPG-held evidence are supported with study/service requirement scope, while actual study receipts/action keys remain pending. DoRA refresh does not renew registry/PPG evidence or prove current clinical status. Native dashboard and tenant changes remain separate.
