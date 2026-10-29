# Canonical unattended output

`prepare_canonical_output.py` prepares an additive definition for the existing
monthly exporter. It preserves the registry snapshot actions, outer monitoring,
identity and recurrence. The canonical steps run after the existing snapshot
manifest verification, inside `Export_Run`, so their failure cannot produce an
outer whole-run success receipt. No collector, source refresh, registry update,
email action or new schedule is added.

Use the existing saved exporter and writer captures. Their SharePoint references
must match exactly; only the writer's pinned Power BI reference may be added.
The model query returns the existing 18 export fields. Independently queried
ordered keys and counts must match both the complete output and its monthly
selection. Duplicate or padded keys, blank titles, invalid source/precision values,
nested error envelopes and missing fields fail. Uncertain dates cannot allocate
a month, and corroborated month/day dates require a matching year and month.
An empty month is valid and produces a header-only CSV and empty HTML report.

```sh
.venv/bin/python scripts/prepare_canonical_output.py \
  --exporter private/ops/exporter-preimage.json \
  --writer private/ops/writer-preimage.json \
  --period-policy previous-completed-month-brisbane \
  --revision v1 \
  --output private/ops/canonical-output-package.json
```

The policy selects the previous completed calendar month in Brisbane once per
run. It does not change the model's reporting window or acquire newer data.
An explicitly selected `--reporting-month YYYY-MM` replaces the policy only for
a bounded historical/recovery package. September 2026 is a frozen verification
case, not the scheduled production default. Unknown publication months remain
in the full output and do not acquire an invented month.

The four canonical files and completion manifest have deterministic names bound
to month and explicit revision. Existing identical bytes are reused through reads
only. Different existing bytes are a conflict, including human edits; corrections
require a new revision. Missing files are created through the existing SharePoint
connector's `HttpRequest` operation with server-side `overwrite=false`. Only an
actual404 permits creation. A failed or uncertain POST is reconciled by reading
the exact path, never by repeating the POST. All four files are read back before
the manifest is created, and the manifest is read back last. Earlier accepted
outputs are not overwritten. The existing registry snapshot retains its own
per-run behavior; canonical replay does not imply the entire original flow is
write-free.

CSV keeps all18 fields and escapes formula-like/leading-control text rather than
prefixing every cell. Unicode-whitespace-prefixed formulas are conservatively
escaped too. HTML renders all raw field values with escaping and preserved
line breaks. Layout and CSV quoting may differ from the operator-run exporter;
field parity is the acceptance criterion, not identical old file bytes. Stored
bytes must exactly match the newly generated content.

## Verification and native boundary

Focused tests cover preservation, input/refusal cases, field expressions,
period policy, immutable creation/replay branches and deployment-plan limits.
The frozen1344-record full and14-record September inputs pass the existing
exporter's all-field CSV/HTML readback comparison using the generated field
expressions. The empty connector output is supported by retained successful
native response evidence. Restricted expression evaluation is not a native
workflow engine or proof of the new definition running.

The private package includes a complete candidate, source hashes, the original
clientdata for rollback and a plan limited to canonical actions plus the one
Power BI reference. It deliberately reports `deployment_ready=false`: a fresh
exact-target read must establish stopped state, complete inactive-run history,
no unowned draft and the permitted connection binding before native update.
The stopped-record helper forbids reference changes by default. Its explicit
`--canonical-contract` option accepts a JSON object containing `writer` (the
complete retained writer snapshot), `reporting_month`, `period_policy` and
`revision`. It rebuilds the complete candidate from the fresh exporter preimage
and requires exact equality before permitting the pinned Power BI addition.
Existing SharePoint credentials, wrapper, actions and schedule cannot change.
The plan pins the donor snapshot hash. Real stopped-state, draft and inactive-run
readbacks remain required; never fabricate these from the historical running
snapshot. Source compatibility does not prove current permission or execution.

One bounded native verification of the added path remains necessary after the
package is approved for that target. Check the saved definition and all four
stored outputs against independent model keys/fields, then unchanged replay.
Reuse unchanged snapshot/reader evidence. Natural recurrence remains separate;
the existing 1 November observation must distinguish registry-snapshot delivery
from canonical delivery until this addition is deployed and verified. This
source package does not authorize a run, activation or schedule change.
