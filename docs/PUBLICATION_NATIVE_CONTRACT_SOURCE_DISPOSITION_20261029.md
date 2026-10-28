# Publication native-contract source disposition — 29 October 2026

Delivery chat `01a1831e-cc6d-7371-9d57-021a339b708a`, branch
`codex/rims-grants-roadmap`, actual checkout
`/Users/doughnut/.codex/worktrees/ef45/chhhs-research-publications`.
Clean entry/canonical comparison: `632224327b00b1f8794a32c93c346a31a1d1bb15`.
Parent assigned the three independent offline helpers, paired unittest tests and
this leaf. Native scope is NONE. No shared contract, schema, runtime, dependency,
handoff, Conductor record, writer/model generator or native adapter changed.

## Delivered independent packet

| Source | Supported offline behavior |
|---|---|
| `verify_publication_protected_fields.py` | Compares count-bound, same-target captures with exact native GUID/integer item identities, every field from existing PROTECTED_MANUAL_FIELDS, current ETags/versions and preserved complete history. New PubMed SourceKeys and CanonicalKeys must match independent supplied expectations; no canonical identity is generated or inferred. |
| `verify_publication_replay.py` | Compares complete logical captures with exact positive decimal-text item IDs, exact source/PMID identities, all existing protected fields, versions and observation chronology. Duplicate/added/removed items or keys, human edits, lost history, unadvanced selected observations and uncertain dates prevent success. |
| `prepare_publication_operator_flow.py` | Requires supplied stopped-flow identity, saved revision, independent accepted definition fingerprint and complete fresh same-target terminal-run history. Changes only the recurrence trigger to an input-free manual trigger. Actions, parameters, bindings, trigger metadata/runtime settings and full restore preimage remain exact and detached from mutable output. No activation or invocation authority is created. |

Existing `scripts/publication_batch_contract.py` supplies the protected-field
policy; it is imported portably and is not changed. No absent writer, OpenAlex,
model or schema generator is imported. Shared local capture/output utilities live
in the protected-field module; replay and operator preparation depend on that
module within this same packet, using stdlib only.

### Explicit supplied-input profiles

These are local verifier input requirements, not a new native list/flow schema.
A captured object must declare `complete: true`, `item_count` equal to its array
length, an exact `target` containing `site_url` and `list_id`,
`observed_at_utc` and a nonblank `capture_reference`. Registry captures additionally
require `history_complete: true`. Error/partial envelopes and unresolved
continuations fail closed. Capture timestamps must be known UTC instants within
15 minutes of the stated evaluation time, with no future/reversed captures. This
is capture freshness, not evidence of upstream harvest freshness.

The raw protected-field profile uses `value`, exact lowercase GUID `Id`, positive
integer `ID`, and the retained `field_N`/Title mappings. Every existing policy
field must be present, even when its value is null or its source date is unknown.
The logical replay profile uses `rows`, exact positive decimal-text `Id`, the
logical policy field names, PMID and LastObservedUTC. Neither profile silently
converts an integer into an ID string or guesses a projection for another export.
Native schema/internal-name qualification stays with the existing owner;
verification reports explicitly retain `native_field_contract_qualified: false`.

Each registry row supplies `version`, `etag` and an ordered nonempty `versions`
array. History entries carry exact version/ETag and capture-reference values;
the last entry must match the current row. Previous entries must survive exactly,
including any extra saved evidence. A selected replay's advanced LastObservedUTC
also requires advanced version history and a new processing stamp inside the
before/after capture interval; an old-but-advanced stamp cannot prove current replay. These are complete supplied evidence
assertions, not independent retrieval or server attestation.

The protected-field helper retains unknown dates unchanged. Replay reports
unknown/locale-naive/unknown-offset row timestamps as explicit uncertainty and
cannot certify replay ordering from them. No missing timestamp is assigned a zone
or replaced by processing time. JSON comparisons retain types and list order;
duplicate JSON keys and non-finite values are rejected. Export hashes bind the
single byte read used for protected-field comparison. Replay hashes explicitly
bind canonical supplied JSON, rather than claiming original transport bytes.

Expected new CanonicalKeys are a separately supplied complete map keyed by the
expected new SourceKeys. The retained assumption that CanonicalKey must equal
SourceKey is removed: this verifier requires exact caller expectations and never
performs a mapping or migration. New review status is likewise explicit input,
not a review decision. Complete capture references/fingerprints do not establish
source truth, authenticated actors or permission to change a native record.

Operator evidence additionally supplies `saved_revision` as an exact ETag or
version label. Operation handles and placeholder revisions are refused. Its
`run_history` declares complete/count-bound values, exact flow/environment,
capture timestamp/reference and unique terminal run IDs. The packet records full
readback/preimage/definition/binding/history fingerprints, exact install/restore
scope, `native_execution: NOT_PERFORMED`, and false native/write/activation flags.

### CLI failure preservation

All CLI inputs and new outputs stay under this checkout's ignored `private/` in
existing owned directories, without symlink redirection. Inputs are read only.
Strict JSON is fully parsed and a result serialized before output creation. A
mode0600 owned temporary file is atomically linked to the new result path;
existing or concurrently created files cannot be overwritten. Failed validation,
serialization or write preparation leaves prior evidence intact and no accepted
final result. A completed negative replay comparison may write a failure report
and returns a nonzero status; that report is evidence, not a successful replay.

Each CLI accepts optional `--as-of` for explicitly dated offline evaluation and
records that evaluation time. Historical evaluation never refreshes native proof.
Without it the local current UTC clock is used. The protected verifier also
requires `--expected-canonical-keys` naming the private independent expectation
map. No capture, login, activation, invocation, native write or retry command is
provided by these CLIs. Private operation handles/bindings/journals stay untouched.

## Focused verification

Repo-local Python 3.15.1, with site initialization disabled (`-S`): focused
unittest discovery executes 35 tests, zero skips: 11 protected-field, 14 replay
and 10 operator tests. Tests use synthetic captures and stdlib temporary files;
there are no unrelated private-fixture skips. Direct CLI help/import checks also
run from outside the repository with `-S -B`. Changed-behavior cases cover identity
coercion/padding, complete counts, history loss, typed protected-value changes,
uncertain dates, stale/future/foreign captures, unqualified saved revisions,
nonterminal runs, exact restore, independent canonical expectations, exclusive
output, symlink refusal and preservation on malformed input/serialization failure.
The single-read/hash test reproduced the retained double-read provenance weakness.

Project structural/link/scope checks pass. The earlier broad source-only harness
receipt is reused; no broad suite or accepted native test was repeated here.
Local checks prove only the supplied-input behavior described above.

## Complete 40-path disposition and exact dependencies

The frozen inventory is [publication source disposition](../audit/publication-source-disposition-20261029.json),
category `retained_native_contract_packet`. All 40 original hashes were checked
against the preserved authoring checkout; all match. Five retained paths are now
implemented by this packet, plus the newly authorized dedicated protected-field
test. The other 35 paths remain explicit dispositions below. Missing filenames
are not counts of missing features.

| Family | Paths | Disposition / precise dependency |
|---|---:|---|
| Independent helpers | 5 | Implemented here with narrowed supplied-input profiles and focused tests. |
| Legacy PMID repair | 2 | Retain as historical repair source. It assumes a direct SharePoint_Update_item absent from the current canonical conditional-update graph, mutates its input definition and permits output replacement. No default writer change or automatic application is qualified. |
| SourceKey/row-count/comparison | 7 | Exact tracked guard nodes/preimages are absent from the current canonical graph. Native comparison additionally imports QUERY_ACTIONS from absent model-scoped patch_publication_model_binding.py. Isolate generic JSON comparison only after ownership assignment; do not import model scope or widen the tracked definition merely to satisfy these helpers/tests. |
| Committed/enrichment writer chain | 9 | Requires absent prepare_openalex_flow.py and prepare_sharepoint_writer_concurrency.py, the retained concurrency/title reducers, exact compatible writer graph and qualified field types/full-title sink. Missing-only metadata-fill and reduction tests cannot qualify a different current writer or authorize broader field updates. |
| Bootstrap/helper plans | 9 | Field-help/index/quality/view helpers import bootstrap utilities. Field help also requires absent config/publication-field-meanings.json; it has no paired test among these 40 paths. Quality's metadata_difference_kind and safe_cell dependencies already exist. Separate offline utility/preparation behavior from CliCapture and generated migration/rollback shell before a future packet. Bare m365 capture/mutation commands are not this workload's qualified route. |
| Native JS adapters | 4 | Preserve with native owner: browser-context capture and authenticated field/index/view/quality mutations. No import or invocation in this packet. Future adoption needs exact target/preimage/journal, qualified route and native readback/recovery scope. |
| Historical model/canary patches | 4 | Preserve with model/report owner. Isolated PubMed audit imports absent patch_report_bound_pubmed_metadata_union.py; efficiency patch imports absent patch_retained_canary_definition.py and patch_retained_canary_source_partition.py. These are retained target-specific M/model repairs, not independent publication-contract helpers. |

All remaining dependencies require explicit later scope. Nothing here changes
source admission, canonical membership, sharing, retained field capacity or
review authority. The native owner must qualify actual field projections,
version-history/capture completeness, fresh same-object state and the existing
operation/journal before any separately authorized action. No current native
capture, save, run, activation, refresh, send or operational acceptance is claimed.

### Exact retained paths

| Retained path | Disposition |
|---|---|
| `scripts/patch_isolated_pubmed_ingestion_audit.py` | Model/canary dependency |
| `scripts/patch_publication_native_comparison.py` | Tracked guard/comparison dependency |
| `scripts/patch_publication_pmid_package.py` | Historical PMID repair retained |
| `scripts/patch_publication_row_count_guard.py` | Tracked guard/comparison dependency |
| `scripts/patch_publication_sourcekey_guard.py` | Tracked guard/comparison dependency |
| `scripts/patch_retained_canary_pubmed_efficiency.py` | Model/canary dependency |
| `scripts/preflight_publication_flow_activation.py` | Committed-writer dependency |
| `scripts/prepare_publication_field_help.py` | Bootstrap/helper dependency |
| `scripts/prepare_publication_indexes.py` | Bootstrap/helper dependency |
| `scripts/prepare_publication_observation_concurrency.py` | Committed-writer dependency |
| `scripts/prepare_publication_operator_flow.py` | Implemented independent helper |
| `scripts/prepare_publication_quality.py` | Bootstrap/helper dependency |
| `scripts/prepare_publication_registry_bootstrap.py` | Bootstrap/helper dependency |
| `scripts/prepare_publication_title_projection.py` | Committed-writer dependency |
| `scripts/prepare_publication_views.py` | Bootstrap/helper dependency |
| `scripts/prepare_registry_source_metadata.py` | Committed-writer dependency |
| `scripts/publication_committed_flow_contract.py` | Committed-writer dependency |
| `scripts/publication_field_help_native.js` | Native adapter retained |
| `scripts/publication_indexes_native.js` | Native adapter retained |
| `scripts/publication_quality_native.js` | Native adapter retained |
| `scripts/publication_views_native.js` | Native adapter retained |
| `scripts/verify_publication_protected_fields.py` | Implemented independent helper |
| `scripts/verify_publication_replay.py` | Implemented independent helper |
| `tests/test_patch_isolated_pubmed_ingestion_audit.py` | Model/canary dependency |
| `tests/test_patch_publication_pmid_package.py` | Historical PMID repair retained |
| `tests/test_patch_publication_row_count_guard.py` | Tracked guard/comparison dependency |
| `tests/test_patch_publication_sourcekey_guard.py` | Tracked guard/comparison dependency |
| `tests/test_patch_retained_canary_pubmed_efficiency.py` | Model/canary dependency |
| `tests/test_preflight_publication_flow_activation.py` | Committed-writer dependency |
| `tests/test_prepare_publication_indexes.py` | Bootstrap/helper dependency |
| `tests/test_prepare_publication_observation_concurrency.py` | Committed-writer dependency |
| `tests/test_prepare_publication_operator_flow.py` | Implemented independent helper |
| `tests/test_prepare_publication_quality.py` | Bootstrap/helper dependency |
| `tests/test_prepare_publication_registry_bootstrap.py` | Bootstrap/helper dependency |
| `tests/test_prepare_publication_title_projection.py` | Committed-writer dependency |
| `tests/test_prepare_publication_views.py` | Bootstrap/helper dependency |
| `tests/test_publication_committed_flow_contract.py` | Committed-writer dependency |
| `tests/test_publication_sourcekey_flow_guard.py` | Tracked guard/comparison dependency |
| `tests/test_publication_sourcekey_projection.py` | Tracked guard/comparison dependency |
| `tests/test_verify_publication_replay.py` | Implemented independent helper |

Inventory SHA-256: `5143c5c9d4ccc6b96429c9b0f88c7260156f3428def246417cf56f5762e622c0`. Original source/receipts remain in their existing checkout; no private rows or bindings were copied.
