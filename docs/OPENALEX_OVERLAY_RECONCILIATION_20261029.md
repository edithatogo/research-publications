# OpenAlex overlay source reconciliation — 29 October 2026

The standalone overlay and its original focused tests are retained from
`origin/codex/openalex-retained-consumer` at `c38a266dd62849ab2455324dd8a21cde6dc5df54`.
The source was reviewed against canonical `enrich_openalex.py` and exercised with
fictional inputs on the repository-local Python 3.15.1. It prepares a reference
projection only; it performs no provider call, native write, model refresh or
acceptance. It does not integrate the remaining OpenAlex branch or claim the
unverified native M function matches this Python overlay.

Review found that the old tests did not cover two existing publication keys
sharing a DOI. The old overlay applied one provider value to both keys despite
its one-to-one contract. The candidate now refuses a duplicate canonical DOI
when the supplied enrichment matches it; duplicate DOIs outside that enrichment
remain unchanged. A second boundary rejects malformed provider work URLs rather
than accepting any text beginning with the work-ID prefix. Nine focused tests
pass, including the two identity boundaries and six retained tests.

The remaining OpenAlex branch has additional source, model and documentation
changes and later versions in the original authoring checkout. Its complete
source, dependencies, provenance and native gates remain to be reconciled.
This packet must be integrated serially after PR74's verified main result.

The same retained branch also contains `prepare_openalex_retention.py` and its
paired tests, byte-identical to the observed authoring copy before this change.
The source preparer preserves full provider response bytes and recursive schema
before projection and retains failed attempts without replacement. During review,
its CLI's directory-name check was found insufficient to prove that inputs and
outputs were actually ignored by Git. The candidate now requires the real
repository ignore policy to cover the private root and each exact input/output
path; absent Git or a missing ignore rule fails before reading or writing data.
Eight focused retention tests pass, including a temporary-repository test of
ignored and non-ignored paths. This does not qualify native storage or enable a
provider request.
