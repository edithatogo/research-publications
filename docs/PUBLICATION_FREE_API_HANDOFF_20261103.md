# Free-API publication enrichment: consolidated handoff

## Delivery decision — 3 November 2026

The selected source integrations use free APIs and retained archives. No paid subscription, institutional-only feed, paid tier or purchase-dependent fallback remains in the active plan. Preserve earlier provider assessments as history; they are not executable onboarding tasks.

| Source | Accepted native integration | Coverage and remaining boundary |
|---|---|---|
| Europe PMC | Existing SharePoint archive, isolated Power BI source tables and publication ingestion evidence guard | Frozen1,344 publications:1,286 exact PMID matches and58 missing identifiers;140 populated field paths. Saved-generation manual integration accepted. |
| OpenAlex | Existing SharePoint archive, isolated Power BI source tables and publication ingestion evidence guard | Same frozen set:1,284 matches,57 missing identifiers and3 verified no-matches;232 populated field paths. Saved-generation manual integration accepted. |
| Crossref | Existing native collector/archive, targeted DOI enrichment and failed-generation diagnostics | Dated28October acceptance covers1,286 source DOI keys:1,285 retained records plus one fresh DOI response, comprising1,282 HTTP200 and four explicit404 outcomes. The77-action incremental collector was saved Started at daily03:30 Brisbane; natural execution was not claimed. The revised recovery lane is closed; the stalled full sweep and37 broad windows remain retired/history. This is not a fresh November1,344-publication sweep. |
| OpenCitations | Native count and bibliographic collectors, Archived source assertions consumer, incoming citation-link archive and native field-guide documentation | Accepted48-DOI scope:48 imported assertions; metadata44 single matches,3 no-hits,1 multiple match. Incoming-link scope retained344 unique OCI observations. It is not a complete1,344-publication model projection. No wider acquisition is required to preserve accepted scope. |
| Semantic Scholar | Saved responses in the same SharePoint/model/ingestion route as Europe PMC/OpenAlex |1,266 matches,19 verified no-matches,12 missing/invalid identifiers,2 DOI/PMID conflicts,45 provider-deferred lookups;45 populated field paths across20 requested parent fields. Explicit quota checkpoint, not complete collection. |

Earlier wording that Crossref/OpenCitations were not integrated conflated different accepted consumer scopes. The November source-evidence tables cover Europe PMC, OpenAlex and Semantic Scholar; Crossref/OpenCitations already have their separate native paths. Adding their complete retained payloads to these newer generic tables would be an additional consumer projection, not repairing an absent source integration. No source-specific citation counts should be summed or silently substituted.

## Model and field contract

The81 accepted source pages reconstruct exactly from the native byte-preserving archive. The model contains4,032 unique publication/source pairs for the three November sources. Every source-specific nested field-presence count reconciles to the saved coverage report. Queryable record strings may be case-normalised by the model dictionary; Base64 archive chunks are the exact-byte oracle.

Four additive tables serve distinct purposes:

| Table | Purpose |
|---|---|
| PublicationSourceEvidence | One canonical publication/source disposition, including missing, ambiguous, no-match and deferred cases |
| PublicationSourceRecordChunks | Queryable complete source-record JSON, with source and observation context |
| PublicationSourceArchiveChunks | Exact archived file bytes in ordered Base64 chunks, verified againstSHA256 |
| PublicationSourceFields | Nonempty nested source field/occurrence values and per-publication field coverage; accepted matches only |

All1,344 canonical keys and every value of the existing18-field export are unchanged. The retained monthly output still has exactly14 keys. Provider assertions enrich source evidence and do not silently overwrite reviewed canonical fields. The heterogeneous row readers preserve missing provider-specific columns with `MissingField.UseNull`.

All20 selected Semantic Scholar parent fields are requested: paperId,corpusId,externalIds,url,title,abstract,venue,publicationVenue,year,referenceCount,citationCount,influentialCitationCount,isOpenAccess,openAccessPdf,fieldsOfStudy,s2FieldsOfStudy,publicationTypes,publicationDate,journal,authors. Complete returned objects/arrays/nulls and observation evidence are retained. A present container does not imply every leaf is available. The accompanying field-coverageJSON gives source-path counts and requested-parent absence counts.

## Deduplication and native verification

The final accepted ingestion run succeeded, selected zero admission candidates and verified1,348 registry source keys were unique. Existing aliases and legacy rows were preserved. The flow's original recurrence and Stopped state were restored and independently read back. No source schedule or sharing setting was enabled.

For Semantic Scholar,1,332 identified publication rows yield1,329 distinct lookup identifiers; three duplicate provider requests are avoided while every canonical publication remains represented. Twelve records have no usable frozen identifier, including one title stored in the DOI cell. Two DOI responses conflict with canonical PMIDs. Retained Europe PMC/OpenAlex evidence was reviewed: preserve these14 exceptions with explicit decisions, not guessed corrections. Seven additional retained DOI candidates for the deferred PMID group have no matching saved Semantic Scholar response, so they cannot fill the cache without provider access.

## Evidence, continuation and closeout

Accepted receipts remain in the original checkout under `private/ops/2026-11-02-publication-lock-recovery` and `private/ops/2026-11-02-semantic-scholar-full`. OpenCitations native assertion/archive/documentation receipts remain under its24October operations. Native IDs, raw provider payloads, authentication pins and process journals stay private.

The45 Semantic Scholar lookups remain a separately labelled rate-limit dependency. The existing cache-first CLI collector uses three-second pacing, conservative hourly backoff and longer server instructions. One owned native continuation waits for complete collection, checks exact model/flow drift, uploads changed pages only, refreshes transactionally and verifies a bounded ingestion run before restoring native state. Do not restart either operation from a lock/state file alone; verify its actual live process first. No new login is selected.

The [Conductor execution plan](../conductor/tracks/publication_source_completion_20261103/plan.md) preserves final collection/native tasks as incomplete. This consolidated handoff and native documentation close the dependency-ready documentation work; they do not relabel the quota checkpoint as complete collection, enable recurrence or claim full institutional coverage. Source integration uses the existing repository main/PR route and preserves other worktrees and native owners.

## Related accepted records

- [Europe PMC/OpenAlex native delivery](PUBLICATION_ENRICHMENT_NATIVE_20261102.md)
- [Semantic Scholar field coverage and checkpoint](SEMANTIC_SCHOLAR_NATIVE_CHECKPOINT_20261103.md)
- [OpenCitations native assertions](OPENCITATIONS_SOURCE_ASSERTIONS.md)
- [OpenCitations field guide and native documentation](OPENCITATIONS_NATIVE_DOCUMENTATION.md)
- [OpenCitations incoming citation links](OPENCITATIONS_CITATION_LINKS.md)
