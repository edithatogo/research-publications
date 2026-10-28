# E09 preview and no-send builder source closure — 29 October 2026

This packet closes the two independent retained helper families identified in
the [storage handoff](E09_SOURCE_STORAGE_HANDOFF_20261029.md): workflow previews
and a manual SharePoint-only mapping graph builder. It introduces no workflow
framework, native operation, authenticated actor, provider/AI route or delivery.

Chat `01a1831e-cc6d-7371-9d57-021a339b708a` owns only these two E09 source modules,
their paired tests and this leaf handoff, under sole integrator
`01a182f2-fd8e-7953-9bd2-f9b8002664a6`. Actual app-managed checkout remains
`/Users/doughnut/.codex/worktrees/ef45/chhhs-research-publications`, branch
`codex/rims-grants-roadmap`. Packet base:
`af4a54319f037e75ea4327f7329ab87f74ed7f8e`. Native scope is empty.

## Source delivered

`e09_workflow_previews.py` retains the four pure preparation functions:

- Contribution preview requires matching caller-supplied trusted actor and exact
  source/project revisions; a submission cannot contain a curator decision.
- Curator preview prepares append-only proposed decision evidence, refuses
  replacement of completed decisions, requires caller-supplied curator access,
  exact revisions and a concrete ETag reference. It always keeps
  canonical_write=false. Accept/amend is a requested decision requiring an
  authorised update path, not an actual canonical update.
- Preference preview preserves the original before image, enrolment, subscriber
  and contact route; its next revision always clears delivery authority. A prior
  authority reference in the retained before image is history, not permission.
- Grounded advisory preview checks supplied excerpts against supplied retained
  text and explicit identifiers. Hostile instructions remain inert data. No
  extraction/model/provider is called, and authoritative remains false.

Every factory passes its output through `validate_no_send_preview`. The exact
artifact fields/kind/payload/fingerprint are checked, intended_outcome must be
no_send and native_write must be the boolean false. Nested canonical/delivery
write claims, executor fields, forged outputs, identity/history drift and
rehashed authority injection are rejected. Fingerprints establish local content
consistency only; they do not prove source truth, trusted actor provenance,
access, native identity or curator authority. Native adapters must provide those
independently; form-supplied assertions are insufficient.

`build_e09_no_send_flow.py` retains the existing mapping qualification template,
with a closed artifact validator. It returns an in-memory definition; it does
not create/save/import/start/invoke a flow or a connection. Its dependencies are
standard libraries, existing renderer wording and the existing two E09 schemas.
Shared schemas/contracts, storage/edition code and identities are unchanged.

## Fail-closed graph boundary

`definition(site_url, list_id)` builds and validates the artifact.
`validate_no_send_definition(graph, site_url, list_id)` can revalidate a frozen
artifact before any separately authorised adoption. Validation is deliberately
limited to this exact source template; service annotations or later variants
need a separate reviewed qualification, not automatic normalization.

- Only Compose, ParseJson, If and the exact existing SharePoint HttpRequest
  connector action are admitted. Nested HTTP/sender/child-workflow/unknown nodes
  are rejected. Connector methods, same supplied site/list target and retry none
  are independently enforced. Only fixed mapping GET/create/conditional update
  paths occur; no mail, Teams, provider, AI, arbitrary HTTP or dispatch node exists.
- The sole trigger is manual Request/Button, concurrency1. Its exact input
  schema requires NoSendOnly=true, rejects extra fields and provides no authority
  default. Recurrence and additional triggers are rejected.
- The local receipt-schema copy is narrowed to intended no_send, recorded_only
  or failed_uncertain outcomes, and null post/authority references. Shared
  contracts remain byte-identical. The result states no_send=true,
  message_created=false and provider_reference=null; root outputs stay empty.
- Independent connector/type/trigger/receipt/result policy also validates the
  factory output, so an accidental new sender or implicit authority in the
  factory fails even when compared against that same new template. Canonical
  JSON template comparison additionally protects every guard, branch dependency,
  default and output against artifact mutation, preserving boolean/number types.
- PUB hex remains the canonical identity. Native expression guards require that
  syntax and bind the receipt ID to the thread ID. No PMID/DoRA canonical-key
  widening or rekeying is introduced.
- Existing no-write replay, uncertain-outcome hold, preserved human notes and
  aliases, expected revision/hash/ETag checks and conditional mapping update are
  retained. Encoded traversal, padded/control-bearing or port-bearing targets,
  credentials, fragments, malformed IDs and non-SharePoint sites fail before
  graph preparation.

These are source-graph checks, not a Logic Apps/Power Automate execution proof.
The graph's length/hex checks do not recompute cryptographic envelope hashes.
Only operator-qualified envelopes, validated by the existing local storage/thread
helpers and bound to frozen accepted input, are in scope. This is not an
untrusted-user endpoint or proof of native semantic equivalence. Native template
parsing, exact saved definition/bindings, no-retry behavior, runtime rejection,
readback and recovery still require an assigned isolated DEV object and owner.

## Native-input projection remains blocked

The retained `e09_native_inputs.py` calls the retained widened canonical parser
on source PMID/DoRA values. That behavior is incompatible with the authoritative
PUB-only canonical contract. It is not imported, and `e09_first_discovery.py` is
unchanged.

Source PMID/DoRA values may remain provenance or explicit mapped references only.
A later adapter must consume an existing accepted mapping to an existing PUB
identity, with its source key/record reference, evidence/version and ambiguity
boundaries. No such mapping is supplied or consumed by this packet; this is not
an assertion that none exists elsewhere. Missing/ambiguous mapping must remain
unresolved, never generate a new PUB key, silently relabel a source ID, merge
business records or broaden the canonical parser. Parent retains that mapping,
source-binding and inclusion decision.

## Verification and finite residual work

The21 focused preview/builder tests pass without skips, including the retained
10 cases and11 adversarial cases. The current E09 discovery selector passes112
tests with four existing optional-jsonschema skips; builder tests are a separate
selector because their filename starts test_build. These are local source
results, not native acceptance. Logs/checks are under the lane-owned temporary
`/Volumes/PortableSSD/tmp/rims-e09-ef45-preview-` prefix.

Project validation passes446 checks, web-first returns PASS_LOCAL_ONLY and
Conductor reports zero structural errors. Repo-local Python3.15.1 and existing
locks/runtime are unchanged. Shared feed contracts, both E09 schema files and
first-discovery identity parser remain byte-identical. Relative links and diff
whitespace checks pass. No private input/contribution/edition/actor records were
copied, and the original native jobs/bindings/journals remain untouched.

Finite remaining dependencies:

1. Parent-owned accepted source-reference-to-PUB mapping and frozen native column
   projection are required before revisiting native input. No automatic rekeying.
2. Native actor/curator access and authenticated submission/update routes remain
   external prerequisites; previews cannot establish them.
3. The parent retains exact flow/storage target, actual binding/solution state,
   schema, isolated native save/runtime/no-send/uncertainty/rollback proof and any
   future adoption decision. This packet changes none of those objects.
4. Retained advisory-consumer refinements remain a separate source review against
   existing schema/manual fallback. Exact AI prompt/provider/data handling and
   actual posting/delivery routes remain unqualified and inactive in this lane.

Next operation is serial source review/integration of this packet. No auth,
native calls, external posts/mail, source/provider/AI uploads, schedules or actual
delivery were performed or authorised by these source artifacts.
