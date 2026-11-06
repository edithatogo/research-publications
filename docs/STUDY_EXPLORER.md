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

## Reviewed evidence in the study view

`--reviewed-evidence <private-packet.json>` and `--reviewed-evidence-sha256 <independent-hash>` integrate a reviewed association/registry packet into DoRA views. This replaces `--associations` for that invocation and requires `--dora-directory`, so the original receipt bytes are independently pinned. Reviewed evidence with `--dora-capture` is refused; the older envelope-only route remains available without reviewed evidence. Real packets and populated outputs remain private, not source fixtures or public datasets.

The packet contains schema_version1, the exact combined capture_sha256, review_id/scope, existing associations, association_evidence keyed by source key, and registry_decisions. Site evidence retains the original field/value/time, receipt and facility-contract hashes and matched facility keys. Each registry decision has a qualified key/URL, confirmed or candidate disposition, review basis/scope, corroboration, source differences, and a pinned local registry payload/locator/snapshot/update assertion. The reader verifies the payload bytes, registry identity and source update metadata; it does not re-adjudicate the review or infer identity from titles.

Validation checks the full capture domain before filtering and refuses stale capture/packet/payload hashes, absent source/registry keys, changed site assertions, duplicate/conflicting decisions and inconsistent metadata. Candidates never become confirmed links. The HTML shows source-reported site context, reviewed identity links versus unconfirmed candidates, and expandable evidence/difference notes; JSON retains the structured evidence. Full unselected review decisions remain in the hash-pinned input packet. No source field is overwritten, and a registry identity match does not confirm a local conducting site.

The user-selected retained view now contains11 source-reported CHHHS studies among442 records, with one reviewed trial identity link and one unconfirmed topic-based candidate. The selected private packet and generated view are recorded in the existing five-area Conductor amendment. This is local reader integration only; it does not admit records to SharePoint, change model/report definitions, establish current recruitment/activity or remove the other431 records.

## Maintain the registry from DoRA

Use the existing collector for a new isolated local observation, then reconcile it against the accepted capture and review packet. Existing native acquisition flows are separate. The source scope remains the selected active public datastore resource, not every historical DoRA resource or a clinical-study census.

```sh
.venv/bin/python scripts/dora_activity.py private/ops/<new-capture>
.venv/bin/python -m scripts.refresh_study_registry \
  --previous-directory private/ops/<accepted-capture> \
  --previous-receipt-sha256 <accepted-original-receipt-sha256> \
  --current-directory private/ops/<new-capture> \
  --current-receipt-sha256 <new-original-receipt-sha256> \
  --reviewed-evidence private/ops/<accepted-review>.json \
  --reviewed-evidence-sha256 <accepted-review-sha256> \
  --facilities config/facilities.json --facilities-sha256 <pinned-facility-contract-sha256> \
  --revision-id <new-explicit-revision> \
  --output private/ops/<new-registry-generation>
```

Reuse an already accepted capture rather than collect again when its observation is sufficient. Receipt bytes and the complete record/identity hashes are verified through the same directory reader as the study explorer. Observations older than the previous capture and changed source scope/schema are rejected. Compare full source records using resource-scoped row keys, not Project ID or title. Full record changes invalidate automatic review reuse, including changes outside the minimal display projection. A changed facility-reference pin also requires association review.

Unchanged same-resource rows may reuse their existing associations, registry decisions and PPG references. The new packet records the previous capture/review hashes and original review identity; advancing the DoRA observation never renews registry or PPG timestamps. New/changed rows remain candidates needing review. Source-missing rows retain prior projected history and quarantined decisions; missing from one snapshot never means study closure or deletion. Replacement resources require explicit crosswalk/review even when row numbers, Project IDs or titles match. Candidate facility-name matches are review hints only.

Outputs are next-reviewed-evidence.json, the complete current-source study view, reconciliation.json, review-queue.json, quarantined-review.json and a commit-last maintenance-manifest.json with every artifact hash/length. Only a generation with its final manifest and successful verification is complete. No existing output or capture is overwritten, and no native selector is changed. On failure, keep the last accepted generation; inspect the specific source/contract/evidence failure before proceeding. Identical replay keeps the original review bytes and identity. Use the next packet's manifest hash and the current capture as inputs to the next cycle.

## Versioned PPG evidence references

Review packet version1 remains supported. Version2 adds ppg_references and refresh_lineage. References use the existing PPG retrieved-source identity/version contract: sourceId, canonicalUrl, retrievedAtUtc, nativeUniqueId, nativeVersionRef, sha256, authorityLabel and status. PPG defines sha256 as extracted UTF-8 text, not original Office/PDF bytes. RIMS stores these metadata only, never evidence text, quotes or documents.

Each reference also supplies source_key, frameworkKey, requirementKey and relationshipScope (study or service). This preserves the distinction between service-level governance evidence and study-specific evidence. Only a retrieved receipt with a nonempty native version and explicit PPG authority label is accepted. Denied/missing/unsupported sources cannot supply reference metadata. The stored receipt does not prove current access, current authority or compliance; the native destination applies its existing access controls when opened.

To attach user-selected, already retrieved PPG references during reconciliation, provide `--ppg-references <private-reference-array.json>` and `--ppg-references-sha256 <independent-hash>`. Additions require unchanged reviewed CHHHS associations. Identical references are reused; conflicting metadata for the same requirement/source/version refuses the operation. New source versions remain separate references rather than silently replacing an old version. For changed study identity or corrections/withdrawals, preserve old packets and explicitly review the new mapping instead of modifying history. Newly selected PPG evidence retains its own retrieval time; it is not made current by a DoRA refresh.

No verified study-specific PPG receipts were supplied for the current registry. The refreshed view explicitly reports zero versioned PPG evidence references. Exact NCTGF framework/action/version keys and real PPG source receipts remain inputs from the existing workbench owner; no identifiers, links or clinical evidence are invented. This local reference projection has fictional contract tests, not a native PPG integration/permission certificate.
