# E09 advisory consumer source refinement — 29 October 2026

Delivery chat `01a1831e-cc6d-7371-9d57-021a339b708a`, branch
`codex/rims-grants-roadmap`, actual checkout
`/Users/doughnut/.codex/worktrees/ef45/chhhs-research-publications`.
Clean baseline: `10354634822d373d36be0ef10247390d1f157439`.
Parent assigned advisory source/tests and this leaf only. Shared contracts,
source identity/native-input/builder code, Conductor records, dependencies,
authentication, native objects and original journals retain their owners.

## Retained requirement and missing behavior

The original checkout at
`/Volumes/PortableSSD/GitHub/RIMS/chhhs-research-publications` retains the E09 spec
at `conductor/tracks/collaborative_research_feed_20261022/spec.md`, the refinement
in `scripts/e09_advisory_consumer.py` and its tests, and the explanatory receipt
`docs/E09_ADVISORY_EXTRACTION_20261024.md`. These were inspected read-only.

The existing spec requires bounded evidence-linked advisory extraction with
source/prompt provenance, distinct inferred suggestions and human decisions,
and deterministic/manual operation when optional AI is unavailable or invalid.
The canonical consumer already bounded fields, HTTPS evidence-link syntax,
keyword/URL counts, source/prompt revisions, publication/thread identity and
non-authority. It was missing the retained request-binding refinement:
supplied failure records could describe another request/publication, successful
output could name another advisory request, and expected revisions were unchecked.
Invalid supplied failures could raise out of the consumer instead of producing
its explicit manual fallback.

## Implemented supplied-input behavior

- Validate caller publication/request identity, positive non-boolean expected
  revisions and the fallback date before either success or failure consumption.
  Invalid caller controls raise ValueError; no valid advisory is inferred.
- Successful output must match the advisory request as well as source publication
  and source/prompt revisions. Changed request/identity/revisions abstain with
  `stale_advisory`; they cannot become accepted suggestions.
- Supplied failures must match publication/request and any known source/prompt
  revisions. Foreign or stale failures become a manual fallback tied to the
  current request. Valid null outage revisions stay null; they are not invented.
- Invalid supplied failures become bounded `invalid_output` manual fallbacks.
  Non-text object keys fail validation before sorting; generated invalid-output
  diagnostics do not echo hostile field names or raw supplier exceptions.
- Valid evidence URLs, keywords, source identity/revisions and outage provenance
  remain unchanged, and caller payloads are not mutated. Output stays
  non-authoritative; successful suggestions still require a curator decision and
  manual operation. No actor, canonical fact, provider result or delivery
  authority is inferred from structurally valid output.

The first three points migrate the retained refinement. Date/key validation and
bounded diagnostic text close additional malformed-input cases exposed by the
new focused tests. Field sets and shared schemas are unchanged.

## Grounding and remaining gates

The existing [grounding preview](../scripts/e09_workflow_previews.py) already
hashes supplied retained text, validates supporting excerpts and requires
trial/grant identifiers to occur explicitly in the excerpt. Its existing tests
cover changed fingerprints, missing/fabricated excerpts, hostile fictional text
and deterministic replay. That code was not edited.

HTTPS links and revision equality in this consumer do not prove evidence truth,
source authenticity or excerpt grounding. Consumer and grounding preview remain
separate local contracts; no joined extraction runtime or provider route is
qualified here. Source-content changes without a changed revision cannot be
detected by this revision-only consumer. Actual extraction still requires the
existing owner's exact prompt/schema/data-handling and source-fingerprint binding,
qualified provider behavior and observed invalid-output/outage recovery. The
retained digest route receipt is not evidence of E09-specific qualification.
Trusted actor/curator authority and native advisory persistence remain separate.

## Verification and handoff

Python 3.15.1, explicitly selected from this worktree's `.venv`:

- Added retained binding cases plus malformed-control/key, hostile-diagnostic
  and unchanged-provenance cases first; observed failures against the baseline.
- `python -m pytest -q tests/test_e09_advisory_consumer.py tests/test_e09_workflow_previews.py`:
  34 passed, one optional jsonschema check skipped, 52 subtests passed.
- Project structural/link checks passed. The unchanged broad harness receipt from
  the preceding identity packet is retained; no repeated broad run is claimed.

This completes the missing bounded source consumer refinement. The next actual
extraction exit remains provider/source binding under its existing owner; it is
not supplied by a local validator or the historical digest receipt. No native
read/write, authentication, provider request, content upload, deployment, send,
schedule or canonical-record mutation occurred.
