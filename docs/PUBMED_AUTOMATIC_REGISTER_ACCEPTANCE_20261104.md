# PubMed automatic collection to register acceptance

The existing PubMed collector now completes acquisition, verified XML archiving,
new-publication admission and register reconciliation in one flow run. The
4 November commissioning run succeeded from 11:40 to 11:43 Brisbane. Its trigger
was invoked through the authenticated management route; every subsequent step
ran automatically. A post-repair natural recurrence has not yet been observed.
The existing daily 01:30 Brisbane schedule remains enabled and unchanged.

## Native results

| Check | Accepted result |
| --- | --- |
| Completed acquisition | 1,284 PubMed records in 13 verified XML archive members |
| Register admission | Seven missing PMIDs created |
| Register size | 1,651 before, 1,658 after |
| Complete source coverage | Every collected PMID is present in the register |
| Identity integrity | 1,355 nonblank SourceKeys, all unique |
| Existing records | Every stored value on all 1,651 pre-existing rows preserved |
| Legacy placeholders | All 303 blank-key rows preserved |
| Independent field verification | Titles, full titles, authors, journals, DOI normalization, raw dates, year/month and date precision match independent XML parsing |
| Uncertainty and notices | Unevaluated affiliation explicitly labelled; source publication types retained in evidence, including the published erratum |
| Same-archive replay | Zero admission candidates, all PMIDs present, existing rows unchanged |

The independent REST comparison excludes only the response-generated `odata.id`
envelope GUID. Item identity, ETag, versions, dates and every stored field remain
in the comparison. The flow's own before/after connector comparison also passed.

## Repair and implementation

Today's original natural collection failed before provider acquisition because
SharePoint received a literal `@concat(...)` folder path. The repaired request
uses a whole-value expression to serialize the evaluated folder path. Native
folder creation and the following complete acquisition passed.

`scripts/prepare_pubmed_register_bridge.py` adds the register stage to the
existing collector. It reads only the completed generation's named archive
members, checks each member's PMID set, and reuses the existing registry writer's
exact identity lookup and create mapping. Parsing and validation finish before
the serial writer starts. A failed acquisition cannot enter this stage.

Existing records are left unchanged, including a record found by the final
lookup after an earlier inventory. The completed XML archive retains every
source observation. This acceptance covers automatic admission of new PubMed
records and preservation of existing register records; it does not certify
overwriting existing metadata with newer provider values. Affiliation attribution
remains explicitly unevaluated for these directly admitted records.

No new flow, connector, connection, sharing setting or schedule was introduced.
The previous collector actions and connection references are unchanged apart
from the folder-expression repair. The temporary read-only qualification and
replay used the existing qualification flow, which was restored and Stopped.
The separate model-based ingestion flow remains Stopped.

## Evidence and scope

Private evidence is retained under `private/ops/pubmed-auto-cycle-20261104/`
in the dedicated delivery checkout, with independent SharePoint captures in the
same relative directory of the original checkout. It includes saved preimages,
candidate/readback definitions, single-send intents, successful run identity,
projection qualification, independent XML expectations, full registry snapshots,
reconciliation, replay and restoration evidence. Native identifiers and source
content remain excluded from Git.

The required local checks pass: 2,504 unittest tests with 19 existing capability
skips, all 446 project checks and web-first contract validation. This source
packet changes no dependency/runtime baseline.

This closes the bounded **automatic collection to list admission** step for
PubMed. Natural post-repair recurrence, canonical model/report promotion of the
new records, and other providers retain their separate acceptance requirements.
