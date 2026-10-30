# Local-first outcomes CLI recipe

This increment reuses the outcomes track and existing relationship builders.
Canonical source and the sanitized CareOps module remain separate histories.
The source writer owns only its isolated checkout; native objects, authentication,
shared main and CareOps pins retain their current integrators.

## Prepare and compare locally

Select `.venv/bin/python` and verify Python 3.15.1. Use the `outcomes`,
`relationships`, `projections` or `reader` harness selection for affected work.
The harness remains offline. Existing `check --task all` is the integration gate;
do not repeat it after unrelated documentation edits. Docs need structural/link
checks, not mirrored application tests. Package/unpack only affected solutions.

`outcome_persistence.py` replays exact source bytes and their original reference
snapshots through `outcome_evidence.intake`. It retains explicit human edits and
all revisions. Reporting calls the existing eligibility/redaction projection;
facts and project bridges remain separate, avoiding multiplication of totals.

The initial adapter is a bounded journal in one existing SharePoint item, updated
with an exact ETag. Candidate field mapping is an existing plain multiline-text
field holding the journal; item ID and native ETag are outside that payload.
This is a technical candidate, not a selected/provisioned authoritative register.
An existing register with different semantics needs an explicit mapping adapter;
never replace it with this storage shape automatically. Journal text is capped at
60,000 UTF-16 code units and fails rather than truncating or silently sharding.
This bounded candidate does not implement a scalable cross-domain register.

Read the exact owner-approved list schema, field type/limits, item and ETag before
finalising the mapping. Existing item creation, uniqueness/index changes and
provisioning are separate candidates. Missing item/schema is not an empty store.
Do not copy authentication caches, create fresh clients, or broaden retained read
allowlists to acquire this evidence. No binding or native schema capture exists
in this lane, so its target-bound migration is blocked pending that evidence.

## Apply once, read back, recover

The adapter's owner-supplied transport has `read(item_id)` and
`compare_and_set(item_id, etag, journal)`. Reads return the logical snapshot
`item_id`, `etag`, `journal`; updates touch only the privately bound journal field.
The transport MUST use SharePoint server-enforced `If-Match`, not a pre-read-only
comparison; disable mutation retries and redirects. The local transport fixture
is not qualification of a native transport.

`prepare` validates the complete history and generates a before/after hash and
conditional update. `apply_once` reads the current state, rejects drift, sends at
most once, and reconciles a lost response by readback. Unknown results stay
unknown; they never trigger another write. A retained preimage can be restored
only against the actual postimage's ETag after confirming no later human edit.
Never overwrite intervening revisions to make rollback convenient.

For flows, reuse the existing [same-record deployment helper](FLOW_DEPLOYMENT_HELPER.md)
and accepted SharePoint action examples. Do not guess the connector contract or
add an HTTP/premium connector. Existing stopped/no-send state remains unchanged.
A generated candidate, pack/unpack pass or saved definition is not runtime proof.

## Power BI and manual handoff

Prepare model/report candidates from complete frozen source definitions. Retain
all existing pages, parts and identities. Use the supported definition API only
after the owning client/resource/target and non-premium entitlement are qualified.
The legacy browser-session and saved-token entrypoints now prepare offline packets only. They do not execute a deployment.
No current private target binding/entitlement receipt is available in this lane;
do not claim the API is unavailable globally or infer entitlement from a helper.

If MFA/consent is required, provide the exact supported login step to the user.
For changed report pages provide a manual readability, keyboard, filter/detail
and recovery checklist. If a non-premium authoring API is unavailable, provide
an eligible manual import/edit handoff or record a blocker. No browser automation,
VM, capacity purchase, Copilot or premium feature is a fallback.

## Minimum evidence and reuse

Record source/package hashes, interpreter/dependency identity, exact selectors,
results and changed native inputs in existing private receipts. Reuse unchanged
checks. Native checks cover only changed behaviour: exact saved state/references,
one fictional example, replay and scoped recovery. Keep local, saved-definition,
runtime and visual outcomes separate. Do not add a new evidence registry, global
skill, MCP server or automatic retry/test-selection framework.

## Local commands and implemented reader subset

Run `scripts/outcome_persistence.py --help` for private prepare/project/schema
inputs. `scripts/prepare_outcome_reader.py --help` prepares additive TMDL tables
and an evidence-count/detail page from complete model/report definitions and
accepted card/table templates. It requires an already reviewed OutcomeProjection
M expression; it does not invent a source URL or silently embed fictional data.
The current subset has no project-filter relationship propagation, quantitative
impact plots, funding/capacity pages or evidence drillthrough. These remain actual
implementation gaps, not native acceptance-only tasks.

`scripts/deploy_report_definition.py --help` prepares a complete definition
update/recovery packet, refusing omitted parts, unreviewed changes and binding
changes. `deploy_canonical_report.py` delegates to the same isolated preparation
route. `deploy_measures.py` now prepares its legacy measure text locally and does
not drive a browser editor. A supported same-client native executor remains
blocked on exact target/client/entitlement and no-retry transport qualification;
none of these entrypoints submits a request or reads a token file.

Project-scoped CLI projections now accept repeated `--project-id` values. They filter facts through distinct bridge keys without multiplying records. This does not implement native Power BI filter propagation. Project detail is limited to eligible-linked identities; the complete withdrawal audit remains a separately scoped view.

The retained completion-owner binding was inspected without authentication changes: it pins SharePoint, Graph and ARM resources, not the Fabric/Power BI definition resource. Its absence of an active lock does not transfer ownership or qualify a new resource. Native definition-write qualification remains unresolved; do not broaden this binding.

The quantitative projection now exposes each eligible observation's estimate,
numerator, denominator, explicit value states, indicator/version, unit and cohort
identity. The reader candidate includes an individual-observation table and a
single-observation estimate measure; multiple selected observations produce no
pooled estimate. This is not the remaining quantitative chart or drillthrough
implementation and has not been verified in the native model.

A bounded read of the retained exact personal-workspace report through the
previously successful Azure CLI Power BI resource route returned AADSTS70043
on 30 October. This is an expired/invalid refresh-token authentication result,
not proof of a permission or non-premium licensing failure. Shared authentication
was not renewed or switched. The existing authentication owner must complete
supported interactive renewal before this route can supply fresh target evidence.
The retained owner binding for other resources remains unchanged.

The funding/capacity CLI projection now implements C01 active/known-led project
counts, C02 distinct evidenced participants and F01 award-start cohorts separated
by currency. It requires explicitly mapped complete inputs; existing ARC text
amounts are not silently parsed or promoted to institutional funding. Unknown
periods/lead evidence are counted, and FTE/training/application success remain
unavailable. Funding/capacity model tables and report pages remain unfinished.

`python -m scripts.prepare_funding_capacity_reader --help` prepares additive
funding/capacity tables and a 1920×1080 detail page against a reviewed existing
FundingCapacityProjection expression. It preserves existing report parts and
keeps award currency/start cohorts separate. This implements local detail-page
preparation, not charts, drillthrough or native source binding/acceptance.

The outcome reader now prepares a bar chart and explicit drillthrough/back
buttons using the existing repository visual contracts. Estimates are shown per
observation and suppressed for mixed indicator/version/unit/population/setting
contexts. The detail page carries the observation ID filter. Local structure
checks do not prove DAX execution, filter propagation, rendering or keyboard
behaviour; those native/manual exits remain open.

Funding candidates now include an award-start chart with explicit currency series
and navigation to the exact-decimal detail tables. The chart measure admits only
one currency/cohort, converts its display value without changing retained decimal
text, and returns blank on conversion failure. Native DAX/locale, currency-series
behaviour and rendering still require qualification; no exchange-rate comparison
or cross-currency total is supplied.

`python -m scripts.prepare_outcome_flow --help` now prepares an operator-qualified
frozen journal update for an existing empty isolated manual flow. It preserves
the supplied connection reference and trigger, reuses the standard SharePoint
HTTP action contract, disables retries, enforces an exact ETag, and reads back
after success/failure/timeout. Existing nonempty flows are refused rather than
replaced. This is a bounded pilot candidate, not dynamic untrusted-user intake,
a deployed persistence service or native recovery proof.
