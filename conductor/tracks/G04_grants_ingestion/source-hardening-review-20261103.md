# Review Report: broader source/platform hardening

## Summary
The historical-source comparator now rejects incomplete expected populations and paged native responses before issuing acceptance.

## Verification Checks
- [x] **Plan Compliance** Yes for the selected bounded source-integrity fix; broader native/platform hardening remains open.
- [x] **Style Compliance** Pass. Existing comparator and guarded read route reused.
- [x] **New Tests** Yes. Empty manifests and three native continuation spellings.
- [x] **Test Coverage** Focused negative acceptance regressions plus existing history builder/reader checks.
- [x] **Test Results** Four selected tests pass on repo-local Python3.15.1. Full integration suite result is recorded in the plan after completion.

## Findings
### High — Empty expected population could receive acceptance
- **File** scripts/grantconnect_history_verify.py
- **Context** An empty ready manifest could previously compare three empty lists successfully. The selected historical population requires awards, closed opportunities and links.
- **Suggestion** Applied. Require all three expected entity populations to be nonempty before native reads. Test verifies no native call and no acceptance file.

### High — Continuation metadata was ignored
- **File** scripts/grantconnect_history_verify.py
- **Context** A paged inventory/item response was consumed as a complete page. The ID-window reader could advance past a server-truncated window.
- **Suggestion** Applied. Reject nonempty @odata.nextLink, odata.nextLink or __next rather than certify partial reads. The caller must obtain complete bounded responses before rerunning; no native mutation/retry is added.

## Remaining boundaries and handoff

These source fixes do not recover missing original manifests or establish current
import completion. They do not claim provider freshness, natural monthly delivery,
native restoration or whole-platform acceptance. No native write occurred.

Owner is chat01a19f3f-5187-7c23-ac14-192cb93a5a26 in
/Volumes/PortableSSD/GitHub/RIMS/dependency-qualification-20261103.
Owned source paths are scripts/grantconnect_history_verify.py and
tests/test_grantconnect_history_verify.py, plus this review and G04 plan entry.
Earlier local review work and native owners are preserved. Changes remain local
and unstaged under the supplied review skill's explicit commit boundary.
