# NIH RePORTER publication-reference source consumer

The integrator owns the new `prepare_nih_publication_relationships.py`, its
paired test and this leaf, independently of the three delivery lanes. Base is
verified PR69 main `30bd1e9fd9559ac277089ffeef91ec41d9095134`. There are no imports
from a retained original implementation and no changes to the NIH opportunities,
observer, worker, schedules, authentication or journals.

## Provider evidence

The [official API documentation](https://api.reporter.nih.gov/) documents a
publication search by PMID, application ID or core project number. Its publication
pagination has a maximum offset of9,999 and limit of500; the default is50. It
requests at most one request per second. RePORTER covers both NIH and non-NIH
agency awards, so a returned project reference is not sufficient to label an
institutional NIH award. The [published OpenAPI document](https://api.reporter.nih.gov/swagger/v2/swagger.json)
also contains camel-case schema properties alongside snake-case examples; these
are retained as a documentation difference, not silently treated as interchangeable.

On29October Brisbane, one POST search using one PMID from the official public
example, offset0/limit1, returned HTTP200. Its observed envelope was
`meta/results/facet_results`; records used `coreproject`, integer `pmid` and
integer `applid`. Total4 with one returned row proves only a bounded sample,
not complete acquisition. No repository publication identifiers were submitted.
Exact documentation, request/response bytes, hashes and observation time remain
under ignored `private/ops/2026-10-29-nih-publication-source/`.

## Implemented offline boundary

`project(pages, scope, publications, generation, *, expected_pages_sha256,
expected_scope_sha256, expected_generation_sha256)` is a pure supplied-input API.
It does not fetch, save, deploy, admit or mutate records. Pins bind the complete
typed inputs, including raw response buffers. They do not establish caller
authority, provenance authenticity or source-retention acceptance.

The explicit profile uses one PMID per query and the exact endpoint, POST body,
ascending core-project sort, offset and limit. Every page carries a unique leaf
name, raw bytes/length/hash, HTTP status and observed time or explicit unknown.
All queries must have complete contiguous coverage with stable totals and page
limits, exact row counts and no duplicate project identity. Partial/failure or
contradictory governing envelopes fail before any result. An omitted zero-result
query cannot be interpreted as zero. Totals over10,000 or unsupported identifier
and response shapes require a separately qualified profile; they are not truncated.

Source integer PMID and latest-application fields retain their raw representation.
The candidate's textual PMID follows the explicit positive-int32 response profile;
canonical PMID inputs must already be exact decimal text. Core-project spelling
is preserved. A latest application may be explicitly unknown null, but cannot
be reconstructed from a project number. Whole source records and occurrence
locations remain in the result, including unknown nested fields and literal text.

Canonical mappings are independently generation-bound. Missing/ambiguous matches
remain visible; publication totals never increase with reference counts. Candidate
keys distinguish RePORTER core projects from admitted awards. All mutation,
identity, funding-attribution and native-admission claims remain false/unknown.
A later latest-application value changes the revision while retaining the stable
reference key. There is no store, implicit withdrawal or replacement of human edits.

## Verification and remaining exits

Twelve focused fictional tests pass on repository-local Python3.15.1 with `-S`.
They cover two-page completeness, complete zero versus missing coverage, exact
identifiers, strict raw JSON/byte proofs, independent pins, ambiguous canonical
bindings, duplicate/drifting pages, candidate preservation and stable revisions.
Ruff and formatting checks pass. The public sample is not a fictional test or a
complete source acceptance receipt.

Remaining dependencies are a qualified complete retained source capture for the
selected repository PMID scope, temporal snapshot/reconciliation evidence,
source-qualified award/funder mappings, authorised review/persistence and native
bridge/reader cardinality and correction/withdrawal recovery. This module neither
replaces the existing opportunities collector nor qualifies scheduled operation.
