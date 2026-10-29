# Offline source route preparation

The historical solution has15 flows containing46 generic HTTP actions. Those
definitions remain held under the current Standard-only Power Automate decision.
Successful historical runs do not establish Premium entitlement. The replacement
acquisition route is an assisted, source-specific CLI capture or reuse of the
complete retained archive. No provider request, native save, run, activation or
schedule change was performed during this preparation.

## Implemented scope repairs

Three new CLI entry points reuse the existing bounded read transport, private
create-only storage and manifest-last receipts. They default to offline
validation/help; provider reads require an explicit `--capture` argument.

- `capture_discovery_source.py`: Crossref affiliation discovery and the complete
  maintained ClinicalTrials query. It preserves query parameters, full records
  and original responses; requires two matching complete reads, exact totals,
  terminal pagination and stable ClinicalTrials API/data version. Crossref uses
  explicit immutable created-date bounds. Exact-ID collectors remain necessary
  for supplementary retained DOI/NCT inputs; discovery does not replace them.
- `capture_ckan_source.py`: every resource in the complete QGIP agency index, or
  the maintained current DoRA activity resource. It retains index, resource,
  package, schema and every original page before selection. Two complete reads
  and stable source metadata are required. Records retain the resource-plus-row
  identity and every field. The existing QGIP enabled-policy gate remains; its
  current disabled setting was not changed.
- `capture_official_workbooks.py`: every advertised NHMRC/MRFF workbook, including
  historical vintages. It retains source/copyright pages and original binaries,
  checks ZIP integrity, repeated-byte equality and the complete link inventory.
  Unsupported tabular links fail preparation rather than being silently omitted.

All three retain failed response bodies and failure receipts, default to one
request attempt, bound bytes/pages/records, refuse overwritten generations and
leave native/canonical admission false. Local completion is not fresh provider,
scheduled, native storage or downstream-consumer acceptance.

Offline entry-point checks (no provider request):

```sh
.venv/bin/python -m scripts.capture_discovery_source --scope private/ops/source-integration-offline-20261030/clinicaltrials-discovery-scope.json
.venv/bin/python -m scripts.capture_ckan_source --source qgip
.venv/bin/python -m scripts.capture_official_workbooks --source nhmrc
```

## Disposition of all15 held definitions

| Historical flow | Permitted preparation route | Remaining package boundary |
| --- | --- | --- |
| Crossref isolated batch qualifier | Preserve its completed qualification receipt | No replacement deployment selected; not a permanent collector |
| QGIP source collection | New complete-agency CKAN capture | Enabled policy remains false; freeze full resource inventory and native consumer mapping |
| Funding test machine endpoints | Preserve historical diagnostic definition | No replacement deployment selected; do not run a diagnostic as a source collector |
| ClinicalTrials source collection | New broad discovery plus existing `clinicaltrials_source.py` supplementary exact IDs | Frozen discovery query retained verbatim; bind the six retained supplementary IDs and complete archive generation |
| ARC award collection | Existing `grants_arc_api.py` complete two-pass capture | Reuse source policy, raw snapshots and award grain; private-fixture skips are not parity proof |
| DoRA activity collection | New complete CKAN capture | Freeze source resource and native activity consumer mapping; never treat activity rows as publications |
| NHMRC workbook collection | New all-vintage capture or verified retained14-workbook archive | Raw package prepared; bind the existing archive destination and selected consumer generation |
| MRFF workbook collection | New all-workbook capture or verified retained three-workbook archive | Raw package prepared; preserve awards, summary and rates as different file kinds |
| Open-access paper archive | Existing retained-paper metadata preparation and accepted originals | Raw paper eligibility, exact original-file inventory and consumer mapping remain to be frozen; legacy downloader presence is not route qualification |
| ROR organisation collection | Verified retained complete official release | Raw package prepared; preserve release identity and complete dump before country filtering |
| DataCite related outputs | Existing `datacite_source.py` complete related-identifier queries | Freeze exact publication DOI scope and native relationship-consumer mapping |
| PubMed source collection | Existing `collect_pubmed.py`, or retained accepted generation | Preserve full search/raw XML coverage and shared rate ownership; no newer identities acquired |
| DoRA publication collection | Existing `collect_dora_history.py`, or retained accepted generation | Preserve full collection/metadata pages and accepted identity scope |
| Crossref notice collection | New full discovery plus existing `crossref_source.py` exact DOI capture | Freeze all hedge queries, cutoff/partitions and supplementary DOI scope; no exact-ID-only substitution |
| ARDC identifier collection | Existing retained OAI archive reader/capture pipeline | Pin complete baseline/increment manifests and source-generation lineage; existing native owner retains in-flight work |

## Frozen artifacts and checks

Private artifacts are under the integrator's
`private/ops/source-integration-offline-20261030/`:

- `clinicaltrials-discovery-scope.json` preserves the historical query exactly.
- `retained-assets/nhmrc.zip` retains14 workbooks and original manifests. Every
  workbook matches its captured SHA256/length and saved native-download bytes;
  the URL set matches the frozen23October landing page. The earlier one-file
  coverage hold is explicitly superseded, not silently deleted.
- `retained-assets/mrff.zip` retains all three advertised workbooks, source page,
  copyright page and original receipt. Hashes, lengths and ZIP integrity pass.
- `retained-assets/ror.zip` retains the complete official release, metadata and
  original receipt. SHA256, publisher MD5 and ZIP CRC checks pass. No selective
  country projection is relabelled as the full release.

The packages preserve original observation dates; packaging is not a new source
observation. Native bindings and private raw content remain outside Git.

The31 focused tests cover the new routes and existing exact-ID complements with
fictional injected transport. They include missing/estimated/changing totals,
duplicates, pagination, full-field drift, version changes, byte limits, failed
responses, disabled policy and historical-vintage retention. No platform tests
were performed. The canonical-output package is described separately in
[Canonical unattended output](CANONICAL_UNATTENDED_OUTPUT.md).

## Completion boundary

This batch repairs six source acquisition implementations and prepares three
complete retained raw-asset bundles. It does **not** yet make all15 historical
flow definitions deployment-ready. The remaining offline work is exact
archive-to-consumer packaging for the selected generations, including the
supplementary identifier scopes and immutable staging manifests. Keep generic
HTTP definitions held and platform testing deferred until that preparation is
complete. Then perform one coordinated exact-target preflight and only the
changed saved-definition/output/replay checks, reusing unchanged receipts.
