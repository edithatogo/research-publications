# Writer runtime and recovery qualification — 22 October 2026

The existing publication writer now has controlled native evidence for its
rejection paths, genuine creates, replay, complete export and exact restoration.
The normal 11-action daily definition and original connections are restored,
Stopped, with no active or queued writer run. No production schedule was enabled.

Four temporary read-only cases reused the original readiness, row-count and
source-key guards. Empty results and a one-row partial result were rejected
against the 1,344-row readiness count. All 1,344 deliberately blank source keys
were rejected before downstream work. A genuine DAX ERROR returned HTTP 200 with
QueryUserError and empty rows; the row-count guard rejected it. The latter proves
this actual error-bearing response shape, not every possible provider failure.
These graphs contained no register or export mutation actions. An independent
complete register read afterward preserved all 1,648 rows/every returned value
and all 303 legacy blank-key rows.

Three newly retained publications were independently absent by source/canonical
key, PMID, DOI, title and PubMed URL. The bounded positive run reused the original
create/update/full-title/author logic and all four full-register export actions.
Three correlated native HTTP 201 results and independent list reads prove exactly
three additions. Source fields, complete titles/authors and date precision agree
with the actual model projection. All earlier 1,648 records remain unchanged.

The fresh same-input replay succeeded with all three create actions Skipped and
three HTTP 200 updates to the same IDs. The complete 1,651-row ID/key sets and
122,174 returned fields were compared: only the three records' LastObservedUTC,
Modified and version metadata changed. First observation, source identity,
substantive fields and human/review fields were preserved; no duplicate appeared.
Existing indexed SourceKey/CanonicalKey uniqueness remains enabled.

Both native CSV outputs contain the complete configured exportable register:
1,348 rows and 54 columns. The 303 legacy rows with neither export key remain in
the list under the unchanged export filter. Each export's 72,792 values matches
its native selected records. Independent stored-file reads match the native CSV
bytes and SHA-256. The replay CSV differs only in the three LastObservedUTC cells.
The existing timestamp-plus-GUID naming preserves earlier CSV files.

Private evidence remains under
`private/ops/2026-10-21-e01-runtime-qualification/`:
`writer-22-four-native-guards-acceptance.json`,
`writer-22-newthree-runtime-acceptance.json`,
`writer-22-newthree-register-preservation.json`,
`writer-22-newthree-replay-native-acceptance.json`,
`writer-22-newthree-replay-register-preservation.json`,
`writer-22-newthree-replay-csv-acceptance.json`,
`writer-22-final-original-restoration.json`, and
`writer-22-final-original-service-renewed-raw.json`.

This closes the selected writer technical qualification, not business acceptance
or unattended operation. Later natural occurrences remain E08. The retained
Crossref generation and original raw-source archive integration remain separate
E01 technical work. The final normal writer graph is unchanged, so temporary
qualification graphs do not require a new production documentation release.

## Failure after register writes and before export — 12 October run, reconciled 4 November
The publication loop completed and the downstream register read succeeded. CSV projection then failed because the mapping treated a URL string as an object. The file-write action was never reached. The post-failure register read returned 1,648 items, including 1,345 keyed rows, with no duplicate source or canonical keys. The corrected projection was saved and the full flow was resubmitted successfully. The persisted CSV matched all 1,345 keyed register items by ID, source key, canonical key, review status and review notes. The 303 blank-key rows were outside the configured export.

This covers recovery from the observed post-loop projection failure. It does not establish which rows the failed run changed, preservation of the preceding export's bytes, or recovery from a stop partway through the register loop. Keep those H04 cases open. The original private receipts share the prefix `2026-10-12-e01-` and include `manual-register-export-run-failure`, `register-postfailure-readback`, `export-url-type-fix-native-save-readback`, `manual-register-export-retry-success` and `register-export-csv-readback`.

## Native fault matrix reconciled on 4 November 2026
The original controlled interruption completed one existing-item update and suppressed two later writes and the export. The full replay updated three existing items, created none and preserved protected and substantive values across 1,651 rows. All 476 earlier export files were preserved. Independent stored and generated CSV bytes matched across 1,348 rows and 54 columns. The original eleven-action definition, connections and Stopped state were restored. This closes the controlled mid-write replay requirement. The separate November cancellation has different run identities.

The original query guard rejected injected malformed envelopes. The native HTTP action exhausted three retries on a controlled 429, suppressed downstream actions on a client timeout, and handled a controlled 403. An actual platform destination-policy denial was also recorded. Actual SharePoint connector ACL denial remains unverified. The selected ClinicalTrials partial-page test returned 100 of 12,677 expected rows and skipped both study and manifest saves.

Receipts are in the original checkout's ignored `private/ops/2026-10-23-e01-current-state/`. Use `writer-h04-interruption-replay-runtime-acceptance.json`, `writer-h04-interruption-replay-csv-value-acceptance.json`, `writer-h04-final-restore-acceptance.json`, the separate malformed, public429, public403, public-delay-timeout, native-policy-denial and post-fault preservation receipts, and `h04-partial-provider-page-reconciliation.json`. The public-delay timeout receipt resolves the timeout limitation recorded in the earlier HTTP summary.
