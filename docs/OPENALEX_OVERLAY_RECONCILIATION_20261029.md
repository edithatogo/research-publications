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

The retained field projector and its focused tests are also reconciled from the
same source branch and match the observed authoring copies before repair. The
projector preserves complete raw-linked provenance, nulls and full values while
suppressing oversized flat candidates under supplied physical limits. Review found
that it validated the byte hash but did not bind the envelope's requested DOI to
the DOI in those bytes. The candidate requires matching normalized DOI and a
well-formed matching OpenAlex work ID. A fictional end-to-end test constructs an
envelope through the retained preparer, reconstructs its chunks and projects its
fields. Seven projector tests pass; these are local source checks and do not
qualify native schema, capture or model parity.

The branch's archive-page preparer and bounded bootstrap-increment helper are
included with their retained tests. They prepare supplied candidate definitions
and pages only: prior chunks are retained, failed/partial source outcomes cannot
advance the candidate, and archive commit/readback gates remain explicit. The
archive CLI now verifies actual Git ignore coverage for the private root, inputs,
optional native preimage/receipt and output before reading or creating files.
A fictional temporary-repository test exercises denial and the allowed ignored
path; no native operation is performed. Forty-seven focused OpenAlex tests pass
across the currently selected source packet. Existing 46-part fixture checks are
not proof of the current native model, and the wider branch still requires review.

The retained committed-archive reader candidate is included with its focused
fictional tests. It checks full page bytes, key sets and the supplied model
preimage before preparing three changed model parts; it neither writes nor
refreshes a model. The original hard-coded model fingerprint is replaced by a
required independently supplied private pin, and the CLI verifies Git ignore
coverage for the pin, all inputs/pages and output, then checks for input drift
before creating files. Three tests pass, including non-ignored path rejection,
wrong-pin rejection and a fictional successful candidate. The 46-part baseline
is an old source contract and is not current-model or native acceptance proof.

Source package `0.4.0-integration.4` at `b30532b7` passed fresh extraction and
its full harness using the documented disposable Git and locked Python3.15.1
fixture. SHA256 `9b0d5bc4839ed358ccfba43dad6934e54242c16e3b6720fe5856cb1abc2691a5`.
This receipt predates the reader-candidate addition and is not a package test of
that later change; requalify the next coherent source milestone.
