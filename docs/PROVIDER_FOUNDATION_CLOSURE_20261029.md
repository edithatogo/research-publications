# Provider foundation source closure — 29 October 2026

Owner: publications lane `01a1831e-449a-7693-af1a-08bb23391c76`, actual checkout
`/Users/doughnut/.codex/worktrees/fa70/chhhs-research-publications`, branch
`codex/rims-publications-roadmap`. Entry base is parent-reviewed/local-merged
`36e66cbff70058b1732bf35f0bf108711364660b`. The parent explicitly selected continued
source development on this base while hosted main integration remains serial.
This is not a verified-main or native acceptance claim.

## Exact assignment

Five modules: `source_capture_receipt.py`, `source_http_retry.py`,
`clinicaltrials_source.py`, `crossref_source.py`, `datacite_source.py` under
`scripts/`; five paired tests under `tests/`: `test_source_capture_receipt.py`,
`test_source_http_retry.py`, `test_clinicaltrials_source_capture.py`,
`test_crossref_source_capture.py`, `test_datacite_source_capture.py`; this leaf.

The five original modules and original Crossref/DataCite tests were read/copied
only within this assignment. Their original authoring copies remain byte-identical
to the entry hashes. Three focused test files replace the need to import mixed
funding/workbook/health tests. No unrelated provider, health, registry, native,
model, report, runtime, dependency, authentication or shared coordination file
changed. ROR, ARDC and source assertion consumers remain a later packet.

The existing canonical strict JSON parser from
`patch_clinicaltrials_read_retries.py` is reused unchanged. Dependencies otherwise
remain the standard library and these five modules. Imports have no acquisition
side effects. The transport helper now owns the common provider-read loop;
the receipt helper performs local filesystem operations only.

## Capture and retry contracts

`capture(ids, output, resume_from=None)` remains available for all three sources.
The new keyword-only `opener`, `max_attempts`, and `sleep` support explicit read
policy and fictional transport testing. `max_attempts=1` is the default: **zero
retries**. An explicit integer budget of 2–4 permits only classified temporary
GET failures, with 10/20/40-second bounded backoff. Boolean/float/out-of-range
budgets fail before acquisition. The retained `MAX_READ_ATTEMPTS=4` constant is
the upper bound, not the default. CLI `--max-read-attempts` follows the same rule.
The former three private read loops are consolidated in `read_response`; they
are not separate public acquisition interfaces.

The selected temporary HTTP statuses remain 408, 425, 429, 500, 502, 503 and 504.
Known temporary connection/timeout/network errors and temporary DNS resolution
can qualify. TLS, permanent DNS, unknown network errors, permanent HTTP errors,
storage failures, malformed JSON, projection errors and incomplete reads are
not retried. Failed attempts keep request URL hash, attempt number, observation
time, HTTP/error classification and available response length. Available HTTP
error bodies are stored before classification, including the first failure
before any explicit retry. Crossref 404 remains a retained lookup outcome.

The default urllib opener refuses every redirect. Known final response origins
are also checked against the requested HTTPS origin; credentials, unsupported
ports, fragments and non-GET requests are refused. Injected openers are an
explicit transport trust boundary; tests supply only fictional implementations.
They must not introduce their own hidden redirect/retry behavior.

Each response read is capped at 16,000,001 bytes. A response exceeding 16,000,000
bytes is rejected after retaining that bounded diagnostic prefix. Available
`IncompleteRead.partial` bytes are likewise retained and the capture fails.
Neither is represented as a complete source response. Successful captures bind
the complete bytes returned within the limit, not original transport framing.

## Completeness, identity and values

Inputs are bounded to 1–50,000 exact IDs. NCT IDs use ASCII digits and sort into
an exact unique scope. DOI scope preserves supplied order/spelling and refuses
case-insensitive duplicates; DOI source keys retain their existing lowercase
projection. DataCite escapes quote/backslash characters inside the exact related
identifier query rather than silently changing the DOI or broadening the query.

ClinicalTrials validates requested/returned identity and projected field types,
preserves full titles and structured date precision, and emits only source-owned
register fields. Operator-maintained values remain outside that projection.
Crossref checks its registered DOI/status and title array; update notices,
relations and assertions remain source metadata. A 404 or empty notice field
does not prove the absence of publication concerns.

DataCite requires exact integer page/count metadata, 25 rows per page, at most
2,500 returned records/100 pages, exact expected row counts, stable declared
totals, nonduplicated IDs within/across pages and record DOI/ID equality.
Only records containing the exact related publication DOI enter its derived
projection. Nonmatching search results and all unknown fields remain in raw
pages. Resource types, versions and relationship types are preserved; no dataset,
software or conceptual-output classification is invented. This is complete
single-query coverage, not two-pass temporal snapshot stability.

Strict JSON rejects duplicate keys, nonfinite constants and numeric overflow.
Raw response bytes are privately written and read back before interpretation;
malformed/identity-conflicting records remain retained without successful commit.
Before finalization every raw file is rechecked against its exact hash/length,
and uninventoried files are refused. Original source values/unknown fields remain
in the raw artifacts; projections do not reconstruct previously lost evidence.

## Storage, failure and fresh-folder recovery

All outputs must remain below this checkout's ignored `private/ops`. Capture
folders are created exclusively with mode 0700; files use exclusive/no-follow
creation with mode 0600, fsync, exact byte readback and directory fsync.
Projection and final manifest are both serialized with finite JSON before
either final artifact is opened. The manifest is committed last. Local manifests
explicitly carry `accepted=false`; completion is not native admission.

Failures, including storage/finalization failures, produce a create-only,
fsynced/read-back `failed-generation.json` when storage permits. It records
`complete=false`, `accepted=false`, exact scope hash, completed prefix, failed ID,
attempts, source inventory and hashes/lengths of every observed partial artifact.
An existing failure marker invalidates completion even if a final manifest was
already written before its verification failed. Consumers must enforce that
rule; checking `manifest.complete` alone is insufficient. Catastrophic failure
of the receipt storage itself is raised, never reported as durable acceptance.

Resume validates the exact source/scope/hash, integer counts, consecutive completed
prefix, file names/request identities, status/attempt types and complete saved-byte
inventory before creating output. Symlinks, tampering, extra files and changed
scope fail closed. A historical v1 receipt without `observed_files` is accepted
only when its exact declared raw inventory accounts for the whole failed folder;
it gains no retrospective evidence. Existing private evidence is never rewritten.

Recovery always creates a fresh private folder outside the input folder, preserving
the input bytes. ClinicalTrials/Crossref reuse only complete re-projectable IDs.
DataCite revalidates and reuses only complete earlier DOI queries; the interrupted
query restarts at page one. Failed pages/error bodies remain bound in the original
receipt; no interrupted offset is spliced into a later response set. New failures
retain the prior receipt hash/lineage. Finalization-only failure can reuse the
entire verified prefix in a fresh folder without provider calls.

These are tightened local contracts: callers relying on public output locations,
implicit retries, redirects, permissive JSON/numeric metadata or incomplete
inventories must migrate explicitly. Native manifest formats and consumers are
not automatically compatible or migrated by this packet.

## Evidence and retained limits

Explicit repo-local interpreter: Python **3.15.1**. Five focused stdlib suites
pass **39 tests** under `-S`: receipt 8, retry 7, ClinicalTrials 9, Crossref 6,
DataCite 9. Ruff and formatting checks pass. Direct provider CLI `--help` entry
points run outside the repository with `PYTHONPATH` absent and `-S -B`; their
helper imports need no site packages. Every positive capture/resume/transport
test injects fictional responses or patches the opener; no provider request,
accepted-history resume or source acquisition occurred. Tests cover error/partial
bytes, retry budgets/first failure, redirect refusal, raw hashes, strict types,
identity/paging drift, serialization/storage failures, create-only private output,
commit-last failure markers and unchanged resume inputs. These are local tests,
not native flow execution or runtime/operational proof.

Retained receipt scopes remain separate: ClinicalTrials' release-pinned discovery
continuation and independently hashed terminal artifacts do not certify all-page
independent downloads or the later saved recovery runtime. DataCite's accepted
prefix recovery used zero-row queries; positive-row native recovery remains
separate. Crossref's accepted combined dated coverage is not a fresh complete
sweep or natural scheduled-run proof; the user closed further follow-up.
No accepted receipt is rerun, promoted or reinterpreted here.

Remaining admission depends on the assigned owner's exact current native
definition/binding, authorised source scope, complete immutable native archive
and projection/readback, compatible receipt/consumer validation, protected
conditional register writes, replay/rollback and downstream field/key parity.
Schedules, sends, activation, authentication renewal and operational recurrence
retain their existing explicit authority. Native/provider/authentication scope
for this packet is **none**.

## Bounded parent-review correction

Successful-shaped payloads no longer override contradictory governing fields.
The three providers reject root `error`, `errors` or `failure` members; partial,
truncated, incomplete and failed flags must be literal false when present, while
complete/success flags must be literal true. Known failure/partial status strings
are refused. These checks apply at the governing root only: ordinary nested
source metadata with the same names remains untouched. Raw bytes are already
retained before refusal, and no success manifest is committed. DataCite also
rejects a non-null `links.next` on its declared terminal page, including a zero-row
terminal result; absent/null next links remain compatible.

Failure receipt raw/observed inventories now validate against one cached immutable
byte buffer per file. Overlapping length/hash assertions must agree, both are
checked against that same buffer, and the exact verified bytes are returned for
projection. The receipt itself is read once too. Synthetic read-count/mutable
second-read and conflicting-inventory tests qualify this frozen-buffer boundary;
it does not assert that a mutable filesystem path cannot later change.

ClinicalTrials separates its bounded `Title` display fallback from
`FullStudyTitle`. Missing/null source titles remain null in FullStudyTitle and
empty source titles remain empty; the NCT ID may fill the display field only.
Display truncation is explicitly limited to 255 UTF-16 code units without
splitting supplementary characters, while FullStudyTitle retains the complete
source text. This is a pure source proposal and supplies no native field-size,
schema-save or rendering acceptance.

The correction stays within the same eleven-path assignment on the existing
branch, directly after `1b2163eb98f8cc8f62ab90d17b189f4f42f64379`. Unchanged retry
tests are reused; the four affected suites are rerun. No canonical helper,
dependency, provider, authentication, native object or accepted history changed.
