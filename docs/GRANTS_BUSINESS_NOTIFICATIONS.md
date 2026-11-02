# GrantConnect business notifications

The existing operator's saved email preferences now have a dedicated unattended
GrantConnect sender. It reuses the established standard Outlook/SharePoint
delivery graph, existing private watchlist and delivery ledger. It sends only to
the fixed operator mailbox bound privately at deployment. Wider recipient or
multi-user delivery is outside this increment.

## Behaviour

- Reviewed GrantConnect records need current classification evidence and an
  active, server-owned saved email preference. Opportunity, funder and category
  follows are supported. The current operator timezone is Australia/Brisbane.
- Opportunity revisions, reviewed committed deadline changes/cancellations and
  explicit source-day reminder offsets produce typed event identities.
  Approximate/unknown dates do not produce precise reminders. Notice content
  links to the official source; deadline notices include its recorded calendar
  day. No eligibility or institutional-policy approval is inferred.
- Immediate preferences are evaluated every 15 minutes. Daily preferences run
  within the existing 08:00 Brisbane window; weekly preferences use Monday's
  08:00 window. These are functional notification evaluations, not additional
  monitoring or scheduled-verification jobs. Existing publication, intake,
  calendar and legacy-monitor schedules were not changed.
- Source/classification, saved preference ownership, active consent and exact
  source/preference/deadline versions are checked again immediately before send.
  Malformed classification or event/offset arrays fail closed. No caller-supplied
  recipient, report slicer or default template can authorise a message.
- One serial worker owns GrantConnect business notices. Overlapping follows and
  repeated evaluations share the same user/opportunity/event/revision/offset key.
  It claims the existing private ledger before sending, with no connector write
  retries. Existing claims never automatically send again. Ambiguous attempts
  receive receipt-only reconciliation rather than another send.
- The ledger row ID provides a unique, bounded subject receipt marker. Readback
  requires the exact subject, single intended recipient and appropriate mailbox
  folder. Sent-only evidence is `submitted`; absent evidence is `unknown`.
  Actual received evidence is separate from flow success. Delivered entries skip
  subsequent provider/ledger work, avoiding endless unchanged history growth.

## Source ownership and deployment

The older local monitor retains its exact operational email worker and hourly
schedule. Its private delivery configuration now excludes `GrantConnectRSS`
business candidates. The single existing runtime module was promoted at a
verified idle checkpoint, with its exact preimage preserved; other dirty files,
native bindings, environments and one-send journals were not moved or replaced.
The canonical module also retains the previously accepted classification-shape
hardening. Operational health alerts are unaffected by the business exclusion.

The new flow was created and updated using FlowAgent, reusing the qualified
connection identities. Its native identity, context, preimages, source ownership
cutover and final acceptance receipt are in ignored
`private/ops/grants-business-notifications-20261102/` in the feature checkout.
The original monitor's private configuration stays in its original checkout.
Never run a second GrantConnect dispatcher against this ledger or restore the
legacy source exclusion while the new worker remains enabled.

Prepare a new private candidate using the qualified repository Python 3.15.1:

```sh
<repo-python> -m scripts.prepare_grants_business_notifications \
  --context private/ops/<occurrence>/context.json \
  --output private/ops/<occurrence>/candidate.json
```

`--qualification` produces an input-free manual definition whose dispatch branch
is unconditionally disabled. It reads current list boundaries and eligibility;
it cannot send, claim or alter a preference. Preparation performs no native work.
Use FlowAgent for native authoring, preserving the recorded identity and refs.

Rollback disables only the new business worker. Keep the legacy exclusion until
an explicit single-writer cutover is ready; do not restore old business sending
blindly. Preserve all ledger entries and pending attempts. No source refresh,
review-state changes, schedule recovery or NIH activation is part of rollback.

## Acceptance and current data gate

The focused selection covered 13 business/legacy delivery cases. Two test-harness
errors were corrected and only those cases rerun. The review's affected action
dependency check also passed; no broad test rerun was added.

The single native no-send qualification succeeded. It found **zero reviewed
GrantConnect records and zero currently due own email preferences**. No message
or test subscription was introduced. Final native definition, Started state and
retained connections match the reviewed generator; the legacy source ownership
cutover matches its retained preimage plus the explicit exclusion.

The unattended implementation is deployed. A real business-message receipt is
not established by this qualification: it requires a genuinely reviewed record
and a matching saved email preference. Do not relabel the 120 retained Needs
Review records, fabricate a deadline/change or send an unsolicited test to obtain
that evidence. NIH remains on the inactive roadmap.
