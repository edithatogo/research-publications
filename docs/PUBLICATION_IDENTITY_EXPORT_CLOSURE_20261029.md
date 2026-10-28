# Publication identity diagnostics and multiline export — 29 October 2026

This packet starts at `b04ce59600fae45c47f01a131d39886e99566f7a` in
`/Users/doughnut/.codex/worktrees/fa70/chhhs-research-publications`, branch
`codex/rims-publications-roadmap`. Delivery chat
`01a1831e-449a-7693-af1a-08bb23391c76` owns these publication identity/export
scripts, tests and leaf handoff. Integrator chat
`01a182f2-fd8e-7953-9bd2-f9b8002664a6` retains integration and shared/native scope.
No shared build/model/contract, registry decision, native setting or authentication
operation is included. The original authoring checkout remains read only.

## Bounded source closure

These are the eight identity files identified in the prior
[finite disposition](../audit/publication-source-disposition-20261029.json):

| Retained source and paired test | Delivered independent behavior |
|---|---|
| `build_publication_identity_resolution_packet.py` / `test_publication_identity_resolution_packet.py` | Exact saved PMID/DoRA-source joins retain all legacy identities, PUB keys, ambiguous candidates, original rows and unresolved membership. Shared handles preserve every linked registry ID rather than overwriting an earlier ID. Positive ASCII PMID guards reject zero, padding, Unicode digits and duplicate typed identities. |
| `build_unified_publication_review_queue.py` / `test_build_unified_publication_review_queue.py` | A new optional `build_diagnostic` handles complete cohorts independently of review status and the old 16/709 counts. Original values, dates and model reference rows are preserved; exact references remain presence evidence. The dated review-snapshot profile remains explicit compatibility only. |
| `plan_publication_organisation_backfill.py` / `test_publication_organisation_backfill_plan.py` | Read-only logical organisation candidates reuse the qualified policy matcher, preserving source intervals and unknown dates. Any populated/partial existing organisation attribution blocks a replacement proposal. Original rows and exact part hashes remain in the plan. Native schema qualification stays false. |
| `registry_publication_crosswalks.py` / `test_registry_publication_crosswalks.py` | Frozen typed related-publication references require exact handles, namespace/source hashes and repository identity. Raw DOI spelling and missing source datestamps remain visible. Distinct handle evidence is not coalesced merely because normalized DOIs agree. No funding, registry admission, identity merge or review authority is created. |

The imported code was reviewed and narrowed/hardened, with paired failure cases.
Results explicitly retain candidate-only, no-write, no-merge and no-review
authority. Diagnostic output is detached from mutable input evidence. CLI outputs
use exclusive new-file creation so a rerun cannot overwrite an existing packet.
No actual historical row or operation was reopened.

### Historical queue compatibility

`build` retains compatibility with the dated 16-PubMed/709-DoRA snapshot and
reports `historical_snapshot_only=true` and
`routine_admission_prerequisite=false`. Its old Pending/Needs Review checks apply
only to that snapshot profile. CLI use of it requires
`--historical-review-snapshot`; the default CLI selects the independent current
presence diagnostic instead. No routine per-record human gate is introduced.

The current diagnostic accepts existing Included, excluded and reviewed values
without changing them. It requires complete evidence before making presence
claims, rejects error/partial envelopes and duplicates, and never matches a URL
suffix or a similar title. The direct DoRA source-key projection uses the existing
canonical namespace rule without adding a second `DORA:` prefix. Stored legacy
registry keys are preserved as original values; this is no registry key migration.

### Exact remaining organisation dependency

`config/publication-organisation-fields.schema.json` is absent in this checkout.
It is not copied, stubbed or silently treated as qualified. The eight logical
candidate field names agree with the retained source schema, but every plan
reports `native_field_contract_qualified=false`, `write_authorized=false` and
the exact missing dependency path. Current native internal names, field types,
permissions and freshness still require the shared/native owner.

The canonical organisation reference retains its dated validity windows. Missing
publication dates therefore remain unknown and may produce no attribution
candidate. Tests of undated aliases use an explicitly undated synthetic reference;
the real reference is not edited to make them match. Existing review/evidence
fields and partial organisation values are never replaced.

## Multiline export fidelity

The retained multiline HTML test is integrated and expanded to cover CSV
roundtrip of embedded CR/LF, quotes, Unicode and escaped literal text; range dates
keep unknown year/month fields empty. Formula-shaped text retains the canonical
spreadsheet safety prefix while source values and visible citation text survive.
Existing output directories remain protected against overwrite.

The new test reproduced a real source bug: HTML metadata contained literal CR
characters that universal-newline readback normalized, causing exact fidelity
verification to fail. A one-expression renderer fix emits CR as `&#13;` in complete
metadata. The reader recovers the original CR/CRLF; visible citations continue
using escaped `<br>` boundaries. No expected manifest was regenerated and no
verification guard was relaxed. This is local HTML/CSV proof, not a new native
monthly export or scheduled observation.

## Evidence reused and remaining requirements

The accepted [offline typed comparison](PUBMED_OFFLINE_TYPED_CANDIDATE_20261029.md)
is reused: its five unresolved metadata deltas and two new source identities are
not reclassified or corrected. Only its small hash-bound comparison receipt is
read for this packet. No large XML reconstruction, provider harvest, registry
read/write, flow invocation or native export was repeated.

Ignored lane evidence is under `private/ops/publications-identity-export/`:
retained/lane source dispositions and hashes, comparison-reuse receipt and test
logs. Private bindings, native journals and authentication remain with their
existing owners. The previous public disposition remains an immutable snapshot;
this handoff records the scoped follow-through on its eight identity files and
multiline test.

Before operational use, remaining requirements are:

1. Frozen snapshot provenance/completeness and exact current identity-consumer
   contracts for the intended target. Candidate counts are evidence rows, not
   accepted unique publications, resolved identities or admission decisions.
2. The missing organisation field schema and qualified reference/validity behavior
   for the selected native sink, plus fresh protected-field preimages and rollback.
   These source diagnostics provide no apply operation.
3. Native consumer acceptance of related-publication evidence, including handle
   versus DOI identity and missing datestamps; no grant-funding relationship is
   inferred by this publication projection.
4. The existing notification, native schema, 61-part model baseline, H03/H04 and
   operational gates remain separate. Read-only notification qualification is a
   subsequent assignment; no notification state is claimed current by this packet.

No dependencies, runtime, hooks, workflows, sharing, settings or schedules changed.

## Verification

Existing repo-local Python: 3.15.1. Focused checks: 55 tests and 43 subtests pass.
Full harness: 1,161 tests with 25 existing capability skips, 446 project checks,
web-first contracts, Conductor structure and tooling preflight pass. All nine
imported identity/export source/test files pass Ruff and formatting; the renderer
passes affected syntax/undefined-name checks. The new CR/CRLF case reproduced the
failure before the fix and passes afterward. No test skip, retry plugin or native
operation was added. These checks prove source behavior only.
