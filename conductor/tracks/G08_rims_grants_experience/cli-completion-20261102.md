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
- [ ] Complete business notifications and live calendar subscriptions. Existing
  notification/delivery/ICS logic remains reusable; an ICS snapshot does not
  establish an authenticated revocable live subscription. The selected recipient,
  cadence and exact calendar destination must be bound before delivery.
- [ ] Connect institutional deadlines to an authoritative policy. None is
  inferred from the example lead times. Source closing dates remain unchanged;
  calculated dates without approved policy remain provisional.
- [ ] Expand reviewed project/person/ethics/DoRA/publication links from actual
  identifiers and evidence. Existing 169 publication-reference candidates remain
  accepted; they are not proof of institutional funding or ethics approval.

No source refresh, import restart, scheduled-run check, schedule change, business
email, invitation or NIH activation occurred. CLI submission without waiting for
completion cannot establish successful runtime delivery or model processing.
