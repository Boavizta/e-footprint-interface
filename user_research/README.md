# User research

A lightweight, durable record of **needs expressed by real e-footprint users** — so that
recurrent needs surface and get prioritized, instead of being re-discovered every time.

This lives in the interface repo because the interface is the product surface most users
interact with, and prioritization decisions are taken here. Needs may nonetheless be resolved
in either repo (library or interface); each entry notes where.

## How to use it

- **`needs-backlog.md`** — the aggregated, de-duplicated list of expressed needs with a status
  and a recurrence count. This is the file to scan when deciding what to build next. A need
  mentioned by more than one source is a strong prioritization signal.
- **One file per source** (e.g. `2026-05-19-ecoscan.md`) — the raw, dated record of what a
  given user/exercise expressed, what was already addressed, and what was parked. Keep the
  source's own framing; don't pre-filter.

## Conventions

- Name source files `YYYY-MM-DD-<short-source>.md`.
- When a source raises a need, add or bump it in `needs-backlog.md` (increment its recurrence
  count and link back to the source).
- Statuses: **addressed** (link the feature/track), **partially addressed**, **parked**
  (captured, not scheduled), **roadmap** (acknowledged long-term), **out of scope**.
- Don't duplicate the resolution design here — link to the relevant `specs/features/<name>/`
  in the repo that drives it.
