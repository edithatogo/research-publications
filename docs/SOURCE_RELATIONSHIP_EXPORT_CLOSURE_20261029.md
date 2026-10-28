# Typed candidate relationship evidence export

29 October 2026. Sole source owner is relationships replacement chat
`01a184c7-5192-71b1-b1fb-be4888a04f51`, managed checkout
`/Users/doughnut/.codex/worktrees/rims-relationship-replacement/chhhs-research-publications`,
branch `codex/rims-relationship-connected-reader`. The clean lane fast-forwarded
with ordinary Git from `190430ef` to verified PR70 main
`7c20256211e961be7b5f19ceadf08287bf309d34` before implementation. Parent supplied
exact-main quality `40786340401` and security `40786340390` acceptance. This
packet owns only this leaf, the new export helper and its paired test. Shared
coordination records remain with the integrator; earlier assignments are history.
Native scope is none. Next operation is terminal source integration by the parent.

## Connected outcome and inputs

[The exporter](../scripts/prepare_source_relationship_export.py) connects the
existing supported producer rows through the frozen typed projection and prepared
model packet to a local candidate evidence JSON/CSV bundle. It rebuilds the exact
model proposal using `prepare_source_relationship_model.prepare` and compares the
entire result to the independently pinned supplied packet. This verifies model
parts, field/measure/source-template contracts and supplied context associations
without changing any of the frozen seven model/reader/M files.

Required keyword inputs are:

- `model_inputs`: exactly the existing model preparer's argument object, including
  complete source model/part inventory and independent model digest, producer
  rows, complete canonical publication snapshot, producer context and independent
  context digest. The frozen context retains complete row/key/field/count and
  provider/eligibility bindings.
- `model_packet` and independently retained `model_packet_sha256`.
- Independently retained `rows_sha256`, `publications_sha256` and
  `typed_rows_sha256`, using the existing typed `fingerprint` helper. Model-document
  digests continue to use the existing document-hash helper.

These pins must come from separately retained review/capture evidence. Computing
new pins from drifted inputs does not establish source authority. Capability
references remain caller-supplied associations; fictional qualified references
in tests are not real native qualifications. A blocked model proposal cannot be
exported through this path.

The CLI consumes a single strict JSON input file containing those keyword inputs,
requires an independently retained SHA256 of its exact file bytes and reads the
file once. Inputs and output remain under ignored `private/ops`, with no symlink
paths. Example shape (substitute actual independently retained paths and digest):

```sh
.venv/bin/python -B -S scripts/prepare_source_relationship_export.py \
  --input private/ops/relationship-export-input.json \
  --input-sha256 <independently-retained-file-sha256> \
  --output private/ops/new-relationship-export
```

No files are discovered from native services. No NIH, DataCite, admission,
provider, runtime, dependency, authentication or shared-record implementation is
changed. Unsupported producer families still fail the frozen typed contract.

## Export meaning, parity and recovery

`evidence.json` preserves every typed row, its input order, literal text, nulls,
booleans and integer counts. It carries the unchanged `RawAssertionJSON` and
`SourcePathsJSON` strings. It does not collapse assertion revisions, occurrences,
ambiguous mappings or unmapped rows into canonical publication counts. Source
retraction, unknown observation times, candidate eligibility, review state and
false authority flags remain explicit. Empty evidence remains an empty candidate
export; it does not establish a complete institutional zero.

`evidence.csv` uses the exact frozen field order. Every data cell is a literal
apostrophe followed by the JSON encoding of its scalar value. This includes
ordinary text, formula-like text, leading controls, literal apostrophes, empty
strings, nulls, booleans and integers. Remove exactly one apostrophe and JSON-decode
to recover each value; `decode_csv` implements this inverse. This explicit display
format preserves types and prevents unescaped formula-leading values. JSON
remains the literal evidence artifact. Actual Excel/Power BI rendering, apostrophe
display and spreadsheet import behavior have not been qualified.

`manifest.json` records row count, ordered evidence/revision keys, distinct
nonblank candidate canonical keys, input/context/model/typed digests, exact field
inventory and byte SHA256 for both artifacts. It retains candidate-only status
and false native acceptance/admission/identity/mutation flags. Counts are row/key
accounting, never funding or outcome claims.

Serialization is deterministic and checked by JSON/CSV typed-hash parity before
writing. Output directory creation is exclusive. Every file is exclusively
created, flushed, fsynced and read back; typed JSON/CSV readback is checked again.
The manifest is written last. On I/O failure, owned partial output is retained
for inspection and never overwritten or automatically cleaned. Consumers must
require the manifest and matching artifact hashes; presence alone is insufficient.
Recovery uses a separately named new output after diagnosis, preserving the old
bundle. There is no retry, native publication or correction mutation.

## Focused verification

Actual `.venv/bin/python --version`: **Python 3.15.1**. A fresh lane-local venv
was created from the installed Python 3.15.1, without replacing any other runtime.
This packet uses only standard-library dependencies and existing repository
helpers. Existing hash locks and dependencies are unchanged; no installation or
new dependency qualification is claimed.

```sh
.venv/bin/python -B -S -m unittest discover -s tests \
  -p test_prepare_source_relationship_export.py -v
git diff --check
```

**13 tests passed.** They cover literal/formula/control/Unicode text round trips,
nullable and typed values, occurrence/revision preservation, ambiguity/unmapped
and empty generations, every independent pin, model/source/context/capability/
part drift, duplicate revisions, partial envelopes, exclusive private output,
symlinks, a failed write without a manifest, corrupt readback and real CLI
byte-pin/duplicate-key rejection. The initial run exposed macOS `/var` temporary
path symlinks in test fixtures; resolved fixture paths corrected the tests while
the production symlink guard stayed enabled. Frozen model/reader tests and their
previously accepted evidence were not rerun. Full integration/package/hosted
checks remain with the integrator.

## Remaining native dependencies

This packet establishes local candidate export parity only. Native adoption still
requires exact producer/model/report identities and complete current binding,
real upstream hash/canonical parity capability receipts, M/DAX execution and
cardinality/filter parity, compatible import and verified inverse, rendered
light/dark/accessibility/detail/export/access behavior, and correction/withdrawal
persistence with protected history and recovery. Native current data, sharing,
schedules, deliveries and activation remain with their existing owners and gates.
