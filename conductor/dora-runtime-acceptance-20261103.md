# DoRA continuation and failure/source-health acceptance — 3 November 2026

**Accepted for the existing safe fresh-restart contract.** Qualified CLI/FlowAgent reads and independent stored-byte comparisons close this collector's selected continuation and failed-generation visibility gap. Existing acquisition is reused; no new crawl, flow run, mutation, schedule change or notification was needed.

## Actual native evidence

- The31October scheduled generation failed after a real provider HTTP timeout in the after-membership scan at offset440. The failure flag was set; the complete-generation guard rejected the result. The durable failure receipt was saved, read and byte-verified, with `complete=false`, `accepted=false` and both completion write/readback skipped. This is actual provider-failure evidence, not a synthetic fault or a successful zero-result response.
- The1November scheduled generation retained exactly the same prior complete checkpoint lineage. Both current membership scans restarted at offset zero. All36 offsets per scan were contiguous through700; both complete key sets reconciled to709unique records, with709verified record-file references and72verified collection-page references. The stable-collection and completion-readback guards succeeded.
- Independent guarded SharePoint downloads match the native failure-receipt and recovered-completion readback bytes exactly. The prior complete marker remains readable and matches the same scope/count/run referenced before the failure and by the recovered generation. The failed generation did not replace it.
- The native run has an explicit failed terminal disposition and durable incomplete source receipt; the next complete generation is separately identified. This accepts native collector failure/source-health visibility and last-good preservation, not a new SourceRuns table, report-health display, alert-delivery route or every possible transport-error class.

## Continuation contract and limits

DoRA has no qualified versioned cursor or stable-offset contract. Cross-run page splicing and cached record reuse are therefore unsupported. The accepted continuation is a complete fresh restart after interruption, preserving previous accepted output until complete current before/after membership and raw-record guards pass. This closes the requested safe recovery path; it does not certify literal continuation at the failed offset or sitemap-based skipping.

The later current native preflight also observes successful subsequent scheduled generations and no active run. Final exact-target CLI readback preserves the original definition, connections, Started state, recurrence and failure-alert setting. No field, canonical key, export, register or model was changed.

## Receipts and focused checks

Private definitions, full action metadata, failure/recovery bodies, recorded offset resets, independent downloads/hashes, renewal receipt and terminal acceptance remain in the original native-owner checkout under `private/ops/2026-11-03-dora-runtime/`. The terminal result is `PASS_NATIVE_FAILURE_AND_SAFE_FRESH_RESTART`. Only the expired existing SharePoint workload was renewed through the pinned client; no new permissions or credentials were introduced.

No runtime source repair was needed. Existing acquisition tests were reused. The focused acceptance assertions checked native receipt parity, failed completion suppression, unchanged prior lineage, zero-offset restart, contiguous page/key coverage, unique records and complete manifest guards. Documentation validation remains separate from this native proof.

[Current flow backlog](flow-backlog-reconciliation-20261103.md) and [retrieval constraints](../docs/DORA_RETRIEVAL_EFFICIENCY.md) retain the distinction between accepted recovery and optional unqualified reuse optimisations. Other publication/grants/operating gates remain unchanged.
