# Local study explorer

The user-selected scope covers all clinical studies, with interventional trials identified, and separate external discovery and confirmed-association views. RIMS holds study identities; evidence and standards remain in PPG. This first local implementation searches retained ClinicalTrials.gov records, including observational records. It reuses the existing source projection and exact-ID ZIP integrity validator. It makes no network requests or native changes.

## Run

Use repo-local Python3.15.1. For an existing accepted exact-ID archive:

```sh
.venv/bin/python -m scripts.study_explorer \
  --archive private/ops/<accepted-capture>/studies.zip \
  --sha256 <independently-retained-archive-sha256> \
  --observed-at <source-observation-with-timezone> \
  --associations private/ops/<reviewed-associations>.json \
  --query diabetes --country Australia \
  --output private/ops/<new-explorer-output>
```

Alternatively `--input` accepts a retained JSON object containing only `studies`, an array of full ClinicalTrials.gov protocol records; supply its independent `--sha256`. It refuses raw paginated API envelopes so a nextPageToken cannot be silently ignored. The tool does not establish corpus completeness. Optional exact filters are `--status` (e.g. RECRUITING), `--study-type` (INTERVENTIONAL or OBSERVATIONAL); query searches title, identifier, condition and intervention. HTML is searchable with ordinary browser find; change filters through the CLI. Outputs are HTML and JSON, with filters, capture hash, association-set hash and source observation time. Output stays below repository private/ops, refuses symlink escape and existing destinations, and retains distinct keys.

## Reviewed association input

An optional JSON array contains exactly: `source_key`, `review_status` (Reviewed), `involvement` (conducting_site, sponsor or investigator_affiliation), `evidence_url` (HTTPS) and `ppg_evidence_urls` (HTTPS array). An evidence-backed investigator affiliation is not a conducting site. No association is inferred from names, source location strings or title matches. The caller must supply genuinely reviewed assertions; the tool checks their shape and references, not their substantive truth or the caller's approval authority. Association keys absent from the capture are rejected. Omitting the file places all records in external discovery.

PPG evidence is linked, not fetched or copied; viewing links uses existing permissions. HTML escapes source labels and refuses non-HTTPS/credential-bearing evidence links. The source snapshot and caller-supplied observation time remain the authority for freshness, not output generation time.

## Remaining delivery

This is a local retained-record explorer, verified with fictional fixtures. No live CHHHS population or clinical usefulness is claimed. The DoRA local adapter below consumes retained source contracts; ANZCTR still needs an adapter against its existing accepted projection and access contract. The CHHHS clinical-study register still needs complete selected-source admission, genuine association review, coverage reconciliation and native reader acceptance. Online discovery, phase/site facets, cross-registry deduplication and saved interactive UI remain planned; no new collector, API, flow or Power BI page is installed. PPG requirements/evidence links need exact native keys and current NCTGF action/version mapping before operational use.

## DoRA activity adapter — 6 November 2026

The explorer also accepts `--dora-capture` with an existing `dora-activity-v1` receipt containing its `records` array. Supply the complete envelope's independent `--sha256`; omit `--observed-at` because the adapter uses the retained source timestamp. Receipt and source records may be combined locally from an existing capture without making another provider request. Existing complete schema/count/key/record-hash checks run before projection; absent hashes, failed or partial receipts fail closed.

```sh
.venv/bin/python -m scripts.study_explorer \
  --dora-capture private/ops/<retained-envelope>.json \
  --sha256 <independent-envelope-sha256> \
  --query diabetes \
  --output private/ops/<new-dora-study-view>
```

The minimal view retains resource-scoped row identity, source Project ID, title, source trial flag, dates, site label, disease category and provenance. It excludes investigator/contact details, descriptions and ethics/review references. Repeated Project IDs remain distinct rows. Numeric identifiers and year-only dates retain source scalar values rather than fabricated date precision. A DoRA trial flag does not establish interventional design, recruitment status, registry identity or CHHHS participation. A non-trial activity is not automatically a clinically scoped study. Source site text is retained as an assertion; only a separate reviewed association places a record in the CHHHS view.

Local retained-data replay used the existing 3 October capture:442 source records projected,0 reviewed CHHHS associations and442 discovery candidates. This is old selected-resource coverage, not current whole-DoRA coverage or a CHHHS trial census. Outputs/receipt remain in ignored private/ops/dora-study-preview-20261106. No source refresh, native admission, contact export or dashboard change occurred. A first real reviewed CHHHS link and authoritative cross-registry mapping remain required for operational use.

For an existing capture directory, `--dora-directory private/ops/<capture>` directly reads receipt.json and records.json; `--sha256` pins the receipt bytes, whose mandatory record/identity hashes then verify records.json. The adapter combines them only in memory, so no duplicate contact-bearing envelope is written. The result records both the receipt and combined-input hashes. This is the preferred route for existing local collector outputs.
