# Publication provider source closure — 29 October 2026

Source-only packet from canonical `632224327b00b1f8794a32c93c346a31a1d1bb15`.
It closes two pure adapters and their paired tests from the nine-file
`retained_provider_dependency_packet` in the [frozen inventory](../audit/publication-source-disposition-20261029.json).
No provider, authentication, cache, tenant, capture, schedule, flow or register
operation is performed. Shared contracts, dependencies, runtime, locks, model,
Conductor and original checkout remain unchanged.

## Raw publication DOI input proposal

`scripts.prepare_raw_publication_doi_inputs.with_raw_producer_dois` retains the
existing legacy DOI union for a Stopped normal Crossref or DataCite definition.
Recovery/extension graphs and existing raw-input transformations are refused.
The stricter preparation API requires:

- `document`, `archive_parent`, and the explicit ordered `producers` tuple/list;
- `preimage_bytes` and `expected_preimage_sha256`, matching both the exact raw
  input bytes and the supplied document's complete JSON value;
- `checkpoints`, keyed by exactly the requested producers. Each proof supplies
  `raw_bytes`, `sha256`, `length`, exact `name`, `file_id` and non-wildcard `etag`.

Proofs validate full marker bytes/hash/length, source/format, explicit completeness
and unfiltered status, run/folder/file identity, unique positive source keys,
integer count, declared scope hash and nonblank own-DOI provenance. Duplicate JSON
keys, nonfinite JSON, error/partial envelopes, malformed identifiers and stale
preimages fail closed. The declared scope hash is retained evidence; this adapter
does not independently certify its provider-policy meaning or native origin.

The proposal replaces the retained adapter's newest-marker discovery with exact
file-ID reads and pinned name/path/length/ETag guards. It proposes a metadata
recheck after content retrieval and compares the connector's saved base64 content
to the entire frozen marker before parsing. The byte comparison is deliberately
literal: no unsupported native SHA256 function is invented. Complete raw marker
bytes supply this proof; no publication XML, PDF or provider payload is embedded
or reacquired. The generated connector response shape, expression/definition size
and actual saved-byte behavior remain unqualified until a separately assigned
native adoption checks the exact target. Local tests do not execute WDL or prove
those native behaviors.

Parsed marker provenance carries the exact filename, source byte hash, file ID,
ETag and length. Own DOI spellings remain in the immutable marker; only derived
related-source inputs are normalized. The retained conditional resolver behavior
is preserved: PubMed alone lowercases/trims; inclusion of DoRA enables anchored
`doi:` and DOI-resolver removal. Percent-encoded suffixes are not decoded. An
explicit locally validated DOI set replaces the old loose `10.`/slash shape
filter. Invalid nonblank values remain diagnostic rather than being promoted;
empty values are not invented identifiers. None of this admits publications,
merges identities or establishes archiving permission.

Only new raw-read/validation actions, the existing union's inputs/dependencies,
the Manifest input fields and optional DOI-source snapshot input fields change.
The original union remains nested intact. Unrelated actions, authentication
fields, recurrence and evaluated recurrence, connection references and the rest
of the source envelope are preserved. The retained global cleanup is excluded.
Same-input replay yields the same proposal; applying the transform to an already
prepared graph is refused instead of nesting or overwriting its action namespace.

The CLI accepts a local definition, explicit preimage hash and checkpoint proof
JSON. Proof JSON supplies each local marker `path` plus the proof fields above;
the CLI reads its bytes locally. Its output is an exclusively created plan
envelope containing the proposal, preimage path/hash and `native_acceptance:false`.

```sh
.venv/bin/python -m scripts.prepare_raw_publication_doi_inputs \
  --document private/ops/current-definition.json \
  --preimage-sha256 '<exact-current-file-sha256>' \
  --checkpoints private/ops/frozen-producer-proofs.json \
  --archive-parent '/Documents/Archive' \
  --output private/ops/new-raw-input-plan.json
```

There is no apply command. Before any later native save, the assigned owner must
recheck the actual current preimage and exact pinned marker identities/content,
qualify connector/body/expression behavior and retain the existing recovery and
activation gates. A complete frozen marker does not prove current freshness,
collector success, consumer admission or a new source generation. No dynamic
"latest" fallback or accepted-capture rerun is queued here.

## Retained PubMed own identifiers

`scripts.oa_pubmed_retained.identifiers` reuses the current strict
`publication_source_metadata_contract.reconstruct_metadata_rows`. It checks
positive ASCII PMID text, complete ordered chunk counts/length/encoding and exact
UTF8 JSON reconstruction without mutating row order or evidence. Only the own
`PubmedData/ArticleIdList` contributes PMID, DOI and PMCID; cited references and
free text do not. Ambiguous or malformed own identifiers, zero/padded PMCID
identities and missing or foreign/book structures fail closed. An absent optional
DOI/PMCID stays absent rather than being inferred.

The formerly absent `oa_paper_locations.normalize_doi` dependency is replaced
with the same narrowly internal pure normalization behavior: trim, remove one
anchored HTTP(S) `doi.org`/`dx.doi.org` resolver, validate the retained DOI shape
and lowercase. Explicit parity tests preserve case handling and encoded suffixes;
they retain rejection of the unsupported `doi:` prefix and do not silently use
the broader canonical/Crossref normalizers. No OA framework is imported.

The result retains the exact reconstructed source metadata SHA256,
`archiving_eligibility: not_evaluated` and `native_projection_applied: false`.
A PMCID is discovery evidence, not a licence, full-text eligibility decision,
download instruction or authority to archive. A create-only local CLI is available:

```sh
.venv/bin/python -m scripts.oa_pubmed_retained \
  --rows private/ops/retained-pubmed-chunks.json --pmid '<exact-positive-PMID>' \
  --output private/ops/new-own-identifiers.json
```

## Complete nine-file disposition

| Frozen family file | Current disposition / exact remaining dependency |
| --- | --- |
| `scripts/prepare_raw_publication_doi_inputs.py` | Delivered pure proposal adapter with exact input and marker proofs; native rewiring excluded. |
| `tests/test_prepare_raw_publication_doi_inputs.py` | Delivered stdlib discovery suite, including malformed proofs, drift, replay, preserved action/envelope scope and local CLI failures. |
| `scripts/oa_pubmed_retained.py` | Delivered pure own-identifier recovery with internal legacy normalization and strict shared chunk reader. |
| `tests/test_oa_pubmed_retained.py` | Delivered stdlib discovery suite, including normalization parity, reference exclusion, identity/chunk ambiguity and local CLI behavior. |
| `scripts/prepare_pubmed_acquisition.py` | Retained, not imported. Needs absent `prepare_qgip_source_collection.build/compose/gate`; current `collect_pubmed.validate_config/BASE` already exist. Its bounded-recovery function also imports absent `patch_clinicaltrials_read_retries.definition_sha256/POLICY` and requires an existing durable `Observe_failed_generation` preimage. The base builder does not supply that observer. The retained policy permits three exponential retries only on three exact read-only ESearch/EFetch POST leaves; it is not a licence to retry SharePoint effects or start a run. |
| `tests/test_prepare_pubmed_acquisition.py` | Retained with that exact scaffold, retry/hash and observer dependency. Fake observer insertion in a local test does not prove native durable failure behavior. |
| `scripts/prepare_dora_publication_collection.py` | Retained, not imported. Needs the same absent QGIP scaffold and qualified Embedded SharePoint reference contract. Full collection before/after reconciliation and own-DOI completion-marker behavior remain the selected acquisition scope. |
| `tests/test_prepare_dora_publication_collection.py` | Retained with the scaffold dependency. Canonical `prepare_dora_metadata_cycle` consumes retained metadata and is not a full-collection acquisition replacement. |
| `scripts/capture_query_pubmed_source.py` | Historical capture execution path retained, not imported or rerun. Requires absent `capture_retained_canary_acceptance`, `capture_native_source_pages` and `query_pubmed_projections` runtime helpers. Its entry hard-codes42part comparisons, invokes Azure CLI/Fabric token routes and uses fixed historical query/cache paths. A current exact-part/target/auth/processing-chain contract is required before any new capture adaptation. Preserve old receipts; do not relabel them current or rerun accepted captures. |

The missing QGIP builder depends on the already present `grants_qld_qgip_api`, but
its broader acquisition graph is not needed merely to obtain an envelope. Any
later bounded scaffold migration/adaptation requires parent-assigned shared source
ownership and direct tests; it is not imported here. The canonical NIH acquisition
builder targets Grants.gov and is not a PubMed replacement. Existing Crossref and
DataCite failure-observer builders are source references, not proof that the
PubMed graph already has an appropriate observer.

The accepted [offline PubMed candidate](PUBMED_OFFLINE_TYPED_CANDIDATE_20261029.md)
and [identity/export closure](PUBLICATION_IDENTITY_EXPORT_CLOSURE_20261029.md)
supersede repeating retained reconstruction/comparison for the same inputs. They
do not supply a current native capture transport or certify source freshness.
Original bytes for all nine files remain unchanged against the frozen inventory.

## Focused verification

Actual repo-local Python3.15.1. Stdlib discovery passes **14 raw DOI tests and
8 own-identifier tests**, including local CLI create-only output and failure
preservation. Ruff check/format and leaf link/diff checks pass. Original dependency
failure and changed-behavior failing tests are retained in ignored
`private/ops/provider-source/`, alongside original hashes and final focused logs.
No broad harness or accepted native capture is repeated for this packet.
These results establish local source behavior only; native/operational acceptance
and every source/object owner remain separate.
