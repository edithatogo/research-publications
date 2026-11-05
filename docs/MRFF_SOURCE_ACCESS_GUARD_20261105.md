# MRFF workbook discovery and source access — 5 November 2026

The failed 2 November 06:00 Brisbane collection received an HTTP-200 browser
verification interstitial from the official source. Its saved response contains
the interstitial verification endpoint and challenge function, with no workbook
links. The existing coverage guard correctly prevented workbook and completion
writes, but reported the generic `QGIP_SOURCE_GUARD_FAILED` expression error.
This was blocked source access, not evidence that the official inventory became
empty or that the XLSX link parser stopped recognising the source files.

The official page was inspected in the Codex internal browser on 5 November.
It still displays the same three workbook links as the retained successful page.
Offline discovery of that real successful response returns exactly those three
URLs. The real failed response now raises `SOURCE_ACCESS_BLOCKED` in the local
capture helper. No fresh machine request to the provider was submitted.

## Saved repair

The existing MRFF collector now has an explicit `Guard_source_access` after
each verified saved-page read, including the final inventory-stability read.
A recognised challenge terminates with `MRFF_SOURCE_ACCESS_BLOCKED` before
link discovery or completion can proceed. A normal page continues through
the existing parser and all existing completeness/integrity gates.

The exact native preview and independent saved readback establish:

- Two added guard actions and two changed parser `runAfter` dependencies.
- All other 39 original top-level actions unchanged.
- Source requests, retry policies, workbook discovery, known-file context,
  inventory checks, archive writes and completion naming unchanged.
- Connection references, Started state and weekly Monday 06:00 Brisbane
  recurrence unchanged.
- Recent run history unchanged; no new invocation, replay, cancellation or
  archive write was performed by this repair.

The preimage and the last successful completion response are retained privately.
The patch neither overwrites the prior archive nor substitutes its dated URLs
for a fresh complete live inventory. It does not solve challenges, forward
browser cookies/tokens, alter client identity or weaken the nonempty guard.

## Verification and remaining boundary

Nine focused tests pass, covering real capture behavior, preservation on failure,
challenge rejection even when links are present, ordinary-page handling and
exact candidate preservation/refusal. Separate offline checks use the retained
real good and failed responses. The service saved the candidate; independent
readback exactly matches its definition, connections, state and trigger.
The complete local suite passes 2,525 tests with 19 existing capability skips;
all 446 project checks and web-first contract validation pass. The earlier
interrupted invocation produced no terminal suite result; the resumed complete
invocation supplies this evidence.

The non-executing flow preflight passes on an authoring view and reports the
existing connection Connected. Direct validation of service readback initially
rejects its engine-injected authentication fields. The validation-only view
omits those 11 unchanged generated parameter references, also present in the
preimage; persisted definition/authentication fields were not changed. This
normalization is not a second save, runtime test or permission grant.

**Post-save runtime and successful unattended source access remain unverified.**
No native execution was submitted. A future unchanged natural occurrence can
establish actual runtime behavior. If the provider again serves a challenge,
the collector must fail explicitly and preserve the last good archive; a
provider-supported access route is required before claiming restored acquisition.
Browser availability does not prove that the cloud HTTP action has that access.

RMD-05 remains pending for the separate 1 December monthly exporter/observer.
No monthly plan, other flow, schedule, preference, recipient or shared
authentication selection changed.

## Evidence, ownership and documentation

Exact targets, complete preimage/candidate/readback, one-save intent, preview,
retained page/completion responses and offline/native reconciliation are in the
original checkout's ignored `private/ops/2026-11-05-mrff-discovery-repair/`.
The new source builder is pure and performs no network or native writes.
Definition rollback must use that preimage with a fresh concurrency preview;
no rollback or archive restoration was required or attempted.

Current owner is chat `01a1a569-bccc-7181-93bf-010e7dfdadde`, branch
`codex/mrff-discovery-repair-20261105`, standard Git worktree
`/Volumes/PortableSSD/GitHub/RIMS/integrate-pmf-readback-20261105`.
Owned native scope is the existing MRFF collector's four scoped action changes.
Other source/native/authentication owners retain their objects and evidence.

**Native guide/diagram publication pending:** the shared Toolkit profile differs
from the pinned workload; it was preserved and no shared documentation object was
edited. The MRFF lane retains this documentary follow-up: use the existing exact
guide/catalogue/Loop bindings and qualified identity, preserve current preimages
and human edits, publish the two-guard change and verify current/prior versions.
Source deployment does not establish native documentation parity.

## Supported browser source access — later 5 November 2026

The later user assignment selected resolution through a supported route without
flow replays or schedule changes. Ordinary downloads from the official MRFF
dataset page succeeded in the Codex internal browser for all three advertised
Excel files. The publisher's copyright page was also loaded there: it permits
unaltered personal/internal use subject to its notices and exceptions. No
cookie/token transfer, challenge solver, alternate client identity or proxy was
used. This is a qualified manual browser acquisition route, not a repair of the
cloud HTTP client's access.

The complete selected workbook capture is retained privately and independently
verified:

| Original resource | Bytes | Verification |
| --- | ---: | --- |
| Grant recipients | 1,326,355 | Complete XLSX/ZIP; saved bytes exact |
| Awarded-grants summary | 60,771 | Complete XLSX/ZIP; saved bytes exact |
| Funded-rates summary | 55,621 | Complete XLSX/ZIP; saved bytes exact |
| Total | 1,442,747 | All three advertised links accounted for |

Source and copyright document responses were captured through the internal
browser with HTTP 200. The source response was not a disk-cache response.
The link inventory remained unchanged across the downloads and source-page
reload. The response bodies, original XLSX bytes, observed URLs, capture time,
SHA-256 hashes and notices are retained. Download response headers/final redirect
URLs were not independently exposed by the browser download API and are not
invented in the receipt. Source data remains dated 10 July 2026, with publication
on 27 August; capture on 5 November does not restate those dates as current data.

The bounded data.gov.au search for MRFF returned one unrelated NSW forestry
dataset. No matching publisher machine route was established by that search;
this is not an assertion that every possible API was exhaustively checked.

### Repeatable operator route

1. Use the Codex internal browser to open the exact official source and
   copyright pages. Discover the current full Excel inventory from that page.
2. Download each advertised workbook through its normal browser link. Retain
   source/copyright responses and the observed before/after link sets in a new
   ignored capture directory. Preserve original files and publisher dates.
3. Seal the observed downloads locally with the existing MRFF tool:

   ```sh
   .venv/bin/python -m scripts.grants_mrff_download \
     --from-browser private/ops/NEW_CAPTURE/browser-observation.json \
     --out private/ops/NEW_VERIFIED_GENERATION
   ```

   `--from-browser` makes no provider request. It rejects incomplete/changed
   inventories, challenge pages, wrong sources, invalid workbook payloads and
   missing rights/date evidence. It retains source notices and originals,
   verifies every saved byte, writes the receipt last and refuses an existing
   destination. Use the real browser/session evidence: a JSON assertion by
   itself is not proof of origin or authority for native admission.
4. Keep this manual capture separate from the cloud collector's completion
   namespace and last-good selector. Any later native archive/consumer handoff
   needs the existing exact-target contract and actual stored/consumer readback;
   this capture does not commission or invoke that handoff.

The actual browser evidence is in the original checkout's ignored
`private/ops/2026-11-05-mrff-supported-browser-access/`. The byte-verified sealed
generation is in this source worktree's ignored
`private/ops/2026-11-05-mrff-browser-verified/`. Local tests use fictional bytes
only; the real download receipt separately establishes this observed capture.
The changed route passes 12 focused tests. The complete local suite passes
2,528 tests with 19 existing capability skips, all 446 project checks, web-first
contracts and Conductor structure validation. Independent rereads of the real
retained files reconcile all three lengths and SHA-256 hashes.

### Remaining automation boundary

Manual browser access is verified. Unattended cloud HTTP access, native archive
promotion and downstream consumer execution remain unqualified; the existing
collector/guard, old accepted archive and all schedules are unchanged. No flow
was invoked, replayed, cancelled or created. No source rows were analysed or
admitted, no external redistribution is authorised, and no automatic browser
job or new reminder was created. RMD-05 remains pending for 1 December.

## Unattended source-access investigation — 5 November 2026

**Still blocked at source access; no unattended replacement is qualified.** A
single ordinary request through the existing capture helper at 12:10:51 Brisbane
returned HTTP 200 with a 2,491-byte verification interstitial. The helper stopped
with `SOURCE_ACCESS_BLOCKED`, completed zero workbooks and wrote only an isolated
failed-generation receipt. It made no retry, native admission or accepted-selector
write. This is current machine-access evidence, separate from the manual capture
accepted through PR165.

The [official programme page](https://www.health.gov.au/our-work/mrff)
still directs comprehensive awarded-grant data to the existing spreadsheet
publication. Its dashboard and GrantConnect opportunity links do not establish
a supported equivalent API for the complete three-workbook inventory. The
[exact-phrase catalogue search](https://data.gov.au/data/dataset/?q=%22Medical+Research+Future+Fund%22)
returned only an unrelated university annual report. These bounded checks do
not establish that no other publisher interface exists.

[GovCMS protection guidance](https://www.govcms.gov.au/support/security/govcms-web-protection-services)
describes its WAF and automated-bot management. This corroborates the access
classification; it does not grant an exemption or identify the rule matching
this client. A local parser change cannot grant source-side machine access.
The publisher's [website guidance](https://www.health.gov.au/using-our-websites/about-our-website)
provides the feedback/general-enquiry route. An unsent request has been prepared
privately; no form, email, support ticket, subscription or external message was
submitted.

Unblock with either a documented publisher machine interface providing the
complete current inventory, update identity, originals and applicable terms,
or publisher-authorised access for the existing cloud client. Qualify the exact
approved route without browser credentials or client impersonation. Native
definition/readback and a later unchanged natural occurrence remain separate
from a local source test. No guessed API routes, alternate origins, proxy,
challenge solver or new browser job were introduced.

Read-only native comparison still matches the previously accepted definition,
connections, Started state and recurrence exactly. The latest recorded run is
the failed 2 November occurrence; the recent history contains no new invocation.
The last good archive and the separately retained manual capture are preserved.
No flow was replayed or invoked and no schedule changed. RMD-05 stays unchecked
for 1 December.

Evidence is retained under this owned worktree's ignored
`private/ops/2026-11-05-mrff-unattended-access/`: isolated failed capture,
native current/history readbacks, reconciliation and the unsent source-access
request. This source-access blocker is recorded once; recheck after a relevant
publisher/access input changes or an explicit user direction.
