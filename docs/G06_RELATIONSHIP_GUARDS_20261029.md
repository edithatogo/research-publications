# Relationship guard source closure — 29 October 2026

Grants delivery chat `01a1831e-cc6d-7371-9d57-021a339b708a` owns only
`scripts/grants_relationships.py`, its directly paired tests and this leaf
handoff for this packet, under sole integrator
`01a182f2-fd8e-7953-9bd2-f9b8002664a6`. The app-managed checkout remains
`/Users/doughnut/.codex/worktrees/ef45/chhhs-research-publications`, branch
`codex/rims-grants-roadmap`, packet base
`70befec638ac73fabfd50fd8709c538a1109d04a`. Native scope is empty.

The retained namespace, alias-duplicate and candidate-affiliation guards are
migrated semantically, preserving canonical reviewed/withdrawn/source-key,
duplicate/orphan and typed relationship identity rules. Award links require the
existing `AWARD:<funder>:<id>` syntax. Source-key namespace and supplied funder
namespace must agree. Legacy single labels and `FUNDER:<namespace>` compare
case-insensitively only to detect disagreement/duplicate ambiguity; no key is
rewritten, no funder identity is adjudicated and no source is merged.

Multiple supplied affiliation targets reject candidate as well as confirmed
links. A single resolved candidate remains candidate/Needs Review. Alias-aware
same-award ambiguity rejects rather than selecting a winner; the same award
number under distinct funder namespaces remains separate. The retained five
test cases reproduced seven failures before repair. Two additional regressions
prove candidate preservation and a fixed existing relationship key remains exact.

All53 relationship/schema tests pass on the existing repo-local Python3.15.1.
No native list/model, authoritative source identity, review status, publication
record, shared contract, runtime, schedule, authentication or delivery changed.
G06 still needs authoritative key/funder/identity review, assigned native bridge
and cardinality proof, then reviewed correction/withdrawal/recovery. The latest
source-only reconciliation manifest remains a frozen prior-packet snapshot;
it is not edited as a shared status record here.

## Preference/ledger compatibility decision

Do not import the retained planner/ledger change as a default-key replacement.
The current canonical planner's six-part typed tuple is compact-JSON hashed to
`EVENT:` plus24 hex characters. The retained planner instead base64-encodes that
six-part tuple. The live worker encodes a seven-part tuple that includes
DeadlineKey; its operational alert has a distinct four-part system identity.
All share EVENT: without a version discriminator. Dry-run SQLite stores
identity_json beside the old key, but that does not inventory every native
ledger row, private outbox/one-send intent or event ownership.

An exact preservation migration therefore needs an explicitly owned, frozen
inventory of key/typed-identity/status/attempt/provider associations and the
native key/row constraints. Keep the old default and all literal keys untouched.
Any later versioned reader must distinguish the legacy hash-six, base64-six,
base64-seven and system identities, preserve unknown/submitted/pending claims,
and suppress duplicates across approved equivalences without fabricating a
missing DeadlineKey. It must reject ambiguous/unknown formats and avoid rekeying
or replaying live intents. A local recomputation alone cannot prove all existing
identity compatibility.

No such full identity authority/inventory is assigned to this source lane;
planning, ledger, schemas and live worker are unchanged. This is the precise
migration decision held for the integrator, not an authentication or service
failure. The next bounded offline work is classification/source-change closure,
with model/schema/native promotion kept unsupported and outside this packet.
