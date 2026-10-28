# Publication acquisition builders: source packet — 29 October 2026

Verified entry base: `546926c0ab3186527a3d4c9d738d55712ff7ae68` (PR64).
The lane was clean, fetched origin, confirmed that exact main and fast-forwarded
without resetting, cleaning or replacing its environment. This packet owns only
the four builder/patch modules, their paired tests and this leaf. Shared constants,
contracts, runtime, dependencies, locks, handoffs and tracks are unchanged.

## Dependency closure and manual scope

| Module and paired test | Delivered source behavior |
| --- | --- |
| `prepare_qgip_source_collection` | Pure constructor and `compose`/`gate` helpers using the six existing canonical `grants_qld_qgip_api` constants. Produces Stopped/manual output with an explicit supplied Embedded SharePoint reference. |
| `prepare_pubmed_acquisition` | Pure full-selected-scope XML acquisition proposal. Reuses QGIP's reference/envelope helpers and current `collect_pubmed.validate_config/BASE`. Preserves article and book PMID paths and own DOI fields, with no citation selection. |
| `prepare_dora_publication_collection` | Pure established-collection/full-metadata HTML proposal and fingerprint-bound own-DOI checkpoint extension. No new holdings, PDF retrieval or admission. |
| `patch_clinicaltrials_read_retries` | Pure definition fingerprint and explicitly selected two-leaf same-GET retry patch. Its tests use a minimal fictional definition, avoiding imports of the absent ClinicalTrials collector/discovery family. |

The first three constructors produce Stopped/manual candidates. The retained
`with_daily_updates` names explicitly refuse recurrence proposals in this packet;
their original implementations remain history in the original checkout. No daily
source operation or native schedule is restored or changed. Retry patches preserve
the supplied existing flow state and triggers; they do not activate that flow.

QGIP requires an explicitly supplied Embedded reference with the exact SharePoint
API and clean existing connection/logical-reference identity. Invoker references
are refused, never converted. The supplied reference, source mode and diagnostic
expansions are deep-copied intact; no connection, credential or account is invented.
Strict site/archive checks reject credentials, query/fragment scope, path traversal,
encoded separators, control characters and unqualified ports. These local checks
do not establish actual tenant access or qualify a supplied binding natively.

The packet imports no private bindings, tokens, journals, collector drivers or
native mutation/authentication entry points. The two available CLIs read only
explicit local inputs and create output exclusively. QGIP tenant-specific output
stays under the repository's ignored `private/ops`; the retry CLI requires an
explicit `--action discovery` and/or `--action detail`. Neither submits a request.

## Raw preservation and completion structure

QGIP retains complete native-decoded HTTP JSON values, including failed response
envelopes, before validation or candidate filtering. It proposes two bounded
serial complete reads, exact offsets/totals and unique keys, before/after source
identity/schema checks and a last manifest write after every saved file has a
base64 readback comparison. Original HTTP wire bytes and native cryptographic
hashing are explicitly not claimed by that serialization path.

PubMed retains both search responses and complete XML before checking exact batch
PMID equality, before/after search identity and complete fetched identity coverage.
The original XML is saved before the temporary DOCTYPE adjustment used for XPath.
Both article/book IDs and own ArticleIdList DOI paths are retained; cited ReferenceList
identifiers do not become related-source inputs. Completion checkpoint creation
follows manifest save/readback verification. Caller policy/configuration objects
are copied, so editing a returned proposal cannot alter their authoritative inputs.

DoRA retains complete collection pages and full metadata HTML. Before/after
collection keys and every selected record reconcile before a manifest; own DOI
projection follows raw metadata save/readback and record-identity guards. The
checkpoint extension requires the exact current definition hash and refuses
occupied top-level, loop-action or newly managed Manifest namespaces. It never
overwrites an existing completion action or DOI-provenance field. Rejected
preparation leaves the supplied graph and policy untouched.

The review follow-up preserves every existing `Record_file.runAfter` dependency
and status list, adding `Set_own_dois: [Succeeded]` as a further requirement.
Unknown predecessors, sibling cycles and guards statically incompatible with
required `Guard_record` success are refused. This is a limited dependency check,
not an interpreter or proof of arbitrary WDL conditions. Before adding the array,
a conservative recursive scan rejects existing `OwnPublicationDOIs` declarations
under any initializer/action name or nesting, including case variants.

PubMed search/XML and DoRA collection/record success paths retain their original
content expressions and success dependencies. Separate Failed/TimedOut branches
now propose raw failure envelopes containing the available HTTP outputs and body,
capture time, stage and explicit `accepted:false`/`source_valid:false`. A missing
body is labelled `unavailable` and remains null; no XML, HTML or success response
is synthesized. These envelopes are distinct from successful source artifacts.
The branch sets a generation failure flag before its separate zero-retry
save/readback/verification chain. Completion guards require that flag to remain
false; successful failure-evidence storage cannot authorize a complete marker.
Serialization certifies no original transport bytes. These generated branches
are not an installed or verified durable native observer.

These are generated WDL structures and local fixture checks. Native connector
response shapes, WDL execution, HTML/XML behavior, complete stored content,
failure paths and output fidelity remain separate qualification. No native
completed marker or new provider observation is asserted by local construction.
The already accepted source captures and comparisons are not repeated.

## Selected retries and observer limitation

The shared retained retry policy is finite exponential recovery: count3,
initial/minimum interval10seconds and maximum interval1minute. It is applied only
through an explicit selected-path argument. Unknown, duplicate, mutation or
implicit selections fail closed. No SharePoint save, marker write, register update,
send or other effect receives a retry policy from these functions.

ClinicalTrials patches only the two known discovery/detail HTTP GET leaves.
Their anonymous input shape and exact maintained URI expressions are checked;
the literal root is parsed for HTTPS, exact host/path and absence of credentials
or fragments. A provider URL embedded inside another hostname/query is not an
allowlist match. Extra body/authentication inputs and changed custom policies are
refused. A matching already-installed policy is an unchanged local proposal,
not evidence that native retry execution or cross-run resumption occurred.

PubMed bounded recovery similarly restricts selected ESearch/EFetch POST leaves
to the exact NCBI URI, form headers and maintained read-only body expression.
Those POST endpoints are reads; arbitrary POST bodies or suffixes are refused.
The complete definition hash must match before preparation. Already-recovered
PubMed leaves require reconciliation rather than another policy rewrite.

The PubMed base constructor creates **no failure observer**. Recovery requires
an existing supplied `Observe_failed_generation` Scope, nonempty actions,
failure-only dependencies on existing actions, separately supplied observer bytes
and their exact SHA256 matching that scope. The patch preserves those values
unchanged and edits only the selected retry policies. An absent, changed or
unbound observer is refused; no observer is synthesized by production code.

The observer checks prove local preimage identity and limited structure only.
They do not prove durable storage, source health or native provenance. Positive
unit fixtures are explicitly fictional supplied scopes and are not native
observer evidence. Before adoption the native owner must supply the real current
observer/readback and independently prove its durable failure receipt and recovery
behavior. A dictionary, a hash or the presence of a Scope is not that proof.

Saved QGIP reference JSON, retry CLI definition JSON and PubMed observer preimage
JSON now share a strict parser local to this packet. Duplicate keys at any level
and NaN/Infinity values are refused before preparation. They are not silently
collapsed into an apparently matching current preimage. Valid JSON and existing
create-only output behavior remain unchanged; no new parser dependency is added.

## Verification and native remainder

Actual repo-local Python3.15.1. The review follow-up passes **45 focused stdlib
tests**:9 QGIP,14 PubMed,11 DoRA and11 ClinicalTrials retry tests. The original
37-test baseline remains in its original logs. Current cases include changed
input/definition/observer hashes, strict URI/body selection, action/field collisions,
input immutability, preservation of unrelated actions and references, manual-only
output, selected policy diffs, deterministic unchanged retry preparation and local
CLI create-only/failure preservation, strict saved JSON, preserved record guards,
variable collisions and failure-route structure. A small local runAfter model
checks Failed/TimedOut branch selection, failure-evidence ordering and skipped
success paths; it does not execute WDL, storage or a native observer.
Ruff check/format and leaf link/diff checks
pass for the owned packet. No broad unchanged harness is rerun.

Ignored `private/ops/acquisition-builders/` retains original eight-file hashes,
baseline/failing/final focused logs and source disposition receipts. The follow-up
uses `review-*-final.log` and its separate receipt, preserving earlier evidence. All eight
original files remain byte-identical to the recorded authoring-checkout versions.
Neither its active services nor its journals/environment are touched.

Native acceptance remains false/unproved: actual existing flow identity and
binding ownership, fresh preimages, compatible saved definitions, complete raw
storage, interrupted acquisition, retry/failure-observer execution, checkpoint
readback, source health, consumer admission and scheduled success all require
their existing owner and exact operation qualification. No adoption, activation,
provider request, send, authentication recovery or recurrence is queued here.
This closes the bounded source dependencies identified in the
[provider disposition](PUBLICATION_PROVIDER_SOURCE_CLOSURE_20261029.md); the
historical42part capture driver remains excluded.
