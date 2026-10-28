# Publication document-library source disposition — 29 October 2026

This bounded packet closes offline metadata preparation for existing saved paper
copies and accepted report artifacts. It imports four of the six files classified
as `retained_document_library_packet` in the [frozen source inventory](../audit/publication-source-disposition-20261029.json).
The two native appliers remain preserved in the original authoring checkout.
There is no tenant operation, authentication/cache access, artifact generation,
field creation, flow invocation, schedule change or send in this packet.

## Six-file disposition

| Listed source requirement | Disposition and evidence |
| --- | --- |
| `scripts/prepare_paper_library_metadata.py` | Imported and hardened. Offline plan for existing Title/Description only; exact linked-copy/hash/length/version/provenance evidence, known UTC capture time, exact parent record link, protected human fields and unchanged replay. |
| `tests/test_prepare_paper_library_metadata.py` | Imported and extended: 14 tests, including immutable inputs, changed managed blocks, source/recovery drift, historical content ETag preservation and create-only CLI output. |
| `scripts/prepare_report_library_metadata.py` | Imported and hardened. Reconciles retained receipt, source context and canonical manifest; preserves each artifact's own output revision, source query/template hashes and count scope. Rejects conflicting metadata, ambiguous native property aliases, duplicate file/item identities and invalid provenance/counts. |
| `tests/test_prepare_report_library_metadata.py` | Imported and extended: 14 tests, including cross-generation failures, exact bindings, human conflicts, independent file preimages, immutable field contract, unknown revisions and failure/replay preservation. |
| `scripts/apply_paper_library_metadata.mjs` | Retained, not imported or invoked. Frozen SHA256 `86d0a3b62ab42f97a1f5fa0c9e3c6faeab1a791f3a2fd908dc8ff26a80c2f6c8`. Native/auth dependency described below. |
| `scripts/apply_report_library_metadata.mjs` | Retained, not imported or invoked. Frozen SHA256 `ddd9a9f2fd08ed31ab67feaae522b87f0c13ea8103d586386ae82b0f2a53c45c`. Native/auth dependency described below. |

Original working-tree bytes for all six still match the frozen inventory at this
checkpoint. The inventory remains unchanged; this leaf supplies the later
disposition. Original native receipts, bindings, environments and journals remain
with their owner. The source comparison used the existing original
`docs/PAPER_LIBRARY_METADATA.md`, `docs/REPORT_LIBRARY_METADATA.md`, the
19 October paper-library entry in the E01 archive specification and the T14
16 October structured-output qualification record. Those dated native claims
were not requalified or copied into this packet as current acceptance.

## Output route and preservation

Evaluate the user's preferred maintained SharePoint Word-template route first
for an improved recurring document. The retained 16 October exact-route evidence
records no selected RIMS document-generation template or supported generation
entry point, a form server-save error and unqualified repeating-field mapping.
The later retained suite direction also distinguishes saved library properties
from Word-body refresh. These are dated gaps, not a fresh capability verdict.
Keep the existing working HTML/CSV/PDF and manual Word outputs until one selected
template passes complete repeating/optional content, provenance, editing,
reader access and recovery parity. These metadata preparers neither generate a
body nor provide that qualification. No replacement generator or framework is added.

Paper plans append one exact managed provenance block while preserving human
Description text and existing Title. A changed, partial or duplicated managed
block fails closed. Article-version identity and the original capture timestamp
are retained. A historical content-verification ETag is not rewritten to equal a
later metadata ETag. Saved-but-unlinked recovery evidence remains ineligible.

Report plans keep generation/source/query/refresh identity, complete and monthly
counts/key hashes, template hash where recorded, manifest URLs and each output's
own revision. A canonical artifact receives no invented HTML template version.
Title and Description remain outside the report metadata scope. Conflicting
existing properties, including mapped human edits, are refused. Plans contain
independent copies of preimages; editing a returned plan cannot alter its input
evidence or subsequent field contracts. This does not verify supplied assertions
against a tenant or establish a complete artifact membership set on its own.

Both CLIs bind the input file path and SHA256 and create their output with
exclusive creation. A failed preparation leaves the input and an earlier plan
unchanged and creates no replacement plan. Neither preparer imports a native
client or sends a request. A plan is metadata preparation, not permission to apply
it, substantive review, clinical/scientific acceptance or authority to issue.

## Exact remaining applier dependency

Both retained `.mjs` programs select a global CLI distribution and call
`auth.restoreAuth()` without the current workload's pinned SDK, selected
client/account/tenant/resource/callback checks or shared-owner lock. They block
some interactive hooks only after restoration and use a standalone CLI request
for initial access. Their existing conditional ETags, narrow-field scope,
transport journal, saved-byte/version/access checks and unchanged replay are
useful retained behavior; those do not qualify their current authentication
entry point. No global CLI or credential store was invoked to test them here.

The next executable **source** packet is to adapt these two exact native
operators to the parent's existing qualified workload entry point, preserving
exact field/item targets, preimages and durable one-send recovery. Offline
transport tests must prove identity/SDK drift and interactive authentication are
refused before any request; unexpected targets, concurrent edits, repeated or
uncertain effects and partial-batch failures must preserve the journal and require
readback. Importing their old standalone authentication path is not a dependency
closure. Parent retains shared wrapper/auth ownership and every native operation.
Current shared renewal remains untouched; this packet does not queue a retry.

Only after source qualification and an exact native assignment can the owner
check actual field IDs/internal names/types, file/item association, current bytes,
ETags/checkouts, version retrieval, access, output rendering and zero-write replay.
Existing historical receipts need no repeat merely to reconcile this source audit.

## Verification

Repo-local interpreter: Python 3.15.1. The original two imported test modules
passed 15 tests before changes. New failing cases reproduced the mutable-preimage,
provenance-link, malformed-identity/count, unknown-revision and field-alias gaps
before fixes. Final focused run: **28 tests and 13 subtests passed**. CLI failure
and exclusive-output tests use synthetic temporary files and the selected
interpreter. Ruff check and format check pass for the four imported files.

Full local harness: **1,189 tests, 25 existing capability skips**, 446 project
checks, web-first contracts, Conductor structure and tooling checks pass.
Ignored evidence: `private/ops/document-library-source/` contains original-byte
hashes, failing-test logs, focused results and the full harness log. Local checks
prove source behavior only; native and operational acceptance remain separate.
