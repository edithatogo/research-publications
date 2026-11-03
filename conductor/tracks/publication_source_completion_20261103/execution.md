# Execution and evidence — 3 November 2026

## Current acceptance

The [native quota checkpoint](../../../docs/SEMANTIC_SCHOLAR_NATIVE_CHECKPOINT_20261103.md) remains accepted; no new native write has occurred during recovery. Its original private completion receipt is `private/ops/2026-11-02-semantic-scholar-full/completion-receipt.json` in the original checkout. It proves archive bytes, per-field counts,4,032 unique source/publication pairs, canonical/export preservation, a successful ingestion run and restoration. This is not a zero-deferred completion receipt.

## Recovery

Both recorded old PIDs were absent. The two owned lock directories and their original owner files were moved intact into `private/ops/2026-11-03-semantic-scholar-recovery/preserved-stale-lock-*`. The recovery receipt records zero authentication/native-lock changes. A cache-resuming CLI attempt made exactly one provider request and returnedHTTP429 at12:44 Brisbane. Counts remained unchanged. Its complete response and headers are saved in `collection.log` and `coverage-after-recovery.json`.

The14-case retained-evidence review made zero provider requests and zero canonical writes. Twelve records lack usable identifiers in the frozen canonical record and accepted Europe PMC/OpenAlex evidence; one DOI cell contains a title. Two DOI matches return conflicting PMIDs. Preserve all14 with explicit decisions; this is not an automatic canonical data-correction task.

The recovered collector is in a verified live cooldown, next permitted attempt13:46 Brisbane3November. A single recovered continuation is waiting for complete collection. Live process receipts and session handles are retained privately; recheck them before asserting current activity. A lock/state file alone is not liveness proof. No schedule/recurring automation or login was created.

## Current blocker

Scope: anonymous Semantic Scholar lookup collection,45 deferred PMID-only identifiers. Evidence: repeatedHTTP429, latest bounded attempt3November; no Retry-After header. Unblock condition: the same public single-record route permits requests after cooldown. No new client, key, login, URL rotation or provider-limit bypass is selected. Dependent native tasks remain unchecked. Continue independent retained-evidence/documentation work and reuse unchanged checks.

## Source packet and native ownership

The source packet is on `codex/publication-source-coverage`, not a main merge. Current chat owns the collector/cache and the exact existing isolated model four-table/ingestion-flow scope. Native bindings/journals remain in the original checkout; other dirty source work is preserved. Earlier stopped operations and accepted receipts remain history. Conditional providers and the original standalone source draft retain their existing owners/gates.

## Source packet checks

The24-task/metadata/link check passed, with final native acceptance explicitly incomplete. Project validation passed446 checks with zero failures. No collector, model-reader or flow-definition source code changed in this packet; accepted focused source tests, full milestone and web-first receipts were reused. No broad unittest rerun was needed for Conductor/documentation edits. Only the selected Conductor leaf, its index/register pointers and owned coverage report are committed; no original-checkout files are staged.
