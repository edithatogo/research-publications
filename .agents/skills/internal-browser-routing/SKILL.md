---
name: internal-browser-routing
description: Apply the repository internal-browser-only rule for sign-in, reauthentication, page access and browser QA.
---

# Internal browser routing

Use the Codex internal browser for every browser-based action unless the user
explicitly directs otherwise. Apply this to tool sign-in, reauthentication,
account selection, consent pages, opening links, browsing, native UI and QA.
Never substitute Chrome, Edge, an external BrowserOS session or a system-browser
launcher. Historical instructions naming those routes do not override AGENTS.md.

Local build, test and file operations are separate. Generic CLI-first guidance
does not authorise a CLI/API substitute for sign-in, reauthentication, opening
or loading pages, web interactions or browser QA. An exception must come from
an explicit user instruction actually covering the operation or a higher-priority
requirement. Check its exact scope; do not infer an exception from an installed
CLI, a qualified adapter or a historical example. Report genuine instruction
conflicts instead of silently broadening an exception.

Preserve the existing authentication workload, guarded entry point and recovery
owner. If an explicitly authorised CLI authentication recipe is applicable,
prevent external-browser launch and open only its freshly generated authorised
URL in the internal browser. Password, MFA, new consent and policy challenges
remain human. Never transfer caches, switch clients to evade a denial or weaken
a guard.

If internal browser access is unavailable or a required operation cannot be
completed there, record the exact limitation and continue independent work.
Do not silently fall back to another browser. An exception needs the operation-specific user
instruction or higher-priority requirement described above.

This skill grants no native mutation, send, recurrence, permission, purchase,
push, merge or deployment authority. Preserve existing scope and rollback gates.

The harness includes this file in its baseline context for every task.
