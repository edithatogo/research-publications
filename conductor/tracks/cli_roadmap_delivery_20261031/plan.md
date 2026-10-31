# Sequenced CLI delivery plan

**Status: slices 1 and 2 authorised, in progress; slices 3–6 remain deferred.**
Unchecked boxes are not accepted outcomes. The user authorises isolated/offline
work before 1 November, preserving the working publication path and its existing
scheduled verification. The current essential closeout remains accepted. Existing G06,
E02/E03/E05, E04/T18, E09 and recovery tracks retain their detailed requirements;
this plan orders their usable CLI slices rather than duplicating their backlog.

## Selected isolated outputs — 31 October 2026

The selected scope for slices 1 and 2 is the isolated CLI consumer and stored
cloud evidence described in [the adoption packet](../../../docs/RETAINED_CONSUMER_ADOPTION_20261031.md).
Terminal cloud verification is accepted; both artifacts were created once and
full downloaded-byte hashes matched. Exact receipts and hashes are in the
[current handoff](../../../handoff/CURRENT_STATE.md). Source owner reports one focused
consumer test invocation (2 tests) and relationship tests (2 tests), rerun only
after the actual retained DOI defect exposed an unnecessary dependency.

- [x] Selected slice 1: isolated complete PubMed CLI consumer and cloud artifact.
- [x] Selected slice 2: isolated PMID grant-reference evidence and cloud artifact.

The consumer retains 1,277 publications, complete metadata and 11,731 author
evidence rows from accepted raw23. The PMID-only relationship export retains
169 candidate GrantList edges mapped to 67 of the unchanged 1,344 canonical
publications. No confirmed award relationship or canonical admission follows.
The malformed unrelated DOI literal is preserved; the full canonical digest is
retained. Existing retained-reader code/wiring is implemented. The additive grant-reference
model candidate and inverse are [prepared](../../../docs/NATIVE_READER_CONNECTION_PREPARATION_20261031.md),
not deployed or deployment-ready. Native adoption is still unqualified and not
marked complete; working-path promotion still requires the 1 November result.
Remaining detailed boxes below describe broader exits, not failed isolated work.
Slices 3–6 remain deferred.

## Execution contract: one test, one verify

For each selected slice, agree one output, exact inputs/target, rollback and
acceptance assertion before editing. Reuse the current capability and acceptance
receipts if their relevant inputs have not changed. Prepare the complete change,
then run **one focused offline test command** covering changed behaviour and
failure boundaries; do not run successive exploratory suites or mirror tests.
Choose exact nodes/modules from the existing tests named below when the actual
delta is known. A test invocation can contain the affected selectors together.

Then perform **one consolidated native verification episode** on the selected
isolated target: exact saved-definition/reference readback and the resulting
stored output/key/field comparison in one receipt. Default to bounded reads when
runtime is unchanged. A changed runtime gets one approved invocation, followed
by its output readback; no deliberate live failure matrix. Reuse accepted replay
and recovery proof. If the change materially alters idempotency and cannot reuse
that proof, specify an unchanged replay as part of the same verification episode
before starting, rather than adding it after success or concealing a second run.

A real failure is not a pass: record it, reconcile any effect, change the
hypothesis and fix the cause. Rerun only the failed affected selector/verification
portion invalidated by that fix. No blind retries, repeated full validation or
native sends via a retrying test runner. Stop on an unchanged denial. Existing
CI/security/clean-package gates remain once at a coherent shared integration or
release milestone, not extra per-edit or per-document test campaigns. One
integrator batches compatible source slices; only one writer per native object.
The plan itself needs one Conductor structure/link check, no feature tests.

## 0. Entry gate and reuse, not a new discovery phase

- [ ] Before promoting changes into the working publication path, consume the
  existing 1 November 07:50 scheduled-verification result. Isolated/offline work
  for authorised slices 1 and 2 may proceed before then. If verification fails,
  preserve the baseline and resolve that concrete incident before promotion;
  do not run a manual substitute or use roadmap work as an unreviewed repair.
- [ ] Execute only the authorised first bounded slice, then slice 2, and
  freeze its input hashes, key sets, target preimage and inverse in existing
  private receipts. Confirm ownership and no in-flight operation. Reuse source
  tests, installed versions and native reads already accepted for these inputs.
- [ ] For an unqualified operation, inspect its installed CLI help/schema and
  perform one exact-target capability read. A read proves only that read; qualify
  any write in the isolated target's existing approved rollback path. If blocked,
  record client/resource/operation and stop that native portion immediately.

## 1. Retained raw archive to one existing consumer — first delivery

**Why first:** removes an existing adoption gap using preserved data, without
provider acquisition, new identities, or a new service. Select one source and
one consumer with a currently qualified Standard/CLI route, not all 12 at once.

- [ ] Reuse `prepare_source_archive_stage.py`, the per-source consumer-generation
  bindings, `ardc_native_batch_reader.py` where applicable, and the current
  source-archive/typed-consumer contracts. Pin the full retained source version
  and its explicit selection; preserve raw bytes/schema before filtering.
- [ ] Connect that input to the existing selected consumer in isolation. Do not
  replace canonical publication keys or label raw23 archive commit as downstream
  reader adoption. If native authoring is unavailable, stop at the separately
  labelled CLI export; do not claim the adoption exit has passed.
- [ ] Test once using affected nodes from `test_prepare_source_archive_stage.py`
  and the chosen consumer's existing contract tests. Verify once: native input
  version/binding, selected keys/counts/all contracted fields and preserved human
  fields match; unchanged canonical/output membership stays intact. Retain one
  source-to-consumer receipt and rollback pointer, then stop.

**Known blocker:** old PubMed 1,276 source PMIDs versus 1,277 accepted canonical
contributions, DataCite 1,281 versus later 1,283 DOI scopes, and ROR API32 versus
complete releases are different observations. Reconcile explicitly; never union,
trim or repin to force parity. Typed input preparation alone is not adoption.

## 2. Identifier-backed relationship and author evidence

**Depends on:** a qualified retained-data consumer from step 1. Deliver the useful
evidence export first, then a separately selected typed bridge; avoid redesigning
the report or building a person-management system.

- [ ] Reuse `prepare_datacite_output_relationships.py`,
  `prepare_nih_publication_relationships.py`, `source_relationship_evidence.py`,
  `prepare_source_relationship_export.py` and `author_registry.py`. Select one
  named use, such as publication-to-award or DOI-to-related-output, with exact
  DOI/PMID/award/ORCID/provider-ID crosswalks. Keep candidate assertions distinct
  from confirmed relationships; retain conflicts and correction/withdrawal history.
- [ ] Add only the selected bridge/projection through existing qualified writers
  or `prepare_source_relationship_model.py`; preserve cardinality, source dates,
  uncertainty, current measures and canonical keys. No model write if the exact
  authoring operation and isolation inverse remain unqualified.
- [ ] Test once with the affected relationship/author/export selectors. Verify
  once: exact persisted edge keys, provenance and one intended consumer filter
  reconcile; unrelated rows and accepted output counts remain unchanged.

**Known blockers:** name-only matches, ambiguous funder aliases and missing
authoritative role/affiliation identifiers. Hold unresolved identities for human
resolution; no fuzzy auto-merging, institution-wide inference or fictional data.

## 3. Bounded DoRA activity registry qualification

**Independent branch after entry gate:** do not make this block steps 1–2 or mix
activity rows into publication membership. The 442-row raw archive is accepted;
current SPN10 guarded registry runtime is a separate unproven operation.

- [ ] Reuse `build_dora_activity_flow_package.py` and the exact retained manual
  input/schema. Qualify the existing target's supported input-preserving CLI run
  route. Historical APIHub/callback denial and unsubmitted bodies are not proof.
  Do not use an invocation that drops `ActivityRowsJson`, resource ID or row count.
- [ ] If qualified and later authorised, select the smallest representative
  stable-key subset or reuse an accepted subset; do not default to a bulk442
  import. Preserve state, reviewer fields, uniqueness and the agreed inverse.
- [ ] Test once with the affected DoRA activity package/contract nodes; verify
  once with the agreed bounded invocation/readback, including an unchanged replay
  only if the materially changed guard requires new idempotency proof. Defer the
  eight-case race benchmark and unrelated concurrency experiments.

**Stop condition:** an unchanged exact-target permission or input-transport
failure. Keep raw-source acceptance, record the operation gap and move on; never
cycle clients or remove the guard to obtain a green result.

## 4. Selected freshness/acquisition and CLI recovery

**After retained consumers work and only on explicit selection:** update one
source generation or the two deferred records, not every provider or collector.

- [ ] Reuse `collect_pubmed.py`, `collect_dora_history.py`,
  `capture_discovery_source.py`, `capture_ckan_source.py` or
  `capture_official_workbooks.py` as appropriate. Keep full raw capture, stable
  scope, pagination, hashes and schema; use accepted archives when freshness
  adds no required value. Respect shared rate ownership and source terms.
- [ ] Reuse admission/protected-field/replay tools for an explicit identity delta
  through the existing registry/model/output path. Preserve last-good generation,
  review values, immutable output revisions and the working schedules. Broader
  paper acquisition additionally needs item-specific rights and original hashes.
- [ ] Test once: affected collector/admission nodes with injected transport,
  covering partial/changing totals and protected fields. Verify once: selected
  admitted delta, retained records and full/month output keys reconcile. Fold an
  existing isolated restore/hash comparison into this verification if recovery
  changed; no separate disaster-exercise campaign or new backup framework.

**Known blockers:** Crossref broad discovery previously failed full-metadata
two-read stability; a prefix is not complete. Preserve failure receipts and use
the accepted exact-DOI scope until a separately selected complete capture passes.
On rate limits or a changed source schema, preserve the checkpoint and stop;
never promote partial results or refresh solely to make an archive newer.

## 5. Real outcome evidence, then forecasting

- [ ] Require a named decision and authorised real evidence before adding a
  store. Reuse `outcome_evidence.py`, existing outcome measures and
  `dashboard_metrics.py`; preserve denominators, baselines, comparators, follow-up,
  uncertainty, revisions and unavailable/suppressed states. Do not treat source
  coverage or counts as demonstrated institutional impact.
- [ ] Add a CLI aggregate/export to the existing selected consumer first. For
  forecasting, use retained coverage rules and rolling-origin baseline evaluation;
  the current gate requires ten training years and five rolling origins per
  scored horizon. Suppression or retaining the baseline is a valid result.
- [ ] Test once with affected outcome/metrics nodes; verify once against the
  selected aggregate source totals and provenance, or the frozen evaluation
  input and baseline comparison. No new model service, external upload or weights.

**Blocker:** insufficient real evidence/coverage. Defer the slice instead of
building an empty reporting system or manufacturing metrics.

## 6. Conditional surfaces — qualify before commissioning

- [ ] Reader changes: CLI can prepare PBIR/TMDL/M/DAX and bounded API deployment
  where qualified. Existing exact-version import/linguistic-schema and authoring
  limits must be resolved before promotion. Rendering, keyboard/accessibility
  and visual acceptance require a selected UI check; exclude that finish line
  from a strict CLI-only tranche rather than call generated JSON a usable report.
- [ ] Collaboration/privacy/subscriptions: qualify existing identity, storage,
  permission and Standard routes first. Cross-user privacy needs actual permitted
  test identities; no CLI source test substitutes for it. Subscription delivery,
  sharing, recipients and permissions require their own later authorisation.
- [ ] Documents: evaluate the preferred maintained SharePoint template/structured
  generation route with existing supported APIs and actual licensing first.
  Preserve revisions and human edits. If unavailable, record the exact gap before
  choosing the simplest fallback. Generated bytes are not substantive approval or
  authority to circulate; visual/output acceptance may need UI inspection.

## Scheduling, ownership and terminal handover

| Cross-cutting blocker | Planned response |
| --- | --- |
| PortableSSD/raw archive unavailable | Preserve the existing handle/checkpoint; stop native work that depends on it. Use verified preserved source for independent offline work only; do not fabricate missing raw evidence or repair shared Git metadata speculatively. |
| Expired authentication | Use the retained same-client guarded renewal under one owner. Ordinary account selection is routine; password/MFA/new consent remains human. Resume the exact target after terminal renewal, not a new client or broad discovery. |
| Standard-only licensing or denied operation | Keep the source/CLI export usable and identify the exact native dependency. No purchase, generic HTTP substitution or permission widening is implied. |
| Competing owner, drift or uncertain mutation | Stop that object, preserve the preimage/journal, reconcile actual effects before another write; never remove another process's lock. |
| Source instability or incomplete coverage | Keep the last-good generation and retained failure/prefix. Admit no partial generation; fresh capture is a separately selected outcome. |
| No suitable native authoring route or real evidence | Finish only the separately labelled CLI export if selected; leave native adoption/outcomes unaccepted and move to independent ready work. |

- [ ] Implement one selected slice at a time. A shared-object dependency serialises
  native work even when source edits use separate branches. Batch independent
  reviewed source packets into a coherent merge; do not create extra chats,
  recurring jobs, approval queues or acknowledgement loops.
- [ ] At each terminal result record only input/target hashes, changed paths,
  selected test invocation, one verification receipt, rollback and any exact
  blocker in the existing checkpoint/handoff. Mark the relevant existing roadmap
  item complete only for its evidenced scope. No repeat of the current essential
  closeout or the scheduled-occurrence checks.

**Current authorisation:** step 1 for one retained source/consumer,
followed by step 2 for one identifier-backed relationship export. Steps 3–6 are
conditional selections, not automatic commitments, and have no implementation
dates until their inputs and operation-specific capabilities are known.
