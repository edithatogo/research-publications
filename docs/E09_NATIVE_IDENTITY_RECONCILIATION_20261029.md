# E09 frozen native identity reconciliation — 29 October 2026

Read-only technical reconciliation against source commit `76fc710b394da8291e14321120f15a768c83884c`.
Owner: delivery chat `01a1831e-cc6d-7371-9d57-021a339b708a`, worktree
`/Users/doughnut/.codex/worktrees/ef45/chhhs-research-publications`.
The integrator retains shared contract and native scope. This leaf proposes a
change; it implements no validator, schema, adapter or native change.

## Finding and correction of the blocker

The canonical E09 source validator is narrower than the retained E09 input
implementation. Its PUB-only restriction is not established by the E09 spec or
captured SharePoint field schema. The retained spec explicitly includes committed
source/candidate records outside the accepted canonical set, without inflating
accepted totals. A bounded compatibility repair can preserve existing native
references without a new business mapping decision or invented PUB identities.
This supersedes any earlier implication that every retained candidate must first
be mapped to a PUB key merely to satisfy E09 input syntax.

The evidence does **not** establish persisted native mappings for all three
families. Distinguish observed registry identity, accepted adapter syntax,
temporal eligibility, stored mapping and accepted publication/model membership.
An extension must preserve those boundaries.

## Frozen provenance and acceptance limits

All private evidence remains in the original authoring checkout
`/Volumes/PortableSSD/GitHub/RIMS/chhhs-research-publications`. Paths below are
relative to its `private/ops/`; no private rows or target identifiers are copied.
No new native read, authentication, provider request or mutation was performed.

- `2026-10-24-e09-resource-qualification/read-status.json`: captured
  `2026-10-24T11:22:35.581123+00:00`; its acceptance was checked at
  `2026-10-24T11:24:18.499343+00:00`.
- The corresponding `fields.json` identifies `CanonicalKey` as `field_2`, type
  Text, maximum length 255, indexed and unique, **not required**, with null
  ValidationFormula and ValidationMessage. This captured schema has no PUB-only
  formula. Required logical input remains stricter than the native optional field.
- `2026-10-24-e09-phase2/input-qualification.json`: captured
  `2026-10-24T11:51:29.433492+00:00`, 1,651 rows, stable double read. Independently
  reproduced locally: remove only `odata.id`, sort rows by `Id`, serialize with
  sorted keys, compact separators and `ensure_ascii=False`, UTF-8 SHA-256:
  `d89b44facfd76979669b48ac0f0bdc242ab22284fec5dd943b4ae89ea9d5bda5`.
  Both saved projections match under that normalization; saved before/after
  metadata also match. Raw response bytes differ and are retained separately.
- Phase 2 `acceptance.json`, checked `2026-10-25T01:24:04.610198+00:00`, records
  `PASS_QUALIFIED_NATIVE_SELECTION_AND_OWNER_ONLY_NO_SEND_MAPPING`.
  Its source hashes match all eight retained source/schema files today; the six
  script hashes differ from this canonical worktree, while the two JSON schemas
  match. These are check-time source fingerprints, not independent server
  attestations of deployed Python or original acquisition time.

| Family | Keyed registry rows | Retained adapter syntax | Temporally qualified rows | Actual saved no-send mappings |
|---|---:|---|---:|---:|
| `PUB:` lowercase hex | 1,265 | Accepted | 1,265 | 2 |
| `PMID:` positive decimal without leading zero | 16 | Accepted | 0 | 0 |
| `DORA:` official HTTPS handle URL | 67 | Accepted | 0 | 0 |
| Missing identity placeholders | 303 | Accounted separately | 0 | 0 |

All 83 PMID/DoRA rows have unknown/unqualified first-observation instants:
67 DoRA possible, seven PMID possible and nine PMID confirmed by saved review
status. Status alone does not establish temporal eligibility or canonical model
membership. The qualified PUB rows comprise 1,256 confirmed, eight possible and
one rejected; selection excludes the rejected row. Initial no-send baseline
produced zero new entries; the technical catch-up preview contained 1,264.
Locale-naive processing timestamps must not be guessed into aware instants.
LastObservedUTC is latest registry upsert processing time, not upstream freshness.

The actual confirmed record's two saved revisions and actual possible record
all retain PUB identities. Their payload hashes recompute exactly. The accepted
receipt records two active actual no-send mappings, 13 controlled runs (nine
successes, four expected guard failures), zero channel messages/provider message
references and final flow state Stopped. These remain historical bounded receipts,
not fresh native verification. They do not prove PMID/DoRA mapping persistence.

## Source and consumer impact

- `scripts/e09_first_discovery.py` currently requires `^PUB:[0-9a-f]+$` and
  describes every CanonicalKey as a deduplicated PUB identity. Retained source
  accepts the strict three-family union, preserving the exact supplied value.
- Retained `scripts/e09_native_inputs.py` maps SourceKey/CanonicalKey/status/first/
  last observation from `field_1/field_2/field_17/field_19/field_20`, accounts for
  every row, retains native version/ETag/raw timestamp evidence, and holds equal
  canonical alias groups. It neither mints keys nor merges aliases. This adapter
  is not yet present in the canonical packet.
- `e09_post_content.py` and `e09_subscription_editions.py` consume the common
  validator. `e09_thread_mapping.py` validates through rendering and retains
  immutable canonical identity during revision transitions. Source-based
  `thread:{SourceKey}` identities must remain unchanged.
- The newly closed canonical `build_e09_no_send_flow.py` explicitly enforces PUB
  syntax in its native expression guard. A Python-only extension would leave
  this consumer inconsistent. Preserve every other envelope, revision, target,
  uncertainty, human-edit and no-send guard when designing the bounded extension.
  Do not redeploy over the existing owner's stopped native flow.
- The preparation/storage JSON schemas do not expose a CanonicalKey property
  with a PUB-only regex. Their source/thread-key constraints are separate; they
  are not evidence of native canonical identity validation. No schema widening
  is justified merely by their filenames or by this input mismatch.

## Smallest proposed compatibility packet, pending parent assignment

1. Extend the E09 reference validator and explanatory text only to the retained
   union: `PUB:[0-9a-f]+`, `PMID:[1-9][0-9]*`, and
   `DORA:https://dora.health.qld.gov.au/qldresearchjspui/handle/` followed by two
   positive decimal path components without leading zero. Use whole-string
   matching and retain the existing whitespace/identifier checks. Do not accept
   other hosts, paths, credentials, ports, queries, fragments or encoded variants.
2. Migrate the reviewed native-input adapter as an explicit dependency-closed
   source packet. Keep complete accounting, raw evidence, unknown-first holds,
   optional-last uncertainty and alias reconciliation intact. Accepting syntax
   does not release the existing 83 temporal holds.
3. Extend the builder's equivalent guard and artifact validator together, retaining
   all existing safeguards. Add synthetic dependent-consumer cases for discovery,
   rendering, mapping/storage replay and editions, plus builder guard equivalence.
   Prove byte-identical PUB outputs/IDs, unchanged source/thread IDs for all
   families, strict malformed-key rejection, held aliases, immutable identities,
   no-send/null references, and timestamp holds. A native PMID/DoRA persistence
   claim requires separately scoped qualification; synthetic cases cannot supply it.
4. Treat this as additive input acceptance, with no row migration or automatic
   key conversion. Preserve saved payload bytes, hashes, revisions, editions and
   history. Do not recompute existing snapshots or change model keysets. Any
   actual identity correction remains an explicit evidence-backed migration with
   an assigned owner, prior-state recovery and dependent-consumer reconciliation.

## Reproducible evidence fingerprints

SHA-256 of saved bytes, under the private root above:

| Relative evidence path | SHA-256 |
|---|---|
| `2026-10-24-e09-resource-qualification/fields.json` | `d878c7aeb2282a13535bb631912b3acb40c3e516d5bc5cd9358ba1ba0082fca6` |
| `2026-10-24-e09-resource-qualification/read-status.json` | `74e07fca95eb12b5098de194700dc0e4caf6995782d75bd9fc25050939ed26c6` |
| `2026-10-24-e09-phase2/rows-first.json` | `857eafbd78846546bc1b5148e45f260c3586ec5b5d1df1c8bcb0ceff87880d21` |
| `2026-10-24-e09-phase2/rows-second.json` | `628a470d6f227a781a6234555a46bed6578a43f342625f2929313f38649722eb` |
| `2026-10-24-e09-phase2/input-qualification.json` | `b303e93535e64d1c1ac06a0b639b850b054e0f9588438b7e693cc2068e9f2b96` |
| `2026-10-24-e09-phase2/qualified-inputs.json` | `e42f6c7c28b10589125425312e9492482fb87a14ba250b7b9750454335c0d5da` |
| `2026-10-24-e09-phase2/acceptance.json` | `bd6837810a1ccf9d55f957bdfc100e7c30e223774c728a1e88401142ac74e28a` |

Narrative receipts/specification remain in the original checkout at
`docs/E09_RESOURCE_QUALIFICATION_20261024.md`,
`docs/E09_PHASE2_SELECTION_AND_MAPPING_20261024.md`,
`docs/E09_DUPLICATE_CORRECTION_VERIFICATION_20261024.md`, and
`conductor/tracks/collaborative_research_feed_20261022/spec.md`.
The prior canonical packet is [preview/builder source closure](E09_PREVIEW_BUILDER_SOURCE_20261029.md).
