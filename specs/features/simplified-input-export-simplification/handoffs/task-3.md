# Task 3 — Reconcile export documentation

Repository and documentation range: `e-footprint-interface`, `787564e8..29aa92b9`.

## Review pointers

- Persistence and workspace architecture now describe accepted-state exports, busy suppression without replay, and the dirty/clean Configure behavior.
- The earlier Simplified-input guide and executable mockup reflect the follow-up policy; the plan links the three delivered E2E test names and the follow-up spec.
- `AGENTS.md` still labels the pointer “Save-aware export”; suggest renaming it to “Saved-state export.” `CLAUDE.md` is a symlink to `AGENTS.md`, so no duplicate edit is needed.

## Validation and limitation

`git diff --check`, HTML parsing, updated source/test link checks, and `node --check` on the mockup script passed. The browser could not open the local HTML: its security policy permits only `http:`/`https:` and explicitly prohibited workarounds, so clean/dirty Configure and save/export interactions were not exercised in a rendered browser. No product suites were rerun for this documentation task; Task 2's browser evidence is recorded in its handoff.
