# Semantic Scholar native bootstrap — 2 November 2026

The retained Semantic Scholar response is verified in the existing SharePoint destination and isolated RIMS model. This is a quota-labelled bootstrap, not a complete Semantic Scholar collection. Its frozen manifest has one match, 1,331 deferred publications and 12 missing identifiers. Anonymous collection has resumed separately, with three-second pacing, hashed caches and increasing backoff on HTTP 429.

The full bibliography has 1,344 canonical publications. The 1,332 publications with identifiers share 1,329 distinct provider lookup identifiers; three duplicate requests are avoided without merging canonical publications. Exact DOI matching and the independent PMID conflict check determine admission. Ambiguous responses remain candidate evidence rather than publication field values.

## Native acceptance

- All 81 source pages, including the 27 new bootstrap pages, reconstruct exactly from the model's byte-preserving archive table.
- All 4,032 source/publication dispositions reconcile to the frozen combined report. Per-publication field-presence counts match over 140 Europe PMC, 232 OpenAlex and 42 populated Semantic Scholar field paths. All 20 requested Semantic Scholar parent fields are populated in the retained response; nested records, arrays, original response evidence and observation dates are retained.
- All 1,344 canonical keys and their 18 export values remain exact. The retained monthly set remains 14 keys.
- The existing native ingestion flow succeeded. Its evidence output explicitly labels Semantic Scholar collection incomplete. It selected zero admission candidates and verified 1,348 existing source keys were unique. Existing aliases and legacy rows were preserved.
- The original recurrence and stopped state were restored with exact definition and connection-reference readback. No interactive login, schedule activation, report layout or sharing change was performed.

The first combined refresh failed because the row reader expected Europe PMC-specific metadata on other providers' rows. The transactional refresh preserved prior data. `MissingField.UseNull` repairs the three heterogeneous row readers; the subsequent four-table refresh completed and all field/value/archive checks passed.

The guarded Toolkit SharePoint session requires human renewal and was left untouched. The already-qualified flow's existing SharePoint connection performed the uploads, and the model's existing SharePoint reader independently verified their saved bytes. This does not renew or bypass the Toolkit session. Manual-trigger transports rejected runtime input bodies before execution; the qualified bodyless management route succeeded with fixed, validated cache inputs.

## Resume and evidence

Use `scripts/collect_semantic_scholar_publications.py --transport single` with the existing canonical envelope, retained bootstrap and cache. Completed responses are reused by exact request scope and SHA-256. `--replay-only` performs no provider calls. The active one-task controller retains the next allowed request time and uses 15-minute, 30-minute and one-hour cooldowns, honouring longer server instructions.

`scripts/stage_semantic_scholar_native.py` normally rejects deferred collections. Its explicit `--quota-bootstrap` mode requires retained HTTP 429 evidence, at least one matched record and a visibly incomplete coverage label. Staging performs no native writes. It preserves old archive hashes, checks identity and field coverage, and changes only the four existing source-reader parts. A full generation needs a new output directory and fresh native preimages; preserve the bootstrap receipts.

Private receipts under `private/ops/2026-11-02-semantic-scholar-native` in the original checkout separately establish native save, completed refresh, archive bytes, field counts, canonical/monthly exports, run outputs and final restoration. `bootstrap-completion-receipt.json` accepts only this bootstrap. The full collection and its final native promotion remain pending. Wider institutional/public-use rights and conditional provider feeds retain their existing gates; no standalone source draft was activated. Versioned narrative SharePoint/Loop documentation remains pending the final generation; the native run saved its machine-readable coverage/uniqueness artifact.

Focused tests cover retained-byte integrity, strict identifier matching, no-match caching, throttling and replay, default rejection of incomplete collections, and explicit quota-bootstrap labelling. Required project and web-first checks passed. The 2,473-test milestone encountered 138 host temporary-volume errors; the 85 affected methods were replayed, with the single outside-Git fixture replayed in an external temporary directory. All remaining cases passed; 19 existing capability skips remain. Source-specific reader repair checks also pass.
