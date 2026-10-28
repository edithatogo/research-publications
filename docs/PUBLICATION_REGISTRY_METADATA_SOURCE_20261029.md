# Publication registry metadata helpers: offline source closure

This packet starts at PR65 main `d6ede523966e8e83e01c9085c6db8238bed0d710`.
The sole source writer is chat `01a1831e-cc6d-7371-9d57-021a339b708a` in
`/Users/doughnut/.codex/worktrees/ef45/chhhs-research-publications`, branch
`codex/rims-grants-roadmap`. The integrator retains shared contracts, runtime,
dependencies and handoffs. The original authoring checkout, private bindings,
mutation journals, authentication and native operations remain with their owners.

The five helpers below are rewritten offline interfaces, not drop-in native
migration commands. They accept supplied evidence and produce proposals or compare
supplied readbacks. Every plan/result retains `native_acceptance=false`,
`native_schema_qualified=false` and `write_authorized=false`. A successful local
comparison verifies consistency of the supplied evidence only. It cannot establish
its authenticity, permissions, native execution, rendering, current-source truth,
performance, approval, delivery or operational acceptance.

| Source | Supported behavior |
|---|---|
| `scripts/prepare_publication_registry_bootstrap.py` | Strict complete snapshot validation; existing plain Note/full-title qualification; detached plan/preimage/target hashes; scoped field/XML/ETag comparison; complete query evidence comparison; private exclusive CLI envelopes |
| `scripts/prepare_publication_field_help.py` | Description-only proposals for exact existing fields, separately pinned profile/writer semantics qualification, bounded UTF-16 descriptions, preservation reconciliation |
| `scripts/prepare_publication_indexes.py` | Same-field index-only proposals within an explicitly supplied budget, collision/placeholder diagnostics, deterministic literal-escaped probes, supplied readback comparison |
| `scripts/prepare_publication_views.py` | Explicit existing/new view bindings, previous complete Brisbane month fixed at supplied as-of, preserved existing columns/formatting, exact membership/query reconciliation |
| `scripts/prepare_publication_quality.py` | Revision-bound supplied comparison artifacts, raw JSON and formula-safe CSV, exact proposed new quality view, supplied file/view/query receipt comparison |

## Inputs and preservation

Snapshots require `complete=true`, no error/partial/continuation indicators,
`capture_reference`, known UTC `observedAtUTC`, exact `site_url`/`list_id`, list
metadata including its ETag and `ItemCount`, and exact `counts.items`,
`counts.fields`, `counts.views`. Arrays contain unique identities. Items have
positive integer `Id`, explicit values for every supplied field (missing values
are not inferred as null), matching optional `ID`, saved ETag and explicit
`OData__UIVersionString`. Fields carry canonical GUID, internal/display/type
identity, explicit constraint/writability flags, complete schema XML and ETag.
Views carry canonical GUID, explicit privacy/default/hidden/paging flags, HTML
kind, positive row limit, XML query, ETag and resolved existing columns at
`resolvedFields.Items.results`. Fixtures demonstrate the complete shape.

Retain full supplied rows, version/history payloads, field properties/XML and
view properties. Comparisons index by exact ID and preserve values and JSON
types; they do not erase `__metadata`, human edits or allegedly volatile fields.
For selected field edits only the requested Description/Indexed property, its
matching XML attribute, same-or-next XML Version, saved ETag and explicitly
supported index-status transition may differ. Other metadata must match. For
selected existing views only the proposed properties and saved ETag may differ;
columns, formatter, XML and other properties remain exact. New views require
explicit new distinct IDs in supplied receipts. Missing/extra identities fail.

Existing Note qualification requires writable, unsealed Note with explicitly
false RichText/AppendOnly. `SourceFullTitle` must already exist with matching
name/title, no required/indexed/unique constraint and that plain Note profile.
Missing/converted fields are a separate schema migration requirement. Helpers do
not create them or infer capacity from a configuration label.

The parent-owned [meanings profile](PUBLICATION_FIELD_MEANINGS_PROFILE_20261029.md)
remains unchanged. It is a historical description proposal. Field-help callers
must supply `field_semantics_confirmed=true`, exact `profile_sha256` and
`preimage_sha256`, a `reference` and a `writer_semantics_reference`. Those are
supplied qualification assertions, not independent verification. Existing native
types, Note behavior, full-title behavior and timestamp writer meanings still need
exact native/writer evidence. Type mismatches fail rather than silently changing
Choice/Text or migrating columns.

Index budgets are supplied, not assumed to be tenant limits. Required/Unique
constraints are never relaxed or introduced. Exact and casefold collisions and
blank SourceKeys are diagnostics; uniqueness and performance remain unproved.
No positive PMID sample or configured period produces an explicit probe gap,
not a fabricated sample or a failed implicit lookup. Query results require
complete count-bound arrays pinned to target, plan, capture and postimage time,
with exact IDs and SourceKeys. No query is executed by these scripts.

View roles `publications`, `month`, `uncertainty`, `placeholders` require complete
bindings: exact GUID or null for a proposed new view. Default, personal and hidden
views are protected. Desired titles are compared with casefolding against every
other view identity. New bindings cannot recreate an existing desired title;
existing bindings cannot rename over another identity. Previously created views
require explicit receipt-ID handover rather than implicit title adoption. Period
bounds use an aware as-of converted to Brisbane;
no automatic rollover is installed. Keyed nonExcluded rows are register cohorts,
not accepted canonical totals. Unknown months remain unknown, placeholders remain
retained, and no publication date is invented. Supplied native query results must
confirm the selected cohorts, including blank/null behavior.

## Quality artifacts and receipts

Disposition and case packets require complete indicators, matching
`registry_sha256` and `source_revision`. Disposition includes `rule_version` and
exact `{id,field,registry,canonical}` entries. Case packet includes a source SHA256,
exact case/difference counts and one exact `registry:<positive ID>` /
`canonical-for:<same ID>` pair per case. Both SourceKeys must match the current
row; every supplied difference must match retained and source values exactly.
A retained record may be a pointer with no `values` member. If `values` is
supplied it must be an object using only the nine supported logical metadata
fields in `FIELDS`; every supplied value, including fields outside the disputed
set, must match its exact current registry value and JSON type. Native field
aliases, context labels and other unsupported fields fail rather than being
discarded. Absence of `values` does not assert a retained value snapshot.
Duplicate, stale, uncovered, malformed and mixed-generation pairs fail. The source
hash binds a supplied source assertion; this helper does not fetch or hash an
external source. Cases and differences cover the complete supplied historical set,
not a fresh complete acquisition audit.

JSON preserves literal values and provenance; CSV prefixes spreadsheet formulas
and retains the JSON counterpart. Counts are computed from inputs with no fixed
cohort total or truncation. All keyed unknown months, including Excluded, are
reported separately from the nonExcluded reader uncertainty denominator.

`prepare` returns data, an in-memory filename-to-bytes payload map and a plan.
The CLI stores them in one new private envelope using `local_payloads_utf8`;
UTF-8 re-encoding reproduces the JSON/CSV bytes, including the CSV BOM. The
manifest binds the two data files; the plan binds those files and the manifest.
No artifact is uploaded. The required folder is an explicit unencoded
site-relative path; traversal, encoded separators, query/fragment and host changes
fail. Proposed links are not made or verified, and `link_existence_verified`
remains false. The existing uncertainty view must be bound by ID and already
have the qualified query. Existing quality titles fail preparation to prevent
replay through duplicate creation. Empty differences use a false positive-ID
predicate rather than an empty CAML In.

Quality receipt reconciliation requires complete target/plan/capture/time-bound
file evidence, `created_views={quality: <new GUID>}` and exact file records
`{name,unique_id,etag,status,bytes,sha256,server_relative_url}`. Each unique file
identity, nonwildcard ETag, HTTP 200 integer status, byte count, hash and planned
location must match. Query evidence includes `differenceRows` and
`uncertaintyRows`; rows also preserve `field_6` and `field_8` values. Existing
rows, fields and views remain unchanged. Receipt claims alone are not native or
link-access proof.

## Local CLI use

Use the existing explicitly selected repository Python 3.15.1 interpreter.
Every input/output is under the same repository `private/` with an existing
parent and no symlink redirection; the immutable tracked meanings profile is the
sole default config read. Outputs are exclusive atomic envelopes, never replaced.
Input byte hashes come from the same read that supplies strict JSON decoding;
duplicate keys and nonfinite numbers fail. Canonical object hashes are separately
labelled in plans. Before/after comparisons require an independently retained
`--expected-plan-sha256`; editing and rehashing a plan does not qualify it.
A plan rebound to a different preimage fails. Repeated offline comparison is
read-only; no native replay capability is provided.

Entry points expose `--help`. Snapshot validation uses `--snapshot --output`.
Description preparation adds `--qualification` and optional `--meanings`.
Index preparation adds `--index-budget` and optional two-bound `--period`.
Views add `--bindings --as-of`. Quality adds `--disposition --cases --folder
--uncertainty-view-id`. Optional `--after --plan --expected-plan-sha256` switches
to comparison with the corresponding required query/created/file receipts; partial
comparison arguments fail. Quality consumes its full preparation envelope, with
its plan inside `result.plan`; other helpers store the plan directly in `result`.

## Historical exclusions and remaining native dependencies

The nine retained source/test files were assessed; five helpers and five stdlib
synthetic test files are now supplied in this bounded packet. The new field-help
tests close its previously absent paired-test coverage. This is an amended
source port; it is not an unchanged import or a claim that every historical case
or native operation is now qualified.

The historical bootstrap `qualify`, `prepare`, `check_packet`, `preflight`,
`verify`, `rollback`, `prepare_full_title`, `verify_full_title`, `command`,
`_bootstrap_shell_header`, `full_title_packet_files`, `packet_files` and
`CliCapture` are intentionally excluded. Their schema conversion/creation,
command generation, live capture and rollback capabilities need a separately
owned approved native mutation packet, exact preimages, operation-specific
permission, ETag guards, recovery and readback. Historical `bare` and
`persistent_view` normalization are excluded because they discard metadata.
Historical wrappers `validate_target`, `unwrap`, `value_rows`, `write_json` and
`view_guard` are replaced by the strict supplied-profile, preservation and
exclusive-output interfaces above. Historical SHA/canonical helpers are replaced
by the existing qualified strict JSON implementation.

No bare m365, CliCapture, process/service calls, migration/rollback shell, JS
adapter, schema edits, authentication, writes to native objects, uploads,
activation, scheduled execution or sends are included. There is no SharePoint
structured-document requirement for these machine-readable comparison artifacts;
Word/template generation and substantive review remain outside this slice.
Native schema/type/full-title/writer qualification, current complete capture,
actual index/query behavior, mutation recovery, list rendering, file persistence
and reader access remain separate owner-operated gates. Local source tests cannot
close any of them.

## Verification

The existing `.venv/bin/python` reports Python 3.15.1. Focused stdlib tests run
with site packages disabled:

```text
.venv/bin/python -S -m unittest \
  tests.test_prepare_publication_registry_bootstrap \
  tests.test_prepare_publication_field_help \
  tests.test_prepare_publication_indexes \
  tests.test_prepare_publication_views \
  tests.test_prepare_publication_quality -q
```

The original packet passed 39 tests, including exact preservation, plan
tampering, malformed and
partial inputs, explicit policy qualification, cohorts of 201 comparisons,
empty differences, receipt substitution and local CLI round trips/exclusive
outputs. The review follow-up passed all 20 affected view/quality tests on the
same Python 3.15.1 interpreter, including four new regressions for replay after
creation, unrelated title collisions, contradictory retained values and
unsupported/malformed retained-value objects. These are synthetic fixtures.
Unchanged tests reuse the original receipt; broad harness/native checks were not
repeated. The integrator retains the integration/release gates.
