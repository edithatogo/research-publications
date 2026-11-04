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

Use supported CLI/API routes for non-browser work. Before a CLI login, inspect
its qualified recipe so it cannot silently launch an external browser. Reuse
the existing authentication workload, guarded entry point and recovery owner;
open only its freshly generated authorised URL in the internal browser. Keep
password, MFA, new consent and policy challenges human. Never transfer caches,
switch clients to evade a denial or weaken a guard.

If internal browser access is unavailable or a required operation cannot be
completed there, record the exact limitation and continue independent work.
Do not silently fall back to another browser. Only a later explicit user
instruction can change this browser choice.

This skill grants no native mutation, send, recurrence, permission, purchase,
push, merge or deployment authority. Preserve existing scope and rollback gates.

The harness includes this file in its baseline context for every task.
