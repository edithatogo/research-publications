# Forecast dependency qualification — 29 October 2026

The isolated repository-local Python3.15.1 environment passes exact installed
version checks for42 pinned distributions, `pip check`, offline Chronos2Pipeline
import and an actual PyTorch CPU tensor operation. Chronos forecasting2.3.2,
PyTorch2.15.0 and Transformers5.21.0 load together without replacing the shared
repository environment. Socket connections were disabled for the import/tensor
probe. No model weights or real research data were used.

This qualifies the dependency/import prerequisite only. It does not qualify
Chronos-2 model loading or inference, model weights/revision, scientific accuracy,
interval calibration, native deployment or forecast selection. No real-data
benchmark or forecast is presented. The all-collection coverage, frozen annual
keys/generation, baseline and rolling-origin requirements remain open; the native
writer hold remains. No dependency/runtime promotion is made by this record.

## Installation evidence and corrections

- The official [PyTorch release documentation](https://pytorch.org/blog/pytorch-2-14-release-blog/)
  documents Python3.15 wheels on the PyTorch download index. The actual index
  resolved2.15.0 for this platform; lack of packages in the shared environment
  was not treated as proof of incompatibility.
- [Chronos forecasting2.3.2](https://pypi.org/project/chronos-forecasting/2.3.2/)
  and all transitive dependencies were resolved and pinned by exact artifact
  URL/SHA256. Installation enforced hashes with no dependency re-resolution and
  zero automatic network retries.
- Binary-only resolution failed because PyYAML lacked a matching wheel. The
  supported6.0.3 source distribution built locally on3.15.1. Its installed
  pure-Python implementation passes a safe YAML round trip; the optional C
  extension is absent. No downgrade or ABI compatibility bypass was used.
- One PyTorch mirror artifact lacked a hash in pip's report. Its exact filename
  and downloaded bytes matched the corresponding PyPI release SHA256 before it
  entered the lock. The mirror's R2 wheel URL was verified against its official
  PyTorch index.
- A read-only import probe began before installation completed and failed on
  absent NumPy. It is retained as a premature diagnostic, not accepted evidence.
  The install was neither interrupted nor restarted; a new probe ran after its
  terminal successful exit. All42 installed versions then matched the pins.

## Ownership and evidence

This source record belongs to chat `01a17f83-9384-75b3-b9fa-167ae2befc4c`, branch
`codex/conductor-goal-source`, in its app-managed worktree. The shared dirty
checkout was not copied, reset, cleaned or staged. Earlier owned source evidence
stays at its existing paths; private bindings, journals and authentication remain
with their native owners.

Ignored evidence and the isolated environment remain in the original checkout's
`private/ops/2026-10-29-e04-forecast-runtime/`: resolver reports,42-artifact lock,
source/mirror metadata, install log, terminal `pip check`, offline import/tensor
receipt and `dependency-acceptance.json`. No native object, schedule, email,
sharing, capacity, hook or shared runtime was changed.

## Conductor review

Plan compliance is partial for E04-P11 and complete for this dependency slice.
The scientific evaluation and native acceptance gates remain explicit. Review
corrected the binary-only PyYAML assumption, required the missing artifact hash,
and excluded the premature probe. Validation consists of actual isolated runtime
execution and exact installed-pin/readback checks. No project source code changed;
unchanged project tests are not rerun or represented as inference evidence.
