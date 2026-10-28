# CHHHS research publications: current web-first work package

Start with [START_HERE.md](START_HERE.md) and [the plugin opening prompt](handoff/POWERBI_PLUGIN_START_HERE.md). Ten new Conductor tracks prioritise the existing Power BI report and ordinary web UI. UTM/Desktop is conditional. No live report/model/VM changes are claimed by this release.

The earlier v0.3 source is preserved as a baseline with known defects; old deployment instructions below are historical, not the current route.

---

## Historical v0.3 source README

# CHHHS Research Publications

Project-owned software is licensed under [Apache-2.0](LICENSE), with scope and
third-party exclusions in [NOTICE](NOTICE). Source packages retain both files.

Browser-first Power BI/Fabric project for a monthly Cairns and Hinterland Hospital and Health Service publication report.

The canonical report combines **PubMed affiliation discovery** with the **Queensland Health DORA CHHHS RSS feed**, deduplicates cross-source records conservatively and retains source/attribution evidence.

Start with [START_HERE.md](START_HERE.md). For browser deployment without Power BI Desktop, use [docs/FABRIC_BROWSER_DEPLOYMENT.md](docs/FABRIC_BROWSER_DEPLOYMENT.md).

Core governance artefacts are in `contracts/`; implementation history and acceptance gates are in `conductor/`.


## Local Python and dependency setup

Use Python **3.15.1** (`.python-version`) for local preparation and CI. Microsoft
remains the deployed runtime. Do not replace an interpreter under an active
process: create a fresh environment and keep its path explicit.

```sh
uv python install 3.15.1 --no-bin
uv venv --python 3.15.1 .venv
.venv/bin/python -c 'import sys; assert sys.version_info[:3] == (3, 15, 1); print(sys.version)'
uv pip sync --python .venv/bin/python --require-hashes requirements-dev.txt
.venv/bin/python -m pip check
.venv/bin/python scripts/agent_harness.py check --task all
```

`requirements-dev.in` contains direct local preparation/quality dependencies;
`requirements-dev.txt` locks their entire resolved graph with hashes. The smaller
`requirements-source-ingestion.in`/`.txt` pair covers workbook parsing. Newest
compatible releases, including prereleases, are resolved in an isolated candidate
with `uv pip compile --python .venv/bin/python --prerelease allow --upgrade
--generate-hashes --universal requirements-dev.in -o requirements-dev.txt`.
Promote after exact-revision qualification. Pins are not deployment, native
acceptance, activation or email authority. The repo has no Node package manifest;
standalone native browser helpers use the separately qualified agent tooling.
