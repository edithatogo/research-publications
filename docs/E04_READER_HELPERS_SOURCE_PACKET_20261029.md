# E04 retained reader-helper source packet — 29 October 2026

This packet qualifies three reader-only helpers and their exact source dependency.
It supersedes the three retained-only dispositions in the
[finite register](E04_T18_READER_SOURCE_DISPOSITIONS_20261029.md) at this bounded
scope. No model/DAX contract, source record, review state, runtime, shared handoff,
track, native target or browser state is changed. E04 native writes remain stopped
at the [import/recovery blocker](E04_T18_SOURCE_PACKET_20261029.md). T18 current-target
identification remains unresolved; no substitute report is proposed.

## Provenance and dependencies

The helpers were amended from the preserved authoring checkout, not imported as
private operational history. Project Apache-2.0 notices remain. The retained
source hashes below identify the starting implementations; full new hashes are
in the private `retained-source-provenance.json` receipt.

| Retained source | Original SHA256 |
| --- | --- |
| `prepare_dashboard_funding_layout.py` | `ceb89f9fc89a9d7920b3cdaab5cf6d215148c97141255e0c93e47b845cee5ddb` |
| `prepare_dashboard_relationship_summary.py` | `3c18e4294291da5b35a713140b41d28cbb0f505a5e9a3a3648b6afdb75ac9108` |
| `prepare_dashboard_source_freshness.py` | `00755b61c7bb684a917cfd7b376cefcbf13b19f20a78d10fdff8b04a900931e6` |

All three use the new reader-owned `scripts/dashboard_reader_source.py` for
immutable report capture, exact frozen model metadata extraction, field/type
checks, new visual/page construction and exclusive candidate/manifest output.
Its only repository dependency is maintained `scripts/prepare_dashboard_overview.py`
for `literal` and direct-field `projection`. No legacy-format generator, historical
ResearchDatasetConsumers page, overview-confirmed visual or relationship-summary
page is required as an implicit template/dependency. Existing report pages supply
only their schema declarations for new objects; their filters and query state are
not cloned into new objects.

Each entry point requires the complete report bundle digest, complete model bytes
and expected model SHA256. Model extraction requires unique safe InlineBase64
parts, the model root, exactly61 parts and53 distinct table identities, and
rejects duplicate field declarations. It extracts field existence/type without
executing DAX, M, processing or data queries. Those checks do not certify row
completeness, uniqueness, review or admission. Current qualification uses the same
frozen model capture from the terminal read-only preflight and the prior source-only
clearance candidate; neither input changes. It is not a fresh native baseline.

Use the explicit repo-local Python3.15.1 interpreter with `-m`:
`-m scripts.prepare_dashboard_funding_layout`,
`-m scripts.prepare_dashboard_relationship_summary`, or
`-m scripts.prepare_dashboard_source_freshness`.
Each accepts positional source/output directories and required `--expected-sha`,
`--model` and `--expected-model-sha`. Use the frozen receipt's exact digest, not
an arbitrary replacement capture. Relationships optionally accepts a complete
`--links` JSON object and explicit `--allowed-host` values; omission creates
visible unavailable-link text and no action buttons. No entry point offers a
native save, data acquisition, authentication or model-update operation.

## Qualified source behavior

**Funding.** Existing opportunity, calendar and watchlist page/visual identities,
all original projections, filters, sort definitions, rich text and protected
fields survive. OpportunityKey, DeadlineKey and watchlist OpportunityKey/Scope/
TargetKey consumers must be present and match the frozen model; incomplete,
duplicate or aliased bindings fail before output. The original opportunity table
retains its fields and x/width/z/tab order; only y/height are reserved for detail.
Two page heights grow without shrinking their canvas or replacing page properties.
Three new visuals add source/context limits and a detail table with explicit
OpportunityKey, Title, Funder, Eligibility, Description, Geography, ReviewStatus,
DeadlinePrecision and URL. No columns are removed from existing tables. Blank
precision/deadlines, empty scopes, source terms and unqualified selection/detail
interactions are explained, not adjudicated. No opportunity is admitted or linked
to an award/publication by this helper.

**Relationships.** A new ResearchRelationships page consumes the existing governed
Candidate links, Confirmed reviewed links, Unclassified or unresolved links and
Current relationship rows measures. It requires explicit relationship/type/from/
to/evidence/confidence/review/typed-admission fields, canonical publication and
award keys, and the existing identity-match/typed-binding/native-key counters.
No fallback count replaces a missing measure or incomplete typed consumer contract.
Those metadata dependencies do not independently approve records; existing model
rules and human review remain authoritative. Publication author/facility-match
patterns use the existing Publications measure and retain their source meaning.
Source activity keys count nonblank key rows, not unique projects or people; a
missing activity-key field becomes visibly unavailable. Missing links are visible
unavailability, not guessed URLs. Supplied links require exactly three keys and
HTTPS view URLs within an explicit exact SharePoint host allowlist; existence and
access still require separate acceptance. No name match, author/facility/project
identity inference, funded-publication inference, combined research total or
monetary sum is introduced.

**Source timestamp evidence.** Observation, acquisition, processing, publication
and provider modification have distinct visible meanings. Each dated scalar is a
maximum over a qualified dateTime column only, with the correct Max query reference
and aggregation function. Blank cards mean unavailable in the selected scope;
no string maximum, text-date parsing, timezone conversion, missing-as-zero or
cross-provider timestamp substitution occurs. ReportingWindow.RefreshedAtUTC is
labelled query materialization context, never whole-model/per-source processing
success, recurrence or delivery. Publication dates remain separate record events
and are not used as freshness dates. No processing-success receipt is consumed.

## Frozen-contract gaps and local evidence

Funding and relationship required bindings all resolve in the frozen capture.
Four timestamp cards have qualified dateTime dependencies: FreshSearchAudit.
RefreshedAtUTC (PubMed search observation), DORA Activity Registry.DORAObservedUTC
(activity source observation, with acquisition independently unavailable),
OpenAlexWorks.OpenAlexObservedUTC (imported-work observation),
and ReportingWindow.RefreshedAtUTC (materialization context).

Three additional fields exist as **string**, so their chronological scalar
consumers remain unavailable: ARCAwardContext.RetrievedUTC, Study register.
SourceObservedUTC and DORA Activity Registry.DORAResourceLastModified. Any typed
projection/conversion belongs to the model/source owner and requires its own
qualification; these helpers do not change those types. Seven other source rows
have no qualified scalar at all: DORA publications, NHMRC awards, MRFF awards,
ROR, Crossref, ARDC and DataCite. Each is visibly unavailable with a concrete
receipt dependency. Provider-update scalars for other sources, per-source processing
completion and publication-date freshness scalars are not claimed. Record-level
structured LastUpdateSource remains unparsed evidence.

Sixteen focused fictional tests pass on the explicitly selected repo-local
Python3.15.1 interpreter:
`-m unittest tests.test_dashboard_reader_helpers`.
They exercise full/partial/duplicate/model-identity/hash guards; quoted/commented
TMDL fields; exact existing bytes and protected queries/filters; missing typed
keys, evidence, review, governed measures and watchlist scope; pre-output geometry
collision; exclusive output/receipt/source guards; unavailable optional consumers;
exact link keys/hosts; timestamp kinds, string/absent-date suppression, correct
Max references, refusal to replace an existing appended page and composed-increment
preservation of prior reader parts. Fixtures contain
no native records or invented outcomes. Ordinary hooks remain enabled.

Local normal CLI0.5.0 validation of all three independently prepared candidates
reports zero errors and the same two PBIR_SCHEMA_UNREACHABLE warnings each. Only
public schema retrieval is involved in that validation, with no Fabric/Power BI
workload call, authentication, upload or native effect. Missing exact report3.4.0
and visualContainer2.14.0 schema coverage remains explicit. Those results cannot
overturn the native linguisticSchemaSyncVersion import blocker.

| Candidate, independently based on the same75-part local input | Existing changed parts | Added parts | Unavailable dependencies |
| --- | ---: | ---: | ---: |
| Funding | 3: two page heights and opportunity-table position only | 3 | 0 |
| Relationships | 1: page order only | 15 | 0 with the current activity key; three unsupplied view links visibly unavailable |
| Timestamp evidence | 1: page order only | 32 | 10: seven absent scalars and three string-typed fields |

Every other original part is byte-exact. Independent scope comparisons and full
hash manifests are private under `private/ops/e04-reader-helper-source-20261029/`,
including frozen-source qualification, retained-source provenance, candidate
manifests, per-candidate normal CLI validation and focused test result receipts. No pack,
mutation, data query, new screenshot, baseline rebuild or repeated frozen
source/detail/plot parity run occurs.

## Residual acceptance

Authoritative exact-version import semantics and bounded recovery remain the first
native gate. Any future reader save needs new exact ownership/scope, fresh complete
preimage/drift guards, saved definition/binding readback and exercised scoped
recovery. Local structural/geometry/type checks are not rendering or operational
acceptance. All new reader pages/details require actual light/dark viewport/zoom,
long-label/wrapping/scroll, keyboard/focus, blank/no-result and table-selection/
filter/detail checks; source links need actual access/existence checks. No native
interaction/filter or typed-row acceptance is inferred from the local candidates.
T18 still requires current-target identification before its separate preserved
reader/performance/report-restore gates can resume. Canonical metric denominators,
taxonomy/provider-ID criteria, five forecast origins per horizon and suppression
rules remain unchanged; no data, forecast, model or outcome acceptance is added.

Final event-meaning correction: the frozen DORA Activity Registry partition
requires an explicit UTC source observation timestamp. It does not independently
establish acquisition time. The final timestamp candidate is
`freshness-observation.Report`; its earlier local candidate is preserved as history.
The changed event-meaning test passed again; unchanged test/validation evidence
for the other helpers is reused. No model value or type is changed.
