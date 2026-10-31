# Native reader and grant-reference connection preparation

The frozen 61-part model already contains the retained PubMed/DoRA readers and
`CanonicalPublications` consumes them. The raw23 adoption flag describes runtime
acceptance, not missing reader code. No replacement reader is needed merely to
clear that flag. The working publication/export path remains unchanged.

The new feature connection is an additive `RetainedGrantReferences` table and a
many-to-one, single-direction relationship to `Publication.CanonicalKey`. Its
source is the existing immutable owner-only cloud artifact containing 169 candidate
grant references. No source collection, name matching, confirmed award admission,
new credential scope or replacement publication partition is introduced.

[The bounded preparer](../scripts/prepare_retained_grant_connection.py) consumes
independently pinned input bytes containing the complete frozen model, exact
artifact text and accepted cloud-upload receipt, and the existing target binding.
It checks artifact hash/length, candidate-only flags, unique evidence keys,
complete field inventory, existing model source and canonical-key dependency.
Its M source reuses `SharePoint.Contents` navigation, checks the selected file,
byte length, row scope and exact evidence-key set, and serializes source paths
without dropping them. Existing model properties and unknown parts are retained.

The output contains the candidate and the complete exact inverse. On the selected
frozen input it preserves 59 parts, changes only the model root and relationship
part, and adds one table: 61 parts become 62. Existing Publication columns,
expressions, reader definitions and report parts are untouched. The new source
has 169 rows; it does not replace or add canonical publications.

```sh
.venv/bin/python scripts/prepare_retained_grant_connection.py \
  --input private/ops/native-reader-preparation-20261031/input.json \
  --input-sha256 INDEPENDENT_INPUT_SHA256 \
  --output private/ops/native-reader-preparation-20261031/candidate-and-inverse.json
```

Run with the explicitly selected Python 3.15.1 interpreter. Real native identities,
cloud paths, payloads, source snapshots, target mapping and inverse stay ignored.
The current private packet is under
`private/ops/native-reader-preparation-20261031/`; its receipt is
`PASS_OFFLINE_NATIVE_CONNECTION_PREPARATION`, SHA256
`784ebf61d87ed56ec368c3a42a84324bda5dc64572c585493b51e8fe3f7c5aee`.
One focused invocation of `tests.test_prepare_retained_grant_connection` passes
two tests; one offline packet comparison establishes the exact delta/inverse.
Existing reader/consumer/native checks were not repeated.

## Preparation boundary

The candidate is **prepared, not deployed or deployment-ready**. The complete
18-field CSV does not represent the larger native Publication schema, and the
frozen model does not establish current live state. The packet explicitly retains
these unresolved deployment inputs:

- Exact current model identity, complete preimage, drift check, supported write
  operation and inverse ownership; do not substitute the separate funding model
  or unresolved T18 reader.
- Exact cloud file identity/version and full-byte hash guard. M length/key checks
  alone do not prove byte identity; reuse the accepted immutable receipt only
  while its target/version remain unchanged.
- Current native Publication keys and complete relevant model field context;
  never invent missing fields or capability receipts from the CSV.
- Native M execution and relationship filter behavior after any authorised save.

No native call, refresh, deployment, source request, schedule change or flow run
was performed for this preparation. The existing 1 November observation is
preserved. Optional DoRA activity, wider relationships, freshness, source expansion,
collaboration, redesign and outcomes work is not commissioned by this packet.
