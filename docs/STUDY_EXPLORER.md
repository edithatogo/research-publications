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

This is a local retained-record explorer, verified with fictional fixtures. No live CHHHS population or clinical usefulness is claimed. DoRA/ANZCTR adapters must consume existing accepted projections and their field/access contracts before inclusion. The CHHHS clinical-study register still needs complete selected-source admission, genuine association review, coverage reconciliation and native reader acceptance. Online discovery, phase/site facets, cross-registry deduplication and saved interactive UI remain planned; no new collector, API, flow or Power BI page is installed. PPG requirements/evidence links need exact native keys and current NCTGF action/version mapping before operational use.
