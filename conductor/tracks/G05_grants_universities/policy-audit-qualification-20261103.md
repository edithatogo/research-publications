# G03 audit and G05 policy qualification — 3 November 2026

## G03: exact audit-query list denied

The existing guarded Toolkit workload was used for one bounded Graph v1.0
`GET /security/auditLog/queries` metadata read. A task-specific private binding
added only this exact read root while preserving the client, account, tenant,
resource and SDK pins. Its first attempt stopped before the native request
because the service session needed interactive renewal. The same pinned client
then completed one normal `form_post` renewal in the Codex internal browser;
identity validation passed. The one subsequent exact metadata read returned
HTTP 403 and produced no response file. This is an operation/client-specific
access denial; it does not prove that the historical event does not exist or
that another already-qualified workload is denied. No audit-search job was
created, no additional consent requested, and no native grant data changed.

The [documented Graph operation](https://learn.microsoft.com/en-us/graph/api/security-auditcoreroot-list-auditlogqueries?view=graph-rest-1.0)
is a query-list read. It is not a successful historical search, a SharePoint
record read, or proof of recoverability. G03 remains partial pending an already
qualified audit route or retained exact historical evidence. Preserve the
previously accepted scoped fixture and writer-safety evidence.

## G05: publisher-linked current policy

The university's official policy site
describes itself as the authoritative source for current documents. On 3
November its own search returned “External Research Funding Management Policy”
as the first result. The PDF link opened from that result points to the
[publisher-hosted document](https://sharepointpubstor.blob.core.windows.net/policylibrary-prod/External%20Research%20Funding%20Management%20Policy.pdf).
Its downloaded bytes match the previously retained 2024 candidate exactly.
The document identifies number 2024/0001156, approval on 14 November 2024,
effect from 1 January 2025 and review in 2027. No formal version number is
asserted. The publisher-linked search result resolves current-document
provenance at this observation date; it supersedes the earlier statement in
`qualified-routes-20261103.md` that current policy status was unverified.

This is policy-document evidence, not a project entitlement, eligibility
assessment, internal deadline, permitted machine feed or authorised export.
Keep manual-review intake and unknown timezones/lead times. The current
catalogue's `verified_versioned` state requires an actual version, so it is not
set by inventing one from the document number or date. G05 remains partial for
institutional source and native-intake acceptance; no opportunities were
admitted and no source, flow or model was changed.

## Retained evidence

The exact pinned-read and identity-validation receipts, publisher-search
screenshot, downloaded PDF, byte comparison and reconciliation are held under
`private/ops/2026-11-03-g03-audit-read-qualification/` in the original native
checkout. No identities, raw responses, tokens or publisher PDF are included in
this source record. The shared grants-import owner and existing journals remain
unchanged. Main checks for the preceding PR passed on its merge commit.
