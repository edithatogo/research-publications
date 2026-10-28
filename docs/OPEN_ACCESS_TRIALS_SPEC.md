# Open Access evidence and clinical trial linkage specification

## Current source correction — 29 October 2026

An explicit provider category describes an access route; it is not a policy
compliance decision. The local classifier returns the existing category vocabulary
only for exact known labels, keeps contradictory inputs unknown, and emits
`Unknown` for new `OAComplianceNHMRC` values. A licence string or general open flag
does not establish Gold, Hybrid or Green. Existing recorded category/compliance
values and human notes are preserved; no native records or measure names are
rewritten. Historical auto-generated values require provenance review before use
as compliance evidence, not automatic replacement.

The current [NHMRC and MRFF Open Science Policy](https://www.nhmrc.gov.au/about-us/resources/nhmrc-and-mrff-open-science-policy)
distinguishes access timing, publication version and licence requirements. A
selected assessment additionally needs applicable funding/policy scope and dated
source evidence. This source function does not collect or adjudicate those facts.
Archived category-to-compliance tables are historical and superseded for execution.

The public function signature, tuple shape, field names and category values are
unchanged. `batch_enrich_sources.py` still exports the same columns. New records
keep compliance unknown; existing populated records retain their exact values.
There is no native migration or alteration of existing `[Open Access Rate]` or
T18 assessed-status/coverage measures. No report should label an OA-category ratio
as policy compliance without a separately qualified assessment contract.

Validation: regression tests first reproduced unsupported positive/negative
compliance, licence-derived routes and overwritten recorded values. Focused
classification/enrichment and dependent batch tests verify the correction.

---

## 2. Clinical Trial Registry Linkages

Clinical research governance requires linking peer-reviewed publications to registered clinical trials to monitor translation and prevent publication bias.

### Registry Matching Rules
1. **ANZCTR (Australian New Zealand Clinical Trials Registry):**
   - Pattern: `ACTRN\d{14}`
   - Resolver: `https://www.anzctr.org.au/Trial/Registration/TrialReview.aspx?id={id}`
2. **ClinicalTrials.gov:**
   - Pattern: `NCT\d{8}`
   - Resolver: `https://clinicaltrials.gov/study/{id}`

### Schema Columns for SharePoint List
- `OACategory`: Choice (`Gold`, `Hybrid`, `Green`, `Bronze`, `Closed`)
- `OALicense`: Single line of text (e.g. `CC-BY 4.0`)
- `OAUrl`: Hyperlink (Direct link to open version / PDF)
- `TrialRegistryID`: Single line of text (e.g. `ACTRN12621000123456`)
- `TrialRegistryURL`: Hyperlink (Link to registry trial record)
