# PubMed offline typed candidate — 29 October 2026

This source-only continuation starts at `3ed171d00a37bc70023994d2e0cbd62bf7ec3e26`
in `/Users/doughnut/.codex/worktrees/fa70/chhhs-research-publications`, branch
`codex/rims-publications-roadmap`. Delivery chat
`01a1831e-449a-7693-af1a-08bb23391c76` owns this packet; integrator chat
`01a182f2-fd8e-7953-9bd2-f9b8002664a6` retains integration, native assignments
and any model/report overlap. No native object is assigned here.

The original authoring checkout and its bindings, environments, jobs and journals
remain read only. There was no provider request, authentication renewal, native
invocation, model declaration change, registry write, send or schedule change.

## Reviewed helper closure

- `build_native_commit_package.py` gains offline chunk reconstruction and frozen
  typed-archive validation. All pre-existing function bodies remain AST-identical.
  Its legacy package builder and hardcoded accepted-baseline guards are preserved;
  it is not a writer for this new candidate.
- `build_native_retention_package.py` changes only package/direct-script import
  selection. Existing function bodies remain AST-identical. No source extraction,
  native package behavior or baseline counter changes were imported.
- `capture_report_bound_source_union.py` imports only four pure retained EFetch
  field/date projection functions, with stricter positive PMID/root validation.
  The retained token, fetch, native capture, refresh and report-binding functions
  are deliberately excluded.
- `publication_xml_metadata.py` preserves complete article element content,
  attributes, unknown fields and serialized article XML, while producing an
  explicit offline XML-shaped JSON profile. Authoritative original XML file
  references and hashes remain available. Serialized article XML is not claimed
  to reproduce the original XML byte spelling.
- `reconcile_pubmed_source_cycle.py` builds the offline candidate and complete
  comparison from supplied frozen bytes. It excludes the retained module's
  native request/readback and historical human-decision packet machinery.

No wholesale retained builder replacement, query/model promotion, collector
expansion, dependency change or shared handoff edit occurred. These pure paths
are dependency-closed; they do not claim the broader retained native adapters
are integrated. Both package-style and existing direct-script imports retain
the canonical package behavior.

## Evidence and reconstruction

The current raw proof verifies all 13 saved XML files and ordered identities,
their exact file byte counts/hashes and the complete 1,279-key raw manifest.
The prior typed proof verifies its exact source-page capture hash, all 173
archive-file hashes/counts, unique terminal pages, error/partial rejection,
three-table equality, committed batch/model/request identity, source key digests,
full metadata payload digest, and author-evidence count/key digest.

The consumed generation reconstructs 1,277 complete metadata documents from
3,963 chunks with 11,731 author-evidence rows. The current offline candidate has:

| Output | Count |
|---|---:|
| Source rows and complete metadata documents | 1,279 |
| UTF8-HEX metadata chunks | 3,955 |
| Metadata hex characters | 65,600,290 |
| Author-affiliation evidence rows | 11,767 |
| Overlapping complete metadata payloads with matching values and node order | 1,272 |
| Overlapping records with preserved metadata differences | 5 |
| New source identities | 2 |
| Prior typed identities absent from current raw XML | 0 |

The five literal metadata deltas concern conflict-of-interest text, reference
text, abstract text and correction/revision metadata. Their exact paths and both
values remain private. They are not reviewed corrections or instructions to
replace registry values.

Source-summary/author projection differences are reported separately. There are
648 records with at least one new identity, metadata, summary or author-evidence
difference; this does not mean 648 full metadata changes. Entity decoding and
plain display text account for many differences. DOI and author differences
remain preserved without identity merging or automatic correction.

### Explicit representation profile

The retained `Xml.Document` metadata contains XML-escaped text and inline markup
inside text values, plus empty elements represented as child lists. The offline
profile reproduces that shape. Comparison preserves all values and child order,
ignores XML attribute ordering and separately recognizes one XML serialization
layer, including numeric entities, inline attributes and empty-element spelling.
Encoded literal tags remain text; they are not turned into formatted elements.
Any normalized comparison still retains the original literal path differences.
No general whitespace, author-name, identity or substantive equivalence is inferred.

The first private diagnostic profile exposed serialization noise. Its artifacts
are retained as `v1`; the corrected `v2` output is the packet's authoritative
offline result. Neither profile proves native engine execution.

## Artifact and source references

Large outputs are on PortableSSD, avoiding the nearly full internal volume:
`/Volumes/PortableSSD/CodexScratch/rims-publications-fa70-typed-20261029-v2/`.
The directory contains `candidate.json`, `comparison.json` and
`differences-private.json`. The ignored lane receipt
`private/ops/publications-pubmed-typed/frozen-comparison-receipt-v2.json` pins
their exact SHA256 hashes and all original input paths/hashes. The final prior
archive validation and canonical-function preservation receipts are alongside it.
No private metadata or actual native target IDs enter tracked source.

Original inputs remain below the original authoring checkout's `private/ops/`:

- `2026-10-28-e01-t11-cli-implementation/source-marker-readback/pubmed.json` and
  `commit.json` in the same directory; `cached-source-cycle/readback.json` and
  its 13 XML originals.
- `2026-10-21-e01-runtime-qualification/raw23-qualified-source-pages.json`,
  `raw23-typed-archive-receipt-private.json` and `raw23-typed-archive-files/`.

The candidate preserves every prior source-summary row verbatim as context,
alongside current source fields and complete metadata. It does not read or edit
registry review fields. A source-generation hash is not a native batch/refresh
identity, and no committed marker is generated for this candidate.

## Exact next admission requirements

1. Assign the exact existing isolated DEV processing/model and typed commit sink.
   Reconcile against a fresh complete preimage; the retained model has 61 parts.
   Legacy 36/42-part or 1,261-record guards are not authority for a new operation.
2. Qualify native schema/engine parity. The candidate contains complete XML,
   source field projections, chunk proof and author evidence; it does not claim
   every native summary column, facility classification, date type or reporting
   dependency is accepted. Prior classification/context is retained separately.
3. Confirm operation-specific permissions, rollback and immutable source-history
   preservation, then require exact definition and full output readback. Never
   silently overwrite accepted titles, notes, attribution or reviewed values.
4. Qualify correction/retraction handling for the new correction metadata and
   retain all five literal deltas as unresolved until that consumer behavior is
   verified. No publication identity or substantive review is decided here.
5. Before any native test, resolve the automatic-mail prerequisites documented
   in [the prior cycle handoff](PUBLICATION_CYCLE_CLOSURE_20261029.md): saved
   per-flow failure alerts are enabled and account weekly failure-digest
   suppression remains unqualified. No native invocation is authorized by this
   source receipt. Runtime, H03/H04 recovery and operational acceptance remain
   separate from this complete offline source comparison.

## Local qualification

The existing repo-local interpreter is Python 3.15.1; locked dependencies and
environments were preserved. The 13 focused tests and 10 subtests pass, including
canonical package generation, complete metadata/author reconstruction, preserved
review context, unknown fields, entities/literal tags, partial/error responses,
missing terminal pages, altered hashes and committed author-digest drift.
Full harness: 1,097 tests with 25 existing capability skips, 446 project checks,
web-first contracts, Conductor structure and tooling preflight pass. New modules
pass Ruff and formatting; affected shared helpers pass syntax/undefined-name
checks. Existing function-body AST parity is recorded separately. These results
prove offline source behavior only.
