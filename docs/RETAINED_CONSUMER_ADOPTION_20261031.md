# Isolated retained consumer and grant references

The CLI consumer reads the accepted raw23 committed batch, checks every typed
member against its independently retained byte receipt, reconciles the complete
publication keys and reconstructs full metadata using the existing chunk decoder.
It preserves the summary fields, complete structured metadata and author evidence.
It reuses the pinned complete raw-byte acceptance; it does not reacquire sources
or repeat the already accepted raw archive verification.

`scripts/consume_retained_pubmed.py` requires the typed receipt and raw acceptance
file SHA256s, the retained typed archive directory and an exclusive new output.
All real inputs, outputs, bindings and receipts belong in ignored `private/ops`.
Use the explicitly selected Python 3.15.1 interpreter. Example shape:

```sh
.venv/bin/python scripts/consume_retained_pubmed.py \
  --receipt private/ops/typed-byte-acceptance.json --receipt-sha256 RETAINED_HASH \
  --raw-acceptance private/ops/raw-byte-acceptance.json --raw-acceptance-sha256 RETAINED_HASH \
  --archive private/ops/typed-archive --output private/ops/new-consumer.json
```

`scripts/consume_retained_grant_references.py` consumes that pinned output and
the accepted full canonical CSV bytes. It reuses `source_relationship_evidence`
for one named use: PMID-to-source-scoped GrantList references. The join uses only
`CanonicalKey` and `PMID`; the complete canonical input digest is retained as
well. DOI values, titles and names do not establish this relationship. It retains
agency/country/grant identifier namespaces, source paths, metadata digests,
ambiguous mappings, unresolved namespaces and candidate/retraction state.
It never equates a grant reference with a confirmed award-register relationship.

```sh
.venv/bin/python scripts/consume_retained_grant_references.py \
  --consumer private/ops/new-consumer.json --consumer-sha256 RETAINED_HASH \
  --publications-csv private/ops/accepted-full.csv --publications-sha256 RETAINED_HASH \
  --output private/ops/new-grant-references.json
```

The selected retained generation yields 1,277 publications, complete metadata and
11,731 author-evidence rows. Grant references yield 169 candidate edges mapped
to 67 of the unchanged 1,344 canonical publications; zero are promoted to confirmed
relationships. One retained canonical DOI cell contains a title; it is preserved
and is outside this PMID-only join. No freshness or new record admission follows.

Cloud delivery uses the existing guarded `documentation-sync` CLI and exact
owner-only DEV reporting target. Each isolated artifact has a new immutable name.
Require every plan action to be `create`, then apply once with its own journal;
the existing helper checks saved identity/version and downloaded-byte SHA256.
Never widen target pins or overwrite an existing artifact to complete this slice.
The old team documentation folder was observed absent, so no write was attempted
there. The original stale read lock was preserved; same-client resource renewals
and lane-local identity-only bindings retain the existing authentication route.

This is adoption by an isolated CLI consumer with stored cloud evidence output.
It is **not** adoption by the existing Power BI retained-reader query or a native
typed relationship model. Those require an independently qualified model target
and saved/runtime proof. The working model, exporter, monitor and existing
1 November 07:50 Brisbane verification remain unchanged. Working-path promotion
must consume that natural-schedule result first. Rollback is to stop using the
isolated new artifacts; no baseline object or data restoration is needed.

Focused checks: `tests.test_consume_retained_pubmed` and
`tests.test_consume_retained_grant_references`, one selected invocation per slice.
The relationship check was rerun only after the real retained DOI defect exposed
an unnecessary DOI dependency; the corrected PMID-only join is covered. Native
receipts are under `private/ops/retained-{consumer,relationships}-20261031`.
