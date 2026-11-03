# Offline repository privacy guard

This repository is intentionally PUBLIC under the current user direction. The
local pre-push guard verifies the exact approved repository and current PUBLIC
visibility; it never changes visibility. Public hosting does not approve personal,
clinical, operational or credential data for publication. CareOps' separate parent
policy remains PRIVATE.

The frozen installed worker checks outgoing committed text, filenames and commit
messages, including intermediate added-then-deleted blobs. Gitleaks8.30.1 checks
the same outgoing commit set and staged additions. Binary documents, notebooks and
unknown encodings need an exact path/SHA-256/content-review approval; changed bytes
invalidate it. Existing installed hooks are retained and chained with redacted
output. Existing source CI and pre-commit configuration remain unchanged.

Local selection excludes only branches actually advertised by the approved remote
whose commit objects exist locally. Those baseline objects are already public,
not newly approved. CI uses an explicit fetched commit base. This is prevention
for outgoing changes, not a full legacy/history disclosure assessment. Existing
full-history security jobs, where present, remain independent and unchanged.
No legacy baseline, directory exemption or historical approval is imported.

## Setup in each actual checkout

Use an explicitly verified Python3.15.1 helper environment; create only absent
environments and preserve active application/native work:

```sh
test ! -e .venv-privacy-hooks
test ! -e .venv-privacy-presidio
uv venv --python 3.15.1 .venv-privacy-hooks
uv venv --python 3.15.1 .venv-privacy-presidio
uv pip sync --python .venv-privacy-presidio/bin/python --require-hashes .privacy-guard/requirements-presidio.lock
.venv-privacy-hooks/bin/python -I -m unittest discover -s .privacy-guard -p 'test_*.py'
.venv-privacy-presidio/bin/python -I .privacy-guard/qualify_presidio.py
.venv-privacy-hooks/bin/python -I .privacy-guard/install_hooks.py
```

The installer requires the qualified helper prefix, inspects actual hook ownership,
saves any executable predecessors, snapshots reviewed code/policy and reads back
installed hashes. A changed owner, symlink or unsupported hooksPath stops it.
It does not override hooksPath or touch another clone. This delivery's installed
hooks apply to its isolated canonical clone/worktree; old native checkouts need
an explicit owner-qualified adoption, not an implied installation claim.
Each linked checkout needs its own scanner environment; missing models block push.
Keep ordinary hooks enabled; do not use direct API uploads or hook overrides to
avoid a refusal. New checkouts need this deliberate installation.

The analyzer uses the normal packaged English model with network calls prohibited.
Missing/drifted models and unsupported dependency metadata refuse the operation.
The qualified released analyzer2.2.359 admits Python3.15.1; later examined releases
exclude3.15. The dependency/model hashes are locked. Do not override metadata,
substitute a tokenizer or replace NLP with regex. Keep dependency/model licences
and the bundled source LICENSE/NOTICE. Upgrades require focused qualification.

## Review and scope

Keep raw findings and source preimages in ignored local receipts. A detector
candidate is not a confirmed disclosure. Remove genuine sensitive content; review
a demonstrable technical false positive only at exact policy/blob/entity/span/
value scope in presidio-reviewed-findings.json with a substantive reason/reviewer.
A changed path, byte, policy or match invalidates that review. Document approval
is separate and requires inspecting actual content; no document is approved here.
The installed snapshot must be deliberately promoted after an authorised review.
Only schema-validated numeric offsets/ranks in that exact review control artifact
are treated as control metadata when misclassified as phones. Its free text, other
JSON files and genuine identifier values receive no such exemption.

Failures print fixed messages only. A generic local macOS notification never
permits transfer if it fails. CI uses read-only credentials and the same worker;
it posts no raw comments or findings artifacts. It is an after-upload backstop,
not local prevention. CI success does not itself establish protected-branch
requirements or installation in another checkout.

Submodules, existing public history, author/ref metadata, releases, external
copies, confidential non-PII and non-Git upload routes need their own review.
The worker does not OCR documents or prove complete identity detection. Native
bindings, active imports, existing outputs, authentication profiles and email
approval gates retain their owners. No email, tenant mutation, Google key test,
credential deletion or history rewrite is part of this source setup.
