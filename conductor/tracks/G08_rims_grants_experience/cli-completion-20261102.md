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
- [ ] Save/process the historical reader natively after complete history is
  available. The builder's output is a candidate, not a populated native reader.
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
