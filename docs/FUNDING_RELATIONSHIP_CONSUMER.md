# Funding relationship consumer

This selected G06 consumer reads the exact existing relationship list through
the model's existing SharePoint.Tables resource. Every native row is retained.
The register supplies current review, confidence, evidence and modification
values at an operator-run targeted refresh. This is an Import snapshot, not
instantaneous live review state or a new unattended schedule.

The accepted reference packet supplies identity material only: the actual
registry keys, exact model/award crosswalk and registered typed relationship
hashes including their evidence URL. Three-field left joining preserves identity
context even when typed validation fails; six-field matching admits only a
registered typed identity. Raw unknown, padded, withdrawn and unresolved records
remain visible as unclassified or unresolved, with their original values retained.
New or changed evidence requires identity-material regeneration and a supported
model update. It never silently overwrites review state or disappears.

Candidate and confirmed-reviewed admission are distinct positive rules. Current
model publication/award membership and exact award code are required; a withdrawn
award in the imported ARC source cannot support a confirmed-reviewed link. ARC
status and acquisition time remain retained-source context, not live ARC access
or institutional attribution. Candidate links do not create funded-publication,
award-amount or eligibility measures.

Two single-direction dimension-to-bridge relationships support existing readers
without filtering or multiplying publication/award facts in reverse. Preserve
the full existing model, source values, connections and disabled schedule. Refresh
only the new bridge after qualified same-ID deployment; compare complete native
IDs, review/evidence and classification with the authoritative source capture.

SharePoint.Tables may expose evidence as text or a URL record and may omit native
ETags. The reader retains the observed raw JSON shape and labels missing ETags;
it never invents a version or treats Modified as source freshness. The original
list and its version history remain authoritative and are linked from the reader.

Native source/refresh, model preservation, report interactions and reviewed
companion integration are separate acceptance gates. Preparation and focused
source checks alone do not establish those native outcomes.

## Incremental receipt connection — 29 October 2026

The G06 incremental worker now passes native-verified delivery rows and accepted
source context to the existing consumer preparer before advancing its processing
checkpoint. It writes `rims-consumer.json` and records its hash in the final
`receipt.json`. Raw native review, confidence, evidence, ETags and unmapped rows
are retained. Repeated identical source context collapses for identity matching
while every source/hash occurrence remains in provenance. Removed source evidence
does not delete native relationships or change human review.

The CLI adapter calls the existing consumer preparer unchanged:

```sh
.venv/bin/python scripts/connect_g06_rims.py \
  --processing-receipt private/ops/selected-delivery/native-delivery.json \
  --baseline-consumer private/ops/accepted-consumer.json \
  --output private/ops/selected-delivery/rims-consumer.json
```

`--processing-receipt` accepts only a completed native-delivery stage or a final
delivered checkpoint with verified native rows; it refuses prepared/failed jobs
and snapshot overrides. Outputs are exclusive private files with mode `0600`.
The baseline is optional and hash-bound by the incremental job when supplied.
`identity_update_required` compares material with that supplied baseline; a false
value does not prove what is currently deployed in Power BI. No baseline yields
an explicit unknown value. Changed material requires the existing isolation,
definition/binding preservation, targeted refresh and cardinality gates.

The intermediate `g06-native-delivery-verified-v1` stage can prepare the consumer
but cannot serve as an incremental checkpoint. Only after consumer preparation
passes does the worker write `g06-incremental-delivered-v1`. A local consumer
failure preserves native acceptance and journals without advancing the processing
checkpoint. No model write, report edit or refresh is performed by preparation.

Source tests pass. The actual new incremental/native/RIMS cycle remains pending
the existing shared-lock exception and the exact publication-source pin/readback.
The retained 29 October writer readback prepares two candidates and zero confirmed
rows, with identity material matching the accepted baseline. This is a dated
retained-evidence comparison, not a new live refresh or deployed-model readback.

## Native integration lesson — 18 October 2026

The same-ID 53-part definition save succeeded. Its first transactional bridge
refresh failed with `DMTS_MonikerWithUnboundDataSources`. Item-connection readback
showed all four existing references unbound, although datasource enumeration and
existing imported publication queries still succeeded. Those observations prove
source references and retained data, respectively; neither proves refresh binding.

Before a post-definition refresh, compare item connections with the last accepted
binding receipt. Restore only exact existing connection IDs, types and paths through
the supported binding API, then read back every binding. Keep personal/shareable
connection kinds and privacy settings unchanged. A failed tool exit remains a
failed gate even if its body contains HTTP 200: reconcile that specific effect
read-only before any dependent action or resubmission. Retain the original failed
refresh receipt; retry only after the observed binding cause has changed.

This adds a binding-preservation step to the existing deployment sequence, not
new credentials, consent or a new source. Actual bridge refresh and reader output
remain separate checks after configuration recovery.

After exact bindings were restored, a second refresh reached source discovery and
failed with `Premium_ASWL_Error`. The generic custom-connector message does not
justify installing a gateway: this consumer uses built-in SharePoint.Tables.
The bounded correction places its literal existing site URL in the partition's
source expression and passes the resulting table to the transformation function.
This preserves source scope and all classification logic. Five focused tests
passed; runtime success must still be established by the changed-source refresh.
The corrected definition preserved all four binding IDs on saved readback.

The literal-source correction completed a real bridge refresh. That operation
also returned a calculated-column warning: `Typed` was rejected as a DAX variable.
Renaming it to `RegisteredAdmission` preserved the admission logic. The subsequent
table-only transactional refresh completed without warnings. Native queries returned
2 current candidates, 0 confirmed-reviewed and 0 unresolved/unclassified, with
publication and award totals 1,341 and 34,977. Evidence URLs arrive as text, version
as `1.0`, and ETags are not exposed; the availability label reports that honestly.

Treat refresh messages and calculated-column/measure queries as part of output
proof even when refresh status is Completed. Source generation checks cannot
validate the service's M source discovery or DAX parser. Apply these lessons in
the existing native happy-path step before report and package integration.

## Existing ARC reader

The existing ARC page now includes a relationship admission slicer, separate
candidate/confirmed/unclassified counts, and a relationship table with current
register review/confidence, retained ARC status, publication/ARC/register/evidence
links and provenance. Scroll right for the register read time, ARC acquisition
time, raw modification text, version and explicit ETag availability. Raw connector
modification text has no timezone; it is not labelled UTC. This adds no page and
preserves the eight other pages and existing award query.

Native verification passed: all 34,977 awards with 2 candidates/0 confirmed;
candidate admission leaves the award total intact; selecting LP140100020 shows
1 award/1 candidate; reset and reload restore both candidates. All four child
link columns navigated to their intended URLs. This proves navigation, not
external source availability or business review. Saved visual dictionaries match
the submitted page by stable name; the service only reordered their array.
Three focused reader checks and schema validation passed; native screenshot
review found no overlap or rendering errors. The maintained overview is now version11.0 and the independently reviewed R17b
companion is current. R16 remains preserved as its accepted predecessor.

## Reproducible handover lesson

The first R17 assembly stopped before archive or pointer changes because the
shared typed relationship normalizer was absent from Git and the prior package.
Its only local dependency imports `OPPORTUNITY_KEY_PREFIXES` from the registry;
that constant was also missing from the tracked registry revision. Version the
unchanged normalizer and add only the existing constant to the tracked registry,
preserving unrelated working edits. Future package preparation must walk this
selected import chain before sealing and include builder/test dependencies.

R17 retains its explicit frozen source revision and exact local registry snapshot
under `DirtyBuild`; the later minimal Git import repair does not rewrite that
historical archive. A sealed source snapshot, later repository closeout, and
native runtime acceptance have separate identities. Record them explicitly rather
than silently resealing an accepted package for a later documentation repair.
The native overview is now11.0/seven diagrams, with prior10.0 history exact.

The integration milestone also requires registering a newly accepted M runtime
file in the existing additive runtime manifest. The first full run correctly
flagged the unregistered bridge function; no previous runtime file had changed.
Bind that one added file to its reviewed Git/native bytes, retain the historical
baseline hash, then rerun the required integration check. Do not refresh a frozen
baseline wholesale or loosen validator coverage to hide a legitimate addition.

The first sealed R17 candidate retained the older source additions manifest.
Independent review caught that the packaged contract omitted the new M function,
even though the repository recheck passed. Preserve the unpromoted candidate and
rebuild from the predecessor with the exact committed manifest repair included.
Check the source contract inside the sealed archive, not only the working tree;
advance pointers only after the corrected archive's own reviews pass. This is a
material reproducibility correction, distinct from later closeout-only records.


## Reviewed R17 closeout — 18 October 2026

The final R17b archive includes the small145-file reviewed authored-local runtime
baseline, its existing three contracts and unchanged drift guard. Running that
guard from an isolated extraction passes exact equality; these local authored
files are labelled separately from the current native53-part model and9-page
report. Archive-only model and reader reconstruction also passes. The initial
and intermediate unpromoted candidates remain preserved with their findings.

All1,912 manifest hashes, CRC, predecessor history and selected native companions
pass parent and independent reviews. Three current-package pointers read back
SHA256 `88bd5c346b250bf1e7f0f51b017c1e97969f343fc148d29049f7e2ad1bed5684`.
The required repository integration run passes1,892tests/eightskips after the
exact additive registration repair; this is separate from packaged guard and
native output proof. Frozen source6adba4b and later repository closeout retain
separate provenance. Whole-platform acceptance and production remain unqualified.

For the next selected increment, check transitive imports and the included source
contracts before sealing, then run existing guards against the actual extraction.
Retain exact bindings after definition changes, keep source calls discoverable,
inspect refresh warnings and query calculated outputs before reader integration.
These checks support the existing implementation steps and do not create a new
commissioning framework or operational review gate.
