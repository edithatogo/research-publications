# Frozen collector artifacts to admission inputs

Entry base is verified PR69 main `30bd1e9fd9559ac277089ffeef91ec41d9095134`,
quality `40767034102`, security `40767034100`. This lane confirmed a clean checkout
and fast-forwarded its existing branch to that exact `origin/main` before writing.
Source owner is chat `01a1831e-cc6d-7371-9d57-021a339b708a`, managed checkout
`/Users/doughnut/.codex/worktrees/ef45/chhhs-research-publications`, branch
`codex/rims-grants-roadmap`.

The five owned paths are the new collector adapter, its paired test and this leaf,
plus the admission helper/test for additive literal DoRA support. Other shared
preflight, feed, protocol, package, tracked-flow, configuration, dependency/runtime
and handoff files remain unchanged. Original operations, auth and bindings retain
their owners. No native request, new capture, store, publish, acceptance marker or
private record export occurred.

## Adapter behavior

`prepare_publication_collector_admission_inputs` accepts explicit frozen bytes,
independent artifact-inventory, generation-bridge and binding hashes. It produces
local acquisition/typed input components with original provenance. Unsupported
book/XML or full HTML input produces a retained-input blocker without partial
admission files. A blocked selected source cannot be omitted during combination.
All results retain false native/write/schema acceptance flags.

`inventory` hashes the exact supplied byte artifacts and named file maps.
`adapt_pubmed` and `adapt_dora` validate one source. `combine` requires every selected
source plus independently pinned external registry, schema, writer, bindings,
state, ledger, current policy and reference. It assembles complete ordered pages,
then calls the existing admission preparer. No defaults, CanonicalKeys, source
identities or accepted markers are invented. The combined packet remains a local
proposal, and downstream writer readiness remains unresolved.

## PubMed frozen EFetch and comparison evidence

The explicit artifact bundle contains bytes for `manifest`, `readback`, `commit`,
`source_pages`, `typed_receipt`, `candidate`, `comparison`, `differences` and
`receipt`, plus exact `raw_files` and `typed_files` byte maps. The adapter:

1. Pins all original bytes and validates current UTF-8/XML own-record structure
   through the accepted admission guard before projection. Books or unsupported
   XML shapes/encodings remain retained blocked inputs, never a filtered subset.
2. Reuses `prepare_offline_typed_candidate` and its retained archive validator to
   rebuild the complete candidate/comparison/differences from those same bytes.
   Prior typed files and reconstructed metadata also receive strict JSON checks.
3. Requires exact equality with all three saved outputs. The existing frozen
   comparison receipt profile is used directly: `counts`, `input_paths`,
   `input_sha256`, `native_invoked`, `output_path`, `output_sha256`. Its five input
   hashes and three output hashes must match the supplied originals exactly.
   Original paths remain provenance; they are never automatically dereferenced.
4. Preserves XML bytes, full metadata, unknown nodes/attributes, richer candidate
   and author-evidence references. Admission's narrower exact typed projection is
   derived separately; it does not erase the richer artifacts.

The raw marker remains `rims-pubmed-full-hedge-commit-v1`, complete, with no
applied downstream selection. Manifest-wide identities, per-file ordered IDs,
readback lengths/hashes and prior typed proofs are validated through the existing
rebuild. Derived part identity inventories are sorted for admission; original XML,
manifest ordering and receipt bytes remain unchanged.

## Independent generation bridge

`publication_collector_generation_bridge_v1` is complete and independently pinned.
Its closed fields are `source`, `reference`, `artifact_inventory_sha256`,
`binding_inventory_sha256`, `generation`, `raw_generation_reference`,
`candidate_generation_sha256`, `commit_sha256` and `binding_role`, alongside kind
and completeness. The supplied generation must equal the independently bound
source generation and its selected consumer model/workspace.

For PubMed, the role is `offline_candidate_for_consumer_validation`. The original
raw reference must equal the collector run, the content generation must equal the
rebuilt candidate SHA256, and the prior consumed commit hash is retained. The new
candidate cannot inherit the prior native generation or refresh request. This
prevents treating a newer raw candidate as already consumed by an older marker.
The existing frozen evidence records 1,279 raw identities versus 1,277 consumed
typed identities; these are historical receipts, not new collection results.

The bridge is an independently supplied provenance assertion for a local consumer
candidate. It does not authenticate an origin or prove a new native processing
request. Observation time is explicitly supplied, never inferred from the current
clock. Planning/registry processing time and source observation remain distinct.

## DoRA completed metadata union

The union adapter consumes exact bytes for `pages`, `generation`, `validation` and
`commit`, with independently pinned prior state and literal representation profile.
It reuses strict native-page/chunk reconstruction and `prepare_dora_metadata_cycle`:

- Exact complete pages, terminal proofs, same completed model/request/generation,
  named audit/field parity and prior historical identity preservation must pass.
- Strict decoded metadata must retain every ordered node, duplicate value,
  language/unknown property and literal date. Sparse RSS cannot substitute for
  full metadata.
- The committed descriptor must select exactly one full DoRA metadata profile and
  the complete key inventory. Payload/chunk/character/key hashes and counts,
  extraction model/request/generation, terminal flags and completion time must
  agree. Contradictory or incompatible historical evidence is blocked, not upgraded.
- The bridge role is `retained_union_candidate_for_consumer_validation`, bound to
  the selected completed union and its exact metadata payload hash. The adapter
  writes no replacement commit and does not label the result native-admitted.

The generated `dora_literal_metadata_records_v1` JSON is a derived retained-metadata
artifact. Its original capture/chunk/marker hashes and reconstructed payload
hashes remain in provenance. It is not certified original HTTP wire content.
The full public-collection HTML collector profile is explicitly blocked: a lossless
HTML extraction adapter is not implemented, and the old flattened collector parser
is not imported as a complete metadata replacement.

## Additive literal identity and representation profile

Existing `dora_metadata_records_v1` short-ID behavior is unchanged. Its source IDs
remain `DORA:1/<positive decimal>` with the original exact URI rule. URL identities
cannot enter through that old raw profile.

The new raw profile accepts literal source IDs beginning `DORA:https://` at the
exact official host and `/qldresearchjspui/handle/<positive>/<positive>` path.
SourceKeys remain exactly `dora:` plus that original URL. CanonicalKeys remain
independently supplied. There is no shortening, rekey, URL canonicalization or
metadata URI replacement. `identity` is only a lexical check; it grants no
mapping authority.

The optional additive schema member `dora_representation_profile` is included in
the independently pinned schema hash. The complete profile kind is
`dora_literal_representation_profile_v1`, with nonblank `reference` and explicit
`bindings` of `{source_id,SourceKey,own_uri,verified_https_uri}`. Each binding must
name the exact HTTPS source URL and key. Its literal own URI may be that URL or
only the HTTP scheme spelling of the identical official host/handle. Both
originals are retained. Queries, fragments, ports, credentials, encoded paths,
other hosts, padded/zero handles and ambiguous/missing mappings are refused.
The raw wrapper pins that exact representation profile hash. These supplied
assertions are not independently authenticated native authority.

Alias detection compares only the closed known physical handle forms to detect
collisions; it never returns rewritten data. Mixed short/URL forms across selected
bindings, current registry or retained history fail instead of creating parallel
identities. Existing URL-shaped version/state keys remain literal, and old version
prefixes remain unchanged. A real key migration requires a separate assignment.

This additive contract works with the existing feed/protocol implementations
without changing them: bindings retain their existing document shape, the schema
extension remains pinned, and their lexical identity call recognises literal URLs.
The compatibility tests also retain full metadata and HTTP own-URI text. Protocol
completion remains simulation, never deployable WDL or native runtime acceptance.

## API and CLI preservation

Per-source results have an independently retainable `result_sha256`, derived from
all input/provenance documents and exact output-file hashes. `combine` requires
those pins, rejects claimed native authority, verifies the same external bindings,
generations and representation authority, and refuses artifact-name collisions.
No silently renamed file, invented registry/schema/writer/state or dropped source
is used to make a packet pass.

The CLI accepts `--request <private JSON> --output <new private JSON>`. A request
supplies source, explicit artifact paths/file maps, bridge and bindings, all pins,
and a positive `page_records`; DoRA additionally supplies prior state and literal
profile with their independent pins. It reads only those explicit paths under
this checkout's private area. It does not discover or copy original receipts,
follow receipt path strings, acquire data or invoke a collector.

Output kind is `publication_collector_adapter_local_v1`. The local result contains
`files_utf8`; re-encoding preserves the exact supported original XML or derived
JSON bytes. Same-read input hashes accompany the result. Strict JSON, symlink
refusal and exclusive owner-only atomic output rules preserve prior files.
Exit zero means a diagnostic/local artifact was written, including blocked status,
not that source admission succeeded. The pure byte API allows an authorised owner
to supply frozen evidence without modifying its source location.

## Evidence and remaining gates

The existing [PubMed frozen candidate evidence](PUBMED_OFFLINE_TYPED_CANDIDATE_20261029.md)
and [DoRA cycle evidence](PUBLICATION_CYCLE_CLOSURE_20261029.md) remain unchanged.
This packet used their format/provenance contracts and synthetic fixtures. It did
not replay real reconstruction or claim that every historical receipt already
satisfies the stricter current input profiles. No private record entered tracked
source or an external provider. Existing provider foundation and its capture
receipt helpers remain integrated; no collector framework was duplicated.

Actual repository Python is 3.15.1. All 84 focused stdlib tests pass with `-S`:
16 adapter tests, 34 admission tests (including all 29 old-profile tests), six
preflight tests and 28 unchanged feed/protocol tests. Both new adapter direct CLI
and existing direct consumer CLIs run with site packages disabled. Tests cover
byte/receipt substitution, candidate lineage, literal identity, explicit HTTP
representation, full metadata/language/duplicate preservation, prior history,
strict/malformed inputs, blocked books/HTML, complete combination and dependent
feed/protocol behavior.

No broad harness, native acceptance or source capture was repeated. Current real
artifact compatibility, externally qualified mapping/bridge authority, schema/
engine parity, native typed admission and the [writer runtime prerequisites](PUBLICATION_GUARDED_WRITER_SOURCE_20261029.md)
remain owner-operated gates. No source generation, review value, writer graph,
sharing, activation, notification or schedule is promoted by this packet.
