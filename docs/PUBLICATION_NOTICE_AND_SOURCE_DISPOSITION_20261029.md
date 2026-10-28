# Publication source disposition and notice evidence — 29 October 2026

This packet starts at `fbc75ca3891c059a4367229fecb41be7df65c1ae` in app-managed
worktree `/Users/doughnut/.codex/worktrees/fa70/chhhs-research-publications`, branch
`codex/rims-publications-roadmap`. Delivery chat
`01a1831e-449a-7693-af1a-08bb23391c76` owns the publication source/tests and this
leaf handoff. Integrator chat `01a182f2-fd8e-7953-9bd2-f9b8002664a6` retains shared
records and native-object assignments. Shared build helpers, model/report source,
authentication, native services, schedules and registry decisions were untouched.

## Finite retained-source disposition

[The per-file inventory](../audit/publication-source-disposition-20261029.json)
accounts for 94 original scripts and 74 test modules. Its scope is top-level
filenames containing `publication`, `pubmed` or `metadata`, the explicitly
assigned capture-source pair and the paired export-failure test. It records
retained/lane hashes, explicit disposition reasons and Python function comparison
where both files exist. Private/generated source, fixtures, shared build helpers
and model definitions are outside this inventory. No generic unresolved leaf
bucket remains. These are file counts, not feature or acceptance counts.

| Disposition group | Files |
|---|---:|
| Exact bytes already covered, or selected bounded lane/export/offline slice delivered | 31 |
| Canonical contract preserved instead of retained replacement | 5 |
| Historical evidence validators retained without creating current prerequisites | 6 |
| Model/report or grants/protocol scope reserved to its owner | 47 |
| Explicit later publication source packets | 79 |
| Total original source/test files | 168 |

The later packets comprise 40 native-contract files, 14 legacy-preservation files,
nine provider-dependency files, eight identity diagnostics, six document-library
files, one delivery file and one multiline export-fidelity test. Each has a named
per-file reason. Retention does not authorize execution, revive an obsolete
human-admission gate, delete original source or declare the native work complete.
The inventory also protects 15 additional lane/canonical-only files absent from
this original source cohort.

Semantic review preserves the canonical platform validator: the retained version
removes canonical manifest validation and depends on missing-only/title native
writer extensions that are not qualified in this lane. The source reconciler
keeps its lightweight policy-contract import. Broader collector and native
adapter differences stay with their explicit dependency packets. No unrelated
history merge or wholesale source replacement occurred.

## Correction and retraction contract

The existing `config/publication-policy.json` requires retention with labels.
The [NLM linked-citation policy](https://www.nlm.nih.gov/bsd/policy/errata.html)
distinguishes the subject article from a notice and describes the direction of
erratum, retraction and republication links. The implementation pins reference
names to [NLM's 2025 output-element documentation](https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/250101/el-CommentsCorrections.html).
Its optional related PMID is preserved as optional; citation text is not converted
into an invented identity.

`publication_notice_evidence.py` now supports ordinary nested JSON and the
retained XML `Name`/`Value`/`Attributes` representation. It reads exact declared
publication types, notice fields, booleans and reference types. Titles, abstracts,
notes and reference prose cannot create notice labels. Negated/substring wording
such as `uncorrected` does not become a correction. Ordinary comments and
expressions of concern are not classified as retractions.

| Reference pair | Preserved record roles |
|---|---|
| `RetractionIn` / `RetractionOf` | Subject article / notice record |
| `ErratumIn` / `ErratumFor` | Subject article / notice record |
| `CorrectedandRepublishedIn` / `CorrectedandRepublishedFrom` | Original / corrected version |
| `RetractedandRepublishedIn` / `RetractedandRepublishedFrom` | Retracted original / republished version |

The republished version receives a correction/republication label; its relationship
to a retracted original does not label the new version itself as retracted.
Paired tests cover both source representations and both directions. Positive,
canonical ASCII PMIDs are required for an identity locator. Missing or malformed
related PMIDs retain their raw values and citation evidence without a fabricated
link. Duplicate source identities, foreign namespaces, unknown reference types
and malformed metadata remain visibly unqualified.

`publication_policy.evaluate` adds `NoticeEvidence` to new derived observations.
It retains the original `Record` exactly, preserves automatic Included/eligible
policy and keeps all prior versions. Known foreign metadata cannot label the
requested source identity. Evidence issues receive an uncertainty label rather
than an invented correction or an exclusion. Existing retained versions are not
rewritten to add derived fields.

Identifier matching is the extent of `source_identity_bound`. Every result and
link remains candidate evidence, with authoritative-linkage verification,
consumer acceptance and correction authority false. No title, author, review,
status, identity or registry correction is applied. Routine inclusion gains no
new per-record human approval requirement. DoRA declarations retain generic
labels; cross-source DoRA/PubMed notice linkage remains unqualified.

## Export guard closure

The small retained export delta was imported with paired tests, preserving all
canonical key/count/generation, output fidelity and no-replace guards. Declared
producer/page failure now rejects even when the keys match. Empty error objects
and malformed partial/truncation flags fail closed; explicit clear markers
(`error=null`, empty error list and false flags) remain accepted. Failure messages
expose signal names, not private provider diagnostics, and prior output survives.
The retained positive test's empty error object was replaced by an explicit null
marker; a paired negative test now proves the empty object is rejected.

## Reused evidence and remaining requirements

The accepted [offline comparison](PUBMED_OFFLINE_TYPED_CANDIDATE_20261029.md)
remains unchanged: 1,272 matching overlapping metadata payloads, five preserved
literal metadata deltas and two new identities. The small comparison receipt was
hash-checked and reused. The large reconstruction was not run again, and no
source version or unresolved value was replaced. The ignored lane evidence is
`private/ops/publications-notice-disposition/frozen-comparison-reuse.json`.

Before any correction or consumer status change, the assigned owner still needs
exact source/snapshot binding, authoritative related-record linkage, fresh
protected-value preimages and qualified consumer behavior. Current native schema,
61-part model baseline, rollback and full output readback remain separate.
Per-flow failure alerts and account weekly failure-digest suppression remain
unqualified for a no-send test. No native/authentication activity or sends occurred.

The finite inventory identifies subsequent source closures; it does not authorize
restarting old provider operations, restoring legacy rows, running delivery or
copying bindings/journals. Historical full-generation closeout remains accepted
at its original scope. Model/report work and shared native contract promotion
return to the integrator.

## Verification

The existing repo-local Python remains 3.15.1 with unchanged locked dependencies.
Focused notice, policy, retention/DoRA and export checks: 42 tests and 78 subtests
pass. The finite inventory passes coverage, uniqueness, byte-hash and link checks.
Full harness: 1,111 tests with 25 existing capability skips, 446 project checks,
web-first contracts, Conductor structure and tooling preflight pass. Notice and
export tests include paired directions, false-positive prose, invalid identities,
history preservation, malformed failure signals and prior-output preservation.
No capability skip, retry plugin, dependency, runtime, hook or workflow changed.
Local tests and source inventories confer no native or operational acceptance.
