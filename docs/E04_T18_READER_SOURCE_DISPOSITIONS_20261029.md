# E04/T18 reader source dispositions — 29 October 2026

This source-only packet addresses the ten inherited textbox-height warnings in
the retained current six-page E04 baseline. It makes no service or browser change
and does not repeat frozen parity, processing, export or baseline screenshot work.
The native import blocker and unchanged effect readback remain recorded in
[E04/T18 source evidence](E04_T18_SOURCE_PACKET_20261029.md).

## Bounded reader change

The maintained `scripts/prepare_dashboard_readable_layout.py` now offers
`--textbox-clearance` separately from its historical overview redesign. It requires
the exact six-page inventory and ten named textboxes, supported typography, an
expected complete bundle digest and a new output/manifest outside the source.
It fingerprints and transforms the same captured bytes, rejecting intervening
capture drift, missing/type/font changes, ambiguous padding, non-finite geometry,
canvas overflow and visual overlap before output creation.

On Sources, Monthly, Overview and Profile, each heading moves from y16/height48
to y0/height64; captions retain y64/height40. The Monthly footer retains y1016
and grows from32 to40. The Profile footer retains y960/height40. All ten receive
zero top/bottom padding; horizontal padding and every font size remain unchanged.
The largest retained heading font has a conservative one-line floor57 after
vertical padding removal; the other textboxes have floor35. These are CLI
heuristics, not measurements of wrapped text at runtime. No other page/visual
position, text, query, filter, order, control, theme or model binding is changed.
In particular, inherited Profile compliance/ANZSRC wording is not endorsed by
this geometry-only operation and remains a separate content correction.

The input for local qualification is the already prepared labels/theme candidate,
whose native save failed. The new mode adds no label/theme/import-property repair.
Its local output contains75 parts: ten changed files and65 untouched byte-exact;
19 JSON property differences comprise ten new default-padding objects (top/bottom
only), eight heading position fields and one footer height. Independent comparison
checks that exact whitelist. The original native preimage is preserved.

## Finite retained-source register

At source base `5a89454cf35041b46bb67decb891fbc6d19d4074`, this register covers22 retained Python paths selected by the explicit filename
families `*dashboard*.py`, `*publication*reader*.py`, `*reader*improvement*.py` and
`prepare_funding*layout*.py` in the preserved authoring checkout's `scripts/`.
It is a bounded E04/T18 source comparison, not a claim to reconcile every file in
the private authoring history. Earlier packet manifests retain other imported
helper/test/contract closure. Each row gives the retained file's SHA256 prefix;
full before/current hashes and dispositions are retained privately in
`private/ops/e04-textbox-source-20261029/retained-source-inventory.json`.
Retained-only files are not silently copied, deleted or treated as implemented.

| Retained script | Current source / retained SHA256 prefix | Finite disposition |
| --- | --- | --- |
| `dashboard_metrics.py` | qualified source differs; `7413a8aaaf5d` | Keep qualified per-horizon origin/type guards; do not restore the retained weaker forecast gate. |
| `dashboard_researchers.py` | exact retained bytes; `be87a4be04e1` | Keep canonical provider-ID source projection; names are unresolved labels, not person identity. |
| `dashboard_topics.py` | exact retained bytes; `a63df463c4c0` | Keep taxonomy, provenance and exact canonical-key constraints; no new acquisition. |
| `prepare_dashboard_accessibility.py` | qualified source differs; `07893d65950b` | Keep historical nine-page helper; do not apply it wholesale to the current six pages. Bounded clearance uses the maintained layout builder below. |
| `prepare_dashboard_dataset_consumers.py` | retained only; `4fb4e04da5b1` | Defer outside this lane: shared model/table consumers require the model owner and exact contract/loading qualification. |
| `prepare_dashboard_funding_layout.py` | retained only; `ceb89f9fc89a` | Defer a separate reader packet: adds detail/context visuals and field selections, rather than just clearance. Needs complete pre-output guards, contract parity and empty/selection/detail tests first. |
| `prepare_dashboard_model_metrics.py` | exact retained bytes; `7508300f23b6` | Keep existing metric builder and governed denominators; no model or DAX edits assigned. |
| `prepare_dashboard_overview.py` | qualified source differs; `138045794582` | Keep canonical drift/duplicate protections and historical inventory guard; do not replace with retained raw source. |
| `prepare_dashboard_profile_wording.py` | exact retained bytes; `a7094842d75f` | Keep source-backed assessed-OA/trial-type/funding wording candidate. Substantive native correction and coverage display remain separate. |
| `prepare_dashboard_readable_layout.py` | qualified source differs; `e8eb05cadc8c` | Amend here with the bounded ten-textbox six-page mode; keep historical overview redesign separate. |
| `prepare_dashboard_reader_increment.py` | exact retained bytes; `398defb9ed91` | Keep exact direct-field label mapping and refusal to infer aggregate labels; no native replay. |
| `prepare_dashboard_relationship_summary.py` | retained only; `3c18e4294291` | Defer separate reader packet: adds a page with relationship summaries. Requires current model consumer contract and typed evidence parity; no inferred relationships. |
| `prepare_dashboard_source_freshness.py` | retained only; `00755b61c7bb` | Defer with its relationship-summary dependency: new page/consumer fields need explicit observation-versus-processing semantics and complete source tests. |
| `prepare_dashboard_theme_identity.py` | exact retained bytes; `10682d66f246` | Keep the bounded registered-theme identity repair; its prepared candidate is not a successful save. |
| `prepare_dashboard_topic_model.py` | exact retained bytes; `86a75814f447` | Keep canonical additive topic builder; loading/processing remains a model-owner/native gate. |
| `prepare_existing_reader_improvements.py` | retained only; `77baf2b8f2b3` | Do not migrate this legacy-format/filter layout into the current PBIR reader. Preserve as historical source; current reader builders remain authoritative. |
| `prepare_publication_outcome_reader.py` | qualified source differs; `58d0af4924b6` | Keep canonical envelope/type/duplicate guards and existing outcome contracts; no fabricated outcome records. |
| `prepare_publication_reader_recovery.py` | retained only; `68a10ba2cd99` | Defer outside this lane: model-table recovery must not rebuild the accepted frozen baseline or imply report-definition restore. |
| `prepare_publication_reader_theme.py` | qualified source differs; `a442bca51b6f` | Keep qualified dark-theme preservation. Current target, dark clipping and rendered acceptance remain unresolved. |
| `prepare_publication_versioned_reader.py` | qualified source differs; `019c0e173802` | Keep versioned source reader and existing identities; no replacement report or baseline replay. |
| `prepare_windows_dashboard.py` | retained only; `50682cc5c414` | Do not adopt a legacy Windows/conversion route as an import workaround. Retain historically; no supported recovery qualification for this exact PBIR/property follows. |
| `qualify_dashboard_topic_snapshot.py` | qualified source differs; `9c5b288dd7c4` | Keep repaired completeness/envelope/type qualification; retained captures prove only their frozen scope. |

## Qualification and exact residual dependencies

The exact affected selection passed12 tests on Python3.15.1:
`python -m unittest tests.test_dashboard_readable_layout tests.test_prepare_dashboard_reader_increment`
(using the explicitly verified repo-local interpreter). Focused fictional tests cover allowed-change-only preservation, unchanged input
and binary resources, idempotent preparation, missing/font/selector/page drift,
overlap/overflow/non-finite rejection, complete-hash and existing-manifest guards,
intervening capture drift and implicit horizontal padding. They do not query a
service or manufacture operational data. Existing reader-increment tests remain
part of the affected selection. Python3.15.1 is selected explicitly; no dependency,
runtime, shared model/DAX contract, handoff or track file changes occur.

CLI0.5.0 validation of the local75-part candidate reports zero errors and two
`PBIR_SCHEMA_UNREACHABLE` warnings. All ten inherited textbox-height warnings are
absent. Exact report3.4.0 and visualContainer2.14.0 schema coverage remains missing;
zero local errors cannot overturn the observed native import rejection of the
unchanged `linguisticSchemaSyncVersion` property. No pack or upload is performed
for this source-only candidate. Candidate, manifest, normal CLI validation and
independent scope verification remain private under the evidence directory above.

Remaining acceptance dependencies are finite and distinct:

1. E04 needs authoritative exact-version export/import semantics and a qualified
   bounded report-definition recovery route before any newly scoped save.
2. After that gate, a fresh sole-writer full preimage/drift check, exact intended
   save/readback, inverse and separately guarded final reapplication are required.
3. Actual all-six-page light/dark rendering at1280×720,1366×768 and1920×1080,
   zoom/wrapping/long-label, keyboard/focus and clipping checks remain open.
   The local floor/overlap results close only source geometry preparation.
4. T18 current-target identification remains unresolved: its exact retained ID
   returned404 and neither bounded assigned inventory matched it. Do not select
   another report from a shared model or historical sidebar name. Retained
   slice-1 parity/export acceptance is reused; target-specific dark clipping,
   reader journeys, five same-host timing observations, strict warm budgets and
   maintained-source/report restore qualification remain open.
5. Canonical metric denominators, provider-ID identity, taxonomy coverage and
   forecast suppression criteria remain unchanged. Forecasts require contiguous
   complete acquisition coverage, ten training years and five origins per scored
   horizon, plus qualification/interval/native display gates. No synthetic outcome,
   missing-as-zero, provider-metric sum or model-deployment claim is introduced.
