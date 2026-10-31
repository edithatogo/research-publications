# Grants completion: GrantConnect first, no UI authoring or monitoring

Execution authorised by the user on 31 October 2026. GrantConnect is the grants intake priority; NIH opportunity
acquisition, admission and further chain work remain long-term roadmap. Retain
existing NIH records/configuration and source assertions in the immutable PubMed
reference artifact. Do not restart the archived integration chat.

The user-selected first source is GrantConnect RSS at
`https://www.grants.gov.au/public_data/rss/rss.xml`. Use the standard RSS
connector through FlowAgent and retain its complete returned payload before
filtering. Do not require CSV notifications/export to begin. A direct research
GET returned403; this is not evidence that the feed is absent or that the
connector route is denied. Qualify that exact supported route separately.
Primary completion chat owns this execution/source-integration lane; the former
integration chat stays archived. Existing native object and authentication owners
retain their exact scopes.

## Tool ownership

| Work | Route |
| --- | --- |
| Flow discovery, connector schemas, definition preview/update, manual execution and run outputs | FlowAgent with explicit environment/flow IDs and existing connection references. Reuse canonical JSON generators and accepted flows. |
| SharePoint lists, rows, files and existing permissions | Qualified guarded M365 CLI/API; preserve human fields, exact IDs, versions and write journals. |
| Solution packaging/release transport, if affected | Existing PAC route and canonical solution builders; no competing flow-authoring route. |
| Model, DAX and report authoring/transport | Existing Fabric CLI, bounded model preparers and powerbi-report-author pack/unpack/preview. |
| Source transformation and local checks | Existing Python builders under explicitly selected repository Python 3.15.1. |

FlowAgent is the selected API tool for flows; it is not being described as a
literal shell command. All other implementation uses the supported CLI/API
routes above. No browser-driven authoring, desktop automation, new Fabric
project, premium connector, AI service or replacement framework is selected.
Human authentication/MFA/consent is not automated or bypassed.

## Sequence and finite finish lines

1. **GrantConnect bootstrap and adapter.** Reuse the current source catalogue,
   source probe, complete-archive handling, registry identity and reviewed-import
   contracts. Establish the actual permitted API/feed/export route and reuse
   terms; do not assume one exists. Bootstrap one complete selected export or
   retained capture before implementing incremental new/amended/closed/withdrawn
   handling. Preserve source bytes/schema, round identity, uncertain dates and
   source versions. If only a permitted manual export is available, automate its
   ingestion and label acquisition manual; do not claim automatic acquisition.
2. **Register-to-reader path.** Adapt the existing guarded import/projection and
   grants-only model route to that selected GrantConnect batch. Use FlowAgent for
   the changed flow graph. Connect opportunity details/search/filter and funding
   calendar views with existing PBIR templates, retaining external versus
   institutional deadlines and review-preserving updates. Finish with the same
   opportunity/round/deadline keys and fields across source, register and reader.
3. **Personal watchlists.** Reuse existing watchlist schemas and upsert builders,
   authenticated entry surfaces and canonical UserKey conventions. Persist
   opportunity/category/funder follows, preferences, pause and unsubscribe.
   Enforce identity at the backend, not through report filters or caller-supplied
   identities. Include two already-authorised test identities in the single
   verification batch before claiming cross-user isolation.
4. **Notifications and calendars.** Reuse grants_planning, grants_calendar,
   grants_calendar_changes, grants_delivery_ledger and the existing delivery
   worker/package builders. Connect event/revision identity, reminders, changes,
   cancellations and digest preferences to the existing standard connectors.
   Verify the selected authorised recipient/channel in one controlled manual
   batch. An ICS download is not a live calendar subscription; subscription is
   complete only with an authenticated/revocable route and update/cancel handling.
   Missing recipient/send or access authority is a concrete blocker, not a reason
   to send anyway or silently claim delivery complete.
5. **Grant-reference reader integration, independently ready work.** Reuse the
   prepared 169-edge model/report adapter and current complete preimages, keeping
   the 70-part model/90-part report outcomes additions intact. Add only the
   candidate table/relationship/page, process only the new table and retain the
   exact inverse. Finish with all 169 edges, 67 mapped publications, protected
   canonical membership, provenance and publication-filter behavior intact.
   This can advance while a GrantConnect dependency is blocked; it neither
   substitutes for GrantConnect opportunities nor confirms funding relationships.

## One test and one verification per feature

- Freeze the selected output, inputs, target, inverse and assertions before
  editing. Bounded target/schema/ownership reads are prerequisites, not repeated
  acceptance campaigns. Reuse unchanged receipts and previous test results.
- Complete the feature change, then run **one combined focused test invocation**
  covering its changed behavior and meaningful failure cases. No broad exploratory
  suites, automatic retries or live negative test matrix.
- Run **one bounded manual verification batch**: saved state, one controlled
  execution where needed, actual output/data/permission comparisons and affected
  reader screenshots through the CLI. Keep these in one receipt. Multi-user and
  subscription cases belong in that planned batch, not later repeated campaigns.
- FlowAgent run_flow may wait for the same manual run with a finite timeout;
  collect that run's outputs once. A timeout is pending, not success: retain its
  ID and move to independent work. Never resubmit because the wait expired.
- A real failure requires a changed diagnosis/fix and only an affected rerun;
  the one-pass aim never means ignoring a failure. Uncertain mutations are
  reconciled before any further write or rollback.
- Do not verify recurrence, scheduled runs, operating days or scheduled delivery
  as part of these features. Do not add heartbeat jobs, monitoring loops or
  scheduled test triggers. Existing schedules and the separate 1 November
  verification remain untouched; they are not rerun or expanded by this plan.
- When a feature passes, record its result and move directly to the next ready
  feature. When blocked, retain the exact blocker/owned handles and move to an
  independent item; do not monitor it indefinitely or mark it complete.

Reuse normal source integration gates once per coherent source packet. These do
not add native/scheduled verification or justify repeating accepted feature checks.
Before any whole-definition model/report write, resolve the existing outcomes
owner and active native state, capture fresh drift/inverse and preserve their
objects. Do not infer ownership from an archived or idle chat.

## Conditions that cannot be promised away

Entirely non-UI implementation depends on a supported GrantConnect source route,
usable existing service permissions/connections, real user identities for privacy,
and CLI-capable model/report processing and preview. On an exact unsupported or
denied operation, stop that portion and move on; do not add a browser workaround,
change clients, broaden consent or invent qualification. A human-only provider
download or login must remain explicitly labelled if unavoidable.

## Execution checkpoint — 31 October 2026

Feature 5 is complete natively: all 169 references/67 publications, unchanged
canonical fields, relationship filtering, live reader rendering and saved model/
report readback passed. Preserved all outcomes additions and current report binding.

Feature 1 has a reusable manual RSS definition and complete connector-item
projector in `scripts/grantconnect_rss.py`. Run `definition --output` to prepare
its graph, or `project --input --input-sha256 --output` to transform an exact
retained capture. Outputs are private/create-only. FlowAgent saved its native
collector Stopped; direct GET403 and the enabled failure-alert subscription mean
actual RSS capture remains unverified. No CSV prerequisite was introduced.
Source-derived lifecycle dates/status cannot be claimed before a real capture.

Features 2 and 4 still require real admitted GrantConnect input and selected
recipient/channel authority. Feature 3 reuses implemented native backend identity,
version and item-security guards; real multi-user acceptance is not inferred from
fictional fixtures. These are concrete unfinished outcomes, not scheduled checks.
