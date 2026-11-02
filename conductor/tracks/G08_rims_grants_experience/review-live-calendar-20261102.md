# Review Report: Live calendar subscriptions

## Summary

Current-operator calendar synchronisation is implemented and saved through
FlowAgent; whole-track and multi-user acceptance remain separate.

## Verification Checks

- [x] **Plan Compliance**: Partial — current operator, confirmed GrantConnect days,
  existing preferences/ledger/calendar; no public feed or institutional policy.
- [x] **Style Compliance**: Pass — standard-library builder, private native pins.
- [x] **New Tests**: Yes — seven focused source-day/ownership/withdrawal/uncertainty
  and native-boundary regression cases passed in one unittest invocation.
- [x] **Test Coverage**: Partial — deterministic decisions and prepared graph;
  exact-calendar create/update/delete qualified natively, no multi-user claim.
- [x] **Test Results**: Passed after correcting the native marker URL encoding.
  The failed first attempt created one temporary event; continuation reused and
  removed that exact event. No repeated create or existing-event mutation.
  One affected adapter test passed after adding registry-classification signals.
  The live-reader worker execution succeeded behind a no-active-opt-in guard;
  its file-change trigger was restored afterwards.

## Applied fixes

1. URI-encode extended-property braces to prevent Outlook connector substitution.
2. Keep action names unique case-insensitively and explicitly bind the retained
   SharePoint reference when promoting the Outlook-only qualification flow.
3. Re-read preference/source versions before provider changes; protect human
   edits with change keys and conditional provider writes; retain pending attempts
   without automatic reposts.
4. Keep unknown source/classification separate from explicit withdrawal. Exclude
   approximate/ongoing deadlines, invitations and reminders. Coalesce three
   source signals to one serial provider writer and skip untouched rows.

## Remaining acceptance boundary

No actual calendar follow was introduced. Automatic source-change propagation
and the complete saved-follow/ledger/pause lifecycle are not established merely
by native definition readback or the isolated CRUD qualification. Keep G08-H05
and H06 open for any unaccepted scope; no scheduled checks or new monitor are
introduced. Source and native details: [calendar contract](../../../docs/GRANTS_LIVE_CALENDAR.md).
