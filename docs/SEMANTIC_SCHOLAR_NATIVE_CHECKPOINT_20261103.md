# Semantic Scholar native checkpoint — 3 November 2026

The saved anonymous Semantic Scholar results have been delivered to the existing SharePoint reporting folder, isolated RIMS model and ingestion flow. This supersedes the one-record bootstrap's native snapshot. Collection is quota-limited: 45 lookups remain deferred, and the existing paced collector retains their resume point.

| Disposition | Publications |
|---|---:|
| Matched | 1,266 |
| Verified no match | 19 |
| Ambiguous identifier | 2 |
| Missing identifier | 12 |
| Deferred after HTTP 429 | 45 |
| Total | 1,344 |

The 20 selected parent fields and all returned nested values are retained with source observations and response hashes. Accepted records expose 45 populated field paths. Ambiguous records remain archive evidence and are excluded from accepted field values. Provider absence remains distinct from an unattempted or throttled lookup.

## Native proof

All 27 new content-addressed Semantic Scholar pages were uploaded through bounded manual batches. Together with the 54 accepted Europe PMC/OpenAlex pages, all 81 pages reconstruct byte-for-byte from the refreshed model. The four source tables contain exactly 4,032 unique publication/source pairs. Per-publication field-presence counts match the combined saved coverage report: Europe PMC 140 paths, OpenAlex 232, Semantic Scholar 45.

All 1,344 canonical keys and every value of the existing 18-field export remain exact. The frozen monthly set remains the same 14 keys. The native ingestion run succeeded, selected zero admission candidates and verified 1,348 registry source keys were unique. Existing aliases and legacy rows were preserved. The original recurrence, valid connection-reference map and stopped state were restored and read back. No schedule, sharing or report-layout change occurred; no interactive login was used.

The anonymous single-record collector uses three-second pacing, immutable hashed response caching and increasing HTTP 429 cooldowns, honouring longer provider instructions. Replaying completed lookups needs no provider calls. It deduplicates 1,332 identified publications into 1,329 lookup identifiers while preserving each canonical publication. The remaining 45 are PMID-only lookups; no no-match status has been inferred from throttling.

## Recovery and continuation

The native flow definition exceeded size limits when all saved page literals were placed in one definition. Bounded batches below the qualified size limit succeeded. Exact clientdata updates through the existing FlowAgent Azure CLI workload preserved the solution connection references; each batch verified its runtime manual trigger before running. Model import changed only the four source-reader parts, followed by a completed transactional refresh.

Private receipts in the original checkout's `private/ops/2026-11-02-semantic-scholar-full` include the upload batches, model definition readback, completed refresh, byte and field reconciliation, final native run, restoration and `completion-receipt.json`. This receipt is **PASS_NATIVE_QUOTA_LIMITED_CHECKPOINT**, not complete collection. Preserve these receipts and preimages. A changed cache requires a new frozen generation; reuse unchanged archive pages and issue no duplicate writes. The original bootstrap receipts remain historical evidence.

Source tests and required repository checks are unchanged from the [bootstrap qualification](SEMANTIC_SCHOLAR_NATIVE_BOOTSTRAP_20261102.md); they were reused. This generation added native data, byte, field, identity and flow proof. Conditional licensed feeds and wider institutional/public-use rights remain outside this no-login pass.

## Requested-field coverage

Counts refer to the 1,266 accepted matches. A present object can contain null subfields; for example, an `openAccessPdf` object does not establish that a PDF URL is available. Nested nonempty values are accounted for separately in the 45-path field report.

| Requested field | Present | Absent from matched responses |
|---|---:|---:|
| paperId | 1,266 | 0 |
| corpusId | 1,266 | 0 |
| externalIds | 1,266 | 0 |
| url | 1,266 | 0 |
| title | 1,266 | 0 |
| abstract | 846 | 420 |
| venue | 1,250 | 16 |
| publicationVenue | 1,185 | 81 |
| year | 1,266 | 0 |
| referenceCount | 1,266 | 0 |
| citationCount | 1,266 | 0 |
| influentialCitationCount | 1,266 | 0 |
| isOpenAccess | 1,266 | 0 |
| openAccessPdf | 1,266 | 0 |
| fieldsOfStudy | 1,240 | 26 |
| s2FieldsOfStudy | 1,265 | 1 |
| publicationTypes | 1,233 | 33 |
| publicationDate | 1,243 | 23 |
| journal | 1,266 | 0 |
| authors | 1,265 | 1 |

At 00:36 Brisbane on 3 November, the retry after a full one-hour cooldown still returned HTTP 429 with no Retry-After header. No new results were obtained. The existing collector retained the 45 deferred lookups and scheduled its next conservative attempt for 01:36 Brisbane. A one-task foreground continuation waits for complete collection, then uses the verified checkpoint preimages, checks native drift, skips unchanged pages, and runs the existing native delivery/reconciliation sequence. It creates no schedule or login and stops on errors without retrying uncertain mutations. Its private status is `private/ops/2026-11-03-semantic-scholar-complete/continuation.log`; `completion-receipt.json` there exists only after final native checks pass. Until then, the accepted result remains the quota-limited checkpoint above.
