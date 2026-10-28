# DataCite output relationship source closure — 29 October 2026

Owner: acquisition/publications lane `01a1831e-449a-7693-af1a-08bb23391c76`,
`/Users/doughnut/.codex/worktrees/fa70/chhhs-research-publications`, branch
`codex/rims-publications-roadmap`. The clean branch fast-forwarded without reset
from `f6b83d5ffc7d06bec69554228a58085d3ea56fd7` to verified PR69 main
`30bd1e9fd9559ac277089ffeef91ec41d9095134` before writing. Parent-supplied exact
main receipts: quality `40767034102`, security `40767034100`. Parent owns source
integration; this packet makes no native acceptance claim.

## Three-path disposition and user journey

- New `scripts/prepare_datacite_output_relationships.py`: pure reader/API plus
  a private create-only JSON CLI.
- New `tests/test_prepare_datacite_output_relationships.py`: focused fictional
  archive, generation, paging, occurrence, revision and CLI cases.
- This leaf. No shared helper, contract, dependency, runtime, native object or
  coordination file changed.

The retained `build_retained_research_relationships.py` DataCite function and its
tests were references only. Its dated private paths, fixed query/DOI counts,
unrelated source families and people/ROR import are not brought across. Existing
original code, captures and acceptance receipts remain in their owner's checkout.
The already integrated publication/award crosswalk packet is reused, not repeated.

The source journey is: select a pinned complete DataCite archive and independent
canonical generation, obtain Dataset/Software-to-publication assertions with the
source's literal relation/version and every occurrence, then review explicit
ambiguity/unmapped/type diagnostics. No publication or output is admitted or
counted as another publication by this operation.

## Supported collector profiles

`prepare(folder, publications, *, expected_manifest_sha256, generation, ...)`
supports two explicit profiles:

1. `exact_doi` (default): the reviewed `datacite_source.capture` archive with
   `manifest.json`, every declared raw response/error body and
   `related-outputs.json`. Exact ordered DOI scope, scope hash, query/page totals,
   source URLs, statuses, attempt lineage, raw bytes and the complete recomputed
   collector projection must agree. Completed retry bodies remain retained
   evidence. Reused complete-query prefixes bind the recorded prior receipt hash;
   the consumer never follows that prior private path or performs recovery.
2. `native_cursor`: the existing `rims-datacite-discovery-v1` archive. It requires
   raw downloaded-file receipt bytes and a separately supplied SHA256 pin. This
   is the retained receipt shape with `run` and a filename-to-`bytes`/`sha256` map.
   Every selected file, the manifest, scope, publication input snapshot, each
   query completion, each page and the final completion marker must agree.
   The receipt's run must match the manifest's capture run. The independent
   canonical generation additionally binds `native_receipt_sha256`.

Bounded metadata inspection of the retained native archive confirmed the profile:
discovery-v1, a full reconciliation, 76 query summaries/pages, 76 query completion
files, scope/input snapshots, completion marker and a 156-file download receipt
with lengths/hashes. The largest selected file is below the reused 16 MB bound.
Only shape, counts, sizes and proof metadata were inspected. No real record was
emitted, capture replayed, query run or native verification rerun. The required
byte-proof metadata exists; known native format support was implemented rather
than deferred as an external blocker. Private fingerprints stay in ignored
lane evidence, not this document.

Native scope determines institutional queries, page size and related-DOI batch
size; no fixed 65/76-query or 1,281/1,501-DOI assumption exists in code. Each saved
request must retain the exact query/window, opaque cursor and full metadata
options. HTTP status/count types, original XML metadata presence, complete row
and unique-ID totals, terminal state and endpoint are checked. Continuation
origins, scope-changing parameters and cursor cycles fail closed. No link or
cursor is followed.

Full baselines bind their own cutoff. Overlap updates require separate prior
manifest bytes/pin, also bound by `generation.prior_manifest_sha256`; prior
scope/baseline/publication population must agree, cutoff must advance and the
institutional window must have the exact seven-day overlap. Related queries
retain their complete created-through-cutoff population. An update is complete
for its declared windows, not a replacement of prior baseline history.

Complete query/page bytes already downloaded from retained prior native folders
are supported in the flat frozen bundle. Original `archive_folder` pointers
remain per-occurrence provenance, never filesystem or service instructions.
Independent receipt hashes bind the materialized files. Missing proof, unsafe or
extra files, failed/partial snapshots and incomplete queries raise explicit
refusals; they never become empty output or zero Software findings.

## Independent generation and same-byte evidence

Generation requires source `datacite`, explicit generation/canonical/source
snapshot identities, complete/unpaged state, manifest and source scope hashes,
typed canonical-publication digest, exact publication count and query count.
The source snapshot ID is the collector generation ID or native capture run.
Canonical keys must be unique; DOI/PMID shapes are validated. Pins must come
from the authorised evidence owner, not be recomputed from an untrusted folder
as a substitute for independent evidence. These checks do not authenticate a
receipt, establish current permission, human review or source freshness.

Every selected file is read once into an immutable byte cache. Hash, length,
strict JSON, page interpretation and projection use that buffer. Duplicate JSON
keys, nonfinite numbers, boolean counts, symlinks, unsafe names, unlisted files,
contradictory governing status/flags and source/projection disagreement reject.
Qualified canonical strict JSON, DataCite identity/projection/page checks,
governing-envelope rules, DOI/fingerprint and private verified-write helpers are
reused unchanged. No dated monolith or native transport is imported.

## Literal values, grain and counts

Only literal source `Dataset` and `Software` labels enter selected relationship
rows. Other, absent and unfamiliar types produce visible diagnostics with the
full source record; they are not inferred into a category. Unknown/null/empty
versions and unfamiliar nonempty relation strings remain source values. Relation
direction is preserved as DataCite output to publication with its original
`relationType`, without reversing or turning it into a causal/funding claim.

Assertion identity binds output DOI, publication DOI, version, literal related
identifier/type/relation and diagnostic reason. Identical repetitions aggregate
all `SourcePaths`, including file hash/length, record/relatedIdentifier JSON
positions, request URL/parameters, query key, raw provider date and original
native folder pointer. Differing literal spellings remain distinguishable.
Conflicting content for one output DOI across overlapping queries is refused.
Raw record IDs, DOI spellings, relation values, versions, unknown fields and XML
remain available in `SourceRecord` and the immutable source files.

Related-query targets are preserved per occurrence. Institutional queries have
no fabricated requested DOI: their occurrence-level requested DOI is null.
An explicit institutional record reference can still match a supplied canonical
publication, while coverage separately reports that its DOI was not queried.
Ambiguous canonical matches keep an empty key and all candidate keys; unmapped
and missing-reference records remain diagnostics. No identity is invented.

Coverage counts unique explicit Dataset/Software DOI records, assertions and
unselected/unknown types separately. A zero is qualified only for the complete
declared source scope and literal source labels. It does not prove global
absence. Unqueried canonical publications remain counted explicitly. Canonical
publication count/key-set digest and resolved distinct keys are separate from
assertion counts; overlapping queries or repeated references cannot multiply
the canonical population. Missing a later assertion is not withdrawal authority.

Replaying identical inputs is deterministic. Revision hashes bind profile,
manifest and the full independent generation; changed source or canonical
snapshot produces another immutable revision. Every row/diagnostic and packet
has false canonical/mutation/native admission flags and unreviewed candidate
status. No human disposition or prior history is replaced.

Native cutoff, capture observation, provider HTTP date and record version remain
distinct. A cutoff never fills an absent capture observation. Unknown native
capture/provider dates stay null; original source dates remain in source records.

## CLI and verification

The CLI accepts `--capture`, `--publications`, `--generation`,
`--manifest-sha256`, `--output` and optional `--profile native_cursor`,
`--native-receipt`, `--receipt-sha256`, `--prior-manifest`, `--prior-sha256`.
There is no acquisition/apply command. Outputs remain below this worktree's
ignored `private/ops`, outside the immutable archive. Finite serialization occurs
before output creation; exclusive mode-0600 verified writes retain fsync/readback
and overwrite refusal. Source API calls perform no writes.

Actual repo-local Python **3.15.1** passes **24 focused stdlib tests** with `-S`:

```sh
.venv/bin/python -S -B -m unittest discover -s tests -p test_prepare_datacite_output_relationships.py -v
```

Ruff and formatting checks pass. Tests exercise both direct CLIs outside the
repository with `PYTHONPATH` absent, one-read proofs, multipage and cursor
coverage, independent receipt drift, overlap/prior pins, reused query pointers,
strict/contradictory envelopes, repeated occurrences, literal types/versions,
canonical ambiguity/unmapped cases, zero/unavailable distinctions, revision
replay and canonical totals. All payloads are fictional. Local native-profile
fixtures do not establish new native WDL, storage, permission or runtime proof.

Remaining G06-H01 gates are trusted current source/canonical/authority associations,
permissions and reviewed identity reuse. G06-H02 still needs the exact existing
native schema/preimages, authorised protected persistence/readback, bridge/model
cardinality and unchanged consumer totals. G06-H03 needs reviewed live links,
correction/withdrawal history and recovery. No provider/authentication request,
native write, schedule, activation, accepted-history replay or real relationship
admission occurred. Source integration remains with the parent.
