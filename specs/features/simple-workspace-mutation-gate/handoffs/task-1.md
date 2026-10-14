# Task 1 — Scope the save lock and retire the shared mutation lifecycle

Repository and implementation range: `e-footprint-interface` —
`1e8a8a28103da01d85efb6fc866b18a9e751580c..425ee74917c384553bf114d3db9e95d9827e2f6a`.
Review correction: `197bf0098a3cc30308d242b24ea4994d96ba47c3..0301ca9140d7efe1d6cbfc6f4f70794fe05d8b02`.
The intervening catalog and changelog-policy commits belong to concurrent work.

## Review pointers

- Field and Configure completion match their own XHR through request completion and any pending
  settlement. Document listeners run after body handlers restore native prerequisites and permit rejected OOB swaps.
- Results closure waits for requests and swaps within its own target, plus requests carrying
  `recomputation` that can refresh the panel from outside. Final cleanup reapplies the closed layout
  after late OOB initialization and resolves the current Results button.

## Open concerns

- Task 2 owns the now-inert export busy check in `simplified_inputs/index.js` and the export-specific
  regression updates. The full Jest run currently has nine expected failures in those older export cases;
  complete run gates remain pending Task 2.
- Pre-existing editable `efootprint` changes in `pyproject.toml` and `poetry.lock` remain uncommitted;
  restoring the publishable PyPI dependency remains a prerequisite before merge.
