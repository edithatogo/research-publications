# Europe PMC and OpenAlex native integration — 2 November 2026

The frozen bibliography contains 1,344 publications. It has 1,286 Europe PMC matches, 58 missing PMIDs, 1,284 OpenAlex matches, 57 missing DOIs and three OpenAlex no-matches.

## Native data delivery

The existing approved SharePoint reporting folder contains 54 versioned data files and a manifest. Every saved file was read back and matched by SHA-256. The isolated existing RIMS semantic model reads these files through its existing SharePoint.Contents route.

Four additive tables contain the source/publication index, queryable record chunks, byte-preserving archive chunks, and a publication-related field/occurrence evidence table. The canonical index contains 2,688 unique source/publication pairs. The archive table preserves original JSON bytes independently of the model text dictionary's case normalisation. Every source field path and its per-publication presence count was queried from the field table and reconciled exactly against the saved coverage report.

Full native archive reconstruction reconciles all 54 input hashes and all 2,570 matched provider records, including nested fields and observation metadata. Per-publication field-presence counts match the saved report exactly over 140 populated Europe PMC field paths and 232 OpenAlex field paths.

## Flow delivery

The existing publication registry ingestion flow gained an evidence query that requires the complete 2,688-row unique key set and canonical key membership before its existing ingestion queries proceed. Two historical DAX query strings had literal backslash-n sequences repaired to actual newlines.

The flow now checks existing source keys, canonical keys, PMIDs and retained DoRA alias forms before selecting records requiring admission. Its original row-level identity and conditional-write safeguards remain. This avoids reprocessing unchanged records and preserves legacy identities.

The selected flow was originally stopped with a recurrence trigger. A temporary manual trigger was used for authorised operator runs. The initial broad legacy run was cancelled at a verified terminal checkpoint; its completed conditional writes were retained. The bounded run and subsequent replays succeeded. The final replay selected zero admission candidates, verified all 1,348 registered source keys were unique, and saved its coverage/uniqueness verification output in the existing reporting folder. The original recurrence definition and stopped state were then restored and independently read back with exact definition and connection-reference equality.

## Recovery and evidence

The first candidate embedded a large compressed data payload and failed Fabric import. Native readback proved the original 75-part definition remained exact and its 1,344 canonical keys still queried successfully. The replacement SharePoint reader imported and refreshed successfully. The final model has 79 definition parts; all original table definitions remain exact. Existing changes are limited to model table references and the added publication-to-field-evidence relationship.

Final native key queries reconcile all 1,344 canonical publication keys and the 14-record retained monthly output key set. The existing 18-field canonical export interface is preserved. Completion is accepted for the saved-generation manual integration scope; recurring provider acquisition and production activation retain their existing gates.

Exact native IDs, source responses, model preimages/candidates, single-send intents, refresh/run receipts, reconciliation responses and rollback inputs remain in ignored private storage. Raw provider fields remain full source-attributed evidence; this increment preserves the existing 18-field canonical export interface.

The terminal private receipt is completion-receipt.json under private/ops/2026-11-02-publication-lock-recovery in the original checkout. Its supporting receipts separately establish SharePoint saved-byte equality, model archive byte equality, queryable field counts, canonical/monthly keys, successful flow execution, source-key uniqueness, zero replay admissions and final stopped-state restoration. Existing local test results were reused; native verification targeted the changed path.

Current implementation ownership is the publication-source-coverage chat and worktree at /Volumes/PortableSSD/GitHub/RIMS/publication-source-coverage. Its native scope is the existing isolated model's added publication-source tables, the selected ingestion flow, and newly created SharePoint enrichment files. Existing shared authentication pins and other source owners retain their scopes.
