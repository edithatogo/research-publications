# Personal live calendar synchronisation

The current operator can use the existing authenticated watchlist lifecycle to
follow an opportunity with `Channel=calendar`. Saved subscribe/resume, pause and
unsubscribe changes drive the operator's existing Outlook Calendar. This is
direct authenticated synchronisation, rather than a public subscription URL or
a one-time ICS import. Other users' calendars are outside this deployment.

One serial worker owns managed Outlook events. Three small SharePoint adapters
signal preference, source-calendar and registry-classification changes through
the owned `rims-calendar-sync.json` file in the existing reporting folder.
Signals coalesce; the worker reads current lists rather than trusting an old
trigger payload. Each connector polls for changes every five minutes. This is
functional change delivery, not a scheduled-verification monitor. Existing
publication and historical-import schedules are unchanged.

## Event behaviour

- Only committed, canonical GrantConnect source deadlines marked `Reviewed` or
  `Source confirmed` are eligible. Official source URLs must match the registry.
  The explicit source calendar day produces an all-day, private, free event.
  Exact closing times remain on the linked official page. Ongoing and uncertain
  dates receive no fabricated day or reminder.
- Opportunity follows can use source-confirmed closing days. Funder/category
  matching additionally requires current, reviewed classification evidence.
  Unknown classification holds existing entries rather than treating it as an
  unsubscribe. Overlapping follows produce one logical deadline event.
- A managed marker and ledger bind user, exact calendar and deadline identity.
  A changed title/day updates the same provider event. Pause, unsubscribe or
  explicit cancellation removes only that user's managed event. Re-follow after
  removal starts a new persisted attempt. Unchanged replay performs no writes.
- No attendees, invitations or email actions are used. Reminders are off.
  Existing events with attendees cannot be changed or removed by this worker.
- Before a provider write, current preferences and source versions are read
  again. Updates/deletes use provider ETags. Changed provider change keys stop
  automatic overwrites, preserving subsequent human edits.
- The existing private delivery ledger records the pending attempt before the
  provider call and appends its outcome after readback. Writes have no automatic
  transport retries. A pending/ambiguous attempt stops further writes for that
  identity; retain its receipt and reconcile it explicitly before resuming.
  History capacity and incomplete/paginated reads fail visibly rather than
  truncating evidence or creating duplicates. Missing source/calendar rows do
  not imply withdrawal: retain the event for explicit reconciliation.

## CLI preparation and native ownership

Use the existing qualified Python 3.15.1 interpreter from the completion
checkout; do not replace its environment during the historical import.

```sh
<repo-python> -m scripts.prepare_live_grants_calendar \
  --context private/ops/<occurrence>/context.json \
  --output private/ops/<occurrence>/packet.json
```

Context pins the existing site/lists/library/folder, existing SharePoint and
Outlook connections, current operator and exact owned calendar. Output must be
a new ignored private file. Preparation performs no native operation. Use
FlowAgent to save the worker and three adapters, preserving their recorded IDs
and references. Native identities, definitions, preimages and terminal receipts
are retained in `private/ops/grants-live-calendar-20261102/` in the feature
checkout; no identity, token or private calendar URL belongs in source control.
Disable only these owned flows for rollback; preserve source rows, preferences,
ledger history and existing business schedules. Never recreate a flow to bypass
an uncertain write. Reconcile or remove only exact owned event identities.

The [standard Outlook connector](https://learn.microsoft.com/en-us/connectors/office365/)
provides the calendar API route. The worker uses the supported
[calendar events endpoint](https://learn.microsoft.com/en-us/graph/api/calendar-post-events?view=graph-rest-1.0),
with an [extended-property marker](https://learn.microsoft.com/en-us/graph/api/singlevaluelegacyextendedproperty-get?view=graph-rest-1.0).
The marker's braces must be URI-encoded in lookup URLs: otherwise the connector
interprets the GUID as a substitution variable.

## Acceptance scope

The bounded qualification created one clearly labelled temporary private/free
all-day event in the exact operator calendar. After correcting the marker URL
encoding, its continuation found the same event, updated it in place, deleted it
and confirmed marker absence. No second event or invitation was created.
Seven focused local tests passed. Review fixes include encoded marker queries,
case-insensitive action-name uniqueness, explicit SharePoint connection binding,
source-version guards and skipping provider lookups for unfollowed/unmanaged rows.
A subsequent read-only execution of the worker's actual live-list graph passed
with an explicit guard requiring no active calendar opt-ins. It performed no
source/provider writes. The production file-change trigger was then restored.

Saved-definition acceptance and this exact-calendar CRUD qualification do not
claim multi-user delivery, scheduled-run observation, public feed support or
notification/reminder delivery. Full opt-in-to-ledger lifecycle acceptance must
be recorded separately from the bounded qualification; no real follow is added
merely to obtain a test result. NIH stays on the inactive roadmap.
