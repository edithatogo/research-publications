# Collector changed-path native qualification — 3 November 2026

This pass qualifies the changed PubMed, DataCite and ClinicalTrials.gov recovery paths. Existing acquisition acceptance is retained. It does not repeat a full collection, promote an interrupted prefix, admit publications, refresh the model or enable a schedule.

## Native evidence

| Case | Actual result |
|---|---|
| PubMed scheduled acquisition | Reused the successful 3 November scheduled run. The three published ESearch/EFetch read leaves have the same exponential policy: three configured retries, 10-second minimum/initial interval and one-minute maximum. |
| PubMed failed generation | Reused the real 30 October storage failure. Its failure receipt was saved, read and verified; completion writes were skipped. Independent guarded CLI download equals the recorded receipt, with `complete=false`, `accepted=false`. XML from that failed generation is not a current snapshot or a resumable XML cache. |
| PubMed retry path | A temporary manual native HTTP action used the exact published policy against a controlled synthetic HTTP503 endpoint. It reached terminal HTTP503 in about67seconds; the expected-failure handler and overall qualification run succeeded. No live publication query or data went to the fault endpoint. The Flow action API did not expose per-attempt retry history, including an expanded read; the configured count is verified, but an exact observed attempt count is not asserted. This is not evidence of an actual NCBI outage. |
| DataCite v3 failure producer | One genuine complete institutional query, with a valid zero-result response, was archived and read back before a controlled next-query HTTP400. The native v3 receipt preserved the entire76-query plan, frozen cutoff, previous checkpoint identity and completed query/page evidence. Receipt save/read/verify and independent CLI byte comparison passed. Completion writes were skipped. |
| DataCite automatic continuation | The native v3 reader, checkpoint identity, prefix order, archived page bytes/ETag, total and query identity guards succeeded. It reused the first completed query unchanged, issued the fresh successful provider read only for query1, advanced the prefix to two completed queries, and preserved the original cutoff and entire76-query plan. A controlled query2 failure produced another independently verified incomplete v3 receipt; completion writes were skipped. |
| ClinicalTrials checkpoint | One genuine100-study discovery page produced a native saved/read/verified first-pass checkpoint. Independent guarded CLI downloads verified the checkpoint and raw page. A controlled next-page HTTP400 prevented completion and produced a saved/read/verified failure receipt. |
| ClinicalTrials continuation | The native run consumed that checkpoint, retained the first100 study IDs and raw-page lineage, continued its exact cursor and advanced to200 unique study IDs. Independent downloads verified the new checkpoint and second raw page. The original source generation and mandatory complete-two-pass guards remained in place. Controlled later failure kept this a prefix, with no detail collection or completed manifest. |
| ClinicalTrials stale generation | A deliberately stale source-generation value was rejected by the actual native `Guard_source_version_before` with `CTGOV_RECOVERY_SOURCE_GENERATION_CHANGED`. Discovery continuation and manifest writes were skipped. Its failure receipt was saved/read/verified and independently downloaded with exact parity. |

## Integrity and scope

The original three collector definitions were independently reread through the guarded M365 CLI and remained unchanged. PubMed and DataCite remain Started; ClinicalTrials remains Stopped. Their failure alerts and existing connections were preserved. Independent CLI downloads of all three accepted last-good completion markers matched the recorded native bytes exactly. Qualification flows were manual-only, used the existing SharePoint connection and wrote into a separate runtime-qualification archive. All three temporary flows are now Stopped with no active runs and remain available for native review. Their alerts were disabled before failures; the API's misleading successful alert update was detected by readback and the actual native control was used.

The FlowAgent definition-update wrapper incorrectly remapped a connection alias on the temporary DataCite copy. No source collector was changed. The temporary target was inspected before an explicit same-client Flow service API update preserved its existing aliases and was independently read back. There were no blind mutation retries, authentication-client changes, permission additions or new connections.

Controlled400/503 responses are deliberate qualification faults, not real provider outages. DataCite's valid zero-result query verifies the empty-result path, not positive-match field coverage. ClinicalTrials'200-study prefix is not full discovery acceptance. These observations do not replace the previously accepted acquisition baselines.

## Evidence and checks

Detailed journals, definitions, action/repetition content, hashes, independent SharePoint downloads and current ownership remain in the original native owner's ignored `private/ops/2026-11-03-collector-runtime/`. Case folders are `pubmed-failure`, `pubmed-success`, `pubmed-retry-probe`, `dc-prefix`, `dc-resume`, `ct-prefix`, `ct-resume`, `ct-stale`, `ct-success` and `original-final`. No credentials or raw source snapshots are included in this source packet.

The unchanged source baseline passed the required unittest discovery:2482tests,19skips. Project validation passed446checks; web-first contract validation passed. These local checks are separate from the native case evidence above. No new helper framework or synthetic test suite was added.

Related: [current qualification track](../conductor/tracks/collector_runtime_qualification_20261103/index.md), [publication source disposition](PUBLICATION_SOURCE_DISPOSITION.md), and [acquisition builder source contract](PUBLICATION_ACQUISITION_BUILDERS_SOURCE_20261029.md). Broader publication-cycle, Semantic Scholar rate-limit and unrelated flow gates retain their existing dispositions.
