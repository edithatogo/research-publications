# Publication award-crosswalk source closure

29 October 2026. Dependent source base:
`f6a05a5f47007fb1e416890419ee6770ec43f545`. The parent reviewed and locally merged
that exact relationship dependency and authorised continuation on this clean
branch pending the combined hosted milestone. This is not verified-main or
native acceptance. Native scope is none. No provider calls, collectors, stores,
model/report edits, source replay or environment changes occurred.

## Finite source disposition and dependency closure

Four retained paths were absent at this base. Their original bytes were verified
against these SHA-256 pins before copying from the read-only authoring checkout;
all four are amended in this packet:

| Retained path | Original SHA-256 |
| --- | --- |
| scripts/award_identifier_crosswalks.py | 10319ddc5490be9f10e2b0040c7c5bf3cb9b9ff2246f0758ebe7625eb288a3dd |
| scripts/crossref_award_crosswalks.py | 128f7513f47cfb01a4d4772005f4efd3c2d6819130b5b73f881f31820bedf309 |
| tests/test_award_identifier_crosswalks.py | b02abc6522ab20fa8208fd29221d0299572dd8c810ee35ffd9d8cd15d18ad5bf |
| tests/test_crossref_award_crosswalks.py | 64dbc39046be8b3fb83eb5c49bf541e792ce0e0b59a930fa748b72406901d4d8 |

The two helpers use standard library plus unchanged canonical
`source_relationship_evidence.normalise_doi`/`fingerprint` and
`plan_publication_stub_restore.strict_json_loads`/`utc`. Those reused canonical APIs are
unchanged. Neither retained helper exposed a CLI; this packet remains a pure
read-only file/API projection without an output writer or native transport.
Package and direct-module imports both close under Python `-S`.

The G06 plan's **Crossref-to-ARDC exact award identity guard — 25 October 2026**
records corrections in a separate retained builder. Those corrections are
carried here as explicit no-padding DOI/PMID/PURL/award checks and exact PURL
namespace/identifier agreement. Prefix variants, similar titles, funder names
and search results cannot establish an alias.

## Independently pinned inputs

`qualify_award_alias` now requires `authority_sha256`. Its authority object
contains `complete: true`, exact `ror`, single-segment `namespace`, unique exact
`fundref_dois`, `authority_raw_sha256` and nonblank `evidence_ref`. Crossref
supplies its actual FundRef DOI through `source_funder_doi`; it does not invent
that source's ROR by passing the authority ROR back to itself. Direct callers
may instead supply a source ROR already supported by their own evidence.

`project_packet` requires `expected_manifest_sha256`, `authority_binding`,
`authority_binding_sha256` and `generation`. The independent binding must agree
with the captured ROR record ID, raw hash, NHMRC website and exact FundRef set.
A rehashed outer packet cannot rebind a changed authority while retaining its
independent pin. Pins must originate from the authorised capture/authority owner,
not be computed from an untrusted folder as a substitute for that evidence.
These checks bind supplied evidence; they do not establish its authenticity,
current permission, human review or institutional authority.

Generation requires complete/unpaged status, nonblank `generation_id` and
`canonical_snapshot_id`, `source_snapshot_id` equal to the retained batch,
`manifest_sha256`, typed `publications_sha256`, and exact actual-integer
`publication_count`, `crossref_count` and `ardc_count`. Canonical identities must
be unique; PMID remains ASCII positive text and DOI normalization is limited to
the existing explicit URL/case convention after rejecting padding. Ambiguous
canonical DOI assignments retain an empty key and explicit match count.

## Complete snapshot and exact matching

The manifest declares the existing `publication_award_crosswalk_retention_v1`
NHMRC scope, complete/unpaged status, batch, exact `file_count`, `crossref_count`
and `ardc_count`, and full file/query inventories. Every file is read once;
hash, actual-integer byte length and strict JSON parsing use that same buffer.
Duplicate JSON keys, nonfinite numbers, unsafe paths, symlinks, missing/unlisted
files, duplicate/overlapping references, unreferenced inventory entries and
provenance-hash disagreement are refused. A file cannot be certified solely by
its own newly recomputed manifest hash.

Each query requires actual-integer HTTP 200, explicit complete/unpaged state and
an observation timestamp or unknown null. Crossref URL/request/returned DOI
identities must agree. ARDC query URL/identifier, offset zero, exact numFound /
record count and terminal pagination must agree. This packet handles a complete
single response per identifier, not a new multipage collector. Failure envelopes,
boolean counts and duplicate query/record IDs fail validation even when rehashed.

Grant identifiers must be exact supported single URI segments. Unsupported
values block qualification rather than being trimmed, prefixed or rewritten.
Grant records retain text IDs without `str()` coercion. Explicit identifiers
must be unique arrays, never strings used for substring matching. A positive
technical alias needs one exact HTTPS PURL on `purl.org`, matching the pinned
namespace and original award number, with that number also explicitly listed.
Other hosts/ports, prefix variants and PURL/identifier disagreement never create
a positive edge. Multiple distinct matching records remain ambiguous.

## Candidate grain, diagnostics and history

Missing numbers/lookups, no-exact-match results and ambiguous grant records emit
`publication_award_crosswalk_diagnostic` rows with empty ToKey and explicit state;
ambiguity is not silently dropped. Exact aliases emit
`publication_award_crosswalk`, still candidate-only. Unselected funder namespaces
are outside the explicitly NHMRC-scoped projection, not zero funding findings.

Rows preserve original award text, raw/requested/returned DOI provenance, exact
source hashes/URLs, authority-binding hash, unknown observation dates and all
repeated funder/award occurrence paths. One repeated assertion remains one row.
`AliasMatches` retains ambiguous record identities. `ReferenceType` remains JSON
text alongside the established SourceWorkID/FromKey/ToKey/RawSHA256 fields.

`SourceBatch` preserves the supplied label. `SourceVersion` is the immutable
manifest-byte digest, explicitly labelled by `SourceVersionKind`, so a changed
capture cannot silently reuse the same version merely by retaining its label.
`ProjectionRevisionSHA256` additionally binds authority policy and canonical
input; generation and snapshot identities remain explicit. Consumers must retain
that versioned evidence grain and count distinct publication/award identities
under filters rather than sum assertion or occurrence rows. Missing a prior
assertion in a later source snapshot is not withdrawal authority. This helper
neither deletes history nor updates human reviews/corrections.

Every row has candidate confidence and false `IdentityQualified`,
`CanonicalAdmission`, `MutationAuthorized` and `NativeG06Admission`. The technical
`source_supported_alias` state means exact source identifier support only; it
never means confirmed funding, current award status, institutional attribution,
allocation/expenditure or outcome contribution. Existing G06 native schema is
unchanged, and its normalizer rejects direct admission of these assertion rows.

## Verification and remaining dependencies

Repo-local Python reports 3.15.1. All 24 focused stdlib unittest methods pass
with `-S`: all 14 retained methods plus ten new methods. There are no skips or
pytest-only functions. Tests cover independent authority tampering despite
recomputed outer hashes, generation drift, exact identifiers, counts/pagination,
strict JSON, inventory/symlink/source failures, visible ambiguity/missing lookups,
immutable inputs, one-read hashing, occurrence deduplication, replay/revision
hashes, unknown dates, bridge/filter implications and refusal of native admission.

```sh
.venv/bin/python -S -m unittest discover -s tests -p test_award_identifier_crosswalks.py
.venv/bin/python -S -m unittest discover -s tests -p test_crossref_award_crosswalks.py
```

Government/workbook crosswalks remain separate: they add openpyxl and independently
pinned upstream-original workbook/coordinate semantics. Protocol/PDF evidence
remains separate with `qualify_protocol_award_metadata` and its PDF/text/study
lineage gates. Neither family is imported or qualified here.

G06-H01 still needs trusted current authority/canonical/source associations and
source permissions. G06-H02 still needs the exact native schema, scope, complete
preimages, permissions, typed bridge persistence/readback and model/cardinality
acceptance. G06-H03 still needs authorised reviewed live links, correction and
withdrawal history plus recovery and unchanged publication totals. No real alias
capture was replayed and no native graph, funding fact or authority was accepted.

## Governing-envelope review correction

A shared local validator now rejects contradictory known control evidence in the
manifest, canonical generation, Crossref/ARDC query envelopes and direct authority
binding. Presence of `error`/`errors` is disqualifying even if empty/null, matching
the existing failure-envelope convention. Known partial/incomplete/truncated or
failure/has-more flags must be explicitly false; supplied completion/success
flags must be explicitly true. Known continuation links/tokens/cursors must be
terminal, and explicit failed, partial, incomplete or nonterminal status/state/
outcome values cannot coexist with a completeness claim.

The validator is limited to these governing envelopes and does not recursively
reinterpret ordinary provider metadata. Unknown observation timestamps remain
null. A positive regression retains nested source annotations containing error/
partial words and terminal indicators without fabricating dates. Native
admission and authority flags remain false.

Three new focused methods exercise direct authority binding plus every governing
envelope with otherwise valid hashes, independent pins and counts, and preserve
the unknown-time/source-metadata case. The direct binding regression first
reproduced the gap. All 27 focused stdlib methods subsequently pass on Python
3.15.1 with `-S`, including the previous 24. No shared or native changes occurred.
