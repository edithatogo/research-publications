# Review Report: E04/T18 bindings and visual acceptance

## Summary
Current read-only native inspection supersedes historical nine-error observations for Clinical Analytics; semantic and full reader acceptance remain open.

## Verification Checks
- [x] **Plan Compliance** Partial. Internal browser current-account navigation reached the existing dashboard and Clinical Analytics.
- [x] **Style Compliance** Local 8px geometry, PBIR field resolution and palette contrast validation pass.
- [x] **New Tests** No runtime implementation change.
- [x] **Test Coverage** Eight visual/theme tests passed; two outcome-reader tests passed after correcting the runner's tests import path.
- [x] **Test Results** Ten tests passed. Initial outcome-reader import failed under module-qualified invocation; PYTHONPATH=tests rerun passed. No source defect inferred from the harness failure.

## Findings
### High — Compliance interpretation is not established by displayed coverage
- **File** Current native Clinical Analytics page
- **Context** Card shows open access compliance rate67.9%, open access publications36; distribution shows1291 blank statuses among1344 records. These values are visible evidence, not a verified denominator or institutional compliance result. Field-of-research labels also assert ANZSRC divisions while visible categories include Agricultural and Biological Sciences and Arts and Humanities.
- **Suggestion** Reconcile measures, denominator eligibility, missingness, classification provenance and policy applicability against current isolated model definitions before accepting or revising labels. Preserve source uncertainty.

### Medium — Current binding status differs from dated backlog
- **File** conductor/tracks/E04_fluent_visual_polish/plan.md
- **Context** Existing current report has12 visible pages. Clinical Analytics cards, charts, slicers and DoRA table render after loading, without historical nine field-error tiles in this inspection.
- **Suggestion** Applied documentary correction. Retain dated six-page/nine-error evidence as history, not the current observed state.

## Remaining implementation and native gates

This read does not establish current full model definition parity, report/model
write isolation or rollback, light/dark acceptance, keyboard journey, performance
budgets or all T18 page semantics. No shared report/model save was performed.
Current read-only rendering is not a reason to redeploy definitions blindly.
The next implementation packet must bind current model/report preimages and a
qualified isolated target to the observed metric/classification issue.

Review owner is chat01a19f3f-5187-7c23-ac14-192cb93a5a26 in
/Volumes/PortableSSD/GitHub/RIMS/dependency-qualification-20261103. Native scope
is current-account read-only report inspection. Existing write owners and all
earlier local review edits are preserved. Exact tenant/report identifiers stay
outside tracked output. Changes remain unstaged under the supplied review skill's
explicit commit boundary.

## CLI model and measure verification — later 3 November 2026

Azure CLI exact report/pages reads succeeded and confirmed12 pages and current
dataset binding. Fabric getDefinition returned202; its canonical operation
result succeeded and retained all79 model parts privately. The original regional
result URL stalled, so the canonical operation-result route was used for the
same operation. No model/report write occurred.

Native definitions bind Open Access Publications to K02 Known open publications,
and Open Access Rate to K02 OA rate among assessed. That measure divides known
open by assessed publications; coverage is a separate measure. Live DAX returned
1344 publications,36 known open,1291 blank OA statuses and rate0.6792452830188679.
Thus36/53 is an assessed-subset rate, not a whole-register compliance rate.

Applied source fixes to ClinicalAnalytics titles/footer remove unsupported policy
compliance and ANZSRC-division claims. Generic source classification and incomplete
coverage are explicit. Native measure logic is retained; deploying these label
edits still requires current report preimage and qualified isolated save/readback.
The source fix does not establish that native labels changed.

The user's later explicit commit/integration instruction supersedes the earlier
review-only commit boundary for this chat's accumulated source packet.

Integration review caught the frozen-runtime gate for the three label edits.
They are retained as private label-candidate JSON, while active source definitions
are restored to accepted hashes. No runtime gate is weakened or rewritten.
A separately reviewed runtime revision and qualified native deployment remain
required. This supersedes the earlier source-fix-applied wording at that scope.
