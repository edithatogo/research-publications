# Review Report: Native GrantConnect historical reader

## Summary

The additive historical reader is saved and processed in the existing isolated
model/report, with explicit partial-snapshot wording and protected publication data.

## Verification Checks

- [x] **Plan Compliance**: Yes for the selected native snapshot reader. The
  separate import's full-population comparison remains with its existing owner.
- [x] **Style Compliance**: Pass for the changed source and page.
- [x] **New Tests**: Existing focused regression extended for the coverage label
  and entity-specific headings; no duplicate test framework.
- [x] **Test Coverage**: Targeted source boundaries, additive parts, source binding,
  native M processing, preserved publication data and historical field samples.
- [x] **Test Results**: One focused invocation passed; one consolidated native
  verification pass completed, reusing successful receipts after local assertion
  handling was corrected. No completed native query or processing was repeated.

## Findings

### Medium — Snapshot coverage was ambiguous; fixed

- **File**: `scripts/prepare_grantconnect_history_reader.py`
- **Context**: Import continues independently. The heading must not imply a
  complete historical population merely because the reader has been deployed.
- **Applied fix**: The saved page explicitly says it is the last processed list
  snapshot and may be partial while historical import continues.

### Medium — Entity headings were missing; fixed

- **File**: `scripts/prepare_grantconnect_history_reader.py`
- **Context**: The three tables share identifier columns but represent different
  entities and grains.
- **Applied fix**: Visible headings distinguish award versions, closed or archived
  opportunities and confirmed award-version/opportunity identifiers. No inferred
  relationships or monetary totals were added.

## Native result and limits

The model has 74 parts and the report 103. All 70 protected model parts and 97
protected report parts remain unchanged; page order adds only GrantConnect history
and preserves the existing landing/binding. One transactional request processed
only the three new tables, completed on its first attempt, and loaded 220,124 award
versions, 1,072 closed opportunities and 100,888 confirmed links. Each table has
distinct nonblank keys. Thirty first/last records match retained identifiers,
titles and evidence hashes. All 1,344 publication rows and all 50 fields remain exact.

The local PBIR validator reports 70 pre-existing errors and 10 warnings in the
retained report; none identifies the added history page. This is not a claim that
the whole report passes that validator. The native save and targeted data checks
passed. Visual rendering was not checked during the CLI-only deployment.

The interruption left the first model send without a terminal receipt. A bounded
recovery read proved the model still matched the exact preimage before a separately
journalled replacement. Its operation succeeded. The retained helper's attempt to
retrieve a nonexistent write-result body was corrected without repeating that
successful save. DAX serialized an empty COUNTROWS as null; that assertion was
corrected against the frozen successful count response without rerunning it.

Native receipts, inverse definitions and the single processing handle remain in
ignored `private/ops/grantconnect-history-native-20261102/` in the feature checkout.
No provider acquisition, import restart, schedule change, business send, sharing
change or NIH activation occurred. G08's other features remain open.
