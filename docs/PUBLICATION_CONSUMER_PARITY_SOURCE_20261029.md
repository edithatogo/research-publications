# Publication admission-to-consumer parity — 29 October 2026

## Ownership and delivery boundary

Admission chat `01a1831e-cc6d-7371-9d57-021a339b708a` owns only
`scripts/prepare_publication_consumer_parity.py`, its paired test and this leaf.
The clean ef45 checkout on `codex/rims-grants-roadmap` was fast-forwarded from
`a80bc1f7` to verified main `7c20256211e961be7b5f19ceadf08287bf309d34`
before implementation. The existing repo-local interpreter reports Python
3.15.1; its environment and existing hash locks were preserved. The integrator
owns shared contracts, wiring, dependencies and status records. Original
operational checkouts, services, authentication and journals retain their owners.

This packet connects supplied retained source evidence through a rebuilt
admission candidate to expected registry values, model values and complete
bibliography/monthly extracts. It does not deploy a writer, query a service,
admit current native data or alter a consumer. All tests use fictional data.
No provider, authentication, native, refresh, activation, schedule or send
operation was performed. The receipt always has `NativeAcceptance=false`,
`native_acceptance=false`, `writer_ready=false` and `write_authorized=false`.

## Reused foundations

The public entry point `prepare` invokes the existing
[admission verifier](PUBLICATION_ADMISSION_WRITER_SOURCE_20261029.md), rebuilding
the packet from independently pinned acquisition, typed, binding, complete
registry, writer, schema, retained-state and ledger inputs plus current pinned
policy/reference data and exact raw bytes. The expected packet digest is a
separate argument. Neither a matching self-hash nor a caller-supplied proposal
is sufficient.

It reuses `export_publication_register.assemble_paginated_export` and
`export_errors`, then `reconcile_full_month_exports.reconcile`. The new connection
is an independent expected registry/model/bibliography projection from the
verified admission and retained preimage. Repeating matching mistakes in both
supplied exports does not pass that comparison. Existing renderer, source-key,
metadata and full/monthly comparators remain unchanged.

## Explicit supplied contract

`publication_consumer_contract_v1` has exactly these fields:

| Field | Meaning |
|---|---|
| `kind`, `version`, `reference` | Exact profile, nonblank version and supplied contract reference |
| `target`, `generations` | Exact admission target and complete source-generation descriptors |
| `packet_sha256`, `registry_sha256` | Admission digest and complete original registry preimage digest |
| `context` | Correlation and source/target bindings described below |
| `reporting_month` | Explicit `YYYY-MM`; never selected from the current clock |
| `registry_fields` | Complete logical-to-physical field bindings, including protected fields, dates, observation timestamps, PMID, affiliated-author labels and full title |
| `export_fields` | Every field in the existing `EXPORT_FIELDS` bibliography contract |
| `filters` | Exact supported model/reader scope and multiplicity policy |

Every registry binding is `{internal_name, field_id, missing_new}`. Required
meanings use the existing admission field map plus the retained affiliated-author
field. The supplied field GUID, internal name and display meaning must agree
with the supplied complete schema. Additional bibliography meanings, such as
DOI, may bind existing fields only when those exact identities and meanings
agree. Two logical meanings cannot alias one physical field. No field is added,
renamed or migrated by this module.

`missing_new` must explicitly be `null` or `error`. It applies to logical
projection of values absent from a create proposal. `null` means unavailable in
this candidate projection; it does **not** assert that a native default is null.
Existing values cannot be omitted: the original complete field-value set is
preserved. In particular, missing month data is never derived from processing
time, a year or a range. If declared day/month precision lacks a month, the
existing export validator blocks the result. An independently qualified consumer
projection is required to resolve such a gap; this checker invents no value.

Export mappings support these bounded rules:

- Required bibliography fields bind their corresponding registry meanings.
- Title uses the retained human/display `Title` for existing rows and the
  untruncated `SourceFullTitle` for new rows. Existing source-title differences
  never replace human title edits. The model separately preserves both fields.
- Source labels explicitly map `pubmed:` to `PubMed` and `dora:` to `DORA`.
  No identity is inferred from a CanonicalKey or a name.
- Other fields either bind the same schema-qualified logical meaning or declare
  `{kind: "null", reason: "supplied evidence reference"}`. Arbitrary expressions,
  literal authority claims, identifier inference and relationship joins are
  unsupported. A missing attribution field remains unavailable. Already bound
  optional meanings and populated schema fields with that bibliography meaning
  cannot be declared unavailable to suppress their values.

The explicit filter contract is:

```json
{
  "model": "all_registry_rows",
  "placeholders": "exclude_from_exports",
  "excluded_statuses": ["Excluded"],
  "canonical_multiplicity": "reject"
}
```

The model capture includes every projected registry row, including historical
rows, placeholders and explicit exclusions. Reader/export projections include
keyed `Included` and `Needs Review` records and exclude exact `Excluded` records
and blank-key placeholders. Unknown status values fail closed. A placeholder
with a populated canonical identity fails as ambiguous. Canonical multiplicity,
including casefold collisions, fails rather than silently deduplicating: alias
consolidation needs its own qualified contract. None of this changes stored
status or requires routine per-publication approval.

## Context, captures and independent pins

`context` has exactly these fields:

- `generation_id`, `source_snapshot_id`, `query_version`,
  `model_refresh_correlation`, `extraction_contract_sha256`, `data_kind`;
- `target`, `source_generations`, `admission_packet_sha256`,
  `registry_preimage_sha256`.

The last four bind directly to the rebuilt admission and preimage. Every capture
must repeat the same complete context. `data_kind` is `synthetic` or
`live_export`; a live label remains a supplied assertion, not provenance proof.
A consumer generation is distinct from each producer generation. Opaque IDs
and an extraction digest must come from the selected capture contract, not be
generated as evidence of a native operation by this checker.

`captures` must contain exactly `registry`, `model`, `full` and `monthly`.
`consumer_pins` independently supplies canonical JSON SHA-256 digests for those
four documents and `contract`. Admission pins and the packet pin remain separate.
API digests use the existing canonical JSON serializer; the CLI additionally
records exact file-byte hashes from the same reads. Strict JSON parsing rejects
duplicate member names and non-finite numbers. Pins establish consistency of
supplied data, not the authenticity of its origin.

Registry and model use the normalized `publication_consumer_capture_v1` shape:
`kind`, `complete: true`, `next_links: []`, `role`, `context`, `row_count`,
`rows_sha256`, `pages`. Each page has `number`, `cursor_before`, `cursor_after`,
`terminal`, `rows`. Pages are consecutive; nonterminal pages are nonempty and
advance unique explicit cursors. The last page is explicitly empty and retains
the previous cursor. Missing terminal pages, unresolved continuation, errors,
partial data, count/hash drift and duplicate row identities fail.

Registry rows are `{row_id, origin, values}`. Existing row IDs are
`item:<saved integer ID>`; their `values` preserve **every** saved schema field,
including fields outside the selected bibliography, while applying only a
verified proposed `LastObservedUTC` change. New IDs are candidate identities
`new:<SourceKey>`; their values contain exactly the admitted physical create
fields. They are not invented native item IDs. Native-generated metadata,
new-row defaults and subsequent row versions need a separately qualified native
adapter/readback and are not asserted by this profile. Original saved versions,
ETags, history and unknown metadata stay pinned in the complete preimage.

Model rows are `{row_id, values}` with the complete selected logical field set.
Both captures compare exact values and row multiplicity against reconstruction,
independent of row order. Full/monthly inputs use the existing paginated export
profile, including complete pages, separate expected canonical-key inventories,
counts, hashes, matching correlation and exact export field sets. Unresolved
continuation on individual export pages also fails. Monthly metadata and keys
must equal the requested month partition of the independently checked full
bibliography. Unknown-month rows stay in the full bibliography and its separate
count; they cannot be allocated to the month export.

## API and CLI

```python
receipt = prepare(
    admission_inputs, raw_files, verified_packet,
    input_pins=independent_admission_pins,
    packet_pin=independent_packet_sha256,
    contract=explicit_consumer_contract,
    captures=complete_supplied_captures,
    consumer_pins=independent_consumer_pins,
    as_of=explicit_planned_processing_time,
)
```

`verify(receipt, ..., receipt_pin=independent_receipt_sha256)` rebuilds all
comparisons and rejects a changed receipt, even when its own digest is replaced.
Public projection helpers alone are not an admission/parity verification route.
The receipt contains context, independent pins, projection/key fingerprints,
counts and reused export reconciliation, not raw bibliography rows. Counts
separately expose existing/new/model rows, keyed/placeholder/excluded rows,
historical keys absent from this batch, full/monthly rows and unknown months.
No elapsed time, candidate digest or `as_of` proves a native operation occurred.

All CLI inputs, raw paths and output must be under this checkout's ignored
`private/` directory. No remote URL, automatic discovery or provider client is
used. `--packet` contains the existing
`publication_admission_local_result_v1` envelope; the other documents are the
objects described above. `--files` is an explicit name-to-local-raw-path map.

```sh
.venv/bin/python -S scripts/prepare_publication_consumer_parity.py \
  --inputs private/parity/inputs.json \
  --files private/parity/files.json \
  --pins private/parity/admission-pins.json \
  --packet private/parity/admission-result.json \
  --packet-sha256 '<independent packet digest>' \
  --contract private/parity/contract.json \
  --captures private/parity/captures.json \
  --consumer-pins private/parity/consumer-pins.json \
  --as-of '<explicit UTC planned processing instant>' \
  --output private/parity/new-result.json
```

Output creation is atomic and exclusive through the existing private-path and
write helpers. Prior outputs are preserved on replay/failure; failures return 2
without echoing private diagnostic content. Source inputs are never changed.

## Verification and remaining native exits

Focused command:

```sh
.venv/bin/python -S -m unittest tests.test_prepare_publication_consumer_parity
```

All 26 focused tests passed on the existing repo-local Python 3.15.1. Leaf
links and compilation of the two new Python files passed. The fictional cases
cover the connected journey, independent pin/reconstruction
failure, complete pagination, target/generation/source bindings, whole-row and
model protected-field drift, absent current-source history, placeholders,
exclusions, noops, optional bibliography fields, long Unicode full titles,
missing/extra/duplicate exports, month uncertainty, mapping ambiguity and
private atomic CLI output preservation. Existing admission and export suites
are reused at their retained checkpoints; no unchanged full harness is rerun
by this lane. The parent retains integration/release checks.

Still required: authoritative exact current field/filter/extraction contracts;
complete independently captured native post-admission registry/model/export
inputs and their target/correlation/producer lineage; normalized-capture adapters
that preserve those proofs and account for new native IDs/defaults/versions;
the guarded native writer, admission and refresh; protected row readback;
reader adoption and rendering/accessibility/performance; real monthly output
and natural-schedule acceptance. A matching local receipt establishes only
supplied candidate parity. It does not replace any of those exits or authorise
publishing, activation, delivery or native writes.
