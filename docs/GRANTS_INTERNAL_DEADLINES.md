# Policy-backed internal deadlines

Current status: validated CLI preparation and existing native storage qualified;
live policy application is blocked by the absence of an identified applicable
approved CHHHS lead-time rule. No internal dates have been applied. This is not
an accepted end-to-end native policy-to-report deployment.

## Public policy search — 2 November 2026

The public [CHHHS grants page](https://www.cairns-hinterland.health.qld.gov.au/research/start-a-research-project/research-grants-and-support)
lists funding sources and support. It does not state a general numerical lead
time for internal grant submission. The public
[governance page](https://www.cairns-hinterland.health.qld.gov.au/research/start-a-research-project/apply-for-governance-authorisation)
and linked [SSA requirements](https://www.cairns-hinterland.health.qld.gov.au/_media/research/apply-for-governance-authorisation/ssa-submission-requirements.pdf)
describe budget verification, signatures and endorsement. These are governance
submission steps, not a quantified offset from a grant closing date.

The [Queensland Health funding pages](https://www.health.qld.gov.au/research-reports/research/researchers/grants-support)
and accessible [capacity-building FAQs](https://www.health.qld.gov.au/__data/assets/pdf_file/0032/1465538/queensland-health-clinical-research-capacity-building-faqs-26.pdf)
did not establish a general CHHHS internal lead time. One linked funding guideline
could not be retrieved by the research tool; raw CLI downloads also returned
HTTP 403. The accessible pages were inspected using the research tool. This
bounded search does not prove that no internal or scheme-specific policy exists.
University or other HHS timing rules cannot be silently adopted as CHHHS policy.
No external contact, policy approval or new grant admission was performed.

## Implemented preparation

`scripts/grants_internal_deadlines.py` reuses the existing institutional date
calculator and append-only override reconciler. It consumes complete retained
policy, override, registry and source-calendar captures. The restored policy and
override schemas preserve their existing contracts; a separate authority-binding
schema describes the evidence needed to use an already-approved rule.

- A policy version has a typed immutable key. Organisation, final-deadline
  anchor, GrantConnect applicability, version and effective interval are explicit.
  Overlapping applicable policies fail rather than guessing precedence.
- The authority binding retains document/version, source URL, original document
  hash, exact extracted-rule hash and approval evidence. Original bytes must
  match. A valid JSON object, `Approved` label or fictional test record does not
  itself create institutional authority; the actual source must support the rule.
- Business-day calculations require the existing verified holiday-coverage
  contract plus matching original holiday evidence. Partial dates, cancellation,
  expired policies and uncovered date intervals produce held dispositions.
- Internal identities remain separate from the official `GC-CLOSE` anchor.
  No source date is rewritten. Policy/source provenance remains in the proposal;
  transport ETag changes alone do not alter its material revision.
- Reviewed current overrides can supply an effective date. Stale or unreviewed
  override histories remain intact and flagged; an unresolved override withholds
  the effective date instead of silently substituting the calculated date.

The CLI writes a new ignored private planning artifact only:

```sh
<qualified-python-3.15.1> -m scripts.grants_internal_deadlines \
  --snapshot private/ops/<occurrence>/Snapshot-raw.json \
  --organisation CHHHS --as-of YYYY-MM-DD \
  --evidence-map private/ops/<occurrence>/evidence-map.json \
  --output private/ops/<occurrence>/internal-plan.json
```

The evidence map binds each SHA-256 to its retained original file. PolicyJson
uses `rims-approved-policy-v1`; unbound historical/test policies remain inactive.
Every result retains `native_submission_allowed=false`. This command is not a
native publisher or an unattended recalculation service.

## Verification and exact remaining work

The single focused invocation ran 33 cases: 32 passed and one existing optional
jsonschema-capability case was skipped. Two affected review checks then passed.
The selected interpreter reports Python 3.15.1.

One bounded native read through the existing SharePoint connection confirmed:
one policy row, one override row, zero authority-bound approved policies, 85
source calendar rows and 121 retained registry rows. The policy-version and
override keys are required and unique, and their JSON columns are present.
The retained snapshot produced **85 `approved_policy_missing` dispositions and
zero internal dates**. Source, policy and override data remained unchanged.
Large saved outputs exceeded the FlowAgent response cap; those same outputs
were retrieved through the retained Azure CLI workload route, without rerunning
the flow. The temporary read-only qualification flow was removed after its
definition and outputs were archived privately.

The remaining work is explicit:

1. Identify an applicable authoritative CHHHS rule or receive an explicitly
   authorised local rule, including scope, effective dates and any holiday basis.
2. Bind the real source and preserve its original evidence in the existing
   versioned storage. Do not promote the fictional test record.
3. Complete the native append-only policy/override writer and source-version-bound
   internal-date application, then connect its actual output to the intended
   reader. These components are not claimed implemented by the local planner.
4. Reconcile one real policy-to-output result within the same bounded scope.

Conductor G08-H01 remains open. Private identities, native snapshots and receipts
are under `private/ops/grants-policy-deadlines-20261102/` in the feature checkout.
Existing schedules, publication data, live notification/calendar writers and NIH
deferral are preserved. No source refresh, email or approval-state change occurred.

## Apply a retained generation and prepare a reviewed override

Use `python -m scripts.grants_deadline_application` with the qualified
repository interpreter. Supply `--snapshot`, `--evidence`, `--organisation`,
`--as-of` and a new private `--output`. A dated snapshot is the unit of
application. Rebuild it from the four complete native arrays after a source,
policy or override change. The report displays the snapshot date beside its
effective date, source date, policy identity, review disposition and revision.

For an override add `--context` and `--override`. Supply a reviewed history
record and the existing qualified SharePoint binding. The CLI checks the
complete revision chain and resolves the applicable authority-bound policy.
Use FlowAgent to preflight and save the resulting manual definition. It reads
the live policy and anchor versions before append, creates only a missing
immutable key, and compares the saved JSON at the end. A new decision requires
a new revision. Preserve the private receipts for each operation.

For date application add `--model` and `--report` with complete current
definitions. Apply the returned model and report through the existing Fabric
CLI updateDefinition route and process only GrantInternalDeadlines. This
materializes dated results in the reader and preserves the official calendar.
Missing policy authority produces a held row with blank internal dates.
The existing schedules continue independently of this explicit CLI operation.

To apply dates to the funding calendar, use the same CLI inputs with
`--apply-calendar --context <private-binding>`. Use FlowAgent to update the
existing manual application flow with that occurrence's prepared definition.
Its four list version checks cover added, removed and modified rows. Only
separate INTERNAL keys are eligible for updates. Apply the occurrence once,
retain its result and recapture the calendar before preparing the reader.
Publication of an effective date requires the stored calendar revision and
effective date to agree with the policy calculation and reviewed override.
