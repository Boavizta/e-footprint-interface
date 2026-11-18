# Local folder link — draft feature kickoff

Status: parked idea for a separate `spec-specify` session · 2026-11-18.
No spec, implementation plan or UI design has been approved for this feature.

## User outcome

A user links a folder on their own machine to the interface, then opens modelings from it and saves
modelings back to it, without going through manual upload and download each time. The folder becomes
the durable place where they keep as many modelings as they want, and possibly later their object
libraries.

In a company setting the folder can be a synced one (for example OneDrive), so backup, sharing and
access control come from company storage rather than from the interface.

## Where the idea comes from

It came up during a technology exploration about deploying e-footprint inside a large company, where
Microsoft Copilot produces the modeling JSON and the user loads it in the interface. Two directions
were discussed there and are **not** part of this feature:

- a standalone build of the interface that runs Django in the browser through Pyodide, so that
  modeling data never leaves the user's machine;
- making `boaviztapi` and the visualisation dependencies optional in the library.

The folder link was first raised for that standalone build, then recognised as doable on the current
hosted Django version. It is parked here because it is useful on its own and because it would carry
over unchanged to a standalone build if the folder logic lives in browser-side JavaScript and talks
to the app only through "load this JSON" and "give me the JSON to save".

## What it does not do

On the hosted version the modeling is still uploaded to the server, held in the session store and
computed there. The folder link gives durable user-managed storage; it does not address the concern
of internal data leaving the company. Only a standalone build would.

## Existing behavior, verified on 18 November

- The interface already has the server half: `upload-json/` loads a modeling, `download-json/` and
  `download-workspace/` return one (`model_builder/urls.py`).
- A workspace holds at most two modelings (`MAX_SLOTS = 2` in
  `model_builder/adapters/repositories/workspace_base.py`) and sessions expire, so there is no
  durable place today for a user to keep many modelings.
- Templates reference no external CDN; all assets are local.

## Browser facts, checked on 18 November

- The folder picker (File System Access API, `showDirectoryPicker`) is available in Chrome and Edge
  since version 86. It needs HTTPS or localhost and a user click.
- Firefox and Safari do not support it and both vendors oppose it. Those users need a fallback.
- Edge has enterprise policies that can disable it (`DefaultFileSystemReadGuardSetting`,
  `DefaultFileSystemWriteGuardSetting`), with per-site allowlists. The CIS hardening benchmarks
  recommend blocking file system access by default.

Not verified:

- whether the target company's Edge configuration blocks the folder picker. This is the main risk
  and is quick to test on a company laptop with any demo page that uses the picker;
- whether Chrome and Edge let the user grant folder access "on every visit" rather than
  re-confirming each session (believed true for recent versions);
- whether Copilot can save its output JSON into a user's synced folder, which would remove the
  manual import step.

## Questions for the future specification

- When is the folder written to: an explicit "save to folder" action, a save on leaving the page,
  or auto-save on each edit? Auto-save costs a JSON download round-trip per change, and JSON
  round-trips are already a known latency constraint. The exploration leaned towards starting with
  an explicit save.
- What happens when a file changes on disk while the modeling is open (sync client or another
  tool)? Which side wins, and how is the user told?
- How does the folder relate to the two-slot workspace: does it replace the slots as the list of
  available modelings, or sit beside them as a file browser?
- What is the experience in browsers without the folder picker, or where policy blocks it? Is it
  simply today's upload and download, or something more?
- How are files named and recognised as modelings? What happens with JSON files that are not
  e-footprint modelings, or that come from an older library version?
- Are object libraries in scope for the first version or a later one? They may deserve their own
  spec.
- Does the folder link need any onboarding or explanation about what the interface can and cannot
  see on the user's machine?

## Suggested scope for a first version

Keep it to one linked folder, opening and explicitly saving modelings, in Chrome and Edge, with
today's upload and download remaining the path for everyone else. Refine with `spec-specify`; do not
treat this kickoff as a finished specification.
