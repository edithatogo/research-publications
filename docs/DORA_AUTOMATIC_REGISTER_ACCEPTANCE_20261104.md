# DoRA automatic collection to publication register — 4 November 2026

Scope: the existing DoRA publication collector and the existing SharePoint
publication register. This is separate from the DoRA activity register and
from semantic-model/report refresh.

The selected acceptance combines today's successful natural collection with a
native continuation from that exact completed archive. It does not claim a
second full crawl or observation of the next post-repair daily recurrence.

## Source and implementation

The natural daily collection completed at 07:04 Brisbane on 4 November: 709
publication handles, with full HTML stored and the complete checkpoint verified.
The repair appends archive-to-register admission after that checkpoint, preserving
all original acquisition actions, pacing, connections and the 04:30 Brisbane
schedule. No incomplete generation can enter the new stage.

`prepare_dora_register_bridge.build` compiles the additive definition from exact
collector and accepted writer preimages. It inventories the complete register,
recognises historical DoRA key/URL aliases, and projects only missing handles
from their stored full-metadata HTML. Identity and title are checked before
admission. Source description, publication type and archive provenance are
retained; affiliation attribution remains explicitly unevaluated. Existing
records are preserved, including review fields, enrichment and legacy identities.

The qualified writer's identity lookup and create mapping are reused. Creates
have no automatic retry; a failed or ambiguous write requires readback before
recovery. Each admission has a subsequent identity readback. Missing keys are
processed serially. The inventory fails closed at 5,000 rows or a continuation
link rather than silently accepting partial coverage.

## Acceptance evidence

**Accepted for zero-change commissioning of automatic collection → list update.**

| Check | Result |
| --- | --- |
| Natural source acquisition and complete stored archive | Pass: 709 handles |
| Native archived HTML projection | Pass: one real archived record independently compared |
| Native missing-record continuation/replay | Pass: zero missing handles; final guard true |
| Source-to-register coverage | Pass: all 709 handles represented |
| Complete independent before/after register comparison | Pass: 1,658 → 1,658 rows; every stored value unchanged |
| Nonblank SourceKey uniqueness | Pass: 1,355 unique keys; 303 legacy blank-key rows preserved |
| Existing multiple-row identities | Four historical DoRA/PubMed pairs preserved; no new duplicates |
| Saved daily collector | Pass: 13 added top-level actions; all 45 original actions preserved |
| Connections, Started state and 04:30 Brisbane schedule | Unchanged |
| Temporary qualification flow | Original definition/references restored; Stopped |
| Local verification | 2,504 tests run successfully, including 19 capability skips; 446 project checks; web-first contracts passed |

The native projection ran at 13:33 Brisbane and the exact missing-record replay
at 13:36 on 4 November. The production definition was saved at 13:37. FlowAgent
returned `PreviewConcurrencyConflict` after the exact proposed definition had
reached the service. A fresh readback proved the complete candidate, original
source actions, connections, trigger and Started state; the mutation was not
resent. The only comparison normalization was the engine's standard injected
`$authentication` reference. A transient final SharePoint read timeout was
followed by one successful bounded read-only retry.

No new DoRA row was required or created: this is a genuine zero-change cycle,
not a synthetic create test. The create mapping reuses the existing accepted
publication writer; a new DoRA-specific create and the next post-repair natural
recurrence have not been observed. Current-source coverage and preservation are
verified, not historical metadata completeness, identity consolidation or
semantic-model/report promotion.

## Evidence and rollback

Raw receipts, exact native identifiers, captured definitions, mutation intents,
run details and full inventory snapshots remain in ignored private paths:

- Delivery checkout: `private/ops/dora-auto-cycle-20261104/`.
- Original checkout: `private/ops/dora-auto-cycle-20261104/` for guarded
  SharePoint downloads and authentication receipts.

The production preimage is `collector-before/result.json`. Restore its exact
`properties.definition` and connection references through FlowAgent's preview
and update route if rollback is required; preserve its existing Started state
and recurrence. The temporary qualification flow has its own separate preimage.
No original publication rows are deleted or rewritten by this repair.
