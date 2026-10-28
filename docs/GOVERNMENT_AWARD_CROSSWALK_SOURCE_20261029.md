# Historical government workbook crosswalk: source closure

29 October 2026. Base: `da27d986f81cfd853fd55db7120b2b505fa509de`, the exact
reviewed/local-merged dependency authorised for this lane pending the combined
hosted milestone. No prior commit or branch base was moved. This is source and
candidate-environment qualification, not verified-main, native or business
acceptance. Only this leaf, the helper and paired tests are changed.

## Original scope and source pins

The following retained originals were verified before copying; no original
source, workbook, native object, runtime or active service was changed:

| Original path | SHA-256 |
| --- | --- |
| scripts/government_award_crosswalks.py | 41f112da833d4b4a41dd088899e1bdd9c7c2af96ae3dc24b1dd86c3b9f0f05fc |
| tests/test_government_award_crosswalks.py | 15fa48f16e073a423da8360f8899c641b1a74b78f6acab155c3412241728fcb3 |

Both are amended here. The original eleven unittest methods remain, with fixtures
made explicit about new pins and extraction policy. Ten additional methods cover
the changed behavior. The helper still exposes no CLI, output writer, native
transport or provider adapter. Protocol/PDF and workbook-collection families are
not imported. It reuses already reviewed authority/governing-envelope, DOI,
strict JSON, typed fingerprint and count/query guards unchanged.

## Isolated environment qualification

The existing lane `.venv` was incomplete and remains untouched. Parent had
separately qualified the same package versions on Python3.15.1; no Python
incompatibility or new package version is inferred from the lane-local gap.
A new lane-owned environment was created at:

`private/ops/government-award-crosswalk-20261029/artifact-venv`

It uses the installed Python3.15.1 base and unchanged
`requirements-source-ingestion.txt` with `uv pip sync --require-hashes`.
The exact lock SHA-256 is
`1999cbcbb75e766d553f503791bf79641ce9636e98d0c303c0857752e6d60ac1`.
Actual imports report openpyxl3.1.5 and et_xmlfile2.0.0. A fictional in-memory
save/read preserved text `0123456` and an unknown cell. Actual runtime/import/
roundtrip evidence is retained in the ignored
`private/ops/government-award-crosswalk-20261029/environment-proof.json`.
No shared runtime/dependency promotion, original-environment repair or new
research-source/native authentication occurred.

## Independent retention and generation inputs

`project_packet` retains `trusted_upstream_sha256` and now additionally requires
an independently pinned outer manifest, authority binding, complete canonical
generation and extraction scope. Supplied pins bind bytes and scope, not their
authenticity, current reuse rights, human review or native permissions.

Both upstream routes remain explicit and independently pinned:

1. **Source-manifest route:** the selected original workbook entry already has
   SHA-256 and actual-integer length; the trusted pin must match that upstream
   manifest. Both must match the exact captured workbook bytes.
2. **Retention-receipt route:** both original hash/length fields are absent; the
   trusted pin must match the separate original-retention receipt. Its successful
   recorded status, exact run, original manifest hash/length, unique selected
   workbook and original-CLI-capture comparison must bind the same bytes.

A partial hash/length pair cannot silently switch routes. An unused alternate
receipt cannot be treated as implicit fallback. Recomputed outer hashes cannot
replace either independent upstream pin. These are retained historical receipt
checks, not a new native archive acceptance or recapture.

All manifest files are unique, contained regular files without symlinks. Strict
JSON, hash and byte checks use the same single read of every artifact. Exact
inventory/reference coverage, actual integer counts, error/partial/continuation
guards, independently bound ROR/FundRef namespace and exact official workbook
source URL are required. The generation binds full canonical input, counts,
manifest and source-batch identity. Query status/pagination, DOI/PMID text and
source/query identities are validated without trimming or prefix rewriting.
Unknown observation timestamps remain null.

## Complete workbook inspection and identity boundaries

`inspect_workbook` verifies ZIP integrity and unique members, exact unique sheet
and internal worksheet relationship, physical row/cell coordinates and the unique
APP ID header. It resets worksheet dimensions and reconciles all physical rows
in the selected scope, so a false declared dimension cannot truncate extraction.
The original whole workbook remains untouched, including other sheets, fields,
styles, unknowns and unlabelled columns; this is complete selected-sheet APP ID
inspection, not a flattened replacement for the original workbook.

The independently pinned scope contains the workbook hash, exact sheet/header
row/column identity and letter, numeric policy, data/identifier/diagnostic counts,
key-set digest and full extraction digest. Source descriptors retain cell
coordinate, Python value/type, cell type, number format, raw XML value and formula/
cached-value context. Duplicate identifiers anywhere in scope fail qualification,
even if no current Crossref query selects them. Duplicate headers, row/cell
coordinates, incomplete extraction and scope drift also fail explicitly.

Text identifiers retain exact spelling and leading zeros. Default inspection
rejects numeric identity; `positive_integer_decimal` is a separate, explicitly
pinned source policy. It accepts only positive integer numeric cells within the
exact numeric range and General/0 formatting, retaining raw type/value/format.
It does not convert floats, pad digits or reconstruct lost zeros. Unsupported
text/type/format, blank, formula and error cells remain visible diagnostics.
Formula caches are preserved as raw evidence but never evaluated or accepted
as identifiers. Dates or cached values cannot become source keys by conversion.
No field dictionary or numeric policy alone establishes a real grant identity.

## Candidate assertions and preservation

Exact Crossref funding-number matches point to historical APP ID cells and retain
workbook hash, sheet/column/row/cell, upstream route/pin, authority and source
provenance. Missing or prefix-mismatched keys produce explicit diagnostics rather
than positive edges. Repeated source mentions retain all occurrence paths without
multiplying a relationship. Source-version and projection-revision hashes retain
changed captures even if a batch label is reused. No disappearance authorizes
withdrawal or deletion; there is no store or upsert here.

Every row is candidate-only with false identity qualification, canonical
admission, mutation authority and native G06 admission. APP ID is an application-
keyed historical source identity, not the distinct Grant ID, an ARDC grant PURL,
current award status or the complete eligible application denominator. Announced
full-duration value is not expenditure or annual allocation. No amount, currency,
CHHHS participation, institutional attribution or funding contribution is inferred.
Existing human reviews/corrections and source objects are immutable inputs;
source-assertion `Not reviewed` must not overwrite human review fields. Distinct
canonical publication counts remain separate from bridge/occurrence row counts.
The unchanged G06 normalizer rejects direct admission of these extended rows.

## Focused evidence and residual gates

All21 focused unittest methods pass on the new Python3.15.1 environment, including
all11 retained methods and no skips/stubs. Tests use fictional workbooks only.
They cover both retention routes and tampering, formula cache/error/blank/style
and leading-zero behavior, complete extraction despite false dimensions,
unselected duplicate IDs, exact coordinates/counts, strict JSON/envelopes and
paths, independent pins, replay/revisions, immutable human/source inputs and
bridge/filter cardinality. Each artifact is verified as read once.

The suite also passes with `-B -S` and only the explicitly qualified candidate
site-packages directory added to that subprocess. This is not stdlib-only
workbook execution: the two locked packages are required. Package and direct-
module import closure are tested the same way. No broad harness, provider query,
real-workbook replay or native operation is represented by these results.

Native transformed-data reuse/access remains unresolved. Historical original-
binary retention does not settle derived-export permission. G06-H01 still needs
trusted real source/dictionary/authority/canonical associations. G06-H02 needs
exact native schema, scope, preimages, permissions, typed persistence/readback
and cardinality acceptance. G06-H03 needs authorised reviewed links, correction/
withdrawal history and recovery without changed publication totals. No shared
schema, dependency, runtime, Conductor record, model or report is changed.
