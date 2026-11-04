# DoRA changed-metadata updates — 4 November 2026

The selected repair reuses the accepted complete 709-record DoRA publication
archive. It adds changed-metadata updates to the existing collector after its
accepted admission stage. It does not start another provider crawl.

## Ownership and update contract

All 709 archived handles are already represented by 713 register rows: 62 have
DoRA source keys and 651 have PubMed source keys. Four historical overlaps retain
both existing identities. The registry's established PubMed precedence remains
in force, including rows whose displayed source set alone says DORA.

`scripts/prepare_dora_metadata_bridge.py` projects the 62 source-owned rows from
saved full-metadata HTML. It reuses the accepted parser, exact handle/title guard,
and conservative publication-date handling. Issued dates come from
`dc.date.issued`; repository deposit or update timestamps are not substituted.
The complete original HTML remains in the accepted archive.

The only mutable fields are Title (255-character display limit), SourceFullTitle,
Authors, Journal, PublicationYear, PublicationMonth, PublicationDateRaw and
PublicationDatePrecision. Source/canonical keys, DOI/PMID/URLs, source set,
review status and notes, affiliation/attribution, first/last-observed timestamps,
and every enrichment field remain outside the write payload.

The stage requires a complete bounded register inventory, one verified archive
file per selected source key, and successful projection of every candidate before
writing. Absent authors or journals retain their existing register values. Missing or
unparseable issued years preserve the existing date group. Equal null/empty
textual values do not cause a rewrite. Each changed row
is reread, its identity and metadata preimage are checked, and the update uses
its actual ETag with mutation retries disabled. A native readback verifies the
new values. Interrupted work is recovered by readback and a new comparison, not
blind mutation retries.

A uniquely named archive receipt correlates the accepted source run with the
list-update run, field scope, source filename and row-level before/after values.
The receipt itself is read back and verified byte-for-byte. The production change
is additive and preserves the original collector, connection references,
recurrence and state.

## Verification

The read-only comparison caught missing journal metadata that would otherwise
have cleared 50 populated values. No writes had occurred. The compiler now
preserves absent source values, with a regression test for that rule. This is the
reusable lesson: missing metadata is not evidence of deletion.

All four final candidates match independent Python HTMLParser parsing of their
actual archived full-metadata HTML. The qualified native update succeeded at
15:21:15 Brisbane on 4 November and saved its source-correlated receipt with
byte-for-byte readback. The existing qualification flow performed this bounded
continuation of the accepted archive; no provider collection was triggered.

| Acceptance check | Result |
| --- | --- |
| Accepted archive | 709 handles, reused without a fresh crawl |
| Ownership accounting | 62 DoRA-owned rows; 651 PubMed-owned rows preserved |
| Actual updates | Four existing rows: full title, journal, issued year/raw date/precision |
| Absent source metadata | 50 existing journal values preserved |
| Register membership | 1,658 rows before and after; no additions or deletions |
| Protected fields | All unchanged on every row |
| Unselected rows | All stored values on 1,654 rows unchanged |
| Updated-row system changes | Modified, item version and ETag only |
| Same-archive replay | Succeeded at 15:25:31 Brisbane; zero candidates and zero list changes |
| Replay preservation | Every stored value, timestamp, version and ETag unchanged |
| Daily collector deployment | Ten added actions; all 58 original actions, references and Started state preserved |
| Schedule | Existing daily 04:30 Brisbane recurrence unchanged |
| Qualification/deployment parity | All ten added action objects match the successful writer and replay |
| Temporary qualification flow | Exact original definition/references restored; Stopped |

The complete independent REST comparison excludes only response-generated
`odata.id`. The local milestone passed 2,510 tests with 19 existing skips,
446 project checks and the web-first contracts. These are local gates; native
acceptance is supported separately by the retained
update, replay and saved-definition receipts.

The changed-metadata path is repaired and commissioned against the accepted
archive. The next naturally scheduled execution of the newly extended full
collector has not yet been observed. Commissioning and replay are not claimed
as a new natural collection cycle. No extra monitoring or scheduled jobs were
created.

Raw definitions, exact list/run identities, full-register snapshots, archived
HTML hashes, mutation intent, action results and restoration evidence remain in
ignored `private/ops/dora-metadata-20261104/` evidence directories. The source
compiler and this acceptance record form the bounded delivery packet.
