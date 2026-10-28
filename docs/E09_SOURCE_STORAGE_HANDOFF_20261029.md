# E09 no-send storage source closure — 29 October 2026

This packet consolidates the smallest complete retained storage dependency
family: logical threads, immutable editions and generic qualification envelopes.
It performs no business inclusion decision, storage write, authentication,
provider/AI call, post, mail, schedule operation or actual delivery.

Chat `01a1831e-cc6d-7371-9d57-021a339b708a` is assigned only these E09 source/test
paths and this leaf handoff, under sole integrator
`01a182f2-fd8e-7953-9bd2-f9b8002664a6`. Actual app-managed checkout remains
`/Users/doughnut/.codex/worktrees/ef45/chhhs-research-publications`, branch
`codex/rims-grants-roadmap`. Packet base:
`fed7ac781c03ef06b3af78a8463ccd3bb7fe9ac8`. Canonical source comparison checkpoint:
`56ac7d923e94b3e6d92d371c6836cd57d11284e4`; the four existing E09 dependency
modules matched this checkout at entry. Native scope is empty.

## Complete source family

| Module | Behavior and dependency |
| --- | --- |
| `e09_thread_mapping.py` | Deterministic no-send render/receipt mapping; binds stable thread/publication/canonical/receipt identities, aliases, revision, input fingerprint and source-reference text. Updates preserve human notes and historical aliases. Unknown outcomes block every changed retry. Depends only on existing contracts/renderer. |
| `e09_edition_storage.py` | Immutable no-send snapshots retain exact preference, discovered inputs, delivered-key input, explicit date span, empty windows, suppression counts and output fingerprint. A saved snapshot is never a delivered receipt. Uses existing edition/contract functions and an aware-time Brisbane projection. |
| `e09_storage.py` | Lossless qualification envelopes for contribution, subscription, receipt, thread and edition records. Typed logical keys are distinct across kinds; content is exact canonical JSON with hash, revision and byte-cap rejection rather than truncation. Replay is unchanged; incompatible identity/revision/provenance fails. Edition replacement is forbidden. No native ETag, access or writer is supplied. |
| Existing renderer/edition builder | Retained validation increments enforce already declared source-key, PUB canonical-key, tier/status, trigger and date rules. They reject contradictory input rather than selecting a new business tier or admitting another identity format. Existing valid content, stable thread IDs, edition grouping, enrolment, opt-out and duplicate recovery remain covered. |

Dependency graph is closed within existing code and the Python standard library:
storage -> thread mapping -> renderer -> first-discovery/contracts; storage ->
edition storage -> subscription editions -> first-discovery/contracts. No new
package, framework, shared contract, model, flow definition or native connection
is introduced. Core feed contracts and both E09 schema files are unchanged.

The source-reference field remains supplied evidence text. Syntax validation
and a local fingerprint do not establish its provenance, authenticated actor,
source completeness, native access or permission to update anything. Aliases
remain caller-supplied transport assertions; this code does not discover a
winner, merge source records, change review labels or open a real thread.

## Semantic review and adversarial repairs

The retained three modules and15 paired cases were migrated together. Test
imports were made package-qualified for both focused unittest and discovery.
Seven additional adversarial cases cover these repaired boundaries:

- Explicit empty/malformed alias lists cannot silently become inferred defaults;
  malformed alias objects fail with ValueError before set/sort operations.
- Receipt ID must bind the stable thread ID. Source-reference text must be exact
  and unpadded. Human notes, publication identity and historical aliases remain
  immutable across thread revisions.
- A standalone failed_uncertain receipt cannot be relabelled recorded_only by a
  new storage revision; independent reconciliation remains required. An exact
  replay stays unchanged. Thread uncertainty has the same no-retry boundary.
- Padded/malformed already-delivered source identities cannot evade duplicate
  suppression and re-enter an edition. Delivery authority is refused for storage
  qualification; snapshots remain no_send, authoritative=false, delivered=false.
- Contradictory review status/tier, malformed labels/triggers, impossible dates,
  invalid publication months and unqualified canonical identities fail closed.
  Padded publication source keys are rejected rather than trimmed into a stable
  thread identity. Those pre-repair acceptance gaps were reproduced locally.
- Uncertainty requires a boolean. Exact Unicode/human text survives envelope
  round trips, while payload alteration, hash/identity drift, stale revisions,
  forged outputs and attempted edition replacement are rejected.

Renderer documentation now states its real limit: extra fields are excluded,
but sensitive text within an allowed title still requires source qualification.
It does not claim that a field allowlist can identify sensitive content. No real
publication records, private source snapshots, contributions or human notes were
copied; every added test fixture is fictional.

## Finite residual source dependencies and decisions

1. **Native input projection:** retained `e09_native_inputs.py` and its tests
   expect the retained widened canonical-key rule in `e09_first_discovery.py`:
   PUB hex plus PMID and official DoRA record URI identities. Canonical currently
   accepts PUB hex only. Silently widening that rule would change identity meaning
   and requires the parent's authoritative mapping/compatibility decision. The
   retained native-column mapping, first/latest-processing timestamp semantics,
   full accounting and alias-hold rules also need an exact frozen source binding.
   This packet neither imports that adapter nor changes the canonical identity
   parser. Existing source key formats remain unchanged.
2. **Workflow previews:** `e09_workflow_previews.py` plus its tests are an
   independent finite helper family. Trusted actor/curator access, source/project
   revisions and fresh ETag inputs remain external prerequisites; previews are
   not authenticated submission, curator authority or canonical update paths.
   It is not required for the storage envelope closure and is not imported here.
3. **No-send graph builder:** `build_e09_no_send_flow.py` and its paired tests
   remain a separate source-generation review. Parent retains actual shared flow,
   storage target/schema/bindings and all decisions. Any later generated graph
   needs its exact target/no-send/retry/identity/uncertainty checks and native
   preimage/readback/recovery qualification before adoption. No flow is generated,
   saved, started or invoked by this packet.
4. **Advisory consumer refinement:** the retained differing advisory consumer
   source/tests remain separate from this dependency family. Any extra fields or
   source binding must preserve existing schema and manual fallback. No AI prompt,
   provider, data handling route or upload is qualified by local preparation.

Native adoption is still separate: owner-only versus cross-user storage access,
trusted actor/curator identity, exact source projection, version/ETag conflict
handling, real message/provider reconciliation, solution membership, native
publisher readback and any future dispatch all retain their existing authority
and evidence gates. Prepared or saved no-send records are never delivery proof.

## Verification and preservation

All100 current E09 tests pass with four existing optional-jsonschema skips.
This includes22 added storage/thread/edition/adversarial cases, with no new skip,
retry or xfail. Focused and discovery imports both pass. Existing immutable
edition, enrolment, opt-out, source-key and history tests are retained. Log:
`/Volumes/PortableSSD/tmp/rims-e09-ef45-storage-tests.log`.

Project validation passes446 checks, web-first returns PASS_LOCAL_ONLY and
Conductor reports zero structural errors. Python3.15.1 and existing locks/runtime
are unchanged. Diff whitespace and relative handoff links pass. Shared contracts,
first-discovery identity rule, grants preference/ledger keys, private bindings,
original native jobs and all one-send/history records remain untouched.

Next operation is the parent's serial source review/integration. The earlier
[finite source disposition](G08_SOURCE_RECONCILIATION_20261029.md) remains a frozen
comparison and is not rewritten as a shared status record in this leaf packet.
