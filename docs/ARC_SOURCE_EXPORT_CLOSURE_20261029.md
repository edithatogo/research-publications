# ARC source and export source packet — 29 October 2026

Owner: publications source lane `01a1831e-449a-7693-af1a-08bb23391c76`,
`/Users/doughnut/.codex/worktrees/fa70/chhhs-research-publications`, branch
`codex/rims-publications-roadmap`. Entry base:
`e98c6a0b81a33ccdd4d40c5d056d39fa4495156e`, the explicitly supplied locally
qualified integration checkpoint. Hosted CI/main and native acceptance are
separate gates. The parent retains shared contracts, model/report integration,
runtime/dependency promotion, authentication and all native operations.

## Owned dependency closure

- `scripts/prepare_arc_source_collection.py` and its paired test prepare a
  Stopped manual ARC full-source collector using the canonical acquisition base.
- `scripts/prepare_qgip_candidate_export.py` and its paired test close the retained
  QGIP consumer dependency used for the common source-run guard.
- `scripts/prepare_arc_award_export.py` and its paired test prepare a Stopped
  manual ARC award-context export from an existing committed source folder.
- `scripts/read_arc_committed_source.py` and its paired test independently check
  a frozen downloaded commit and derive its twelve-text-field award view. This
  optional reader is included to test complete file coverage, hashes, unknown
  source fields and projection without executing a native flow definition.

These eight paths and this leaf are the entire source packet. Existing canonical
helpers, configuration, dependencies, shared handoffs, models and reports are
unchanged. The original authoring copies remain in place; ignored local receipts
record their entry hashes and final unchanged-byte verification.

## Contracts and failure boundaries

Constructors preserve the supplied qualified SharePoint connection reference and
source mode; the canonical base rejects Invoker mode. No credential creation or
reference conversion occurs. CLI input uses the existing strict JSON parser,
rejecting duplicate keys, nonfinite constants and numeric overflow. Constructors
perform no network operations. Direct `python -S` execution also works outside
the repository with `PYTHONPATH` absent.

ARC collection retains complete native HTTP JSON response values before status
or schema checks, including failed/timed-out responses when available. This is
not certification of original transport bytes. Two serial complete reads enforce
500-row pages, at most 100 pages/50,000 awards, exact metadata/row coverage,
nonempty unique keys, and full data-row equality per page sorted by ID. Unknown
fields remain in the raw files. The commit manifest follows complete coverage
and exact stored-content readback.

A non-resetting failure flag blocks later page passes and final manifests.
HTTP failure and skipped/failed page tails latch the flag; full-set comparison
failure also latches it. ARC export initializes that flag before reaching its
source folder. Nested output-write/readback failures fail the page comparison
and skip its increment. Candidate conversion retains the same failure guards.
All generated HTTP and SharePoint actions have retry policy `none`. Fresh
output folders require an exclusive 201 response with zero items; an incomplete
run is not replayed into an existing folder.

Exports bind the complete source manifest, validate saved request/page identity,
replay both complete reads, and reread the unchanged manifest before committing
derived outputs. ARC outputs are bounded page JSON/CSV files. QGIP emits a
separate candidate-only artifact with `CandidateUnproven`, `Needs Review` and
`CanonicalAdmission=false`; its boolean metadata is not the ARC field schema.

ARC records have exactly these twelve text fields, in order:
`RecordKind`, `Source`, `SourceID`, `AwardCode`, `Title`, `Funder`, `URL`,
`Description`, `Amount`, `Status`, `RetrievedUTC`, `EvidenceHash`.
Amount remains source text; unknown amount/title/description and EvidenceHash
remain blank, and unknown status remains `Unknown`. RetrievedUTC remains text
from the committed source timestamp. A chronological model scalar requires the
separate model owner's explicit conversion. Award context does not establish
opportunity lifecycle, institutional attribution or institutional funding totals.

The offline reader rejects missing/extra/duplicate file declarations, symlink or
escaping files, ambiguous/nonfinite JSON, noninteger page identities, metadata
drift, duplicate award IDs and full row-content drift. It retains the manifest
hash and every complete stored-file hash. CLI results stay under ignored
`private/ops`, are serialized before exclusive creation, and use mode 0600.
Existing evidence is never overwritten.

Configured catalogue binding requires a matching definition preimage, an enabled
ARC context-only entry and the expected endpoint without credentials, port or
fragment. It preserves the complete-source graph. The retained weekly helper
refuses recurrence construction in this manual-only packet. The reader can
explicitly match a historical weekly manifest; that never proves recurrence.

## Evidence and remaining gates

Explicit repo-local Python: **3.15.1**. Four focused stdlib suites pass **33 tests**
(11 source, 6 ARC export, 6 QGIP candidate, 10 offline reader); Ruff and formatting
checks pass. Tests include strict direct CLI behavior, exclusive/private output,
serialization failure before file creation, dependency closure/cycle checks,
initialization ancestry, runAfter failure propagation, unknown-field drift,
complete-file hashes and all twelve text values. The runAfter model is a static
test oracle, not a native WDL engine or runtime proof.

Reader fixtures use fictional local qualification declarations with
`example.invalid` references because private acquisition evidence is absent in a
clean source checkout. Production catalogue qualification is unchanged. No live
captures, provider calls, authentication, native writes, activation, sends or
schedules occurred. Historical native evidence is not refreshed or promoted by
these synthetic checks. Native schema validation, deployment/readback, runtime
failure behavior, actual exports, access and downstream model/report acceptance
remain with their existing owners and approval gates.
