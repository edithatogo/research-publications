# Retained OpenAlex source disposition

The 36-file branch packet at `c38a266d` has been reconciled against canonical
`c4acd992`. Seven files are identical. The remaining 29 have an explicit
[path-by-path disposition](../audit/openalex-source-disposition-20261029.json).

Existing author evidence now preserves its source-specific URL and observation
time, confines DoRA affiliation/identifiers to the named author, updates
confidence consistently and counts publication roles once per publication while
retaining affiliation rows. Malformed source identities and indexes fail closed.
Existing author-key bytes remain unchanged. The historical scheme/scoped key
replacement requires an identity migration; same-name and cross-scheme collision
limitations remain unresolved and these outputs still require human review.

The other existing OpenAlex modules retain canonical exact-identity, private-path,
independent baseline and source-drift guards. Historical native acquisition,
bootstrap, pending-envelope and flow builders are preserved roadmap source, not
needed by the accepted captured-generation manual cloud-file path. Their old
hard-coded baseline fingerprints are not current native authority. Their tests
and dated native handoff remain historical evidence, not new acceptance.

The full source history is preserved in the verified standalone bundle recorded
in the manifest. It can be restored with ordinary Git fetch into a new branch;
no private binding, original checkout, provider request or native operation is
changed. After this packet passes PR and main checks, the redundant remote branch
can be retired. This disposition does not close optional provider expansion or
assert a new deployment.
