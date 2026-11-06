# RIMS CERIF application profile — draft contract

Status: design only, 6 November 2026. No CERIF compliance claim is established. Scope is the five-area application profile, not all possible CERIF entities. Pin an exact CERIF model/schema, entity/relationship vocabulary snapshot and optional exchange profile before implementation. Do not confuse CERIF model versions, vocabulary commits and OpenAIRE profile versions.

## Initial crosswalk

| RIMS area/entity | CERIF target to verify against selected version | Local boundary |
| --- | --- | --- |
| Research Outputs: publication | cfResPubl / Publication | Preserve canonical keys plus DOI/PMID/DoRA aliases; future datasets/software require explicit Product typing |
| People & Collaborations: resolved person | cfPers / Person | Author labels remain unresolved mentions; no person minted from name equality |
| Projects & Studies: project/study | cfProj / Project | Registry record, project, local site and ethics approval remain separate identities or typed relations |
| Funding: award/funding | cfFund / Funding | Opportunity, application and award are distinct lifecycle records; do not map every opportunity as an awarded grant |
| Organisations & Affiliations: organisation/unit | cfOrgUnit / OrganisationUnit | Preserve local units, ROR mappings and date-bounded person/unit roles |

## Required mapping record

Each included source field and relationship must record local schema/version, source path, target entity/property or relation, target URI/code and vocabulary version, transformation, identifier namespace, cardinality, role, validity dates/precision, provenance and loss/extension/unmapped disposition. Use official relationship schemes for person-output, person-project, person-organisation, project-output and project-funding as applicable. Candidate links remain candidate; unknown is distinct from negative. Do not fabricate dates to satisfy an exchange format.

## Acceptance and recovery

- [ ] Select and retain authoritative specification/schema/vocabulary bytes and rights; PPG publication/edition/capture readback complete.
- [ ] Agree the bounded application profile and explicitly excluded entities; map every included field and relation, preserving local extensions.
- [ ] Implement a machine-readable mapping and export schema; retain source keys, versions, assertions and inverse mapping. No runtime adoption in this documentation increment.
- [ ] Validate representative real authorised exports against the pinned schema and semantic/cardinality rules; reconcile complete selected key sets, identifier uniqueness, relationship endpoints and date/role semantics.
- [ ] Check ambiguous identities, unknown dates, conflicting sources, many-to-many links, withdrawn/corrected observations and access-scoped exports. Ensure links do not multiply publication or award totals.
- [ ] Demonstrate round-trip preservation or explicitly quantified information loss; verify changes/rollback without rewriting source history.
- [ ] If OpenAIRE exchange is selected, qualify that profile and protocol separately. Generic CERIF alignment is not OpenAIRE interoperability.
- [ ] Publish a scoped conformance statement naming version/profile, tested entities, exceptions and evidence. Keep planned, implemented, schema-valid, semantically validated and exchange-tested states distinct.

Clinical governance applicability and accreditation decisions remain outside this technical contract. No blanket compliance label may result from the crosswalk alone.

## Captured entity vocabulary

The supplied HTML endpoint timed out on 6 November. The authoritative euroCRIS source repository supplied CERIFEntities.xml at commit ff4bdf3d710ef4d9065d20aeeebdd625475f3d80. Its header declares release 1.5 and date 2012-10-02; that is the vocabulary artifact's declaration, not a claim it is the latest full CERIF model. Private original bytes and capture manifest are retained under /Volumes/PortableSSD/PPG-private/rims-cerif-20261106/. Rights remain unverified; no external bytes are committed here. Pinning the remaining model/schema/relationship sources and PPG native registration remains open.
