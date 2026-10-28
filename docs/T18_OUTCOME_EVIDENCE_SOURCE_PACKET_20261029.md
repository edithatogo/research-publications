# T18 outcome-evidence source packet — 29 October 2026

This is an offline technical packet for TranslationEvent and OutcomeObservation.
It creates no intake store, form, workflow, model table, DAX, review queue or native
record. No browser, authentication, source acquisition or send occurs. No real
outcome, clinical threshold, verdict, comparator equivalence or identity mapping
is invented. Native persistence and operational acceptance remain unproved.

## Normative source and existing-code assessment

The read-only normative reference is parent commit
`b74922eccf2945a36fbc36d1ab095c2bdd454cfa`, specifically the outcome-evidence and
reproducibility sections of
`conductor/tracks/chhhs_outcomes_powerbi_20261021/spec.md` and the
technical intake handoff in
`conductor/tracks/chhhs_outcomes_powerbi_20261021/outcomes.md`.
Current parent copies matched that revision at inspection. Its source hashes are
retained privately; no Conductor file is changed or copied into this packet.
All slices are selected under the current assignment; historical slice-1 limits
do not defer this independently authorised source work.

Existing publication outcome-reader, measure and source/detail/plot reconciliation
modules operate on publication grains. Neither the delivery checkout nor the
preserved authoring scripts contained a TranslationEvent/OutcomeObservation
intake/revision equivalent. Replaying accepted publication parity would not prove
these new behaviors, so those checks and captures were reused unchanged.

## Owned implementation

Only `scripts/outcome_evidence.py`, `tests/test_outcome_evidence.py` and this leaf
document are added. The module uses the standard library, with no runtime,
dependency, shared contract/model/DAX or shared handoff changes.

`intake(history, source_bytes, references, human_edits=...)` returns a new tuple of
frozen Revision values and a receipt. It does not mutate supplied history,
references or source bytes. Revisions contain canonical structured source and
effective JSON, exact raw-source SHA256, protected human fields, the selected
indicator definition subset and reference-snapshot fingerprint. Callers must
retain the exact original bytes in their existing authoritative source; canonical
JSON is not a byte-for-byte replacement for that artifact. Evidence content hashes
and links are checked against the supplied reference catalogue; evidence blobs
are not fetched or independently certified.

The supplied read-only reference subset includes explicit canonical project,
population, setting and method IDs; versioned comparator/baseline IDs; evidence
ID/revision/source ID/source revision/content fingerprint/reference/status; and
indicator ID/version/unit with explicit requirement flags. It does not replace
the full governed IndicatorDefinition dictionary. No requirement or eligibility
threshold is guessed from an indicator name. Exact IDs are validated without
normalising labels or resolving people, projects or relationships.

Both grains require stable identity, revision/superseded revision, context,
contributor, recorded UTC timestamp, explicit verification fields and explicit
aggregate-authorisation metadata. TranslationEvent retains its supplied type,
description, date/precision and multiple project contributions as one event plus
a bridge. OutcomeObservation retains indicator version, explicit event/project
references, period, estimate/unit, numerator/denominator, comparator, baseline,
follow-up amount/unit/anchor, uncertainty/method, contribution and limitations.
The module neither verifies a real event nor advances status on successful intake.

Numeric/value slots distinguish available, confirmed_zero, unavailable,
not_applicable, not_yet_observable and suppressed. Non-values require a reason
and carry None; numeric zero requires explicit confirmed_zero. NaN, infinity,
boolean-as-number and implicit unit conversion are rejected. Dates retain day,
month, year or unknown precision; unknown has no fabricated value. Required
incomplete periods, follow-up or components withhold projection eligibility.
An explicitly empty evidence list remains traceable but unavailable. Invalid or
unregistered references reject intake rather than create a placeholder identity.

An unchanged byte-identical replay adds nothing and never reactivates an older
revision. Changed content cannot reuse a revision ID. New revisions must name the
exact current predecessor, with no stale fork or recorded-time regression.
Indicator semantics and evidence/source metadata cannot change under an unchanged
version. Human-edited fields carry forward while source fields remain unchanged
or converge to the human value. Conflicting upstream changes fail without effect;
explicit caller-supplied human resolution requires a new revision. Original source,
human edits, evidence links and superseded revisions remain in the returned history.

## Projection boundary

`project(...)` selects revisions at an explicit recorded-time UTC cutoff and
retains source/reference snapshot, model revision and report revision metadata.
It returns technically eligible event facts/project bridges, authorised outcome
aggregates at their original observation grain, explicit observation-project
bridges and traceable detail. Multiple projects do not multiply event counts;
project-only observations do not acquire inferred event links or extra projects.

Only supplied verified metadata with complete required evidence is eligible.
Disputed/withdrawn current records or referenced evidence are excluded, as are
outcomes depending on an unavailable linked event. Their IDs, revisions,
supersession and source/evidence fingerprints remain traceable. Missing or changed
historical indicator/evidence references produce unavailability, never fallback
to a newer version. Source verification states are not rewritten by projection.

An aggregate-authorisation flag is an explicit caller input, not proof of tenant
access or permission. Unauthorised outcome values and raw evidence URLs are not
projected; unauthorised event dates are withheld. Actual access remains with the
existing source and its owner. Unknown/incomplete records are counted separately
from the count of technically eligible event records; zero eligible evidence is
not a zero-impact score.

The helper does not pool outcome estimates, average percentages, infer compatible
cohorts or compute a clinical/economic effect. Source numerator/denominator pairs
remain visible; a required zero eligible denominator makes the outcome unavailable.
Future governed rate rollups must recompute from compatible totals in their
authorised semantic layer. Comparator, baseline and method references establish
technical reference validity, not scientific comparability. Follow-up is supplied,
not adjudicated as clinically sufficient or automatically mature.

Historical reconstruction needs the retained exact source and reference snapshots.
The pure function cannot replace an issued result in a store. A newly supplied
reference snapshot yields a separately fingerprinted result; callers must preserve
original/restated outputs and their reasons rather than overwrite issued history.

## Focused evidence and residual gates

Eighteen focused fictional tests passed on the explicitly selected repo-local
Python3.15.1 interpreter. The complete affected selector is
`-m unittest tests.test_outcome_evidence`. No skipped tests,
retries, real clinical rows or native calls are involved.

The retained fictional end-to-end receipt proves one event with two declared
project contributions counts once; one authorised aggregate observation replays
unchanged; a new evidence/source/indicator revision supersedes its predecessor;
the human caveat survives; the original projection retains its earlier value;
a protected-edit failure preserves the prior history; and a withdrawn revision
removes the observation from eligible projection without losing its four-revision
trace. Other tests cover unavailable versus explicit zero/N/A, dates, required
denominator/comparator/baseline/follow-up/method/uncertainty, invalid canonical
references, duplicate JSON keys, source/indicator version drift, missing historical
references, human evidence-link preservation, status non-promotion and suppression.
Malformed, duplicate or reordered revision chains are rejected, not silently
repaired into a different current state.

Private receipts are in `private/ops/t18-outcome-evidence-source-20261029/`:
`normative-sources.json`, `focused-tests.json` and
`fictional-end-to-end.json`. These prove pure source behavior only. They do not
prove save/readback, authorisation, privacy/security behavior, native measures,
report binding/rendering, export parity, scheduled delivery or real impact.

Remaining dependencies are the exact existing authoritative project/activity/
evidence home and custodian; stable live IDs, access and edit/history behavior;
the full approved indicator definitions and evidence/comparator/baseline/method
revisions; lawful authorised aggregates and comparability/follow-up policies; then
explicitly scoped native persistence/readback, replay, human-edit/supersession and
withdrawal acceptance. No new store decision is implied. T18 current-target
identification remains unresolved; no replacement reader is selected. E04's
native import/recovery hold and all other lanes' ownership remain intact.
