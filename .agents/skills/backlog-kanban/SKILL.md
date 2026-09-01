---
name: backlog-kanban
description: Where e-footprint bugs, features and ideas go (GitHub issues + Boavizta kanban project 5) and the gh CLI mechanics to manage board items. Use when filing, triaging or scripting backlog items.
---

# backlog-kanban

Conventions for the e-footprint backlog, shared by the library and interface repos.
Kanban board: https://github.com/orgs/Boavizta/projects/5

## Where things go

- **Bugs** → GitHub issues (Boavizta/e-footprint for the library, Boavizta/e-footprint-interface
  for the interface), **plus** a card on the kanban — issues do not appear on the board
  automatically; add them with `gh project item-add`. Prioritized bugs go to "Todo Next".
- **Actionable features and observations** → draft items on the kanban,
  "Problems 🚨, Obs°s 👁️, Ideas 💡" column, where anyone can add cards for later qualification.
- **Long-term or unshaped ideas, open questions** → ONE place: the kanban card
  **"Long-term considerations (parking)"** (OTHER column). One bullet per idea, with
  attribution and date. When an idea matures, it graduates to its own draft.
- **Label and wording fixes** → ONE single ticket: the kanban draft "Labels audit against the
  writing style guide" (rules in `specs/design/writing-style-guide.md` of the interface
  repo) — never separate label tickets.

## How to triage

1. **Dedupe against the kanban first** — most "new" ideas already have a card; extend the
   existing card (dated, attributed note) rather than create a duplicate.
2. **Verify before filing bugs** — reproduce on the deployed app
   (https://e-footprint.boavizta.org/) or run the repro through the current efootprint
   package.
3. **Editing an issue description you authored** is fine for adding key
   requirements/questions (marked, dated section); comments serve as discussion trace.

## gh CLI mechanics

- Kanban read/write needs `gh auth refresh -s project` (`read:project` is not enough).
- Commands: `gh project item-list 5 --owner Boavizta --format json` ·
  `item-create` (drafts) · `item-add` (link real issues) ·
  `item-edit --field-id … --single-select-option-id …` to set the Status column ·
  `item-delete`.
- Status option ids (project 5, field `PVTSSF_lADOBHOQGc4A0kgMzgqLmZs`): Problems `c3fbd533` ·
  Todo Next `f75ad846` · Backlog qualified `7c1ac36a` · ARCHIVE `b1a90c0c` · OTHER `dcefbb77`.
- Draft titles are renamed via GraphQL `updateProjectV2DraftIssue`.
