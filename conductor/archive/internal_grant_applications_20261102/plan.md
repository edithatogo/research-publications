# Internal grant application tracking — closed 2 November 2026

The manual flow **RIMS - Track internal grant applications** stores one application
per GrantConnect opportunity per configured operator in **RIMS Internal Grant
Applications**. SharePoint records the operator as Author and versions each change.
The existing private connection supplies the owner. Keep the flow owner-only.

Use FlowAgent run_flow with the registry item ID and the following trigger body.
For example, read first with `{"RegistryID":28,"Target":"Read","ExpectedVersion":"read"}`.
Read the Result action output for the current stage and odata.etag. Use Draft
and version new to create. Use the returned ETag for every later transition.
After an uncertain write, read before deciding on another action.

| Current stage | Allowed next stages |
| --- | --- |
| Draft | Submitted, Withdrawn |
| Submitted | Awarded, Unsuccessful, Withdrawn |
| Awarded, Unsuccessful, Withdrawn | Terminal |

These stages describe the operator's application. Source opportunity status and
official grant award records retain independent identities. The private store
uses one serial writer and rejects duplicate matches. SharePoint prohibits a
unique column on a list restricted to reading one's own items.

- [x] Provision private versioned storage and deploy the manual writer.
- [x] Test owner identity, stage rules, serialization and exact version matching.
- [x] Read a real opportunity using the deployed flow. Exercise draft, submitted
  and withdrawn through the same actions on an explicitly fictional key in a
  temporary qualification flow. Recycle the fixture and confirm its absence.
- [x] Remove the temporary flow and pause the chat's scheduled GrantConnect
  browser intake. The historical import closeout has separate ownership.
