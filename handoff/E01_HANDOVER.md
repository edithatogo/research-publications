# E01 technical handover — 24 October 2026

**Status: accepted non-Crossref evidence consolidated; Crossref final results pending.**
This handover reuses accepted receipts. It does not mark E01 complete or establish
new native state, operational adoption, production cutover or authority to send.

## PubMed/DoRA continuation — 24 October 2026

The [retrieval qualification continuation](../docs/DORA_RETRIEVAL_EFFICIENCY.md#qualification-continuation--24-october-2026)
supersedes any implication below that Crossref is the sole remaining selected
outcome. Fresh complete PAC clientdata and independent Flow API readback match
accepted PubMed57/DoRA110, original connections/Started/daily schedules/concurrency1.
Accepted guide20/catalogue21/Loop82 documentation is reused unchanged. The current
DoRA graph has10second delay and the provider-failure latch; historical2second
artifacts remain superseded. No native mutation or collection invocation occurred.

Next affected natural runs are25October01:30Brisbane and04:30Brisbane respectively;
neither had occurred at readback. Their runtime, actual savings and DoRA latch
failure-path acceptance remain pending. Existing accepted raw/replay/restart
receipts remain usable where their graph/inputs are unchanged. Do not launch a
duplicate or full-generation verification run.

Sitemap qualification did not pass: the second full page/all709selected tokens and
one40,847-byte record remain identical, with no observed changed-record transition
or established site-specific freshness bound. Three serial provider requests used
4,494,698decoded bytes; observed retrieval savings are zero. Tokens remain opaque.
The local selector now requires an explicit response-age bound and rejects stale,
future and unbounded cache entries; no native reference reuse or consumer migration
is claimed. Keep the supported full-fetch/10second/commit-last fallback. The709
record spacing floor is118.17minutes, before other work. Evidence and the next
natural-run checklist are in primary
`private/ops/2026-10-24-pubmed-dora-completion/`.

This selected continuation owns PubMed/DoRA only. Preserve the retained Crossref
run, recovery material and active three-hour monitor exactly. Other lanes retain
the shared model/report, grants, native documentation objects and CURRENT_STATE.

## Accepted capabilities

Fresh native setup inventory and the reduced-run delivery approach are in
[source schedules/state](../docs/SOURCE_FLOW_NATIVE_SETUP_20261024.md) and
[accelerated delivery](../conductor/tracks/E01_flow_automation/accelerated-delivery-20261024.md).
These are definition/state evidence; they do not assert new runtime acceptance.

| Area | Accepted evidence | Last accepted restored state |
| --- | --- | --- |
| DataCite | Genuine completed-query prefix automatically reused without recollection; second query completed under frozen provenance; chained archive guards passed; original checkpoint identity/ETag/all260707bytes unchanged | 63actions, Thursday05:00 Brisbane, concurrency1, original binding, Started |
| ClinicalTrials | Release-pinned100-row prefix continued; two exact12677-ID sets;253 new discovery pages and6 full trial payloads passed native archive/readback guards; terminal manifest/studies independently byte verified | 32actions, Wednesday04:00 Brisbane, original binding, Stopped |
| H04 / register writer | Representative malformed/count/key/query-error/partial-page/429-retry/actual HTTP-timeout/policy-denial cases; interrupted update followed by replay with zero creates;1651 register rows,303 legacy blank-key rows and last-good export preserved | 11actions, original daily schedule and bindings, Stopped |
| Digest | Supported draft removal and repair; exact native/service sender wiring and equivalent reset; run history unchanged; native no-send control readback | Manual, Stopped, literal send-authority gate false |

### Qualification limits

- DataCite's prefix contained completed queries, but both provider responses had
  zero rows. Positive-row dataset recovery and a new accepted full generation are
  not claimed.
- ClinicalTrials raw-page equality was proved by native guards. The two terminal
  artifacts were independently read and hashed; all raw pages were not separately
  downloaded. Its running recovery candidate's scope ordering caveat and corrected
  restored dependency remain in the receipt.
- H04's later actual HTTP-timeout receipt supersedes the earlier timeout gap.
  Injected403 and actual HTTP destination-policy denial are distinguished from
  a real SharePoint ACL denial; no ACL changes were made.
- Digest email delivery is not accepted or authorised. Particular recipients,
  content, attachments and intended send scope require explicit human approval.
  Drafts/previews are allowed. Do not enable or send test/production mail.

## Sole remaining E01 exit: Crossref

Preserve the retained handle and all completed partitions. Its last native
readback is Running. Do not duplicate, cancel or treat elapsed time as failure.

1. On success, reconcile full query/window and DOI coverage, retained raw pages,
   totals/key sets, manifest, stored completion/checkpoint bytes and last-good.
2. Verify replay and duplicate prevention using the qualified same-ID route.
3. On natural failure only, reconcile any additional complete windows and current
   archive/checkpoint/native drift before using the prepared continuation path.
   Retain original cutoff; restart only unfinished work with a fresh cursor.
4. Confirm normal definition, bindings, state, schedule and concurrency, reconcile
   affected records, then close E01 when these final results pass.

The user subsequently authorised throughput implementation. The
[updated plan](../conductor/tracks/E01_flow_automation/crossref-throughput-improvements.md)
and `scripts/prepare_crossref_batches.py` now provide a local low-copy, bounded
hedge-batch candidate with frozen progress and original acceptance guards.
The permanent pair is not deployed; the retained Running handle still gates
its deployment. The subsequent `prepare_crossref_lanes.py` candidate separates
the existing daily flow from a new Stopped baseline worker with independent
progress/archives/checkpoints; native creation/save/readback and runtime proof
remain pending. It supersedes the single-flow candidate for future deployment.
DOI batching remains conditional on phase-specific measurements. Throughput evidence supports throttling;
no reliable completion ETA or qualified force-resume is established.

### Isolated parallel qualification accepted

The separately authorised manual qualification succeeded alongside the original
run. Its acquisition branch took25seconds and retained one189,482-byte page with
13rows/13unique DOIs, exactly matching the provider total for the selected
Yarrabah query. Scope, raw envelope, attempt/window summaries and unaccepted
progress were independently read and hashed. Full native definition/reference
readback passed before execution and after restoration to Draft/Stopped.

The current last-good selector, ID, ETag, length and hash were unchanged; no
accepted checkpoint marker was written. Keep the qualifier Stopped as evidence
and do not invoke it again automatically. This proves a small one-query path,
not monthly projection parity, two-batch continuation, full reconciliation,
sustained capacity or a quantified speedup. Native versioned documentation is
pending. Receipts: `qualification-runtime-acceptance.json`,
`qualification-runtime-archive-proof.json` and `qualification-lastgood-postrun.json`
in the existing ignored E01 directory.

The recovered exact PAC client now supports full FetchXML native readback and
same-ID Power Fx clientdata updates. Use the existing native Dataverse reference
representation, preserving connection/logical-reference IDs. A Flow API reference
presentation is not interchangeable with Dataverse's map. Treat native validation
and complete readback as authoritative; PAC can exit zero after a rejected Patch.

## Local email safeguards

Sender/schedule review and local preparation-gate evidence are retained in
`email-local-safeguards-review.json` in the ignored private E01 directory.
A historical helper with open send authority is now rejected before adoption;
its unchanged evidence is not a deployable send approval. Native state is unchanged.

## Evidence and recovery

- [Consolidated machine-readable handover and20 receipt hashes](../private/ops/2026-10-23-e01-current-state/e01-consolidated-handover.json)
- [Accepted maintenance and source-health handoff](../private/ops/publication-flow-operations-acceptance.json)
- [Crossref frozen-window recovery handoff](../private/ops/2026-10-23-e01-current-state/CROSSREF_RECOVERY_READY.md)
- [Crossref recovery package hashes](../private/ops/2026-10-23-e01-current-state/crossref-recovery-package-manifest.json)

Native definitions, bindings, identities, operation handles and raw evidence stay
in ignored private paths. Historical receipts remain intact; the consolidated
handover explicitly records superseding results and limits.

## Ownership and resumption

E01 retains its existing flow/checkpoint ownership. T11 owns shared-model freshness
and coverage projection; E01's source-evidence handoff is reconciled, without
claiming T11 native projection acceptance. E08 retains later natural recurrence
and unattended observations. Adoption, rollout and business acceptance are later
work, outside current technical setup completion.

Use the existing qualified VS Code workload authentication route if recovery is
needed. Preserve exact clients/resources/references and failed-effect gates.
No new grants, connections, licences, sharing, activation, contacts or email
authority follow from this handover. Resume Crossref from CURRENT_STATE and the
retained handle; do not repeat accepted diagnostics or receipt-only runs.

## Current recovery preparation — 24 October

The verified original-generation prefix now contains251of313windows,330pages,
84,886rows and1,158,439,717bytes. All482previously selected metadata identities,
ETags and lengths are unchanged. Two other listed pages are outside the verified
complete-window prefix and excluded. Use the251-window complete manifest through
CROSSREF_RECOVERY_READY; old210/218packages remain history. Recovery still requires
genuine terminal failure and fresh drift checks. The updated consolidated receipt
is `e01-consolidated-handover-20261024.json`; this handover leaves E01 incomplete.

## Independent enrichment admission — 24 October

The next incoming-citation increment is also accepted:48 native responses,
344 distinct OCI relationships, all102 earlier OpenCitations files unchanged,
manual/Stopped and exact native definition/reference readback. Its native
documentation is complete (guide17/catalogue18/Loop74;43 exact native sources,
prior42 unchanged). Reuse
`private/ops/2026-10-24-opencitations-citations/acceptance.json` and
[the implementation leaf](../docs/OPENCITATIONS_CITATION_LINKS.md); do not repeat
acquisition automatically. This supersedes the earlier documentation versions
below while retaining their accepted scope. Crossref was still Running at final
read; its retained handle, archives and monitor remain preserved.

The pending native documentation for this increment is now complete. Current
guide16.0/catalogue17.0,42 reopened native Mermaid sources,24 downloadable graph
files and the scoped field-guide source are accepted. Prior39 native source
hashes and318 unrelated file identities/versions/content metadata are unchanged.
See [native documentation](../docs/OPENCITATIONS_NATIVE_DOCUMENTATION.md) and
`private/ops/2026-10-24-opencitations-documentation/acceptance.json`. This
supersedes documentation-pending wording below, without closing solution admission
or Crossref/E01.

The48 accepted OpenCitations count/metadata observations are admitted through the
existing Archived source assertions manual consumer, using the original archives
and zero provider requests. Independent readback verifies48 exact new assertions,
46 unchanged earlier records and99 unchanged earlier OpenCitations archive files.
The temporary bounded packet path is restored; full native candidate readback,
original reference and Stopped/manual/concurrency-one state pass. Reuse
`private/ops/2026-10-24-opencitations-consumer/acceptance.json` and the
[implementation leaf](../docs/OPENCITATIONS_SOURCE_ASSERTIONS.md); do not repeat
accepted acquisitions or this import automatically. Native versioned documentation
publication remains pending. Crossref was still Running at the latest native
read during this work; its retained handle, archives and monitor are preserved.

## Revised Crossref search policy — 24 October 2026

The user authorised [targeted discovery plus DOI reuse](../docs/CROSSREF_TARGETED_DISCOVERY.md).
New local policy/compilers supersede the former broad-search candidate.19enabled
queries omit Tropical/Liz and6other broad tokens, with all maintained aliases
mapped and discovery gaps explicit. Independently hashed330-page analysis retains
all archives and builds1,501provenance-linked DOIs, including every1,283prior DOI.
The saved original generation remains a separate frozen scope and was freshly
Running at implementation entry. Keep its monitor and terminal gate.

Page-level yield/resume and accepted native-version DOI reuse are compiled local
behavior, not saved/runtime proof. New-scope primary bootstrap, exact native
save/readback, two actual batches, final reconciliation/replay and native diagrams
remain pending. Read private/ops/2026-10-24-crossref-targeted/implementation.json
and the owned E01 checkpoint before effectful work. Do not deploy the old599-window
candidate or reset the retained handle to apply the new scope.
