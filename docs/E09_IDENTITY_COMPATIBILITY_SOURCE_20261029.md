# E09 identity compatibility source packet — 29 October 2026

Implements the parent-assigned four-step proposal in
[native identity reconciliation](E09_NATIVE_IDENTITY_RECONCILIATION_20261029.md).
Delivery chat `01a1831e-cc6d-7371-9d57-021a339b708a` owns this bounded packet in
`/Users/doughnut/.codex/worktrees/ef45/chhhs-research-publications`, branch
`codex/rims-grants-roadmap`, based on `e2b387c8`.
The parent retains integration, shared contracts, native objects and authentication.

## Changed behavior

The E09 input validator now accepts the exact retained three-family union:
existing lowercase-hex PUB keys, positive ASCII decimal PMID keys, and uppercase
`DORA:` followed by the exact official HTTPS DoRA handle URL and two positive
ASCII decimal path components. Full-string matching rejects padding, leading
zeros in numeric components, Unicode digits, signs, decimal/exponent forms,
case changes, alternate hosts/paths, ports, credentials, encodings, queries and
fragments. The supplied identity is returned unchanged. Syntax acceptance grants
no canonical publication/model membership.

The retained pure read-only native-row adapter is included with its synthetic
tests. Changes from the retained source are the Apache-2.0 header and explicit
row-object/positive-item-ID validation before sorting, so malformed mixed input
fails through ValueError without a partial result. No capture, login, transport,
private binding or deployment helper is included. Source/status mapping, raw
first/last/publication-date evidence, ETag/version, unknown-first holds, optional
last-time uncertainty, complete placeholder accounting and alias holds remain.

The builder's canonical-reference guard now accepts the same strict union.
It checks literal case using case-sensitive replacement plus exact length;
`startsWith` alone is case-insensitive. It validates ASCII digit strings without
integer or floating-point conversion, preserving arbitrarily large syntactically
valid identifiers without overflow/coercion. The identity guard expression is
5,368 characters. Function semantics were checked against the
[Microsoft expression reference](https://learn.microsoft.com/en-us/azure/logic-apps/expression-functions-reference).
The closed artifact validator admits this revised template while continuing to
reject guard bypasses, senders, target changes, retries and implicit authority.

## Consumer and migration evidence

| Consumer/boundary | Evidence |
|---|---|
| Discovery and selection | Exact union accepted; strict malformed variants rejected; status/tier and timestamp rules retained. |
| Native-input adapter | Synthetic 83-row PMID/DoRA fixture stays entirely held: 74 possible, nine confirmed; placeholder, alias, raw timestamp, ETag/version and malformed-batch cases covered. Equal keys across qualified and unknown-time rows stay held together. |
| Rendering, threads and storage | Each family passes through real discovery, renderer, thread preparation, lossless envelope and replay with the same SourceKey/thread ID. Human notes, null provider/authority and no-send behavior persist; changed canonical identity cannot revise an existing thread. |
| Editions and saved history | Candidate references preserve source-key/tier output. A changed reference produces a separate immutable snapshot and cannot overwrite the prior one. Existing PUB thread and edition fixture envelopes retain their exact pre-change SHA-256 values. |
| Generated graph | A strict local evaluator executes the emitted boolean/string guard against valid, malformed, oversized, case-altered and Unicode candidates, plus no-send, provider, authority, render, revision and identity tampering. This is local expression-subset evidence, not native engine execution. |

No native row migration is required or performed. No keys are mapped, generated,
trimmed, normalized or replaced. Existing saved payload bytes, hashes, revisions,
editions and histories remain valid and are not rewritten. The two shared JSON
schemas are unchanged. A real identity correction still requires an explicitly
assigned evidence-backed migration and recovery path. The optional native mapping
qualification for PMID/DoRA remains separate from this source packet.

## Verification

- Explicit repo-local interpreter: Python 3.15.1.
- Tests were introduced before the validator/guard change: candidate keys failed
  the old Python validator and graph guard, and the adapter module was missing.
  The graph tests also exposed the old case-insensitive PUB-prefix acceptance.
- Focused E09 run: 130 passed, four optional JSON Schema checks skipped because
  jsonschema is absent. After adding two further history/guard cases and extra
  malformed variants, the affected compatibility file passed all nine tests and
  142 subtests. Existing consumer suites and source-template safety tests passed.
- `scripts/agent_harness.py check --task all` passed: repository unittest
  discovery, project checks, web-first local checks, Conductor integrity and
  tooling presence. Local success does not establish tenant acceptance.
- Bounded offline read of the retained `rows-second.json` reproduced the complete
  saved `qualified-inputs.json` under sorted compact JSON serialization, with
  no row changes: qualified 1,265; placeholders 303; unknown-first 83. The input
  file still hashes to
  `628a470d6f227a781a6234555a46bed6578a43f342625f2929313f38649722eb`.
  Source rows were neither copied into tracked files nor uploaded. The earlier
  reconciliation records capture/schema provenance and frozen receipt limits.

No native/authentication call, deployment, activation, provider send or schedule
change occurred. The existing frozen native persistence evidence remains PUB-only.
