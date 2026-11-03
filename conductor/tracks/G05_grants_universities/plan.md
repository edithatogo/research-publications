# Implementation plan

## Current source priorities — 3 November 2026

GrantConnect remains the active source for Commonwealth opportunities. Use its existing
intake and canonical opportunity keys. Evaluate the following candidates before adding
a collector, checking coverage, reuse terms, source identifiers and overlap with GrantConnect.

| Active assessment | Intended use |
| --- | --- |
| [Commonwealth grants and programs finder](https://business.gov.au/grants-and-programs) and [Queensland innovation grants](https://www.business.qld.gov.au/running-business/growing-business/becoming-innovative/grants) | Discover business and innovation programs. Follow the issuing agency's listing to confirm the round, eligibility and closing date. |
| [Queensland open data](https://www.data.qld.gov.au/) and [Commonwealth open data](https://data.gov.au/) | Use CKAN catalogue searches to locate grant datasets. Check each resource's licence, update date and whether its records describe open calls or past awards. |
| [ARC grants portal](https://dataportal.arc.gov.au/NCGP/Web/Grant/Help), [ARDC Research Activities API](https://documentation.ardc.edu.au/rda/research-activities-api) and [OpenAlex Awards](https://help.openalex.org/data/awards/) | Assess award and project data for funding history and links to research outputs. Keep award identifiers separate from open-call identifiers. |
| [PollenOne](https://pollenone.com/search) | Assess as a discovery aid. The publisher describes free access during its beta. RIMS API access and reuse terms still need verification. |
| [The Grants Hub](https://www.thegrantshub.com.au/pricing) | Assessed as a subscription directory with a 14-day trial and restrictions on reuse in searchable grant tools. Exclude from active automated intake. |

## Future institutional integrations

Defer Pivot-RP, GrantForward, Streamlyne FundFit, Academic Analytics, Atom Grants,
Research Professional, Instrumentl, Candid (Foundation Directory Online) and GrantWatch.
Revisit each provider when the institution has a supported API key and licence terms
cover RIMS use. Verify the provider offers the required API and data before scheduling
implementation. The catalogue retains university access notes for reference. Obtaining
a Pivot-RP account, export or calendar subscription is outside the active work plan.

**Access scope:** current-user permitted source inspection and reviewed/manual
institution intake only. No cross-user directory or unattended portal access
is assumed.

- [x] Record scope and acceptance requirements.
- [x] Inspect current inputs, dependencies and relevant platform objects. University research-office pages and access boundaries were checked; no institutional login or portal export was used.
- [x] Implement: Record JCU, UQ, QUT and Griffith authority pages, formats, access, eligibility scope and only source-backed internal lead-time facts.
- [~] Verify public sources and retain unknown lead times as null. Subscription portal access moves to the future institutional integrations above.
- [x] Record local and live evidence separately before closure.

## University source freshness recheck — 2026-09-22

- [x] Recheck UQ's public current-funding table and research-office guidance:
  internal and external closes are distinct, with a stated standard ten
  working-day internal close and scheme-specific exceptions. UQ access and
  submission workflow remain manual-review boundaries.
- [x] Recheck QUT's public research/ARC guidance: public pages identify
  scheme information and direct applicants to the Research Office for internal
  deadlines; no permitted feed/export was exposed.
- [x] Refresh the UQ and QUT catalogue `last_verified` dates to `2026-09-22`.
- [x] Recheck JCU and Griffith through their current official pages. JCU's
  current application-procedures page confirms one-week Australian and
  two-week overseas internal submission lead times; Griffith's public page
  confirms the Research Funding support route is internal-only. Neither public
  route supplies a permitted feed/export or authenticated portal route.
- [~] Keep JCU and Griffith at manual-review intake with unknown or qualified
  lead-time fields; do not promote either institution to unattended ingestion
  without a permitted export/API or authenticated portal evidence.

## Phase: Review fixes

- [x] Task: Validate known institutional lead-time objects while retaining null for unknown evidence (a179d73).
- [x] Task: Reject boolean lead times and invalid authority/verification metadata before source use (f0ee882).
- [x] Task: Reject fractional institutional lead times so catalogue values match integer-day planning inputs (ae2a630).
- [x] Task: Reject non-object rows, non-string institution identities and future verification dates using the Australia/Brisbane business date.

## Phase: Conductor review fixes — 2026-09-22

- [x] Task: Reuse the strict university catalogue validator before bounded authority probing, so malformed rows cannot be mistaken for source evidence (`1a073b7`).
- [x] Verification: focused source-probe/university tests (12), full local suite (449 tests, 8 skipped), project checks (460), web-first contracts, Conductor validation and diff validation pass locally.
- [~] Permitted institutional feed/export or authenticated portal acceptance remains open; authority-page probes remain read-only evidence only.

## Phase: Conductor review fix — authority URL boundary — 2026-09-22

- [x] Task: Reject surrounding whitespace in university `authority_url` values instead of stripping a source identity before validation (`1f5c25f`).
- [x] Verification: focused university tests (9), full local suite, project checks (460), web-first contracts, Conductor validation and diff validation pass locally.
- [~] Permitted institutional feed/export or authenticated portal acceptance remains open; authority-page probes remain read-only evidence only.

## Organisation identity evidence — 24 October 2026

Verified all four maintained institution identities against individual official ROR v2 API records: exact catalogue name, institutional website host, Australian location and active status. The catalogue retains the canonical ROR URL, observation date and original-response SHA256. Original responses are retained privately under `private/ops/2026-10-24-g05-ror/`. Existing local institution keys and manual-review intake are unchanged. These identities do not qualify feed/export entitlement, CHHHS eligibility or any opportunity relationship; those acceptance tasks remain open.
