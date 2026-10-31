# Additive grant-reference reader integration

The authorised feature connects the existing 169 candidate grant references to
the existing model/report. The model candidate and exact inverse are in
[native connection preparation](NATIVE_READER_CONNECTION_PREPARATION_20261031.md).
The direct reader adapter is `scripts/prepare_retained_grant_report.py`; it does
not use the broader `SourceRelationshipEvidence` report-builder contract.

The page adds a canonical-publication-key selector and an evidence table with
publication title, PMID, source-scoped grant label/identifier, identity/review
state, source URL/version, source paths and evidence key. It labels references
as candidates rather than confirmed funding. Canonical keys avoid ambiguous
title-only selection. The report binding, active page, existing pages/visuals and
unknown files are preserved; only page order changes and one page is appended.

## CLI sequence

1. Resolve the current report's dataset/workspace binding with the existing
   Fabric CLI. Read complete current report/model definitions and the native
   Publication field/key snapshot, plus exact artifact identity/version. No
   substitute target, fresh source collection or new credentials are allowed.
2. Rebuild the model packet from those current inputs through the existing
   preparer. Use `powerbi-report-author unpack` on the report capture; run the
   reader adapter with its exact capture digest/model ID; use
   `powerbi-report-author pack --mode update --raw` for transport. Keep the
   frozen packet as reference only, not a current deployment preimage.
3. The one focused invocation is
   `.venv/bin/python -m unittest tests.test_retained_grant_report_integration -v`, under the
   explicitly selected qualified repository Python 3.15.1 interpreter. Two tests
   pass: additive page/field/filter preservation and fail-closed drift rejection.
   Existing model/archive/consumer checks are reused rather than rerun.
4. Native promotion remains after the existing 1 November observation. Prepare
   complete same-ID update/recovery bodies with `deploy_report_definition.py`.
   Submit each authorised update once through `fab api`, with the appropriate
   skill header; retain each LRO ID and poll that operation rather than resend.
   Process only `RetainedGrantReferences` through an exact qualified table-only
   operation. No full model/source refresh, report rebind or schedule change.
   Do not deploy a report pointing to an unprocessed/missing table.
5. One consolidated verification episode consumes saved definition readbacks,
   terminal processing status, all 169 persisted edge fields and provenance,
   67 mapped publication keys, unchanged 1,344 canonical keys/protected fields,
   and one publication-key filter result. Compare complete report parts/binding
   and all unchanged model parts against the current preimages. Use the existing
   accepted immutable artifact and replay receipts while their inputs match.
   Within this same episode, validate the edited PBIR, load it with the CLI
   service preview, capture/review the new page and close owned preview resources.
   Rendering is not inferred from a schema check or DAX result.
6. An uncertain write is reconciled before another mutation. Failed deployment
   uses the complete exact inverse through the supported route; a callback,
   permission, table-processing or current-schema blocker remains explicit.
   Source integration does not establish native feature completion.

## Current bounded source result

The source owner used the retained 75-part report and prepared model to assemble
and pack an offline reader candidate. This is a reproducible deployment bundle,
not a saved native report. Installed routes: Fabric CLI 1.8.0 and report-author
0.5.0. Its service preview host reports screenshot support; Desktop is unavailable
on this Mac. The exact-target CLI read currently waits on the existing Fabric
sign-in callback. No duplicate login, cache transfer or native write is used.

Private source inputs, packed candidate, auth/preflight process state and current
receipts stay under `private/ops/grant-reference-integration-20261031/`. The
owner retains the pending callback and scheduled-baseline boundary. The existing
1 November verification, exporter and monitor are unchanged. Wider relationships,
freshness, provider expansion, notifications and other optional features remain
deferred.
