# ARC snapshot, model and reader source closure

29 October 2026. Base: `396c2d5809cc1adfaa680f4b73148a73af2e915f`.
Native scope: none. No provider calls, replay, refresh, deployment, source
acquisition, flow generation or scheduling occurred. This source packet reuses
canonical `powerquery/fnReadArcAwardExport.m` and the canonical
`scripts/build_legacy_report_json.py::make_visual_container` API unchanged.

## Requirement and dispositions

T18 slice 2 requires separate project, award, application and participation grains,
explicit identities/periods, currency/share, and nonmultiplying bridges
(`conductor/tracks/chhhs_outcomes_powerbi_20261021/spec.md`, lines 24–26;
`plan.md`, slice 2). This packet restores a narrower prerequisite: retained ARC
source-context comparison and additive model/reader preparation. It does not
supply C01 active/led projects, F01 institutional funding, P01 partnerships or
C02 workforce/roles. Opportunities, applications and source award-context records
remain distinct.

The original `docs/ARC_AWARD_READER.md` records historical scoped acceptance of
34,977 source records, source status/award-code selection, blank amount text,
links and preserved pages. This is reused historical evidence, not recaptured
current-native acceptance. Declined and not-yet-accepted records are included;
the count is not funded awards or CHHHS attribution. The original native owner,
private captures and environments were not changed.

The six retained paths below were absent at the source base and are amended here.
Original hashes identify the read-only authoring bytes, not a native data capture.

| Retained path | Original SHA-256 | Disposition |
| --- | --- | --- |
| `scripts/reconcile_arc_awards_snapshots.py` | `dd9f58c0de2b323b63279b55207823a079ef4a8b5380b481d823e9f84dc5c3f8` | Amended source / focused test |
| `scripts/prepare_arc_award_model.py` | `9522e7ffff5409a8c35f3a9d2b551df56a5a0f96aadda3d0308f0b52d63e24c6` | Amended source / focused test |
| `scripts/prepare_arc_award_report_page.py` | `e8c39038edacc45195eed716f52fe4ec5562d5c1d8e6a79ab9aa7beccbda7eba` | Amended source / focused test |
| `tests/test_reconcile_arc_awards_snapshots.py` | `4f3d0625e13fb1d5d05a08684afd6803848694ff4dbe5e806b5d3c1237052c73` | Amended source / focused test |
| `tests/test_prepare_arc_award_model.py` | `e171cd1281874e2538a4365dfe31b05dd46f0b98e3e395155448d2da33ca2bae` | Amended source / focused test |
| `tests/test_arc_award_report_page.py` | `572176ee809cc3d7b6e40ff60e0556c14c4372c90065049527bf89ef10a31c5b` | Amended source / focused test |

Reused unchanged Power Query SHA-256: `81022b91476e092c0fa7e3ef94dc61cf2b3b4f7da18e74b1db64c1da2be409a7`.

## Input and preservation contract

The snapshot comparator requires independently caller-pinned SHA-256 values for
both exact saved byte streams. Each stream is read once, then hashed and strictly
parsed. Duplicate JSON keys, nonfinite values (including overflow), failure
envelopes, conflicting source identities, duplicate or padded SourceID/AwardCode,
boolean or incorrect counts, incomplete snapshots/pagination and record-digest
drift fail validation. A snapshot explicitly contains `source: arc`,
`record_kind: awards_only`, `snapshot_complete: true`, `next_links: []`, exact
`source_total`, `records`, and `snapshot_hash` equal to the canonical record-array
digest (sorted JSON keys, compact separators, UTF-8, no NaN). A file hash computed
only after reading an untrusted input is not independent capture authority.

Comparison preserves unknown dates and raw amount strings/nulls, reports pairing
drift even with equal identity sets, distinguishes missing from explicit null,
and never declares lifecycle semantics, native acceptance or opportunity admission.
Observation time/evidence-hash differences remain explicitly excluded from the
business-field comparison; source files and their exact byte hashes remain intact.

Model preparation requires the canonical full preimage digest and explicit complete
part inventory. Every part must have a unique safe path and valid inline base64.
Its pinned archive receipt supplies exact existing site/folder, export/source run
identities, positive actual-integer row count, ordered twelve-field inventory,
awards-only kind, completeness/unpaged declaration and manifest SHA-256. It also
binds `snapshot_file_sha256` and `snapshot_records_sha256` to a separately supplied
saved snapshot whose bytes, records, IDs/count and all twelve raw text/null fields
are validated. The manifest digest is supplied evidence; this helper does not
recapture or independently authenticate the native archive manifest or source.
The existing M reader retains its native archive validation responsibility.

Only the model references, expressions and one new hidden `ARCAwardContext` table
are changed. All unrelated parts and envelope metadata survive unchanged; the
source object is not mutated. Existing ARC tables/expressions are refused rather
than overwritten. Every source field has string type and no summarization; URL
retains WebUrl metadata. Amounts are not converted, summed, allocated or filled.

Reader preparation requires a pinned complete outer report digest and explicit
complete part inventory including the existing `definition.pbir` binding. It
accepts only PBIR-Legacy with exactly eight uniquely identified existing pages.
It rejects current six-page E04/PBIR input, duplicate target pages/parts, stale
preimages and ambiguous inner JSON. Only a ninth ARC source-context page is
appended; all existing sections, edits, filters, bindings and other parts survive.
The retained obsolete tableEx webURL expression is replaced with the canonical
global URL-icon option, relying on WebUrl column metadata. This is source parity
with the established API, not a new native link/rendering acceptance result.

All CLI inputs and new outputs must be under ignored `private/ops`, with distinct
inputs/output and no symlink traversal. Serialization and validation finish before
an output is installed. A private temporary file is exclusively linked into the
new output name; existing files are never replaced and temporary files are removed
on failure. No optional validation-directory writer or native operation is exposed.

## Executable qualification

Repo-local `.venv/bin/python` reported Python 3.15.1. The three focused stdlib
unittest files passed 26 methods: all original 18 methods retained, eight added.
The added fixtures exercise pinned hashes, schema/count/pagination/identity drift,
strict JSON, unknown dates, raw amount types, null versus missing fields,
protected preimages, six-page/PBIR refusal, symlink and serialization failures,
and exact CLI output preservation. There are no pytest-only functions or skips.
The connected fictional CLI test runs each script directly with the same verified
interpreter and `-S`, from a different working directory, proving source/import
closure without optional site packages. It connects one saved two-row snapshot,
comparison, pinned model preparation and an eight-page reader proposal. It checks
unrelated table/binding preservation and never contacts a service.

```sh
.venv/bin/python -m unittest discover -s tests -p test_reconcile_arc_awards_snapshots.py
.venv/bin/python -m unittest discover -s tests -p test_prepare_arc_award_model.py
.venv/bin/python -m unittest discover -s tests -p test_arc_award_report_page.py
```

Direct CLI `--help` exposes the required pins. Comparator uses
`--baseline-sha256` and `--current-sha256`. Model uses `--expected-sha256`,
`--expected-parts` (JSON path inventory), `--archive-receipt`, `--archive-sha256`,
`--snapshot`, `--snapshot-sha256` and the exact site/folder/runs/count. Reader uses
`--expected-sha256` and `--expected-parts`. Definitions may contain private native
identities and therefore remain ignored. The model's optional outer `definition`
wrapper is preserved; its expected digest applies to the inner definition. The
reader's expected digest applies to its complete outer document.

## Remaining exits

This packet supplies offline proposals, not permission to load them. Current
native identity, source archive authority, complete current preimages, model
isolation/rollback and connection preservation, table-only refresh, full key/field
parity, actual selection/reset/link/export/access behavior and native rendering
remain separately qualified by their exact owners. E04's import/recovery blocker
and T18's missing current reader identity remain open; no replacement is selected.

The retained ARC exporter/collection family has separate QGIP/source-collection
builder dependencies and is not imported. Funding relationship/classification,
award aliases, Crossref/government references and protocol-study chains have
separate layered SourceRelationshipEvidence contracts; they do not become
canonical project/award facts through this packet. Translation/outcome intake
continues to use `scripts/outcome_evidence.py`; authoritative records/custodian,
indicator versions, denominators/comparators, follow-up, native persistence and
semantic-reader acceptance remain unresolved. No shared contracts, runtimes,
dependencies, coordination records or existing native objects are changed.
