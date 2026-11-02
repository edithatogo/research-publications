# CLI feature increment — 2 November 2026

Owner: completion chat `01a1876d-55fc-7e42-b806-18589a94e6fa`.
Source checkout: `/Volumes/PortableSSD/GitHub/RIMS/grants-feature-completion`,
branch `codex/grants-feature-completion`. This separate checkout preserves the
historical import's active closeout continuation in its original checkout.

- [x] Promote the retained watchlist lifecycle guard repairs with FlowAgent.
  Only the existing-owner/version and saved-owner guards changed. Native
  definition readback matches; Invoker binding, Started state and trigger remain
  unchanged. This is saved-definition acceptance, not a two-user runtime claim.
- [x] Implement the additive historical model/report reader builder. It reuses
  the model's existing SharePoint source and exact history list IDs, separates
  awards, closed opportunities and confirmed GA/GO pairs, and preserves original
  tables, relationships, report pages and binding. No inferred joins or amounts
  are added. Processing scope contains only the three new history tables.
- [x] One consolidated test invocation passed eight cases. One verification pass
  checked the saved watchlist graph and prepared the reader against retained real
  model/report captures. Private evidence is in this checkout under
  `private/ops/grants-features-20261102/`.
- [x] Save/process the historical reader natively from committed list rows. The
  selected 2 November deployment is independent of final import completion and
  labels the last-processed snapshot as potentially partial. Import membership
  acceptance stays with the existing import owner. Current deployment evidence:
  `private/ops/grantconnect-history-native-20261102/` in this checkout.
  Both native saves and the single three-table processing request succeeded.
  The processed snapshot has 220,124 award versions, 1,072 closed opportunities
  and 100,888 confirmed links. Thirty first/last source rows match retained fields;
  keys are nonblank and distinct. All 1,344 publication rows and 50 fields remain
  exact. All 70 protected model parts and 97 protected report parts are unchanged.
  See [deployment review](review-history-reader-20261102.md). Full historical
  import membership and visual rendering are not claimed by this CLI acceptance.
- [x] Implement and deploy current-operator live Outlook calendar synchronisation
  using existing authenticated preferences, calendar and private delivery ledger.
  One serial writer and three change-signal adapters are saved Started. Confirmed
  GrantConnect source days only; no invitations or reminders. Exact-calendar
  create/read/update/delete qualification passed after an encoding correction
  reusing the same fixture. A read-only full-worker execution succeeded with no
  active calendar follows and no provider/source writes. Private receipts:
  `private/ops/grants-live-calendar-20261102/` in this checkout. See
  [calendar review](review-live-calendar-20261102.md).
- [ ] Accept the complete opt-in/change/pause/unsubscribe ledger lifecycle and
  two-user access scope. The deployed current-operator route and isolated CRUD
  qualification do not establish these broader outcomes. No real follow was
  introduced for testing. G08-H05/H06 remain open for unaccepted scope.
- [x] Implement/deploy fixed-operator GrantConnect business notifications using
  the retained standard-connector sender, private preferences and delivery ledger.
  Native no-send qualification passed; reviewed record count and due email rule
  count were both zero. Final reviewed definition and references match Started
  readback. The old monitor excludes GrantConnect business candidates and retains
  its operational alerts/schedule. See [business review](review-business-notifications-20261102.md).
- [ ] Accept the first actual reviewed business-message receipt when a genuine
  reviewed GrantConnect record matches a saved due email preference. No source
  review was fabricated and no unsolicited test message or follow introduced.
- [ ] Connect institutional deadlines to an authoritative policy. None is
  inferred from the example lead times. Source closing dates remain unchanged;
  calculated dates without approved policy remain provisional.
  2 November: policy/override schemas restored; evidence-bound CLI preparation
  and native storage qualification pass. The live snapshot contains no approved
  authority-bound policy; all 85 anchors are held unchanged. Requested public
  CHHHS/QH research found no applicable numerical lead-time rule in accessible
  pages. Native append-only writer, date application and reader integration are
  still pending; this is not a deployed deadline feature. See
  [policy review](review-policy-deadlines-20261102.md).
- [x] Implement broader typed project relationships through the existing CLI,
  append-only journal and native reader. People, ethics, DoRA and opportunities
  now accompany publications, awards, datasets and software; legacy journal hashes
  and projections remain valid. Fifteen focused tests pass. The existing reader
  and page are saved/read back; bridge processing completed. All 1,344 publication
  rows and 50 fields, 169 reference candidates, 73 other model parts and 102 other
  report parts are preserved, with no new journal rows or schedules. See
  [relationship review](review-relationships-20261102.md).
- [ ] Admit actual reviewed person/ethics/DoRA/grant relationships once exact
  authoritative inventories and genuine reviewed evidence are available. The
  inspected native project journal contains one explicitly fictional publication
  candidate and zero reviewed links. Retained source assertions remain candidates;
  their filenames or source co-occurrence do not establish review. Existing 169
  publication-reference candidates remain accepted and unchanged; they are not
  proof of institutional funding or ethics approval. This data-admission item and
  G06-H01/H03 remain open; technical reader support does not close them.

No source refresh, import restart, scheduled-run check, schedule change, business
email, invitation or NIH activation occurred. CLI submission without waiting for
completion cannot establish successful runtime delivery or model processing.

Policy writer increment: `python -m scripts.grants_policy_append` prepares an
append-only manual FlowAgent definition for one evidence-bound policy version.
The existing unique policy key guards concurrent creation. Matching rows replay
through exact readback and conflicts fail. One focused test passed and FlowAgent
preflight returned ready using synthetic input. Native create and real policy
application remain pending. The override writer and date reader remain open.

The deadline application CLI now prepares a revision-specific override append
with live anchor and policy version guards and exact saved-content comparison.
It applies the approved policy and reviewed override to a dated model snapshot.
The internal deadline page exposes the source and internal dates, disposition,
version and snapshot day. Only approved, current inputs can supply an effective
date. One focused test covers override precedence and the missing-policy hold.
FlowAgent preflight passed on the standard SharePoint connection. A real override
write and the first approved institutional date require real reviewed inputs.

The manual application flow is deployed. Its 2 November native run matched all
four list version inventories and returned 85 held, zero planned writes. It
uses separate internal keys, conditional updates and explicit withdrawal when
a previously applied date loses its supporting policy. The reader publication
guard requires exact stored membership, revision and effective day for applied
dates. Evidence is retained in private/ops/deadline-application/.
