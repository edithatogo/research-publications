# Publication admission and writer handoff: supplied evidence only

This source packet starts at frozen reviewed integration commit
`e98c6a0b81a33ccdd4d40c5d056d39fa4495156e`. The integrator authorised that exact
clean fast-forward while PR67 hosted runners were queued. It is not described
as verified origin/main. Source writer: chat
`01a1831e-cc6d-7371-9d57-021a339b708a`, managed checkout
`/Users/doughnut/.codex/worktrees/ef45/chhhs-research-publications`, existing branch
`codex/rims-grants-roadmap`. Shared records, configuration, contracts, runtime,
dependencies, native objects and authentication retain their existing owners.

The executable local journey is frozen acquisition artifacts -> exact typed
projection -> independently supplied source/canonical bindings -> append-only
retention candidate -> logical create/observation proposals and blocked writer
preflight. There is no provider call, native payload, flow transformation, apply,
activation, send, schedule or native acceptance. All outputs retain
`write_authorized=false`, `native_acceptance=false`,
`native_schema_qualified=false` and `writer_ready=false`.

## Executable interfaces

`prepare_publication_admission_packet.prepare(inputs, files,
expected_hashes=..., as_of=...)` returns a deterministic packet.
`verify(packet, inputs, files, expected_hashes=...,
expected_packet_sha256=..., as_of=...)` compares a pinned packet against a complete
rebuild. It rejects changed/rehashed proposals as well as changed input pins.
Neither interface mutates its arguments. Packet verification is a read-only
comparison, not an instruction to replay a proposal.

The eight exact input documents are `acquisition`, `typed`, `bindings`, `registry`,
`writer`, `schema`, `state` and `ledger`. `expected_hashes` independently pins all
eight complete JSON values plus current `policy` and organisation `reference`.
Those canonical object hashes are distinct from CLI input-byte hashes. The
policy/reference are loaded through their existing canonical loaders and checked
again after retention preparation; their active source is unchanged.

The direct CLI uses the explicitly selected repository Python 3.15.1:

```text
.venv/bin/python -S scripts/prepare_publication_admission_packet.py \
  --inputs private/admission/inputs.json \
  --files private/admission/raw-paths.json \
  --pins private/admission/independent-pins.json \
  --as-of <explicit-known-UTC-instant> \
  --output private/admission/new-packet.json
```

The file map associates each declared artifact name with its exact private local
path. Each file is read once; the bytes checked against its manifest are the same
bytes projected and hashed in the CLI envelope. `--packet` together with
`--expected-packet-sha256` selects comparison. Partial comparison arguments fail.
The exact envelope kind is `publication_admission_local_result_v1`, with the
packet/report in `result` and actual input byte hashes in
`source_files_sha256`. Inputs and new exclusive outputs must be under this
checkout's existing `private/`; symlink redirection, duplicate JSON keys,
nonfinite JSON and output replacement fail. No final file is created on failed
validation. The tests use isolated owned temporary paths, never native bindings.

## Evidence profiles and completeness

All evidence documents require the declared versioned kind and explicit complete
flags. Error/partial/continuation indicators fail. Closed profiles reject unknown
members instead of silently dropping them. Source scopes and native origin are
supplied assertions; these helpers do not authenticate captures or certify
provider completeness/freshness beyond the independently pinned declared scope.

Bindings use `publication_source_bindings_v1`: exact `target`, `generations`,
`records`, `item_count`. Target includes site/list, model/workspace, flow and
environment identities. Each source generation carries `source`, `generation`,
`model_id`, `workspace_id`, `request_id`, `observed_at_utc`. Model/workspace must
match the stopped writer's saved queries. Acquisition and typed generation
inventories must match the independently pinned binding inventory exactly.
Each selected source has an explicit nonempty record inventory in this profile;
empty-generation admission is not implemented or inferred from missing rows.

Binding rows contain `{source, source_id, SourceKey, CanonicalKey}`. PubMed IDs
are exact positive ASCII decimal strings. The selected DoRA profile uses exact
`DORA:1/<positive decimal>` source IDs and verifies the own official handle URI in
metadata. CanonicalKeys are supplied independently, never computed from titles,
PMIDs, DoRA handles or another CanonicalKey. Duplicate/case-ambiguous bindings,
canonical collisions and unresolved legacy DoRA aliases fail without adoption,
key rewriting, disposal or identity merging.

Acquisition uses `publication_frozen_acquisition_v1` with `unfiltered=true`,
capture/scope references, generations and an exact parts inventory. Each part
supplies `{name,source,generation,format,bytes,sha256,source_ids}`. The supplied
file map must match all parts exactly, with no fixed part total. Each byte length,
SHA256, own identity inventory and generation must match.

Two retained source artifact profiles are supported:

- `pubmed_efetch_xml_v1`: input bytes must decode as UTF-8 (optional UTF-8 BOM),
  contain no NULs, and have an absent or explicitly UTF-8 XML encoding declaration.
  XML 1.0 declarations are checked before parsing; UTF-16/32 and other declared
  encodings are unsupported. Entity declarations are rejected on the verified
  decoded text before any parser/projection can expand them. Every own article
  must have exactly one direct MedlineCitation, one scalar positive PMID, one
  Article and one nonblank ArticleTitle. Duplicate own citations/IDs/articles/
  titles and nested own fields in scalar values fail. A supplied journal/title
  cannot be ambiguous. Legitimate mixed title markup, built-in/numeric escaped
  text and PMIDs in cited-reference metadata remain supported. The existing
  pure EFetch projector then supplies typed display/date/author fields. Complete article metadata is independently retained
  through `publication_xml_metadata.article_metadata`. Missing/duplicate/foreign
  structures and declared XML entities fail. Original file bytes remain referenced
  by their exact hash; serialized metadata is not claimed byte-identical XML.
- `dora_metadata_records_v1`: a strict complete JSON envelope containing records
  with `{source_id,metadata}`. Each metadata node retains its Field/Value and
  unknown supplied properties. The existing `_dora` projector supplies typed
  fields; own URI evidence must agree. This is a retained full-metadata artifact
  profile, not proof of original HTTP-response bytes. Sparse `dora_rss_v1` is
  refused here: the existing DoRA union/cycle gate retains that responsibility.

These are explicit supplied artifact profiles. The packet does not convert a
native collector completion marker into authenticated raw proof or discover
latest files. An owner must supply the matching frozen artifacts and provenance;
unsupported formats remain a concrete adapter/native dependency.

Typed input uses `publication_typed_admission_input_v1`: capture reference,
generations, records and pages. Every record contains source/source ID,
SourceKey/CanonicalKey, generation, exact part name, typed `record` and complete
`metadata`. Both projected values and metadata must equal the supplied raw
projection, including JSON types. Unknown metadata cannot disappear behind an
unchanged display title. Ordered pages must reproduce the whole typed inventory,
continue explicit cursors and end with one empty page. Existing
`validate_paged_batch` checks independent counts/key sets; page error envelopes,
value substitutions, duplicate rows and missing terminal pages fail.

## Schema, timestamps and preservation

Registry inputs use the complete metadata snapshot profile from the
[metadata helper packet](PUBLICATION_REGISTRY_METADATA_SOURCE_20261029.md).
`publication_admission_schema_v1` pins the exact field inventory, policy and
reference and supplies timestamp/full-title semantics references plus explicit
field-ID/UTF16 capacities. Logical names must match existing physical field
titles/types. Writable/unsealed text destinations, plain Note behavior, compatible
Number year storage and Included Choice support are checked. Missing capacities,
capacity over a supplied Text MaxLength, incompatible fields and oversized values
fail. These supplied qualification assertions do not prove native schema behavior.

The only timestamp profile is `registry_processing_utc`, consistent with the
[current meaning proposal](PUBLICATION_FIELD_MEANINGS_PROFILE_20261029.md).
The explicitly supplied packet `as_of` is a proposed processing instant for new
FirstObservedUTC/LastObservedUTC and existing LastObservedUTC. It is not recorded
native execution or source harvest time. Source observation instants remain in
their generation and retention evidence. Regressing processing observations and
future source/capture evidence fail. A later native writer still needs separately
qualified actual processing-clock behavior and fresh preimages.

New-record proposals follow existing `publication-policy.json` and `evaluate`:
Included automatically, with source uncertainty labels retained. They do not
change existing review status or infer affiliation, employment, person merges or
calendar dates. Full titles are kept in the already-qualified SourceFullTitle
Note; proposed display labels respect the supplied UTF16 capacity without
splitting a surrogate pair. Unmapped source fields remain in source evidence.
No source metadata is enriched or silently truncated.

Existing rows produce only LastObservedUTC or an explicit no-op. The actual
proposal is checked through the canonical update allowlist and restricted further
to `field_20`. Every current row, human value, version/history payload, ETag and
protected logical value remains detached and preserved. CanonicalKey/SourceKey
conflicts fail; no observation fills source metadata or performs year repair.

`publication_retained_cycle.retain` produces an append-only local state candidate.
Historical cycles/versions and missing last-good identities survive. New versions
retain the unmodified typed values plus separate `SourceEvidence` containing
complete metadata and raw-part proof. No accepted state or commit marker is
written. The complete `publication_admission_ledger_v1` has count-bound entries
with packet hashes and exact generation descriptors. A generation already in the
supplied ledger or retained cycles is refused, including identical replay. Ledger
completeness/origin remains an explicit owner-supplied assertion.

## Narrowed stopped-writer preflight

`preflight_publication_flow_activation.assess(writer, registry, target,
expected_writer_sha256=...)` is a supplied-evidence diagnostic. Its historical
activation-oriented name grants no run authority. Inputs require stopped state,
exact flow resource identity, saved version/ETag, connection references, complete
count-bound terminal run history with capture identity/time, and matching saved
SharePoint/model/workspace bindings. The CLI accepts `--writer --registry
--target --expected-writer-sha256 --output`; it uses the same strict private,
single-read hash and exclusive-output rules. Exit zero means a diagnostic was
produced, not that readiness passed.

The current pilot produces all seven named blockers:
`pilot_topn_100`, `missing_rows_coalesced_to_empty`,
`inferred_dora_source_key`, `missing_complete_batch_guard`,
`missing_full_title_protection`, `missing_conditional_etag_protection`, and
`legacy_needs_review_policy`. Common structural success is reported separately.
Adding names, a nonwildcard header or the Included literal does not qualify guard
semantics: `writer_profile_not_qualified` always remains, and no supported input
can produce writer-ready, activation-permitted or native-accepted output.
The tracked flow and `build_sharepoint_upsert_package` remain unchanged.

### Opt-in supplied Standard-connector evidence — 29 October 2026

The replacement admission source lane was explicitly assigned only
`scripts/preflight_publication_flow_activation.py`, its paired test and this
leaf for this packet. Its clean managed checkout
`/Users/doughnut/.codex/worktrees/8cd6/chhhs-research-publications`, branch
`codex/rims-consumer-outcomes-source`, fast-forwarded to orchestrator-released
verified PR72 main `d20e9b773a775d1d056ed60fb43999a4736c2d15` before editing.
The preserved repo-local `.venv/bin/python` actually reports Python 3.15.1.
Shared integration, dependencies, hooks, runtime promotion and native/auth/journal
ownership stay with their existing owners. No live probe or mutation occurred.

The default assessment and CLI output remain unchanged when no optional evidence
is supplied. A frozen fictional receipt from the PR72 implementation is compared
by canonical SHA-256 in the paired tests. The opt-in API is:

```python
result = assess(
    writer, complete_registry, exact_target,
    expected_writer_sha256=independent_writer_sha256,
    standard_evidence=supplied_evidence,
    standard_pins=independent_evidence_pins,
)
```

Supply both optional documents; one alone fails closed. The CLI adds paired
`--standard-evidence private/preflight/standard-evidence.json` and
`--standard-pins private/preflight/standard-pins.json`. It retains strict ignored
private paths, single-read file-byte fingerprints and exclusive output. Exit zero
still means a diagnostic was produced, including when policy blockers exist.
An existing output survives replay or failure without overwrite.

The evidence object has exactly these fields:

| Field | Supplied content |
|---|---|
| `kind`, `complete` | `publication_standard_connector_evidence_v1`, literal `true` |
| `scope` | Exact `writer_sha256`, `target_sha256`, `saved_revision`, `connection_references_sha256` |
| `policy` | Explicit versioned workload policy below |
| `inventory` | Complete, path-sorted inventory rebuilt from every action/control node and trigger, including nested branches |
| `classifications` | Explicit versioned source/schema claims bound to exact inventory operations |

The separate `standard_pins` object supplies canonical JSON SHA-256 values for
exactly `evidence` (the entire evidence document), `writer` (the complete writer),
`target`, `revision` (the saved revision string), `connection_references` (the
entire captured map), `policy`, `inventory` and `classifications`. These pins
establish consistency of the supplied snapshots, not provenance authenticity or
rights. A self-consistent replacement scope cannot pass an independent pin or the
comparison with the actual supplied writer/target/revision.

`policy` has exactly:

```json
{
  "kind": "publication_standard_workload_policy_v1",
  "version": "supplied-version",
  "reference": "supplied-user-direction-reference",
  "power_automate_premium": false,
  "power_bi_entitlement": "not_power_automate_evidence",
  "custom_connectors_allowed": false,
  "allowed_classes": ["BuiltIn", "Standard"]
}
```

The two false values must be JSON booleans. Power BI Premium or an altered
allowed-class list cannot replace the no-Power-Automate-Premium direction.
This policy records the selected workload constraint; it neither discovers
nor changes a licence assignment, purchase, trial or tenant-wide policy.

Each inventory row has exactly `path`, `node_type`, `api_id`, `operation_id`,
`connection_reference`, `node_sha256`. Paths are arrays of exact segments, such
as `["actions", "ScopeName", "actions", "RepeatedName"]` or
`["triggers", "RepeatedName"]`; names containing slashes and names reused in
different branches remain distinct. Paths cover nested `actions`, `else`,
`default`, and every `cases` branch. Missing/malformed branches and absent trigger
inventories fail closed. Every node's complete captured bytes are represented by
its canonical digest, including unselected parameters/metadata. Missing, extra,
reordered or changed inventory rows fail reconstruction.

Host values come from the exact `apiId`, `operationId`, and `connectionName` or
`connectionReferenceName`. Both reference forms may coexist only when equal.
No-host nodes explicitly retain null identity values. Each classification entry
contains exactly `operation` (the entire matching inventory row),
`classification`, `version`, `reference`, `source_sha256` and
`operation_schema_sha256`. Nonblank version/reference and valid source/schema
fingerprints are mandatory. These are retained supplied assertions; the helper
does not fetch a reference or authenticate its classification, schema or licence.

Supported declared classes are `BuiltIn`, `Standard`, `Premium`, `Custom` and
`Unknown`. No class is inferred from a friendly name, action type, connector API
suffix or Power BI entitlement. Missing classification coverage becomes an
explicit `Unknown` per-path diagnostic with `missing_classification`, rather
than disappearing. Premium, Custom and Unknown remain blocking. Duplicate,
extra or rebound classification paths are rejected. Conflicting classifications
for the same exact node-type/API/operation identity remain inconsistent and
blocking; neither declaration silently wins. A connector declared BuiltIn or a
Standard declaration lacking connector bindings is also blocking.

Every hosted operation must have complete connector/operation/reference bindings.
Its reference key must resolve in the pinned captured map, with an exact matching
`id` and a nonblank captured `connectionName`. API namespaces are not normalized
or matched by suffix: unresolved aliases need separate exact owner evidence.
Expressions and unresolved `{{...}}` placeholders are not literal connector or
connection identities and remain blocking; this checker never evaluates them.
Missing or malformed bindings remain unresolved; unused reference entries are
retained and blocking. A captured connection name associated with differing API
identities is ambiguous and blocking. Reusing a connection for operations with
the same exact API identity does not itself create that ambiguity.

The opt-in result adds `standard_connector_evidence`, containing per-path
operations/unknowns, every raw captured reference, the complete unmodified
`supplied_evidence`, independent hashes, policy blockers and limits. Thus source
references, versions, source/schema hashes, contradictory declarations and
unselected raw values remain available for owner review. It does not invent
missing classifications or discard unknowns. All original structural errors and
blockers remain. New policy blockers are prefixed `standard_evidence:` in the
outer result, and `standard_evidence_claims_unauthenticated` always remains.
The diagnostic always has `claims_authenticated=false` and
`licensing_qualified=false`; existing readiness, activation, diagnostic-run,
write and native flags remain false even with no supplied-policy conflicts.

Verification: **20 affected fictional unittest cases** pass on Python 3.15.1,
including all six existing default cases, frozen default receipt compatibility,
component pins/scope, Standard/Premium/Custom/Unknown/missing declarations,
policy substitution, raw unknown/reference preservation, conflicting identities,
all nested branches and reused names, connector triggers, malformed/incomplete
coverage, and strict private CLI output/replay/failure behavior. No unchanged
full harness or old review was repeated by this lane; integration/hosted gates
remain with the integrator.

Remaining native/input blockers: authoritative retained classification sources
and exact operation schemas; current workload/licence rights and service-specific
permissions; DLP/environment restrictions; exact available connections and
identity/namespace resolution; native action behavior, authentication and current
target access; guarded writer graph, durable outcome journal, processing clocks,
protected readback, admission, refresh and consumer/runtime acceptance. The
existing assisted fallback remains available. Supplied Standard claims cannot
authorize save, activation, a diagnostic native run, a schedule or a send.

## Retained dispositions and remaining adoption dependencies

| Retained nine-path family | Disposition |
|---|---|
| `scripts/preflight_publication_flow_activation.py` and paired test | Rewritten for supplied-input diagnostics; historical legacy/committed activation profiles are excluded. |
| `scripts/publication_committed_flow_contract.py` and paired test | Retained outside this packet. Its older enriched reconstruction cannot qualify the canonical nested update branch. |
| `scripts/prepare_publication_observation_concurrency.py` and paired test | Retained. Fixed five/nine/fourteen-field sets and old reducer do not represent the current timestamp-only update. |
| `scripts/prepare_publication_title_projection.py` and paired test | Retained. Requires the absent author/year predecessor graph; no title HTTP graph is rebuilt here. |
| `scripts/prepare_registry_source_metadata.py` | Retained. URL/author fills and protected year/precision repairs require separate policy/native scope. |

The absent `prepare_openalex_flow` and `prepare_sharepoint_writer_concurrency`
remain excluded dependencies. The former assumes the older enrichment branch;
the latter's builder supports grants/DoRA roles and their timestamp-repair tails.
No old command, reducer, capture transport, package builder, enrichment graph or
historical fixed-part capture is imported to reduce the retained-path count.
Existing PubMed reconstruction, DoRA cycle, policy/retention, protected-field and
batch modules remain unchanged and retain their original owners and receipts.

Remaining source/native work is exact current collector-artifact adaptation where
formats differ, schema/engine parity and typed admission, an explicitly owned
complete-batch/source-binding/full-title/conditional-ETag writer graph, actual
persistence/readback/recovery, reader access and consumer key/metadata/export
parity. Authentication/notification suppression and separate run/activation/
scheduled proof gates remain with native owners. This packet changes no tracked
flow/template, configuration, contract, dependency/runtime or shared handoff.

## Focused verification

The selected `.venv/bin/python` reports 3.15.1. These 30 synthetic stdlib tests
pass with site packages disabled:

```text
.venv/bin/python -S -m unittest \
  tests.test_preflight_publication_flow_activation \
  tests.test_prepare_publication_admission_packet -q
```

Coverage includes a 104-record/three-part journey, exact raw/typed/identity and
model bindings, unknown metadata loss, last-good/history preservation, replay,
field/schema/capacity/typed-value guards, UTF16 display bounds, separate processing
and source clocks, all seven pilot blockers, strict/exclusive CLI behavior and
both direct-script subprocess entry points under the selected Python with `-S`.
No provider, native capture, runtime, deployment or broad unchanged check is
repeated. Integrator-owned integration/release and native gates remain separate.

## Raw PubMed review correction

The follow-up to `0b4a40ed` closes reproduced duplicate-own-ID and UTF-16
entity-declaration gaps entirely within the admission helper. The shared EFetch
projector remains unchanged. Five added regression methods cover duplicated same/
different own PMIDs; duplicated own citation/article/title; malformed scalar
structure; entity declarations in UTF-8/16/32 and unsupported declarations; and
preserved cited IDs, mixed markup, escaped text and original bytes. All 29
admission tests pass under repository Python 3.15.1 with `-S`, including the
existing direct CLI tests. The original six unchanged preflight tests reuse their
prior receipt. No native/source binding, shared helper or tracked flow changed.
