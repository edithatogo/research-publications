# Grants source reconciliation and reviewed calendar packet — 29 October 2026

This bounded packet migrates the retained one-time reviewed source-day calendar
export, preserving canonical institutional-calendar behavior and intake/review
contracts. It also freezes a finite disposition of the scoped retained source
against canonical integration commit `eb52c529fca91192eaf37ee6a67b5303865003e4`.
Source-file differences are not feature-completion counts.

Grants delivery chat `01a1831e-cc6d-7371-9d57-021a339b708a` owns these grants-only
paths in app-managed checkout
`/Users/doughnut/.codex/worktrees/ef45/chhhs-research-publications`, branch
`codex/rims-grants-roadmap`. Packet base:
`843956ff9cfcefadc1cc23d0dddbe3714395c26d`. Sole orchestrator/integrator remains
`01a182f2-fd8e-7953-9bd2-f9b8002664a6`; shared source/model/runtime/track files
are not changed here. Native scope remains empty, including authentication.

## Executable source delivered

`build_native_calendar_export` is an additive branch in the existing
`grants_calendar.py`. It consumes already captured rows from the maintained
calendar contract; it does not select grants, classify eligibility, derive a
policy, fetch a provider or decide whether a human should approve a row.

- Only exact `Reviewed` rows with `RevisionApplied=true` and day precision enter
  the export. Month/uncertain dates remain withheld. Calendar day comes only
  from `Calendar_x0020_day`; UTC CalculatedDate is not a fallback.
- UID follows the existing DeadlineKey identity. The numeric native JSON
  item-version ETag supplies SEQUENCE for that existing item's snapshots. This
  does not establish ordering across list/item recreation or reject an old
  snapshot automatically. The caller must choose the current committed snapshot.
- Changed dates and cancellation retain UID. Cancellation is explicitly labelled
  CANCELLED and transparent/free; it does not delete a calendar event or send a
  meeting cancellation. All events are private all-day markers, with no attendee,
  organizer, alarm, invitation or subscription service.
- Existing canonical escaping/folding helpers are reused. The migrated branch
  adds rejection of conflicting ETag aliases and padded source URLs; both
  weaknesses were reproduced before repair. Malformed rows/keys/cancellation
  states and URL line injection fail closed. Source objects are not mutated.
- The new CLI branch creates an exclusive mode0600 export under an existing,
  Git-ignored `private/ops` directory, refusing symlink redirection and replacement
  of a previous export/human edit. The existing institutional CLI/output behavior
  and policy calculations are preserved unchanged.

```sh
.venv/bin/python -m scripts.grants_calendar PRIVATE_CAPTURED_CALENDAR_ROWS_JSON \
  --native-calendar --generated-utc YYYY-MM-DDTHH:MM:SSZ \
  --out private/ops/EXISTING_OWNED_DIRECTORY/NEW_SNAPSHOT.ics
```

This command writes a local artifact only. It does not import it into Outlook.
No actual calendar/source rows were exported or imported for this packet. The
retained 27 October controlled Outlook import/update/cancellation/cleanup receipt
is reused at its exact tested-client scope; it does not prove live/revocable
feeds or every calendar client. The current source migration was tested using
fictional rows only.

## Requirement reconciliation from retained plans and receipts

These are frozen evidence dispositions, not fresh service, access, policy or
current-run claims. Earlier unfinished paragraphs are retained history; later
explicit scoped acceptance supersedes only its named gates.

| Track | Accepted or covered scope | Precise residual boundary |
| --- | --- | --- |
| G02 | H01 decisions, H02 qualification/disposition and 25 October H03 coverage accepted for the exact NIH route. RGS later two-pass snapshot has34,963 unique IDs and equal ordered ID sets; record bytes differ where investigator strings reorder. | No general NIH/Australian coverage. ARC/RGS reuse/lifetime identity/lifecycle/entity mapping remain incomplete; QGIP stays candidate-only, Grants Finder metadata-only. No award/context source becomes an opportunity because it was reachable or replayed. Source admission expansion requires the missing authoritative facts, not another unchanged probe. |
| G03 | Existing schema/unique-key/version baseline and SP-N10 grants diagnostic/behavioural external-writer conflict/recovery acceptance are retained. | Historical test-row removal provenance/recoverability remains unresolved. Original race windows were missed; diagnostic proof is not original-race proof. Broader atomic-batch/native coverage is not inferred. Do not repeat completed race exercises or recreate history for source reconciliation. |
| G05 | Four-institution public route/policy disposition and reviewed-fact receipt boundary are implemented. Canonical source already contains `prepare_reviewed_institution_import`, which the retained copy lacks. | Project-specific entitlement, permitted feed/export and unresolved policy/affiliation facts remain H01; H02 intake needs those inputs plus trusted evidence/reviewer verification; H03 native source/date reconciliation remains open. Public-page reachability and synthetic verifier callbacks are not provenance or eligibility approval. |
| G06 | Typed candidate normalization, exact snapshot validation and isolated schema alignment exist. Canonical tests already cover reused award numbers, withdrawn/orphan/duplicate links and explicit reviewed confirmed-state guards. | Retained namespace/alias-duplicate and ambiguous-affiliation source guards still need migration. Authoritative key/funder mapping and reviewed identity reuse remain H01. H02 native bridge/cardinality and H03 reviewed correction/withdrawal/recovery require exact accepted sources and native assignment. Candidates never establish funded publications. Cross-vertical retained projection work is outside grants-only source ownership. |
| G08 | Selected single-operator preactivation scope is archived complete. Later canonical model/report calendar readback/render and controlled same-UID Outlook file import are accepted at their dated scope. This packet closes the native-calendar exporter source gap. | Institutional/holiday policies, cross-user privacy/Invoker/reader/form proof, live or revocable feeds and real reviewed notice/reminder/provider-deadline proof remain distinct. Later G07 own-notification activation supersedes earlier blanket disabled-state wording only for its existing fixed-operator scope; no configuration is changed here. |
| E09 | Owner-operated no-send technical scope is complete, including maintained contracts, selection/rendering/editions, owner-only storage/form and integrated no-send receipts. Canonical source already contains the core feed contracts and preparation library. | Retained storage/thread/native-input/preview/no-send builder closure and edition refinements need a separate shared feed/contribution source owner. Real thread/post/provider reconciliation, cross-user curator identity/access, qualified AI route, solution membership and native documentation publication remain adoption gates. They are not authorised sends or reasons to rebuild completed no-send slices. |

The G08 closeout's older natural-generation hash gap was superseded by later G07
residual receipts, and later activation/recovery limits are already reconciled
in the [first source handoff](G07_SOURCE_HANDOFF_20261029.md). No accepted original
worker, schedule, fixed subscription, one-send intent or native receipt was moved,
rerun or altered. The [conditional adapter](G07_CONDITIONAL_ADAPTER_20261029.md)
remains source-only and unassigned natively.

## Complete scoped source disposition

[Machine-readable disposition](../contracts/grants-source-disposition-20261029.json)
records every selected retained top-level grants script/test/contract/operating
document, plus related E09 scripts/tests/contracts as read-only dependencies.
The scope excludes generated diagrams, shared model/config paths, unrelated builders, provider
records and private/native operational tooling. It is not a whole-repository
inventory. It includes exact retained/canonical/packet hashes and seven private
receipt references, without copying their contents.

The164 source-file entries contain two integrated paths,44 already covered,
18 superseded and100 remaining. Seven receipt records are private. These numbers
classify file disposition, not164 features or100 missing operational outcomes.
`integrated` means included in this lane packet, not merged/native acceptance.
`remaining` includes finite semantic/fixture or evidence-document migration work;
it is not a requirement to publish every retained file.

Notable superseded copies are concrete safety differences:

- ARC's retained adapter lacks canonical aggregate raw-byte capture bounds.
- Retained ingestion lacks canonical source-request validation; the retained
  probe is an older authority-HTML diagnostic rather than canonical structured
  endpoint evidence capture. Do not overwrite the current intake contract.
- Retained university source/tests omit canonical reviewed institutional-import
  preparation. Its receipt schema and trusted-verifier boundary are preserved.
- Retained native schedule source/tests use TMDL description properties that the
  canonical generator already replaced after native rejection.
- The retained NIH observer and delivery tests predate this lane's exact typed
  identity and no-send/journal regressions. Older preactivation status paragraphs
  remain dated evidence, not current operational configuration instructions.

## Finite remaining source packets and dependencies

1. **Preference/ledger closure:** migrate grants_planning, grants_delivery_ledger,
   preference activation and their paired tests coherently. The retained planner
   changes six-part event identities from hash to bounded base64; the live delivery
   worker uses a distinct seven-part deadline-aware identity. Preserve both scopes
   and existing native ledger/journal identities. No subscription, opt-out or send
   migration may be inferred from a local key change.
2. **Relationship guard closure:** reconcile the namespace/alias and ambiguity
   changes in grants_relationships plus its affected tests against canonical
   reviewed-state guards. No authoritative identity or native bridge is supplied
   by those synthetic rules. Shared cross-source/people/model projections remain
   with their existing owners.
3. **Classification/recovery closure:** retained reviewed-classification,
   source-change invalidation, recovery backup/history preparation and isolated
   helper tests form explicit source families. Keep G07 wrapper modes unsupported
   until each dependency closure is reviewed. Model mutation/builders, worker
   invocation and native/auth ownership are not part of this packet.
4. **Importer/source-safety delta:** review retained evidence/timestamp/order and
   solution patch helpers with their paired fixtures. Preserve canonical-only
   source contracts/byte caps; do not replace current shared definitions or treat
   private prehardening fixtures as accepted deployment. Any current native-state
   comparison requires the integrator's separate exact assignment.
5. **Evidence-document disposition:** reconcile dated G02/G03/G05/G07/G08 native
   summaries against their referenced frozen receipts before any public migration.
   Historical status, raw identifiers and screenshots remain private. This can
   retire stale tasks without another source request, native mutation or send.
6. **E09 source closure:** the manifest names the retained missing/differing
   no-send libraries and tests. This is a shared feed/contribution dependency,
   not ownership of publications, canonical decisions, digest or delivery. Hand
   it to the existing integrator/assigned shared-source owner; no duplicate lane,
   no new framework and no speculative provider integration.

All remaining scoped paths are explicitly enumerated in the manifest rather than
left as an unbounded feature inventory. No additional provider request, native
read/write, authentication renewal, mail, post, schedule change or source/model
promotion was performed. Next operation is the integrator's source review and
serial integration; native prerequisites and existing ownership remain intact.

## Verification

The affected native/institutional calendar, planning and relationship selection
runs95 tests successfully, with one existing optional-jsonschema skip. The six
native-export cases use only fictional inputs and temporary local files. The
source-URL/version regressions failed before the two guard repairs.

Project validation passes446 checks, web-first returns PASS_LOCAL_ONLY and
Conductor reports zero structural errors. Repo-local Python3.15.1 is retained;
no dependency or runtime changes were needed. All164 retained/packet source
fingerprints and dispositions were checked, all seven receipt references exist,
and relative handoff links resolve. The integrator advanced after the frozen
comparison commit; its later committed paths have no overlap with this inventory.
Whitespace checks pass. Earlier broad/native receipts are reused at their exact
scope; none is relabelled as a fresh provider, native or operational result.
