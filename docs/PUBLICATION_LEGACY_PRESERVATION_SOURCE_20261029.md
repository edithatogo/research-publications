# Publication legacy preservation: offline source packet

Date: 29 October 2026. Source base: `632224327b00b1f8794a32c93c346a31a1d1bb15`.

This packet implements the fourteen retained files identified as
`retained_legacy_preservation_packet` in
`audit/publication-source-disposition-20261029.json`. It is an offline evidence
assessment packet. It performs no native reads, restores, deletions, schema
changes or row writes, and creates no native write payloads.

## File dispositions

Each retained helper and its paired test is implemented in this packet:

| Helper under scripts/ | Paired file under tests/ |
| --- | --- |
| build_publication_stub_preservation_ledger.py | test_build_publication_stub_preservation_ledger.py |
| match_publication_stub_actions.py | test_match_publication_stub_actions.py |
| plan_publication_stub_restore.py | test_publication_stub_restore.py |
| preflight_publication_key_migration.py | test_preflight_publication_key_migration.py |
| reconcile_publication_stub_disposition.py | test_reconcile_publication_stub_disposition.py |
| reconcile_publication_stub_version_pagination.py | test_reconcile_publication_stub_version_pagination.py |
| rehearse_publication_stub_restore.py | test_rehearse_publication_stub_restore.py |

The helpers reuse canonical integer, UTC and key-set validation. There is no new
native driver or general preservation framework. The original 64 test methods
remain, with fixtures adapted to explicit evidence requirements; 21 additional
methods exercise the changed behavior.

## Evidence contract

Cohort coverage comes from supplied complete, unpaged inventories and exact
counts. Duplicate IDs, boolean counts, padded identities, inconsistent aliases,
missing schema metadata and ambiguous current-version markers fail validation.
Raw values, human edits, exact returned IDs, provenance and unresolved origins
remain intact. Unknown dates produce gaps rather than invented timestamps.

The ledger requires a complete field inventory receipt with source identity,
field count, canonical field digest and captured artifact SHA-256. Its CLI also
checks the captured field bytes. Coverage includes every selected visible,
noncomputed scalar field, including fields outside the historical fixed range.
An explicit, complete field-to-native-version-property map is required; property
names are not guessed. Field visibility is not permission to write.

Saved native version pages must have verified bytes, complete pagination chains,
unique labels and exactly one explicit current marker. Current version values
must match current item values. Attachment collections and saved attachment
bytes are checked independently. Missing older fields and competing historical
values remain diagnostic gaps; populated current values are never overwritten.

The planner requires caller-supplied aware UTC time and a governed freshness
policy containing `policy_id`, `evidence_ref`, `max_age_hours`, `max_skew_hours`,
`max_context_skew_hours` and `max_review_age_hours`. Its CLI requires
`--as-of-utc` and `--freshness-policy`. Evidence-complete candidates are reported
separately from authority: restore-ready counts remain zero and write payloads
remain null. Legacy readiness claims are diagnostic only. Key migration
preflight also leaves mutation and schema-change authority false.

All CLI input/output paths are confined to ignored `private/ops` storage.
Outputs are new, exclusive-create receipts; inputs and existing receipts cannot
be overwritten. Relative capture paths must remain inside their capture root,
and symlink escapes and altered hashes fail validation. Pure helper functions
copy inputs before processing.

## Historical evidence and native dependencies

The saved 28 October receipt describing 303 retained items, 301 exact Create
returns and two unresolved origins is historical evidence reused by reference.
It was not recaptured or replayed by this packet. Its stronger blank-create
shapes covered 100 items and do not establish the other 203. Its saved version
and attachment observations do not establish current native state. No current
303-item coverage or live acceptance is claimed.

Any later native proposal needs exact current list/item identity, GUID and ETag;
a complete typed field inventory and explicit native version-property map;
complete current and older version captures with pagination and immutable hashes;
and attachment metadata plus captured-byte hashes. Exact action returns may
establish provenance for individual items; unresolved origins remain unresolved.
It also needs fresh, governed evidence for retention, holds, labels, records,
permissions and responsible human disposition, plus explicit authorization and
an exercised recovery route preserving the required identity and history.
Ordinary item recreation does not preserve original IDs, system audit values or
version history. Read/manage access alone does not grant disposal authority.

## Verification

The existing repo-local interpreter reports Python 3.15.1. Focused unittest
discovery ran all 85 methods successfully, with synthetic fixtures and no private
fixture skips. The synthetic pipeline exercises matching, historical rehearsal,
planning and disposition reconciliation while retaining zero restore authority.
Tests cover changed field coverage, receipt hashes, pagination, attachment bytes,
unknown dates, immutable inputs, strict identities and create-only outputs.

```sh
.venv/bin/python - <<'PY'
import unittest
suite = unittest.defaultTestLoader.discover('tests', pattern='test_*stub*.py')
suite.addTests(unittest.defaultTestLoader.loadTestsFromName(
    'tests.test_preflight_publication_key_migration'))
result = unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(not result.wasSuccessful())
PY
```

This is focused source verification. Native behavior, preservation acceptance,
restoration, disposition and scheduled operation remain unverified and
unauthorized by this packet. Shared contracts, dependency/runtime files,
coordination handoffs and historical audit inventories are outside its scope.
