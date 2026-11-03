# Review Report: E09 actor binding, privacy, persistence and adoption

## Summary
Local no-send actor/revision/storage safeguards pass; native trusted-actor, cross-user privacy and adoption acceptance remain incomplete.

## Verification Checks
- [x] **Plan Compliance** Partial. Existing no-send implementation and retained source/native handoffs inspected.
- [x] **Style Compliance** Pass for inspected preview and storage boundaries.
- [x] **New Tests** No source changes warranted by inspected results.
- [x] **Test Coverage** E09-focused unittest discovery covers contracts, previews, identity compatibility, storage/revisions, advisory and edition handling.
- [x] **Test Results** Passed.134 tests with4 existing skips on repo-local Python3.15.1. Skipped capability cases are not verified.

## Findings
### High — Trusted actor and privacy adoption remain unqualified
- **File** scripts/e09_workflow_previews.py
- **Context** The module explicitly consumes trusted actor/access/revision arguments from a native adapter; local matching checks cannot authenticate their provenance. Owner-only raw forms and successful preview fingerprints do not prove cross-user isolation or authorised curator updates.
- **Suggestion** Qualify the existing native adapter with actual permitted identities, exact access/actor binding and conditional update/history readback before accepting multi-user adoption. Preserve owner-only/no-send scope until then.

### Medium — Native persistence scope remains narrower than source compatibility
- **File** conductor/tracks/collaborative_research_feed_20261022/plan.md
- **Context** Retained native persistence is PUB-only. Later PMID/DoRA identity compatibility and timestamp holds are source-level evidence. Same-ID solution membership and native documentation publication remain separate gates.
- **Suggestion** Consume exact target preimages, current ownership, supported operation permission and recovery before native persistence/adoption. Preserve ambiguous timestamps and source identity; no canonical promotion follows from syntax or alias matching.

## Review outcome and handoff

No implementation defect was established by the inspected source and focused
tests. A native authority/access gap cannot be repaired by accepting caller form
identity as authenticated or treating local previews as writes. This review
updates the status boundary without claiming current tenant inventory or a new
permission denial.

No Teams/channel/email action, grant of access, source review, native persistence,
solution membership, authentication or schedule change occurred. Existing native
owners and prior no-send acceptance remain preserved. Bounded reviewer is
chat01a19f3f-5187-7c23-ac14-192cb93a5a26 in
/Volumes/PortableSSD/GitHub/RIMS/dependency-qualification-20261103.
Earlier local review edits remain intact. Changes remain unstaged under the
supplied review skill's explicit commit boundary.
