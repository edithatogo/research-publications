# Crossref recurring collection and automatic list updates — 4 November 2026

The selected scope is the existing daily incremental DOI collector and the
`CitationCount_Crossref` field on matching publication-register rows. It does not
create publications, consolidate identities, overwrite review decisions, merge
funders/awards, or imply fresh capture of every publication's metadata.

## Recurring collection evidence

FlowAgent CLI readback confirmed the existing collector is Started with its
unchanged daily 03:30 Brisbane recurrence. Seven natural executions succeeded
from 29 October through 4 November. The latest run completed at 03:31:50 Brisbane;
its complete coverage/checkpoint guards passed and its current batch was empty.

The accepted 1,286 DOI keys remain a subset of the current 1,288-key coverage.
Natural runs on 30 October and 2 November each added one DOI. Both HTTP200
responses were independently downloaded, parsed and identity-checked. The
remaining dated responses are reused under the existing explicit-expiry policy.
No new provider requests, source sweep, scope expansion or expiry declaration
was submitted by this repair. This is not a fresh sweep of 1,344 publications.

## Transport recovery and missing connection

Exact FlowAgent reads initially failed with `UND_ERR_CONNECT_TIMEOUT`. DNS and
TLS checks established endpoint reachability; scoped Node options
`--dns-result-order=ipv4first --no-network-family-autoselection` allowed the
required exact reads and saved-definition operations to succeed with the same
client, account and connection references. An independent SharePoint read also
reported IPv6 `EHOSTUNREACH` and IPv4 timeouts. Completed downloads were retained;
only remaining reads were resumed. This is a qualified transport mitigation,
not a claim that all external network failures have been eliminated.

Fresh readback showed the existing model-based publication writer is Stopped.
Its Crossref reference is an export mapping, not a list-field write. The daily
collector had archive/checkpoint writes but no publication-list update action.
The repair adds the missing archive-to-list stage to that collector.

## Update contract

`scripts/prepare_crossref_register_bridge.py` appends the stage after verified
incremental checkpoint completion, preserving the original source graph,
recurrence, physical connections and state. It reads a complete bounded register
inventory and accepts exact DOI matches only. Existing citation counts are
preserved unless that DOI belongs to the collector's explicitly refreshed batch;
missing counts can be filled from dated, verified coverage entries.

Only HTTP200 records with matching requested/returned DOI and a nonnegative
integer `is-referenced-by-count` are eligible. HTTP404 is not converted to zero.
All selected raw responses are projected before list writes begin. Each serial
update rereads the target identity/count, checks the exact preimage, uses its
current ETag, changes only `CitationCount_Crossref`, and rereads the result.
Mutation retries are disabled. Ambiguous failures require readback before
recovery; a later run can fill still-missing rows without overwriting completed
ones. Shared metric timestamps and other providers' values are preserved.

A source-correlated receipt retains each row identity, DOI, before/after count,
source file and original capture run. It is saved under a unique list-update
run filename in the existing archive and read back byte-for-byte.

## Verification

The read-only native projection succeeded. All 72 proposed row values across
69 distinct DOIs match independent parsing of the actual archived responses.
Four matched HTTP404 rows remain ineligible. The 2,505-test suite passed with
19 existing skips; 446 project checks and web-first contracts also passed.

The native downstream continuation succeeded at 13:59:36 Brisbane on
4 November, using the exact coverage produced by that morning's natural
03:30 collection. The existing qualification flow performed the continuation;
no new source collection was triggered.

| Acceptance check | Result |
| --- | --- |
| Actual SharePoint updates | 72 existing rows across 69 DOIs |
| Register membership | 1,658 before and after; no additions/deletions |
| Updated values | All match independently parsed stored Crossref responses |
| Protected business fields | All unchanged, including shared timestamps and other providers' metrics |
| Unselected rows | All stored values on 1,586 rows unchanged |
| Expected system changes on updated rows | Modified, item version and ETag only |
| HTTP404 cases | Four matched rows remain blank, not zero |
| Same-archive replay | Succeeded at 14:00:45 Brisbane; zero candidates and no list changes |
| Daily collector deployment | 12 added actions; all 77 original actions, references, recurrence and Started state preserved |
| Qualification/deployment parity | All 12 added action objects exactly match the successful writer and replay |
| Temporary qualification flow | Exact original definition/references restored; Stopped |

The complete independent REST comparison excludes only the response-generated
`odata.id` annotation. Replay also preserves system timestamps, versions and
ETags. The source-correlated receipt was saved and its bytes verified natively.

**The collection-to-list path is repaired and commissioned for Crossref citation
counts.** Existing natural collection evidence and its exact downstream archive
continuation are accepted together. A single natural run through the newly
extended collector has not yet occurred; the next unchanged recurrence is
5 November at 03:30 Brisbane. This does not claim fresh citation counts for all
retained DOIs, broader enrichment-field synchronization or model/report promotion.

## Private evidence and rollback

Exact identifiers, preimages, mutation intents, transport diagnostics and native
run receipts remain in ignored `private/ops/crossref-natural-20261104/` in the
delivery checkout. Independently downloaded archive files and complete register
snapshots use the same relative path in the original checkout.

Restore the collector's exact preimage definition/references through the same
preview/update route if needed. A flow rollback does not undo list values; any
value rollback must use the retained per-row preimage and current ETag, and must
refuse intervening field changes. Preserve both source archives and receipts.
