# Reviewed project relationships

The existing project-link journal and reader support project links to people,
ethics records, DoRA records and grant opportunities, alongside publications,
awards, datasets and software. Opportunities and awards are separate types.
The legacy field names `output_kind` and `output_id` are retained to preserve
existing journals, CLI inputs and report bindings.

## Admission and corrections

Use exact keys from the corresponding authoritative inventories. A person key
must resolve in the person inventory; an ethics key cannot resolve through that
person inventory even if its text happens to match. Names, titles, approximate
matches and source co-occurrence are not review evidence. A DoRA link means an
association with the specified record, not approval, funding or ethics clearance.
An opportunity link does not establish an award.

The original inventory shape remains valid:
`project`, `publication`, `award`, `dataset`, `software`.
To admit any broader type, supply the complete expanded shape with these four
additional inventories: `person`, `ethics`, `dora`, `opportunity`. Explicit empty
lists are allowed; omitted, duplicate, padded and unknown keys are rejected.
Old history entries retain their original inventories and hashes unchanged.

Each assertion retains the exact project/target IDs, evidence identity, evidence
revision and SHA-256, plus an explicit `candidate`, `reviewed` or `withdrawn`
disposition. The evidence must retain the actual review and its authority; a
caller-supplied status is not independent certification. The CLI does not invent
review evidence or resolve identity from an ORCID, author name or grant mention.

Use the existing paired-field intake:

```sh
/path/to/qualified/.venv/bin/python -m scripts.project_link_intake \
  --binding private/ops/<qualified-binding>.json \
  --target private/ops/<existing-project-link-target>.json \
  --input private/ops/<reviewed-revision>.json \
  --output private/ops/<new-immutable-occurrence> --apply
```

The input is the existing revision envelope: `record`, `inventories`, `complete`,
`revision_id`, `supersedes`, `reason`. `record` has `project_id`, `output_kind`,
`output_id`, `evidence_id`, `evidence_revision`, `evidence_sha256`, `status`.
Correct or withdraw using the current predecessor revision. Do not overwrite old
entries or change a lineage's target type. Exact replay is idempotent; stale forks,
conflicting revision IDs and edited stored projections stop before writing.
The guarded conditional store preserves unrelated outcome fields and never
retries a mutation. Use the retained workload renewal if its authentication
expires, rather than substituting a client or resetting another owner's session.

## Reader and acceptance

The existing project page shows the current reviewed bridge separately from the
all-disposition evidence audit. Its typed bridge accepts legacy and expanded
payloads, rejects unknown/missing legacy kinds, and retains distinct
project/type/target rows. One-direction project filtering remains unchanged;
there are no new joins into publication or grant facts and no multiplying totals.
Corrections replace only the current assertion; withdrawals leave audit history
and remove the current bridge entry.

2 November deployment changed only the existing bridge M source and relationship
page title. The existing native journal contains one fictional publication
candidate, zero reviewed links. It was read, validated against its stored
projection and preserved without writes. The retained source relationship
projection explicitly contains candidates; it was not reclassified as business
review. The 169 publication-reference candidates remain separate.

Technical support and native reader deployment do not establish actual reviewed
person/ethics/DoRA/grant links. Admission of those links remains open until exact
canonical inventories and genuine reviewed evidence are supplied. No new source
refresh, import restart, schedule change, email or NIH activation is part of this
feature. Native processing acceptance is recorded in the G08 review; CLI work
cannot establish visual rendering acceptance.
