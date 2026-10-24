# DoRA retrieval and native documentation — 24 October 2026

## Documentation completed

The saved PubMed57-action and DoRA108-action response-copy changes were published
as17stable-ID SharePoint updates. Saved bytes and prior versions passed. Guide18,
catalogue19 and43reopened native Loop sources retained existing identities and
unselected content; both updated sources and58/109preview elements reconciled.
Later DoRA hardening has its own versioned successor described below. Historical
snapshots remain history, not proof of the current graph or runtime performance.

## Measured retrieval constraints

The accepted DoRA baseline has709records. Its record loop took80.03minutes inside
an89.77-minute generation; the preceding generation took177.91minutes. The old
five-second per-record delay alone represents59.08minutes at that record count.

Three accepted records expose Last-Modified but no ETag. Normal and matching/older
If-Modified-Since requests all returned200 and complete HTML: nine record requests
provided no conditional-download saving. The two standard public OAI/REST routes
checked returned404; other possible interfaces remain unqualified.

The provider's published robots policy specifies Crawl-delay:10. A temporary
two-second candidate was corrected before any native collection ran. The current
saved graph uses10seconds and serial concurrency one. Faster crawling is not the
selected optimisation.709records require118.17minutes of programmed spacing alone,
so a one-hour daily full-HTML sweep cannot meet this provider policy.

## Saved hardening and the next optimisation

The110-action graph has a fresh Boolean provider-failure latch. The existing handle
guard checks it before delay/request; a failed or timed-out HTTP action sets it,
preventing further provider requests in that generation. This includes429 reported
as a failed HTTP action. Existing failure receipts/last-good preservation remain;
there are no new retries or concurrent requests. Failure-latch runtime proof is
pending; structural tests and exact native save/readback are separate evidence.

Flow identity, physical connection, Started, daily04:30Brisbane, concurrency one,
source scope, provider URL, raw HTML serialization/readback, own-DOI extraction
and manifest/checkpoint guards are preserved. No additional full collection was
invoked. The next natural occurrence supplies performance/integrity evidence.

The published sitemap is available:35,073URLs/4,453,597bytes, containing all709
accepted publication handles. This provides a candidate bulk version inventory.
Three sampled sitemap timestamps differ from HTTP Last-Modified by10or11hours;
they remain opaque tokens, not certified UTC dates or acquisition cutoffs.

`scripts/dora_change_inventory.py` maps the complete required handle set, exposes
gaps, rejects duplicate selected handles/entities and preserves exact version
tokens. Its local selector defaults to fetching rather than reusing. Reuse needs
independent qualification of source version-change semantics plus the original raw
file ID, ETag, length, hash and provenance. It is not deployed in the native flow.
No unchanged URL, elapsed cache age or stable timestamp alone establishes freshness.

Remaining implementation is to qualify version changes/index freshness, bootstrap
verified raw references and migrate the producer/consumers together, retaining
complete membership checks and periodic full reconciliation. Do not carry all
35,073sitemap rows through per-record flow history. If that reduced workload still
exceeds capacity, retain the measured deficit for a separate bulk-worker decision.

Private receipts: `private/ops/2026-10-24-ingestion-documentation/` and
`private/ops/2026-10-24-dora-retrieval/` in the primary checkout. Crossref's retained
run, archives, monitor and terminal-gated19-query deployment remain separate.

## Qualification continuation — 24 October 2026

Fresh full PAC clientdata and independent Flow API definition/reference readbacks
match the accepted PubMed57 and DoRA110 graphs. Both remain Started with their
original daily schedules and concurrency one. Neither has executed since these
changes: the next natural occurrences are25October01:30Brisbane for PubMed and
04:30 for DoRA. Older successful runs cannot accept the changed implementation.
No collection was invoked and no native definition, schedule or connection changed
during this continuation. Accepted guide20/catalogue21/Loop82 documentation is
reused; the saved graph has no further documentation delta.

A second complete sitemap-index/page capture and one accepted detail capture used
three serial HTTP200 requests, separated by10.013/10.005seconds after the preceding
response. Decoded bodies total4,494,698bytes; Content-Length headers total241,946
compressed body bytes, excluding HTTP/TLS overhead. The sole page contains all709
required handles and is byte-identical to the earlier capture. None of their opaque
tokens changed. Sample11319's40,847-byte HTML, metadata table and Last-Modified
header also match. This is an unchanged observation, not changed-record detection
proof. No conditional download or retrieval saving occurred.

The sitemap HTTP Last-Modified is24October05:00:50GMT. Its independently observed
freshness is not a site-specific maximum indexing lag, transaction boundary or
guarantee that changes after generation appear before collection. No changed-record
transition or DoRA deployment/configuration contract was established. Consequently
**sitemap-based native skipping does not qualify** with the available evidence.
This does not prove that a future supported change-feed contract is impossible.

Upstream [DSpace6 generation source](https://github.com/DSpace/DSpace/blob/dspace-6_x/dspace-api/src/main/java/org/dspace/app/sitemap/GenerateSitemaps.java)
passes item last-modified values to a separately generated sitemap. Its
[formatter](https://github.com/DSpace/DSpace/blob/dspace-6_x/dspace-api/src/main/java/org/dspace/app/sitemap/SitemapsOrgGenerator.java)
uses a literal Z without explicitly selecting a timezone. This is a possible
explanation for the offset, not proof of DoRA's installed version, configuration,
freshness or change semantics. Continue comparing exact opaque tokens; never
derive verified UTC timestamps or acquisition cutoffs from them.

The local selector now additionally requires an explicit independently qualified
maximum response age and an aware current time. Missing/invalid/naive/future/stale
response observations fetch again; an archive recheck cannot reset response age.
The sitemap token is never parsed as a date. This is local defensive preparation,
not a chosen freshness allowance, independent archive proof, cross-folder native
consumer support or a deployed reuse path. Seven focused tests pass.

## Supported fallback and remaining acceptance

Keep the currently saved complete before/after membership scans, full detail GETs,
exact raw save/readback, manifest reconciliation and commit-last/last-good guards.
Keep10second serial pacing, no HTTP retries and the failure latch. This is the
simplest qualified fallback; it yields zero provider-request or byte savings from
sitemap/conditional retrieval. At709records it still needs at least7,090seconds
(118.17minutes) of programmed record spacing, plus discovery/provider/storage work.
No shorter cadence, reduced coverage, extra worker/runtime or schedule change has
been deployed or qualified. Capacity for a one-hour full sweep remains insufficient.

Reference reuse stays disabled until an independently evidenced change/freshness
contract and response-age bound exist, and actual consumers resolve immutable
earlier-folder files with exact native identity/version, length, hash, response
version, source relationships and coverage. Freshness qualification cannot be
replaced by a Boolean configuration flag or repeated unchanged samples.

Inspect each next natural occurrence without invoking another generation. Follow
every relevant action/repetition/file-inventory page. Confirm the actual executed
graph omits the removed aliases; for DoRA check10second inputs and the failure
latch's branch. Reconcile complete before/after keys, all batch/record summaries,
raw save/readback guards, manifest/checkpoint bytes, previous-checkpoint lineage
and last-good. Measure provider calls, response bytes, executed actions and duration
from that occurrence. Success can accept only the successful branch; retain the
latch's native failure branch as unproved until the smallest bounded native case
or a natural failure establishes stopping and checkpoint preservation. Reuse
accepted replay/restart evidence where its graph and archive inputs are unchanged.

Current receipts, raw observations, native readbacks and the next-run checklist are
in `private/ops/2026-10-24-pubmed-dora-completion/` in the primary checkout.
Runtime acceptance and E01 completion remain open. Crossref and its three-hour
monitor retain their existing owner and operation.
