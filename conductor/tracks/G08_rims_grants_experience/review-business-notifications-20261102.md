# Review Report: Business notifications

## Summary

The fixed-operator GrantConnect sender is deployed with current-evidence,
private-consent and one-send guards; real business receipt remains data-gated.

## Verification Checks

- [x] **Plan Compliance**: Yes for current-operator business implementation;
  existing planner/worker/ledger reused, NIH inactive and prior schedules intact.
- [x] **Style Compliance**: Pass — standard-library generator, parsed native
  definitions, private identities and exact preimages retained.
- [x] **New Tests**: Yes — seven feature cases plus six existing delivery cases.
- [x] **Test Coverage**: Partial — deterministic ownership/boundary contracts,
  legacy compatibility and native no-send execution; no real grant receipt claim.
- [x] **Test Results**: Passed — two test-harness errors corrected with affected
  reruns only; final affected action-dependency check passed after review fixes.

## Applied fixes

1. Resolve sender ownership explicitly. The ledger's Title is indexed but not
   unique, so the legacy monitor excludes GrantConnect business candidates while
   keeping its operational alerts. No competing business writer is introduced.
2. Reuse claim-before-send and receipt-only recovery, preserving attempt identity
   and source/preference/deadline ETags. Bind preference AuthorId and fixed mailbox.
3. Use the native ledger ID for a bounded exact receipt marker; require the exact
   intended recipient. Skip completed deliveries on unchanged evaluations.
4. Parse classification and preference arrays against explicit schemas, preserve
   uncertainty and evaluate reminder offsets only for reminder events. This avoids
   null comparisons on opportunity notices and malformed category matching.
5. Constrain CLI output to new ignored private paths and preserve the original
   runtime/configuration preimages during the bounded idle cutover.

## Native result and limits

The single manual no-send qualification succeeded: zero reviewed GrantConnect
records and zero due own email rules. Dispatch was unconditionally disabled;
no email, preference, source or ledger write occurred in that run. The reviewed
live definition is saved Started with exact retained connection identities.

Actual business-message receipt, a real changed provider deadline and multi-user
acceptance are not inferred. Data review and saved user preferences must remain
genuine. No scheduled occurrence was checked, source refreshed or existing
schedule changed. See [notification contract](../../../docs/GRANTS_BUSINESS_NOTIFICATIONS.md).
