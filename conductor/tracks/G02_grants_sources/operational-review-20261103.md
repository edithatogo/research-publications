# Review Report: remaining grants/source operational limitations

## Summary
A malformed-evidence diagnostic failure is fixed; source qualification and operational acceptance retain their explicit dependencies.

## Verification Checks
- [x] **Plan Compliance** Partial. Existing saved-evidence health evaluator reused.
- [x] **Style Compliance** Pass. Standard-library validation with no new abstractions.
- [x] **New Tests** Yes. Invalid source, run identity and generation-container inputs.
- [x] **Test Coverage** Existing health-state/archive-integrity suite plus malformed-input regression.
- [x] **Test Results** Six focused tests pass; full integration outcome recorded in plan.

## Findings
### Medium — Malformed archive inputs raised an incidental exception
- **File** scripts/grants_source_health.py
- **Context** verify_archive('nhmrc', None, [], None) raised TypeError from the regular expression rather than returning unverified. Unknown/unhashable source and malformed generation containers also lacked an explicit boundary.
- **Suggestion** Applied. Validate source, run identifier and list container before regex/source lookup/iteration. Seven malformed-input cases return False. Existing valid archive/tamper coverage remains intact.

## Remaining work by scope

| Scope | Remaining prerequisite |
| --- | --- |
| G02 source catalogue | Per-source authorised access, reuse, pagination, identity and lifecycle evidence; only admitted opportunity sources count toward coverage. |
| G05 universities | Permitted institutional feeds/exports or authenticated portals. Preserve unknown internal lead times and manual-review scope. |
| G03 storage | Historical removal/recoverability and unaccepted writer race/failure requirements at their original scope. |
| G04 intake | Original retained import terminal/manifests and final complete comparison; source hardening does not replace those originals. |
| G07/G08 operations | Genuine eligible preferences/events and permitted identities for lifecycle/access/delivery acceptance. |
| E08 retained limitations | Actual affected natural source occurrences and conditional future operating evidence; historical administrative archive remains preserved. |

This source fix does not establish fresh tenant state, native permissions, source
rights, delivery or whole-track acceptance. NIH remains deferred. No source
collection, native write, schedule, subscription, message or authentication change
occurred.

Owner is chat01a19f3f-5187-7c23-ac14-192cb93a5a26 in
/Volumes/PortableSSD/GitHub/RIMS/dependency-qualification-20261103.
Owned code is grants_source_health.py and its existing tests, plus this review
and G02 plan entry. Earlier edits and native owners are preserved. Changes
remain local and unstaged under the supplied review skill's commit boundary.
