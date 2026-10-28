# Retained source relationship evidence closure

29 October 2026. Base: `e98c6a0b81a33ccdd4d40c5d056d39fa4495156e`, the
parent's frozen, locally qualified integration commit under the CI resource
exception. It is not asserted to be hosted-CI-verified main. This packet owns
only the helper, paired unittest file and this leaf. Native scope is none: no
provider calls, replay, store/model/report changes, native transport or new CLI.

## Scope and dependency closure

The retained module is a pure projection of OpenAlex work assertions,
ClinicalTrials.gov RESULT/DERIVED publication references and structured PubMed
Author/GrantList/DataBankList metadata. All original imports were standard
library. The amendment reuses already canonical `strict_json_loads` and `utc`
from `scripts/plan_publication_stub_restore.py`; their existing standard-library
closure is verified by `-S` execution. No dependency, runtime, G06 contract,
coordination or Conductor record is edited.

The following retained paths were absent at the frozen base; both are amended,
not copied as an accepted native graph. Original SHA-256 values:

- `scripts/source_relationship_evidence.py`: `d5272f4b695fe3e538881f8f9202f98a4b093ed534243a164fd728d995bc768b`.

- `tests/test_source_relationship_evidence.py`: `49d7df4c3b6858bcd06a57d063a9b7c55cac365a84161d8499610598539886c4`.

Separate retained `build_retained_research_relationships.py`,
`datacite_source.py`, `prepare_source_relationship_model.py`,
`prepare_source_relationship_report.py` and later award crosswalk families are
outside this closure. They require their own dependency and contract review.
DataCite dataset/software and NIH RePORTER PMID/award relations are not implemented
by this module; no missing or unknown source slice is fabricated to satisfy them.

## Generation and provenance contract

The three public projection functions require keyword `generation`. The caller
must independently supply complete/unpaged source and canonical scope, exact
source kind (`openalex`, `clinicaltrials.gov`, or `pubmed`), nonblank
`generation_id`, `canonical_snapshot_id`, `source_snapshot_id`, actual-integer
`source_count`/`publication_count`, and exact `source_sha256` and
`publications_sha256` values. `fingerprint` uses typed, deterministic JSON,
including distinctly tagged raw byte buffers. It rejects unsupported values and
nonfinite numbers. These pins bind supplied inputs; they do not authenticate
source authority, prove institutional coverage or supply native acceptance.

Canonical keys must be unique exact text. PMID text is not coerced from numbers;
DOI handling is limited to the retained explicit DOI URL/case normalization,
with original bytes/values retained at the source. Ambiguous DOI/PMID-to-canonical
assignments keep an empty CanonicalKey and explicit match count. Names do not
establish identity. Each capture requires successful actual-integer HTTP 200,
`complete: true`, `next_links: []`, and explicit observation time or unknown null.
Unknown dates are not filled with current time or artificial calendar dates.

OpenAlex bytes are decoded, hashed and strictly parsed from the same retained
buffer. Duplicate raw JSON keys, failure/partial envelopes, repeated works/DOI
retrievals and conflicting assertions fail validation. Structured authorship
arrays and award fields must have their declared shapes. Funder IDs scope equal
award numbers; unresolved award namespaces stay explicit unresolved references.

Study captures require raw bytes, their expected SHA-256 and a parsed record
whose typed digest equals strict parsing of those exact bytes. Duplicate study
captures and conflicting reference types are refused. Only explicit RESULT and
DERIVED references produce links; BACKGROUND is not an output relationship.

PubMed's structured metadata has a separate `metadata_sha256` and supplied
source-version reference. Duplicate records, conflicting singleton fields,
duplicate attributes and invalid metadata structure fail. The projection retains
`StructuredMetadataSHA256` while leaving `RawSHA256` empty: transformed structured
metadata is not proof of the original HTTP/XML bytes or its upstream transform.
That native/raw retention association remains an external dependency.

## Assertion grain and safeguards

Every emitted row carries its generation/snapshot/digest bindings, candidate
confidence, `RelationshipAdmission: source_assertion_only`, unauthenticated and
unreviewed status, and false identity qualification, canonical admission and
mutation authority. The retained label `Source-supported` describes a source
assertion only; it is not person authentication, human approval or a confirmed
funding relationship. ORCID syntax/checksum and explicit provider aliases do not
establish authoritative person identity. Equal names remain separate unresolved
mentions. Coauthorship/institution cooccurrence are derived work-local pairs,
not workforce, institutional partnership, project membership or outcome facts.

Repeated identical mentions/references retain all named `SourcePaths` while
producing one relationship assertion; conflicting repeated assertions are
rejected. Pair assertions point to the relevant source collection. Consumers
must count canonical publications distinctly under explicit relation filters,
not count flattened bridge rows or sum award amounts. The tests demonstrate
one publication remaining one through multiple authors, affiliations and
funder-scoped awards. Overlapping providers remain separate source evidence,
not independent corroboration or duplicated publication facts.

Separate calls preserve stable assertion keys plus source versions and generation
IDs; a downstream history store must retain that versioned grain. No existing
history, corrections or human review records are accepted as writable inputs.
`ReviewState: Not reviewed` is a new source-assertion state and must never be used
to overwrite a human review field. Source input objects are copied before use.
This helper does not implement a persistence/upsert or human-review transition.

Explicit OpenAlex retraction and PubMed Retracted Publication markers retain
assertions but set source-retracted state and disable candidate eligibility.
That eligibility flag is a source-retraction diagnostic, not canonical admission
or reviewed qualification. A withdrawn study status is retained as raw context;
it does not imply that an explicit publication reference is retracted. No row is
deleted, and no authority to correct, withdraw or restore native records follows.
The emitted extended assertion schema is deliberately not accepted directly by
`grants_relationships.normalize_relationship`; the existing G06 write contract
is unchanged.

## Verification and remaining acceptance

Repo-local Python reports 3.15.1. All 24 stdlib unittest methods passed with `-S`,
including all 16 retained methods plus eight new methods. There are no hidden
pytest functions, skips, provider calls or new native fixtures:

```sh
.venv/bin/python -S -m unittest discover -s tests -p test_source_relationship_evidence.py
```

Tests cover hashes and generation drift, boolean counts, incomplete pagination,
strict raw JSON, duplicate/conflicting identities, immutable human/source values,
unknown dates, occurrence preservation, source revisions/retractions, study raw
versus parsed drift, structured PubMed provenance and candidate bridge/filter
cardinality. Original scopes of name separation, ambiguous canonical mappings,
ORCID checks, exact references and funder namespaces remain tested. No original
native acceptance or current broader graph qualification is claimed.

Remaining G06-H01 requires authoritative publication/award/funder/person/organisation
keys, trusted source-to-retention associations, current source permissions and
qualified source-specific slices. G06-H02 requires the existing native target's
complete schema/permissions/preimage, scoped typed bridge persistence, exact
readback and model/filter/cardinality preservation. G06-H03 requires separately
reviewed live links, correction/withdrawal history, recovery and unchanged
publication totals after fixture cleanup. Current native identities and review
actors are not inferred from local assertions. Dataset/software, NIH RePORTER
and cross-source award aliases remain separate source packets. This closure
creates no live graph, institutional funding measure, workforce denominator or
verified outcome.

## Review corrections: exact identifiers, occurrences and unknown state

ClinicalTrials.gov RESULT/DERIVED reference PMIDs now require ASCII positive
text (`[1-9][0-9]*`). Unicode digits, zero/leading-zero values, padding, booleans,
numbers and other nontext values fail validation explicitly. Absent/null/empty
reference IDs and BACKGROUND citations retain their documented exclusion; a
malformed background identifier is not promoted into an output link.

Each PubMed accession path now includes
`DataBank/<index>/AccessionNumberList/AccessionNumber/<index>`. Repeated identical
accessions retain distinct occurrence paths on one assertion; multiple IDs retain
their own indexed paths. Raw source work DOI values must be exact unpadded text
before DOI URL/case normalization; padding is rejected rather than silently
matched to the requested identity.

PubMed `SourceRetracted` is true only for the explicit Retracted Publication
marker, otherwise null. Absent, empty or unrelated PublicationTypeList values
cannot establish a negative retraction finding. This module has no separate
qualified PubMed negative-status input and therefore emits no false negative
assertion. `CandidateEligible` merely reports that the source was not explicitly
marked retracted in this supplied evidence; an unknown status may retain this
diagnostic flag while canonical admission, identity qualification and mutation
authority all remain false. Native consumers must not interpret it as admission.

Four new stdlib regression methods first reproduced the review findings, then
passed after correction. The complete focused file now passes 28 methods on
Python 3.15.1 with `-S`, retaining all previous 24 methods and no skips. No shared
files, native objects, source captures, provider calls or environments changed.
